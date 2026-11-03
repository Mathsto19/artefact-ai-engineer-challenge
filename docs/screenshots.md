# README screenshot provenance

The seven PNGs in [assets/screenshots](assets/screenshots/) were captured from the running Streamlit application. They are browser captures, not generated UI mockups or retouched compositions. [The manifest](assets/screenshots/manifest.json) records capture time, provenance and SHA-256 hashes.

| File | What it shows | Execution origin |
| --- | --- | --- |
| `overview-dark.png` | Full desktop UI, dark theme | Fresh greeting and direct acoustic-guitar CSV recommendation; no model inference |
| `overview-light.png` | The same conversation, light theme | Same disposable local history |
| `catalog.png` | Budget lookup and steel-string follow-up | Replay of `quality_ui_acceptance.json`, first two turns |
| `pricing.png` | Promotion, PIX and budget | Replay of `pricing_after_quality.json`, first three turns |
| `returns.png` | Purchase channel and receipt-date clarification | Replay of `policies_after_quality.json`, first two turns |
| `orders.png` | Demo number/email flow and historical total | Replay of `orders_after_quality.json`, first three turns, email redacted |
| `policy-sources.png` | Expanded section/page provenance | First reply of the recorded return-policy conversation |

The replay screenshots use the current UI to display unchanged recorded answers with presentation formatting. They are not additional model runs. The underlying reports remain in [evidence](evidence/), and historical bilingual transcripts remain in [examples](../examples/).

## Reproduce the captures

Capture tooling is optional and separate from application dependencies. The original capture used Playwright 1.64.1 and an installed Microsoft Edge executable in headless mode, with a fresh browser context. No browser profile, personal history or logged-in account was used.

Create a separate authoring environment from the repository root:

```powershell
py -3.12 -m venv tmp/screenshots-env
.\tmp\screenshots-env\Scripts\python.exe -m pip install playwright==1.64.1
```

Start a dedicated application server in one PowerShell terminal. Use a **fresh disposable database path**, never the private `.local` history:

```powershell
$env:ZUBUMAFU_HISTORY_PATH = Join-Path (Get-Location) "tmp/readme-capture/new-history.sqlite3"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=8502
```

In another terminal, capture the UI:

```powershell
.\tmp\screenshots-env\Scripts\python.exe scripts/capture_readme.py --base-url http://127.0.0.1:8502 --browser-executable "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
```

The script writes PNGs and a new manifest to `docs/assets/screenshots/`. The browser executable can point to another compatible local Chromium installation. It captures the overview at 1440 x 1080, then uses a taller viewport for full conversation-pane captures. It does not edit the images or change the application DOM to restyle the product.

Stop the dedicated server after capture. Close its PowerShell terminal to discard the history environment variable. For a repeat capture, choose another empty database path. Disposable files under `tmp/` are ignored by Git. The regular application on port 8501 and its private history are separate.

## Checks and limits

- All seven captures were visually inspected for complete replies, valid prices, readable references and email redaction.
- The capture script navigates the actual application, sends the direct-lookup overview messages and opens the recorded dialogues/source panel.
- Captured theme states do not establish mobile usability or exhaustive visual regression coverage.
- There are no credentials, browser chrome, personal desktop contents, model reasoning or unredacted customer emails in these images.
