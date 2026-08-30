from datetime import datetime
from app import db


class SharedFile(db.Model):
    __tablename__ = "shared_files"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Original filename is kept for the download's Content-Disposition header.
    # storage_ref is the on-disk path (local dev) or the Vercel Blob URL (prod) -
    # either way it's opaque to callers, who go through app/storage.py.
    original_filename = db.Column(db.String(255), nullable=False)
    storage_ref = db.Column(db.String(512), nullable=False)

    content_type = db.Column(db.String(128), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    one_time = db.Column(db.Boolean, default=False, nullable=False)
    downloaded = db.Column(db.Boolean, default=False, nullable=False)

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def is_gone(self) -> bool:
        """True if the file should no longer be servable for any reason."""
        return self.is_expired() or (self.one_time and self.downloaded)

    def to_dict(self):
        return {
            "token": self.token,
            "filename": self.original_filename,
            "size_bytes": self.size_bytes,
            "uploaded_at": self.uploaded_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "one_time": self.one_time,
        }
