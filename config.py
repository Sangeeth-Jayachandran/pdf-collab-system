import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-here'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Database configuration
    DB_HOST = os.getenv('DB_HOST') or 'localhost'
    DB_USER = os.getenv('DB_USER') or 'root'
    DB_PASSWORD = os.getenv('DB_PASSWORD') or ''
    DB_NAME = os.getenv('DB_NAME') or 'pdf_collab'