from flask import Flask
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config
from utils.database import db_pool
from routes import register_routes

def create_application():
    # Initialize Flask application
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    mail = Mail(app)
    bcrypt = Bcrypt(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth_routes.login'
    
    # Initialize database pool
    db_pool.init_app(app)
    
    # Store extensions in app context for easy access
    app.mail = mail
    app.bcrypt = bcrypt
    app.login_manager = login_manager
    
    # Register routes
    register_routes(app)
    
    return app

# Create the application instance
application = create_application()

if __name__ == '__main__':
    application.run(debug=True)