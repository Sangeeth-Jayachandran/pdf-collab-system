import os
from flask import Flask
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config
from routes.auth_routes import auth_bp 
from routes.comment_routes import comment_bp
from routes.pdf_routes import pdf_bp
from routes.share_routes import share_bp
from routes.user_routes import user_bp
from utils.database import db_pool

def create_application():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    mail = Mail(app)
    bcrypt = Bcrypt(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth_routes.login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.get_by_id(user_id) 

    db_pool.init_app(app)
    app.db_pool = db_pool
    
    app.mail = mail
    app.bcrypt = bcrypt
    app.login_manager = login_manager
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(user_bp)
    
    return app

app = create_application()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))