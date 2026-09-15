from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models.video import Video
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import uuid
import os


ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}

media_bp = Blueprint("media", __name__)

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the uploads directory exists

@media_bp.route("/api/media/upload", methods=["POST"])
@jwt_required()
def upload_media():
    user_id = get_jwt_identity()
    file = request.files.get("file")

    if not file:
        return jsonify({
            "error": "No File provided"
        }), 400

    

    # extension check
    if "." not in file.filename:
        return jsonify({
            "error": "File must have extension"
        }), 400

    extension = file.filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"File extension not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # secure the filename
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    video = Video(
        user_id = user_id,
        original_filename = original_filename,
        stored_filename = filename,
        file_size = os.path.getsize(os.path.join(UPLOAD_FOLDER, filename)),
        status = "uploaded"
    )
    db.session.add(video)
    db.session.commit()
    return jsonify({
        "message": "File uploaded successfully",
        "filename": f"{filename}"
    }),200