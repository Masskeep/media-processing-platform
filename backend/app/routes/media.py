import math

from flask import Blueprint, jsonify, request,current_app, session
from app.extensions import db
from app.models.video import Video
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models.uploadsession import UploadSession
import uuid
from app.services.s3_services import (
generate_upload_url,
initiate_multipart_upload,
abort_multipart_upload,
generate_part_upload_url,
complete_multipart_upload,
)
import os


ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}

media_bp = Blueprint("media", __name__)

@media_bp.route("/api/media/presigned-url", methods=["POST"])
@jwt_required()
def create_presigned_url():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request must be JSON"}), 400

    filename = data.get("filename")
    content_type = data.get("content_type")

    if not filename or not content_type:
        return jsonify({"error": "Missing required fields: filename and content_type"}), 400

    allowed_content_types = {
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska"
    }

    if content_type not in allowed_content_types:
        return jsonify({"error": f"Content type '{content_type}' is not allowed"}), 400

    object_key = f"uploads/{user_id}/{uuid.uuid4().hex}"

    try:
        upload_url = generate_upload_url( object_key = object_key,
                                         content_type = content_type)

    except RuntimeError:
        current_app.logger.exception("S3 configuration error")

        return jsonify({"error": "S3 configuration error"}), 500

    except Exception:
        current_app.logger.exception("Failed to generate presigned URL")

        return jsonify({"error": "Failed to generate presigned URL"}), 500

    return jsonify({
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": 300
    }),200



@media_bp.route("/api/media/multipart-upload/start", methods=["POST"])
@jwt_required()
def start_multipart_upload():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request must be JSON"}), 400

    filename = data.get("filename")
    content_type = data.get("content_type")
    file_size = data.get("file_size")

    if (
        not isinstance(filename, str)
        or not filename.strip()
        or not isinstance(content_type, str)
        or not content_type.strip()
        or file_size is None
    ):
        return jsonify({"error": "Missing required fields: filename, content_type, and file_size"}), 400

    allowed_content_types = {
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska"
    }

    if not isinstance(content_type, str) or content_type not in allowed_content_types:
        return jsonify({"error": f"Content type '{content_type}' is not allowed"}), 400

    if(
        isinstance(file_size, bool) or
        not isinstance(file_size, (int)) or
        file_size <= 0
    ):
        return jsonify({"error": "file_size must be a positive integer"}), 400

    max_file_size = 500*1024*1024  # 500MB
    if file_size > max_file_size:
        return jsonify({"error": f"File size exceeds the maximum limit of {max_file_size} bytes"}), 400

    chunk_size = 8*1024*1024  # 8MB
    total_chunks = math.ceil(file_size / chunk_size)

    object_key = f"uploads/{user_id}/{uuid.uuid4().hex}"
    s3_upload_id = None

    try:
        s3_upload_id = initiate_multipart_upload(
            object_key = object_key,
            content_type = content_type
        )

        session = UploadSession(
            user_id = user_id,
            original_filename = filename,
            file_size = file_size,
            chunk_size = chunk_size,
            total_chunks = total_chunks,
            s3_object_key = object_key,
            s3_upload_id = s3_upload_id,
            status = "initiated"
        )
        db.session.add(session)
        db.session.commit()

    except Exception:
        db.session.rollback()

        if s3_upload_id:
            try:
                abort_multipart_upload(
                    object_key = object_key,
                    upload_id = s3_upload_id
                )
            except Exception:
                current_app.logger.exception("Failed to abort multipart upload after DB rollback")

        current_app.logger.exception("Failed to initiate multipart upload")

        return jsonify({"error": "Failed to initiate multipart upload"}), 500
    return jsonify({
        "message": "Multipart upload initiated successfully",
        "upload_id": session.id,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "s3_object_key": object_key,
        "s3_upload_id": s3_upload_id    
    }),201

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the uploads directory exists


@media_bp.route("/api/media/multipart-upload/<string:session_id>/part/<int:part_number>/url", methods = ["POST"],)
@jwt_required()
def get_multipart_part_url(session_id, part_number):
    user_id = get_jwt_identity()

    session = db.session.get(UploadSession, session_id)

    if session is None:
        return jsonify({"error": "Upload session not found"}), 404

    if str(session.user_id) != str(user_id):
        return jsonify({"error": "Unauthorized access to this upload session"}), 403

    if not session.s3_object_key or not session.s3_upload_id:
        return jsonify({"error": "S3 object key or upload ID is missing for this session"}), 400

    if session.status not in ["initiated", "uploading"]:
        return jsonify({"error": f"Cannot get part URL for session in '{session.status}' status"}), 409

    if part_number <1 or part_number > session.total_chunks:
        return jsonify({"error": f"part_number must be between 1 and {session.total_chunks}"}), 400

    try:
        presigned_url = generate_part_upload_url(
            object_key = session.s3_object_key,
            upload_id = session.s3_upload_id,
            part_number = part_number
        )

    except Exception:
        current_app.logger.exception("Failed to generate presigned URL for part upload")
        return jsonify({"error": "Failed to generate presigned URL for part upload"}), 500
    
    return jsonify({
        "message": "Presigned URL generated successfully",
        "presigned_url": presigned_url,
        "expires_in": 300
    }), 200


@media_bp.route("/api/media/multipart-upload/<string:session_id>/complete", methods=["POST"])
@jwt_required()

def complete_multipart_upload_route(session_id):
    user_id = get_jwt_identity()

    session = db.session.get(UploadSession, session_id)

    if session is None:
        return jsonify({"error": "Upload session not found"}), 404

    if str(session.user_id) != str(user_id):
        return jsonify({"error": "You are not authorized to complete this upload session"}), 403

    if not session.s3_object_key or not session.s3_upload_id:
        return jsonify({"error": "S3 object key or upload ID is missing for this session"}), 400

    if session.status not in ["initiated", "uploading"]:
        return jsonify({"error": f"Cannot complete upload for session in '{session.status}' status"}), 409

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request must be JSON"}), 400

    parts = data.get("parts")

    if not isinstance(parts, list) or not parts:
        return jsonify({"error": "Missing or invalid 'parts' field. It must be a non-empty list of parts."}), 400

    normalized_parts = []
    seen_part_numbers = set()

    for part in parts:
        if not isinstance(part, dict):
            return jsonify({"error": "Each part must be an object with 'part_number' and 'ETag' keys."}), 400

        part_number = part.get("part_number")
        etag = part.get("eTag")

        if(
            isinstance(part_number, bool) or
            not isinstance(part_number, int) or
            part_number < 1 or
            part_number > session.total_chunks
        ):
            return jsonify({"error": f"Invalid 'part_number': {part_number}. It must be an integer between 1 and {session.total_chunks}."}), 400

        if part_number in seen_part_numbers:
            return jsonify({"error": f"Duplicate 'part_number': {part_number}. Each part number must be unique."}), 400

        if not isinstance(etag, str) or not etag.strip():
            return jsonify({"error": f"Invalid 'eTag' for part_number {part_number}. It must be a non-empty string."}), 400

        seen_part_numbers.add(part_number)

        normalized_parts.append({
            "PartNumber": part_number,
            "ETag": etag.strip()
        })

    # in this range function we are using 1 to total_chunks + 1 because range is exclusive of the upper bound, so we need to go one past the total_chunks to include it in the expected part numbers.
    expected_part_numbers = list(range(1, session.total_chunks + 1))

    normalized_parts.sort(key=lambda x: x["PartNumber"])

    received_part_numbers = [part["PartNumber"] for part in normalized_parts]

    if received_part_numbers != expected_part_numbers:
        return jsonify({"error": f"Missing or extra parts. Expected part numbers: {expected_part_numbers}. Received: {received_part_numbers}."}), 400

    try:
        s3_response = complete_multipart_upload(
            object_key = session.s3_object_key,
            upload_id = session.s3_upload_id,
            parts = normalized_parts
        )
    except Exception:
        current_app.logger.exception("Failed to complete multipart upload")

        return jsonify({"error": "Failed to complete multipart upload"}), 500

    try:
        video = Video(
            user_id = session.user_id,
            original_filename = session.original_filename,
            stored_filename = f"{uuid.uuid4().hex}{os.path.splitext(session.original_filename)[1].lower()}",
            file_size = session.file_size,
            s3_object_key = session.s3_object_key,
            status = "uploaded"
        )

        session.status = "completed"

        db.session.add(video)
        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to save video record or update session status after completing multipart upload")
        return jsonify({"error": "File uploaded to S3, but failed to save video record or update session status"}), 500


    return jsonify({
        "message": "Multipart upload completed successfully",
        "video_id": video.id,
        "filename": video.stored_filename,
        "s3_object_key": video.s3_object_key,
        "s3_location": s3_response.get("Location"),
    }),200
                                             


    
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
        user_id = session.user_id,
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

