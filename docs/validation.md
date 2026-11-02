# Initial milestone validation

Observed on **2 November 2026**, using São Paulo time (UTC-03:00). This validates an initial catalog increment, not the complete challenge.

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

## Remaining work

Policy retrieval, promotions and pricing rules, an explicit decision about order lookup, broader scope/error evaluation and 3–5 distinct observed conversations remain pending. Context pressure, latency, reasoning controls and unsupported factual claims require further evaluation. No general reliability score or production readiness is claimed.
