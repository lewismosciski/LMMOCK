import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_version_and_import_do_not_create_database(tmp_path):
    data = tmp_path / "unused"
    env = {**os.environ, "LMMOCK_DATA_DIR": str(data), "PYTHONPATH": os.pathsep.join([str(Path(__file__).resolve().parents[1] / "src"), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run([sys.executable, "-m", "lmmock", "version"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not data.exists()
    result = subprocess.run([sys.executable, "-c", "from lmmock.app import app; assert app is not None"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (data / "lmmock.sqlite3").exists()


@pytest.mark.parametrize("before", [True, False])
def test_serve_preserves_options_on_either_side_of_subcommand(tmp_path, monkeypatch, before):
    from lmmock import cli

    captured = {}
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: captured.update(app=app, **kwargs))
    options = ["--host", "127.0.0.2", "--port", "18432", "--data-dir", str(tmp_path), "--no-open-browser"]
    assert cli.main([*options, "serve"] if before else ["serve", *options]) == 0
    assert captured["port"] == 18432
    assert captured["host"] == "127.0.0.2"
    assert captured["app"].state.lmmock.store.path.parent == tmp_path
