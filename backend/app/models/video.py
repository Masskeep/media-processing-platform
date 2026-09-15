from datetime import datetime, timezone
from app.extensions import db

class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)


    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    original_filename = db.Column(
        db.String(255),
        nullable=False
    )
    stored_filename = db.Column(
        db.String(255),
        nullable=False

    )

    file_size = db.Column(
        db.BigInteger,
        nullable=False
    )
    status = db.Column(
        db.String(50),
        nullable=False,
        default = "uploaded"
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default= lambda: datetime.now(timezone.utc)
    )