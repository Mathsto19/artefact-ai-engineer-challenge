# Order lookup increment — integration handoff

**Provenance note:** the sections below describe the incoming package before canonical integration. Its 40-test result is an upstream observation, not the current repository total. Canonical refinements, the 89-test regression suite and real-model acceptance are recorded in [validation.md](validation.md). The local/GitHub checkout remains authoritative.

This package is an **older prototype snapshot plus the new order-lookup increment**. It is not a replacement for the newer canonical Windows/GitHub repository. Preserve its existing history, fixes, policy controls, pinned dependencies, tests and evidence. Merge the changes listed below selectively; never import this package's `.git` directory (none is included).

## New files

| File | Change |
| --- | --- |
| `zubumafu/orders.py` | Implements `get_order_status` and read-only CSV indexing of orders, customers, order items and product names. |
| `tests/test_orders.py` | Covers input order, successful/mismatched association, missing fields and shipment details, data integrity, and mocked agent tool calls. |
| `docs/order_increment_handoff.md` | This integration record. |

## Files updated for this increment

| File | Change |
| --- | --- |
| `zubumafu/agent.py` | Registers `get_order_status`, passes tool results back to the model, blocks unverified order claims and formats verified order fields deterministically. |
| `zubumafu/persona.py` | Guides one-question-at-a-time verification and forbids unsupported order actions/details. |
| `app.py` | Updates the capability and verification warning. |
| `README.md` | Documents tool, demo flow, limitations, and local testing. |
| `docs/decisions.md` | Records the order boundary and verification tradeoff. |
| `docs/validation.md` | Separates simulated test results from pending real-model acceptance. |

All other files in the ZIP are pre-existing baseline material; **do not overwrite newer versions** with them. The original CSV files and PDF have not been changed for this increment. No new runtime dependency was needed.

## Local checks actually run

- `python3 -B -m unittest discover -s tests -q` — **40 tests passed** on 2026-11-02 (16 order tests, plus 24 existing tests).
- `git diff --check` — passed.
- The tool was exercised with actual supplied CSV rows and a simulated Ollama tool-call cycle. This is **not** a real `qwen3:4b` execution.

## Pending after selective integration

1. Run the full existing test suite from the newer canonical repository, including its larger regression set.
2. In a real Qwen3 chat: ask for order status, give number, give registered email, and verify tool calls and the final answer. Test wrong email, nonexistent order, no tracking and no estimated delivery; save only redacted evidence and elapsed times.
3. Confirm that this older snapshot's agent/session design meshes with the newer repository's turn-state controls. In particular, retain any deterministic policy-return clarification rules and visible-answer/thinking filtering already present there.
4. Keep order number + email explicitly demo-only. Production would require authentication, authorization, logging policies, rate limits and an appropriately secured order source.
5. Only after reconciliation and real validation, create the expected commit and push from the canonical repository. No commit or push was made for this increment here.

No cancellations, refunds, freight, installments, live carrier queries, or customer-account changes were implemented.
