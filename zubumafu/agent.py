"""One bounded Ollama tool-calling cycle; no arbitrary tool execution."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .catalog import search_products
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
        from ollama import chat as chat_fn

    messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend((history or [])[-12:])
    messages.append({"role": "user", "content": user_message})
    trace: list[dict[str, object]] = []

    for _ in range(TOOL_CYCLE_LIMIT):
        response = chat_fn(
            model=MODEL,
            messages=messages,
            tools=[search_products],
            think=False,
            stream=False,
            options={"temperature": 0.3, "num_ctx": 4096},
        )
        message = response.message
        calls = getattr(message, "tool_calls", None) or []
        if not calls:
            content = (getattr(message, "content", None) or "").strip()
            if not content:
                return "Não consegui preparar uma resposta agora. Tente novamente, por favor.", trace
            if not trace and _requires_catalog_lookup(user_message):
                return "Não consegui confirmar essa informação no catálogo. Pode tentar reformular a pergunta?", trace
            return content, trace

        messages.append(message)
        for call in calls[:5]:
            name = call.function.name
            arguments = call.function.arguments or {}
            if name not in TOOLS:
                result = json.dumps({"error": "unknown tool"})
                trace.append({"tool": name, "status": "rejected"})
            else:
                try:
                    result = TOOLS[name](**arguments)
                    decoded = json.loads(result)
                    trace.append({"tool": name, "status": "error" if "error" in decoded else "ok", "matches": decoded.get("total_matches")})
                except (TypeError, ValueError, OSError) as exc:
                    result = json.dumps({"error": type(exc).__name__})
                    trace.append({"tool": name, "status": "error"})
            messages.append({"role": "tool", "tool_name": name, "content": result})

    return "A consulta ficou mais complexa do que o esperado. Vamos tentar uma pergunta mais específica?", trace


def _requires_catalog_lookup(message: str) -> bool:
    lowered = message.casefold()
    return any(token in lowered for token in ("preço", "preco", "custa", "estoque", "disponível", "disponive", "violão", "violões", "guitarra", "ukulele", "até r$", "ate r$"))
