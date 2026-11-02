"""Opt-in real-model order dialogue and denial checks, with email-redacted evidence."""

from __future__ import annotations

import argparse
import csv
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
from zubumafu.pricing import display_brl


EMAIL_PATTERN = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)


def redact(value):
    if isinstance(value, str):
        return EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


def read_rows(name):
    with (Path(__file__).resolve().parents[1] / "data" / f"desafio_tecnico_ai_eng - {name}.csv").open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    orders = read_rows("orders")
    customers = {row["customer_id"]: row for row in read_rows("customers")}
    products = {row["product_id"]: row["name"] for row in read_rows("products")}
    # Deliberately choose a historical Kalani order with no carrier/date fields.
    order = next(row for row in orders if row["order_id"] == "11")
    email = customers[order["customer_id"]]["email"]
    source_items = [{"product_name": products[row["product_id"]], "quantity": int(row["quantity"])}
                    for row in read_rows("order_items") if row["order_id"] == order["order_id"]]
    chat = create_chat()
    turns = []

    def run_turn(question, history, scenario):
        calls, tool_results = [], []

        def recorded_chat(**kwargs):
            for message in kwargs["messages"]:
                if isinstance(message, dict) and message.get("role") == "tool":
                    payload = json.loads(message["content"])
                    if payload not in tool_results:
                        tool_results.append(payload)
            start = time.perf_counter()
            response = chat(**kwargs)
            message = response.message
            raw = message.content or ""
            calls.append({
                "think_requested": kwargs["think"],
                "tool_calls": [{"name": call.function.name, "arguments": redact(call.function.arguments)}
                               for call in (message.tool_calls or [])],
                "reasoning_output_observed": bool(getattr(message, "thinking", None) or "<think" in raw.casefold() or "</think" in raw.casefold()),
                "generated_tokens": response.eval_count, "prompt_tokens": response.prompt_eval_count,
                "finish_reason": response.done_reason,
                "elapsed_seconds": round(time.perf_counter() - start, 2),
            })
            print(f"{scenario}, request {len(calls)}: {calls[-1]['elapsed_seconds']} s", flush=True)
            return response

        start = time.perf_counter()
        answer, trace = respond(question, history, chat_fn=recorded_chat)
        turn = {"scenario": scenario, "question": redact(question), "answer": redact(answer),
                "history_messages_supplied": len(history), "trace": trace,
                "elapsed_seconds": round(time.perf_counter() - start, 2),
                "model_requests": calls, "tool_results": redact(tool_results)}
        turns.append(turn)
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
        print(redact(answer), flush=True)
        return turn

    history = []
    first = run_turn("Onde está meu pedido?", history, "ask_order_number")
    second = run_turn(order["order_id"], history, "ask_registered_email")
    verified = run_turn(email, history, "verified_order_without_tracking")
    wrong = run_turn(f"Quero consultar o pedido {order['order_id']}, e-mail wrong@example.invalid", [], "wrong_email")
    missing = run_turn("Quero consultar o pedido 999999999999, e-mail wrong@example.invalid", [], "nonexistent_order")
    results = [item for item in verified["tool_results"] if item.get("status") == "verified"]
    checks = {
        "first_asks_only_order_number": "numero do pedido" in _normalize(first["answer"]) and first["answer"].count("?") == 1,
        "second_asks_only_registered_email": "e-mail cadastrado" in _normalize(second["answer"]) and second["answer"].count("?") == 1,
        "no_order_details_before_verification": all("Total registrado" not in turn["answer"] and not any(item.get("status") == "verified" for item in turn["tool_results"]) for turn in [first, second]),
        "verified_followup_has_two_prior_turns": verified["history_messages_supplied"] == 4,
        "model_requests_order_tool_on_verified_turn": any(call["name"] == "get_order_status" for request in verified["model_requests"] for call in request["tool_calls"]),
        "verified_result_returned_to_real_model": bool(results),
        "source_order_and_items_match": bool(results) and all(item["order_id"] == order["order_id"] and item["order_status"] == order["status"] and item["items"] == source_items for item in results),
        "historical_total_preserved": bool(results) and all(Decimal(item["recorded_total_brl"]) == Decimal(order["total_brl"]) for item in results) and display_brl(order["total_brl"]) in verified["answer"],
        "missing_tracking_and_estimate_not_invented": bool(results) and all(item["tracking_code"] is None and item["estimated_delivery"] is None for item in results) and verified["answer"].count("não consta no registro") == 2,
        "historical_not_live_receipt_notice": "históricos" in verified["answer"] and "não confirma o recebimento" in verified["answer"],
        "wrong_email_denied_by_tool": any(item.get("status") == "not_verified" for item in wrong["tool_results"]),
        "nonexistent_order_denied_by_tool": any(item.get("status") == "not_verified" for item in missing["tool_results"]),
        "denials_are_identical_and_generic": wrong["answer"] == missing["answer"] and "Não consegui confirmar" in wrong["answer"] and "Total registrado" not in wrong["answer"],
        "no_customer_fields_in_order_results": all(not set(item).intersection({"email", "customer_id", "phone", "notes"}) for turn in turns for item in turn["tool_results"] if item.get("status") == "verified"),
        "no_visible_thinking": all("<think" not in turn["answer"].casefold() and "</think" not in turn["answer"].casefold() for turn in turns),
        "all_requests_use_think_false": all(request["think_requested"] is False for turn in turns for request in turn["model_requests"]),
    }
    report = {"recorded_at": datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec="seconds"),
              "model": os.environ.get("OLLAMA_MODEL", MODEL), "python": sys.version.split()[0],
              "ollama_python_sdk": version("ollama"), "email_redacted": True,
              "turns": turns, "checks": checks, "passed": all(checks.values()),
              "evaluation_limit": "Order replies are rendered by Python from customer-bound tool results; this is not independent model claim accuracy. Review source, access checks, tone and latency separately. No raw reasoning or full emails are stored."}
    serialized = json.dumps(redact(report), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
