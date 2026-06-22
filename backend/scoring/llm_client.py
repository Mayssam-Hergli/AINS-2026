"""
LLM provider abstraction for the MS2 scoring agent.

This is the ONLY file that knows which provider is active.
Change provider with one env-var — no other file needs to change:

    LLM_PROVIDER=groq        (default) Groq via OpenAI-compatible API
    LLM_PROVIDER=anthropic   Anthropic API directly

Schema format note
------------------
TOOLS in tools.py use Anthropic schema shape:
    {"name": ..., "description": ..., "input_schema": {...}}

OpenAI/Groq expects:
    {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}

_anthropic_to_openai_tools() converts on the fly so the canonical
schema lives in one place (tools.py) and is never duplicated.

Message format note
-------------------
agent.py builds history in OpenAI format (de facto cross-provider standard).
The Anthropic branch converts that history to Anthropic format before each
API call. Both paths return the same normalized dict:
    {
        "text":        str | None,       assistant's text content if any
        "tool_calls":  list[dict],       [{call_id, tool_name, tool_input}]
        "stop_reason": "tool_use" | "end_turn",
    }
agent.py never sees a provider-specific object.
"""
from __future__ import annotations

import json
import os


# ---------------------------------------------------------------------------
# Schema converter: Anthropic -> OpenAI/Groq
# ---------------------------------------------------------------------------

def _anthropic_to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


# ---------------------------------------------------------------------------
# Message format converter: OpenAI history -> Anthropic messages
# ---------------------------------------------------------------------------

def _openai_to_anthropic_messages(messages: list[dict]) -> list[dict]:
    """
    OpenAI assistant turn:
        {"role": "assistant", "content": None,  "tool_calls": [{id, type, function}]}
    OpenAI tool result:
        {"role": "tool",      "tool_call_id": "...", "content": "..."}

    Anthropic assistant turn:
        {"role": "assistant", "content": [{"type": "tool_use", "id": ..., "name": ..., "input": {...}}]}
    Anthropic tool results (multiple from one turn -> single user message):
        {"role": "user",      "content": [{"type": "tool_result", "tool_use_id": ..., "content": "..."}]}
    """
    result: list[dict] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg["role"]

        if role == "user":
            result.append({"role": "user", "content": msg["content"]})
            i += 1

        elif role == "assistant":
            content: list[dict] = []
            if msg.get("content"):
                content.append({"type": "text", "text": msg["content"]})
            for tc in (msg.get("tool_calls") or []):
                content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"]),
                })
            # Anthropic rejects an empty content list
            if not content:
                content = [{"type": "text", "text": ""}]
            result.append({"role": "assistant", "content": content})
            i += 1

            # Collect all tool results that belong to this assistant turn
            tool_results: list[dict] = []
            while i < len(messages) and messages[i]["role"] == "tool":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": messages[i]["tool_call_id"],
                    "content": messages[i]["content"],
                })
                i += 1
            if tool_results:
                result.append({"role": "user", "content": tool_results})

        else:
            i += 1

    return result


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _run_groq_turn(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
) -> dict:
    from openai import OpenAI

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ["GROQ_API_KEY"],
    )

    kwargs: dict = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    if tools:
        kwargs["tools"] = _anthropic_to_openai_tools(tools)
        kwargs["tool_choice"] = "auto"

    response = client.chat.completions.create(**kwargs)
    message = response.choices[0].message

    normalized_calls = []
    for tc in (message.tool_calls or []):
        normalized_calls.append({
            "call_id": tc.id,
            "tool_name": tc.function.name,
            "tool_input": json.loads(tc.function.arguments),
        })

    return {
        "text": message.content,
        "tool_calls": normalized_calls,
        "stop_reason": "tool_use" if normalized_calls else "end_turn",
    }


def _run_anthropic_turn(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
) -> dict:
    # Imported lazily — anthropic package is optional until this branch is used
    import anthropic  # noqa: PLC0415

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    kwargs: dict = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": _openai_to_anthropic_messages(messages),
    }
    if tools:
        kwargs["tools"] = tools  # already in Anthropic format

    response = client.messages.create(**kwargs)

    text = None
    normalized_calls = []
    for block in response.content:
        if block.type == "text":
            text = block.text
        elif block.type == "tool_use":
            normalized_calls.append({
                "call_id": block.id,
                "tool_name": block.name,
                "tool_input": block.input,
            })

    return {
        "text": text,
        "tool_calls": normalized_calls,
        "stop_reason": "tool_use" if normalized_calls else "end_turn",
    }


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

_PROVIDERS: dict = {
    "groq":      _run_groq_turn,
    "anthropic": _run_anthropic_turn,
}


def run_agent_turn(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
) -> dict:
    """
    Execute one LLM turn, returning a normalized result dict:

        {
            "text":        str | None,
            "tool_calls":  [{"call_id": str, "tool_name": str, "tool_input": dict}],
            "stop_reason": "tool_use" | "end_turn",
        }

    Provider is selected by LLM_PROVIDER env var (default: "groq").
    Swap providers by changing that variable — nothing else needs to change.
    """
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER={provider!r}. Valid: {sorted(_PROVIDERS)}"
        )
    return fn(system_prompt, messages, tools)
