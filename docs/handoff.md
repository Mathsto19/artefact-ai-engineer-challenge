# Development handoff

Catalog, policies, promotion/PIX pricing and demonstrative order lookup are implemented. This is not the finished Artefact submission.

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
- `get_order_status` checks the order/customer/email association, preserves historical totals and excludes customer/internal fields.
- Agent-level order arguments are bound to customer-provided facts; assistant text and guessed credentials cannot authorize disclosure.
- Order replies are rendered from structured Python results after the tool/model round-trip. The trace records this controlled origin without the email.
- The opt-in order acceptance script checks the three-turn dialogue plus wrong-email/nonexistent-order denials, redacting emails in saved evidence.

See [validation.md](validation.md) for the actual evidence and its limits. A simulated-model test is not a real-model test. Reasoning hidden from a customer is not proof that reasoning generation was disabled.

The pricing milestone passed 61 offline tests and its actual three-turn source/price checks, recorded in `examples/03_promotion_pix_budget.{md,json}`. The order milestone extends that suite to 89 tests, preserving the earlier regressions. The actual order conversation and two denial cases passed 16 structural checks; see the latest validation section for observed behavior, timings and limitations. Controlled price/return/order replies are application safeguards; do not attribute them entirely to the model. Example count alone is not final acceptance.

## Next increment

1. Review factuality/persona and out-of-scope/error behavior, keeping recorded observations distinct from expected results.
2. Keep unresolved contacts, installment thresholds and the exact R$ 500 freight boundary explicit; do not silently turn them into automatic decisions.
3. Keep the selected order consultation explicitly demonstrative and read-only; stronger authentication belongs to future production work.
4. Complete out-of-scope/error handling and the chosen acceptance matrix. Return clarification phrase matching is not a general eligibility engine.
5. Review the recorded conversations for final coverage and add scenarios where needed; check clean setup and final submission materials.

The known reasoning/latency limitation should also be reevaluated with measured evidence. Do not expand the project with multi-agent orchestration or additional infrastructure unless a concrete requirement warrants it.

## Continue between platforms

Incoming ZIPs are expected to contain an older baseline plus a new increment. The canonical local/GitHub repository remains the integration reference. Treat a ZIP as a source of feature changes: identify new files and relevant function edits, integrate selectively, preserve current fixes/tests/dependency pins/evidence, compare original source hashes and run the full applicable regressions plus real acceptance before committing. Do not replace the canonical checkout or import ZIP Git configuration. The separate platform is not required to update its whole baseline.

When working directly in another clone, pull the shared repository first. Keep each actual completed increment in Git and push before switching platforms. Never rewrite the shared history. [The incoming order handoff](order_increment_handoff.md) records the original package's checks separately from canonical verification.

Before returning the project for review, provide the current branch/commit, changes, commands executed, observed outputs and unresolved issues. Keep the English README and AI assistance disclosure current. Do not commit local virtual environments, ZIP handoff packages, credentials, raw reasoning logs or the internal Portuguese planning guide.

After final submission, freeze the repository as required by the challenge. No submission has been performed as part of this integration work.
