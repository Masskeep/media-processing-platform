import math

from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models.video import Video
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models.uploadsession import UploadSession
import uuid

import os


ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}

media_bp = Blueprint("media", __name__)

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the uploads directory exists

@media_bp.route("/api/media/upload/start", methods=["POST"])
@jwt_required()

def start_upload():
    user_id = get_jwt_identity()

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request must be JSON"
        }), 400

    if "filename" not in data or "file_size" not in data:
        return jsonify({
            "error": "Missing required fields: filename and file_size"
        }), 400

    filename = data["filename"]
    file_size = data["file_size"]

    if not filename :
        return jsonify({
            "error": "Filename cannot be empty"
        }), 400

    if not isinstance(file_size, int) or file_size <= 0:
        return jsonify({
            "error": "File size must be a positive integer"
        }), 400

    chunk_size = 5 * 1024 * 1024  # 5MB

    total_chunks = math.ceil(file_size / chunk_size)

    upload_id = str(uuid.uuid4())

    upload_session = UploadSession(
        id = upload_id,
        user_id = user_id,
        original_filename = secure_filename(filename),
        file_size = file_size,
        chunk_size = chunk_size,
        total_chunks = total_chunks,
        status = "uploading"
    )

    db.session.add(upload_session)
    db.session.commit()

    return jsonify({
        "message" : "Upload session created",
        "upload_id" : upload_id,
        "chunk_size" : chunk_size,
        "total_chunks" : total_chunks
    }),201

#chunk section
@media_bp.route("/api/media/upload/chunk", methods=["POST"])
@jwt_required()
def upload_chunk():
    upload_id = request.form.get("upload_id")
    chunk_index = request.form.get("chunk_index")
    chunk = request.files.get("chunk")

    if not upload_id:
        return jsonify({
            "error": "Missing upload_id"
        }),400
    if chunk_index is None:
        return jsonify({
            "error": "Missing chunk_index"
        }),400
    if not chunk:
        return jsonify({
            "error": "Missing chunk file"
        }),400

    upload_session = UploadSession.query.filter_by(id = upload_id,
                                                   user_id = get_jwt_identity()
                                                   ).first()

    if not upload_session:
        return jsonify({
            "error": "Upload session not found"
        }),404

    try:
        chunk_index = int(chunk_index)
    except ValueError:
        return jsonify({
            "error": "chunk_index must be an integer"
        }),400

    if chunk_index < 0 or chunk_index >= upload_session.total_chunks:
        return jsonify({
            "error": f"chunk_index must be between 0 and {upload_session.total_chunks - 1}"
        }),400

    chunk_size = os.fstat(chunk.stream.fileno()).st_size

    if chunk_index < upload_session.total_chunks -1:
        if chunk_size != upload_session.chunk_size:
            return jsonify({
                "error": f"Chunk size must be {upload_session.chunk_size} bytes for all chunks except the last one"
            }),400
    else: 
        if chunk_size > upload_session.chunk_size:
            return jsonify({
                "error": f"Last chunk size must be less than or equal to {upload_session.chunk_size} bytes"
            }),400

    chunk_directory = os.path.join(UPLOAD_FOLDER, "chunks", upload_id)
    os.makedirs(chunk_directory, exist_ok=True)

    chunk.save(os.path.join(chunk_directory, f"chunk_{chunk_index}"))
    return jsonify({
        "message": "Chunk uploaded successfully"
    }),200
@media_bp.route("/api/media/upload/complete", methods=["POST"])
@jwt_required()
def complete_upload():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request must be JSON"
        }), 400
    upload_id = data.get("upload_id")
    if not upload_id:
        return jsonify({
            "error": "Missing upload_id"
        }),400
    upload_session = UploadSession.query.filter_by(id = upload_id,
                                                   user_id = user_id
                                                   ).first()

    if not upload_session:
        return jsonify({
            "error": "Upload session not found"
        }),404

    chunk_directory = os.path.join(UPLOAD_FOLDER, "chunks", upload_id)
    for chunk_index in range(upload_session.total_chunks):
        chunk_path = os.path.join(chunk_directory, f"chunk_{chunk_index}")
        if not os.path.exists(chunk_path):
            return jsonify({
                "error": f"Missing chunk {chunk_index}"
            }),400


    extension = os.path.splitext(upload_session.original_filename)[1].lower()
    final_filename = f"{uuid.uuid4().hex}{extension}"
    final_path = os.path.join(UPLOAD_FOLDER, final_filename)

    with open(final_path, "wb") as final_file:
        for chunk_index in range(upload_session.total_chunks):
            chunk_path = os.path.join(chunk_directory, f"chunk_{chunk_index}")

            with open(chunk_path, "rb") as chunk_file:
                final_file.write(chunk_file.read())

    video = Video(
        user_id = user_id,
        original_filename = upload_session.original_filename,
        stored_filename = final_filename,
        file_size = upload_session.file_size,
        status = "uploaded"
    )

    db.session.add(video)

    upload_session.status = "completed"

    db.session.commit()

    return jsonify({
        "message": "Upload completed successfully",
        "video_id": video.id,
        "filename": final_filename

    }),200



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