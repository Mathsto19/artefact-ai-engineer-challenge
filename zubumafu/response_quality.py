"""Small, testable response guards for the most visible model failure modes.

These renderers consume only verified tool payloads, never model-invented
catalog types, discounts, delivery dates or customer records.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .pricing import display_brl


def money_brl(value: str) -> str:
    return display_brl(value).removeprefix("R$ ")


def render_catalog(payload: dict[str, Any]) -> str:
    """Neutral, source-verified suggestions; no arbitrary 'best' ranking."""
    products = payload.get("products") or []
    count = payload.get("total_matches", 0)
    filters = payload.get("filters") or {}
    if not products:
        reason = payload.get("no_match_reason")
        if reason == "not_in_catalog":
            return "Não localizei esse modelo no catálogo fornecido. Pode conferir o nome ou a marca?"
        if reason == "unavailable":
            return "Encontrei esse produto no catálogo, mas ele não está disponível no estoque demonstrativo."
        if reason == "over_budget":
            return "Há produtos com essas características, mas nenhum entra no orçamento informado com os preços finais registrados."
        if reason == "unconfirmed_prices":
            return "Encontrei produtos no catálogo, mas não consegui confirmar o preço final para comparar com esse orçamento."
        return "Não encontrei opções disponíveis que atendam a todos esses filtros no catálogo fornecido."

    lines = ["Encontrei opções do catálogo, ordenadas por preço final:", ""]
    for item in products[:3]:
        name = item["name"]
        specs = item.get("specs") or {}
        strings = specs.get("strings", "")
        strings_label = {"nylon": "cordas de nylon", "steel": "cordas de aço"}.get(str(strings).casefold())
        final = item.get("final_price_brl")
        table = item.get("price_brl")
        if item.get("pricing_status") == "ok" and final:
            price = f"R$ {money_brl(final)}"
            if table and Decimal(str(final)) != Decimal(str(table)):
                price += f" (tabela: R$ {money_brl(table)}; desconto de {item['discount_percent']}%)"
        else:
            price = "preço final não confirmado"
        descriptors = [price]
        if strings_label:
            descriptors.append(strings_label)
        available = item.get("status") == "active" and int(item.get("stock_quantity", 0)) > 0
        descriptors.append(f"{item['stock_quantity']} unidade(s) no estoque demonstrativo" if available else "sem disponibilidade no estoque demonstrativo")
        if item.get("pix_non_cumulative"):
            descriptors.append("sem desconto PIX adicional: os descontos não acumulam")
        lines.append(f"- **{name}** — {' · '.join(descriptors)}")

    budget = Decimal(str(filters.get('max_price_brl', '0')))
    if budget > 0:
        lines.extend(["", f"As opções mostradas cabem no orçamento de {display_brl(budget)}."])
    lines.extend(["", f"*Mostrei {min(3, len(products))} de {count} resultado(s) do arquivo; preços e estoque são demonstrativos, não consultas ao vivo.*"])
    return "\n".join(lines)


def render_pricing(payload: dict[str, Any], budget: Decimal | None = None) -> str:
    """Explain discount non-cumulativity without tempting extra PIX savings."""
    status = payload.get("status")
    if status == "missing_product":
        return "Qual é o modelo exato do instrumento para eu consultar o preço no catálogo?"
    if status == "not_found":
        return "Não encontrei esse modelo no catálogo fornecido. Pode conferir o nome?"
    if status == "ambiguous_product":
        options = [str(p.get("name")) for p in payload.get("candidates", [])[:3]]
        return "Encontrei mais de um modelo parecido. Qual deles você quer consultar? " + "; ".join(options)
    pricing = payload.get("pricing") or {}
    if status != "ok" or pricing.get("status") != "ok":
        return "Não consegui confirmar o preço final desse modelo agora. Pode tentar novamente?"

    name = payload["product_name"]
    original = f"R$ {money_brl(pricing['list_price_brl'])}"
    final = f"R$ {money_brl(pricing['final_price_brl'])}"
    discount = str(pricing.get("discount_percent", "0"))
    lines = [f"**{name}**", f"Preço de tabela: **{original}**."]
    if pricing.get("active_promotion"):
        lines.append(f"Promoção ativa no arquivo: **{discount}% de desconto**. Preço final: **{final}**.")
        if pricing.get("payment_method") == "pix":
            lines.append("**No PIX, o valor permanece o mesmo:** o desconto PIX de 5% não acumula com a promoção.")
    elif pricing.get("discount_type") == "pix":
        lines.append(f"Pagamento por PIX: **5% de desconto**, resultando em **{final}**.")
    else:
        lines.append(f"Preço final registrado: **{final}** (sem promoção ativa aplicada).")
    if payload.get("product_status") != "active" or int(payload.get("stock_quantity", 0)) < 1:
        lines.append("*Atenção: o produto não está disponível no estoque demonstrativo.*")
    lines.append("*Condição consultada nos arquivos fornecidos, sem data de validade informada.*")
    if budget is not None:
        if Decimal(pricing['final_price_brl']) <= budget:
            lines.append(f"Sim, o preço final de {final} cabe no orçamento de {display_brl(budget)}.")
        else:
            lines.append(f"O preço final de {final} ultrapassa o orçamento de {display_brl(budget)}.")
    return "\n".join(lines)


def requested_budget(message: str) -> Decimal | None:
    """Read one explicit BRL budget; ambiguous/multiple amounts are not guessed."""
    from .catalog import _normalize
    if not any(word in _normalize(message) for word in ('orcamento', 'limite', 'ate')):
        return None
    values = re.findall(r'R\$\s*(\d[\d.,]*)', message, flags=re.IGNORECASE)
    if len(values) != 1:
        return None
    value = values[0].rstrip('.,')
    if ',' in value:
        value = value.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', value):
        value = value.replace('.', '')
    try:
        budget = Decimal(value)
    except InvalidOperation:
        return None
    return budget if budget.is_finite() and budget >= 0 else None


def referenced_strings(message: str, history: list[dict]) -> dict | None:
    """Resolve a nylon/steel follow-up to the previously displayed model names."""
    from .catalog import _normalize
    normalized = _normalize(message)
    if not re.search(r'\b(dessas|desses|dessas opcoes|desses modelos)\b', normalized):
        return None
    material = 'steel' if 'aco' in normalized else 'nylon' if 'nylon' in normalized else None
    previous = next((item['content'] for item in reversed(history[-4:]) if item.get('role') == 'assistant'), '')
    if not material or not previous.startswith('Encontrei opções do catálogo, ordenadas por preço final:'):
        return None
    names = re.findall(r'^- \*\*(.+?)\*\* — ', previous, flags=re.MULTILINE)[:3]
    customer = next((item['content'] for item in reversed(history[-4:]) if item.get('role') == 'user'), '')
    method = 'pix' if 'pix' in _normalize(customer) and 'sem pix' not in _normalize(customer) else 'standard'
    return {'names': names, 'material': material, 'budget': requested_budget(customer), 'payment_method': method} if names else None


def lookup_referenced_strings(reference: dict, payment_method: str | None = None) -> str:
    """Re-query each named instrument; visible history never supplies its specs."""
    import json
    from .catalog import search_products
    products = {}
    payload = {}
    payment_method = payment_method or reference.get('payment_method', 'standard')
    for name in reference['names']:
        payload = json.loads(search_products(query=name, available_only=False,
                           max_price_brl=reference['budget'] or 0, payment_method=payment_method))
        if 'error' in payload:
            return json.dumps(payload, ensure_ascii=False)
        for item in payload['products']:
            if item['name'] == name and item['specs'].get('strings') == reference['material']:
                products[item['product_id']] = item
    records = sorted(products.values(), key=lambda item: Decimal(item['final_price_brl'] or item['price_brl']))
    payload.update(products=records, total_matches=len(records), shown_matches=len(records),
                   no_match_reason=None if records else 'no_filters_match')
    payload['filters'].update(query='', reference_names=reference['names'], strings_material=reference['material'])
    return json.dumps(payload, ensure_ascii=False)


_GENERIC_INVITATION = re.compile(
    r"(?i)^\s*(?:se quiser[, ]|quer que eu |posso te ajudar |gostaria que eu |me diga se )"
)
_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u200d\ufe0e\ufe0f\u20e3\U000E0020-\U000E007F]")
_OUTSIDE = re.compile(
    r"(?i)\b(?:previsão do tempo|qual (?:é )?o clima|resultado do futebol|"
    r"cotação do bitcoin|capital da frança|receita de bolo|imposto de renda|"
    r"me ajude a programar|escreva um código python)\b"
)


def outside_scope(message: str) -> bool:
    """Handle clear examples only; let other intents reach the model."""
    return bool(_OUTSIDE.search(message))


def strip_emojis(content: str) -> str:
    """Remove emoji characters and sequence joiners, retaining ordinary text."""
    return _EMOJI.sub("", content).strip()


def clean_model_answer(content: str) -> str:
    """Strip rendered thought tags, repeated boilerplate and all emojis."""
    content = re.sub(r"(?is)<think\b[^>]*>.*?</think\s*>", "", content or "")
    content = re.sub(r"(?is)<think\b[^>]*>.*\Z", "", content)
    lines = []
    saw_invitation = False
    for line in content.strip().splitlines():
        if _GENERIC_INVITATION.match(line):
            if saw_invitation:
                continue
            saw_invitation = True
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    return strip_emojis(cleaned)
