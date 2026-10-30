from datetime import datetime, timezone
import uuid

from app.extensions import db


class UploadSession(db.Model):
    __tablename__ = "upload_sessions"

    # Unique ID for our application's upload session
    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # User who owns this upload
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Original name of the video
    original_filename = db.Column(
        db.String(255),
        nullable=False
    )

    # Expected file size in bytes
    file_size = db.Column(
        db.BigInteger,
        nullable=False
    )

    # Size of each uploaded part in bytes
    chunk_size = db.Column(
        db.Integer,
        nullable=False
    )

    # Number of parts expected
    total_chunks = db.Column(
        db.Integer,
        nullable=False
    )

    # S3 key where the completed video will be stored
    s3_object_key = db.Column(
        db.String(1024),
        nullable=True,
        unique=True
    )

    # S3 identifier for an active multipart upload
    s3_upload_id = db.Column(
        db.String(1024),
        nullable=True
    )

    # Current state of the upload
    status = db.Column(
        db.String(30),
        nullable=False,
        default="initiated"
    )

    # When the upload session was created
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )