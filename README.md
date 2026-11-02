# Zubumafu — Music Store AI Assistant

**Status: early functional prototype; not ready for delivery.**

Zubumafu is an experimental text-based customer assistant for **Empório da Música**, the fictional music store in Artefact's AI Engineer challenge. It speaks Brazilian Portuguese with a warm, musical and professional personality. The initial milestone demonstrates an LLM requesting a Python function to search the supplied product CSV, the function returning a result, and the LLM composing a grounded answer.

## Stack and rationale

| Choice | Rationale |
| --- | --- |
| Python | Required primary language; keeps querying and validation deterministic. |
| Streamlit | Small chat UI without a separate frontend application. |
| Ollama + `qwen3:4b` | Runs without an API key or per-request fee on the developer's laptop. This is a candidate, not a quality benchmark. |
| Python tool calling | CSV filtering stays in code while the model handles intent and language. |
| Session-only memory | Enough for a prototype without the overhead of storing conversation histories. |
| Policies by document sections (planned) | The provided manual is small; a vector database is unnecessary for the initial scope. |

Detailed assumptions and pending verification are in [docs/decisions.md](docs/decisions.md).

## Run locally (Windows / PowerShell)

1. Install Ollama and pull the model: `ollama pull qwen3:4b`.
2. Make sure Ollama is running (`ollama list` should work).
3. Create a Python virtual environment and install the dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Start the chat:

   ```powershell
   streamlit run app.py
   ```

5. Ask **"Quais violões disponíveis custam até R$ 1000?"**. The UI should show a `search_products` tool call. If no call is recorded, the example is not a successful tool-calling demonstration.

   To run data-only tests (does not require Ollama):

   ```powershell
   python -m unittest discover -s tests -v
   ```

## Data and tools

The initial tool is `search_products`, which reads `products.csv` and `categories.csv` from `data/` and filters by category, search phrase, price and stock. Price and stock values are from the provided snapshot, not a live commerce integration. Other supplied CSV files and the store policy PDF are included unchanged for later work.

No external source is used for store facts. General musical knowledge may assist in explanations; specific claims about artists or equipment are not verified by this dataset and must not be invented.

## Known limitations

- Only product search is implemented in the first milestone. Promotions, order lookup and policy retrieval remain pending.
- A successful Python unit test does not establish that `qwen3:4b` reliably chooses tools. Real model calls and answer quality must be measured on the developer's Windows computer.
- The interface does not provide production authentication, customer verification or persistence.
- The source documents contain some conflicting store rules/contact details; those have not yet been implemented or resolved.
- Monetary values use the static CSV source. Do not claim live stock or external tracking.
- Tool errors, prompt injection and out-of-scope behavior require further hardening and testing.

## What would be done with more time

Complete pricing and policy tools, limited and explicitly non-production order consultation, automatic validation, multilingual examples, grounding evaluation and a stronger authentication design.

## AI assistance disclosure

ChatGPT (OpenAI) assisted with planning, architecture decisions, drafting Python code, and reviewing documentation. The local inference model is Qwen3 4B via Ollama. Any additional AI assistants used later should be added here before submission. Code and model interactions must be tested, and no example conversation should be fabricated.

## Submission checklist (not yet completed)

- [ ] All required scope functions implemented and validated.
- [ ] 3–5 **real** interaction transcripts covering distinct scenarios.
- [ ] Public GitHub repository with a genuine sequence of commits.
- [ ] Final README and decisions reviewed in English.
- [ ] Repo frozen after submission (no post-deadline changes).

Refer to the provided challenge PDF for official requirements; the project guide is supplementary planning material. The submission channel and exact deadline still need final confirmation.
