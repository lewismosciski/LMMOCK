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
LOCAL_PACKAGES = ROOT / ".lmmock" / "packages"


def python_bin() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def can_import(interpreter: Path, modules: str = "lmmock", environment: dict[str, str] | None = None) -> bool:
    result = subprocess.run(
        [str(interpreter), "-c", f"import {modules}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
        check=False,
    )
    return result.returncode == 0


def has_pip(interpreter: Path) -> bool:
    return can_import(interpreter, "pip")


def source_environment(*extra_paths: Path) -> dict[str, str]:
    environment = os.environ.copy()
    paths = [ROOT / "src", *extra_paths]
    current = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join([*(str(path) for path in paths), *([current] if current else [])])
    return environment


def run(interpreter: Path, environment: dict[str, str] | None = None) -> int:
    return subprocess.call([str(interpreter), "-m", "lmmock", *sys.argv[1:]], env=environment)


def main() -> int:
    if sys.version_info < (3, 11):
        print("LMMock requires Python 3.11 or newer.", file=sys.stderr)
        return 2
    interpreter = python_bin()
    if not interpreter.exists():
        print(f"Creating {VENV} ...", flush=True)
        try:
            venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
        except subprocess.CalledProcessError:
            pass
    if not interpreter.exists() or not can_import(interpreter, "lmmock.cli"):
        if interpreter.exists() and has_pip(interpreter):
            print("Installing the checkout into the local environment ...", flush=True)
            subprocess.check_call([str(interpreter), "-m", "pip", "install", "-e", str(ROOT)])
        elif has_pip(Path(sys.executable)):
            environment = source_environment(LOCAL_PACKAGES)
            if not can_import(Path(sys.executable), "lmmock.cli", environment):
                print("The virtual environment has no pip; installing dependencies into .lmmock ...", flush=True)
                LOCAL_PACKAGES.mkdir(parents=True, exist_ok=True)
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "--upgrade", "--target", str(LOCAL_PACKAGES), str(ROOT),
                ])
            return run(Path(sys.executable), environment)
        else:
            print("Python has no pip. Install the standard Python distribution or use Docker.", file=sys.stderr)
            return 2
    return run(interpreter)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
