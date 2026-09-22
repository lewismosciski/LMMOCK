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


@pytest.mark.parametrize("host,shown", [("::1", "[::1]"), ("::", "[::1]"), ("0.0.0.0", "127.0.0.1")])
def test_cli_prints_usable_ipv6_and_provider_urls(tmp_path, monkeypatch, capsys, host, shown):
    from lmmock import cli

    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: None)
    cli.main(["--host", host, "--port", "18432", "--data-dir", str(tmp_path), "--no-open-browser"])
    output = capsys.readouterr().out
    for path in ("openai/v1", "anthropic", "gemini"):
        assert f"http://{shown}:18432/{path}" in output


def test_launcher_checks_runtime_imports_without_requiring_httpx(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("launcher", Path(__file__).resolve().parents[1] / "run.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    interpreter = tmp_path / "python"
    interpreter.touch()
    monkeypatch.setattr(launcher, "python_bin", lambda: interpreter)
    monkeypatch.setattr(launcher, "has_pip", lambda executable: executable == Path(sys.executable))
    calls = []

    def can_import(executable, modules, environment=None):
        calls.append(modules)
        return environment is not None and modules == "lmmock.cli"

    monkeypatch.setattr(launcher, "can_import", can_import)
    monkeypatch.setattr(launcher, "run", lambda *args: 0)
    monkeypatch.setattr(launcher.subprocess, "check_call", lambda *args: pytest.fail("Runtime already imports; no reinstall needed"))
    assert launcher.main() == 0
    assert calls == ["lmmock.cli", "lmmock.cli"]
