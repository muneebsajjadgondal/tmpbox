"""
Storage abstraction: uses Vercel Blob when BLOB_READ_WRITE_TOKEN is set
(i.e. when deployed on Vercel), falls back to local disk otherwise
(local dev on your machine). Callers never touch the filesystem or the
Blob SDK directly - they go through save_file/read_file/delete_file/file_url.
"""
import os
from flask import current_app

USE_BLOB = bool(os.environ.get("BLOB_READ_WRITE_TOKEN"))

if USE_BLOB:
    import vercel_blob


def save_file(pathname: str, data: bytes, content_type: str = None) -> str:
    """Saves file bytes under `pathname`. Returns a reference (blob URL or
    local pathname) that read_file/delete_file/file_url can use later."""
    if USE_BLOB:
        options = {"addRandomSuffix": "false"}
        resp = vercel_blob.put(pathname, data, options)
        return resp["url"]
    else:
        full_path = os.path.join(current_app.config["STORAGE_DIR"], pathname)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        return pathname


def read_file(ref: str) -> bytes:
    if USE_BLOB:
        return vercel_blob.get(ref)
    else:
        full_path = os.path.join(current_app.config["STORAGE_DIR"], ref)
        with open(full_path, "rb") as f:
            return f.read()


def delete_file(ref: str) -> None:
    if USE_BLOB:
        try:
            vercel_blob.delete([ref])
        except Exception:
            current_app.logger.warning("Could not delete blob %s", ref)
    else:
        full_path = os.path.join(current_app.config["STORAGE_DIR"], ref)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
        except OSError:
            current_app.logger.warning("Could not remove file %s from disk", ref)


def file_url(ref: str) -> str:
    """Public/download URL for the file. Blob refs already are URLs;
    local dev returns None (caller streams from disk directly)."""
    return ref if USE_BLOB else None
