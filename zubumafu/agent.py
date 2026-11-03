"""One bounded Ollama tool-calling cycle; no arbitrary tool execution."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any

from .catalog import _normalize, search_products
from .policies import search_store_policies
from .pricing import get_product_pricing
from .orders import bound_order_lookup, get_order_status, order_context, render_order_result
from .persona import SYSTEM_PROMPT
from .input_understanding import is_greeting, normalize_intent
from .response_quality import (clean_display_text, clean_model_answer, outside_scope, render_catalog, render_pricing,
                               requested_budget, referenced_strings, lookup_referenced_strings)


MODEL = "qwen3:4b"
TOOLS = {"search_products": search_products, "search_store_policies": search_store_policies,
         "get_product_pricing": get_product_pricing, "get_order_status": get_order_status}
TOOL_CYCLE_LIMIT = 3


def respond(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    chat_fn: Callable[..., Any] | None = None,
    *, on_event: Callable[[dict], None] | None = None,
) -> tuple[str, list[dict[str, object]]]:
    """Reply with optional live workflow/verified-output events, never reasoning."""
    def emit(event: dict) -> None:
        if on_event:
            if event['type'] == 'answer':
                event = {**event, 'text': clean_display_text(event['text'])}
            on_event(event)
    emit({'type': 'stage', 'label': 'Lendo sua mensagem'})
    reply, trace = _respond(user_message, history, chat_fn, emit)
    reply = clean_display_text(reply)
    emit({'type': 'answer', 'text': reply, 'complete': True})
    return reply, trace


def _respond(
    user_message: str,
    history: list[dict[str, str]] | None,
    chat_fn: Callable[..., Any] | None,
    emit: Callable[[dict], None],
) -> tuple[str, list[dict[str, object]]]:
    """Return a source-backed reply and query/reference/clarification metadata.

    The caller owns the visible conversation history. Ollama message objects and
    tool responses are local to this one call, not persisted between sessions.
    """
    if is_greeting(user_message):
        return ("Oi! Como posso ajudar?" if history else
                "Oi! Sou o Zubumafu, assistente do Empório da Música. Como posso ajudar?"), []
    if outside_scope(user_message):
        return "Meu foco é ajudar com instrumentos musicais e o atendimento do Empório da Música. Posso ajudar com algo da loja?", []
    string_reference = referenced_strings(user_message, history or [])
    if string_reference is not None:
        emit({'type': 'stage', 'label': 'Consultando as opções anteriores'})
        # A narrow reference/filter operation is deterministic. Re-query real
        # records without waiting for the model to repeat a known lookup.
        try:
            result = json.loads(lookup_referenced_strings(string_reference))
            if 'error' in result:
                raise ValueError('reference lookup failed')
        except (TypeError, ValueError, OSError):
            return "Não consegui consultar essas opções agora. Tente novamente, por favor.", [{'tool': 'search_products', 'status': 'error', 'invoked_by': 'application_reference_lookup'}]
        proof = [{key: item[key] for key in ('product_id', 'name', 'category', 'final_price_brl', 'specs')} for item in result['products']]
        return render_catalog(result), [{'tool': 'search_products', 'status': 'ok',
            'source': result['source'], 'filters': result['filters'], 'matches': result['total_matches'],
            'reference_products': proof, 'invoked_by': 'application_reference_lookup',
            'reply_origin': 'python_catalog_result_template'}]
    trace: list[dict[str, object]] = []
    order_input = order_context(user_message, history or [])
    required_tool = "get_order_status" if order_input is not None else _required_tool(user_message, history or [])
    if required_tool == "product_pricing":
        single_price = not re.search(r"\b(quais|opcoes|modelos|instrumentos|violoes|guitarras)\b", _normalize(user_message))
        tool_names = ["get_product_pricing"] if single_price else ["get_product_pricing", "search_products"]
    elif required_tool in TOOLS:
        tool_names = [required_tool]
    else:
        tool_names = list(TOOLS)
    # Known educational music questions need no store/customer lookup. Only
    # this source-free branch can reveal streamed final model text.
    musical_explanation = required_tool is None and order_input is None and any(
        word in _normalize(user_message) for word in ('ritmo', 'praticar', 'harmonia', 'acorde', 'escala musical'))
    if musical_explanation:
        tool_names = []
    messages: list[Any] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    messages.extend((history or [])[-12:])
    messages.append({'role': 'user', 'content': user_message + '\n/no_think'})
    if chat_fn is None:
        from .model import create_chat
        chat_fn = create_chat(
            on_progress=lambda: emit({'type': 'progress'}),
            on_text=(lambda text: emit({'type': 'answer', 'text': text, 'complete': False}))
                    if musical_explanation else None,
        )
    order_result = None
    catalog_result = pricing_result = None

    for attempt in range(TOOL_CYCLE_LIMIT):
        policy_clarification = _verified_return_clarification(user_message, history or [], trace)
        product_template = required_tool in {None, 'product_pricing', 'search_products'} and (
            catalog_result is not None or (pricing_result is not None and
            pricing_result.get('status') in {'ok', 'missing_product', 'not_found', 'ambiguous_product'}))
        template_ready = order_result is not None or product_template or policy_clarification is not None
        request_messages = messages
        if template_ready:
            # Results still go back to the real model. Python already owns this
            # reply; avoid generating a long draft that will be discarded.
            request_messages = [*messages, {'role': 'system', 'content': (
                'Os resultados verificados serão apresentados diretamente pelo código. '
                'Não reescreva os dados nem faça outra consulta. Responda somente OK. /no_think')}]
        emit({'type': 'stage', 'label': 'Conferindo os resultados' if template_ready else 'Preparando a resposta'})
        try:
            response = chat_fn(
                model=os.environ.get("OLLAMA_MODEL", MODEL),
                messages=request_messages,
                tools=[] if template_ready else [TOOLS[name] for name in tool_names],
                think=False,
                stream=False,
                options={"temperature": 0.3, "num_ctx": 4096, "num_predict": 64 if template_ready else 2048},
            )
        except (ConnectionError, TimeoutError, OSError):
            return "Não consegui acessar o Ollama agora. Confira se ele está aberto e tente novamente.", trace
        message = response.message
        calls = getattr(message, "tool_calls", None) or []
        if not calls:
            # Order drafts never supply customer-visible details, including
            # when a model hallucinates after verification fails or truncates.
            if order_result is not None:
                for item in trace:
                    if item["tool"] == "get_order_status":
                        item["reply_origin"] = "python_order_result_template"
                return render_order_result(order_result), trace
            if any(item["tool"] == "get_order_status" for item in trace):
                return "Não consegui consultar esse pedido agora. Tente novamente, por favor.", trace
            if order_input is not None and not all(order_input.values()):
                # Missing credentials require only a question, never a lookup
                # revealing whether an order exists. No model tool call claimed.
                return render_order_result(json.loads(get_order_status(**order_input))), trace
            accepted_tools = ({"get_product_pricing", "search_products"}
                              if required_tool == "product_pricing" else {required_tool})
            confirmed_lookup = any(
                item["status"] == "ok" and (required_tool is None or item["tool"] in accepted_tools)
                for item in trace
            )
            if required_tool in {None, "product_pricing", "search_products"}:
                if pricing_result is not None and (confirmed_lookup or pricing_result.get("status") in {"missing_product", "not_found", "ambiguous_product"}):
                    _mark_reply_origin(trace, "get_product_pricing", "python_pricing_result_template")
                    return render_pricing(pricing_result, requested_budget(user_message)), trace
                if catalog_result is not None and confirmed_lookup:
                    _mark_reply_origin(trace, "search_products", "python_catalog_result_template")
                    return render_catalog(catalog_result), trace
            if not confirmed_lookup and (required_tool or trace):
                if attempt == 0 and not trace:
                    # One bounded repair when the model answers from history
                    # without requesting the fresh source required for this turn.
                    reminder_tools = ", ".join(tool_names)
                    messages.append({"role": "system", "content": (
                        "A resposta ainda não foi verificada. Antes de responder à última pergunta, "
                        f"faça uma consulta nova usando {reminder_tools}. "
                        "Resolva o modelo específico pelo histórico e consulte seu nome completo. "
                        "Não basta reutilizar preços ou regras de uma mensagem anterior."
                    )})
                    continue
                return "Não consegui confirmar essa informação nos arquivos da loja. A consulta aos arquivos falhou ou não foi executada. Pode tentar reformular a pergunta?", trace
            if policy_clarification is not None and required_tool == 'search_store_policies':
                field, content = policy_clarification
                for item in trace:
                    if item['tool'] == 'search_store_policies' and item['status'] == 'ok':
                        item.update(clarification_field=field, reply_origin='source_verified_clarification_template')
                return clean_model_answer(_with_policy_sources(content, trace)), trace
            content = _visible_content(getattr(message, "content", None) or "")
            if getattr(response, "done_reason", None) == "length":
                return "Não consegui concluir a resposta. Vamos tentar uma pergunta mais específica?", trace
            if not content:
                return "Não consegui preparar uma resposta agora. Tente novamente, por favor.", trace
            return clean_model_answer(_with_policy_sources(content, trace)), trace

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
            tool_labels = {'search_products': 'Consultando o catálogo',
                           'get_product_pricing': 'Conferindo preços e descontos',
                           'search_store_policies': 'Consultando o manual da loja',
                           'get_order_status': 'Conferindo os dados do pedido'}
            emit({'type': 'stage', 'label': tool_labels.get(name, 'Verificando a consulta')})
            arguments = call.function.arguments or {}
            overrides = []
            normalized_message = _normalize(user_message)
            if name in {"search_products", "get_product_pricing"} and isinstance(arguments, dict):
                if name == 'search_products' and arguments.get('query') and arguments.get('category'):
                    category_named = any(word in normalized_message for word in (
                        'violao', 'violoes', 'guitarra', 'baixo', 'bateria', 'teclado', 'piano',
                        'ukulele', 'violino', 'saxofone', 'flauta', 'trompete', 'cordas orquestrais'))
                    if not category_named:
                        arguments = {**arguments, 'category': ''}
                        overrides.append('category')
                if re.search(r"\b(no pix|via pix|por pix|pelo pix)\b", normalized_message) and not re.search(r"\b(sem pix|nao quero|nao vou)\b", normalized_message):
                    if arguments.get("payment_method") != "pix":
                        arguments = {**arguments, "payment_method": "pix"}
                        overrides.append("payment_method")
            if name not in TOOLS:
                result = json.dumps({"error": "unknown tool"})
                trace.append({"tool": name, "status": "rejected"})
            else:
                try:
                    if name == "get_order_status":
                        result = bound_order_lookup(arguments, order_input)
                    else:
                        result = TOOLS[name](**arguments)
                    decoded = json.loads(result)
                    if name == "get_order_status":
                        order_result = decoded
                        status = decoded["status"] if decoded["status"] in {"verified", "needs_input"} else "error"
                    else:
                        status = "ok" if "error" not in decoded and decoded.get("status", "ok") == "ok" else "error"
                    if name == "search_products":
                        catalog_result = decoded if status == "ok" else None
                    elif name == "get_product_pricing":
                        pricing_result = decoded
                    sections = decoded.get("sections", [])
                    trace.append({
                        "tool": name,
                        "status": status,
                        "matches": decoded.get("total_matches", 1 if decoded.get("product_id") else len(sections)),
                        "filters": decoded.get("filters"),
                        "source": decoded.get("source", decoded.get("source_file")),
                        "sources": decoded.get("sources"),
                        "promotion_source": decoded.get("promotion_source"),
                        "product_id": decoded.get("product_id"),
                        "pricing": decoded.get("pricing"),
                        "price_quotes": _price_quotes(decoded),
                        "order_id": decoded.get("order_id"),
                        "next_field": decoded.get("next_field"),
                        "source_type": decoded.get("source_type"),
                        "argument_overrides": overrides,
                        "topic": decoded.get("topic"),
                        "pages": sorted({page for section in sections for page in section["pages"]}),
                        "chapters": [section["chapter"] for section in sections],
                        "references": [{"chapter": section["chapter"], "pages": section["pages"]} for section in sections],
                        "ambiguities": decoded.get("ambiguities", []),
                    })
                    # Show actual verified text as soon as it is available,
                    # while the bounded tool-result round-trip completes.
                    preview = None
                    if len(calls) == 1:
                        if name == 'search_products' and status == 'ok' and required_tool in {None, 'product_pricing', 'search_products'}:
                            preview = render_catalog(decoded)
                        elif name == 'get_product_pricing' and required_tool in {None, 'product_pricing', 'search_products'}:
                            preview = render_pricing(decoded, requested_budget(user_message))
                        elif name == 'get_order_status':
                            preview = render_order_result(decoded)
                        elif name == 'search_store_policies' and required_tool == 'search_store_policies':
                            clarification = _verified_return_clarification(user_message, history or [], trace)
                            if clarification:
                                preview = _with_policy_sources(clarification[1], trace)
                    if preview:
                        emit({'type': 'answer', 'text': preview, 'complete': False})
                except (TypeError, ValueError, OSError) as exc:
                    result = json.dumps({"error": type(exc).__name__})
                    trace.append({"tool": name, "status": "error"})
            messages.append({"role": "tool", "tool_name": name, "content": result})

    return "A consulta ficou mais complexa do que o esperado. Vamos tentar uma pergunta mais específica?", trace


def _verified_return_clarification(message: str, history: list[dict], trace: list[dict]):
    if any(item['tool'] == 'search_store_policies' and item['status'] == 'ok'
           and item.get('topic') == 'returns' and 4 in item.get('chapters', []) for item in trace):
        return _return_clarification(message, history)
    return None


def _with_policy_sources(content: str, trace: list[dict]) -> str:
    notes = []
    for item in trace:
        if item['tool'] != 'search_store_policies' or item['status'] != 'ok':
            continue
        for reference in item.get('references', []):
            pages = ', '.join(str(page) for page in reference['pages'])
            note = f"Manual de políticas v2.1, seção(ões) {reference['chapter']}, página(s) {pages}"
            if note not in notes:
                notes.append(note)
    return content + ('\n\n*Fonte consultada: ' + '; '.join(notes) + '.*' if notes else '')


def _mark_reply_origin(trace: list[dict], tool: str, origin: str) -> None:
    for item in trace:
        if item["tool"] == tool:
            item["reply_origin"] = origin


def _price_quotes(result: dict) -> list[dict]:
    """Keep compact verified price facts for completing a single-model quote."""
    records = result.get("products", [])
    if "pricing" in result:
        records = [{"product_id": result["product_id"], **result["pricing"]}]
    quotes = []
    for record in records:
        if record.get("pricing_status", record.get("status")) != "ok":
            continue
        quotes.append({
            "product_id": record["product_id"],
            "list_price_display_brl": record.get("list_price_display_brl", record.get("price_display_brl")),
            "final_price_display_brl": record["final_price_display_brl"],
            "discount_percent": record["discount_percent"],
            "discount_type": record["discount_type"],
        })
    return quotes


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
    normalized = normalize_intent(message)
    return any(token in normalized for token in (
        "preco", "custa", "estoque", "disponiv", "catalogo", "r$",
        "violao", "violoes", "guitarra", "ukulele", "baixo", "bateria",
        "teclado", "piano", "violino", "violoncelo", "flauta", "saxofone",
        "trompete", "instrumento", "modelo",
        "voces tem", "voces vendem",
    ))


def _requires_policy_lookup(message: str) -> bool:
    normalized = normalize_intent(message)
    return any(token in normalized for token in (
        "devol", "troca", "arrepend", "defeit", "garantia", "horar",
        "funcionamento", "endereco", "onde fica", "frete", "entrega",
        "parcel", "pagamento", "pagar", "pix", "boleto", "cartao",
        "whatsapp", "telefone", "contato", "privacidade", "dados pessoais",
        "promoc", "desconto", "aberto", "abre", "fecha", "feriado",
    ))


def _required_tool(message: str, history: list[dict[str, str]]) -> str | None:
    normalized = normalize_intent(message)
    # Product prices can be grounded in either deterministic catalog prices or
    # the dedicated pricing tool. General payment policy still needs the PDF.
    policy_subject = any(token in normalized for token in (
        "devol", "troca", "arrepend", "defeit", "garantia", "frete",
        "entrega", "parcel", "horar", "endereco", "telefone", "privacidade",
    ))
    product_context = _requires_catalog_lookup(message) or any(
        _requires_catalog_lookup(item.get("content", "")) for item in history[-4:]
    )
    if not policy_subject and (
        any(token in normalized for token in ("custa", "preco"))
        or (product_context and any(token in normalized for token in ("pix", "desconto", "promoc", "mais barato")))
        or (product_context and "orcamento" in normalized and re.search(r"\b(esse|essa|ele|ela)\b", normalized))
    ):
        return "product_pricing"
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
