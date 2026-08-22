"""Entrypoint: `python -m journal` starts the local web app."""

import sys

import uvicorn

from . import config
from .app import app


def main() -> None:
    host = config.get_host()
    try:
        config.require_safe_host(host)
    except config.UnsafeHostError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    uvicorn.run(app, host=host, port=config.get_port())


if __name__ == "__main__":
    main()
