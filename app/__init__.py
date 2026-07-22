import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from app.services.db_service import init_db

# Define User class for Flask-Login
class User:
    def __init__(self, user_dict):
        self.id = user_dict["id"]
        self.username = user_dict["username"]
        self.email = user_dict["email"]
        self.role = user_dict["role"]
        self.status = user_dict["status"]
        self.profile_picture = user_dict.get("profile_picture") if hasattr(user_dict, "get") else None
        
    @property
    def is_authenticated(self):
        return True
        
    @property
    def is_active(self):
        return self.status == 'active'
        
    @property
    def is_anonymous(self):
        return False
        
    def get_id(self):
        return str(self.id)


def create_app():
    app = Flask(__name__)
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", os.path.join(base_dir, "uploads"))
    app.config["TEMP_FOLDER"] = os.environ.get("TEMP_FOLDER", os.path.join(base_dir, "temp"))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["TEMP_FOLDER"], exist_ok=True)

    init_db(app.config["UPLOAD_FOLDER"], app.config["TEMP_FOLDER"])

    from app.routes import register_routes
    from flask_login import LoginManager
    from app.services.db_service import get_user_by_id

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        user_dict = get_user_by_id(user_id)
        if user_dict:
            return User(user_dict)
        return None

    # Expose login_enabled to templates automatically
    from app.services.db_service import is_login_enabled
    @app.context_processor
    def inject_login_enabled():
        return dict(login_enabled=is_login_enabled())

    register_routes(app)

    return app


app = create_app()
