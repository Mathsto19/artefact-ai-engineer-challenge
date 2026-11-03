"""Capture real local UI states for the README using an isolated demo server.

Optional authoring tool, not an application dependency. Install Playwright in a
separate environment. Run against a server whose ZUBUMAFU_HISTORY_PATH points to
a disposable database, never a private history. No model calls are made here:
the live overview uses bounded direct CSV lookup; the other views replay the
shipped, email-redacted recordings of earlier accepted executions.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8502')
    parser.add_argument('--browser-executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('docs/assets/screenshots'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(args.browser_executable), headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1080}, device_scale_factor=1)
        page.set_default_timeout(45000)
        page.goto(args.base_url + '/?theme=dark')
        page.locator('.st-key-new_chat button').wait_for()
        textbox = page.get_by_test_id('stChatInputTextArea')
        for question, expected in [
            ('Oi', 'Oi! Sou o Zubumafu'),
            ('Me recomenda um violão com um bom preço', 'Tagima Memphis AC-39'),
        ]:
            textbox.fill(question)
            textbox.press('Enter')
            page.get_by_test_id('stChatMessage').filter(has_text=expected).wait_for()
        page.get_by_test_id('stChatMessage').filter(has_text='R$ 549,00').wait_for()

        def stable():
            page.evaluate('document.fonts.ready')
            # Restore the top after Streamlit's automatic scroll-to-input.
            for selector in ('.stMain', '[data-testid="stAppScrollToBottomContainer"]', 'html'):
                element = page.locator(selector)
                if element.count():
                    element.first.evaluate('(element) => { element.scrollTop = 0; }')

        def save(name, provenance, locator=None):
            stable()
            path = args.output / name
            if locator is None:
                page.screenshot(path=str(path), full_page=True, animations='disabled')
            else:
                locator.screenshot(path=str(path), animations='disabled')
            shots.append({'file': name, 'provenance': provenance,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

        save('overview-dark.png', 'Fresh UI exchange: greeting and direct CSV recommendation. No LLM inference.')
        page.goto(args.base_url + '/?theme=light')
        page.get_by_test_id('stChatMessage').filter(has_text='Tagima Memphis AC-39').wait_for()
        save('overview-light.png', 'Same disposable local conversation, light theme. No LLM inference.')

        page.set_viewport_size({'width': 1440, 'height': 1800})
        cases = [
            ('catalog', 'catalog.png', 'quality_ui_acceptance.json', 'Shelby'),
            ('pricing', 'pricing.png', 'pricing_after_quality.json', '323,10'),
            ('returns', 'returns.png', 'policies_after_quality.json', 'Quando você recebeu'),
            ('orders', 'orders.png', 'orders_after_quality.json', '359,00'),
        ]
        for key, filename, evidence, expected in cases:
            page.locator(f'.st-key-recorded_{key} button').click()
            page.get_by_test_id('stChatMessage').filter(has_text=expected).last.wait_for()
            page.get_by_text('Tempo registrado:', exact=False).first.wait_for(state='attached')
            for summary in page.locator('[data-testid="stChatMessage"] details[open] > summary').all():
                summary.click()
            content = page.locator('.st-key-conversation_content')
            save(filename, f'Read-only replay of accepted real-run evidence: docs/evidence/{evidence}. No new inference.', content)
            if key == 'returns':
                first = page.get_by_test_id('stChatMessage').filter(has_text='Entendo.').first
                first.get_by_text('Fontes e ferramentas consultadas', exact=True).click()
                first.get_by_test_id('stJson').wait_for()
                save('policy-sources.png', 'Source panel of the first recorded return-policy reply; original PDF section/page metadata.', first)

        browser.close()
    manifest = {'captured_at': datetime.now(timezone(timedelta(hours=-3))).isoformat(),
                'method': 'Unedited PNGs from actual Streamlit rendering in headless local Edge via Playwright.',
                'privacy': 'Disposable SQLite history; recorded order email is already redacted in shipped evidence.',
                'screenshots': shots}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'captured': len(shots), 'files': [shot['file'] for shot in shots]}))


if __name__ == '__main__':
    main()
