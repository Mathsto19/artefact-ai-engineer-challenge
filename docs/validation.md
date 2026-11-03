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

## Remaining work after the pricing milestone

Three distinct observed conversations are now recorded: catalog, returns and promotion/PIX/budget. This meets the example count's lower bound, but does not establish complete challenge coverage. Still pending: an explicit final decision on order consultation and access verification; out-of-scope, error and broader factuality/persona evaluation; latency/reasoning improvements; final clean setup, English documentation/submission materials and repository freeze after submission. Freight and installment calculations are not implemented. No final submission has been performed.

## Order milestone - selective integration and regressions

The order ZIP passed CRC verification. Its seven original data files matched the canonical sources by SHA-256. Its older baseline was expected: only the new order module/tests/handoff and relevant agent/persona/interface changes were integrated. Current catalog/pricing/policy controls, dependency pins, history and evidence were preserved. No incoming Git configuration was imported.

The incoming package reported 40 passing tests (24 baseline plus 16 order tests); this was not claimed as validation of the canonical version. After integration and refinement, the canonical offline suite passed **89 tests**, including all 61 previous regressions and the 16 incoming order tests. The simulated successful agent test was updated to actually supply the customer's credentials; a model-provided email alone must not authorize details. Additional regressions cover guessed credentials, assistant-provided facts, stale valid email after an incorrect replacement, new-order resets, subject changes, incorrect source tools, malformed/truncated IDs, email text resembling an ID, source read errors, malformed tool arguments and truncated order drafts. `pip check` reported no broken requirements; no dependencies were added.

The agent now binds order-tool inputs to customer messages in a narrow dialogue flow before the CSV association check. Missing credentials are clarified one at a time. The order response/denial is constructed by Python from the verified structured result after the model/tool round-trip; model-invented totals, dates or delivery claims are discarded. The trace marks this origin and does not contain the email. This is demonstrative verification, not production authentication or a general conversation parser.

## Actual order acceptance

Command:

```powershell
.\.venv\Scripts\python.exe scripts/check_orders.py --output tmp/orders-smoke.json
```

Recorded at **2026-11-02 18:29:28 -03:00**, with original `qwen3:4b`, Python 3.12.10 and Ollama SDK 0.6.3. **All 16 structural checks passed**, followed by manual review of the final replies and source fields.

| Scenario | Observed behavior | Elapsed |
| --- | --- | --- |
| "Onde está meu pedido?" | Application asked for the order number after a source-free model draft; no lookup or order existence was claimed. | 12.26 s |
| Customer supplied 11 | Model called `get_order_status`; structured missing-email result led to the single email question. | 33.58 s |
| Registered demo email supplied | Model requested the order tool; its verified result reached the model; Python displayed historical order 11. | 14.61 s |
| Wrong email | Tool denied verification; application displayed the generic denial. | 19.76 s |
| Nonexistent order | Same structured denial and displayed text, without confirming existence. | 31.82 s |

The verified record was **confirmed**, with **1 × Kalani KAL-700T Tenor Natural** and a **R$ 359.00 historical total**. It was not repriced to today's R$ 323.10 promotional offer. Tracking and estimated delivery were both absent and explicitly described as unavailable. No actual receipt date or live tracking was invented. The reply contained no customer profile, internal notes or claimed mutation.

These are controlled application replies, not proof that the model draft was correct. The first turn made one real model request; each other scenario made two. Reasoning still appeared despite `think=False`, was filtered/discarded and was not recorded. Individual timings are not a benchmark or proof of a general performance improvement. Published evidence redacts the matching demo email and all email strings in the recorded requests/questions.

Artifacts: [observed dialogue and English translation](../examples/04_order_lookup.md), [redacted machine-readable evidence](../examples/04_order_lookup.json).

## Order interface check

Streamlit AppTest with a simulated backend verified the three-turn display, four prior messages passed to the final turn, historical total, safe order trace and conversation reset. It used the observed redacted answer/trace fixtures and did not call a real model. The initial test-harness attempt used a relative app path that resolved under `tmp/`; rerunning with the absolute app path passed without application changes.

## Policy regression after adding orders

The actual two-turn return-policy scenario was rerun because the fourth tool and order-context routing could otherwise interfere with policy guidance. At **2026-11-02 18:35:25 -03:00**, all 11 checks passed. The source lookup retrieved chapter 4/page 4 on both turns, and the application retained its controlled purchase-channel then receipt-date questions. Neither reply approved a return or disclosed order details. The regression took **32.48 and 34.20 seconds**; [machine-readable evidence](evidence/policies_after_orders.json) records the actual results and the continued reasoning limitation.

A separate offline regression verifies that "Me arrependi do meu pedido. Posso devolver?" stays in the PDF/return clarification flow despite mentioning an order. The narrow order context must not replace that established behavior with an unnecessary request for order credentials.

## Remaining work recorded after the order milestone

The selected functional scope now includes catalog, policies, promotions/PIX and demonstrative orders. Four distinct conversations are recorded; denial cases supplement the order example. Stop adding features and complete the final review: factuality/persona defects in catalog prose, broader out-of-scope/error behavior, latency/reasoning limits, clean setup, final English documentation and submission materials. Order verification remains demo-only; freight/installment calculations are excluded. No submission or repository freeze has occurred.

## Quality/UI milestone - selective integration and offline verification

The final-quality/UI ZIP was treated as an older baseline with a new increment. Archive CRC passed and all seven original data files matched the canonical sources by SHA-256. Existing policy/order protections, pinned dependencies, historical examples and Git history were retained. The package's 57-test result belongs to its own baseline, not the canonical checkout.

The integrated suite passed **119 offline tests**, including the preceding 89 regressions. Coverage includes source-based catalog/price rendering, neutral customer experience, per-record nylon/steel descriptions, no discount stacking, ambiguous prices, distinct no-result reasons, explicit PIX binding, bounded recovery after a truncated source-free draft, SDK transport failures, and reference filtering. Persistence checks cover atomic exchanges, separate threads, redacted/whitelisted trace metadata, logical scoped deletion and reopening the database from another Python process.

Streamlit AppTest verifies reruns, switching threads, reopening the app, personal/test isolation, cancel/confirm deletion, prompt-template launch, retained PDF evidence and saved backend-failure replies. These interface tests use a simulated backend, not Qwen3. The incoming import-only entrypoint was corrected to call `main()` on each rerun, and SQLite connections now close explicitly after each transaction. No new runtime dependencies were added; `pip check` passed.

### Actual trials and corrections

The original local `qwen3:4b` was retained. Initial pricing trials were rejected: the model guessed the wrong instrument category, omitted the explicit PIX method, or produced a truncated source-free follow-up. Intent-specific advertised tools, customer-bound PIX arguments, category-guess correction and the bounded verification retry addressed those observed paths. Catalog/price replies now discard the model draft and render the verified commercial fields in Python; this supersedes the earlier partial price supplement. Trace metadata identifies the controlled origin.

A steel-string continuation initially skipped the fresh lookup and introduced unrelated recommendations. A subsequent trial safely declined but still did not satisfy the continuation. The final implementation resolves only the names in the previous controlled catalog list, re-queries the source under the previous budget/payment method, and filters actual string specifications directly. This narrow branch makes **no model call** and records `invoked_by: application_reference_lookup`; it is not counted as independent model tool-use success.

An actual unavailable-endpoint test also exposed an SDK transport exception escaping the earlier handler. Mapping SDK transport/response exceptions at the client boundary restored a safe recoverable reply. The test did not stop the running Ollama server.

### Actual pricing regression

Recorded at **2026-11-02 19:33:07 -03:00**: all **11 structural checks passed**. The actual model requested fresh pricing results on all three turns and received those results back. Python displayed R$ 359.00 original, 10% promotion and R$ 323.10 final; PIX retained R$ 323.10 without an additional discount; R$ 323.10 explicitly fit the R$ 340 budget. Turns took **31.45, 23.75 and 47.63 seconds**. See [pricing after quality](evidence/pricing_after_quality.json).

### Accepted quality scenarios

Command: `.\.venv\Scripts\python.exe scripts/check_quality.py --output tmp/quality-accepted.json`.

Recorded at **2026-11-02 19:49:26 -03:00** (22:49:26 UTC in the artifact): all **nine scenario checks passed**, followed by review against the actual records.

| Scenario | Observed behavior | Elapsed |
| --- | --- | --- |
| Available acoustic guitars up to R$ 1,000 | Actual model requested catalog search and received its results; source renderer displayed Tagima R$ 429.90/nylon, Rozini R$ 459.90/nylon and Shelby R$ 549.00/steel, with stock and no beginner assumption/ranking. | 68.60 s |
| Which of those have steel strings? | Direct application re-query retained only the previously displayed Shelby and the R$ 1,000 budget; no model request. | <0.01 s |
| Shelby SN-7C 7 Cordas Nylon Natural | Actual model/tool cycle distinguished an existing but unavailable product from an unknown name. | 23.99 s |
| Zubumafu X-999 | Actual model/tool cycle found no matching catalog name; no product/price invented. | 30.43 s |
| Weather question | Brief application redirect to store/music scope, without model or commercial lookup. | <0.01 s |
| Unavailable model endpoint | Actual SDK request failed; recoverable reply without endpoint/traceback. | 1.21 s |

See [quality acceptance evidence](evidence/quality_ui_acceptance.json). Direct controller lookups and model-requested tools are identified separately. No model reasoning is published. The model still emitted reasoning despite `think=False`; isolated timings do not prove a general improvement. Narrow phrase/reference matching and controlled commercial replies do not establish universal dialogue grounding.

### Policy regression after quality changes

At **2026-11-02 19:50:48 -03:00**, the two-turn return-policy scenario passed all **11 checks** again. Both actual model/tool cycles retrieved chapter 4/page 4. The source-verified questions asked purchase channel and then actual receipt date, with no return approval or invented procedure. Turns took **35.66 and 35.32 seconds**. See [policy regression evidence](evidence/policies_after_quality.json).

### Order regression after quality changes

At **2026-11-02 19:52:49 -03:00**, the order dialogue and denial cases passed all **16 checks**. Missing credentials produced the order-number then email questions without disclosing details or claiming a lookup. After the customer's registered email, the actual model requested `get_order_status`, received its result, and Python displayed the verified order 11: confirmed, one Kalani and historical R$ 359.00 total, with no tracking/estimated delivery invented. Wrong email and nonexistent order produced identical generic denials. The three dialogue turns took **8.21, 6.35 and 10.96 seconds**; denial cases took **18.58 and 49.76 seconds**. Public evidence redacts emails. See [order regression evidence](evidence/orders_after_quality.json).

### Visual review and final packaging

No browser was connected. After an unsuccessful Edge connection attempt, the user explicitly deferred browser setup. AppTest is functional verification only: CSS, real-browser responsiveness and mobile appearance remain **unreviewed**. No visual approval is claimed.

The selected implementation is ready for final packaging, subject to the documented limits. Remaining submission work: clean-install verification, final English README/decisions/example selection and the delivery PDF/channel/deadline check. SQLite history is local and unencrypted; original messages may include the customer-entered email. Order verification remains demonstrative. Freight/installment calculations and production authentication remain excluded. No application submission or repository freeze has occurred.

## Screenshot feedback - consistent theme and no emojis

The user supplied an Edge screenshot showing light custom surfaces mixed with dark Streamlit controls/foregrounds, and requested no emojis. Added a repository light theme, explicit matching header/input/background colors, a smaller header and a readable content width. Sidebar labels were simplified and prototype/privacy details moved into an expandable section. Decorative emoji labels/avatars were replaced with text and monochrome Material icons.

The persona now prohibits emojis. Free-form answer cleanup removes emoji sequences, including flags/joiners/keycaps, instead of allowing one. The interface also filters historical message/title display without rewriting the original stored history. The 119-test suite passed again, including complete emoji removal and scenario-answer persistence assertions. Streamlit loaded the light theme configuration and the restarted localhost server returned HTTP 200 with a healthy endpoint. No new model/tool acceptance or browser-render approval is claimed for this presentation change; the previous actual source checks remain the applicable functional evidence.

## Recorded-conversation review in the interface

Added four read-only recorded dialogues under **Minhas conversas**, using the latest accepted catalog, pricing, policy and order reports. They are recordings of previous executions, not generated fixtures or new model runs. Only the first two catalog turns and first three order turns belong to those displayed dialogues; separate unavailable/unknown/out-of-scope and denial checks are excluded. The original evidence and historical bilingual examples are unchanged.

The complete suite passed **124 tests**. New coverage verifies that displayed turns match the accepted source records, exports retain original answers, order email remains redacted, independent checks stay separate, and no evidence is rewritten. AppTest opens all four recordings without calling the backend, confirms no input/delete controls or SQLite imports, and checks that switching to personal/new chats restores normal interaction without mixing histories. A missing evidence file shows an error without generating a replacement. No new real-model execution was required or claimed: the feature only reads existing evidence. Visual confirmation of the updated sidebar remains separate from AppTest.

## Sidebar reopening, greeting latency and incremental output

The installed Streamlit frontend places `stExpandSidebarButton` inside `stToolbar`. The custom CSS hid the entire toolbar, including the reopen control. Removed that rule, styled the native reopen button and increased top padding so content does not cover the header. This is based on the installed frontend code; no connected-browser interaction/visual approval is claimed.

Standalone greetings now use a narrow full-message Python template with no model request. Compound greeting/product questions still use the guarded lookup path. The UI shows actual workflow stages and elapsed time from streamed SDK activity. For recognized general musical explanations, final text streams after the complete reasoning delimiter. Commercial/order/return-clarification previews are Python-rendered only after a qualifying source result. The result still reaches the model, with no advertised tools and a 64-token acknowledgement cap instead of a long discarded draft. No artificial typing delay is added. Only the completed exchange is saved to SQLite.

### Offline verification

The full suite passed **132 tests**, including the preceding 124. Added checks cover greeting bypass versus compound requests, actual SDK chunk aggregation/statistics, fragmented private delimiters, transport failure during streaming, early verified output before the result round-trip, failure paths without invented previews and persistence of only the final exchange. Existing reasoning/truncation and unsolicited-order tests now use non-greeting inputs so they still exercise the model path. No dependencies changed.

### Measured responsiveness

A preliminary direct SDK greeting took **11.072 seconds** and emitted reasoning markup. A final-assistant-prefix experiment and a temporary empty-think-template experiment did not reliably remove that behavior. Neither was adopted, and the temporary alias was removed; the original model/template remain unchanged.

The accepted responsiveness run was recorded at **2026-11-02 20:41:54 -03:00**. All eight checks passed; see [responsiveness evidence](evidence/responsiveness_acceptance.json).

| Scenario | First visible answer/preview | Total backend time | Interpretation |
| --- | --- | --- | --- |
| Standalone greeting | Immediate final template | 0.0001 s | No inference or commercial lookup; not a browser round-trip measurement. |
| Short musical explanation | 25.5892 s | 27.2135 s | 79 incremental output events after private reasoning; the long initial delay remains a limitation. |
| Catalog query | 16.9206 s | 19.1601 s | Verified source-rendered preview before the short final model acknowledgement. |

The catalog regression subsequently took **90.29 seconds**, including a truncated source-free initial request and bounded repair, despite passing all 11 source/quality checks. This variability means the 19-second run is **not** a general latency guarantee. An additional compact-router prompt experiment failed to request a source and returned the safe fallback after two truncated generations; it was rejected and the previously verified full prompt retained. Experimental timings are not silently treated as production improvements.

### Actual source regressions with the accepted configuration

All four acceptance scripts used the real streaming SDK adapter (via its progress callback), with actual tool results returned to the model. They passed the existing structural checks; review of displayed fields confirmed the source facts. The reports below were captured before the rejected compact-prompt experiment and correspond to the retained full-prompt configuration.

| Scenario | Checks | Observed elapsed time | Evidence |
| --- | --- | --- | --- |
| Catalog | 11/11 | 90.29 s | [catalog](evidence/catalog_after_responsiveness.json) |
| Price / PIX / R$ 340 budget | 11/11 | 14.42 / 13.36 / 39.29 s | [pricing](evidence/pricing_after_responsiveness.json) |
| Return channel / receipt date | 11/11 | 13.51 / 26.41 s | [policies](evidence/policies_after_responsiveness.json) |
| Order number / email / verified order | 16/16 including two denials | 3.68 / 14.43 / 6.12 s; denials 13.31 / 13.81 s | [orders](evidence/orders_after_responsiveness.json) |

Historical order R$ 359.00, absent tracking/estimate, generic denials, non-cumulative PIX and section 4/page 4 references were preserved. Public evidence contains no raw reasoning or full emails. This increment fixes the greeting delay and makes ongoing work/output visible; it does **not** resolve all Qwen inference latency or establish universal grounding. Broader latency improvements require separate measured work. Earlier recorded sidebar examples remain immutable historical conversations.

## Dark mode, app navigation and input variants

The user reported the native sidebar still could not be reopened. Replaced that dependency with an application-owned navigation column and an always-rendered **Abrir conversas / Ocultar conversas** button. Light/dark/system selection remains available at the top while navigation is hidden. Palettes style foregrounds/backgrounds consistently; `?theme=dark` restores dark mode on reload and system mode follows the browser's preference.

The full suite passed **138 tests**. AppTest toggled navigation closed/open in both light and dark modes without losing the selected conversation/messages, exercised controls on the read-only order recording, and verified restoration/persistence of theme through the URL. It also reran the existing scenario, deletion, evidence, streaming and history checks. These are functional checks, not connected-browser visual approval.

New input tests confirm immediate handling of `ui`, `oiii`, `td bm` and other bounded greeting variants without inference; common instrument/policy abbreviations still require the correct tool; compound typo greetings cannot authorize invented prices; and a customer's `pixx@example.invalid` email reaches order verification unchanged despite the intent alias for `pixx`. No new live-model claim or latency improvement is attributed to these UI/intent changes. The original sources, recorded examples and inference configuration were preserved.

## Requested punctuation style

Removed the long dash U+2014 from newly rendered catalog text and editorial Markdown. The persona prohibits it; shared display formatting also normalizes it in final replies, incremental events, saved-history display, provenance metadata and Markdown downloads. Original machine evidence and supplied CSV/PDF sources remain unchanged, while exports disclose presentation normalization. The catalog follow-up parser still recognizes historical separators, so older personal conversations retain working source lookups.

The full **138 tests passed**, including long-dash removal during response cleanup, normalized exports with unchanged source evidence, and steel-string follow-ups from both new and historical catalog formatting. This is a presentation change; no new inference result or source/price claim is asserted.

## Policy citation placement

Policy citation footers now appear inside the collapsed source/tool details instead of the visible answer body. The same display rule applies to incremental output, saved conversations and recorded evaluation examples. Original stored answers, evidence files and structured tool references remain intact. Citation-only legacy records still expose their source details even without a tool trace.

All **138 tests passed**. AppTest verifies that the customer-facing answer excludes the footer, the expander contains its exact section/page citation, structured references remain accessible and the original persisted answer is preserved. This change does not claim new live-model validation.

## Recommendations mentioning price

Recommendation requests such as `me recomenda uma guitarra com um bom preço` now select catalog search before single-model pricing. Previously, the price keyword restricted the model to an exact-product lookup and could produce an irrelevant model-not-found reply. The persona also distinguishes subjective price preferences from product names and numeric budget limits.

All **139 tests passed**, including catalog tool selection, real CSV matches and no invented budget for guitar/violão recommendation variants with an unrelated product in the prior history. Existing specific-model price and PIX follow-up tests remain passing.

The exact reported question also passed a real Qwen3 4B run: catalog search returned five available guitars, displayed the three lowest final prices and did not fabricate a budget. The run took **83.56 seconds**; this routing fix does not resolve inference latency. The full answer, tool references and three passing checks are recorded in [the recommendation report](evidence/recommendation_after_routing.json).

## Currency rendering and avatar contrast

Streamlit interprets paired dollar signs as math delimiters, corrupting replies with multiple BRL amounts. The shared chat display formatter now escapes dollar signs and preserves line breaks in price quotes and order summaries. It covers user messages, streamed/final answers, saved chats and recorded examples without rewriting original histories, evidence, monetary values or Markdown downloads.

Custom material avatars now explicitly use the selected palette's text color, overriding the native light-theme icon color that remained dark against dark-mode backgrounds. Avatar surfaces and borders use the same palette. The installed frontend confirms these icons receive an explicit native color, requiring the scoped override.

All **140 tests passed**. AppTest checks that original/final BRL prices and discount emphasis reach the renderer with literal currency markup in both themes, that quote lines remain separate and that persisted amounts stay unchanged. Existing recorded-conversation and partial-response tests also pass. These are functional checks; final visual appearance remains subject to browser review. No new model run was needed for these presentation fixes.

## Technical notes inside source details

Catalog result-count/snapshot footers and pricing source-validity footers now appear only inside the source/tool expander, alongside policy references. Recorded response timing also moves into that expander. This presentation rule covers new output, saved chats and evaluation recordings while retaining the original evidence and history. Product availability, prices and budget comparisons remain visible customer information.

All **140 tests passed**. The recorded-conversation AppTest verifies every technical footer and elapsed time is available inside its corresponding details panel, while the answer Markdown excludes the technical footer. This is a presentation-only change, with no new model run.

## Native input surfaces in dark mode

The chat composer has an independently painted inner wrapper, and the installed Streamlit 1.66 selectbox uses React Aria components rather than the older Base Web selectors. Their native light surfaces caused the reported white input frame and dropdown arrow area. Scoped palette rules now cover the chat wrapper, selectbox group/input/buttons, dropdown surface, hover and focus borders. The textarea uses a transparent background within its themed wrapper.

All **140 tests passed**, including existing theme switching/navigation checks. The installed frontend structure was inspected to identify the native wrappers. Browser screenshots are still needed to confirm the final visual result; these checks do not assert visual approval.

## Bottom-anchored message composer

The message input now lives at the Streamlit main root, enabling its native bottom-anchored mode. Previously it was inside the conversation column, where Streamlit renders it inline; newly submitted messages and generation status therefore appeared below the input. Chat rendering remains in the conversation area, while the composer stays in the native bottom region. Read-only recordings still omit the composer.

All **140 tests passed**. AppTest now verifies the input's native `is_auto_positioned_at_bottom` flag before/after a streamed exchange and when switching themes, alongside existing navigation, history and scenario checks. No live inference was needed for this layout fix.

## Direct catalog lookup for simple affordable recommendations

The earlier routing/prompt change still depended on model tool selection. Complete category-only requests with an affordability phrase now call the real catalog directly in Python, including the reported `recomneda` spelling and the bounded `guitara` alias. The trace explicitly records `application_catalog_lookup`; it does not claim a model tool call. This path sorts available products by final price without inventing a budget. Full matching excludes requests with brands, specifications, numeric budgets, shipping or PIX constraints so those remain in the existing tool flow.

All **144 tests passed**. New tests verify real guitar results, no model invocation, preservation of constraints, catalog-error handling, and a Streamlit exchange repeated after an earlier model-not-found reply. Original failed history is retained; a new submission produces the corrected result. [Direct catalog evidence](evidence/recommendation_direct_catalog.json) records both spellings, actual CSV results and execution times without inference. This does not resolve latency for other model-dependent requests.

## Composer width within the conversation layout

The native bottom composer now shares the main area's maximum width and horizontal padding. With navigation open on desktop, it uses the conversation column's width and right alignment, matching the 1:3 layout and large column gap. With navigation hidden it fills the available conversation width; narrow screens retain full-width input with reduced margins. Native bottom anchoring remains enabled.

All **144 tests passed**, including bottom-position metadata, navigation/theme changes and real-catalog UI submission. This CSS adjustment requires user browser review for final visual alignment.

## Messenger-style message alignment

Customer messages now use right-aligned, content-sized green bubbles, with the customer avatar on the right. Zubumafu messages use left-aligned content-sized bubbles. Both have responsive maximum widths, wrapping and compact spacing, including existing evaluation recordings and streamed replies. The selectors use the installed frontend's accessible message labels rather than generated class names.

Main and footer containers now enforce the same padding and maximum width against native responsive overrides; the desktop composer width override is explicit as well. The native footer's intermediate surface also follows the chosen theme. These changes address the reported remaining width mismatch while keeping bottom anchoring.

All **144 tests passed**. This validates existing functional flows, not rendered pixel alignment; final appearance needs browser review.

## Compact conversation navigation and composer alignment correction

The navigation now uses compact left-aligned rows, a distinct new-conversation action, quieter active states, smaller section labels and a grouped brand header. Recorded examples, personal histories and test scenarios retain their separate functions and existing identifiers. The panel has a bounded scroll area that reserves space for the bottom composer. Theme selection moves into a compact Appearance popover beside the always-available navigation toggle, removing the large standalone selector from the header.

The column gap is now medium (2rem). Inspection of the installed frontend revealed that native columns subtract the full gap from each flex basis and then share the remaining gap equally. The matching composer width is therefore `calc(75% - 1rem)`, correcting the previous proportional-gap approximation. Main/footer padding overrides and messenger bubble alignment are retained.

All **144 tests passed**, including theme changes via the popover, reopening navigation, recorded examples, actual-catalog submission and preservation of bottom anchoring. Visual browser approval is still separate from these functional checks.
