import os
import subprocess
import sys
from pathlib import Path


def test_version_and_import_do_not_create_database(tmp_path):
    data = tmp_path / "unused"
    env = {**os.environ, "LMMOCK_DATA_DIR": str(data), "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    result = subprocess.run([sys.executable, "-m", "lmmock", "version"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not data.exists()
    result = subprocess.run([sys.executable, "-c", "from lmmock.app import app; assert app is not None"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (data / "lmmock.sqlite3").exists()
