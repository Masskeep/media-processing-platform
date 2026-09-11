from sqlalchemy.exc import IntegrityError

from flask import Blueprint, jsonify, request
from app.models.user import User
from app.extensions import db
from werkzeug.security import generate_password_hash


users_bp = Blueprint("users", __name__)

@users_bp.route("/api/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([
        {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
        for user in users
    ])

@users_bp.route("/api/users", methods=["POST"])
def create_user():
    if not request.is_json:
        return jsonify({
            "error": "Request must be JSON"
        }), 400

    data = request.get_json()

    if "name" not in data or "email" not in data or "password" not in data:
        return jsonify({
            "error": "Missing required fields: name, email, and password"
        }), 400

    if not data["name"] or not data["email"] or not data["password"]:
        return jsonify({
            "error": "Name, email, and password cannot be empty"
        }), 400

    password_hash = generate_password_hash(data["password"])

    user = User(
        name = data["name"],
        email = data["email"],
        password_hash = password_hash
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email already exists"}), 409

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    }), 201
