from datetime import datetime, timezone

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import cloudinary
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'

    # Configure Cloudinary
    cloudinary.config(
        cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=app.config['CLOUDINARY_API_KEY'],
        api_secret=app.config['CLOUDINARY_API_SECRET']
    )

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.book_routes import book_bp
    from app.routes.user_routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(user_bp)

    # Import models to ensure they are registered with SQLAlchemy
    from app.models import User, Role, Book, Category, Order, OrderDetail, Review, PaymentTransaction

    # Add shell context
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': User,
            'Role': Role,
            'Book': Book,
            'Category': Category,
            'Order': Order,
            'OrderDetail': OrderDetail,
            'Review': Review,
            'PaymentTransaction': PaymentTransaction
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}

    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.now(timezone.utc)
        }

    @app.template_global('now')
    def get_now():
        """Hàm now() để sử dụng trong templates."""
        return datetime.now(timezone.utc)
    return app