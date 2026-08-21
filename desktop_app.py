"""Windows desktop entry point: runs the same FastAPI app as `python -m
journal`, but inside a native pywebview window (WebView2 on Windows) instead
of a browser tab, and PyInstaller-friendly (see journalagent.spec).

Must set JOURNAL_DATA_DIR before importing journal.app -- otherwise the
SQLite db and saved audio would default to a relative ./data folder, which
inside a PyInstaller onefile build lives in the temp extraction dir and gets
wiped after the app closes, silently losing every entry.
"""

import os
import sys
import time
import threading
import urllib.request


def _app_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "JournalAIAgent")
    return os.path.join(os.path.expanduser("~"), ".journal-ai-agent")


os.environ.setdefault("JOURNAL_DATA_DIR", _app_data_dir())

import webview  # noqa: E402 -- after the env var is set

from journal import config  # noqa: E402
from journal.app import app  # noqa: E402


def _run_server(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="warning")


def _wait_until_ready(url: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return
        except Exception as exc:  # noqa: BLE001 -- keep retrying until timeout
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"journal server did not start within {timeout}s: {last_error}")


def main() -> None:
    host = config.get_host()
    port = config.get_port()
    url = f"http://{host}:{port}"

    server_thread = threading.Thread(target=_run_server, args=(host, port), daemon=True)
    server_thread.start()
    _wait_until_ready(url)

    webview.create_window("Journal", url, width=960, height=820, min_size=(520, 560))
    webview.start(gui="edgechromium")


if __name__ == "__main__":
    main()
