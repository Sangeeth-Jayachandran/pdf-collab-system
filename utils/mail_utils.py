from flask import current_app, url_for
from flask_mail import Message
from threading import Thread
from extensions import mail

def send_async_email(app, msg):
    """Send email asynchronously using a background thread"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, template, **kwargs):
    """Send email with the given template"""
    app = mail.app
    msg = Message(
        subject=subject,
        recipients=recipients,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    msg.body = template.format(**kwargs)
    # For HTML emails, you could add:
    # msg.html = render_template(template + '.html', **kwargs)
    
    # Send email in background thread
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_share_email(recipient, sharer_name, filename, share_url):
    """Send PDF share notification email"""
    subject = f"Shared PDF: {filename}"
    template = f"""Hello,

{sharer_name} has shared a PDF with you:

File: {filename}
View Link: {share_url}

You can access this PDF without logging in.

Best regards,
PDF Collaboration Team
"""
    send_email(subject, [recipient], template)

def send_password_reset_email(user, reset_url):
    try:
        # Handle both User objects and dictionaries
        user_name = user.name if hasattr(user, 'name') else user.get('name', 'User')
        user_email = user.email if hasattr(user, 'email') else user.get('email', '')
        
        template = f"""Hello {user_name},
        
You requested a password reset for your account. Please click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.
"""
        msg = Message(
            subject="Password Reset Request",
            recipients=[user_email],
            body=template,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {str(e)}")
        raise