"""Spelling tolerance must not bypass lookups or alter order credentials."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from zubumafu.agent import respond, _required_tool
from zubumafu.orders import get_order_status


class InputUnderstandingTests(unittest.TestCase):
    def test_common_greeting_variants_do_not_call_the_model(self):
        with patch('zubumafu.model.create_chat', side_effect=AssertionError('Unexpected inference')):
            for message in ('ui', 'UI!', 'oiii', 'Oie!', 'oy', 'Olá, td bm?', 'oi   zubumafu tudo bom?'):
                with self.subTest(message=message):
                    answer, trace = respond(message)
                    self.assertIn('Como posso ajudar?', answer)
                    self.assertEqual(trace, [])

    def test_typos_and_abbreviations_still_require_the_right_source(self):
        cases = {'vcs tem violau?': 'search_products',
                 'qto custa a guitara?': 'product_pricing',
                 'posso devouver a compra?': 'search_store_policies',
                 'qual a regra de devolcao?': 'search_store_policies'}
        for message, required in cases.items():
            with self.subTest(message=message):
                self.assertEqual(_required_tool(message, []), required)

    def test_compound_typo_greeting_cannot_bypass_price_lookup(self):
        calls = []
        original = 'ui, qto custa a guitara?'

        def chat(**kwargs):
            calls.append(kwargs)
            self.assertEqual(next(m['content'] for m in kwargs['messages'] if m['role'] == 'user'),
                             original+'\n/no_think')
            return SimpleNamespace(message=SimpleNamespace(content='Preço inventado R$ 1,00', tool_calls=[]))
        answer, _ = respond(original, chat_fn=chat)
        self.assertEqual(len(calls), 2)
        self.assertIn('Não consegui confirmar', answer)
        self.assertNotIn('R$ 1,00', answer)

    def test_intent_aliases_never_rewrite_customer_email(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            tool_calls = [SimpleNamespace(function=SimpleNamespace(name='get_order_status',
                arguments={'order_id': '11', 'email': 'pixx@example.invalid'}))] if len(calls) == 1 else []
            return SimpleNamespace(message=SimpleNamespace(content='Untrusted order draft', tool_calls=tool_calls))

        with patch('zubumafu.orders.get_order_status', wraps=get_order_status) as lookup:
            answer, _ = respond('Consultar pedido 11, e-mail pixx@example.invalid', chat_fn=chat)
            lookup.assert_called_once_with(order_id='11', email='pixx@example.invalid')
        self.assertIn('Não consegui confirmar', answer)


if __name__ == '__main__':
    unittest.main()
