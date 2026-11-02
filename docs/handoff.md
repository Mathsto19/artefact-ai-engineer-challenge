# Development handoff

Catalog, policies, promotion/PIX pricing, demonstrative order lookup and the persistent messaging interface are implemented. This is not the finished Artefact submission.

## Repository continuity

The working project lives directly at the repository root. Do not create another outer `zubumafu` project or replace this repository's `.git` directory with one from a ZIP.

Public repository: https://github.com/Mathsto19/artefact-ai-engineer-challenge

The existing first commit (`3c89eec`) and the prototype commits (`fe3745b`, `9929359`) are preserved through a merge. The original data files were identical in both working copies. The merge resolved their line-ending differences while preserving the source working files. Refinements and observed verification are subsequent work, not retroactively manufactured intermediate commits.

## Implemented

- Streamlit chat with separate personal/test threads, local SQLite persistence, scoped deletion and tool evidence.
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
- Catalog and pricing replies use complete source-based renderers with explicit trace metadata; a skipped fresh lookup has one bounded verification retry. This supersedes the earlier partial price-field supplement.
- Per-product nylon/steel descriptions, no assumed beginner profile or unsupported ranking, and distinct unknown/unavailable/budget outcomes.
- A narrow string-type follow-up re-queries the previously displayed names under the prior budget, without a model call; `application_reference_lookup` identifies its origin.
- Seven validation prompt templates start empty and invoke the backend only when requested; they contain no pre-recorded answers.
- SQLite writes exchanges atomically, closes connections explicitly and whitelists/redacts stored trace metadata. Original messages remain unencrypted on the trusted local computer.
- Streamlit rerun, restart, thread isolation, scenario launch and scoped-deletion checks using AppTest; these do not establish visual correctness.
- `get_order_status` checks the order/customer/email association, preserves historical totals and excludes customer/internal fields.
- Agent-level order arguments are bound to customer-provided facts; assistant text and guessed credentials cannot authorize disclosure.
- Order replies are rendered from structured Python results after the tool/model round-trip. The trace records this controlled origin without the email.
- The opt-in order acceptance script checks the three-turn dialogue plus wrong-email/nonexistent-order denials, redacting emails in saved evidence.

See [validation.md](validation.md) for the actual evidence and its limits. A simulated-model test is not a real-model test. Reasoning hidden from a customer is not proof that reasoning generation was disabled.

The pricing milestone passed 61 offline tests and its actual three-turn source/price checks, recorded in `examples/03_promotion_pix_budget.{md,json}`. The order milestone extends that suite to 89 tests, preserving the earlier regressions. The actual order conversation and two denial cases passed 16 structural checks; see the latest validation section for observed behavior, timings and limitations. Controlled price/return/order replies are application safeguards; do not attribute them entirely to the model. Example count alone is not final acceptance.

## Final packaging

1. Verify a clean installation and review the English README, architecture decisions and final example selection against the original challenge.
2. Prepare the submission PDF and confirm the official submission instructions/deadline. Do not submit the application without Matheus's explicit instruction.
3. Keep visual review explicitly pending: no browser was connected and the user deferred Edge setup. AppTest is functional evidence only.
4. Keep unresolved contacts, installment thresholds and the exact R$ 500 freight boundary explicit; do not turn them into automatic decisions.
5. Keep order consultation demonstrative/read-only and local history unencrypted; stronger authentication and secure real-customer storage are future production work.

The quality/UI integration passed 119 offline tests, including the preceding 89, and separate actual model acceptance is recorded in the latest validation section. The known reasoning/latency limitation remains; isolated timings are not performance benchmarks. Do not expand the project with new infrastructure or features during packaging.

## Continue between platforms

Incoming ZIPs are expected to contain an older baseline plus a new increment. The canonical local/GitHub repository remains the integration reference. Treat a ZIP as a source of feature changes: identify new files and relevant function edits, integrate selectively, preserve current fixes/tests/dependency pins/evidence, compare original source hashes and run the full applicable regressions plus real acceptance before committing. Do not replace the canonical checkout or import ZIP Git configuration. The separate platform is not required to update its whole baseline.

When working directly in another clone, pull the shared repository first. Keep each actual completed increment in Git and push before switching platforms. Never rewrite the shared history. [The incoming order handoff](order_increment_handoff.md) records the original package's checks separately from canonical verification.

Before returning the project for review, provide the current branch/commit, changes, commands executed, observed outputs and unresolved issues. Keep the English README and AI assistance disclosure current. Do not commit local virtual environments, ZIP handoff packages, credentials, raw reasoning logs or the internal Portuguese planning guide.

After final submission, freeze the repository as required by the challenge. No submission has been performed as part of this integration work.
