# Validation log

Observed on **2 November 2026**, using São Paulo time (UTC-03:00). The first sections record the original catalog milestone; subsequent policy/pricing results are appended below. This does not validate the complete challenge.

## Source integrity and Git history

- The prototype ZIP passed its CRC integrity check.
- Its seven `data/` files matched the existing source files byte for byte, using SHA-256 comparisons.
- The existing first commit and both prototype commits were preserved through a merge. The ZIP's Git configuration and hooks were not copied over the working repository.
- Temporary import artifacts, the virtual environment and internal planning/ZIP files are ignored by Git.

## Offline unit tests

Command:

```powershell
python -m unittest discover -s tests -v
```

Result: **16 tests passed**, including the six original tests. The tests use real CSV records and a simulated model, with no running Ollama or third-party Python packages required.

Coverage includes budget/stock/category filters, missing products, malformed arguments, specification searches, BRL display, successful tool round-trips, failed/rejected lookups, additional instrument categories, bounded repeated calls, excessive tool batches, reasoning-markup handling and incomplete generations.

The added regressions reproduced actual weaknesses before correction: failed/rejected tool requests could authorize catalog answers; some instrument names bypassed the lookup guard; malformed input types were not consistently rejected; and specifications were not searched despite the tool description.

## Actual local model interaction

Command:

```powershell
.\.venv\Scripts\python.exe scripts/check_catalog.py --output tmp/catalog-smoke.json
```

Environment: Python 3.12.10; Ollama server 0.40.13; Ollama Python SDK 0.6.3; original `qwen3:4b` model, ID `359d7dd4bcda`, Q4_K_M. The runtime reported full GPU residency for the loaded 4B model; this is not a throughput benchmark.

Recorded interaction: **2026-11-02 15:11:33 -03:00**. Question: "Quais violões disponíveis custam até R$ 1.000?"

Result: **the initial acceptance script passed**, with two actual model requests and **40.50 seconds** elapsed in this one run. The model requested `search_products(category="violão", max_price_brl=1000, available_only=True)`, Python executed it, and the resulting JSON was supplied in a tool-role message before the final answer.

The query found 12 matching records, supplied six to the model and displayed these three:

| Product | Displayed price | CSV stock | CSV status |
| --- | --- | --- | --- |
| Tagima Memphis AC-39 Nylon Natural | R$ 429,90 | 15 | active |
| Rozini RC-104 Nylon Estudante | R$ 459,90 | 10 | active |
| Yamaha C40 Nylon Natural | R$ 599,90 | 12 | active |

These product names and prices were checked against the returned source records. This is a static snapshot lookup, not a live inventory integration. The generated answer's general descriptive language is not exhaustively machine-verified; it also assumed a beginner profile the customer had not specified.

Artifacts:

- [Observed dialogue with a separate English translation](../examples/01_catalog_budget.md).
- [Machine-readable answer, tool results and request metrics](../examples/01_catalog_budget.json).

## Reasoning and generation limits

The first real request correctly called the tool but exposed reasoning in visible content despite `think=False`; the overall cycle took 59.27 seconds. The installed model's `/api/show` response advertised `thinking.values: [true]`. Prompt steering alone did not reliably eliminate that output.

A trial generation cap of 600 tokens cut off a response before a usable final answer. That run failed acceptance and was not presented as success. The current cap is 2,048 tokens per model request, with at most three requests and five tools per request. Incomplete final generations and unfinished labeled reasoning produce a fallback.

In the recorded passing run, the backend still produced reasoning output, which the application removed before displaying the final answer. Both requests sent `think=False`; this establishes what was requested, not that reasoning generation was disabled. The final answer contained no thinking markup. Raw reasoning is not included in the published artifacts.

## Streamlit and environment checks

- Streamlit 1.66.1 AppTest: initial screen and chat input loaded without app exceptions.
- With a simulated backend: a customer question and assistant answer appeared, source/filter evidence was rendered, and "Nova conversa" cleared the history.
- With a simulated backend failure: a recoverable customer message was displayed and recorded in the session instead of an app crash.
- `python -m pip check` in `.venv`: no broken requirements found.
- The local Streamlit server returned HTTP 200 at `/` and HTTP 200 with `ok` at `/_stcore/health`, on `127.0.0.1:8501`.

AppTest checks the Streamlit application state without a browser. The actual model acceptance above ran through the same agent function separately; the interface simulation did not call a real model.

## Remaining work after the original catalog milestone

Policy retrieval, promotions and pricing rules, an explicit decision about order lookup, broader scope/error evaluation and 3–5 distinct observed conversations remain pending. Context pressure, latency, reasoning controls and unsupported factual claims require further evaluation. No general reliability score or production readiness is claimed.

## Policy milestone - integration and offline tests

The incoming policy ZIP was based on `9929359`, preceding the refinements already published in this repository. Its two new source/test files and policy changes were integrated without replacing the current agent, catalog corrections, pinned dependencies or existing tests. The seven original data files again matched by SHA-256. The ZIP's `.git` directory was not imported over the existing repository.

The updated suite was run with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: **41 tests passed**, including all 16 previous regressions. Tests now require the installed pypdf dependency, but no running model, API key or network. They cover all ten extracted chapters, chapter continuations, exact source references, return context, three ambiguity warnings, PDF read failures, wrong-tool authorization, follow-up history, explicit clarification control and acceptance-check regressions.

Dependency versions remain pinned, adding pypdf 6.21.4 to both the direct requirements and resolved constraints. `pip check` reported no broken requirements.

## First actual policy trial - rejected on manual review

The first two-turn trial retrieved chapter 4/page 4 correctly on both turns, in 46.98 and 37.62 seconds. The second reply, however, asked about packaging and signs of use instead of the actual receipt date. It also invented a step to follow a process in the online store, which the source did not describe.

The initial automated receipt-date check was too weak: it accepted a mention of the seven-day receipt-based rule plus an unrelated question. The command returned success, but **manual review rejected the interaction**. The checker was corrected to inspect the actual date question, and regression tests distinguish that from a packaging question or a yes/no receipt question.

For an explicit regret dialogue with missing channel/receipt information, Python now enforces those two clarification questions after the successful PDF lookup and actual model/tool round-trip. The trace records the missing field and `reply_origin: source_verified_clarification_template`. These are intentionally controlled customer replies, not evidence that the model independently followed every instruction. Only customer messages can provide purchase facts; no return is approved or registered. This narrow phrase matching is not a general eligibility/date engine.

## Actual policy acceptance after correction

Command:

```powershell
.\.venv\Scripts\python.exe scripts/check_policies.py --output tmp/policy-smoke.json
```

Observed at **2026-11-02 16:10:45 -03:00**, using the original local `qwen3:4b` model through Ollama 0.40.13, SDK 0.6.3, Python 3.12.10 and pypdf 6.21.4.

| Turn | Customer input | Displayed behavior | Source | Elapsed |
| --- | --- | --- | --- | --- |
| 1 | Regret after buying an acoustic guitar; can it be returned? | Asked whether the purchase was online or in the physical store. | Chapter 4, page 4 | 53.68 s |
| 2 | "Foi online." | Retained context and asked when the instrument was received. | Chapter 4, page 4 | 74.47 s |

Each turn made two actual model requests. Both retrieved the original PDF text, returned it to the model and appended verified references. The final answers asked one clarification at a time, did not approve the return and did not invent a storefront procedure. Their wording was controlled by Python as described above. All 11 structural checks passed, and the displayed replies were manually reviewed.

The backend still emitted reasoning despite `think=False`; it was filtered from customer output and is not included in published artifacts. These timings are individual observations, not a performance benchmark.

Artifacts: [actual bilingual dialogue](../examples/02_return_policy.md) and [machine-readable evidence](../examples/02_return_policy.json).

## Catalog regression after enabling the second tool

The actual catalog acceptance script was rerun because the available tool set and source guards changed. At **2026-11-02 16:13:08 -03:00**, it passed its tool/filter/record checks: 12 matching acoustic guitars, six records returned to the model and three displayed names/prices matching the source. Elapsed time was **80.41 seconds** in that run.

The generated text still assumed a beginner profile and claimed the models were popular with beginners without supporting sales/demand data. Consequently this is a passing **tool-cycle and product-record check**, not a full factuality/persona pass. The evidence is retained in [catalog regression JSON](evidence/catalog_after_policies.json), and these qualitative issues remain open.

## Policy interface check

Streamlit AppTest with a simulated backend verified two chat turns, history passed to the second request, and PDF chapter/page references displayed in the expandable evidence. The earlier catalog/reset/backend-failure interface checks also passed with the new integration. The model acceptance runs above are separate from that interface simulation.

## Remaining work after the policy milestone

Next: product-specific promotions and deterministic price rules, including non-cumulative discounts. An explicit decision on order lookup, broader error/out-of-scope and factuality checks, latency/thinking improvements, and a total of 3–5 distinct observed conversations remain pending. Two distinct conversations are now recorded; rerunning the catalog question is a regression check, not a third distinct example. No final submission has been performed.

## Pricing milestone - integration and offline verification

The third ZIP again started from `9929359`. Only the new pricing module/tests and relevant incremental changes were integrated; current policy controls, dependency pins, history and regression tests were retained. Archive CRC passed and all seven original data files matched by SHA-256. No ZIP Git configuration was imported.

The offline suite passed **61 tests**, including the previous 41. New coverage includes active/inactive promotions, non-cumulative PIX, PIX on a non-promotional product, final-price budget filtering, cent rounding/reconciliation, multiple active promotions, ambiguous/missing product names, invalid discounts/payment methods/IDs, fresh price lookups, wrong-source authorization, missing promotion fields and bounded verification recovery. The existing policy/clarification tests still passed. `pip check` reported no broken requirements; no new dependencies were added.

Real-data arithmetic checks confirmed Kalani KAL-700T: R$ 359.00, 10%, R$ 323.10; Ohana CK-20: R$ 549.00, 20%, R$ 439.20. A R$ 340 budget finds the Kalani using its final price. PIX on non-promotional product 145 gives R$ 11,875.00 from R$ 12,500.00. A synthetic R$ 1,100/10% example gives R$ 990.00. These Python checks are separate from model behavior.

## First actual pricing trial - rejected

The three turns took **69.80, 79.32 and 96.55 seconds**. The first retrieved the correct Kalani through `search_products` and quoted R$ 323.10/10%, but omitted the original price. The second used `get_product_pricing(payment_method="pix")`, retained the product context and correctly denied an extra discount. The third did not request a fresh tool lookup; the application returned a verification fallback instead of allowing an unverified budget answer. The interaction was not accepted.

Both product tools share the deterministic calculator, so either can ground a quote. The acceptance checker now requires the dedicated pricing tool on the PIX turn, while allowing either product tool on the initial quote and budget turn. It also recognizes the observed wording "não adiciona desconto extra"; the earlier phrase check missed that correct explanation. These checker adjustments do not make the missing original price or source-free third turn acceptable.

Python now supplements missing original/percentage/final fields in a single-product promotional quote from verified tool results, tagging the added fields and `reply_origin: model_with_source_price_details`. It does not claim to validate all generated assertions. A first reply that skips a required source lookup gets one verification reminder, within the unchanged three-request cap. A repeated failure still produces a fallback. The offline tests exercise both safeguards.

## Pricing interface and environment verification

Streamlit AppTest with a simulated backend rendered the chat, product ID 127, final price R$ 323.10, non-cumulative PIX flag and all three source entries in expandable pricing evidence, without app exceptions. This was a UI simulation using real pricing records, not a real-model conversation. The running local server also returned HTTP 200/`ok` at `/_stcore/health`.

## Actual pricing acceptance after correction

Command:

```powershell
.\.venv\Scripts\python.exe scripts/check_pricing.py --output tmp/pricing-smoke.json
```

Recorded at **2026-11-02 17:03:17 -03:00**, with the same original `qwen3:4b`, Ollama 0.40.13, SDK 0.6.3 and Python 3.12.10.

| Turn | Observed source use | Displayed outcome | Elapsed |
| --- | --- | --- | --- |
| Kalani price | `search_products`, exact model query | R$ 359.00 original, 10% promotion, R$ 323.10 final; 11 units in the snapshot. | 62.22 s |
| PIX follow-up | `get_product_pricing`, same model, `payment_method="pix"` | R$ 323.10 unchanged; no extra discount. | 101.95 s |
| R$ 340 budget | Fresh `get_product_pricing`, same model | Confirmed that R$ 323.10 fits the budget. | 140.06 s |

All **11 structural checks passed**. Each turn executed a source lookup and returned its result to the actual model. The first answer's original-price line was added by Python, explicitly tagged in the trace. The second turn needed the bounded verification reminder before calling the pricing tool; it used three model requests. Turns 1 and 3 used two requests each. No extra PIX discount, promotion expiry date or purchase action was claimed. Manual review accepted the commercial facts and budget outcome.

The second reply's "Se quiser economizar" sentence is awkward and potentially confusing, since PIX offers no extra saving on this promotion. Repeated suggestions and emojis also need refinement. Accordingly this is a **functional price/discount acceptance**, not a full persona/quality pass. Reasoning still appeared despite `think=False` and was filtered rather than published. The high individual response times remain a material limitation.

Artifacts: [actual bilingual conversation](../examples/03_promotion_pix_budget.md) and [full answer/tool evidence without reasoning](../examples/03_promotion_pix_budget.json).

## Catalog regression after adding pricing

The catalog acceptance script was rerun because search results now include final-price fields and the model has a third tool. Recorded at **2026-11-02 17:06:06 -03:00**, the eight structural checks passed in **136.77 seconds**: the model queried available acoustic guitars up to R$ 1,000, received six of 12 matching records and displayed three matching names/prices (Tagima R$ 429.90, Rozini R$ 459.90, Shelby R$ 549.00).

Manual review again found persona/grounding defects: an unsolicited beginner assumption, an unsupported "three best" ranking and an opening nylon-string description despite the third suggestion having steel strings. This is a successful **source/filter/price regression**, not an overall factuality or persona pass. The observed answer is preserved in [catalog-after-pricing evidence](evidence/catalog_after_pricing.json); these text-quality issues remain unresolved.

## Current remaining work

Three distinct observed conversations are now recorded: catalog, returns and promotion/PIX/budget. This meets the example count's lower bound, but does not establish complete challenge coverage. Still pending: an explicit final decision on order consultation and access verification; out-of-scope, error and broader factuality/persona evaluation; latency/reasoning improvements; final clean setup, English documentation/submission materials and repository freeze after submission. Freight and installment calculations are not implemented. No final submission has been performed.
