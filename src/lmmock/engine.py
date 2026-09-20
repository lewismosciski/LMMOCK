from __future__ import annotations

import json
import random
import re
from fnmatch import fnmatchcase
from dataclasses import dataclass
from typing import Any


@dataclass
class SemanticRequest:
    provider: str
    operation: str
    model: str
    text: str
    raw: dict[str, Any]
    stream: bool = False


@dataclass
class SemanticReply:
    kind: str
    text: str = ""
    value: Any = None
    tool_name: str = ""
    arguments: dict[str, Any] | None = None
    status_code: int = 200
    error_type: str = "mock_error"


RANDOM_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _random_text(size: int) -> str:
    chunks = []
    remaining = size
    while remaining:
        length = min(remaining, 65_536)
        chunks.append("".join(random.choices(RANDOM_ALPHABET, k=length)))
        remaining -= length
    return "".join(chunks)


def _part_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_part_text(item.get("text", "")) if isinstance(item, dict) else _part_text(item) for item in value)
    if isinstance(value, dict):
        return str(value.get("text", value.get("content", "")))
    return "" if value is None else str(value)


def request_from(provider: str, operation: str, body: dict[str, Any]) -> SemanticRequest:
    if provider == "openai" and operation == "chat":
        pieces = []
        for message in body.get("messages", []):
            if isinstance(message, dict):
                text = _part_text(message.get("content", ""))
                if text:
                    pieces.append(f"{message.get('role', 'message')}: {text}")
                for call in message.get("tool_calls", []):
                    pieces.append(f"tool_call: {call}")
        text = "\n".join(pieces)
    elif provider == "openai" and operation == "completions":
        text = _part_text(body.get("prompt", ""))
    elif provider == "openai" and operation == "responses":
        text = _part_text(body.get("input", ""))
        if isinstance(body.get("input"), list):
            text = "\n".join(_part_text(item.get("content", item)) if isinstance(item, dict) else _part_text(item) for item in body["input"])
    else:
        pieces = [_part_text(body.get("system", ""))]
        for message in body.get("messages", []):
            if isinstance(message, dict):
                content = _part_text(message.get("content", ""))
                if content:
                    pieces.append(f"{message.get('role', 'message')}: {content}")
        text = "\n".join(piece for piece in pieces if piece)
    return SemanticRequest(provider, operation, str(body.get("model", "gpt-5.6-sol")), text, body, bool(body.get("stream")))


def _fool_ai(value: str) -> str:
    statement = re.sub(r"[?？]+[\"'”’]?\s*$", "", value.strip())
    statement = re.sub(r"[吗么嘛呢]+\s*$", "", statement)
    statement = statement.replace("你们", "我们").replace("您", "我").replace("你", "我")
    return f"{statement}！"


def _template(value: Any, variables: dict[str, str]) -> Any:
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        result = variables.get(match.group(1), match.group(0))
        if match.group(2) == "foolAI":
            return _fool_ai(result)
        return result

    return re.sub(r"\$\{([A-Za-z0-9_.-]+)(?:\|([A-Za-z0-9_.-]+))?\}", replace, value)


def resolve(rules: list[dict[str, Any]], request: SemanticRequest) -> tuple[dict[str, Any] | None, SemanticReply | None]:
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        model_patterns = [pattern.strip() for pattern in rule.get("model_pattern", "*").split(",") if pattern.strip()]
        if not any(fnmatchcase(request.model, pattern) for pattern in model_patterns or ["*"]):
            continue
        if "*" not in rule.get("scopes", ["*"]) and request.operation not in rule.get("scopes", []):
            continue
        match = None
        kind = rule.get("match_type", "all")
        needle = rule.get("match_value", "")
        if kind == "all":
            match = True
        elif kind == "contains":
            match = needle.lower() in request.text.lower()
        elif kind == "regex":
            try:
                match = re.search(needle, request.text, re.IGNORECASE | re.DOTALL)
            except re.error:
                match = False
        if not match:
            continue
        variables = {"model": request.model, "last_user": request.text[-2000:]}
        if hasattr(match, "groupdict"):
            variables.update({key: str(value) for key, value in match.groupdict().items() if value is not None})
            variables.update({str(index): value for index, value in enumerate(match.groups(), 1) if value is not None})
        reply_data = {key: _template(value, variables) for key, value in (rule.get("reply") or {}).items()}
        reply_type = rule.get("reply_type", "text")
        if reply_type == "tool":
            arguments = reply_data.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"value": arguments}
            reply = SemanticReply("tool", tool_name=str(reply_data.get("tool_name", "mock_tool")), arguments=arguments)
        elif reply_type == "json":
            content = reply_data.get("content", "{}")
            try:
                value = json.loads(content) if isinstance(content, str) else content
            except json.JSONDecodeError:
                value = content
            reply = SemanticReply("json", text=json.dumps(value, ensure_ascii=False), value=value)
        elif reply_type == "error":
            reply = SemanticReply("error", text=str(reply_data.get("message", "Mock error")), status_code=int(reply_data.get("status_code", 500)), error_type=str(reply_data.get("error_type", "mock_error")))
        elif reply_type == "random":
            size = max(0, min(int(reply_data.get("size", 4096)), 10_000_000))
            reply = SemanticReply("text", text=_random_text(size))
        else:
            reply = SemanticReply("text", text=str(reply_data.get("content", "")))
        return rule, reply
    return None, None
