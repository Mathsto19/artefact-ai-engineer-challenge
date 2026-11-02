# Zubumafu — Music Store AI Assistant

**Status: early functional prototype; not ready for delivery.**

Zubumafu is an experimental text-based customer assistant for **Empório da Música**, the fictional music store in Artefact's AI Engineer challenge. It speaks Brazilian Portuguese with a warm, musical and professional personality. The current milestone offers catalog searches, retrieval from the original store-policy PDF, deterministic promotion/PIX pricing and demonstrative order consultation. Tool results are returned to the model; verified chapter/page references are appended to policy replies. Final quality and submission review remain pending.

## Stack and rationale

| Choice | Rationale |
| --- | --- |
| Python | Required primary language; keeps querying and validation deterministic. |
| Streamlit | Small chat UI without a separate frontend application. |
| Ollama + `qwen3:4b` | Runs without an API key or per-request fee on the developer's laptop. This is a candidate, not a quality benchmark. |
| Python tool calling | CSV filtering stays in code while the model handles intent and language. |
| Session-only memory | Enough for a prototype without the overhead of storing conversation histories. |
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

Ask **"Quais violões disponíveis custam até R$ 1000?"**. Expand **"Consultas realizadas"** to inspect the executed tool, filters, source and number of matches. Use **"Nova conversa"** to reset the session.

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

### Optional configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen3:4b` | Installed local model to request. |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Local Ollama endpoint. |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Positive, finite HTTP timeout in seconds. |

Set variables in the terminal before starting the app, for example `$env:OLLAMA_TIMEOUT_SECONDS = "120"`. No `.env` file is automatically loaded. No API key is required for the default local configuration.

## Project map

| Path | Responsibility |
| --- | --- |
| `app.py` | Streamlit chat, session history, tool evidence and recoverable error messages. |
| `zubumafu/agent.py` | Bounded model/tool loop and customer-facing output handling. |
| `zubumafu/model.py` | Lazy SDK import, local endpoint and timeout configuration. |
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
| `docs/` | Decisions, observed validation and the next development steps. |
| `examples/` | Recorded interactions as they are validated; final coverage is pending. |
| `data/` | Original supplied datasets and store policies. |
| `desafio_tecnico_ai_eng_artefact.pdf` | Original challenge brief. |

## Data and tools

`search_products` reads the supplied products/categories/promotions CSVs and filters by category, a literal search phrase in names/descriptions/specifications, budget and stock. The budget and ordering use the **final** eligible price, including the PIX discount when `payment_method="pix"`. The legacy `price_brl` and `price_display_brl` fields retain the original price; `final_price_brl` and `final_price_display_brl` give the effective price. The filter trace explicitly identifies this budget meaning. The tool returns up to six records and the full match count; the persona requests at most three suggestions. Search is literal, not semantic, so synonyms and multiword feature combinations can miss matches.

`get_product_pricing` resolves an exact product ID or full/partial model name and calculates its original price, active promotion, discount and final price. Ambiguous names need clarification. A single active promotion takes precedence; the manual's 5% PIX discount applies only to a product without an active promotion. Discounts are never stacked. Multiple active promotions for one product produce an ambiguity, rather than silently choosing or adding them. Budget searches exclude records whose final price cannot be established. Calculations use `Decimal` with `ROUND_HALF_UP` at the final cent, then reconcile the displayed discount against the original price. The original CSV prices already have two decimal places.

Only `is_active` determines promotion activity: the source has no campaign dates, so the assistant cannot promise expiry dates. Prices and sources are visible in the expandable tool evidence. This feature does not calculate installment schedules, freight, cart totals or historical order prices.

If a single-model promotional quote omits the original price, percentage or final price, Python adds the missing fields from the successful tool result. The trace marks `reply_origin: model_with_source_price_details` and `added_price_fields`. This checks completeness; it does not validate every claim in the model draft. When the first model reply skips a required fresh lookup, one verification reminder can request that lookup within the existing three-request limit. If verification still fails, the customer receives a fallback.

Price and stock values are from the supplied snapshot, not a live commerce integration. All seven original files under `data/` were preserved byte for byte when importing the prototype increments.

`search_store_policies` reads the original `data/políticas_da_loja.pdf`, recognizes its ten chapter headings and retains text continued on subsequent pages. It selects relevant chapters using a small topic/keyword map and returns PDF excerpts, 1-based pages, source version and clarification requirements. For defects, it includes the warranty chapter alongside return rules. This is a purpose-built retriever for the supplied manual, not a general semantic PDF search engine; compound questions can require more than one lookup.

The tool flags conflicting contact numbers, inconsistent installment minimums and the undefined local-delivery boundary of exactly R$ 500. These warnings do not silently resolve the source. Policy citations are appended by Python from successful tool results, with each chapter mapped to its actual pages. Catalog, promotion and PDF reads are cached for the Python process; restart the app after changing source files.

For an explicit regret conversation with missing purchase information, Python controls two clarification questions after a successful return-policy lookup and the model/tool round-trip: purchase channel first, then actual receipt date for an online purchase. These displayed questions use short templates rather than an unconstrained model draft. The trace marks `reply_origin: source_verified_clarification_template` and the missing field. This prevents the draft from skipping those questions or inventing a return-submission procedure. It is conservative phrase matching, not a general date parser or an eligibility decision engine.

`get_order_status` joins the original orders, customers, order items and product names. It asks for an order number first, then its registered email, and matches the order-to-customer association in Python before returning details. A nonexistent order and an incompatible email produce the same generic denial. Successful results contain only status, instruments/quantities, historical total and optional tracking/estimated-delivery fields. They exclude email, customer ID, phone, internal notes and payment details. The stored total is never recalculated using current promotions; the source has no historical unit-price fields.

The agent binds order-tool arguments to credentials supplied in customer messages in the current narrow order flow. Assistant text and model guesses cannot supply missing credentials. A new order number clears the previous email; changing subject closes the flow. This is heuristic context handling, not a general identity system. Order number plus email is **demo-only verification, not production authentication**. The original sources are supplied demonstration data in a public challenge repository; do not use this design for real customer records.

After the tool result is returned to the model, Python renders the order response or denial and discards the model draft, marking `reply_origin: python_order_result_template`. A missing-credential question may also be supplied directly when the model makes no tool call; that is not recorded as a model-requested lookup. Missing carrier codes/dates remain absent; historical forecasts do not prove actual receipt or promise a current delivery. No live tracking, cancellations, refunds or record mutations are available. The interface trace excludes the email, but the customer's original message remains in session memory and is sent to the configured Ollama endpoint. Order CSV reads are cached; restart after changing the files.

No external source is used for store facts. General musical knowledge may assist in explanations; specific claims about artists or equipment are not verified by this dataset and must not be invented.

## Known limitations

- Catalog, policies, promotion/PIX pricing and demonstrative order lookup are implemented. Installment and freight calculations remain outside the current implementation.
- Automated tests with a simulated model and actual model acceptance runs are separate evidence. This limited sample does not establish reliability, latency across workloads or full challenge compliance.
- The installed Qwen3 4B template emitted reasoning despite requests with `think=False`. The application also uses `/no_think` as a steering instruction and strips labeled reasoning from visible content. This is an output safeguard, not proof that reasoning generation was disabled. Latency remains a limitation.
- Each reply is bounded to three model requests, five tools per request, 2,048 generated tokens per request and a 4,096-token context. The visible history includes at most 12 previous messages in each request; long conversations can exceed the context budget. Truncated model drafts produce a fallback; verified order replies can still be safely rendered from the completed tool result.
- Source-intent checks are heuristic. Policy questions require the PDF tool; product prices require a fresh catalog or pricing lookup. A general policy lookup alone cannot authorize a specific product quote. Return follow-ups about channel/receipt retain their policy context; price/PIX follow-ups use recent conversation context. The code does not yet verify every generated factual statement, product reference or model-written citation against tool results.
- The first observed answer focused on beginners even though the customer had not specified experience. Persona instructions discourage this assumption, but instructions alone do not guarantee compliance.
- The interface provides only demonstrative order/email matching, without production authentication, rate limits or durable persistence. Context heuristics can miss phrasing; start a new conversation or restate the order number when necessary.
- Conflicting contacts and installment rules, and the missing exact R$ 500 freight case, are explicitly flagged. The prototype does not resolve those policies or approve, reject or register return requests.
- Monetary values use the static CSV source. Do not claim live stock or external tracking.
- Tool errors, prompt injection and out-of-scope behavior require further hardening and testing.

## What would be done with more time

Automated grounding checks, broader dialog evaluation, latency improvements and a production authentication/authorization design for any future real-customer deployment.

## AI assistance disclosure

ChatGPT (OpenAI) assisted with planning, architecture decisions, drafting the initial Python code/tests and the policy/pricing/order increments, and reviewing documentation. Codex assisted with the original material review and repository setup, integrated the prototype history and subsequent increments into the existing repository, preserved and extended the regression tests, bound order lookups to customer-provided credentials, corrected tool/output handling, and ran local model and interface checks. The local inference model is Qwen3 4B via Ollama. Recorded validation distinguishes simulated model tests from real requests; example conversations must not be fabricated.

## Submission checklist (not yet completed)

- [ ] All required scope functions implemented and validated.
- [x] Four **real** interaction transcripts with English translations and source evidence; final coverage/quality review remains pending.
- [x] Public GitHub repository initialized; the initial and imported prototype commits are preserved.
- [ ] Final README and decisions reviewed in English.
- [ ] Repo frozen after submission (no post-deadline changes).

Refer to the provided challenge PDF for official requirements; the project guide is supplementary planning material. The submission channel and exact deadline still need final confirmation.
