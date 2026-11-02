# Zubumafu — Music Store AI Assistant

**Status: early functional prototype; not ready for delivery.**

Zubumafu is an experimental text-based customer assistant for **Empório da Música**, the fictional music store in Artefact's AI Engineer challenge. It speaks Brazilian Portuguese with a warm, musical and professional personality. The current milestone offers catalog searches and section-based retrieval from the original store-policy PDF, with tool results returned to the model and verified chapter/page references appended to policy replies. It does not yet cover the full challenge.

## Stack and rationale

| Choice | Rationale |
| --- | --- |
| Python | Required primary language; keeps querying and validation deterministic. |
| Streamlit | Small chat UI without a separate frontend application. |
| Ollama + `qwen3:4b` | Runs without an API key or per-request fee on the developer's laptop. This is a candidate, not a quality benchmark. |
| Python tool calling | CSV filtering stays in code while the model handles intent and language. |
| Session-only memory | Enough for a prototype without the overhead of storing conversation histories. |
| Policies by document sections | `pypdf` extracts the supplied manual's chapters with page references; a vector database is unnecessary for this eight-page source. |

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
| `zubumafu/policies.py` | Original PDF extraction, ten chapter boundaries, topic matching, page provenance and ambiguity warnings. |
| `tests/` | Offline catalog and orchestration regression tests. |
| `scripts/check_catalog.py` | Opt-in acceptance check against the actual local model. |
| `scripts/check_policies.py` | Opt-in two-turn return-policy acceptance check against the actual local model. |
| `docs/` | Decisions, observed validation and the next development steps. |
| `examples/` | Recorded interactions as they are validated; final coverage is pending. |
| `data/` | Original supplied datasets and store policies. |
| `desafio_tecnico_ai_eng_artefact.pdf` | Original challenge brief. |

## Data and tools

The initial tool is `search_products`, which reads the supplied products and categories CSVs and filters by category, a literal search phrase in names/descriptions/specifications, budget and stock. Prices are parsed with `Decimal`; Brazilian currency display is formatted in Python. The tool returns up to six records, ordered by price, and the full match count. The persona requests at most three suggestions per answer. Search is literal, not semantic, so synonyms and multiword feature combinations can miss matches.

Price and stock values are from the supplied snapshot, not a live commerce integration. All seven original files under `data/` were preserved byte for byte when importing both prototype increments. Unused operational CSVs remain available for later milestones.

`search_store_policies` reads the original `data/políticas_da_loja.pdf`, recognizes its ten chapter headings and retains text continued on subsequent pages. It selects relevant chapters using a small topic/keyword map and returns PDF excerpts, 1-based pages, source version and clarification requirements. For defects, it includes the warranty chapter alongside return rules. This is a purpose-built retriever for the supplied manual, not a general semantic PDF search engine; compound questions can require more than one lookup.

The tool flags conflicting contact numbers, inconsistent installment minimums and the undefined local-delivery boundary of exactly R$ 500. These warnings do not silently resolve the source. Policy citations are appended by Python from successful tool results, with each chapter mapped to its actual pages. The catalog and PDF extraction are cached for the Python process; restart the app after changing source files.

For an explicit regret conversation with missing purchase information, Python controls two clarification questions after a successful return-policy lookup and the model/tool round-trip: purchase channel first, then actual receipt date for an online purchase. These displayed questions use short templates rather than an unconstrained model draft. The trace marks `reply_origin: source_verified_clarification_template` and the missing field. This prevents the draft from skipping those questions or inventing a return-submission procedure. It is conservative phrase matching, not a general date parser or an eligibility decision engine.

No external source is used for store facts. General musical knowledge may assist in explanations; specific claims about artists or equipment are not verified by this dataset and must not be invented.

## Known limitations

- Product search and policy retrieval are implemented. Product-specific promotions, price calculations and order lookup remain pending; general promotion/payment rules can already be retrieved from the manual.
- Automated tests with a simulated model and observed catalog/policy scenarios are separate evidence. This limited sample does not establish reliability, latency across workloads or full challenge compliance.
- The installed Qwen3 4B template emitted reasoning despite requests with `think=False`. The application also uses `/no_think` as a steering instruction and strips labeled reasoning from visible content. This is an output safeguard, not proof that reasoning generation was disabled. Latency remains a limitation.
- Each reply is bounded to three model requests, five tools per request, 2,048 generated tokens per request and a 4,096-token context. The visible history includes at most 12 previous messages in each request; long conversations can exceed the context budget. Truncated final generations produce a fallback instead of an incomplete answer.
- Source-intent checks are heuristic. Recognized catalog and policy questions require a successful lookup of the corresponding tool; a catalog lookup cannot authorize a policy answer or vice versa. Return follow-ups about channel/receipt retain their policy context. The code does not yet verify every generated factual statement or citation written by the model against tool results.
- The first observed answer focused on beginners even though the customer had not specified experience. Persona instructions discourage this assumption, but instructions alone do not guarantee compliance.
- The interface does not provide production authentication, customer verification or persistence.
- Conflicting contacts and installment rules, and the missing exact R$ 500 freight case, are explicitly flagged. The prototype does not resolve those policies or approve, reject or register return requests.
- Monetary values use the static CSV source. Do not claim live stock or external tracking.
- Tool errors, prompt injection and out-of-scope behavior require further hardening and testing.

## What would be done with more time

Complete promotion/pricing tools, limited and explicitly non-production order consultation if selected for the final scope, automated grounding checks, multilingual examples, broader dialog evaluation and a stronger authentication design.

## AI assistance disclosure

ChatGPT (OpenAI) assisted with planning, architecture decisions, drafting the initial Python code/tests and the policy-retrieval increment, and reviewing documentation. Codex assisted with the original material review and repository setup, integrated the prototype history and subsequent policy changes into the existing repository, preserved and extended the regression tests, corrected tool/output handling, and ran local model and interface checks. The local inference model is Qwen3 4B via Ollama. Recorded validation distinguishes simulated model tests from real requests; example conversations must not be fabricated.

## Submission checklist (not yet completed)

- [ ] All required scope functions implemented and validated.
- [ ] 3–5 **real** interaction transcripts covering distinct scenarios.
- [x] Public GitHub repository initialized; the initial and imported prototype commits are preserved.
- [ ] Final README and decisions reviewed in English.
- [ ] Repo frozen after submission (no post-deadline changes).

Refer to the provided challenge PDF for official requirements; the project guide is supplementary planning material. The submission channel and exact deadline still need final confirmation.
