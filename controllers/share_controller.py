from flask import current_app, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from utils.database import db_cursor
import secrets
from datetime import datetime, timedelta
from extensions import mail
from utils.mail_utils import send_share_email
from flask_mail import Message 

@login_required
def share_pdf(file_id):
    """Handle PDF sharing page"""
    try:
        with db_cursor() as cursor:
            # 1. Verify file ownership
            cursor.execute("""
                SELECT * FROM pdf_files 
                WHERE id = %s AND user_id = %s
            """, (file_id, current_user.id))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('No permission to share this file', 'danger')
                return redirect(url_for('pdf_routes.dashboard'))

            # 2. Check for existing share link
            cursor.execute("""
                SELECT * FROM shared_files 
                WHERE file_id = %s AND created_by = %s
            """, (file_id, current_user.id))
            share = cursor.fetchone()

            # 3. Handle form submissions
            if request.method == 'POST':
                action = request.form.get('action')
                
                if action == 'create':
                    # Create new share link
                    share_token = secrets.token_urlsafe(32)
                    expires_at = datetime.now() + timedelta(days=7)
                    
                    cursor.execute("""
                        INSERT INTO shared_files 
                        (file_id, share_token, created_by, expires_at)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        share_token = VALUES(share_token),
                        expires_at = VALUES(expires_at)
                    """, (file_id, share_token, current_user.id, expires_at))
                    flash('Share link created successfully', 'success')
                    
                elif action == 'refresh':
                    # Refresh existing share link
                    new_token = secrets.token_urlsafe(32)
                    cursor.execute("""
                        UPDATE shared_files 
                        SET share_token = %s, expires_at = %s
                        WHERE id = %s
                    """, (new_token, datetime.now() + timedelta(days=7), share['id']))
                    flash('Share link refreshed successfully', 'success')

                elif action == 'permissions':
                    allow_comments = 'allow_comments' in request.form
                    allow_download = 'allow_download' in request.form
                    
                    cursor.execute("""
                        UPDATE shared_files 
                        SET allow_comments = %s, allow_download = %s
                        WHERE file_id = %s AND created_by = %s
                    """, (allow_comments, allow_download, file_id, current_user.id))
            
                    flash('Permissions updated successfully', 'success')
                                    
                return redirect(url_for('share_routes.share_pdf', file_id=file_id))

            # 4. Render the template
            return render_template('share_pdf.html',
                pdf_file=pdf_file,
                share=share,
                share_expiry_delta=timedelta(days=7))
                
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('pdf_routes.view_pdf', file_id=file_id))

@login_required
def share_pdf_email(file_id):
    """Handle email sharing with immediate feedback"""
    email = request.form.get('email')
    if not email:
        flash('❌ Email address is required', 'danger')
        return redirect(url_for('share_routes.share_pdf', file_id=file_id))
    
    try:
        with db_cursor() as cursor:
            # Get file and share info
            cursor.execute("""
                SELECT pf.filename, sf.share_token
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                WHERE pf.id = %s AND pf.user_id = %s
                LIMIT 1
            """, (file_id, current_user.id))
            result = cursor.fetchone()
            
            if not result or not result.get('share_token'):
                flash('❌ Please create a share link first', 'danger')
                return redirect(url_for('share_routes.share_pdf', file_id=file_id))
            
            # Prepare email content
            share_url = url_for('share_routes.view_shared_pdf', 
                              token=result['share_token'], 
                              _external=True)
            
            try:
                msg = Message(
                    subject=f"📄 {current_user.name} shared a PDF with you",
                    recipients=[email],
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    body=f"""
                    {current_user.name} has shared a PDF with you:
                    File: {result['filename']}
                    Link: {share_url}
                    This link expires in 7 days.
                    """
                )
                
                mail.send(msg)
                print(f"Attempting to send email to {email}") 
                print(f"Using SMTP: {current_app.config['MAIL_SERVER']}:{current_app.config['MAIL_PORT']}")
                print(f"Auth: {current_app.config['MAIL_USERNAME']}")
                flash('✅ Share link sent successfully!', 'success')
                current_app.logger.info(f"Email sent to {email}")
                
            except Exception as email_error:
                error_msg = f"❌ Failed to send email: {str(email_error)}"
                current_app.logger.error(error_msg)
                flash(error_msg, 'danger')
            
            return redirect(url_for('share_routes.share_pdf', file_id=file_id))
            
    except Exception as e:
        error_msg = f"❌ System error: {str(e)}"
        current_app.logger.error(error_msg)
        flash(error_msg, 'danger')
        return redirect(url_for('share_routes.share_pdf', file_id=file_id))
    
def view_shared_pdf(token):
    """View a shared PDF without requiring login"""
    try:
        with db_cursor() as cursor:
            # 1. Verify the share token is valid
            cursor.execute("""
                SELECT pf.*, sf.share_token, sf.allow_comments
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                WHERE sf.share_token = %s
                AND (sf.expires_at IS NULL OR sf.expires_at > NOW())
            """, (token,))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('Invalid or expired share link', 'danger')
                return redirect(url_for('auth_routes.login'))
            
            # 2. Get comments for the PDF
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Anonymous') as user_name
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.file_id = %s
                ORDER BY c.created_at
            """, (pdf_file['id'],))
            comments = cursor.fetchall()
            
            # 3. Render the PDF viewer template
            return render_template('pdf_viewer.html',
                pdf_file=pdf_file,
                comments=comments,
                file_url=url_for('pdf_routes.uploaded_file', filename=pdf_file['filepath']),
                is_shared=True,
                share_token=token
            )
            
    except Exception as e:
        current_app.logger.error(f"Error loading shared PDF: {str(e)}")
        flash('Error loading PDF', 'danger')
        return redirect(url_for('auth_routes.login'))
