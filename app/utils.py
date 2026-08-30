import io
import os
import secrets
import mimetypes
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import SharedFile
from app import storage


def generate_token(n_bytes: int = 16) -> str:
    """Cryptographically random, URL-safe token used as the share ID.

    Never sequential/guessable - this token IS the access control.
    """
    return secrets.token_urlsafe(n_bytes)


def build_storage_pathname(token: str, original_filename: str) -> str:
    """token/safe-filename - the random token keeps it unguessable while the
    real filename shows up correctly in Content-Disposition on download."""
    safe_name = secure_filename(original_filename) or "file"
    return f"{token}/{safe_name}"


def is_blocked_extension(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in current_app.config["BLOCKED_EXTENSIONS"]


def strip_image_metadata(data: bytes, content_type: str) -> bytes:
    """Returns image bytes with EXIF/metadata stripped, if Pillow can open
    them. Returns the original bytes unchanged for non-images or on failure."""
    if not content_type or not content_type.startswith("image/"):
        return data
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(list(img.getdata()))
        out = io.BytesIO()
        clean_img.save(out, format=fmt)
        return out.getvalue()
    except Exception:
        return data


def sniff_content_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def delete_file_record(record: SharedFile) -> None:
    """Removes both the DB row and the underlying stored file."""
    storage.delete_file(record.storage_ref)
    db.session.delete(record)
    db.session.commit()


def run_cleanup() -> int:
    """Deletes all expired or spent one-time-download files. Returns count removed."""
    now = datetime.utcnow()
    expired = SharedFile.query.filter(SharedFile.expires_at <= now).all()
    spent = SharedFile.query.filter(
        SharedFile.one_time.is_(True), SharedFile.downloaded.is_(True)
    ).all()

    removed = 0
    for record in {r.id: r for r in (expired + spent)}.values():
        delete_file_record(record)
        removed += 1
    return removed
