# Zubumafu — Music Store AI Assistant

**Status: early functional prototype; not ready for delivery.**

Zubumafu is an experimental text-based customer assistant for **Empório da Música**, the fictional music store in Artefact's AI Engineer challenge. It speaks Brazilian Portuguese with a warm, musical and professional personality. The current milestone implements a model requesting a Python catalog search, receiving its results and preparing a customer-facing answer. It does not yet cover the full challenge.

## Stack and rationale

| Choice | Rationale |
| --- | --- |
| Python | Required primary language; keeps querying and validation deterministic. |
| Streamlit | Small chat UI without a separate frontend application. |
| Ollama + `qwen3:4b` | Runs without an API key or per-request fee on the developer's laptop. This is a candidate, not a quality benchmark. |
| Python tool calling | CSV filtering stays in code while the model handles intent and language. |
| Session-only memory | Enough for a prototype without the overhead of storing conversation histories. |
| Policies by document sections (planned) | The provided manual is small; a vector database is unnecessary for the initial scope. |

See [architecture decisions](docs/decisions.md), [verification evidence](docs/validation.md) and the [development handoff](docs/handoff.md).

## Run locally (Windows / PowerShell)

Use Python **3.12** and install Ollama. The environment was checked with Python 3.12.10, Ollama 0.40.13, the Ollama Python SDK 0.6.3 and Streamlit 1.66.1. The resolved Python dependencies are pinned in `requirements-lock.txt` and used as constraints by `requirements.txt`.

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

### Offline tests and real-model check

The `unittest` suite uses the real CSVs and a simulated model. It runs without a local model or third-party Python dependencies:

```powershell
python -m unittest discover -s tests -v
```

Separately, run the first acceptance scenario against the actual Ollama model:

```powershell
.\.venv\Scripts\python.exe scripts/check_catalog.py --output tmp/catalog-smoke.json
```

The command exits with status 0 when its checks pass and 1 when they fail. It records the displayed answer, tool arguments/results, latency and whether reasoning output was observed. It does not record reasoning text. Passing these checks does not prove every generated claim is correct; the answer still needs review against the returned records.

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
| `tests/` | Offline catalog and orchestration regression tests. |
| `scripts/check_catalog.py` | Opt-in acceptance check against the actual local model. |
| `docs/` | Decisions, observed validation and the next development steps. |
| `examples/` | Recorded interactions as they are validated; final coverage is pending. |
| `data/` | Original supplied datasets and store policies. |
| `desafio_tecnico_ai_eng_artefact.pdf` | Original challenge brief. |

## Data and tools

The initial tool is `search_products`, which reads the supplied products and categories CSVs and filters by category, a literal search phrase in names/descriptions/specifications, budget and stock. Prices are parsed with `Decimal`; Brazilian currency display is formatted in Python. The tool returns up to six records, ordered by price, and the full match count. The persona requests at most three suggestions per answer. Search is literal, not semantic, so synonyms and multiword feature combinations can miss matches.

Price and stock values are from the supplied snapshot, not a live commerce integration. The catalog is cached for the Python process; restart the app after changing source files. All seven original files under `data/` were preserved byte for byte when importing the prototype. Other CSVs and the policy PDF remain available for later milestones.

No external source is used for store facts. General musical knowledge may assist in explanations; specific claims about artists or equipment are not verified by this dataset and must not be invented.

## Known limitations

- Only product search is implemented in the first milestone. Promotions, order lookup and policy retrieval remain pending.
- Automated tests with a simulated model and the initial real-model scenario are separate evidence. A single observed conversation does not establish reliability, latency across workloads or full challenge compliance.
- The installed Qwen3 4B template emitted reasoning despite requests with `think=False`. The application also uses `/no_think` as a steering instruction and strips labeled reasoning from visible content. This is an output safeguard, not proof that reasoning generation was disabled. Latency remains a limitation.
- Each reply is bounded to three model requests, five tools per request, 2,048 generated tokens per request and a 4,096-token context. The visible history includes at most 12 previous messages in each request; long conversations can exceed the context budget. Truncated final generations produce a fallback instead of an incomplete answer.
- Catalog-intent checks are heuristic. A successful lookup is required for recognized catalog questions, and failed/rejected tools do not authorize catalog answers. The code does not yet verify every generated factual statement against tool results.
- The first observed answer focused on beginners even though the customer had not specified experience. Persona instructions discourage this assumption, but instructions alone do not guarantee compliance.
- The interface does not provide production authentication, customer verification or persistence.
- The source documents contain some conflicting store rules/contact details; those have not yet been implemented or resolved.
- Monetary values use the static CSV source. Do not claim live stock or external tracking.
- Tool errors, prompt injection and out-of-scope behavior require further hardening and testing.

## What would be done with more time

Complete pricing and policy tools, limited and explicitly non-production order consultation, automatic validation, multilingual examples, grounding evaluation and a stronger authentication design.

## AI assistance disclosure

ChatGPT (OpenAI) assisted with planning, architecture decisions, drafting the initial Python code and tests, and reviewing documentation. Codex assisted with the original material review and repository setup, integrated the supplied prototype history into the existing Git repository, reproduced the tests, corrected catalog/tool/output handling, and ran local model and interface checks. The local inference model is Qwen3 4B via Ollama. Recorded validation distinguishes simulated model tests from real requests; example conversations must not be fabricated.

## Submission checklist (not yet completed)

- [ ] All required scope functions implemented and validated.
- [ ] 3–5 **real** interaction transcripts covering distinct scenarios.
- [x] Public GitHub repository initialized; the initial and imported prototype commits are preserved.
- [ ] Final README and decisions reviewed in English.
- [ ] Repo frozen after submission (no post-deadline changes).

Refer to the provided challenge PDF for official requirements; the project guide is supplementary planning material. The submission channel and exact deadline still need final confirmation.
