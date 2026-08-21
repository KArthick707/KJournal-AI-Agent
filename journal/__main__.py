"""Entrypoint: `python -m journal` starts the local web app."""

import uvicorn

from . import config
from .app import app


def main() -> None:
    uvicorn.run(app, host=config.get_host(), port=config.get_port())


if __name__ == "__main__":
    main()
