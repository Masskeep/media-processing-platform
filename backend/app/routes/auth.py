from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    print("🔥 REGISTER ROUTE WAS CALLED")
    if not request.is_json:
        return jsonify({
            "error": "Request must be JSON. Set Content-Type to application/json."
        }), 400

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    if (
        "name" not in data or
        "email" not in data or
        "password" not in data
    ):
        return jsonify({
            "error": "Missing required fields: name, email, and password"
        }), 400
    if(
        not data["name"] or
        not data["email"] or
        not data["password"]
    ):
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