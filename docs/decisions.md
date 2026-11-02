# Zubumafu - Architecture Decision Record

Status: catalog, policies, promotion/PIX pricing, demonstrative orders and the persistent conversation interface integrated. Final packaging and visual review are pending. See [validation](validation.md) for observed results.

## Scope and sources

The prototype assists customers of Empório da Música using the supplied CSV datasets and the store's policy PDF. Commercial facts must come exclusively from those materials. General musical knowledge may be used to explain instruments, but unverified claims about specific artists or equipment must be avoided.

## Technology choices

- Primary language: Python.
- Interface: Streamlit text chat with separate persistent threads, scoped deletion and expandable tool evidence.
- Local LLM runtime: Ollama 0.40.13 (verified on the developer's Windows laptop).
- Initial model candidate: `qwen3:4b`, verified to load on the laptop with 100% GPU reported by `ollama ps`. Individual quality/latency observations are recorded in the validation log; no benchmark is claimed.
- Fallback/experiment: compare `qwen3:8b` only if resource usage is acceptable.
- Retrieval: deterministic Python functions for CSV data and section-based retrieval from the original store-policy PDF with pypdf 6.21.4.
- Conversational context: separate local SQLite threads in the current interface; only the last 12 prior messages are sent to the model.
- Tests: standard-library `unittest`, rather than the initially proposed pytest. The offline suite now uses pypdf to exercise the actual policy document; it does not need a running model or API access.
- Dependency versions: top-level packages plus resolved constraints are pinned to the locally installed environment (Windows, Python 3.12.10).

## Model/tool boundary

The LLM identifies customer intent, requests available tools and drafts a response. Python owns implemented filters, money calculations, promotion eligibility, order verification and source provenance. Sensitive order replies use controlled rendering from tool fields. Each tool acceptance demonstration must show a complete cycle of model tool request, Python execution, tool result returned to the model, and a grounded displayed answer.

For Qwen3, request `think=False` through the Ollama client. The local base model nevertheless emitted reasoning in `message.content`, and `/api/show` reported `thinking.values: [true]`. Consequently, simply displaying `message.content` was insufficient. The implementation adds `/no_think` steering and discards labeled reasoning, including a closing tag whose opening tag was prefilled by the template. An unfinished reasoning block is never displayed. This separates customer output from model reasoning but does not establish that generation was disabled.

The model remains the original `qwen3:4b`; there is no fine-tuned model, custom model required by the project or extra weights to distribute. Per-request generation is capped at 2,048 tokens, with a 120-second default HTTP timeout, and incomplete final generations return a fallback. The measured latency and remaining uncertainty are documented rather than described as production readiness.

Successful lookup status is required before answering recognized catalog questions. Unknown or failed tools do not satisfy that requirement. These guards remain heuristic; they do not prove every sentence in a generated answer is grounded. Filters, source and match counts are retained in the visible trace. Tool results include six records at most to limit context consumption; the user receives up to three suggestions under the persona instructions.

## Policy retrieval increment

The supplied eight-page manual has ten named main chapters. Verified heading boundaries allow deterministic extraction, including chapter continuations on another page. A small Portuguese keyword/topic map selects the relevant chapters without embeddings or another service. The original PDF is not rewritten. Headings and the source version are specific to this manual; changing the document requires revalidating the extractor.

Tool results include original excerpts, chapter IDs, actual 1-based PDF pages, ambiguity warnings and information needed for return guidance. For defects, both returns and warranty sections are retrieved. Topic matching is not a general semantic search; mixed topics can need separate lookups.

The three known policy ambiguities are surfaced rather than arbitrarily settled: conflicting telephone/WhatsApp numbers, general versus detailed installment minimums, and the undefined local-freight amount of exactly R$ 500. These ambiguities do not prevent implementing the manual's explicit non-cumulative PIX rule separately.

Policy questions must be supported by `search_store_policies`, not merely a successful catalog lookup. Short return follow-ups such as "Foi online" retain the purchase context and require a fresh policy lookup. Python appends chapter/page references only for successful policy results; references preserve the chapter-to-page mapping. The initial model instructions ask for purchase channel and actual receipt date before suggesting eligibility and prohibit approving or registering a return.

The first actual two-turn policy trial retrieved the right source but did not ask the receipt date on the second turn and invented an online-store procedure. Prompt instructions alone were insufficient. For explicit regret conversations with missing channel/date information, Python therefore replaces the model draft with a bounded clarification template after the successful source lookup and model/tool round-trip. This is recorded as `reply_origin: source_verified_clarification_template` in the trace. Only customer messages supply those facts; these templates ask for information without approving a return. The matching remains intentionally narrow and does not parse arbitrary dates or decide eligibility.

## Promotion and pricing increment

`pricing.py` reads the supplied promotion CSV and uses `Decimal` for a pure calculation shared by `get_product_pricing` and `search_products`. A single active promotion takes priority. PIX gives 5% only without an active promotion, following manual sections 3 and 6. The final price is rounded once with `ROUND_HALF_UP`; the monetary discount reconciles against the cent-based original price. Python supplies customer-ready BRL strings, avoiding separator conversion or discount arithmetic by the model.

The budget is applied **after** eligible discounts. This makes the R$ 359 Kalani discoverable under R$ 340 because its 10% promotional price is R$ 323.10. The original `price_brl` remains available and is not overwritten. Searches requesting PIX pass that payment method to the same calculator. Unknown/multiple promotional prices are excluded from budget matches. Multiple active promotions produce an explicit ambiguity; no best-offer/stacking rule is invented. Activity uses only `is_active`, since the source supplies no validity dates.

The dedicated tool accepts an exact ID or resolves a product name, preferring an exact name over partial matches. Missing/ambiguous names do not yield a price; malformed IDs cannot be silently truncated to another product. Its trace exposes product ID, calculation and source files. General payment rules still use the PDF. Specific product/PIX follow-ups require a fresh catalog or pricing lookup, retaining recent context through heuristic routing. The model remains responsible for choosing the correct product and explaining the returned price; this is not a universal factuality validator. Freight, installments and historical order totals are outside this increment.

An actual first trial omitted the original price and tried to answer the budget follow-up without a new lookup. The guard blocked that last answer. The pricing milestone initially completed missing original/percentage/final fields while retaining the model draft; the quality increment below supersedes that partial supplement with full source rendering. A first response with no required lookup gets one verification reminder; the total limit remains three model requests. This bounded recovery does not authorize a source-free answer and can add latency. Full claim verification and general product-reference resolution remain future work.

## Demonstrative order increment

The selected scope is read-only historical order consultation. `get_order_status` verifies the order/customer/email association before returning any order fields, then joins instruments and quantities without calculating prices. The total comes directly from `orders.total_brl`, not today's promotions. No historical unit price, actual receipt date or live carrier information is invented. Missing tracking and estimated delivery remain null. Internal notes and full customer records are excluded.

The number/email comparison is explicitly demo-only, not production authentication. Existing and nonexistent numbers produce the same missing-email question; a nonexistent order and a mismatching email produce the same generic denial. The agent additionally binds tool arguments to facts in customer messages, preventing a model guess or assistant-invented email from satisfying verification. A changed order resets the email, and a subject change closes the narrow flow. These phrase/regex rules are conservative, not a general identity or conversation-state engine. IDs such as `1.5` or `1e0` cannot be truncated to a valid order.

The tool response still reaches the model, but the order-specific draft is discarded. Python renders only verified fields or the structured clarification/denial. Trace metadata records `python_order_result_template` without the email. When credentials are incomplete and the model answers without a tool, the application asks the next missing field without checking order existence. No model-requested lookup is claimed for that case. The customer's email remains in local session history and configured model requests; saved acceptance evidence redacts it. No new infrastructure or runtime dependency was added. Production authentication, rate limiting and secure real-customer data hosting are future work.

## Quality and messaging-interface increment

Observed model drafts assumed a beginner profile, added unsupported rankings and described mixed nylon/steel lists incorrectly. Catalog and price replies now use deterministic source renderers after the tool/model round-trip, complementing the existing controlled order and return-clarification paths. The trace identifies their origin. Source product names remain intact, including labels such as "Estudante"; string type comes from each instrument's specifications. This trades free-form recommendation prose for predictable commercial facts. General musical/policy prose is not universally validated.

No-result classification distinguishes literal name absence from category, availability, budget and unconfirmed-price constraints. A model-chosen wrong category cannot establish that a named product is absent from the entire catalog. A real failed pricing trial motivated limiting advertised tools by recognized intent, binding an explicit PIX request to the calculation with trace metadata, and retaining one verification repair even after a truncated source-free draft. A single explicit BRL budget is compared in Python; ambiguous multiple amounts are not guessed. These remain heuristic conversation controls, not general semantic understanding.

The interface separates personal chats and seven validation prompt templates. Templates contain no fabricated answers and start with no messages. SQLite stores each exchange atomically under a unique thread ID, supports scoped deletion and survives process restart. Connections are explicitly closed after transaction completion, which matters for Windows file locks. Only selected, email-redacted provenance metadata is saved in traces; raw tool payloads/reasoning are excluded. Original message content remains unencrypted. Local history is ignored by Git; deleting a conversation is logical deletion, not forensic erasure. This is for one trusted computer, without production accounts or authorization.

`app.py` calls `main()` on every rerun. Import-only UI initialization would disappear on later Streamlit reruns because Python caches imported modules. AppTest exercises interaction state and persistence without a browser. It cannot establish CSS correctness, responsive layout or mobile usability. Browser discovery and the explicitly requested Edge connection were unavailable; the user then deferred that review. No visual approval is claimed.

Repeated actual steel-string follow-up trials skipped the required new lookup. For a narrow "which of these" string-type question, the controller now re-queries only the names displayed in the last controlled catalog reply, carrying the prior budget/payment method, and filters the returned source specifications. Names from history are lookup keys, never evidence for prices or string types. This path makes no model call and records `invoked_by: application_reference_lookup`. It is a bounded reference resolver, not general dialogue understanding or a model tool-call demonstration.

An actual unavailable-endpoint trial exposed SDK `httpx.RequestError` exceptions escaping the earlier built-in connection-error handler. The client boundary now maps SDK transport/response errors to the existing recoverable backend failure. The customer sees no internal endpoint or traceback.

## Persona

Zubumafu is friendly, patient, musically knowledgeable, professional, and warm without being effusive. It adapts explanations to the customer's expertise. In complaints it acknowledges frustration, stays calm, avoids forced humor, and gives a concrete next step. It does not claim actions or verification that did not occur.

## Explicitly pending

- Broader real-model grounding, out-of-scope behavior and latency evaluation.
- Human-confirmed interpretations of ambiguous policy rules before implementing their calculations.
- Production authentication/authorization for any use with real customer records; the implemented order/email match is only demonstrative.
- Broader adversarial and dialogue testing beyond the recorded missing-record/error/out-of-scope scenarios.
- Final clean-install check, English documentation/example selection and submission PDF. Four distinct observed conversations and the public repository already exist; no submission has occurred.

## Sources

- `desafio_tecnico_ai_eng_artefact.pdf` (official challenge)
- `data/políticas_da_loja.pdf` (store policies, v2.1)
- Supplied `data/*.csv` datasets
- `GUIA_DO_PROJETO.md` (internal planning guide, not an official requirement)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling).
- [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking).
- [Qwen3 thinking / non-thinking instructions](https://qwen.readthedocs.io/en/stable/inference/transformers.html).
- [pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
