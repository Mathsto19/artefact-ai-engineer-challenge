"""Observe the three-turn pricing acceptance dialogue against local Ollama.

Structural checks complement manual review; no reasoning text is recorded.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
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


QUESTIONS = [
    "Quanto custa o Kalani KAL-700T Tenor Natural?",
    "E pagando no PIX, fica mais barato?",
    "Esse Kalani entra em um orçamento de R$ 340?",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    real_chat = create_chat()
    history = []
    turns = []
    for question in QUESTIONS:
        calls, tool_results = [], []

        def recorded_chat(**kwargs):
            for message in kwargs["messages"]:
                if isinstance(message, dict) and message.get("role") == "tool":
                    payload = json.loads(message["content"])
                    if payload not in tool_results:
                        tool_results.append(payload)
            started = time.perf_counter()
            response = real_chat(**kwargs)
            message = response.message
            content = message.content or ""
            calls.append({
                "think_requested": kwargs["think"],
                "tool_calls": [{"name": call.function.name, "arguments": call.function.arguments}
                               for call in (message.tool_calls or [])],
                "reasoning_output_observed": bool(getattr(message, "thinking", None)
                                                  or "<think" in content.casefold()
                                                  or "</think" in content.casefold()),
                "generated_tokens": response.eval_count,
                "finish_reason": response.done_reason,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
            })
            print(f"Turn {len(turns) + 1}, request {len(calls)}: {calls[-1]['elapsed_seconds']} s", flush=True)
            return response

        started = time.perf_counter()
        answer, trace = respond(question, history, chat_fn=recorded_chat)
        turns.append({"question": question, "answer": answer, "trace": trace,
                      "elapsed_seconds": round(time.perf_counter() - started, 2),
                      "model_requests": calls, "tool_results": tool_results})
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
        print(answer, flush=True)

    first, pix, budget = turns
    pricing = [result for turn in turns for result in turn["tool_results"] if "pricing" in result]
    pix_results = [result for result in pix["tool_results"] if "pricing" in result]
    budget_records = [record for result in budget["tool_results"] for record in (
        result.get("products", []) if "products" in result else [result] if "pricing" in result else []
    ) if str(record.get("product_id")) == "127"]
    pix_text = _normalize(pix["answer"])
    checks = {
        "every_turn_has_successful_product_lookup": all(any(
            item["status"] == "ok" and item["tool"] in {"get_product_pricing", "search_products"}
            for item in turn["trace"]) for turn in turns),
        "every_turn_returns_tool_result_to_model": all(turn["tool_results"] for turn in turns),
        "dedicated_pricing_tool_used_for_pix": any(
            item["tool"] == "get_product_pricing" and item["status"] == "ok" for item in pix["trace"]),
        "pricing_results_match_original_promotion_and_final": bool(pricing) and all(
            result["product_id"] == "127" and result["pricing"]["list_price_brl"] == "359.00"
            and result["pricing"]["discount_percent"] == "10" and result["pricing"]["final_price_brl"] == "323.10"
            for result in pricing),
        "first_answer_shows_original_percentage_and_final": all(
            re.search(pattern, first["answer"]) for pattern in [r"359[,.]00", r"10\s*%", r"323[,.]10"]),
        "pix_lookup_preserves_promotion_without_extra_discount": bool(pix_results) and any(
            result["pricing"].get("payment_method") == "pix"
            and result["pricing"].get("pix_non_cumulative") is True
            and result["pricing"].get("pix_discount_applied") is False for result in pix_results),
        "pix_answer_explains_unchanged_non_cumulative_price": bool(re.search(r"323[,.]10", pix["answer"])) and (
            "nao" in pix_text and any(term in pix_text for term in ["cumul", "acumul", "adicional", "extra", "mais barato"]) ),
        "budget_tool_has_kalani_at_or_below_340": bool(budget_records) and all(
            Decimal(record.get("pricing", record)["final_price_brl"]) <= Decimal("340") for record in budget_records),
        "budget_answer_confirms_fit_at_323_10": bool(re.search(r"323[,.]10", budget["answer"])) and any(
            term in _normalize(budget["answer"]) for term in ["sim", "dentro", "abaixo", "cabe", "entra"]),
        "all_requests_use_think_false": all(call["think_requested"] is False for turn in turns for call in turn["model_requests"]),
        "no_visible_thinking_markup": all("<think" not in turn["answer"].casefold() and "</think" not in turn["answer"].casefold() for turn in turns),
    }
    report = {
        "recorded_at": datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec="seconds"),
        "model": os.environ.get("OLLAMA_MODEL", MODEL), "python": sys.version.split()[0],
        "ollama_python_sdk": version("ollama"), "turns": turns, "checks": checks,
        "passed": all(checks.values()),
        "evaluation_limit": "Structural checks are not a complete factuality/personality evaluation. Review each displayed answer against the source results. No reasoning text is recorded.",
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
