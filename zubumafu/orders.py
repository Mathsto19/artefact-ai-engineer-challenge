"""Read-only, demonstrative order lookup with a Python-side identity match.

Order number plus registered email is NOT production authentication. Never
return order data until the order -> customer -> email association succeeds.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from .catalog import _normalize
from .pricing import display_brl


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ORDERS_FILE = DATA_DIR / "desafio_tecnico_ai_eng - orders.csv"
CUSTOMERS_FILE = DATA_DIR / "desafio_tecnico_ai_eng - customers.csv"
ORDER_ITEMS_FILE = DATA_DIR / "desafio_tecnico_ai_eng - order_items.csv"
PRODUCTS_FILE = DATA_DIR / "desafio_tecnico_ai_eng - products.csv"

_NOT_VERIFIED = {
    "status": "not_verified",
    "message": (
        "Não consegui confirmar esse pedido com o número e o e-mail informados. "
        "Confira os dois dados e tente novamente, por favor."
    ),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@lru_cache(maxsize=1)
def _order_records() -> tuple[
    dict[str, dict[str, str]],
    dict[str, dict[str, str]],
    dict[str, list[dict[str, str]]],
    dict[str, str],
]:
    """Index original snapshots without modifying them or calculating prices."""
    orders = {row["order_id"]: row for row in _read_csv(ORDERS_FILE)}
    customers = {row["customer_id"]: row for row in _read_csv(CUSTOMERS_FILE)}
    items: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_csv(ORDER_ITEMS_FILE):
        items[row["order_id"]].append(row)
    products = {row["product_id"]: row["name"] for row in _read_csv(PRODUCTS_FILE)}
    return orders, customers, dict(items), products


def get_order_status(order_id: str = "", email: str = "") -> str:
    """Look up a historical order only after matching its registered email.

    Args:
        order_id: Customer-provided order number; leave blank to request it first.
        email: Email registered for that order; leave blank to request it second.

    Returns:
        A JSON string with exactly one missing-field question, a generic
        unsuccessful-verification result, or verified historical order details.
        Matching the two values is demonstrative and NOT secure authentication.
        No live carrier lookup, cancellations or order mutations are performed.
    """
    if order_id is None or (isinstance(order_id, str) and not order_id.strip()):
        return json.dumps({
            "status": "needs_input",
            "next_field": "order_id",
            "message": "Claro, posso consultar o registro do pedido. Qual é o número do pedido?",
        }, ensure_ascii=False)

    # Do not interpret scientific notation, fractional numbers or booleans as IDs.
    if isinstance(order_id, bool) or not isinstance(order_id, (str, int)):
        return json.dumps(_NOT_VERIFIED, ensure_ascii=False)
    normalized_id = str(order_id).strip()
    if not re.fullmatch(r"[1-9][0-9]*", normalized_id):
        return json.dumps(_NOT_VERIFIED, ensure_ascii=False)

    if email is None or (isinstance(email, str) and not email.strip()):
        return json.dumps({
            "status": "needs_input",
            "next_field": "email",
            "message": "Obrigado! Agora, qual é o e-mail cadastrado nesse pedido?",
        }, ensure_ascii=False)
    if not isinstance(email, str):
        return json.dumps(_NOT_VERIFIED, ensure_ascii=False)

    try:
        orders, customers, order_items, product_names = _order_records()
    except (OSError, ValueError, KeyError):
        return json.dumps({"status": "source_error", "message": "Não consegui ler o registro desse pedido agora."}, ensure_ascii=False)
    order = orders.get(normalized_id)
    if order is None:
        return json.dumps(_NOT_VERIFIED, ensure_ascii=False)
    customer = customers.get(order["customer_id"])
    if customer is None or customer["email"].strip().casefold() != email.strip().casefold():
        return json.dumps(_NOT_VERIFIED, ensure_ascii=False)

    # Only beyond this point may any order-specific value be returned.
    try:
        recorded_total = Decimal(order["total_brl"])
        if not recorded_total.is_finite() or recorded_total < 0:
            raise InvalidOperation
        lines = [
            {
                "product_name": product_names.get(row["product_id"], "Produto sem nome no catálogo"),
                "quantity": int(row["quantity"]),
            }
            for row in order_items.get(normalized_id, [])
        ]
        if any(line["quantity"] <= 0 for line in lines):
            raise ValueError("invalid quantity")
    except (InvalidOperation, ValueError, TypeError, KeyError):
        # A corrupt source row should not expose partial customer/order data.
        return json.dumps({"status": "source_error", "message": "Não consegui ler o registro desse pedido agora."}, ensure_ascii=False)

    return json.dumps({
        "status": "verified",
        "source_type": "historical_csv_snapshot_not_live_tracking",
        "order_id": normalized_id,
        "order_status": order["status"],
        "items": lines,
        "recorded_total_brl": format(recorded_total, ".2f"),
        "tracking_code": order["tracking_code"].strip() or None,
        "estimated_delivery": order["estimated_delivery"].strip() or None,
        "delivery_note": (
            "The estimated delivery is a historical forecast, not proof of actual receipt. "
            "The CSV does not include an actual receipt date or a live carrier feed."
        ),
    }, ensure_ascii=False)


_EMAIL = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
_ORDER_ID = re.compile(r"\bpedido\s*(?:(?:e|numero|nro|n)\s*)?[:#-]?\s*([1-9][0-9]*)(?![\w.-])")


def order_context(message: str, history: list[dict[str, str]]) -> dict[str, str] | None:
    """Resolve a narrow order dialogue from customer text, never assistant facts.

    Changing subject closes the flow. Changing order resets the email. This is
    deterministic demo conversation handling, not authentication or general NLU.
    """
    context = None
    for item in [*history[-12:], {"role": "user", "content": message}]:
        if item.get("role") != "user":
            continue
        raw = item.get("content", "").strip()
        # An address such as pedido999@example.invalid is an email, not an ID.
        normalized = _normalize(_EMAIL.sub(" ", raw))
        explicit = bool(re.search(r"\b(pedido|encomenda)\b|meu rastreio|rastrear minha compra", normalized))
        number = _ORDER_ID.search(normalized)
        bare_number = re.fullmatch(r"[1-9][0-9]*", raw)
        email = _EMAIL.search(raw)
        followup = any(word in normalized for word in ("rastre", "previsao", "situacao", "status", "chegar"))
        general_policy = any(word in normalized for word in ("devol", "arrepend", "troca", "garantia", "defeit"))
        lookup_request = followup or any(word in normalized for word in ("onde esta", "consultar", "acompanhar", "total"))
        if general_policy and not lookup_request:
            # Mentioning 'meu pedido' in a return-policy question must not
            # replace the existing PDF/channel/receipt clarification flow.
            context = None
            continue
        if explicit:
            found_id = number.group(1) if number else ""
            if context is None or (found_id and found_id != context["order_id"]):
                context = {"order_id": "", "email": ""}
        elif context is None or not (bare_number or email or followup):
            context = None
        if context is not None:
            new_id = number.group(1) if number else raw if bare_number else ""
            if new_id and new_id != context["order_id"]:
                context = {"order_id": new_id, "email": ""}
            if email:
                context["email"] = email.group().casefold()
    # An isolated credential after an assistant question is still sensitive,
    # but assistant text cannot provide the missing customer-supplied order ID.
    if context is None and (_EMAIL.fullmatch(message.strip()) or re.fullmatch(r"[1-9][0-9]*", message.strip())):
        previous = next((item.get("content", "") for item in reversed(history[-4:]) if item.get("role") == "assistant"), "")
        if any(fragment in _normalize(previous) for fragment in ("numero do pedido", "e-mail cadastrado nesse pedido")):
            context = {"order_id": message.strip() if message.strip().isdigit() else "",
                       "email": message.strip().casefold() if _EMAIL.fullmatch(message.strip()) else ""}
    return context


def bound_order_lookup(arguments: dict, context: dict[str, str] | None) -> str:
    """Only execute credentials that match facts supplied in this customer flow."""
    if context is None or not isinstance(arguments, dict) or any(key not in {"order_id", "email"} for key in arguments):
        return json.dumps(_NOT_VERIFIED, ensure_ascii=False)
    for key in ("order_id", "email"):
        value = arguments.get(key, "")
        if value is None or value == "":
            continue
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return json.dumps(_NOT_VERIFIED, ensure_ascii=False)
        if str(value).strip().casefold() != context[key].strip().casefold():
            return json.dumps(_NOT_VERIFIED, ensure_ascii=False)
    return get_order_status(**context)


def render_order_result(result: dict) -> str:
    """Render verified fields or a generic clarification/denial, without LLM text."""
    if result.get("status") != "verified":
        return str(result.get("message", "Não consegui consultar esse pedido agora. Tente novamente, por favor."))
    status_names = {"pending": "pendente", "confirmed": "confirmado", "shipped": "enviado",
                    "delivered": "marcado como entregue", "cancelled": "cancelado"}
    return "\n".join([
        "Conferi o registro demonstrativo do seu pedido:",
        f"**Pedido:** {result['order_id']}",
        f"**Situação registrada:** {status_names.get(result['order_status'], result['order_status'])}",
        "**Itens:**", *[f"- {line['quantity']} × {line['product_name']}" for line in result["items"]],
        f"**Total registrado na compra:** {display_brl(result['recorded_total_brl'])}",
        f"**Código de rastreamento registrado:** {result.get('tracking_code') or 'não consta no registro'}",
        f"**Previsão de entrega registrada:** {result.get('estimated_delivery') or 'não consta no registro'}",
        "*Esses dados são históricos. A previsão não confirma o recebimento; não há rastreamento ao vivo.*",
    ])
