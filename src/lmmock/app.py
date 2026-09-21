from __future__ import annotations

import asyncio
import json
import secrets
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import data_dir
from .engine import SemanticReply, SemanticRequest, request_from, resolve
from .storage import Store


class State:
    def __init__(self, store: Store):
        self.store = store
        self.requests: deque[dict[str, Any]] = deque(maxlen=100)
        self.reset_stats()

    def reset_stats(self) -> None:
        self.stats: dict[str, Any] = {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "by_model": {},
        }

    def add_usage(self, model: str, usage: dict[str, int]) -> None:
        self.stats["requests"] += 1
        model_stats = self.stats["by_model"].setdefault(
            model,
            {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        model_stats["requests"] += 1
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            self.stats[key] += usage[key]
            model_stats[key] += usage[key]


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def _token_count(text: str) -> int:
    """Return a lightweight, tokenizer-free estimate used consistently by every API."""
    return (len(text) + 3) // 4


def _usage(input_text: str, output_text: str) -> dict[str, int]:
    input_tokens = _token_count(input_text)
    output_tokens = _token_count(output_text)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens}


def _reply_output(reply: SemanticReply) -> str:
    return _json(reply.arguments or {}) if reply.kind == "tool" else reply.text


def _error_payload(provider: str, reply: SemanticReply) -> dict[str, Any]:
    if provider == "anthropic":
        return {"type": "error", "error": {"type": reply.error_type, "message": reply.text}}
    return {"error": {"message": reply.text, "type": reply.error_type, "param": None, "code": None}}


def _error(provider: str, reply: SemanticReply, request_id: str) -> JSONResponse:
    header = "request-id" if provider == "anthropic" else "x-request-id"
    return JSONResponse(_error_payload(provider, reply), status_code=reply.status_code, headers={header: request_id})


def _snapshot(value: Any, limit: int = 20_000) -> Any:
    rendered = json.dumps(value, ensure_ascii=False, default=str)
    if len(rendered) <= limit:
        return value
    return {"truncated": True, "preview": rendered[:limit]}


def _chat_payload(request: SemanticRequest, reply: SemanticReply, response_id: str) -> dict[str, Any]:
    if reply.kind == "tool":
        message: dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": _id("call"), "type": "function", "function": {"name": reply.tool_name, "arguments": _json(reply.arguments or {})}}],
        }
        finish = "tool_calls"
    else:
        message = {"role": "assistant", "content": reply.text}
        finish = "stop"
    return {"id": response_id, "object": "chat.completion", "created": int(time.time()), "model": request.model, "choices": [{"index": 0, "message": message, "finish_reason": finish}], "usage": _usage(request.text, _reply_output(reply))}


def _completion_payload(request: SemanticRequest, reply: SemanticReply, response_id: str) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "text_completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{"index": 0, "text": reply.text, "finish_reason": "stop", "logprobs": None}],
        "usage": _usage(request.text, _reply_output(reply)),
    }


def _responses_payload(request: SemanticRequest, reply: SemanticReply, response_id: str) -> dict[str, Any]:
    if reply.kind == "tool":
        output = [{"id": _id("fc"), "type": "function_call", "status": "completed", "call_id": _id("call"), "name": reply.tool_name, "arguments": _json(reply.arguments or {})}]
        output_text = ""
    else:
        output = [{"id": _id("msg"), "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": reply.text, "annotations": []}]}]
        output_text = reply.text
    return {"id": response_id, "object": "response", "created_at": int(time.time()), "status": "completed", "model": request.model, "output": output, "output_text": output_text, "usage": _usage(request.text, _reply_output(reply))}


def _anthropic_payload(request: SemanticRequest, reply: SemanticReply, response_id: str) -> dict[str, Any]:
    if reply.kind == "tool":
        content = [{"type": "tool_use", "id": _id("toolu"), "name": reply.tool_name, "input": reply.arguments or {}}]
        stop_reason = "tool_use"
    else:
        content = [{"type": "text", "text": reply.text}]
        stop_reason = "end_turn"
    usage = _usage(request.text, _reply_output(reply))
    return {"id": response_id, "type": "message", "role": "assistant", "model": request.model, "content": content, "stop_reason": stop_reason, "stop_sequence": None, "usage": {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"]}}


def _sse(data: Any, event: str | None = None) -> bytes:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {_json(data)}\n\n".encode()


async def _chat_stream(request: SemanticRequest, reply: SemanticReply, response_id: str, include_usage: bool) -> AsyncIterator[bytes]:
    base = {"id": response_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": request.model}
    yield _sse({**base, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]})
    if reply.kind == "tool":
        call_id = _id("call")
        yield _sse({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": call_id, "type": "function", "function": {"name": reply.tool_name, "arguments": ""}}]}, "finish_reason": None}]})
        arguments = _json(reply.arguments or {})
        for start in range(0, len(arguments), 32):
            await asyncio.sleep(0)
            yield _sse({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": arguments[start:start + 32]}}]}, "finish_reason": None}]})
        finish = "tool_calls"
    else:
        for start in range(0, len(reply.text), 4096):
            await asyncio.sleep(0)
            yield _sse({**base, "choices": [{"index": 0, "delta": {"content": reply.text[start:start + 4096]}, "finish_reason": None}]})
        finish = "stop"
    yield _sse({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
    if include_usage:
        yield _sse({**base, "choices": [], "usage": _usage(request.text, _reply_output(reply))})
    yield b"data: [DONE]\n\n"


async def _completion_stream(request: SemanticRequest, reply: SemanticReply, response_id: str) -> AsyncIterator[bytes]:
    base = {"id": response_id, "object": "text_completion", "created": int(time.time()), "model": request.model}
    for start in range(0, len(reply.text), 4096):
        await asyncio.sleep(0)
        yield _sse({**base, "choices": [{"index": 0, "text": reply.text[start:start + 4096], "finish_reason": None, "logprobs": None}]})
    yield _sse({**base, "choices": [{"index": 0, "text": "", "finish_reason": "stop", "logprobs": None}]})
    yield b"data: [DONE]\n\n"


async def _responses_stream(request: SemanticRequest, reply: SemanticReply, response_id: str) -> AsyncIterator[bytes]:
    sequence = 0

    def event(kind: str, **values: Any) -> bytes:
        nonlocal sequence
        sequence += 1
        payload: dict[str, Any] = {"type": kind, "sequence_number": sequence}
        payload.update(values)
        return _sse(payload, kind)

    in_progress = {"id": response_id, "object": "response", "created_at": int(time.time()), "status": "in_progress", "model": request.model, "output": []}
    yield event("response.created", response=in_progress)
    yield event("response.in_progress", response=in_progress)
    item_id = _id("msg")
    if reply.kind == "tool":
        item_id = _id("fc")
        call_id = _id("call")
        yield event("response.output_item.added", output_index=0, item={"id": item_id, "type": "function_call", "status": "in_progress", "call_id": call_id, "name": reply.tool_name, "arguments": ""})
        arguments = _json(reply.arguments or {})
        for start in range(0, len(arguments), 32):
            yield event("response.function_call_arguments.delta", item_id=item_id, output_index=0, delta=arguments[start:start + 32])
        yield event("response.function_call_arguments.done", item_id=item_id, output_index=0, arguments=arguments)
        final_item = {"id": item_id, "type": "function_call", "status": "completed", "call_id": call_id, "name": reply.tool_name, "arguments": arguments}
    else:
        yield event("response.output_item.added", output_index=0, item={"id": item_id, "type": "message", "status": "in_progress", "role": "assistant", "content": []})
        yield event("response.content_part.added", item_id=item_id, output_index=0, content_index=0, part={"type": "output_text", "text": "", "annotations": []})
        for start in range(0, len(reply.text), 4096):
            yield event("response.output_text.delta", item_id=item_id, output_index=0, content_index=0, delta=reply.text[start:start + 4096])
        yield event("response.output_text.done", item_id=item_id, output_index=0, content_index=0, text=reply.text)
        content = {"type": "output_text", "text": reply.text, "annotations": []}
        yield event("response.content_part.done", item_id=item_id, output_index=0, content_index=0, part=content)
        final_item = {"id": item_id, "type": "message", "status": "completed", "role": "assistant", "content": [content]}
    yield event("response.output_item.done", output_index=0, item=final_item)
    completed = _responses_payload(request, reply, response_id)
    completed["output"] = [final_item]
    yield event("response.completed", response=completed)


async def _anthropic_stream(request: SemanticRequest, reply: SemanticReply, response_id: str) -> AsyncIterator[bytes]:
    message = _anthropic_payload(request, reply, response_id)
    yield _sse({"type": "message_start", "message": {**message, "content": [], "stop_reason": None}}, "message_start")
    if reply.kind == "tool":
        block = {"type": "tool_use", "id": _id("toolu"), "name": reply.tool_name, "input": {}}
        yield _sse({"type": "content_block_start", "index": 0, "content_block": block}, "content_block_start")
        arguments = _json(reply.arguments or {})
        for start in range(0, len(arguments), 32):
            yield _sse({"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": arguments[start:start + 32]}}, "content_block_delta")
    else:
        yield _sse({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}, "content_block_start")
        for start in range(0, len(reply.text), 4096):
            yield _sse({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": reply.text[start:start + 4096]}}, "content_block_delta")
    yield _sse({"type": "content_block_stop", "index": 0}, "content_block_stop")
    yield _sse({"type": "message_delta", "delta": {"stop_reason": message["stop_reason"]}, "usage": message["usage"]}, "message_delta")
    yield _sse({"type": "message_stop"}, "message_stop")


def create_app(storage_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="LMMock", version=__version__, docs_url=None, redoc_url=None)
    store = Store((storage_dir or data_dir()) / "lmmock.sqlite3")
    state = State(store)
    app.state.lmmock = state
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "name": "lmmock", "version": __version__, "mode": "mock-first"}

    def configured_model(settings: dict[str, Any], model: str, provider: str) -> dict[str, Any] | None:
        return next(
            (config for config in settings["model_configs"] if config["name"] == model and config["protocol"] == provider),
            None,
        )

    def authentication_error(provider: str, request: Request, config: dict[str, Any]) -> Response | None:
        required_key = config["api_key"]
        if not required_key:
            return None
        authorization = request.headers.get("authorization", "")
        bearer = authorization[7:] if authorization.lower().startswith("bearer ") else ""
        supplied = bearer or request.headers.get("x-api-key", "")
        if supplied and secrets.compare_digest(supplied, required_key):
            return None
        error = SemanticReply("error", text=f"A valid API key is required for model '{config['name']}'.", status_code=401, error_type="authentication_error")
        return _error(provider, error, _id("req"))

    async def handle(provider: str, operation: str, request: Request) -> Response:
        raw = await request.body()
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return JSONResponse({"error": {"message": "Request body must be JSON", "type": "invalid_request_error"}}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": {"message": "Request body must be an object", "type": "invalid_request_error"}}, status_code=400)
        settings = store.get_settings()
        body = dict(body)
        provider_default = next((config["name"] for config in settings["model_configs"] if config["protocol"] == provider), "")
        body.setdefault("model", provider_default)
        semantic = request_from(provider, operation, body)
        config = configured_model(settings, semantic.model, provider)
        if config is None:
            error = SemanticReply("error", text=f"Model '{semantic.model}' is not configured for the {provider} interface.", status_code=404, error_type="model_not_found")
            return _error(provider, error, _id("req"))
        auth_error = authentication_error(provider, request, config)
        if auth_error:
            return auth_error
        groups = store.list_groups()
        requested_group = request.headers.get("x-lmmock-group") or body.get("lmmock_group")
        group = next((item for item in groups if str(item["id"]) == str(requested_group) or item["name"] == requested_group), None) if requested_group else None
        if requested_group and (group is None or group["id"] not in config["group_ids"]):
            return JSONResponse({"error": {"message": f"Behavior group '{requested_group}' is not assigned to model '{semantic.model}'.", "type": "invalid_request_error"}}, status_code=400)
        selected_groups = [group] if group else [item for item in groups if item["id"] in config["group_ids"]]
        group_label = ", ".join(item["name"] for item in selected_groups)
        started = time.perf_counter()

        def record(request_id: str, rule_name: str | None, status: int, response_body: Any, output_text: str) -> None:
            usage = _usage(semantic.text, output_text)
            state.add_usage(semantic.model, usage)
            state.requests.appendleft({
                "id": request_id,
                "provider": provider,
                "operation": operation,
                "model": semantic.model,
                "group": group_label,
                "rule": rule_name,
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "input": semantic.text[-240:],
                "request": _snapshot(body),
                "response": _snapshot(response_body),
                "usage": usage,
            })

        rules = [rule for selected_group in selected_groups for rule in store.list_rules(selected_group["id"])]
        rules.sort(key=lambda item: (item["priority"], item["id"]))
        rule, reply = resolve(rules, semantic)
        if reply is None:
            reply = SemanticReply("text", text="No rule matched.")
        if rule and rule.get("delay_ms"):
            await asyncio.sleep(rule["delay_ms"] / 1000)
        request_id = _id("req")
        if reply.kind == "error":
            record(request_id, rule["name"] if rule else None, reply.status_code, _error_payload(provider, reply), reply.text)
            return _error(provider, reply, request_id)
        response_id = _id("chatcmpl" if operation == "chat" else "cmpl" if operation == "completions" else "resp" if operation == "responses" else "msg")
        if operation == "chat":
            payload = _chat_payload(semantic, reply, response_id)
            record(request_id, rule["name"] if rule else None, reply.status_code, payload, _reply_output(reply))
            if semantic.stream:
                include_usage = bool((body.get("stream_options") or {}).get("include_usage"))
                return StreamingResponse(_chat_stream(semantic, reply, response_id, include_usage), media_type="text/event-stream", headers={"cache-control": "no-cache", "x-request-id": request_id})
            return JSONResponse(payload, headers={"x-request-id": request_id})
        if operation == "completions":
            payload = _completion_payload(semantic, reply, response_id)
            record(request_id, rule["name"] if rule else None, reply.status_code, payload, _reply_output(reply))
            if semantic.stream:
                return StreamingResponse(_completion_stream(semantic, reply, response_id), media_type="text/event-stream", headers={"cache-control": "no-cache", "x-request-id": request_id})
            return JSONResponse(payload, headers={"x-request-id": request_id})
        if operation == "responses":
            payload = _responses_payload(semantic, reply, response_id)
            record(request_id, rule["name"] if rule else None, reply.status_code, payload, _reply_output(reply))
            if semantic.stream:
                return StreamingResponse(_responses_stream(semantic, reply, response_id), media_type="text/event-stream", headers={"cache-control": "no-cache", "x-request-id": request_id})
            return JSONResponse(payload, headers={"x-request-id": request_id})
        payload = _anthropic_payload(semantic, reply, response_id)
        record(request_id, rule["name"] if rule else None, reply.status_code, payload, _reply_output(reply))
        if semantic.stream:
            return StreamingResponse(_anthropic_stream(semantic, reply, response_id), media_type="text/event-stream", headers={"cache-control": "no-cache", "request-id": request_id})
        return JSONResponse(payload, headers={"request-id": request_id})

    @app.post("/openai/v1/chat/completions")
    async def chat(request: Request) -> Response:
        return await handle("openai", "chat", request)

    @app.post("/openai/v1/responses")
    async def responses(request: Request) -> Response:
        return await handle("openai", "responses", request)

    @app.post("/openai/v1/completions")
    async def completions(request: Request) -> Response:
        return await handle("openai", "completions", request)

    @app.post("/anthropic/v1/messages")
    async def messages(request: Request) -> Response:
        return await handle("anthropic", "messages", request)

    @app.post("/anthropic/v1/messages/count_tokens")
    async def count_message_tokens(request: Request) -> Response:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"type": "error", "error": {"type": "invalid_request_error", "message": "Request body must be JSON"}}, status_code=400)
        settings = store.get_settings()
        anthropic_default = next((config["name"] for config in settings["model_configs"] if config["protocol"] == "anthropic"), "")
        body.setdefault("model", anthropic_default)
        config = configured_model(settings, str(body["model"]), "anthropic")
        if config is None:
            return JSONResponse({"type": "error", "error": {"type": "model_not_found", "message": f"Model '{body['model']}' is not configured for the anthropic interface."}}, status_code=404)
        auth_error = authentication_error("anthropic", request, config)
        if auth_error:
            return auth_error
        semantic = request_from("anthropic", "messages", body)
        return JSONResponse({"input_tokens": _token_count(semantic.text)})

    @app.get("/openai/v1/models")
    async def openai_models() -> dict[str, Any]:
        models = [config["name"] for config in store.get_settings()["model_configs"] if config["protocol"] == "openai"]
        return {"object": "list", "data": [{"id": model, "object": "model", "created": int(time.time()), "owned_by": "lmmock"} for model in models]}

    @app.get("/anthropic/v1/models")
    async def anthropic_models() -> dict[str, Any]:
        models = [config["name"] for config in store.get_settings()["model_configs"] if config["protocol"] == "anthropic"]
        return {"data": [{"type": "model", "id": model, "display_name": model, "created_at": "2025-01-01T00:00:00Z"} for model in models], "has_more": False, "first_id": models[0] if models else None, "last_id": models[-1] if models else None}

    @app.get("/__lmmock/api/info")
    async def info() -> dict[str, Any]:
        settings = store.get_settings()
        return {"name": "LMMock", "version": __version__, "providers": ["openai", "anthropic"], "operations": ["chat", "completions", "responses", "messages"], "models": settings["models"], "authentication": any(config["api_key"] for config in settings["model_configs"]), "data_dir": str(store.path.parent), "rules": len(store.list_rules()), "groups": len(store.list_groups())}

    @app.get("/__lmmock/api/rules")
    async def list_rules(group_id: int | None = None) -> list[dict[str, Any]]:
        return store.list_rules(group_id)

    @app.post("/__lmmock/api/rules")
    async def create_rule(request: Request) -> Response:
        try:
            return JSONResponse(store.create_rule(await request.json()), status_code=201)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/__lmmock/api/rules/{rule_id}")
    async def update_rule(rule_id: int, request: Request) -> Response:
        try:
            result = store.update_rule(rule_id, await request.json())
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(result) if result else JSONResponse({"error": "Rule not found"}, status_code=404)

    @app.delete("/__lmmock/api/rules/{rule_id}")
    async def delete_rule(rule_id: int) -> Response:
        return Response(status_code=204) if store.delete_rule(rule_id) else JSONResponse({"error": "Rule not found"}, status_code=404)

    @app.post("/__lmmock/api/rules/reorder")
    async def reorder(request: Request) -> list[dict[str, Any]]:
        data = await request.json()
        for priority, rule_id in enumerate(data.get("ids", []), 1):
            current = next((rule for rule in store.list_rules() if rule["id"] == int(rule_id)), None)
            if current:
                current["priority"] = priority
                store.update_rule(int(rule_id), current)
        return store.list_rules()

    @app.get("/__lmmock/api/groups")
    async def list_groups() -> list[dict[str, Any]]:
        return store.list_groups()

    @app.post("/__lmmock/api/groups")
    async def create_group(request: Request) -> Response:
        try:
            return JSONResponse(store.create_group(await request.json()), status_code=201)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/__lmmock/api/groups/{group_id}")
    async def update_group(group_id: int, request: Request) -> Response:
        try:
            result = store.update_group(group_id, await request.json())
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(result) if result else JSONResponse({"error": "Group not found"}, status_code=404)

    @app.delete("/__lmmock/api/groups/{group_id}")
    async def delete_group(group_id: int) -> Response:
        try:
            deleted = store.delete_group(group_id)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        return Response(status_code=204) if deleted else JSONResponse({"error": "Group not found"}, status_code=404)

    @app.post("/__lmmock/api/preview")
    async def preview(request: Request) -> Response:
        data = await request.json()
        protocol = data.get("protocol", "openai_chat")
        mapping = {"openai_chat": ("openai", "chat"), "openai_completions": ("openai", "completions"), "openai_responses": ("openai", "responses"), "anthropic_messages": ("anthropic", "messages")}
        provider, operation = mapping.get(protocol, ("openai", "chat"))
        semantic = request_from(provider, operation, data.get("body", {}))
        settings = store.get_settings()
        config = configured_model(settings, semantic.model, provider)
        group_ids = [int(data["group_id"])] if data.get("group_id") else (config["group_ids"] if config else [])
        rules = [rule for group_id in group_ids for rule in store.list_rules(group_id)]
        rules.sort(key=lambda item: (item["priority"], item["id"]))
        rule, reply = resolve(rules, semantic)
        return {"matched_rule": rule, "semantic_request": {"provider": semantic.provider, "operation": semantic.operation, "model": semantic.model, "text": semantic.text}, "reply": reply.__dict__ if reply else None}

    @app.get("/__lmmock/api/settings")
    async def settings() -> dict[str, Any]:
        return store.get_settings()

    @app.put("/__lmmock/api/settings")
    async def update_settings(request: Request) -> Response:
        try:
            return JSONResponse(store.set_settings(await request.json()))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/__lmmock/api/requests")
    async def recent_requests() -> list[dict[str, Any]]:
        return list(state.requests)

    @app.get("/__lmmock/api/stats")
    async def usage_stats() -> dict[str, Any]:
        return {**state.stats, "estimated": True}

    @app.delete("/__lmmock/api/requests")
    async def clear_requests() -> Response:
        state.requests.clear()
        state.reset_stats()
        return Response(status_code=204)

    return app


app = create_app()
