"""FastAPI app: capture typed or spoken journal entries, structure them with
Claude, store them in SQLite, and serve the browser UI that captures and
browses entries."""

import mimetypes
import os
import re
import uuid
from datetime import datetime

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import agent, config, db

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
VALID_SOURCES = ("typed", "voice", "upload")
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Extensions we trust enough to serve back with a browser-guessed Content-Type.
# Anything else still gets saved (raw bytes preserved), just under a neutral
# extension so it can never be served back as e.g. text/html.
SAFE_AUDIO_EXTENSIONS = {
    ".webm", ".mp3", ".wav", ".m4a", ".ogg", ".oga", ".mp4", ".aac", ".flac", ".3gp", ".amr", ".opus",
}
FALLBACK_AUDIO_EXTENSION = ".bin"

# Exactly matches the <uuid4-hex>.<ext> filenames _save_audio generates --
# an allowlist is a stricter, harder-to-bypass guard than blocking specific
# "bad" characters (e.g. "/", "..") one at a time.
_SAFE_AUDIO_FILENAME = re.compile(r"^[0-9a-f]{32}\.[A-Za-z0-9]{1,8}$")

app = FastAPI(title="Journal AI Agent")


@app.middleware("http")
async def _reject_cross_site_writes(request: Request, call_next):
    """This app has no login, so the only thing standing between "a website
    you have open" and "a forged write to your journal" is this check. A
    browser attaches Origin on state-changing requests whether or not
    they're cross-site, and unlike the request body, it can't be forged by
    the page making the request -- so reject only when it's present AND
    doesn't match this same request's own host. Non-browser tools (curl,
    tests) send no Origin at all and are unaffected."""
    if request.method in UNSAFE_METHODS:
        origin = request.headers.get("origin")
        self_origin = f"{request.url.scheme}://{request.url.netloc}"
        if origin and origin != self_origin:
            return JSONResponse({"detail": "cross-site requests are not allowed"}, status_code=403)
    return await call_next(request)


_conn = None


def get_conn():
    """Lazy singleton connection, initialized on first use so importing this
    module (e.g. for tests) doesn't touch disk."""
    global _conn
    if _conn is None:
        os.makedirs(_audio_dir(), exist_ok=True)
        db_path = os.path.join(config.get_data_dir(), "journal.db")
        _conn = db.connect(db_path)
        db.init_db(_conn)
    return _conn


def _audio_dir() -> str:
    path = os.path.join(config.get_data_dir(), "audio")
    os.makedirs(path, exist_ok=True)
    return path


def _fallback_title(raw_text: str) -> str:
    first_line = raw_text.strip().splitlines()[0] if raw_text.strip() else ""
    if first_line:
        words = first_line.split()
        title = " ".join(words[:8])
        return title + ("…" if len(words) > 8 else "")
    return f"Journal entry — {datetime.now().strftime('%b %d, %Y')}"


def _safe_audio_extension(filename: str) -> str:
    """Never trust the client-supplied extension enough to serve it back
    as-is: an unrecognized one (e.g. ".html") could get guessed into a
    dangerous Content-Type later, so it's normalized to a neutral extension
    that mimetypes.guess_type won't map to anything renderable."""
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in SAFE_AUDIO_EXTENSIONS else FALLBACK_AUDIO_EXTENSION


async def _save_audio(audio: UploadFile) -> str:
    ext = _safe_audio_extension(audio.filename or "")
    name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(_audio_dir(), name)

    max_bytes = config.get_max_audio_bytes()
    contents = await audio.read()
    if len(contents) > max_bytes:
        raise HTTPException(413, f"audio file too large (max {max_bytes} bytes)")

    with open(dest, "wb") as fh:
        fh.write(contents)
    return name


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/audio/{filename}")
def get_audio(filename: str):
    if not _SAFE_AUDIO_FILENAME.match(filename):
        raise HTTPException(400, "invalid filename")
    path = os.path.join(_audio_dir(), filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "not found")
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@app.post("/api/entries")
async def create_entry(
    text: str = Form(""),
    source: str = Form("typed"),
    audio: UploadFile | None = File(None),
):
    if source not in VALID_SOURCES:
        raise HTTPException(400, f"source must be one of {VALID_SOURCES}")

    audio_path = None
    if audio is not None and audio.filename:
        audio_path = await _save_audio(audio)

    raw_text = text.strip()
    tags: list[str] = []
    structured = False

    if raw_text:
        try:
            draft = agent.structure_entry(raw_text)
            title, body, summary, mood = draft.title, draft.body, draft.summary, draft.mood
            tags = list(draft.tags)
            structured = True
        except agent.AgentNotConfigured:
            title = _fallback_title(raw_text)
            body = raw_text
            summary = mood = None
    elif audio_path:
        title = "Untitled voice memo"
        body = "No transcript was captured for this entry — play the audio to hear it."
        summary = mood = None
    else:
        raise HTTPException(400, "entry must include text or an audio recording")

    return db.create_entry(
        get_conn(),
        source=source,
        raw_text=raw_text,
        title=title,
        body=body,
        summary=summary,
        mood=mood,
        tags=tags,
        audio_path=audio_path,
        structured=structured,
    )


@app.get("/api/entries")
def api_list_entries(q: str = "", limit: int = 50, offset: int = 0):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return db.list_entries(get_conn(), query=q or None, limit=limit, offset=offset)


@app.get("/api/entries/{entry_id}")
def api_get_entry(entry_id: int):
    entry = db.get_entry(get_conn(), entry_id)
    if entry is None:
        raise HTTPException(404, "entry not found")
    return entry


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
