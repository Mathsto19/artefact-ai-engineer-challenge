"""Read-only review conversations selected from actual acceptance evidence.

These are shipped with the repository, not generated or seeded into a user's
private SQLite history. Independent negative checks are not joined into a chat.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RecordedExample:
    key: str
    title: str
    evidence_file: str
    turn_count: int
    note: str
    review_note: str


EXAMPLES = (
    RecordedExample(
        "catalog", "Catálogo e tipos de cordas",
        "docs/evidence/quality_ui_acceptance.json", 2,
        "Consulta de violões até R$ 1.000 e continuação sobre cordas de aço. "
        "A segunda resposta usa consulta direta do código, sem nova chamada ao modelo.",
        "The initial catalog turn used the real model/tool cycle. The steel-string "
        "follow-up queried the source directly through the application, without a model call. "
        "Commercial replies use Python source renderers.",
    ),
    RecordedExample(
        "pricing", "Promoção, PIX e orçamento",
        "docs/evidence/pricing_after_quality.json", 3,
        "Consulta real de preço e desconto não cumulativo, com comparação de orçamento.",
        "All three turns used actual model/tool cycles. Python renders the verified "
        "price fields and budget comparison; this is not independent model claim accuracy.",
    ),
    RecordedExample(
        "returns", "Trocas e devoluções",
        "docs/evidence/policies_after_quality.json", 2,
        "Consulta ao manual, com esclarecimento do canal de compra e da data de recebimento.",
        "Both turns retrieved the original policy PDF through actual model/tool cycles. "
        "Python controls the source-verified clarification questions. No return was approved.",
    ),
    RecordedExample(
        "orders", "Consulta de pedido",
        "docs/evidence/orders_after_quality.json", 3,
        "Conferência demonstrativa e total histórico preservado. O e-mail está oculto.",
        "The first two turns requested missing credentials without a lookup. The verified "
        "turn used the real order tool/model cycle and Python rendered the historical fields. "
        "The email is redacted. Separate denial checks are excluded from this conversation.",
    ),
)
EXAMPLE_BY_KEY = {example.key: example for example in EXAMPLES}


def load_example(key: str) -> dict:
    """Load a fixed recorded dialogue; never call the model or write history."""
    example = EXAMPLE_BY_KEY[key]
    report = json.loads((ROOT / example.evidence_file).read_text(encoding="utf-8"))
    if report.get("passed") is not True:
        raise ValueError("The recorded acceptance report did not pass")
    turns = report["turns"][:example.turn_count]
    if len(turns) != example.turn_count or any(
        not isinstance(turn.get("question"), str) or not isinstance(turn.get("answer"), str)
        for turn in turns
    ):
        raise ValueError("Incomplete recorded conversation")
    return {"example": example, "recorded_at": report["recorded_at"],
            "model": report["model"], "turns": turns}


def recorded_date(recording: dict) -> str:
    timestamp = datetime.fromisoformat(recording["recorded_at"])
    return timestamp.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M (UTC-03)")


def as_markdown(recording: dict) -> str:
    """Export original Portuguese dialogue with English provenance, not new output."""
    example = recording["example"]
    lines = [f"# Recorded conversation: {example.title}", "",
             f"Recorded: {recording['recorded_at']} | Model: {recording['model']}", "",
             f"Evidence: `{example.evidence_file}`", "", example.review_note, "",
             "Original Brazilian Portuguese messages follow. This is a read-only record "
             "of an earlier execution, not a new inference or live stock/tracking query.", ""]
    for number, turn in enumerate(recording["turns"], start=1):
        lines.extend([f"## Turn {number}", "", "### Customer", "", turn["question"], "",
                      "### Zubumafu", "", turn["answer"], "",
                      f"Observed elapsed time: {turn['elapsed_seconds']} seconds.", ""])
    return "\n".join(lines)
