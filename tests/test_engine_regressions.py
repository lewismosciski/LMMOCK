import os
import json
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


def test_regex_templates_expand_nested_tool_values_without_mutating_rule():
    rule = {"match_type": "regex", "match_value": r"city=(?P<city>.+)", "reply_type": "tool", "reply": {"arguments": {"places": [{"name": "${city}"}], "count": 2}}}
    request = request_from("openai", "responses", {"input": "city=Shanghai"})
    _, reply = resolve([rule], request)
    assert reply.arguments == {"places": [{"name": "Shanghai"}], "count": 2}
    assert rule["reply"]["arguments"]["places"][0]["name"] == "${city}"


def test_json_template_escapes_captured_quotes():
    rule = {"match_type": "regex", "match_value": r"city=(?P<city>.+)", "reply_type": "json", "reply": {"content": '{"city":"${city}"}'}}
    request = request_from("openai", "responses", {"input": 'city=O"Brien'})
    _, reply = resolve([rule], request)
    assert json.loads(reply.text) == {"city": 'O"Brien'}
