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
        target.add_argument("--host", default=argparse.SUPPRESS if target is serve else host())
        target.add_argument("--port", type=int, default=argparse.SUPPRESS if target is serve else port())
        target.add_argument("--data-dir", default=argparse.SUPPRESS if target is serve else str(data_dir()))
        target.add_argument("--no-open-browser", action="store_true", default=argparse.SUPPRESS if target is serve else False)
    sub.add_parser("version")
    sub.add_parser("data-dir")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "data-dir":
        print(args.data_dir)
        return 0
    browser_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    address = f"http://{browser_host}:{args.port}"
    if not args.no_open_browser and not no_browser():
        threading.Thread(target=_open_browser, args=(address,), daemon=True).start()
    print(f"LMMock listening at {address}")
    print(f"OpenAI-compatible base URL: {address}/openai/v1")
    print(f"Anthropic base URL: {address}/anthropic")
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("Warning: LMMock is listening beyond localhost. Configure optional per-model API keys in the web UI.")
    uvicorn.run(create_app(Path(args.data_dir)), host=args.host, port=args.port, log_level="info")
    return 0
