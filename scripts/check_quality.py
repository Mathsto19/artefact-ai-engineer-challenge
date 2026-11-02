"""Observe catalog follow-ups and missing/unavailable/off-topic quality scenarios."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_orders import redact
from zubumafu.agent import respond, MODEL
from zubumafu.catalog import _normalize
from zubumafu.model import create_chat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    real_chat = create_chat()
    turns = []

    def run(question, history, scenario):
        calls, results = [], []

        def recorded(**kwargs):
            for message in kwargs['messages']:
                if isinstance(message, dict) and message.get('role') == 'tool':
                    result = json.loads(message['content'])
                    if result not in results:
                        results.append(result)
            start = time.perf_counter()
            response = real_chat(**kwargs)
            msg = response.message
            calls.append({'tool_calls': [{'name': call.function.name, 'arguments': redact(call.function.arguments)} for call in (msg.tool_calls or [])],
                          'reasoning_output_observed': bool(getattr(msg, 'thinking', None) or '</think' in (msg.content or '').casefold() or '<think' in (msg.content or '').casefold()),
                          'think_requested': kwargs['think'], 'generated_tokens': response.eval_count,
                          'elapsed_seconds': round(time.perf_counter()-start, 2)})
            print(f'{scenario}, request {len(calls)}: {calls[-1]["elapsed_seconds"]} s', flush=True)
            return response

        start = time.perf_counter()
        answer, trace = respond(question, history, chat_fn=recorded)
        turns.append({'scenario': scenario, 'question': question, 'answer': answer, 'trace': trace,
                      'tool_results': results, 'model_requests': calls, 'elapsed_seconds': round(time.perf_counter()-start, 2)})
        history.extend([{'role': 'user', 'content': question}, {'role': 'assistant', 'content': answer}])
        print(answer, flush=True)

    history = []
    run('Quais violões disponíveis custam até R$ 1.000?', history, 'catalog')
    run('Quais dessas opções têm cordas de aço?', history, 'steel_followup')
    run('Vocês têm o Shelby SN-7C 7 Cordas Nylon Natural?', [], 'unavailable')
    run('Vocês vendem a guitarra Zubumafu X-999?', [], 'unknown')
    run('Qual é a previsão do tempo para amanhã?', [], 'outside_scope')
    with patch.dict('os.environ', {'OLLAMA_HOST': 'http://127.0.0.1:1', 'OLLAMA_TIMEOUT_SECONDS': '1'}):
        start = time.perf_counter()
        answer, trace = respond('Quais guitarras estão disponíveis?')
        failed_backend = {'answer': answer, 'trace': trace, 'elapsed_seconds': round(time.perf_counter()-start, 2),
                          'setup': 'Actual SDK request to an unavailable local endpoint; no running Ollama server was stopped.'}
    catalog, steel, unavailable, unknown, outside = turns
    steel_products = [item for result in steel['tool_results'] for item in result.get('products', [])]
    steel_products.extend(product for item in steel['trace'] if item.get('invoked_by') == 'application_reference_lookup' for product in item.get('reference_products', []))
    checks = {
        'neutral_profile_and_ranking': not any(word in _normalize(catalog['answer']) for word in ['iniciante', 'melhores']),
        'catalog_has_individual_nylon_and_steel': 'cordas de nylon' in catalog['answer'] and 'cordas de aço' in catalog['answer'],
        'catalog_origin_is_explicit': any(item.get('reply_origin') == 'python_catalog_result_template' for item in catalog['trace']),
        'steel_followup_retrieves_only_steel_under_previous_budget': bool(steel_products) and all(item['specs'].get('strings') == 'steel' and item['category'] == 'Violões' and Decimal(item['final_price_brl']) <= 1000 and item['name'] in {p['name'] for result in catalog['tool_results'] for p in result.get('products', [])[:3]} for item in steel_products),
        'unavailable_not_invented_as_unknown': any(result.get('no_match_reason') == 'unavailable' for result in unavailable['tool_results']) and 'não está disponível' in unavailable['answer'],
        'unknown_not_invented_as_available': any(result.get('no_match_reason') == 'not_in_catalog' for result in unknown['tool_results']) and 'não localizei' in unknown['answer'].casefold(),
        'off_topic_redirect_without_model_or_commerce': not outside['model_requests'] and not outside['trace'] and 'instrumentos musicais' in outside['answer'],
        'actual_unavailable_backend_recovers_without_details': 'Ollama' in failed_backend['answer'] and not failed_backend['trace'] and '127.0.0.1' not in failed_backend['answer'],
        'no_visible_thinking_markup': all('<think' not in turn['answer'].casefold() and '</think' not in turn['answer'].casefold() for turn in turns),
    }
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'model': MODEL,
              'turns': turns, 'backend_failure': failed_backend, 'checks': checks, 'passed': all(checks.values()),
              'evaluation_limit': 'Limited scenario checks, not universal grounding. Initial catalog output is controlled Python rendering after model/tool round-trip. The steel follow-up is a direct application lookup with no model call, identified in its trace. Off-topic also uses no model. No reasoning text or full emails are stored.'}
    serialized = json.dumps(redact(report), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized+'\n', encoding='utf-8')
    print(serialized)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
