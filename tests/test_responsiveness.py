"""Responsiveness must preserve source guards and keep reasoning private."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ollama import ChatResponse, Message
from httpx import ReadTimeout

from zubumafu.agent import respond
from zubumafu.model import create_chat, _stream_visible_text


class ResponsivenessTests(unittest.TestCase):
    def test_greeting_bypasses_the_backend_but_combined_requests_do_not(self):
        with patch('zubumafu.model.create_chat', side_effect=AssertionError('No inference for greeting')):
            for question in ['Oi', 'Olá!', 'Bom dia', 'Oi, Zubumafu! Tudo bem?', 'Oie!', 'Oi,   tudo bom?']:
                answer, trace = respond(question)
                self.assertIn('Como posso ajudar?', answer)
                self.assertEqual(trace, [])
        with patch('zubumafu.model.create_chat') as factory:
            factory.return_value.side_effect = ConnectionError
            answer, _ = respond('Oi, quanto custa o Kalani?')
            factory.assert_called_once()
            self.assertIn('Ollama', answer)

    def test_verified_catalog_is_visible_before_bounded_result_roundtrip(self):
        events, calls = [], []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(message=SimpleNamespace(content='Private draft', tool_calls=[
                    Message.ToolCall(function=Message.ToolCall.Function(name='search_products',
                        arguments={'category': 'violão', 'max_price_brl': 1000}))]))
            self.assertTrue(any(event['type'] == 'answer' and not event['complete'] for event in events))
            self.assertEqual(kwargs['tools'], [])
            self.assertEqual(kwargs['options']['num_predict'], 64)
            sources = [json.loads(m['content']) for m in kwargs['messages'] if m.get('role') == 'tool']
            self.assertTrue(sources[0]['products'])
            return SimpleNamespace(message=SimpleNamespace(content='<think>Unfinished private reasoning', tool_calls=[]),
                                   done_reason='length')

        answer, trace = respond('Quais violões até R$ 1.000?', chat_fn=chat, on_event=events.append)
        self.assertIn('Shelby', answer)
        self.assertEqual(events[-1], {'type': 'answer', 'text': answer, 'complete': True})
        self.assertNotIn('Private', str(events))
        self.assertNotIn('reasoning', str(events))
        self.assertEqual(trace[0]['reply_origin'], 'python_catalog_result_template')

    def test_failed_lookup_never_publishes_a_preview(self):
        events = []
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            tool_calls = [Message.ToolCall(function=Message.ToolCall.Function(
                name='search_products', arguments={'max_price_brl': -1}))] if len(calls) == 1 else []
            return SimpleNamespace(message=SimpleNamespace(content='Invented price R$ 1', tool_calls=tool_calls))

        answer, _ = respond('Quais violões?', chat_fn=chat, on_event=events.append)
        self.assertNotIn('R$ 1', answer)
        self.assertEqual([e for e in events if e['type'] == 'answer'],
                         [{'type': 'answer', 'text': answer, 'complete': True}])

    def test_fragmented_reasoning_and_tool_delimiters_stay_private(self):
        for text in ['Private planning', '<think>Private', 'Private</thi',
                     'Private</think><think>More private', 'Private</think><tool_call>{']:
            self.assertEqual(_stream_visible_text(text), '')
        self.assertEqual(_stream_visible_text('Private</think>Resposta <thi'), 'Resposta')
        self.assertEqual(_stream_visible_text('Private</think>Resposta 🎸'), 'Resposta')

    def test_real_sdk_stream_aggregates_tools_and_statistics_without_raw_progress(self):
        chunks = [ChatResponse(message=Message(role='assistant', content='Private planning')),
                  ChatResponse(message=Message(role='assistant', content='</think>')),
                  ChatResponse(message=Message(role='assistant', tool_calls=[Message.ToolCall(
                      function=Message.ToolCall.Function(name='search_products', arguments={'query': 'Kalani'}))])),
                  ChatResponse(message=Message(role='assistant'), done=True, done_reason='stop', eval_count=12)]
        progress = []
        with patch('ollama.Client') as client:
            client.return_value.chat.return_value = iter(chunks)
            answer = create_chat(on_progress=lambda: progress.append('tick'))(model='qwen3:4b', messages=[], stream=False)
            self.assertTrue(client.return_value.chat.call_args.kwargs['stream'])
        self.assertEqual(answer.eval_count, 12)
        self.assertEqual(answer.message.tool_calls[0].function.name, 'search_products')
        self.assertEqual(len(progress), 4)
        self.assertNotIn('Private', str(progress))

    def test_streamed_final_text_waits_for_the_complete_thinking_delimiter(self):
        chunks = [ChatResponse(message=Message(role='assistant', content=part))
                  for part in ['Private', '</thi', 'nk>', 'Olá', ', tudo bem?']]
        chunks.append(ChatResponse(message=Message(role='assistant'), done=True, done_reason='stop'))
        text = []
        with patch('ollama.Client') as client:
            client.return_value.chat.return_value = iter(chunks)
            create_chat(on_text=text.append)(model='qwen3:4b', messages=[])
        self.assertIn('Olá', text)
        self.assertEqual(text[-1], 'Olá, tudo bem?')
        self.assertNotIn('Private', str(text))

    def test_midstream_transport_failure_is_recoverable(self):
        def failed():
            yield ChatResponse(message=Message(role='assistant', content='Private'))
            raise ReadTimeout('private endpoint')
        with patch('ollama.Client') as client:
            client.return_value.chat.return_value = failed()
            answer, _ = respond('Quais violões?', on_event=lambda event: None)
        self.assertIn('Ollama', answer)
        self.assertNotIn('private endpoint', answer)


if __name__ == '__main__':
    unittest.main()
