from extensions import bcrypt
from flask import current_app, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user
from utils.database import db_cursor
from utils.auth_utils import is_email_registered, validate_registration, validate_login
from utils.mail_utils import send_password_reset_email
import secrets
from datetime import datetime, timedelta
from models import User

def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if is_email_registered(email):
            flash("Email already exists.", "danger")
            return redirect(url_for('auth_routes.register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            connection = current_app.db_pool.get_connection()
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """, (name, email, hashed_password))
            connection.commit()
            cursor.close()
            connection.close()

            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('auth_routes.login'))

        except Exception as e:
            print(f"Error during registration: {e}")
            flash("An error occurred. Please try again.", "danger")

    return render_template("auth/register.html")

def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            user, error = validate_login(email, password)
            if error:
                flash(error, 'danger')
                return render_template('auth/login.html')
            
            if not user:
                flash('Invalid email or password', 'danger')
                return render_template('auth/login.html')
            
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('pdf_routes.dashboard'))
        
        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred during login', 'danger')
    
    return render_template('auth/login.html')

def logout():
    logout_user()
    return redirect(url_for('auth_routes.login'))

def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        with db_cursor() as cursor:
            # Check if email exists
            cursor.execute("SELECT id, email, name FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                # Generate reset token (valid for 1 hour)
                reset_token = secrets.token_urlsafe(32)
                expiry_time = datetime.now() + timedelta(hours=1)
                
                # Store token in database
                cursor.execute(
                    "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                    (user['id'], reset_token, expiry_time)
                )
                
                # Send reset email
                reset_url = url_for('auth_routes.reset_password', token=reset_token, _external=True)
                send_password_reset_email(user, reset_url)
                flash('Password reset link has been sent to your email', 'success')
            else:
                flash('If this email exists in our system, a reset link will be sent', 'success')
        
        return redirect(url_for('auth_routes.login'))
    
    return render_template('auth/forgot_password.html')

def reset_password(token):
    with db_cursor() as cursor:
        # Verify token
        cursor.execute("""
            SELECT prt.*, u.email 
            FROM password_reset_tokens prt
            JOIN users u ON prt.user_id = u.id
            WHERE prt.token = %s AND prt.expires_at > NOW() AND prt.used = 0
        """, (token,))
        token_data = cursor.fetchone()
        
        if not token_data:
            flash('Invalid or expired password reset link', 'danger')
            return redirect(url_for('auth_routes.forgot_password'))
        
        if request.method == 'POST':
            new_password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            if new_password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(request.url)
            
            # Update password
            hashed_password = User.generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s",
                (hashed_password, token_data['user_id'])
            )
            
            # Mark token as used
            cursor.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE token = %s",
                (token,)
            )
            
            flash('Password updated successfully. Please login with your new password.', 'success')
            return redirect(url_for('auth_routes.login'))
    
    return render_template('auth/reset_password.html', token=token)