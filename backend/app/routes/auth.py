from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.user import User
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()

    new_access_token = create_access_token(identity = user_id)

    return jsonify({
        "access_token": new_access_token
    }), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    }),200



@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({
            "error" : "Request must be JSON"
        }),400
    if "email" not in data or "password" not in data:
        return jsonify({
            "error" : "Missing required fields: email and password"
        }), 400

    user = User.query.filter_by(email= data["email"]).first()

    if not user:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    if not check_password_hash(user.password_hash, data["password"]):
        return jsonify({
            "error": "Invalid email or password"
        }), 401



    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user":{
            "id" : user.id,
            "name" : user.name,
            "email" : user.email
,
        }
    }),200

    
    
  
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