# Final quality review + messenger UI — selective integration handoff

> Provenance: the 57-test results below describe the incoming older snapshot. Canonical integration preserved the previous 89 regressions and expanded the suite to 119 tests. See [validation.md](validation.md) for local AppTest/model results and remaining visual-review limits. The canonical entrypoint calls `main()` on each rerun; it does not rely on import side effects.

**Base warning:** this ZIP contains an **older project snapshot** with a new, isolated quality/UI increment. The canonical Windows/GitHub repository was reported at `e0db328` with 89 tests and four genuine example conversations before this work. **Do not overwrite that repository, its `.git`, existing deterministic return/policy controls, source snapshots, pinned dependencies, or evidence with the versions in this ZIP.** Merge only the relevant functionality below and adapt integration points.

## New files

| File | Purpose |
| --- | --- |
| `zubumafu/response_quality.py` | Deterministic catalog and pricing reply formatters, off-topic redirect and basic visible-text cleanup. |
| `zubumafu/conversations.py` | Local SQLite chat storage, separate IDs, personal/test labels, trace-field whitelisting, title redaction and scoped deletion. |
| `zubumafu/demo_scenarios.py` | Seven validation **prompt templates and expected criteria**, not fabricated model answers. |
| `zubumafu/streamlit_ui.py` | Messaging-style Streamlit layout, per-chat history sidebar, validation scenario launch/steps and chat deletion confirmation. |
| `tests/test_quality.py` | Regression tests for observed LLM/catalog/PIX issues and error handling. |
| `tests/test_conversations.py` | Persistent-history, privacy and isolation checks without Streamlit. |

## Updated files for this increment

| File | Change to merge selectively |
| --- | --- |
| `app.py` | Thin Streamlit entrypoint importing `zubumafu.streamlit_ui`. |
| `zubumafu/agent.py` | Safe handling of tool failure, authoritative formatting for product/price payloads, off-topic fast path and visible-text cleanup. **Reconcile this with the newer repository's actual conversation/order/return guards** instead of copying the file wholesale. |
| `zubumafu/catalog.py` | Differentiates zero-result reasons: unknown, unavailable, over budget, other filters. Retains original pricing and availability computation. |
| `zubumafu/persona.py` | Explicit source-based string descriptions, no unsupported "best" claim, neutral experience level, PIX no-stacking and concise tone. |
| `.gitignore` | Excludes `.local/` persistent local history. |
| `README.md` | UI instructions, security tradeoffs, quality decisions and pending validation. |
| `docs/decisions.md`, `docs/validation.md` | Architecture and local-test evidence. |

All other files in the ZIP are pre-existing baseline material. The original CSVs and policy PDF were not edited. No new Python runtime dependencies were needed: SQLite is in the standard library and Streamlit was already a dependency.

## Verification actually executed

- `python3 -B -m unittest discover -s tests -q` — **57 tests passed** in the old snapshot (40 preceding tests and 17 new tests).
- `git diff --check` — check against changes in this snapshot before handoff.
- Code parsed with Python's `ast` without installing Streamlit.
- The actual Streamlit UI and local Ollama/Qwen3 model were **not executed** here, and no latency reduction is claimed.
- The SQLite tests use temporary databases and clean them up; no persisted demonstration conversations or full private emails are included in the package.

## Manual acceptance after merging into canonical repo

1. Run the canonical test suite (at least the previously reported 89 tests) plus merged quality/history tests; confirm that return questions, order credentials and history isolation are unchanged.
2. `streamlit run app.py`: verify sidebar, new chat, personal thread switching, `Test` thread creation, template question buttons, chat deletion and chat history after a full application restart. Check mobile and 1366×768 layouts in the actual browser.
3. Ask for violões under R$1,000: check three names, final prices, stocks, nylon/steel labeling, neutral ranking and no assumption that the customer is inexperienced.
4. Ask about Kalani KAL-700T followed by PIX: verify exact R$323.10 and clearly no additional 5%. Check discounted-budget inclusion.
5. Check unknown/discontinued items and a failed tool/disabled Ollama; no made-up availability or prices.
6. Repeat genuine returns and order conversations from current repo, including mismatched email and protection against credentials supplied only by the assistant. Check original PDF references and recorded order totals.
7. Redact full customer emails in any public transcript. **Test scenarios are prompts, not acceptance evidence**: capture the actual tool trace, final answer and elapsed time before using one in the final 3–5-example submission.

### Limitations

- Chat history is a local **unencrypted** SQLite file on a single trusted computer. This demonstration must not be deployed as a multi-user or public service without authentication, data-protection design and appropriate storage.
- Prompt and output guards address selected observed failures; they cannot guarantee grounding of arbitrary LLM prose.
- `think=False` remains configured but does not prove reasoning generation is disabled. UI/backend latency has not been measured in this environment.
- No business writes, cancellations, refunds, freight, installments, carrier integration or external messaging were added.
- No commit, push or submission was performed for this increment. The canonical repository owner should merge, run the real model, record evidence, then commit/push if all checks pass.
