"""Run the two-turn return-policy scenario against the actual local Ollama model.

The report records final answers and tool evidence, never raw reasoning text.
Checks are structural; review the recorded replies for correctness and tone.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zubumafu.agent import MODEL, respond
from zubumafu.catalog import _normalize
from zubumafu.model import create_chat


QUESTIONS = ["Comprei um violão e me arrependi. Posso devolver?", "Foi online."]


def asks_receipt_date(answer: str) -> bool:
    """Require a question about the receipt date, not an unrelated question.

    Merely mentioning 'seven days after receipt' must not pass this check.
    """
    normalized = _normalize(answer)
    questions = [part for part in re.split(r"[.!?\n]", normalized)
                 if re.search(r"\b(quando|qual|que dia|ha quanto)\b", part)]
    return "?" in normalized and any(
        re.search(r"receb|cheg", question) and re.search(r"quando|data|dia|ha quanto", question)
        for question in questions
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence file.")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    real_chat = create_chat()
    history = []
    turns = []
    for index, question in enumerate(QUESTIONS, start=1):
        calls = []
        tool_results = []

        def recorded_chat(**kwargs):
            for message in kwargs["messages"]:
                if isinstance(message, dict) and message.get("role") == "tool":
                    payload = json.loads(message["content"])
                    if payload not in tool_results:
                        tool_results.append(payload)
            started = time.perf_counter()
            response = real_chat(**kwargs)
            message = response.message
            raw = message.content or ""
            calls.append({
                "think_requested": kwargs["think"],
                "tool_calls": [{"name": call.function.name, "arguments": call.function.arguments}
                               for call in (message.tool_calls or [])],
                "reasoning_output_observed": bool(
                    getattr(message, "thinking", None)
                    or "<think" in raw.casefold() or "</think" in raw.casefold()
                ),
                "generated_tokens": response.eval_count,
                "finish_reason": response.done_reason,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
            })
            print(f"Turn {index}, model request {len(calls)}: {calls[-1]['elapsed_seconds']} s", flush=True)
            return response

        started = time.perf_counter()
        answer, trace = respond(question, history, chat_fn=recorded_chat)
        turns.append({
            "question": question,
            "answer": answer,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
            "history_messages_supplied": len(history),
            "trace": trace,
            "model_requests": calls,
            "tool_results": tool_results,
        })
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])

    def retrieved_returns(turn):
        return any(
            result.get("status") == "ok"
            and result.get("source_file") == "data/políticas_da_loja.pdf"
            and any(section["chapter"] == 4 and section["pages"] == [4] for section in result.get("sections", []))
            for result in turn["tool_results"]
        )

    first, second = (_normalize(turn["answer"]) for turn in turns)
    checks = {
        "first_turn_retrieves_return_section_page_4": retrieved_returns(turns[0]),
        "second_turn_retrieves_return_section_page_4": retrieved_returns(turns[1]),
        "first_reply_asks_purchase_channel": "?" in first and bool(re.search(r"online|internet|site", first))
                                            and bool(re.search(r"presencial|fisic|na loja", first)),
        "second_reply_asks_receipt_date": asks_receipt_date(turns[1]["answer"]),
        "previous_dialogue_supplied_on_followup": turns[1]["history_messages_supplied"] == 2,
        "one_clarification_question_per_turn": all(turn["answer"].count("?") == 1 for turn in turns),
        "no_unverified_storefront_process": all("processo na loja virtual" not in _normalize(turn["answer"]) for turn in turns),
        "verified_source_footer_on_both_replies": all("Fonte consultada:" in turn["answer"] for turn in turns),
        "no_explicit_approval_or_action_claim": not any(
            forbidden in answer for answer in [first, second]
            for forbidden in ["devolucao autorizada", "devolucao aprovada", "ja autorizei", "ja registrei", "reembolso aprovado"]
        ),
        "no_visible_thinking_markup": all("<think" not in turn["answer"].casefold()
                                         and "</think" not in turn["answer"].casefold() for turn in turns),
        "all_requests_use_think_false": all(call["think_requested"] is False for turn in turns for call in turn["model_requests"]),
    }
    report = {
        "recorded_at": datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec="seconds"),
        "model": os.environ.get("OLLAMA_MODEL", MODEL),
        "python": sys.version.split()[0],
        "ollama_python_sdk": version("ollama"),
        "pypdf": version("pypdf"),
        "turns": turns,
        "checks": checks,
        "passed": all(checks.values()),
        "evaluation_limit": "Structural checks do not prove every policy statement or the tone is correct; manually review the actual replies and PDF excerpts.",
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
