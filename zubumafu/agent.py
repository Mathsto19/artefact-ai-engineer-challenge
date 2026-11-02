"""One bounded Ollama tool-calling cycle; no arbitrary tool execution."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any

from .catalog import _normalize, search_products
from .persona import SYSTEM_PROMPT


MODEL = "qwen3:4b"
TOOLS = {"search_products": search_products}
TOOL_CYCLE_LIMIT = 3


def respond(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    chat_fn: Callable[..., Any] | None = None,
) -> tuple[str, list[dict[str, object]]]:
    """Return a grounded reply and a tool trace (names/counts only).

    The caller owns the visible conversation history. Ollama message objects and
    tool responses are local to this one call, not persisted between sessions.
    """
    if chat_fn is None:
        from .model import create_chat

        chat_fn = create_chat()

    messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend((history or [])[-12:])
    messages.append({"role": "user", "content": user_message + "\n/no_think"})
    trace: list[dict[str, object]] = []

    for _ in range(TOOL_CYCLE_LIMIT):
        response = chat_fn(
            model=os.environ.get("OLLAMA_MODEL", MODEL),
            messages=messages,
            tools=[search_products],
            think=False,
            stream=False,
            options={"temperature": 0.3, "num_ctx": 4096, "num_predict": 2048},
        )
        message = response.message
        calls = getattr(message, "tool_calls", None) or []
        if not calls:
            content = _visible_content(getattr(message, "content", None) or "")
            if getattr(response, "done_reason", None) == "length":
                return "Não consegui concluir a resposta. Vamos tentar uma pergunta mais específica?", trace
            if not content:
                return "Não consegui preparar uma resposta agora. Tente novamente, por favor.", trace
            confirmed_lookup = any(item["status"] == "ok" for item in trace)
            if not confirmed_lookup and (_requires_catalog_lookup(user_message) or trace):
                return "Não consegui confirmar essa informação no catálogo. Pode tentar reformular a pergunta?", trace
            return content, trace

        if len(calls) > 5:
            return "A consulta pediu operações demais. Vamos tentar uma pergunta mais específica?", trace
        messages.append({
            "role": "assistant",
            "content": _visible_content(getattr(message, "content", None) or ""),
            "tool_calls": [{"function": {
                "name": call.function.name,
                "arguments": call.function.arguments or {},
            }} for call in calls],
        })
        for call in calls:
            name = call.function.name
            arguments = call.function.arguments or {}
            if name not in TOOLS:
                result = json.dumps({"error": "unknown tool"})
                trace.append({"tool": name, "status": "rejected"})
            else:
                try:
                    result = TOOLS[name](**arguments)
                    decoded = json.loads(result)
                    trace.append({
                        "tool": name,
                        "status": "error" if "error" in decoded else "ok",
                        "matches": decoded.get("total_matches"),
                        "filters": decoded.get("filters"),
                        "source": decoded.get("source"),
                    })
                except (TypeError, ValueError, OSError) as exc:
                    result = json.dumps({"error": type(exc).__name__})
                    trace.append({"tool": name, "status": "error"})
            messages.append({"role": "tool", "tool_name": name, "content": result})

    return "A consulta ficou mais complexa do que o esperado. Vamos tentar uma pergunta mais específica?", trace


def _visible_content(content: str) -> str:
    """Keep the final answer when a runtime leaks labeled reasoning into content.

    Some templates prefill <think>, leaving only a closing tag in content.
    An unfinished tagged block is discarded instead of shown to the customer.
    This rendering safeguard does not prove thinking generation was disabled.
    """
    content = re.split(r"</think\s*>", content, flags=re.IGNORECASE)[-1]
    if re.search(r"<think(?:\s|>)", content, flags=re.IGNORECASE):
        return ""
    return content.strip()


def _requires_catalog_lookup(message: str) -> bool:
    normalized = _normalize(message)
    return any(token in normalized for token in (
        "preco", "custa", "estoque", "disponiv", "catalogo", "r$",
        "violao", "violoes", "guitarra", "ukulele", "baixo", "bateria",
        "teclado", "piano", "violino", "violoncelo", "flauta", "saxofone",
        "trompete", "instrumento", "modelo",
    ))
