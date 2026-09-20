"""Small source checkout launcher.

It keeps the checkout isolated in .venv and then delegates to the real CLI.
Use a release binary or Docker when Python is not already available.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def python_bin() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def can_import(interpreter: Path, modules: str = "lmmock") -> bool:
    result = subprocess.run(
        [str(interpreter), "-c", f"import {modules}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def has_pip(interpreter: Path) -> bool:
    return can_import(interpreter, "pip")


def source_environment() -> dict[str, str]:
    environment = os.environ.copy()
    source = str(ROOT / "src")
    environment["PYTHONPATH"] = source + os.pathsep + environment.get("PYTHONPATH", "")
    return environment


def main() -> int:
    if sys.version_info < (3, 11):
        print("LMMock requires Python 3.11 or newer.", file=sys.stderr)
        return 2
    interpreter = python_bin()
    if not interpreter.exists():
        print(f"Creating {VENV} ...")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
    if not can_import(interpreter):
        if has_pip(interpreter):
            print("Installing the checkout into the local environment ...")
            subprocess.check_call([str(interpreter), "-m", "pip", "install", "-e", str(ROOT)])
        elif can_import(Path(sys.executable), "fastapi, httpx, uvicorn"):
            print("The local .venv has no pip; using the current Python with the checkout on PYTHONPATH.")
            return subprocess.call([sys.executable, "-m", "lmmock", *sys.argv[1:]], env=source_environment())
        else:
            print("The local .venv has no pip. Install Python with ensurepip, remove .venv, and run again.", file=sys.stderr)
            return 2
    return subprocess.call([str(interpreter), "-m", "lmmock", *sys.argv[1:]])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
