"""Regression tests for the review's observed response-quality failures."""

import json
import unittest
from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import patch

from zubumafu.agent import respond
from zubumafu.catalog import search_products
from zubumafu.pricing import get_product_pricing
from zubumafu.response_quality import clean_model_answer, render_catalog, render_pricing, requested_budget


def tool(name, **arguments):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


class QualityTests(unittest.TestCase):
    def test_catalog_sources_mixed_strings_without_generic_nylon_claim(self):
        payload = json.loads(search_products(category="violão", max_price_brl=1000))
        reply = render_catalog(payload)
        self.assertIn("cordas de nylon", reply)
        self.assertIn("cordas de aço", reply)
        self.assertIn("Shelby SN-100 Folk Aço Preto", reply)
        self.assertIn("Rozini RC-104 Nylon Estudante", reply)
        self.assertNotIn("para iniciantes", reply)
        self.assertNotIn("três melhores", reply)
        self.assertIn("ordenadas por preço final", reply)

    def test_unknown_product_is_not_conflated_with_unavailability(self):
        unknown = json.loads(search_products(query="Zubumafu X-999"))
        unavailable = json.loads(search_products(query="Shelby SN-7C 7 Cordas Nylon Natural"))
        over_budget = json.loads(search_products(category="violão", max_price_brl=100))
        self.assertEqual(unknown["no_match_reason"], "not_in_catalog")
        self.assertEqual(unavailable["no_match_reason"], "unavailable")
        self.assertEqual(over_budget["no_match_reason"], "over_budget")
        self.assertIn("não localizei", render_catalog(unknown).casefold())
        self.assertIn("não está disponível", render_catalog(unavailable))
        self.assertIn("orçamento", render_catalog(over_budget))

    def test_promotional_pix_price_is_not_described_as_extra_savings(self):
        payload = json.loads(get_product_pricing(product_id=127, payment_method="pix"))
        reply = render_pricing(payload)
        self.assertIn("R$ 359,00", reply)
        self.assertIn("R$ 323,10", reply)
        self.assertIn("não acumula", reply)
        self.assertIn("valor permanece o mesmo", reply)
        self.assertNotIn("se quiser economizar", reply.casefold())

    def test_unpromoted_pix_is_still_applied(self):
        payload = json.loads(get_product_pricing(product_id=93, payment_method="pix"))
        reply = render_pricing(payload)
        if payload["pricing"]["active_promotion"]:
            self.assertIn("não acumula", reply)
        else:
            self.assertIn("5% de desconto", reply)

    def test_cleanup_removes_thinking_duplicate_invitations_and_all_emoji(self):
        model_reply = "<think>segredo da análise</think>Oi! 🎸😊 👨‍👩‍👧‍👦 🇧🇷 1️⃣\nSe quiser, posso detalhar.\nSe quiser, posso detalhar mais."
        reply = clean_model_answer(model_reply)
        self.assertNotIn("segredo", reply)
        self.assertEqual(reply.count("Se quiser"), 1)
        self.assertNotIn("😊", reply)
        self.assertNotIn("🎸", reply)
        self.assertNotIn("🇧", reply)
        self.assertNotIn("\u200d", reply)
        self.assertNotIn("\ufe0f", reply)
        self.assertNotIn("\u20e3", reply)

    def test_catalog_agent_ignores_unsupported_model_superlatives_and_profile(self):
        attempts = []

        def fake_chat(**kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                return SimpleNamespace(message=SimpleNamespace(
                    content="", tool_calls=[tool("search_products", category="violão", max_price_brl=1000)]))
            return SimpleNamespace(message=SimpleNamespace(
                content="Como você é iniciante, estes são os três melhores, todos de nylon! 🎸🎶", tool_calls=[]))

        reply, trace = respond("Quais violões até R$1000?", chat_fn=fake_chat)
        self.assertEqual(trace[0]["tool"], "search_products")
        self.assertIn("cordas de aço", reply)
        self.assertNotIn("você é iniciante", reply.casefold())
        self.assertNotIn("três melhores", reply.casefold())
        self.assertEqual(len(attempts), 2)

    def test_error_tool_cannot_support_model_invented_facts(self):
        attempts = []

        def fake_chat(**kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool("invalid_tool")]))
            return SimpleNamespace(message=SimpleNamespace(content="A guitarra custa R$1 e está em estoque.", tool_calls=[]))

        reply, trace = respond("Quais guitarras estão em estoque?", chat_fn=fake_chat)
        self.assertEqual(trace[0]["status"], "rejected")
        self.assertIn("consulta aos arquivos falhou", reply)
        self.assertNotIn("R$1", reply)

    def test_ollama_failure_has_recoverable_answer(self):
        def broken(**kwargs):
            raise ConnectionError("private machine address")

        reply, trace = respond("Quero uma guitarra", chat_fn=broken)
        self.assertIn("Ollama", reply)
        self.assertNotIn("private machine address", reply)
        self.assertEqual(trace, [])

    def test_obvious_offtopic_does_not_call_commerce_or_model(self):
        def forbidden(**kwargs):
            raise AssertionError("Model should not be called for an obvious off-topic intent")

        reply, trace = respond("Qual é a previsão do tempo para amanhã?", chat_fn=forbidden)
        self.assertIn("instrumentos musicais", reply)
        self.assertEqual(trace, [])

    def test_budget_comparison_uses_verified_final_price(self):
        payload = json.loads(get_product_pricing(product_id=127))
        self.assertIn('cabe no orçamento', render_pricing(payload, Decimal('340')))
        self.assertIn('ultrapassa o orçamento', render_pricing(payload, Decimal('300')))
        self.assertEqual(requested_budget('Cabe no orçamento de R$ 1.000,00?'), Decimal('1000'))
        self.assertIsNone(requested_budget('Orçamento entre R$ 300 e R$ 400'))

    def test_uncertain_promotion_is_not_reported_as_over_budget(self):
        with patch('zubumafu.catalog.pricing_for_product', return_value={'status': 'ambiguous'}):
            payload = json.loads(search_products(query='Kalani KAL-700T', max_price_brl=340))
        self.assertEqual(payload['no_match_reason'], 'unconfirmed_prices')
        self.assertIn('não consegui confirmar o preço final', render_catalog(payload))

    def test_wrong_category_does_not_claim_named_product_is_absent(self):
        payload = json.loads(search_products(category='guitarra', query='Kalani KAL-700T Tenor Natural'))
        self.assertEqual(payload['total_matches'], 0)
        self.assertEqual(payload['no_match_reason'], 'no_category_match')
        self.assertNotIn('não localizei esse modelo', render_catalog(payload).casefold())

    def test_specific_price_advertises_pricing_tool_and_binds_requested_pix(self):
        attempts = []

        def fake_chat(**kwargs):
            attempts.append(kwargs)
            self.assertEqual([function.__name__ for function in kwargs['tools']],
                             ['get_product_pricing'] if len(attempts) == 1 else [])
            if len(attempts) == 1:
                return SimpleNamespace(message=SimpleNamespace(content='', tool_calls=[tool('get_product_pricing', product_id=127, payment_method='standard')]))
            return SimpleNamespace(message=SimpleNamespace(content='PIX reduz mais o preço.', tool_calls=[]))

        history = [{'role': 'user', 'content': 'Quanto custa o Kalani KAL-700T Tenor Natural?'}]
        reply, trace = respond('E pagando no PIX, fica mais barato?', history, chat_fn=fake_chat)
        self.assertIn('valor permanece o mesmo', reply)
        self.assertEqual(trace[0]['argument_overrides'], ['payment_method'])
        self.assertEqual(trace[0]['pricing']['payment_method'], 'pix')
        self.assertEqual(trace[0]['pricing']['final_price_brl'], '323.10')

    def test_truncated_source_free_price_draft_gets_one_bounded_repair(self):
        attempts = []

        def fake_chat(**kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                return SimpleNamespace(message=SimpleNamespace(content='Unfinished internal planning', tool_calls=[]), done_reason='length')
            if len(attempts) == 2:
                return SimpleNamespace(message=SimpleNamespace(content='', tool_calls=[tool('get_product_pricing', product_id=127)]))
            return SimpleNamespace(message=SimpleNamespace(content='Untrusted budget draft', tool_calls=[]))

        reply, trace = respond('Esse Kalani cabe no orçamento de R$ 340?', [{'role': 'user', 'content': 'Quanto custa o Kalani KAL-700T Tenor Natural?'}], chat_fn=fake_chat)
        self.assertEqual(len(attempts), 3)
        self.assertIn('cabe no orçamento', reply)
        self.assertNotIn('planning', reply)

    def test_steel_followup_requeries_only_the_displayed_models(self):
        first = render_catalog(json.loads(search_products(category='violão', max_price_brl=1000)))
        history = [{'role': 'user', 'content': 'Quais violões disponíveis custam até R$ 1.000?'},
                   {'role': 'assistant', 'content': first}]
        attempts = []

        def chat(**kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                return SimpleNamespace(message=SimpleNamespace(content='', tool_calls=[tool('search_products', category='guitarra', query='cordas de aço')]))
            return SimpleNamespace(message=SimpleNamespace(content='Todos são de nylon para iniciantes.', tool_calls=[]))

        reply, trace = respond('Quais dessas opções têm cordas de aço?', history, chat_fn=chat)
        self.assertIn('Shelby SN-100', reply)
        self.assertNotIn('Giannini', reply)
        self.assertNotIn('iniciante', reply)
        self.assertEqual(trace[0]['matches'], 1)
        self.assertEqual(trace[0]['filters']['strings_material'], 'steel')
        self.assertEqual(trace[0]['filters']['max_price_brl'], '1000')
        self.assertEqual(trace[0]['invoked_by'], 'application_reference_lookup')
        self.assertEqual(attempts, [])

    def test_sdk_timeout_has_a_recoverable_answer(self):
        from httpx import ConnectTimeout
        with patch('ollama.Client') as client:
            client.return_value.chat.side_effect = ConnectTimeout('private machine address')
            reply, trace = respond('Quais guitarras estão disponíveis?')
        self.assertIn('Ollama', reply)
        self.assertNotIn('private machine address', reply)
        self.assertEqual(trace, [])

    def test_named_model_does_not_inherit_guessed_category(self):
        attempts = []

        def chat(**kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                return SimpleNamespace(message=SimpleNamespace(content='', tool_calls=[tool('search_products', category='guitarra', query='Shelby SN-7C 7 Cordas Nylon Natural')]))
            return SimpleNamespace(message=SimpleNamespace(content='Não existe na loja.', tool_calls=[]))

        reply, trace = respond('Vocês têm o Shelby SN-7C 7 Cordas Nylon Natural?', chat_fn=chat)
        self.assertIn('não está disponível', reply)
        self.assertEqual(trace[0]['filters']['category'], '')
        self.assertIn('category', trace[0]['argument_overrides'])


if __name__ == "__main__":
    unittest.main()
