# Zubumafu — Music Store AI Assistant

**Status: early functional prototype; not ready for delivery.**

Zubumafu is an experimental text-based customer assistant for **Empório da Música**, the fictional music store in Artefact's AI Engineer challenge. It speaks Brazilian Portuguese. The current milestone offers catalog searches, original-PDF policy retrieval, deterministic promotion/PIX pricing and demonstrative order consultation, with a messaging-style interface and local conversation history. The model requests tools and receives their results; catalog, price and order facts are rendered by Python. Final visual and submission review remain pending.

## Stack and rationale

| Choice | Rationale |
| --- | --- |
| Python | Required primary language; keeps querying and validation deterministic. |
| Streamlit | Small chat UI without a separate frontend application. |
| Ollama + `qwen3:4b` | Runs without an API key or per-request fee on the developer's laptop. This is a candidate, not a quality benchmark. |
| Python tool calling | CSV filtering stays in code while the model handles intent and language. |
| Local SQLite history | Saves separate personal/test conversations on one trusted computer, using Python's standard library. |
| Policies by document sections | `pypdf` extracts the supplied manual's chapters with page references; a vector database is unnecessary for this eight-page source. |
| `Decimal` pricing | Python applies eligible discounts, rounds BRL amounts and compares the final price with the budget. |

See [architecture decisions](docs/decisions.md), [verification evidence](docs/validation.md) and the [development handoff](docs/handoff.md).

## Run locally (Windows / PowerShell)

Use Python **3.12** and install Ollama. The environment was checked with Python 3.12.10, Ollama 0.40.13, the Ollama Python SDK 0.6.3, Streamlit 1.66.1 and pypdf 6.21.4. The resolved Python dependencies are pinned in `requirements-lock.txt` and used as constraints by `requirements.txt`.

From this repository root, run one command at a time:

```powershell
ollama pull qwen3:4b
ollama list
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. Calling the virtual environment's Python directly avoids PowerShell activation-policy issues. Keep the Ollama application running. If `ollama` is not recognized after installation, reopen the terminal.

Ask **"Quais violões disponíveis custam até R$ 1000?"**. Expand **"Fontes e ferramentas consultadas"** to inspect source/filter/reference metadata. Use **"Nova conversa"** to create an independent thread; select a navigation title to reopen an earlier one. **"Excluir"** asks for confirmation and deletes only that thread. The always-present **"Ocultar conversas" / "Abrir conversas"** button at the top controls the conversation panel independently of Streamlit's native sidebar.

The interface is inspired by messaging applications; it is not a WhatsApp integration. The sidebar separates personal conversations from test conversations. Seven built-in validation scenarios supply prompts and expected criteria. A new test thread starts empty: answers appear only when a prompt is executed, and the scenario is not automatically marked as passed.

For a review without running inference, **Minhas conversas** also lists four recorded examples: catalog/string types, promotion/PIX/budget, returns and order consultation. Click a title to read the actual questions/replies, source traces and observed timings, or download the original Portuguese dialogue as Markdown with English provenance notes. These read-only records load from the latest accepted reports in `docs/evidence/`; they work without a running Ollama server and are not inserted into private SQLite history. They cannot be continued or deleted from the interface. Use **Nova conversa** or a validation scenario to run a new interaction. The order email stays redacted, and independent negative checks are not joined into the displayed conversations. The original bilingual milestone transcripts in `examples/` remain historical records.

The **Tema** selector at the top offers **Sistema**, **Claro** and **Escuro**, including when the conversation panel is hidden. App palettes cover messages, forms, navigation and source details. **Sistema** follows the browser's operating-system preference. Explicit choices are reflected in `?theme=light`, `?theme=dark` or `?theme=system`, so refreshing/bookmarking the URL retains the selected mode. For example, open `http://localhost:8501/?theme=dark`. The interface uses plain labels and monochrome icons, without emojis. Generated free-form replies are filtered accordingly; older saved messages/titles are displayed without emojis while their original stored text is preserved. `.streamlit/config.toml` supplies the native widget baseline; app mode palettes are in `zubumafu/ui_theme.py`.

Simple standalone greetings return immediately from a Python template without inference; a greeting combined with a product/policy question still follows the normal lookup path. During inference the interface displays real workflow stages and elapsed time, updated from streamed backend activity. Recognized general musical explanations can display final text incrementally after the reasoning delimiter. Commercial/order replies never stream model drafts: verified Python-rendered text appears as soon as its source lookup completes, while the short tool-result acknowledgement finishes. No artificial typing delays or reasoning text are displayed. Partial output is not stored; only the completed exchange is saved.

Intent recognition tolerates selected common variants, such as standalone `ui`/`oiii`, `td bm`, `vcs`, `qto`, `violau` and `devouver`. This is a bounded alias map, not universal spelling correction. Original messages, product names, prices, order numbers and emails are not rewritten for lookup; unfamiliar/ambiguous model names still require clarification. A compound typo greeting cannot bypass required commercial source checks.

**Local-history privacy:** messages, including emails typed for a demo order, are stored unencrypted in `.local/conversations.sqlite3`. Titles redact emails; saved traces use a metadata whitelist and exclude raw tool payloads and reasoning. The folder and SQLite files are ignored by Git. This is a single-user demonstration, without accounts or production authentication. Use a trusted machine. Chat deletion is logical database deletion, not guaranteed forensic erasure from disk or backups. History created in this interface survives application/process restarts; earlier memory-only sessions are not automatically imported.

For policy retrieval, ask **"Comprei um violão e me arrependi. Posso devolver?"** and then **"Foi online."**. Expected behavior: consult section 4, page 4; ask for the purchase channel first, then the actual receipt date, and avoid approving a return with incomplete information. Other useful questions concern store hours, the address, installment conditions and delivery for exactly R$ 500. Expected behavior is distinct from the observed evidence linked above.

### Offline tests and real-model check

The `unittest` suite uses the real CSV/PDF sources and a simulated model. Install the dependencies first; no running model, API key or network is needed for these tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Separately, run the first acceptance scenario against the actual Ollama model:

```powershell
.\.venv\Scripts\python.exe scripts/check_catalog.py --output tmp/catalog-smoke.json
```

The command exits with status 0 when its checks pass and 1 when they fail. It records the displayed answer, tool arguments/results, latency and whether reasoning output was observed. It does not record reasoning text. Passing these checks does not prove every generated claim is correct; the answer still needs review against the returned records.

Run the separate two-turn return-policy acceptance scenario against the actual model:

```powershell
.\.venv\Scripts\python.exe scripts/check_policies.py --output tmp/policy-smoke.json
```

It checks retrieval of chapter 4/page 4, the purchase-channel question, the receipt-date follow-up, conversation history and source references. Review the actual answers for correctness and naturalness in addition to the structural checks.

Run the separate three-turn promotion/PIX/budget scenario:

```powershell
.\.venv\Scripts\python.exe scripts/check_pricing.py --output tmp/pricing-smoke.json
```

It asks the price of the Kalani KAL-700T Tenor Natural, follows up about PIX, then checks a R$ 340 budget. The supplied data gives a R$ 359,00 original price, 10% promotion and R$ 323,10 final price, unchanged by PIX. The script records fresh source lookups on each turn; structural checks still require manual answer review.

Run the separate order-number/email conversation and unsuccessful verification cases:

```powershell
.\.venv\Scripts\python.exe scripts/check_orders.py --output tmp/orders-smoke.json
```

The script uses supplied demo order 11, checks the historical total and absent tracking/date fields, and compares denials for a wrong email and a nonexistent order. It reads the matching demo email locally and redacts all emails from the saved evidence and terminal output. Order results and the model's discarded reasoning are distinct: the application renders order replies from verified Python fields, not from the model draft.

Run the additional quality scenarios:

```powershell
.\.venv\Scripts\python.exe scripts/check_quality.py --output tmp/quality-smoke.json
```

This checks neutral catalog wording and string types, a steel-string follow-up, unavailable/unknown products, an off-topic redirect and recovery from an unavailable local model endpoint. Off-topic requests can be redirected without a model call. Review individual outputs and source filters; these scenarios do not establish universal reliability.

Check greeting latency, actual streamed musical text and early verified catalog output separately:

```powershell
.\.venv\Scripts\python.exe scripts/check_responsiveness.py --output tmp/responsiveness-smoke.json
```

The greeting bypasses inference. Other scenarios use the actual model and record first-preview/completion timings and workflow events, without saving reasoning or intermediate model text. These are backend observations, not browser end-to-end measurements or general performance guarantees.

### Optional configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen3:4b` | Installed local model to request. |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Local Ollama endpoint. |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Positive, finite HTTP timeout in seconds. |
| `ZUBUMAFU_HISTORY_PATH` | `.local/conversations.sqlite3` under the project root | Alternate local SQLite history path; useful for isolated UI tests. |

Set variables in the terminal before starting the app, for example `$env:OLLAMA_TIMEOUT_SECONDS = "120"`. No `.env` file is automatically loaded. No API key is required for the default local configuration.

## Project map

| Path | Responsibility |
| --- | --- |
| `app.py` | Calls the UI entry point on every Streamlit rerun. |
| `zubumafu/streamlit_ui.py` | Messaging layout, thread selection/deletion, scenario buttons and source evidence. |
| `zubumafu/ui_theme.py` | Light/dark/system palettes for app controls, messages and navigation. |
| `zubumafu/input_understanding.py` | Bounded greeting/intent aliases without rewriting lookup identities. |
| `zubumafu/conversations.py` | Atomic SQLite exchanges, independent thread IDs, safe trace metadata and scoped deletion. |
| `zubumafu/demo_scenarios.py` | Seven prompt/criteria templates, without seeded or fabricated answers. |
| `zubumafu/recorded_examples.py` | Read-only review of four previously recorded acceptance conversations. |
| `zubumafu/response_quality.py` | Source-based catalog/price presentation, explicit budget comparison and bounded output cleanup. |
| `zubumafu/agent.py` | Bounded model/tool loop and customer-facing output handling. |
| `zubumafu/model.py` | Local SDK configuration, streamed tool aggregation and private-reasoning buffering. |
| `zubumafu/persona.py` | Persona, scope and instructions to use verified store facts. |
| `zubumafu/catalog.py` | Read-only CSV search, input validation, filters and BRL display formatting. |
| `zubumafu/pricing.py` | Promotion lookup, non-cumulative PIX rules and deterministic rounded BRL prices. |
| `zubumafu/policies.py` | Original PDF extraction, ten chapter boundaries, topic matching, page provenance and ambiguity warnings. |
| `zubumafu/orders.py` | Read-only order lookup, customer-bound credential checks, narrow dialogue context and controlled order rendering. |
| `tests/` | Offline catalog, policy, pricing, order and orchestration regression tests. |
| `scripts/check_catalog.py` | Opt-in acceptance check against the actual local model. |
| `scripts/check_policies.py` | Opt-in two-turn return-policy acceptance check against the actual local model. |
| `scripts/check_pricing.py` | Opt-in three-turn promotion, PIX and budget acceptance check against the actual local model. |
| `scripts/check_orders.py` | Opt-in order dialogue and unsuccessful-verification checks; evidence redacts emails. |
| `scripts/check_quality.py` | Opt-in quality scenarios and actual unavailable-endpoint recovery. |
| `docs/` | Decisions, observed validation and the next development steps. |
| `examples/` | Recorded interactions as they are validated; final coverage is pending. |
| `data/` | Original supplied datasets and store policies. |
| `desafio_tecnico_ai_eng_artefact.pdf` | Original challenge brief. |

## Data and tools

`search_products` reads the supplied products/categories/promotions CSVs and filters by category, a literal search phrase in names/descriptions/specifications, budget and stock. The budget and ordering use the **final** eligible price, including the PIX discount when `payment_method="pix"`. The legacy `price_brl` and `price_display_brl` fields retain the original price; `final_price_brl` and `final_price_display_brl` give the effective price. The filter trace explicitly identifies this budget meaning. The tool returns up to six records and the full match count; the persona requests at most three suggestions. Search is literal, not semantic, so synonyms and multiword feature combinations can miss matches.

`get_product_pricing` resolves an exact product ID or full/partial model name and calculates its original price, active promotion, discount and final price. Ambiguous names need clarification. A single active promotion takes precedence; the manual's 5% PIX discount applies only to a product without an active promotion. Discounts are never stacked. Multiple active promotions for one product produce an ambiguity, rather than silently choosing or adding them. Budget searches exclude records whose final price cannot be established. Calculations use `Decimal` with `ROUND_HALF_UP` at the final cent, then reconcile the displayed discount against the original price. The original CSV prices already have two decimal places.

Only `is_active` determines promotion activity: the source has no campaign dates, so the assistant cannot promise expiry dates. Prices and sources are visible in the expandable tool evidence. This feature does not calculate installment schedules, freight, cart totals or historical order prices.

Catalog and pricing replies now use structured Python renderers after the real model/tool round-trip. They replace the draft, rather than supplementing missing fields as earlier milestones did. Trace origins are `python_catalog_result_template` and `python_pricing_result_template`. Catalog suggestions retain source names and distinguish nylon/steel per instrument, without inferring the customer's experience or claiming a quality ranking. Source filters distinguish an unknown name from unavailable inventory, budget/category constraints and unconfirmed pricing. A missing or ambiguous product price asks for clarification. This favors predictable factual output over unconstrained musical recommendation prose.

Recognized intents limit the tools advertised to the model. A single-product price/PIX/budget question advertises the pricing tool; general product-list questions can use catalog search. A literal request to pay via PIX sets that method in the deterministic calculation if the model omitted it, with `argument_overrides` in the trace. Intent routing, payment phrase matching and explicit BRL budget parsing remain narrow heuristics. A skipped fresh lookup gets one verification reminder, including after a source-free truncated draft, within the same three-request cap. Repeated failure returns a fallback rather than an invented answer.

A narrow follow-up such as "Which of these options have steel strings?" is resolved by the application: it re-queries only the up to three names displayed in the previous controlled catalog reply, carrying the previous budget/payment method, and filters the current source specifications. It makes no model request. The trace explicitly records `invoked_by: application_reference_lookup`; this is not presented as model-requested tool use or general reference understanding.

Price and stock values are from the supplied snapshot, not a live commerce integration. All seven original files under `data/` were preserved byte for byte when importing the prototype increments.

`search_store_policies` reads the original `data/políticas_da_loja.pdf`, recognizes its ten chapter headings and retains text continued on subsequent pages. It selects relevant chapters using a small topic/keyword map and returns PDF excerpts, 1-based pages, source version and clarification requirements. For defects, it includes the warranty chapter alongside return rules. This is a purpose-built retriever for the supplied manual, not a general semantic PDF search engine; compound questions can require more than one lookup.

The tool flags conflicting contact numbers, inconsistent installment minimums and the undefined local-delivery boundary of exactly R$ 500. These warnings do not silently resolve the source. Policy citations are appended by Python from successful tool results, with each chapter mapped to its actual pages. Catalog, promotion and PDF reads are cached for the Python process; restart the app after changing source files.

For an explicit regret conversation with missing purchase information, Python controls two clarification questions after a successful return-policy lookup and the model/tool round-trip: purchase channel first, then actual receipt date for an online purchase. These displayed questions use short templates rather than an unconstrained model draft. The trace marks `reply_origin: source_verified_clarification_template` and the missing field. This prevents the draft from skipping those questions or inventing a return-submission procedure. It is conservative phrase matching, not a general date parser or an eligibility decision engine.

`get_order_status` joins the original orders, customers, order items and product names. It asks for an order number first, then its registered email, and matches the order-to-customer association in Python before returning details. A nonexistent order and an incompatible email produce the same generic denial. Successful results contain only status, instruments/quantities, historical total and optional tracking/estimated-delivery fields. They exclude email, customer ID, phone, internal notes and payment details. The stored total is never recalculated using current promotions; the source has no historical unit-price fields.

The agent binds order-tool arguments to credentials supplied in customer messages in the current narrow order flow. Assistant text and model guesses cannot supply missing credentials. A new order number clears the previous email; changing subject closes the flow. This is heuristic context handling, not a general identity system. Order number plus email is **demo-only verification, not production authentication**. The original sources are supplied demonstration data in a public challenge repository; do not use this design for real customer records.

After the tool result is returned to the model, Python renders the order response or denial and discards the model draft, marking `reply_origin: python_order_result_template`. A missing-credential question may also be supplied directly when the model makes no tool call; that is not recorded as a model-requested lookup. Missing carrier codes/dates remain absent; historical forecasts do not prove actual receipt or promise a current delivery. No live tracking, cancellations, refunds or record mutations are available. The interface trace excludes the email, but the original customer message is stored in the unencrypted local history and sent to the configured Ollama endpoint. Order CSV reads are cached; restart after changing the files.

No external source is used for store facts. General musical knowledge may assist in explanations; specific claims about artists or equipment are not verified by this dataset and must not be invented.

## Known limitations

- Catalog, policies, promotion/PIX pricing and demonstrative order lookup are implemented. Installment and freight calculations remain outside the current implementation.
- Automated tests with a simulated model and actual model acceptance runs are separate evidence. This limited sample does not establish reliability, latency across workloads or full challenge compliance.
- The installed Qwen3 4B template emitted reasoning despite requests with `think=False`. The application also uses `/no_think` as a steering instruction and strips labeled reasoning from visible content. This is an output safeguard, not proof that reasoning generation was disabled. Latency remains a limitation.
- Each reply is bounded to three model requests, five tools per request and a 4,096-token context. Initial requests allow at most 2,048 generated tokens; the acknowledgement after a controlled source lookup allows 64. The visible history includes at most 12 prior messages; long conversations can exceed the context budget. Truncated source-free drafts produce a fallback; completed verified fields can still render a controlled reply after a truncated acknowledgement.
- Source-intent checks are heuristic. Policy questions require the PDF tool; product prices require a fresh catalog or pricing lookup. A general policy lookup alone cannot authorize a specific product quote. Return follow-ups about channel/receipt retain their policy context; price/PIX follow-ups use recent conversation context. The code does not yet verify every generated factual statement, product reference or model-written citation against tool results.
- Historical catalog runs assumed a beginner profile and mixed nylon/steel descriptions. Controlled product replies address those particular errors; general musical and policy prose still needs broader evaluation. Historical transcripts are retained as observed evidence, not rewritten to suggest the fixes existed earlier.
- The interface provides local durable history and demonstrative order/email matching, without production authentication or rate limits. Context heuristics can miss phrasing; start a new conversation or restate the order number when necessary.
- Streamlit AppTest checks interaction state, not CSS, real-browser responsiveness or mobile appearance. Visual review remains pending because no browser was connected; the user deferred the Edge connection.
- Conflicting contacts and installment rules, and the missing exact R$ 500 freight case, are explicitly flagged. The prototype does not resolve those policies or approve, reject or register return requests.
- Monetary values use the static CSV source. Do not claim live stock or external tracking.
- Tool errors, prompt injection and out-of-scope behavior require further hardening and testing.

## What would be done with more time

Automated grounding checks, broader dialog evaluation, latency improvements and a production authentication/authorization design for any future real-customer deployment.

## AI assistance disclosure

ChatGPT (OpenAI) assisted with planning, architecture decisions, drafting Python code/tests and the policy/pricing/order/quality/UI increments, and reviewing documentation. Codex integrated those older snapshots into the canonical repository, preserved/extended regressions, bound order credentials and explicit PIX requests, corrected source/output handling and SQLite/Streamlit integration, and ran local model and AppTest checks. The local inference model is Qwen3 4B via Ollama. Recorded validation distinguishes simulated tests, actual model requests, controlled application replies and the pending browser review; conversations are not fabricated.

## Submission checklist (not yet completed)

- [ ] All required scope functions implemented and validated.
- [x] Four **real** interaction transcripts with English translations and source evidence; final coverage/quality review remains pending.
- [x] Public GitHub repository initialized; the initial and imported prototype commits are preserved.
- [ ] Final README and decisions reviewed in English.
- [ ] Repo frozen after submission (no post-deadline changes).

Refer to the provided challenge PDF for official requirements; the project guide is supplementary planning material. The submission channel and exact deadline still need final confirmation.
