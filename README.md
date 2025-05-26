# pdf-collab-system
A web application designed to facilitate the seamless management and collaboration of pdfs. The system enables users to sign up, upload PDFs, share them with other users, and collaborate through comments. 

## Features
- User authentication system
- PDF upload and management
- Document sharing via unique links
- Commenting system with threading
- Guest access for shared documents
- Email notifications

## Quick Start
1. Clone the repository
2. Set up virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Configure `.env` file
5. Initialize database: `mysql -u root -p < schema.sql`
6. Run the application: `python app.py`

## Requirements
- Python 3.8+
- MySQL 8.0+
- Modern web browser

## Configuration
Fill in your configuration in `.env`:
- Database credentials
- Email SMTP settings
- Secret key