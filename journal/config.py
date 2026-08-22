"""Environment configuration. Bare os.environ, no settings framework."""

import os

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_DATA_DIR = "data"
DEFAULT_MAX_AUDIO_BYTES = 100_000_000  # 100MB -- generous for a voice journal entry

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def get_model() -> str:
    return os.environ.get("JOURNAL_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_host() -> str:
    return os.environ.get("JOURNAL_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST


def get_port() -> int:
    try:
        return int(os.environ.get("JOURNAL_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


def get_data_dir() -> str:
    return os.environ.get("JOURNAL_DATA_DIR", DEFAULT_DATA_DIR).strip() or DEFAULT_DATA_DIR


def has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def get_max_audio_bytes() -> int:
    try:
        return max(1, int(os.environ.get("JOURNAL_MAX_AUDIO_BYTES", DEFAULT_MAX_AUDIO_BYTES)))
    except ValueError:
        return DEFAULT_MAX_AUDIO_BYTES


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in LOOPBACK_HOSTS


def get_allow_remote() -> bool:
    """This app has no login or access control -- binding it to a
    non-loopback host means anything on the network can read and write the
    journal. Require an explicit opt-in rather than let JOURNAL_HOST alone
    silently remove that protection."""
    return os.environ.get("JOURNAL_ALLOW_REMOTE", "").strip().lower() in ("1", "true", "yes")


class UnsafeHostError(RuntimeError):
    """Raised when JOURNAL_HOST is non-loopback without an explicit opt-in."""


def require_safe_host(host: str) -> None:
    if not is_loopback_host(host) and not get_allow_remote():
        raise UnsafeHostError(
            f"refusing to bind to non-loopback host '{host}' -- this app has no login or "
            "access control, so anything on your network could read, write, and hear your "
            "journal. Set JOURNAL_ALLOW_REMOTE=1 if you understand the risk and want this "
            "anyway."
        )
