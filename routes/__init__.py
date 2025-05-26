from .auth_routes import auth_bp
from .pdf_routes import pdf_bp
from .share_routes import share_bp
from .comment_routes import comment_bp
from .user_routes import user_bp

def register_routes(app):
    """Register all route blueprints with the application"""
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    app.register_blueprint(share_bp, url_prefix='/share')
    app.register_blueprint(comment_bp, url_prefix='/comment')
    app.register_blueprint(user_bp, url_prefix='/user')