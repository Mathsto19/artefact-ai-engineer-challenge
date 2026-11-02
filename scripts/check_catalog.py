"""Run the first catalog acceptance scenario against the actual local model.

This is an opt-in integration check, separate from the offline unit tests.
Recorded artifacts contain the final answer and tool evidence, not reasoning text.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zubumafu.agent import MODEL, respond
from zubumafu.model import create_chat


QUESTION = "Quais violões disponíveis custam até R$ 1.000?"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence file.")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    real_chat = create_chat()
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
        raw_content = message.content or ""
        calls.append({
            "think_requested": kwargs["think"],
            "tool_calls": [{"name": call.function.name, "arguments": call.function.arguments}
                           for call in (message.tool_calls or [])],
            "reasoning_output_observed": bool(
                getattr(message, "thinking", None)
                or "<think" in raw_content.casefold()
                or "</think" in raw_content.casefold()
            ),
            "generated_tokens": response.eval_count,
            "finish_reason": response.done_reason,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        })
        print(f"Completed model request {len(calls)}: {calls[-1]['elapsed_seconds']} s", flush=True)
        return response

    started = time.perf_counter()
    answer, trace = respond(QUESTION, chat_fn=recorded_chat)
    products = [product for result in tool_results for product in result.get("products", [])]
    confirmed_search = [item for item in trace if item["tool"] == "search_products" and item["status"] == "ok"]
    checks = {
        "model_requested_search": any(call["tool_calls"] for call in calls),
        "search_executed_successfully": bool(confirmed_search),
        "tool_result_returned_to_model": bool(tool_results),
        "correct_budget_and_availability_filters": bool(confirmed_search) and all(
            Decimal(item["filters"]["max_price_brl"]) == 1000
            and item["filters"]["available_only"] is True
            for item in confirmed_search
        ),
        "retrieved_products_fit_request": bool(products) and all(
            product["category"] == "Violões"
            and Decimal(product["final_price_brl"]) <= 1000
            and product["stock_quantity"] > 0
            and product["status"] == "active"
            for product in products
        ),
        "answer_mentions_a_retrieved_product": any(product["name"].casefold() in answer.casefold() for product in products),
        "answer_has_no_thinking_markup": "<think" not in answer.casefold() and "</think" not in answer.casefold(),
        "all_requests_use_think_false": all(call["think_requested"] is False for call in calls),
    }
    report = {
        "recorded_at": datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec="seconds"),
        "model": os.environ.get("OLLAMA_MODEL", MODEL),
        "python": sys.version.split()[0],
        "ollama_python_sdk": version("ollama"),
        "question": QUESTION,
        "answer": answer,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "checks": checks,
        "passed": all(checks.values()),
        "trace": trace,
        "model_requests": calls,
        "tool_results": tool_results,
        "evaluation_limit": "These checks do not prove every generated claim is grounded; review the final answer against the returned records.",
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
