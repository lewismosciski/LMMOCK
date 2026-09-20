import pytest

from lmmock.engine import SemanticRequest, request_from, resolve
from lmmock.storage import FOOL_AI_RULE


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("你吃饭了吗？", "我吃饭了！"),
        ("你吃饭了吗?", "我吃饭了！"),
        ("你吃饭了吗", "我吃饭了！"),
        ("你们准备好了吗？", "我们准备好了！"),
        ("您回家了么", "我回家了！"),
        ("你在工作呢？", "我在工作！"),
        ('你好吗？”', "我好！"),
    ],
)
def test_fool_ai_question_variants(question, expected):
    request = SemanticRequest("openai", "completions", "mock-model", question, {}, False)
    rule, reply = resolve([FOOL_AI_RULE], request)
    assert rule["name"] == "foolAI"
    assert reply.text == expected


@pytest.mark.parametrize("statement", ["你吃饭了。", "今天晴天", "user: 你很好！"])
def test_fool_ai_ignores_statements(statement):
    request = SemanticRequest("openai", "completions", "mock-model", statement, {}, False)
    assert resolve([FOOL_AI_RULE], request) == (None, None)


def test_resolve_honors_enabled_scope_and_priority():
    request = SemanticRequest("openai", "chat", "mock-model", "user: hello", {}, False)
    rules = [
        {"name": "disabled", "enabled": False, "priority": 1, "scopes": ["*"], "match_type": "all", "reply_type": "text", "reply": {"content": "wrong"}},
        {"name": "wrong scope", "enabled": True, "priority": 2, "scopes": ["messages"], "match_type": "all", "reply_type": "text", "reply": {"content": "wrong"}},
        {"name": "winner", "enabled": True, "priority": 3, "scopes": ["chat"], "match_type": "contains", "match_value": "hello", "reply_type": "text", "reply": {"content": "right"}},
        {"name": "fallback", "enabled": True, "priority": 4, "scopes": ["*"], "match_type": "all", "reply_type": "text", "reply": {"content": "late"}},
    ]
    rule, reply = resolve(rules, request)
    assert rule["name"] == "winner"
    assert reply.text == "right"


def test_invalid_regex_is_skipped():
    request = SemanticRequest("openai", "responses", "mock-model", "hello", {}, False)
    broken = {"enabled": True, "scopes": ["*"], "match_type": "regex", "match_value": "(", "reply_type": "text", "reply": {"content": "wrong"}}
    assert resolve([broken], request) == (None, None)


def test_request_from_extracts_supported_protocol_text():
    chat = request_from("openai", "chat", {"model": "m", "messages": [{"role": "user", "content": "hello"}]})
    completion = request_from("openai", "completions", {"model": "m", "prompt": "hello"})
    responses = request_from("openai", "responses", {"model": "m", "input": "hello"})
    anthropic = request_from("anthropic", "messages", {"model": "m", "system": "system", "messages": [{"role": "user", "content": "hello"}]})
    assert chat.text == "user: hello"
    assert completion.text == "hello"
    assert responses.text == "hello"
    assert anthropic.text == "system\nuser: hello"
