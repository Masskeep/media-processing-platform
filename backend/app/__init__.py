from flask import Flask
from dotenv import load_dotenv
import os
from flask_cors import CORS

from app.extensions import db, migrate
from flask_jwt_extended import JWTManager
from datetime import timedelta
def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)  # Set token expiration time
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)  # Set refresh token expiration time
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app, resources={r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174"
        ]
    }})

    db.init_app(app)
    migrate.init_app(app, db)
    jwt = JWTManager(app)
    from app.routes.users import users_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)

    from app.models.user import User

    return app