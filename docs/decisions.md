# Zubumafu - Architecture Decision Record

Status: catalog and policy retrieval integrated. The remaining challenge capabilities and broad behavioral validation are pending. See [validation](validation.md) for the observed results.

## Scope and sources

The prototype assists customers of Empório da Música using the supplied CSV datasets and the store's policy PDF. Commercial facts must come exclusively from those materials. General musical knowledge may be used to explain instruments, but unverified claims about specific artists or equipment must be avoided.

## Technology choices

- Primary language: Python.
- Interface: Streamlit text chat with session reset and expandable tool evidence.
- Local LLM runtime: Ollama 0.40.13 (verified on the developer's Windows laptop).
- Initial model candidate: `qwen3:4b`, downloaded and verified to load on the laptop with 100% GPU reported by `ollama ps`. Quality and latency are not yet measured.
- Fallback/experiment: compare `qwen3:8b` only if resource usage is acceptable.
- Retrieval: deterministic Python functions for CSV data and section-based retrieval from the original store-policy PDF with pypdf 6.21.4.
- Conversational context: in-memory session history, no durable persistence in the initial version.
- Tests: standard-library `unittest`, rather than the initially proposed pytest. The offline suite now uses pypdf to exercise the actual policy document; it does not need a running model or API access.
- Dependency versions: top-level packages plus resolved constraints are pinned to the locally installed environment (Windows, Python 3.12.10).

## Model/tool boundary

The LLM identifies the customer intent, requests available tools, and writes a natural response. Python owns filters, money calculations, promotion eligibility, order lookups, and source provenance. The first acceptance demonstration must show a complete cycle of model tool request, Python execution, tool result returned to the model, and a grounded answer.

For Qwen3, request `think=False` through the Ollama client. The local base model nevertheless emitted reasoning in `message.content`, and `/api/show` reported `thinking.values: [true]`. Consequently, simply displaying `message.content` was insufficient. The implementation adds `/no_think` steering and discards labeled reasoning, including a closing tag whose opening tag was prefilled by the template. An unfinished reasoning block is never displayed. This separates customer output from model reasoning but does not establish that generation was disabled.

The model remains the original `qwen3:4b`; there is no fine-tuned model, custom model required by the project or extra weights to distribute. Per-request generation is capped at 2,048 tokens, with a 120-second default HTTP timeout, and incomplete final generations return a fallback. The measured latency and remaining uncertainty are documented rather than described as production readiness.

Successful lookup status is required before answering recognized catalog questions. Unknown or failed tools do not satisfy that requirement. These guards remain heuristic; they do not prove every sentence in a generated answer is grounded. Filters, source and match counts are retained in the visible trace. Tool results include six records at most to limit context consumption; the user receives up to three suggestions under the persona instructions.

## Policy retrieval increment

The supplied eight-page manual has ten named main chapters. Verified heading boundaries allow deterministic extraction, including chapter continuations on another page. A small Portuguese keyword/topic map selects the relevant chapters without embeddings or another service. The original PDF is not rewritten. Headings and the source version are specific to this manual; changing the document requires revalidating the extractor.

Tool results include original excerpts, chapter IDs, actual 1-based PDF pages, ambiguity warnings and information needed for return guidance. For defects, both returns and warranty sections are retrieved. Topic matching is not a general semantic search; mixed topics can need separate lookups.

The three known policy ambiguities are surfaced rather than arbitrarily settled: conflicting telephone/WhatsApp numbers, general versus detailed installment minimums, and the undefined local-freight amount of exactly R$ 500. Calculation and product-specific promotion tools remain outside this increment.

Policy questions must be supported by `search_store_policies`, not merely a successful catalog lookup. Short return follow-ups such as "Foi online" retain the purchase context and require a fresh policy lookup. Python appends chapter/page references only for successful policy results; references preserve the chapter-to-page mapping. The initial model instructions ask for purchase channel and actual receipt date before suggesting eligibility and prohibit approving or registering a return.

The first actual two-turn policy trial retrieved the right source but did not ask the receipt date on the second turn and invented an online-store procedure. Prompt instructions alone were insufficient. For explicit regret conversations with missing channel/date information, Python therefore replaces the model draft with a bounded clarification template after the successful source lookup and model/tool round-trip. This is recorded as `reply_origin: source_verified_clarification_template` in the trace. Only customer messages supply those facts; these templates ask for information without approving a return. The matching remains intentionally narrow and does not parse arbitrary dates or decide eligibility.

## Persona

Zubumafu is friendly, patient, musically knowledgeable, professional, and warm without being effusive. It adapts explanations to the customer's expertise. In complaints it acknowledges frustration, stays calm, avoids forced humor, and gives a concrete next step. It does not claim actions or verification that did not occur.

## Explicitly pending

- Broader real-model grounding and latency evaluation beyond the first catalog scenario.
- Pricing, discount non-cumulativity and human-confirmed interpretations of ambiguous policy rules.
- Secure order-lookup demonstration. Matching an email alone is not production authentication.
- Behavior on missing records, tool errors and out-of-scope questions.
- Final README, 3-5 observed conversations covering distinct scenarios, and final submission. The public repository already exists.

## Sources

- `desafio_tecnico_ai_eng_artefact.pdf` (official challenge)
- `data/políticas_da_loja.pdf` (store policies, v2.1)
- Supplied `data/*.csv` datasets
- `GUIA_DO_PROJETO.md` (internal planning guide, not an official requirement)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling).
- [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking).
- [Qwen3 thinking / non-thinking instructions](https://qwen.readthedocs.io/en/stable/inference/transformers.html).
- [pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
