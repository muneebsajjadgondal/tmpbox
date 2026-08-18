# TMP Box — Anonymous File Sharing Platform

Upload a file, get a link, it self-destructs. No accounts, no tracking.

## Features
- No authentication — access is controlled purely by a cryptographically random
  share token (`secrets.token_urlsafe`), never a guessable/sequential ID.
- Configurable auto-expiration (1 hour / 1 day / 7 days), enforced both on
  access (expired links 404 immediately) and by a background cleanup job.
- Optional one-time-download: file is deleted the moment it's first fetched.
- Blocked-extension list + MIME sniffing on upload.
- EXIF/metadata stripped from uploaded images automatically.
- Per-IP rate limiting on uploads (Flask-Limiter).
- 8 passing pytest tests covering upload, download, expiry, and one-time links.

## Stack
Flask, Flask-SQLAlchemy (SQLite by default), APScheduler (cleanup job),
Flask-Limiter, Pillow (EXIF stripping).

## Setup (Windows PowerShell)

```powershell
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Then open http://127.0.0.1:5000

## Running tests

```powershell
pytest tests/ -v
```

## Project structure

```
tmpbox/
  app/
    __init__.py      # app factory
    models.py         # SharedFile model
    routes.py         # upload / download / info routes
    utils.py           # token generation, EXIF stripping, cleanup
    scheduler.py        # APScheduler background cleanup job
    templates/
    static/
  config.py
  run.py
  tests/
```

## Design notes / things worth knowing

- **File storage**: files are saved to disk under `storage/` with a random
  on-disk name (`stored_name`), decoupled from the original filename. This
  avoids path traversal and collisions. Swapping to S3-compatible storage
  later just means changing `utils.py`'s save/delete/serve calls — the token
  and DB model don't need to change.
- **One-time downloads**: the file is deleted right after
  `send_from_directory` builds the response. On Linux this is safe — an
  open file descriptor stays valid even after `os.remove()` unlinks the
  directory entry, so the download still completes. This is standard
  behavior on the Linux hosts you'd deploy to (Render/Railway/Fly.io); it's
  called out here because it would need a different approach on Windows.
- **Cleanup job**: runs every `CLEANUP_INTERVAL_MINUTES` (default 15) via
  APScheduler, in addition to the immediate 404 check on access. This is a
  simple in-process scheduler; if you ever run multiple worker processes in
  production, move this to a proper task queue (Celery/RQ) so the job
  doesn't run once per worker.

## Deploying to Vercel

Vercel is serverless, so this needs three pieces beyond local dev:

1. **Postgres** — Project → Storage → Create Database → Postgres (Neon-backed).
   Vercel injects `POSTGRES_URL` automatically once connected.
2. **Blob storage** — Project → Storage → Create Database → Blob. Vercel
   injects `BLOB_READ_WRITE_TOKEN` automatically once connected.
3. **Cron cleanup** — already configured in `vercel.json`, hits
   `/api/cleanup` every 15 minutes. Set a `CRON_SECRET` env var in the
   Vercel project settings (any random string) — the cleanup route checks
   it so randoms can't trigger it by hitting the URL directly.

Locally, none of this is needed — leave those env vars unset and the app
automatically falls back to SQLite + local disk + the in-process
APScheduler job, same as before.

## Ideas for later phases

- Swap local disk for S3-compatible storage (MinIO locally, S3/R2 in prod).
- Client-side encryption before upload, so the server never sees plaintext.
- Password-protected links (hash a passphrase, require it before download).
- Upload progress bar + resumable uploads for large files.
- Admin-free abuse reporting (a link that flags a file for early deletion).
