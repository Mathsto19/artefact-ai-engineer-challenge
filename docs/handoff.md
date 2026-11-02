# Development handoff

Catalog, policy retrieval and promotion/PIX pricing are implemented. This is not the finished Artefact submission.

## Repository continuity

The working project lives directly at the repository root. Do not create another outer `zubumafu` project or replace this repository's `.git` directory with one from a ZIP.

Public repository: https://github.com/Mathsto19/artefact-ai-engineer-challenge

The existing first commit (`3c89eec`) and the prototype commits (`fe3745b`, `9929359`) are preserved through a merge. The original data files were identical in both working copies. The merge resolved their line-ending differences while preserving the source working files. Refinements and observed verification are subsequent work, not retroactively manufactured intermediate commits.

## Implemented

- Streamlit chat, session history, conversation reset and tool evidence.
- Local Ollama client with configurable host/model/timeout.
- Bounded tool calling with `think=False` requested and final-content safeguards.
- Read-only `search_products` over the original product/category CSVs.
- Category normalization, availability and budget filters, literal specification search, deterministic BRL display and typed input checks.
- Offline regression tests and a separate real-model catalog acceptance script.
- `search_store_policies` reads the original PDF's ten chapters, retaining page references and chapter continuations.
- Policy results surface the three known contact/installment/freight ambiguities; defects also retrieve warranty rules.
- Policy questions require the corresponding tool. A successful catalog lookup cannot authorize a policy reply.
- Missing purchase channel and online receipt date in an explicit regret dialogue are handled with source-verified clarification templates after the model/tool round-trip; the trace records their origin.
- A separate two-turn policy acceptance script checks actual source use and follow-up behavior.
- `get_product_pricing` calculates original, promotional and final prices with `Decimal`; active promotions do not stack with PIX.
- Catalog budgets and ordering use the final eligible price, with explicit original/final fields and a configurable payment method.
- A separate three-turn acceptance script exercises a product quote, PIX follow-up and budget comparison with the actual model.
- Missing fields in a single-model promotional quote are completed from tool facts with explicit trace metadata; a skipped fresh lookup has one bounded verification retry.

See [validation.md](validation.md) for the actual evidence and its limits. A simulated-model test is not a real-model test. Reasoning hidden from a customer is not proof that reasoning generation was disabled.

The latest pricing milestone passed 61 offline tests and its actual three-turn source/price checks. Evidence is in `examples/03_promotion_pix_budget.{md,json}`. Timings were 62.22, 101.95 and 140.06 seconds. Price completeness and a bounded source-verification retry are application safeguards; do not attribute them entirely to the model. Tone/wording and latency still require work. Three distinct observed conversations now exist; example count alone is not final acceptance.

## Next increment

1. Review factuality/persona and out-of-scope/error behavior, keeping recorded observations distinct from expected results.
2. Keep unresolved contacts, installment thresholds and the exact R$ 500 freight boundary explicit; do not silently turn them into automatic decisions.
3. Decide whether limited order consultation belongs in the final scope; define its demo verification and privacy limits before exposing customer data.
4. Complete out-of-scope/error handling and the chosen acceptance matrix. Return clarification phrase matching is not a general eligibility engine.
5. Review the recorded conversations for final coverage and add scenarios where needed; check clean setup and final submission materials.

The known reasoning/latency limitation should also be reevaluated with measured evidence. Do not expand the project with multi-agent orchestration or additional infrastructure unless a concrete requirement warrants it.

## Continue between platforms

Use this same GitHub repository. Pull before starting work in a separate clone, commit each completed and verified increment, and push before switching platforms. Do not overwrite an existing `.git` directory or rewrite the shared history.

Before returning the project for review, provide the current branch/commit, changes, commands executed, observed outputs and unresolved issues. Keep the English README and AI assistance disclosure current. Do not commit local virtual environments, ZIP handoff packages, credentials, raw reasoning logs or the internal Portuguese planning guide.

After final submission, freeze the repository as required by the challenge. No submission has been performed as part of this integration work.
