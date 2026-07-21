"""OpenRouter client response parsing, offline (HTTP mocked).

Behavior under test:
- a tool_calls response becomes a ToolCall
- a normal content response becomes a final answer
- an empty content response with finish_reason 'length' is surfaced as a
  truncation notice, never a silent empty final that looks like a resolved ticket
"""

import json

import supportagent.openrouter as orouter
from supportagent.openrouter import OpenRouterClient


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _client(monkeypatch, choice):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(orouter.requests, "post", lambda *a, **k: _Resp({"choices": [choice]}))
    return OpenRouterClient()


def test_tool_call_is_parsed(monkeypatch):
    choice = {"finish_reason": "tool_calls", "message": {"tool_calls": [
        {"id": "c1", "type": "function",
         "function": {"name": "get_order_status", "arguments": json.dumps({"order_id": "88213"})}}]}}
    resp = _client(monkeypatch, choice).complete([], [])
    assert resp.tool_call is not None and resp.tool_call.name == "get_order_status"
    assert resp.tool_call.args == {"order_id": "88213"}


def test_normal_content_is_final(monkeypatch):
    choice = {"finish_reason": "stop", "message": {"content": "Delivered 2026-07-19."}}
    resp = _client(monkeypatch, choice).complete([], [])
    assert resp.is_final and resp.final_text == "Delivered 2026-07-19."


def test_truncated_empty_is_surfaced_not_silent(monkeypatch):
    # Reasoning model spent the whole budget before answering: empty content, length.
    choice = {"finish_reason": "length", "message": {"content": ""}}
    resp = _client(monkeypatch, choice).complete([], [])
    assert resp.is_final and "truncated" in resp.final_text.lower()
