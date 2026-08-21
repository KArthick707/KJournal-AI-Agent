"""Environment configuration. Bare os.environ, no settings framework."""

import os

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_DATA_DIR = "data"


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
