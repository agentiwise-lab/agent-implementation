"""A live model behind the same `LLMClient` contract.

Same interface as `FakeLLMClient`, so the loop, tools, caps, and everything above
do not change when the model becomes real. It speaks the OpenAI-compatible
chat-completions API that OpenRouter exposes, forwarding the tool schemas so the
model can call tools.

Kept frugal by construction: temperature 0 and a low `max_tokens` default. Used
for a small number of smoke checks that prove the agent behaves against a real
model, not for bulk runs (those replay recorded runs offline).
"""

from __future__ import annotations

import json
import os

import requests

from .llm import LLMClient, LLMResponse, Message, ToolCall

_DEFAULT_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "google/gemini-3.5-flash"


def _to_openai_messages(messages: list[Message]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if m.role == "assistant" and m.tool_name:
            out.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": m.tool_call_id,
                    "type": "function",
                    "function": {"name": m.tool_name, "arguments": json.dumps(m.tool_args)},
                }],
            })
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        else:
            out.append({"role": m.role, "content": m.content})
    return out


class OpenRouterClient:
    """Live `LLMClient` over OpenRouter's OpenAI-compatible endpoint."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        timeout: int = 60,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set; live client cannot run.")
        self.base_url = (base_url or os.environ.get("OPENROUTER_BASE_URL") or _DEFAULT_BASE).strip().rstrip("/")
        self.model = (model or os.environ.get("OPENROUTER_MODEL") or _DEFAULT_MODEL).strip()
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.calls = 0

    def complete(self, messages: list[Message], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        payload: dict = {
            "model": self.model,
            "messages": _to_openai_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        choice = resp.json()["choices"][0]
        message = choice["message"]

        tool_calls = message.get("tool_calls")
        if tool_calls:
            fn = tool_calls[0]["function"]
            args = json.loads(fn.get("arguments") or "{}")
            return LLMResponse(tool_call=ToolCall(name=fn["name"], args=args))

        content = message.get("content") or ""
        if not content and choice.get("finish_reason") == "length":
            # A reasoning model can spend the whole token budget before emitting any
            # answer. Surface that truncation instead of returning a silent empty
            # final, which would look like a resolved ticket with no answer.
            content = "(no answer: response truncated at max_tokens; raise max_tokens)"
        return LLMResponse(final_text=content)
