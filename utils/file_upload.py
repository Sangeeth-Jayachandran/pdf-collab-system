import os
import uuid
from datetime import datetime
from config import Config
import logging

from utils.database import db_cursor

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file, user_id):
    """Save uploaded file with unique name and store metadata"""
    try:
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        
        # Save file
        file.save(filepath)
        
        # Store file metadata in database
        with db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO pdf_files 
                (user_id, filename, filepath) 
                VALUES (%s, %s, %s)
            """, (user_id, file.filename, unique_name))
            
        return unique_name
    except Exception as e:
        # Clean up if file was partially saved
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        raise e