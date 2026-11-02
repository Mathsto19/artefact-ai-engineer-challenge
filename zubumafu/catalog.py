"""Read-only search over the unmodified products/categories CSV snapshots."""

from __future__ import annotations

import csv
import json
import unicodedata
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from .pricing import display_brl, pricing_for_product

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRODUCTS_FILE = DATA_DIR / "desafio_tecnico_ai_eng - products.csv"
CATEGORIES_FILE = DATA_DIR / "desafio_tecnico_ai_eng - categories.csv"


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold().strip()


@lru_cache(maxsize=1)
def _catalog() -> tuple[list[dict[str, str]], dict[str, str]]:
    with CATEGORIES_FILE.open(encoding="utf-8-sig", newline="") as stream:
        categories = {row["category_id"]: row["name"] for row in csv.DictReader(stream)}
    with PRODUCTS_FILE.open(encoding="utf-8-sig", newline="") as stream:
        products = list(csv.DictReader(stream))
    return products, categories


_ALIASES = {
    "violao": "violoes",
    "violoes": "violoes",
    "guitarra": "guitarras",
    "guitarras": "guitarras",
    "baixo": "baixos",
    "contrabaixo": "baixos",
    "bateria": "baterias e percussao",
    "teclado": "teclados e pianos",
    "piano": "teclados e pianos",
    "ukulele": "ukuleles",
    "violino": "cordas orquestrais",
}


def _category_match(requested: str, category_name: str) -> bool:
    if not requested:
        return True
    requested = _ALIASES.get(_normalize(requested), _normalize(requested))
    actual = _normalize(category_name)
    return requested == actual or requested in actual


def search_products(
    category: str = "",
    query: str = "",
    max_price_brl: float = 0,
    available_only: bool = True,
    payment_method: str = "standard",
) -> str:
    """Search the store's CSV product catalog using category, description/name and maximum BRL price.

    Args:
        category: Instrument category in Portuguese, such as 'violão', 'guitarra' or 'ukulele'.
        query: Optional model name, brand, technical feature or musical genre to match.
        max_price_brl: Maximum FINAL price in BRL, after eligible discounts. Use 0 for no budget.
        available_only: True to return only active products with positive stock.
        payment_method: 'standard' or 'pix'; PIX is not stacked with an active promotion.

    Returns:
        A JSON string containing matched product records, source and filters.
    """
    if not isinstance(category, str) or not isinstance(query, str):
        return json.dumps({"error": "category and query must be strings"})
    if not isinstance(available_only, bool):
        return json.dumps({"error": "available_only must be a boolean"})
    if not isinstance(payment_method, str) or _normalize(payment_method) not in {"standard", "pix"}:
        return json.dumps({"error": "payment_method must be standard or pix"})
    payment_method = _normalize(payment_method)
    if isinstance(max_price_brl, bool):
        return json.dumps({"error": "max_price_brl must be a number"})
    try:
        budget = Decimal(str(max_price_brl))
    except (InvalidOperation, TypeError, ValueError):
        return json.dumps({"error": "invalid max_price_brl"})
    if not budget.is_finite() or budget < 0:
        return json.dumps({"error": "max_price_brl must be nonnegative and finite"})

    products, categories = _catalog()
    results: list[dict[str, object]] = []
    term = _normalize(query)
    query_matches = source_matches = available_candidates = over_budget = unconfirmed_prices = 0
    for product in products:
        name = product["name"]
        description = product["description"]
        category_name = categories.get(product["category_id"], "Unknown")
        if term and term not in _normalize(name + " " + description + " " + product["specs"]):
            continue
        query_matches += 1
        if not _category_match(category, category_name):
            continue
        source_matches += 1
        try:
            price = Decimal(product["price_brl"])
            stock = int(product["stock_quantity"])
        except (InvalidOperation, ValueError):
            continue
        if available_only and (product["status"] != "active" or stock <= 0):
            continue
        available_candidates += 1
        pricing = pricing_for_product(product, payment_method)
        # A missing/ambiguous final price cannot be advertised as within budget.
        if budget:
            if pricing["status"] != "ok":
                unconfirmed_prices += 1
                continue
            if Decimal(pricing["final_price_brl"]) > budget:
                over_budget += 1
                continue
        try:
            specs = json.loads(product["specs"]) if product["specs"] else {}
        except json.JSONDecodeError:
            specs = {}
        results.append({
            "product_id": product["product_id"],
            "name": name,
            "category": category_name,
            "price_brl": str(price.quantize(Decimal("0.01"))),
            "price_display_brl": display_brl(price),
            "pricing_status": pricing["status"],
            "final_price_brl": pricing.get("final_price_brl"),
            "final_price_display_brl": pricing.get("final_price_display_brl"),
            "discount_percent": pricing.get("discount_percent"),
            "discount_type": pricing.get("discount_type"),
            "active_promotion": pricing.get("active_promotion"),
            "pix_discount_applied": pricing.get("pix_discount_applied"),
            "pix_non_cumulative": pricing.get("pix_non_cumulative"),
            "stock_quantity": stock,
            "status": product["status"],
            "description": description,
            "specs": specs,
        })
    results.sort(key=lambda item: (Decimal(str(item["final_price_brl"] or item["price_brl"])), str(item["name"])))
    payload = {
        "source": "data/desafio_tecnico_ai_eng - products.csv",
        "source_type": "provided_snapshot_not_live_inventory",
        "promotion_source": "data/desafio_tecnico_ai_eng - promotions.csv",
        "pricing_note": "price_brl is the original price; budget filtering and ordering use final_price_brl. Only is_active indicates promotion activity; dates are unavailable. PIX does not stack with promotions. Do not quote a final price when pricing_status is not ok.",
        "filters": {"category": category, "query": query, "max_price_brl": str(budget), "budget_applies_to": "final_price_brl", "available_only": available_only, "payment_method": payment_method},
        "total_matches": len(results),
        "no_match_reason": (
            None if results else
            "not_in_catalog" if not query_matches and term else
            "no_category_match" if not source_matches else
            "unavailable" if available_only and not available_candidates else
            "unconfirmed_prices" if unconfirmed_prices else
            "over_budget" if over_budget else "no_filters_match"
        ),
        "shown_matches": min(len(results), 6),
        "products": results[:6],
    }
    return json.dumps(payload, ensure_ascii=False)
