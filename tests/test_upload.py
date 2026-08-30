import io
from app.models import SharedFile


def upload_file(client, filename="hello.txt", content=b"hello world", **form_extra):
    data = {"file": (io.BytesIO(content), filename)}
    data.update(form_extra)
    return client.post("/upload", data=data, content_type="multipart/form-data",
                        follow_redirects=True)


def test_index_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"TMP Box" in resp.data


def test_upload_creates_record(client, app):
    resp = upload_file(client)
    assert resp.status_code == 200
    with app.app_context():
        assert SharedFile.query.count() == 1
        record = SharedFile.query.first()
        assert record.original_filename == "hello.txt"


def test_download_returns_file_content(client, app):
    upload_file(client, content=b"secret payload")
    with app.app_context():
        record = SharedFile.query.first()
        token = record.token
    resp = client.get(f"/f/{token}/download")
    assert resp.status_code == 200
    assert resp.data == b"secret payload"


def test_blocked_extension_rejected(client, app):
    upload_file(client, filename="virus.exe")
    with app.app_context():
        assert SharedFile.query.count() == 0


def test_unknown_token_returns_404(client):
    resp = client.get("/f/does-not-exist")
    assert resp.status_code == 404
