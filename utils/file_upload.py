import os
import uuid
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def save_uploaded_file(file, user_id):
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    
    file.save(filepath)
    
    with db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO pdf_files (user_id, filename, filepath) VALUES (%s, %s, %s)",
            (user_id, filename, unique_filename)
        )
    
    return unique_filename