import os
from flask import Flask

from app.services.db_service import init_db


def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    app.config["TEMP_FOLDER"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
    app.config["SECRET_KEY"] = "dev-secret-key"

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["TEMP_FOLDER"], exist_ok=True)

    init_db(app.config["UPLOAD_FOLDER"], app.config["TEMP_FOLDER"])

    from app.routes import register_routes
    register_routes(app)

    return app


app = create_app()
