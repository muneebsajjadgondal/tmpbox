import os
from datetime import datetime, timedelta

from flask import (
    Blueprint, current_app, render_template, request, redirect,
    url_for, send_from_directory, Response, abort, flash, jsonify
)

from app import db, limiter
from app.models import SharedFile
from app import storage
from app.utils import (
    generate_token, build_storage_pathname, is_blocked_extension,
    strip_image_metadata, sniff_content_type, delete_file_record, run_cleanup
)

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html", presets=current_app.config["EXPIRY_PRESETS"],
                            default_key=current_app.config["DEFAULT_EXPIRY_KEY"])


@bp.route("/upload", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_UPLOAD"])
def upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("main.index"))

    if is_blocked_extension(file.filename):
        flash("This file type isn't allowed.", "error")
        return redirect(url_for("main.index"))

    expiry_key = request.form.get("expiry", current_app.config["DEFAULT_EXPIRY_KEY"])
    minutes = current_app.config["EXPIRY_PRESETS"].get(
        expiry_key, current_app.config["EXPIRY_PRESETS"][current_app.config["DEFAULT_EXPIRY_KEY"]]
    )
    one_time = request.form.get("one_time") == "on"

    token = generate_token()
    data = file.read()
    content_type = sniff_content_type(file.filename)
    data = strip_image_metadata(data, content_type)

    pathname = build_storage_pathname(token, file.filename)
    storage_ref = storage.save_file(pathname, data, content_type)

    record = SharedFile(
        token=token,
        original_filename=file.filename,
        storage_ref=storage_ref,
        content_type=content_type,
        size_bytes=len(data),
        expires_at=datetime.utcnow() + timedelta(minutes=minutes),
        one_time=one_time,
    )
    db.session.add(record)
    db.session.commit()

    return redirect(url_for("main.file_info", token=record.token))


@bp.route("/f/<token>", methods=["GET"])
def file_info(token):
    record = SharedFile.query.filter_by(token=token).first()
    if record is None or record.is_gone():
        abort(404)
    share_url = url_for("main.file_info", token=token, _external=True)
    return render_template("download.html", record=record, share_url=share_url)


@bp.route("/f/<token>/download", methods=["GET"])
def download(token):
    record = SharedFile.query.filter_by(token=token).first()
    if record is None or record.is_gone():
        abort(404)

    url = storage.file_url(record.storage_ref)
    if url:
        # Vercel Blob: redirect the browser straight to the blob's URL
        # (?download=1 forces Content-Disposition: attachment).
        response = redirect(f"{url}?download=1")
    else:
        # Local dev: stream straight from disk.
        directory = os.path.join(current_app.config["STORAGE_DIR"],
                                  os.path.dirname(record.storage_ref))
        filename = os.path.basename(record.storage_ref)
        response = send_from_directory(
            directory, filename, as_attachment=True,
            download_name=record.original_filename,
        )

    if record.one_time:
        record.downloaded = True
        db.session.commit()
        delete_file_record(record)

    return response


@bp.route("/api/cleanup", methods=["GET", "POST"])
def cleanup_endpoint():
    """Called by Vercel Cron on a schedule (see vercel.json). Protected by
    CRON_SECRET so it can't be triggered by randoms hitting the URL."""
    secret = current_app.config.get("CRON_SECRET")
    if secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            abort(401)
    removed = run_cleanup()
    return jsonify({"removed": removed})


@bp.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@bp.errorhandler(413)
def too_large(e):
    flash("File is too large.", "error")
    return redirect(url_for("main.index"))
