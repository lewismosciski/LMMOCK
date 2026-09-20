from __future__ import annotations

import argparse
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from . import __version__
from .app import create_app
from .config import data_dir, host, no_browser, port


def _open_browser(address: str) -> None:
    for _ in range(40):
        try:
            with urllib.request.urlopen(address + "/healthz", timeout=0.25):
                webbrowser.open_new_tab(address)
                return
        except Exception:
            time.sleep(0.1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lmmock", description="Mock LLM APIs locally.")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="start the mock server")
    for target in (parser, serve):
        target.add_argument("--host", default=host())
        target.add_argument("--port", type=int, default=port())
        target.add_argument("--data-dir", default=str(data_dir()))
        target.add_argument("--no-open-browser", action="store_true")
    sub.add_parser("version")
    sub.add_parser("data-dir")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "data-dir":
        print(data_dir())
        return 0
    address = f"http://127.0.0.1:{args.port}"
    if not args.no_open_browser and not no_browser():
        threading.Thread(target=_open_browser, args=(address,), daemon=True).start()
    print(f"LMMock listening at {address}")
    print(f"OpenAI base URL: {address}/v1")
    print(f"Anthropic base URL: {address}")
    uvicorn.run(create_app(Path(args.data_dir)), host=args.host, port=args.port, log_level="info")
    return 0
