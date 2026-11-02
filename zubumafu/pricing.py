"""Deterministic BRL prices from the supplied product and promotion snapshots."""

from __future__ import annotations

import csv
import json
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROMOTIONS_FILE = DATA_DIR / "desafio_tecnico_ai_eng - promotions.csv"
CENT = Decimal("0.01")
PIX_DISCOUNT_PERCENT = Decimal("5")  # Store policy, section 3.


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()


@lru_cache(maxsize=1)
def _promotions() -> list[dict[str, str]]:
    with PROMOTIONS_FILE.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def display_brl(value: str | Decimal) -> str:
    """Format an already calculated monetary value for customer display."""
    return "R$ " + f"{Decimal(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def calculate_price(
    list_price_brl: str | Decimal,
    promotions: Sequence[Mapping[str, str]],
    payment_method: str = "standard",
) -> dict[str, object]:
    """Pure pricing calculation for one product; no model arithmetic.

    Active promotion has priority. The 5% PIX discount applies only to a
    non-promotional table price. Rounding is applied once to the final price,
    then the displayed discount is calculated as table price minus final price.
    """
    if not isinstance(payment_method, str):
        return {"status": "error", "reason": "unsupported_payment_method"}
    method = _normalize(payment_method)
    if method not in {"standard", "pix"}:
        return {"status": "error", "reason": "unsupported_payment_method"}
    try:
        table = Decimal(str(list_price_brl))
    except (InvalidOperation, ValueError, TypeError):
        return {"status": "error", "reason": "invalid_list_price"}
    if not table.is_finite() or table < 0:
        return {"status": "error", "reason": "invalid_list_price"}

    active = [row for row in promotions if str(row.get("is_active", "")).strip() == "1"]
    if len(active) > 1:
        return {
            "status": "ambiguous",
            "reason": "multiple_active_promotions",
            "list_price_brl": _money(table),
            "active_promotion_ids": [row.get("promotion_id") for row in active],
        }

    promotion = active[0] if active else None
    try:
        percent = Decimal(str(promotion["discount_percent"])) if promotion else (
            PIX_DISCOUNT_PERCENT if method == "pix" else Decimal("0")
        )
    except (InvalidOperation, TypeError, ValueError, KeyError):
        return {"status": "error", "reason": "invalid_discount_percent"}
    if not percent.is_finite() or not Decimal("0") <= percent <= Decimal("100"):
        return {"status": "error", "reason": "invalid_discount_percent"}

    final = (table * (Decimal("100") - percent) / Decimal("100")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    discount = table.quantize(CENT, rounding=ROUND_HALF_UP) - final
    return {
        "status": "ok",
        "list_price_brl": _money(table),
        "final_price_brl": _money(final),
        "discount_amount_brl": _money(discount),
        "list_price_display_brl": display_brl(_money(table)),
        "final_price_display_brl": display_brl(_money(final)),
        "discount_amount_display_brl": display_brl(_money(discount)),
        "discount_percent": format(percent.normalize(), "f"),
        "discount_type": "promotion" if promotion else ("pix" if method == "pix" else "none"),
        "payment_method": method,
        "active_promotion": (
            {
                "promotion_id": promotion.get("promotion_id"),
                "description": promotion.get("description", ""),
                "discount_percent": format(percent.normalize(), "f"),
            }
            if promotion else None
        ),
        "pix_discount_applied": method == "pix" and promotion is None,
        "pix_non_cumulative": method == "pix" and promotion is not None,
        "promotion_validity_dates": None,
    }


def pricing_for_product(product: Mapping[str, str], payment_method: str = "standard") -> dict[str, object]:
    applicable = [
        row for row in _promotions()
        if row["product_id"] == str(product["product_id"])
    ]
    return calculate_price(product["price_brl"], applicable, payment_method)


def get_product_pricing(
    product_name: str = "",
    product_id: int = 0,
    payment_method: str = "standard",
) -> str:
    """Look up a product's original, discounted and final BRL prices from CSVs.

    Args:
        product_name: Full or partial product name; required if product_id is not known.
        product_id: Exact product ID returned by catalog search, or 0 if unknown.
        payment_method: 'standard' or 'pix' (5% only when no active promotion).

    Returns:
        JSON with the exact table price, active promotion and final price.
    """
    # Local import avoids a catalog/pricing module import cycle.
    from .catalog import _catalog

    if not isinstance(product_name, str):
        return json.dumps({"status": "error", "reason": "invalid_product_name"})
    if isinstance(product_id, bool) or not isinstance(product_id, (int, str)):
        return json.dumps({"status": "error", "reason": "invalid_product_id"})
    if not isinstance(payment_method, str) or _normalize(payment_method) not in {"standard", "pix"}:
        return json.dumps({"status": "error", "reason": "unsupported_payment_method"})
    try:
        wanted_id = int(product_id)
    except (TypeError, ValueError):
        return json.dumps({"status": "error", "reason": "invalid_product_id"})
    if wanted_id < 0:
        return json.dumps({"status": "error", "reason": "invalid_product_id"})

    products, categories = _catalog()
    if wanted_id:
        matches = [row for row in products if row["product_id"] == str(wanted_id)]
    elif _normalize(product_name):
        name = _normalize(product_name)
        matches = [row for row in products if name in _normalize(row["name"])]
        exact = [row for row in matches if name == _normalize(row["name"])]
        matches = exact or matches
    else:
        return json.dumps({"status": "missing_product", "message": "Ask which instrument the customer means."})

    if not matches:
        return json.dumps({"status": "not_found", "message": "Product not found in the supplied catalog."})
    if len(matches) > 1:
        return json.dumps({
            "status": "ambiguous_product",
            "message": "Ask the customer to specify the exact model.",
            "candidates": [{"product_id": row["product_id"], "name": row["name"]} for row in matches[:10]],
        }, ensure_ascii=False)

    product = matches[0]
    pricing = pricing_for_product(product, payment_method)
    return json.dumps({
        "status": pricing["status"],
        "product_id": product["product_id"],
        "product_name": product["name"],
        "category": categories.get(product["category_id"]),
        "stock_quantity": int(product["stock_quantity"]),
        "product_status": product["status"],
        "pricing": pricing,
        "sources": [
            "data/desafio_tecnico_ai_eng - products.csv",
            "data/desafio_tecnico_ai_eng - promotions.csv",
            "data/políticas_da_loja.pdf, sections 3 and 6",
        ],
        "note": "No promotion dates are present; is_active is the only activity indicator. Do not stack PIX with an active promotion.",
    }, ensure_ascii=False)
