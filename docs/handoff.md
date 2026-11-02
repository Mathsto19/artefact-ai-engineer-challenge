# Development handoff

This is an initial catalog milestone, not the finished Artefact submission.

## Repository continuity

The working project lives directly at the repository root. Do not create another outer `zubumafu` project or replace this repository's `.git` directory with one from a ZIP.

Public repository: https://github.com/Mathsto19/artefact-ai-engineer-challenge

The existing first commit (`3c89eec`) and the prototype commits (`fe3745b`, `9929359`) are preserved through a merge. The original data files were identical in both working copies. The merge resolved their line-ending differences while preserving the source working files. Refinements and observed verification are subsequent work, not retroactively manufactured intermediate commits.

## Implemented

- Streamlit chat, session history, conversation reset and tool evidence.
- Local Ollama client with configurable host/model/timeout.
- Bounded tool calling with `think=False` requested and final-content safeguards.
- Read-only `search_products` over the original product/category CSVs.
- Category normalization, availability and budget filters, literal specification search, deterministic BRL display and typed input checks.
- Offline regression tests and a separate real-model catalog acceptance script.

See [validation.md](validation.md) for the actual evidence and its limits. A simulated-model test is not a real-model test. Reasoning hidden from a customer is not proof that reasoning generation was disabled.

## Next increment

1. Implement policy retrieval by sections with provenance to the supplied PDF.
2. Document interpretations of conflicting contacts, installment rules and the exact R$ 500 shipping boundary before turning them into automatic decisions.
3. Add relevant behavior checks and a real interaction using the policy source.
4. Implement promotion and pricing rules, including non-cumulative discounts and the activity flag's limitations.
5. Decide whether limited order consultation belongs in the final scope; define its demo verification and privacy limits before exposing customer data.
6. Complete out-of-scope/error handling and the chosen acceptance matrix.
7. Record 3–5 distinct observed conversations with English documentation; review clean setup and final submission materials.

The known reasoning/latency limitation should also be reevaluated with measured evidence. Do not expand the project with multi-agent orchestration or additional infrastructure unless a concrete requirement warrants it.

## Continue between platforms

Use this same GitHub repository. Pull before starting work in a separate clone, commit each completed and verified increment, and push before switching platforms. Do not overwrite an existing `.git` directory or rewrite the shared history.

Before returning the project for review, provide the current branch/commit, changes, commands executed, observed outputs and unresolved issues. Keep the English README and AI assistance disclosure current. Do not commit local virtual environments, ZIP handoff packages, credentials, raw reasoning logs or the internal Portuguese planning guide.

After final submission, freeze the repository as required by the challenge. No submission has been performed as part of this integration work.
