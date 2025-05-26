from flask import jsonify, redirect, render_template, request, flash, url_for
from flask_login import login_required, current_user
from utils.database import db_cursor
from utils.mail_utils import send_share_email
import secrets
import os
from config import Config

@login_required
def share_pdf(file_id):
    """Generate a shareable link for a PDF"""
    try:
        with db_cursor() as cursor:
            # Verify file ownership
            cursor.execute("SELECT * FROM pdf_files WHERE id = %s AND user_id = %s", 
                         (file_id, current_user.id))
            if not cursor.fetchone():
                flash('No permission to share this file', 'danger')
                return redirect(url_for('pdf_routes.dashboard'))

            # Generate unique share token
            share_token = secrets.token_urlsafe(32)
            
            # Store share token in database
            cursor.execute("""
                INSERT INTO shared_files (file_id, share_token, created_by)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE share_token = VALUES(share_token)
            """, (file_id, share_token, current_user.id))
            
            # Generate share URL
            share_url = url_for('share_routes.view_shared_pdf', token=share_token, _external=True)
            
            return jsonify({
                'success': True,
                'url': share_url
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@login_required
def share_pdf_email(file_id):
    """Share PDF via email"""
    email = request.form.get('email')
    if not email:
        return jsonify({
            'success': False,
            'error': 'Email address is required'
        }), 400
    
    try:
        with db_cursor() as cursor:
            # Get file info and share token
            cursor.execute("""
                SELECT pf.filename, sf.share_token 
                FROM pdf_files pf
                LEFT JOIN shared_files sf ON pf.id = sf.file_id
                WHERE pf.id = %s AND pf.user_id = %s
            """, (file_id, current_user.id))
            result = cursor.fetchone()
            
            if not result or not result['share_token']:
                return jsonify({
                    'success': False,
                    'error': 'File not found or not shared'
                }), 404
            
            # Send share email
            share_url = url_for('share_routes.view_shared_pdf', 
                              token=result['share_token'], 
                              _external=True)
            send_share_email(
                recipient=email,
                sharer_name=current_user.name,
                filename=result['filename'],
                share_url=share_url
            )
            
            return jsonify({
                'success': True,
                'message': f'Share link sent to {email}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def view_shared_pdf(token):
    """View a shared PDF"""
    try:
        with db_cursor() as cursor:
            # Get PDF file by share token
            cursor.execute("""
                SELECT pf.*, sf.share_token 
                FROM pdf_files pf
                JOIN shared_files sf ON pf.id = sf.file_id
                WHERE sf.share_token = %s
            """, (token,))
            pdf_file = cursor.fetchone()
            
            if not pdf_file:
                flash('Invalid or expired share link', 'danger')
                return redirect(url_for('auth_routes.login'))
            
            # Get comments for the PDF
            cursor.execute("""
                SELECT c.*, COALESCE(u.name, 'Anonymous') as user_name
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.file_id = %s
                ORDER BY c.created_at
            """, (pdf_file['id'],))
            comments = cursor.fetchall()
            
            return render_template('pdf_viewer.html',
                pdf_file=pdf_file,
                comments=comments,
                file_url=url_for('pdf_routes.uploaded_file', filename=pdf_file['filepath']),
                is_shared=True,
                share_token=token
            )
    except Exception as e:
        flash('Error loading shared PDF', 'danger')
        return redirect(url_for('auth_routes.login'))