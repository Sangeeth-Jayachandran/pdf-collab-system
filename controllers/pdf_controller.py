from flask import (
    current_app,
    render_template, 
    request,
    flash, 
    redirect, 
    url_for, 
    send_from_directory,
)
from flask_login import login_required, current_user
from utils.database import db_cursor
from utils.file_upload import allowed_file, save_uploaded_file
import os
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_required
def dashboard():
    search_query = request.args.get('q', '')
    
    try:
        with db_cursor() as cursor:
            # Initialize empty lists as fallback
            user_pdfs = []
            shared_pdfs = []
            
            # Get user's PDFs (with null check)
            cursor.execute("""
                SELECT id, filename, upload_date 
                FROM pdf_files 
                WHERE user_id = %s 
                ORDER BY upload_date DESC
            """, (current_user.id,))
            result = cursor.fetchall()
            user_pdfs = result if result else []
            
            # Get shared PDFs (with null check)
            cursor.execute("""
                SELECT pf.id, pf.filename, pf.upload_date, u.name as owner_name 
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                JOIN users u ON pf.user_id = u.id
                WHERE sf.created_by = %s  # Changed from shared_with to created_by
                ORDER BY pf.upload_date DESC
            """, (current_user.id,))
            result = cursor.fetchall()
            shared_pdfs = result if result else []
            
            return render_template('dashboard.html', 
                               user_pdfs=user_pdfs,
                               shared_pdfs=shared_pdfs,
                               search_query=search_query)
            
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        flash('Error loading dashboard content', 'warning')
        return render_template('dashboard.html', 
                           user_pdfs=[], 
                           shared_pdfs=[],
                           search_query=search_query)

@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('pdf_routes.dashboard'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('pdf_routes.dashboard'))
    
    try:
        if file and allowed_file(file.filename):
            # Debug logging
            current_app.logger.info(f"Attempting to upload file: {file.filename}")
            
            # Ensure upload directory exists
            upload_dir = Config.UPLOAD_FOLDER
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                current_app.logger.info(f"Created upload directory: {upload_dir}")
            
            # Save file and record in database
            unique_filename = save_uploaded_file(file, current_user.id)
            
            # Verify file was saved
            file_path = os.path.join(upload_dir, unique_filename)
            if not os.path.exists(file_path):
                raise Exception("File failed to save to disk")
            
            flash('File uploaded successfully', 'success')
        else:
            flash('Only PDF files are allowed', 'danger')
    except Exception as e:
        current_app.logger.error(f"Upload failed: {str(e)}", exc_info=True)
        flash('Error uploading file', 'danger')
    
    return redirect(url_for('pdf_routes.dashboard'))

@login_required
def view_pdf(file_id):
    try:
        with db_cursor() as cursor:
            pdf_file = get_pdf_with_access(cursor, file_id, current_user.id)
            if not pdf_file:
                flash('You do not have access to this file', 'danger')
                return redirect(url_for('pdf_routes.dashboard'))
            
            comments = get_comments_for_file(cursor, file_id)
            
            return render_template('pdf_viewer.html', 
                               pdf_file=pdf_file, 
                               comments=comments,
                               file_url=url_for('pdf_routes.uploaded_file', filename=pdf_file['filepath']))
    except Exception as e:
        flash('An error occurred while accessing the file', 'danger')
        return redirect(url_for('pdf_routes.dashboard'))

@login_required
def uploaded_file(filename):
    """Serve uploaded PDF files"""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@login_required
def delete_pdf(file_id):
    try:
        with db_cursor() as cursor:
            # Verify file ownership
            cursor.execute("SELECT * FROM pdf_files WHERE id = %s AND user_id = %s", 
                         (file_id, current_user.id))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('File not found or you do not have permission to delete it', 'danger')
                return redirect(url_for('pdf_routes.dashboard'))
            
            # Delete the physical file
            file_path = os.path.join(Config.UPLOAD_FOLDER, pdf_file['filepath'])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete database records
            cursor.execute("DELETE FROM pdf_files WHERE id = %s", (file_id,))
            
            flash('PDF deleted successfully', 'success')
            return redirect(url_for('pdf_routes.dashboard'))
    except Exception as e:
        flash('Error deleting PDF', 'danger')
        return redirect(url_for('pdf_routes.dashboard'))

@login_required
def search():
    try:
        search_query = request.args.get('q', '').strip()
        
        if not search_query:
            return redirect(url_for('pdf_routes.dashboard'))
        
        with db_cursor() as cursor:
            # Search user's own PDFs
            cursor.execute("""
                SELECT id, filename, upload_date 
                FROM pdf_files 
                WHERE user_id = %s AND filename LIKE %s
                ORDER BY upload_date DESC
            """, (current_user.id, f"%{search_query}%"))
            user_pdfs = cursor.fetchall()
            
            # Search shared PDFs (optional)
            cursor.execute("""
                SELECT pf.id, pf.filename, pf.upload_date, u.name as owner_name 
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                JOIN users u ON pf.user_id = u.id
                WHERE sf.share_token IN (
                    SELECT share_token FROM shared_files WHERE created_by = %s
                )
                AND pf.filename LIKE %s
            """, (current_user.id, f"%{search_query}%"))
            shared_pdfs = cursor.fetchall()
            
            return render_template('dashboard.html', 
                               user_pdfs=user_pdfs,
                               shared_pdfs=shared_pdfs,
                               search_query=search_query)
            
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        flash('Error performing search', 'danger')
        return redirect(url_for('pdf_routes.dashboard'))


# Helper functions
def get_pdf_with_access(cursor, file_id, user_id):
    cursor.execute("""
        SELECT pf.* FROM pdf_files pf
        LEFT JOIN shared_files sf ON pf.id = sf.file_id
        WHERE pf.id = %s AND (pf.user_id = %s OR sf.created_by = %s)
    """, (file_id, user_id, user_id))
    return cursor.fetchone()

def get_comments_for_file(cursor, file_id):
    cursor.execute("""
        SELECT c.*, COALESCE(u.name, 'Guest') as user_name 
        FROM comments c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.file_id = %s
        ORDER BY c.created_at ASC
    """, (file_id,))
    return cursor.fetchall()