"""One bounded Ollama tool-calling cycle; no arbitrary tool execution."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any

from .catalog import _normalize, search_products
from .policies import search_store_policies
from .persona import SYSTEM_PROMPT


MODEL = "qwen3:4b"
TOOLS = {"search_products": search_products, "search_store_policies": search_store_policies}
TOOL_CYCLE_LIMIT = 3


def respond(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    chat_fn: Callable[..., Any] | None = None,
) -> tuple[str, list[dict[str, object]]]:
    """Return a source-backed reply and query/reference/clarification metadata.

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
            tools=list(TOOLS.values()),
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
            required_tool = _required_tool(user_message, history or [])
            confirmed_lookup = any(
                item["status"] == "ok" and (required_tool is None or item["tool"] == required_tool)
                for item in trace
            )
            if not confirmed_lookup and (required_tool or trace):
                return "Não consegui confirmar essa informação nos arquivos da loja. Pode tentar reformular a pergunta?", trace
            clarification = _return_clarification(user_message, history or [])
            return_source_verified = any(
                item["tool"] == "search_store_policies" and item["status"] == "ok"
                and item.get("topic") == "returns" and 4 in item.get("chapters", [])
                for item in trace
            )
            if required_tool == "search_store_policies" and clarification and return_source_verified:
                # The model draft must not skip missing return information or
                # invent a submission procedure. The source was retrieved and
                # returned to the model; Python controls these two safe questions.
                field, content = clarification
                for item in trace:
                    if item["tool"] == "search_store_policies" and item["status"] == "ok":
                        item["clarification_field"] = field
                        item["reply_origin"] = "source_verified_clarification_template"
            source_notes = []
            for item in trace:
                if item["tool"] != "search_store_policies" or item["status"] != "ok":
                    continue
                for reference in item.get("references", []):
                    pages = ", ".join(str(page) for page in reference["pages"])
                    note = f"Manual de políticas v2.1, seção(ões) {reference['chapter']}, página(s) {pages}"
                    if note not in source_notes:
                        source_notes.append(note)
            if source_notes:
                content += "\n\n*Fonte consultada: " + "; ".join(source_notes) + ".*"
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
                    status = "ok" if "error" not in decoded and decoded.get("status", "ok") == "ok" else "error"
                    sections = decoded.get("sections", [])
                    trace.append({
                        "tool": name,
                        "status": status,
                        "matches": decoded.get("total_matches", len(sections)),
                        "filters": decoded.get("filters"),
                        "source": decoded.get("source", decoded.get("source_file")),
                        "topic": decoded.get("topic"),
                        "pages": sorted({page for section in sections for page in section["pages"]}),
                        "chapters": [section["chapter"] for section in sections],
                        "references": [{"chapter": section["chapter"], "pages": section["pages"]} for section in sections],
                        "ambiguities": decoded.get("ambiguities", []),
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


def _requires_policy_lookup(message: str) -> bool:
    normalized = _normalize(message)
    return any(token in normalized for token in (
        "devol", "troca", "arrepend", "defeit", "garantia", "horar",
        "funcionamento", "endereco", "onde fica", "frete", "entrega",
        "parcel", "pagamento", "pagar", "pix", "boleto", "cartao",
        "whatsapp", "telefone", "contato", "privacidade", "dados pessoais",
        "promoc", "desconto", "aberto", "abre", "fecha", "feriado",
    ))


def _required_tool(message: str, history: list[dict[str, str]]) -> str | None:
    if _requires_policy_lookup(message):
        return "search_store_policies"
    # A short answer about purchase channel/receipt keeps the return-policy
    # context, but a generic greeting or thanks must not force another lookup.
    if re.search(r"\b(online|presencial|recebi|recebido|chegou)\b", _normalize(message)):
        for previous in reversed(history[-12:]):
            if previous.get("role") != "user":
                continue
            if any(token in _normalize(previous["content"]) for token in ("devol", "troca", "arrepend")):
                return "search_store_policies"
    if _requires_catalog_lookup(message):
        return "search_products"
    return None


def _return_clarification(message: str, history: list[dict[str, str]]) -> tuple[str, str] | None:
    """Control two missing fields in an explicit regret conversation.

    This conservative phrase matching is not a general intent/date parser or an
    eligibility engine. Only customer messages can supply purchase facts.
    """
    customer_messages = [_normalize(item["content"]) for item in history[-12:] if item.get("role") == "user"]
    customer_messages.append(_normalize(message))
    regret_indices = [index for index, text in enumerate(customer_messages) if "arrepend" in text]
    if not regret_indices:
        return None
    context = customer_messages[regret_indices[-1]:]
    if any("defeit" in text for text in context):
        return None
    channel = None
    for text in context:
        if "nao" in text:
            continue
        if re.search(r"\b(foi online|comprei online|compra online|compra foi online|pela internet|no site)\b", text) or text.strip(".!? ") == "online":
            channel = "online"
        elif re.search(r"\b(presencial|loja fisica)\b", text):
            channel = "in_store"
    if channel is None:
        return "purchase_channel", "Entendo. Para te orientar pela política certa, a compra foi online ou na loja física?"
    if channel == "online":
        receipt_date_known = any(
            "nao" not in text and re.search(r"\b(recebi|recebido|chegou)\b.*\b(ontem|hoje|anteontem|\d+)\b", text)
            for text in context
        )
        if not receipt_date_known:
            return "receipt_date", "Entendi, foi online. Para conferir o prazo na política da loja, preciso da data de recebimento. Quando você recebeu o instrumento?"
    return None
