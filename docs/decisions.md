# Zubumafu - Architecture Decision Record

Status: proposed; implementation and end-to-end validation pending.

## Scope and sources

The prototype assists customers of Empório da Música using the supplied CSV datasets and the store's policy PDF. Commercial facts must come exclusively from those materials. General musical knowledge may be used to explain instruments, but unverified claims about specific artists or equipment must be avoided.

## Technology choices

- Primary language: Python.
- Interface: Streamlit text chat.
- Local LLM runtime: Ollama 0.40.13 (verified on the developer's Windows laptop).
- Initial model candidate: `qwen3:4b`, downloaded and verified to load on the laptop with 100% GPU reported by `ollama ps`. Quality and latency are not yet measured.
- Fallback/experiment: compare `qwen3:8b` only if resource usage is acceptable.
- Retrieval: deterministic Python functions for CSV data, section-based retrieval for store policies.
- Conversational context: in-memory session history, no durable persistence in the initial version.

## Model/tool boundary

The LLM identifies the customer intent, requests available tools, and writes a natural response. Python owns filters, money calculations, promotion eligibility, order lookups, and source provenance. The first acceptance demonstration must show a complete cycle of model tool request, Python execution, tool result returned to the model, and a grounded answer.

For Qwen3, request `think=False` through the Ollama client; display only `message.content`. Suppressing a rendered reasoning trace is not equivalent to disabling reasoning generation.

## Persona

Zubumafu is friendly, patient, musically knowledgeable, professional, and warm without being effusive. It adapts explanations to the customer's expertise. In complaints it acknowledges frustration, stays calm, avoids forced humor, and gives a concrete next step. It does not claim actions or verification that did not occur.

## Explicitly pending

- Local end-to-end tool-calling test, response grounding and latency measurements.
- Pricing, discount non-cumulativity, and ambiguous policy rules.
- Secure order-lookup demonstration. Matching an email alone is not production authentication.
- Behavior on missing records, tool errors and out-of-scope questions.
- Final README, 3-5 observed conversations, and repository publication.

## Sources

- `desafio_tecnico_ai_eng_artefact.pdf` (official challenge)
- `data/políticas_da_loja.pdf` (store policies, v2.1)
- Supplied `data/*.csv` datasets
- `GUIA_DO_PROJETO.md` (internal planning guide, not an official requirement)
- Ollama documentation pages explicitly supplied for tool calling and thinking API usage.
