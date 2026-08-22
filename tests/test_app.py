import pytest
from fastapi.testclient import TestClient

from journal import app as app_module
from journal import config


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch):
    """Each test gets its own data dir and a fresh db connection -- app._conn
    is a lazily-created module-level singleton, so it must be reset or tests
    would share one sqlite db (and one on-disk location) across the file."""
    monkeypatch.setenv("JOURNAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app_module._conn = None
    yield
    app_module._conn = None


@pytest.fixture
def client():
    return TestClient(app_module.app)


# ---- cross-site write protection ----

def test_same_origin_post_succeeds(client):
    resp = client.post(
        "/api/entries",
        data={"source": "typed", "text": "hello journal"},
        headers={"Origin": "http://testserver"},
    )
    assert resp.status_code == 200


def test_no_origin_post_succeeds(client):
    """Non-browser tools (curl, scripts) send no Origin header at all and
    aren't a cross-site-forgery risk -- only a browser attaches Origin."""
    resp = client.post("/api/entries", data={"source": "typed", "text": "hello journal"})
    assert resp.status_code == 200


def test_cross_site_post_is_rejected(client):
    resp = client.post(
        "/api/entries",
        data={"source": "typed", "text": "hello journal"},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403


def test_cross_site_get_is_not_blocked(client):
    resp = client.get("/api/entries", headers={"Origin": "https://evil.example"})
    assert resp.status_code == 200


# ---- audio extension allowlisting ----

def test_safe_audio_extension_keeps_known_extension():
    assert app_module._safe_audio_extension("memo.mp3") == ".mp3"


def test_safe_audio_extension_is_case_insensitive():
    assert app_module._safe_audio_extension("memo.MP3") == ".mp3"


def test_safe_audio_extension_normalizes_unknown_extension():
    assert app_module._safe_audio_extension("evil.html") == ".bin"


def test_safe_audio_extension_normalizes_missing_extension():
    assert app_module._safe_audio_extension("noext") == ".bin"


# ---- /audio/{filename} allowlist ----

def test_safe_audio_filename_regex_accepts_generated_format():
    assert app_module._SAFE_AUDIO_FILENAME.match("0123456789abcdef0123456789abcdef.mp3")


def test_safe_audio_filename_regex_rejects_traversal():
    assert not app_module._SAFE_AUDIO_FILENAME.match("../../etc/passwd")
    assert not app_module._SAFE_AUDIO_FILENAME.match("..\\windows\\system32")


def test_get_audio_rejects_unsafe_filename(client):
    resp = client.get("/audio/not-a-valid-name.mp3")
    assert resp.status_code == 400


# ---- upload size cap ----

def test_oversized_audio_upload_is_rejected(client, monkeypatch):
    monkeypatch.setattr(config, "get_max_audio_bytes", lambda: 10)
    resp = client.post(
        "/api/entries",
        data={"source": "upload"},
        files={"audio": ("memo.mp3", b"x" * 100, "audio/mpeg")},
    )
    assert resp.status_code == 413


# ---- host safety guard ----

def test_require_safe_host_allows_loopback():
    config.require_safe_host("127.0.0.1")
    config.require_safe_host("localhost")


def test_require_safe_host_blocks_non_loopback_without_opt_in(monkeypatch):
    monkeypatch.delenv("JOURNAL_ALLOW_REMOTE", raising=False)
    with pytest.raises(config.UnsafeHostError):
        config.require_safe_host("0.0.0.0")


def test_require_safe_host_allows_non_loopback_with_opt_in(monkeypatch):
    monkeypatch.setenv("JOURNAL_ALLOW_REMOTE", "1")
    config.require_safe_host("0.0.0.0")
