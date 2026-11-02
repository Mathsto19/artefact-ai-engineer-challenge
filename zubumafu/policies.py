"""Section-based retrieval from the original store-policy PDF, with page references."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


PDF_FILE = Path(__file__).resolve().parents[1] / "data" / "políticas_da_loja.pdf"

_CHAPTER_NAMES = {
    1: "Sobre a Empório da Música",
    2: "Horário de Funcionamento",
    3: "Formas de Pagamento",
    4: "Política de Trocas e Devoluções",
    5: "Política de Frete e Entregas",
    6: "Promoções e Descontos",
    7: "Atendimento via WhatsApp",
    8: "Garantia",
    9: "Privacidade e Proteção de Dados",
    10: "Disposições Finais",
}
_HEADING_PATTERN = re.compile(
    r"(?m)^\s*(10|[1-9])\.\s+(?:"
    + "|".join(re.escape(title) for title in _CHAPTER_NAMES.values())
    + r")\s*$"
)

_TOPICS = {
    "store": (1,),
    "hours": (2,),
    "payments": (3,),
    "returns": (4,),
    "delivery": (5,),
    "promotions": (6,),
    "service": (7,),
    "warranty": (8, 4),
    "privacy": (9,),
}
_TOPIC_ALIASES = {
    "endereco": "store", "localizacao": "store", "loja": "store", "contato": "store",
    "telefone": "store", "whatsapp": "store", "store": "store",
    "horario": "hours", "horarios": "hours", "funcionamento": "hours", "hours": "hours",
    "pagamento": "payments", "pagamentos": "payments", "pix": "payments", "parcelamento": "payments", "payments": "payments",
    "troca": "returns", "devolucao": "returns", "devolucoes": "returns", "arrependimento": "returns", "returns": "returns",
    "frete": "delivery", "entrega": "delivery", "rastreamento": "delivery", "delivery": "delivery",
    "promocao": "promotions", "desconto": "promotions", "promotions": "promotions",
    "atendimento": "service", "service": "service",
    "garantia": "warranty", "warranty": "warranty",
    "privacidade": "privacy", "dados pessoais": "privacy", "privacy": "privacy",
}
_INFER_PATTERNS = (
    ("returns", ("devol", "troca", "arrepend", "defeit", "reembols", "cancelar compra")),
    ("hours", ("horar", "funcionamento", "aberto", "abre", "fecha", "feriado")),
    ("store", ("endereco", "onde fica", "localiz", "telefone", "contato", "whatsapp", "email", "e-mail")),
    ("payments", ("pagamento", "parcela", "parcelamento", "cartao", "boleto", "pix", "pagar", "6x", "12x")),
    ("delivery", ("frete", "entrega", "transportadora", "rastre", "correios", "sedex")),
    ("warranty", ("garantia",)),
    ("promotions", ("promocao", "desconto", "black friday")),
    ("privacy", ("privacidade", "lgpd", "dados pessoais")),
    ("service", ("atendimento", "reclamacao")),
)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def _clean_page(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Empório da Música Manual de Políticas e Procedimentos"):
            continue
        if re.fullmatch(r"Página\s+\d+", stripped):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def _sections() -> dict[int, list[dict[str, object]]]:
    """Split the PDF at its verified chapter titles, retaining original page indices."""
    reader = PdfReader(PDF_FILE)
    chunks: dict[int, list[dict[str, object]]] = defaultdict(list)
    active: int | None = None
    for page_number, page in enumerate(reader.pages, start=1):
        text = _clean_page(page.extract_text(extraction_mode="layout") or "")
        headings = list(_HEADING_PATTERN.finditer(text))
        if not headings:
            if active is not None and text:
                chunks[active].append({"page": page_number, "text": text})
            continue
        if active is not None and text[:headings[0].start()].strip():
            chunks[active].append({"page": page_number, "text": text[:headings[0].start()].strip()})
        for index, match in enumerate(headings):
            chapter = int(match.group(1))
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            chunks[chapter].append({"page": page_number, "text": text[match.start():end].strip()})
            active = chapter
    return dict(chunks)


def _select_topic(topic: str, question: str) -> str | None:
    key = _normalize(topic)
    if key in _TOPICS:
        return key
    if key in _TOPIC_ALIASES:
        return _TOPIC_ALIASES[key]
    text = _normalize(question)
    for candidate, patterns in _INFER_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return candidate
    return None


def search_store_policies(question: str, topic: str = "") -> str:
    """Find relevant sections of the store's policy PDF, including page references and ambiguities.

    Args:
        question: The customer's original policy question in Portuguese.
        topic: Optional topic: store, hours, payments, returns, delivery, promotions, service, warranty or privacy.

    Returns:
        A JSON string with exact PDF excerpts, chapter IDs, 1-based page references,
        conflicting rules and missing information that should be requested.
    """
    if not isinstance(question, str) or not isinstance(topic, str):
        return json.dumps({"status": "invalid_arguments", "error": "question and topic must be strings"})
    selected = _select_topic(topic, question)
    if selected is None:
        return json.dumps({"status": "not_found", "message": "No matching store-policy section. Ask the customer to clarify the topic."})

    chapter_ids = list(_TOPICS[selected])
    normalized_question = _normalize(question)
    if selected == "store" and any(x in normalized_question for x in ("telefone", "contato", "whatsapp")):
        chapter_ids.append(7)
    if selected == "payments" and "pix" in normalized_question:
        chapter_ids.append(6)
    if selected == "returns" and "defeit" in normalized_question:
        chapter_ids.append(8)

    try:
        indexed = _sections()
    except (OSError, PdfReadError, ValueError):
        return json.dumps({"status": "extraction_error", "error": "Unable to read the supplied policy PDF."})
    excerpts = []
    for chapter in dict.fromkeys(chapter_ids):
        chunks = indexed.get(chapter)
        if not chunks:
            return json.dumps({"status": "extraction_error", "message": f"Chapter {chapter} not extracted from policy PDF."})
        pages = sorted({int(chunk["page"]) for chunk in chunks})
        excerpts.append({
            "chapter": chapter,
            "title": _CHAPTER_NAMES[chapter],
            "pages": pages,
            "text": "\n".join(str(chunk["text"]) for chunk in chunks),
        })

    ambiguities = []
    if selected == "store" and any(x in normalized_question for x in ("telefone", "contato", "whatsapp")):
        ambiguities.append({"issue": "contact_conflict", "note": "Section 1.2 lists (67) 3341-4444 as telephone/WhatsApp, whereas section 7 lists (67) 3321-4500 for WhatsApp. Do not silently pick one as the sole official number."})
    if selected == "payments":
        ambiguities.append({"issue": "installment_thresholds", "note": "The payment summary says credit-card minimum R$100 per installment; section 3.1 specifies different minimums by installment count and an unclear phrase about amounts below R$50. Do not silently resolve the conflict."})
    if selected == "delivery":
        ambiguities.append({"issue": "exactly_500_brl", "note": "The local-delivery policy defines orders above and below R$500, but not exactly R$500. Ask for human confirmation at that boundary."})

    clarifications = []
    if selected == "returns":
        clarifications = [
            "Whether the purchase was online or in-store",
            "Reason for the request: regret, defect or preference",
            "Actual delivery/receipt date or purchase date, as applicable",
            "Condition of the instrument and original packaging, where applicable",
        ]

    return json.dumps({
        "status": "ok",
        "topic": selected,
        "source_file": "data/políticas_da_loja.pdf",
        "source_version": "2.1 (June 2025)",
        "sections": excerpts,
        "ambiguities": ambiguities,
        "information_needed_before_definitive_return_decision": clarifications,
        "note": "Use the relevant excerpt and cite chapter/page in the answer; do not claim to approve, reject or register a request.",
    }, ensure_ascii=False)
