from contextlib import contextmanager
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import mysql.connector
from config import Config
from mysql.connector import pooling
import logging

app = Flask(__name__)
app.config.from_object(Config)
bcrypt = Bcrypt(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection pool
db_pool = pooling.MySQLConnectionPool(
    pool_name="pdf_pool",
    pool_size=5,
    host=app.config['DB_HOST'],
    user=app.config['DB_USER'],
    password=app.config['DB_PASSWORD'],
    database=app.config['DB_NAME'],
    buffered=True,
    autocommit=True
)

# Login manager setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@contextmanager
def db_cursor():
    """Context manager for database cursor with proper cleanup"""
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def get_db_connection():
    """Get a connection from the pool (for operations not using the context manager)"""
    return db_pool.get_connection()

from models import User

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['email'], user_data['name'])
        return None

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        try:
            with db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_password)
                )
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Email already exists. Please use a different email.', 'danger')
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        with db_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            
            if user_data and bcrypt.check_password_hash(user_data['password'], password):
                user = User(user_data['id'], user_data['email'], user_data['name'])
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Login failed. Check email and password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        with db_cursor() as cursor:
            # Get user's PDFs
            cursor.execute("""
                SELECT id, filename, upload_date 
                FROM pdf_files 
                WHERE user_id = %s 
                ORDER BY upload_date DESC
            """, (current_user.id,))
            user_pdfs = cursor.fetchall()
            
            # Get shared PDFs
            cursor.execute("""
                SELECT pf.id, pf.filename, pf.upload_date, u.name as owner_name 
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                JOIN users u ON pf.user_id = u.id
                WHERE sf.share_token IN (
                    SELECT share_token FROM shared_files WHERE created_by = %s
                )
            """, (current_user.id,))
            shared_pdfs = cursor.fetchall()
            
            return render_template('dashboard.html', user_pdfs=user_pdfs, shared_pdfs=shared_pdfs)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard', 'danger')
        return redirect(url_for('home'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        try:
            with db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO pdf_files (user_id, filename, filepath) VALUES (%s, %s, %s)",
                    (current_user.id, filename, unique_filename)
                )
                flash('File uploaded successfully', 'success')
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            flash('Error uploading file', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        flash('Only PDF files are allowed', 'danger')
    
    return redirect(url_for('dashboard'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/view/<int:file_id>')
@login_required
def view_pdf(file_id):
    try:
        with db_cursor() as cursor:
            # Check file access
            cursor.execute("""
                SELECT pf.* FROM pdf_files pf
                LEFT JOIN shared_files sf ON pf.id = sf.file_id
                WHERE pf.id = %s AND (pf.user_id = %s OR sf.created_by = %s)
            """, (file_id, current_user.id, current_user.id))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('You do not have access to this file', 'danger')
                return redirect(url_for('dashboard'))
            
            # Get comments
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Guest') as user_name 
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.file_id = %s
                ORDER BY c.created_at ASC
            """, (file_id,))
            comments = cursor.fetchall()
            
            # Debug: Check what we're passing to the template
            app.logger.debug(f"PDF File: {pdf_file}")
            app.logger.debug(f"Comments: {comments[:2]}")  # First 2 comments for debugging
            
            return render_template('pdf_viewer.html', 
                               pdf_file=pdf_file, 
                               comments=comments,
                               file_url=url_for('uploaded_file', filename=pdf_file['filepath']))
    
    except Exception as e:
        app.logger.error(f"Error in view_pdf: {str(e)}", exc_info=True)
        flash('An error occurred while accessing the file', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/share/<int:file_id>', methods=['GET', 'POST'])
@login_required
def share_pdf(file_id):
    try:
        with db_cursor() as cursor:
            # Verify file ownership
            cursor.execute("SELECT * FROM pdf_files WHERE id = %s AND user_id = %s", 
                         (file_id, current_user.id))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('File not found or you do not have permission to share it', 'danger')
                return redirect(url_for('dashboard'))
            
            # Check if share link already exists
            cursor.execute("SELECT * FROM shared_files WHERE file_id = %s", (file_id,))
            existing_share = cursor.fetchone()
            
            if request.method == 'POST':
                if existing_share:
                    # If share exists, just return the existing link
                    share_url = url_for('view_shared_pdf', token=existing_share['share_token'], _external=True)
                    flash(f'Share link already exists: {share_url}', 'info')
                else:
                    # Create new share link
                    share_token = uuid.uuid4().hex
                    cursor.execute(
                        "INSERT INTO shared_files (file_id, share_token, created_by) VALUES (%s, %s, %s)",
                        (file_id, share_token, current_user.id)
                    )
                    share_url = url_for('view_shared_pdf', token=share_token, _external=True)
                    flash(f'Share link created: {share_url}', 'success')
                
                return redirect(url_for('share_pdf', file_id=file_id))
            
            return render_template('share_pdf.html', 
                                pdf_file=pdf_file, 
                                share=existing_share)  # Pass single share instead of list
    except mysql.connector.IntegrityError:
        flash('This file already has a share link', 'warning')
        return redirect(url_for('share_pdf', file_id=file_id))
    except Exception as e:
        logger.error(f"Share PDF error: {str(e)}")
        flash('Error sharing file', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/shared/<token>')
def view_shared_pdf(token):
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT pf.*, sf.share_token 
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                WHERE sf.share_token = %s
            """, (token,))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('Invalid or expired share link', 'danger')
                return redirect(url_for('home'))
            
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Guest') as user_name 
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.file_id = %s
                ORDER BY c.created_at ASC
            """, (pdf_file['id'],))
            comments = cursor.fetchall()
            
            return render_template('pdf_viewer.html', 
                                 pdf_file=pdf_file, 
                                 comments=comments,
                                 file_url=url_for('uploaded_file', filename=pdf_file['filepath']),
                                 is_shared=True,
                                 share_token=token)
    except Exception as e:
        logger.error(f"Shared PDF view error: {str(e)}")
        flash('Error accessing shared file', 'danger')
        return redirect(url_for('home'))

@app.route('/comment', methods=['POST'])
def add_comment():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    file_id = data.get('file_id')
    content = data.get('content')
    parent_id = data.get('parent_id')
    share_token = data.get('share_token')
    
    if not content or not file_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        with db_cursor() as cursor:
            # Verify access
            user_id = None
            if current_user.is_authenticated:
                cursor.execute("""
                    SELECT 1 FROM pdf_files 
                    WHERE id = %s AND (user_id = %s OR id IN (
                        SELECT file_id FROM shared_files WHERE created_by = %s
                    ))
                """, (file_id, current_user.id, current_user.id))
                if not cursor.fetchone():
                    return jsonify({'error': 'No access to this file'}), 403
                user_id = current_user.id
            elif share_token:
                cursor.execute("""
                    SELECT 1 FROM shared_files 
                    WHERE file_id = %s AND share_token = %s
                """, (file_id, share_token))
                if not cursor.fetchone():
                    return jsonify({'error': 'Invalid share token'}), 403
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Add comment
            cursor.execute("""
                INSERT INTO comments (file_id, user_id, content, parent_id)
                VALUES (%s, %s, %s, %s)
            """, (file_id, user_id, content, parent_id))
            
            # Get the new comment with user info
            comment_id = cursor.lastrowid
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Guest') as user_name 
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.id = %s
            """, (comment_id,))
            new_comment = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'comment': {
                    'id': new_comment['id'],
                    'content': new_comment['content'],
                    'user_name': new_comment['user_name'],
                    'created_at': new_comment['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    'parent_id': new_comment['parent_id']
                }
            })
    except Exception as e:
        logger.error(f"Add comment error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('dashboard'))
    
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, upload_date 
                FROM pdf_files 
                WHERE user_id = %s AND filename LIKE %s
                ORDER BY upload_date DESC
            """, (current_user.id, f"%{query}%"))
            results = cursor.fetchall()
            
            return render_template('dashboard.html', user_pdfs=results, shared_pdfs=[], search_query=query)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        flash('Error performing search', 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)