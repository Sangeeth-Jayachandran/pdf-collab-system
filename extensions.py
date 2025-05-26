from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

mail = Mail()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth_routes.login'