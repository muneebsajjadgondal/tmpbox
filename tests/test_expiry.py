import io
from datetime import datetime, timedelta

from app import db
from app.models import SharedFile
from app.utils import run_cleanup


def upload_file(client, filename="hello.txt", content=b"hello world", **form_extra):
    data = {"file": (io.BytesIO(content), filename)}
    data.update(form_extra)
    return client.post("/upload", data=data, content_type="multipart/form-data",
                        follow_redirects=True)


def test_expired_file_returns_404(client, app):
    upload_file(client)
    with app.app_context():
        record = SharedFile.query.first()
        record.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()
        token = record.token

    resp = client.get(f"/f/{token}")
    assert resp.status_code == 404


def test_cleanup_removes_expired_rows(client, app):
    upload_file(client)
    with app.app_context():
        record = SharedFile.query.first()
        record.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()

        removed = run_cleanup()
        assert removed == 1
        assert SharedFile.query.count() == 0


def test_one_time_download_deletes_after_first_fetch(client, app):
    upload_file(client, one_time="on")
    with app.app_context():
        record = SharedFile.query.first()
        token = record.token

    first = client.get(f"/f/{token}/download")
    assert first.status_code == 200

    second = client.get(f"/f/{token}/download")
    assert second.status_code == 404

    with app.app_context():
        assert SharedFile.query.count() == 0
