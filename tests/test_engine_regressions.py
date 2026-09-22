import os
import subprocess
import sys
from pathlib import Path

from lmmock.engine import request_from, resolve


def test_pathological_regex_cannot_hang_server():
    code = '''
from lmmock.engine import SemanticRequest, resolve
from lmmock.storage import DEFAULT_RULE
rules = [{"match_type": "regex", "match_value": "(a+)+$"}, DEFAULT_RULE]
rule, reply = resolve(rules, SemanticRequest("openai", "chat", "test", "a" * 10000 + "!", {}))
assert reply.text == "LMMock is running."
'''
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(Path(__file__).resolve().parents[1] / "src"), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
