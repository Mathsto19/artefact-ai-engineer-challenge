"""Observe greeting latency, real streamed text and early verified source output."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zubumafu.agent import MODEL, respond


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    turns = []
    for scenario, question in [('greeting', 'Oi'),
                               ('musical_explanation', 'Como posso praticar ritmo? Responda em até três frases.'),
                               ('catalog', 'Quais violões disponíveis custam até R$ 1.000?')]:
        started = time.perf_counter()
        stages, previews = [], []
        progress_count = 0
        unsafe_markup = False

        def event(item):
            nonlocal progress_count, unsafe_markup
            elapsed = time.perf_counter() - started
            if item['type'] == 'stage':
                stages.append({'label': item['label'], 'elapsed_seconds': round(elapsed, 4)})
            elif item['type'] == 'progress':
                progress_count += 1
            elif item['type'] == 'answer':
                unsafe_markup |= '<think' in item['text'].lower() or '</think' in item['text'].lower()
                if not item['complete']:
                    previews.append({'elapsed_seconds': elapsed, 'text': item['text']})

        if scenario == 'greeting':
            def forbidden(**kwargs):
                raise AssertionError('Greeting must not call the model')
            answer, trace = respond(question, chat_fn=forbidden, on_event=event)
        else:
            answer, trace = respond(question, on_event=event)
        turns.append({'scenario': scenario, 'question': question, 'answer': answer, 'trace': trace,
                      'elapsed_seconds': round(time.perf_counter()-started, 4),
                      'first_preview_seconds': round(previews[0]['elapsed_seconds'], 4) if previews else None,
                      'preview_updates': len(previews), 'model_progress_events': progress_count,
                      'first_preview_matches_final': bool(previews) and previews[0]['text'] == answer,
                      'unsafe_markup': unsafe_markup, 'stages': stages})
        print(f"{scenario}: {turns[-1]['elapsed_seconds']} s; preview: {turns[-1]['first_preview_seconds']}", flush=True)
    greeting, music, catalog = turns
    checks = {
        'greeting_bypasses_model_and_commerce': not greeting['model_progress_events'] and not greeting['trace'],
        'greeting_backend_under_one_second': greeting['elapsed_seconds'] < 1,
        'general_musical_answer_streamed_before_completion': music['preview_updates'] > 1 and music['first_preview_seconds'] < music['elapsed_seconds'],
        'actual_stream_received': music['model_progress_events'] > 0 and catalog['model_progress_events'] > 0,
        'verified_catalog_visible_before_completion': catalog['first_preview_matches_final'] and catalog['first_preview_seconds'] < catalog['elapsed_seconds'],
        'catalog_source_and_template_preserved': any(item['tool'] == 'search_products' and item['status'] == 'ok' and item.get('reply_origin') == 'python_catalog_result_template' for item in catalog['trace']),
        'catalog_still_uses_correct_strings': 'cordas de nylon' in catalog['answer'] and 'cordas de aço' in catalog['answer'],
        'no_visible_reasoning_markup': not any(turn['unsafe_markup'] for turn in turns),
    }
    report = {'recorded_at': datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec='seconds'),
              'model': MODEL, 'turns': turns, 'checks': checks, 'passed': all(checks.values()),
              'evaluation_limit': 'Isolated backend timings, not browser end-to-end or general benchmarks. Greeting uses a Python template with no model call. General musical final text streams only after the reasoning delimiter. Commercial preview is rendered from verified source fields, not streamed model drafts. No reasoning text or partial model drafts are saved.'}
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized+'\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'checks': checks}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
