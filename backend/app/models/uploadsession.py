from datetime import datetime, timezone
import uuid

from app.extensions import db

class UploadSession(db.Model):
    __tablename__ = "upload_sessions"

    id = db.Column(
        db.String(36),
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    original_filename = db.Column(
        db.String(255),
        nullable=False
    )

    file_size = db.Column(

        db.BigInteger,
        nullable=False
    )

    chunk_size = db.Column(
        db.Integer,
        nullable=False
    )

    total_chunks = db.Column(
        db.Integer,
        nullable=False
    )
    status = db.Column(
        db.DateTime(timezone=True),
        default = lambda: datetime.now(timezone.utc)   ,
        nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default = lambda: datetime.now(timezone.utc)   ,
        nullable=False
    )