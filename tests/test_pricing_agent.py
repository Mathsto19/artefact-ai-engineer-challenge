import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from zubumafu.agent import respond, _simple_category_recommendation


class PricingAgentTests(unittest.TestCase):
    history = [
        {"role": "user", "content": "Quanto custa o Kalani KAL-700T Tenor Natural?"},
        {"role": "assistant", "content": "O Kalani custa R$ 323,10 em promoção."},
    ]

    def test_price_recommendations_offer_catalog_instead_of_exact_model_lookup(self):
        for question in ('me recomenda uma guitarra com um bom preço',
                         'Me indica um violão com bom custo-benefício',
                         'Quero uma guitarra Fender com bom preço'):
            with self.subTest(question=question):
                calls = []

                def chat(**kwargs):
                    calls.append(kwargs)
                    if len(calls) == 1:
                        self.assertEqual([tool.__name__ for tool in kwargs['tools']], ['search_products'])
                        category = 'violão' if 'violão' in question else 'guitarra'
                        function = SimpleNamespace(name='search_products', arguments={'category': category})
                        return SimpleNamespace(message=SimpleNamespace(content='', tool_calls=[SimpleNamespace(function=function)]))
                    return SimpleNamespace(message=SimpleNamespace(content='OK', tool_calls=[]))

                answer, trace = respond(question, self.history, chat_fn=chat)
                self.assertIn('Encontrei opções', answer)
                self.assertIn('R$', answer)
                self.assertEqual(trace[0]['tool'], 'search_products')
                self.assertEqual(trace[0]['filters']['query'], '')
                self.assertEqual(trace[0]['filters']['max_price_brl'], '0')
                self.assertGreater(trace[0]['matches'], 0)

    def test_plain_recommendations_query_real_catalog_without_inference(self):
        for question in ('me recomenda uma guitarra com um bom preço',
                         'me recomneda uma guitarra com um bom preço',
                         'Me recomenda uma guitara com um bom preco'):
            with self.subTest(question=question):
                model = Mock(side_effect=AssertionError('No model lookup needed'))
                answer, trace = respond(question, self.history, chat_fn=model)
                model.assert_not_called()
                self.assertIn('Fender Telecaster Player Series', answer)
                self.assertIn('R$ 5.400,00', answer)
                self.assertNotIn('Não encontrei esse modelo', answer)
                self.assertEqual(trace[0]['filters']['category'], 'guitarra')
                self.assertEqual(trace[0]['matches'], 5)
                self.assertEqual(trace[0]['invoked_by'], 'application_catalog_lookup')

    def test_direct_recommendation_does_not_drop_constraints_or_names(self):
        for question in ('me recomenda uma guitarra Fender com um bom preço',
                         'me recomenda uma guitarra de sete cordas',
                         'me recomenda uma guitarra até R$ 1000',
                         'me recomenda uma guitarra com frete grátis',
                         'me recomenda uma guitarra com um bom preço no PIX'):
            with self.subTest(question=question):
                self.assertIsNone(_simple_category_recommendation(question))

    def test_direct_catalog_failure_never_claims_product_is_missing(self):
        with patch('zubumafu.agent.search_products', side_effect=OSError):
            answer, trace = respond('me recomenda uma guitarra com um bom preço')
        self.assertIn('Não consegui consultar', answer)
        self.assertNotIn('esse modelo', answer)
        self.assertEqual(trace[0]['status'], 'error')

    def test_pix_followup_receives_pricing_result_and_preserves_history(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name="get_product_pricing", arguments={"product_id": 127, "payment_method": "pix"})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="Continua em R$ 323,10: os descontos não são cumulativos.", tool_calls=[]))

        reply, trace = respond("E pagando no PIX, fica mais barato?", self.history, chat_fn=chat)
        self.assertIn("não acumula", reply)
        self.assertEqual(trace[0]["product_id"], "127")
        self.assertEqual(trace[0]["status"], "ok")
        self.assertEqual(calls[0]["messages"][1:3], self.history)
        result = json.loads(next(m["content"] for m in calls[1]["messages"] if m.get("role") == "tool"))
        self.assertEqual(result["pricing"]["final_price_brl"], "323.10")
        self.assertTrue(result["pricing"]["pix_non_cumulative"])
        self.assertEqual(result["pricing"]["final_price_display_brl"], "R$ 323,10")

    def test_pix_followup_cannot_reuse_old_price_without_new_lookup(self):
        def chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="Sim, fica R$ 306,95.", tool_calls=[]))

        reply, trace = respond("E pagando no PIX, fica mais barato?", self.history, chat_fn=chat)
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace, [])

    def test_policy_lookup_alone_cannot_authorize_product_specific_price(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name="search_store_policies", arguments={"question": "PIX", "topic": "payments"})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="Fica R$ 306,95.", tool_calls=[]))

        reply, trace = respond("E pagando no PIX, fica mais barato?", self.history, chat_fn=chat)
        self.assertEqual(trace[0]["status"], "ok")
        self.assertIn("Não consegui confirmar", reply)

    def test_promotion_quote_is_rendered_entirely_from_catalog_source(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name="search_products", arguments={"query": "Kalani KAL-700T"})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="O preço final é R$ 323,10.", tool_calls=[]))

        reply, trace = respond("Quanto custa o Kalani KAL-700T?", chat_fn=chat)
        self.assertIn("tabela: R$ 359,00", reply)
        self.assertIn("desconto de 10%", reply)
        self.assertIn("R$ 323,10", reply)
        self.assertNotIn("O preço final é R$ 323,10.", reply)
        self.assertEqual(trace[0]["reply_origin"], "python_catalog_result_template")

    def test_missing_lookup_is_repaired_within_existing_request_limit(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(message=SimpleNamespace(content="Sim, basta confiar no preço anterior.", tool_calls=[]))
            if len(calls) == 2:
                self.assertIn("consulta nova", kwargs["messages"][-1]["content"])
                function = SimpleNamespace(name="get_product_pricing", arguments={"product_id": 127})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="Sim, R$ 323,10 cabe no orçamento.", tool_calls=[]))

        reply, trace = respond("Esse Kalani entra em um orçamento de R$ 340?", self.history, chat_fn=chat)
        self.assertEqual(len(calls), 3)
        self.assertEqual(trace[0]["status"], "ok")
        self.assertIn("cabe", reply)
        self.assertNotIn("basta confiar", reply)

    def test_repair_does_not_allow_indefinite_source_free_answers(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(message=SimpleNamespace(content="É só usar o histórico.", tool_calls=[]))

        reply, trace = respond("E no PIX?", self.history, chat_fn=chat)
        self.assertEqual(len(calls), 2)
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace, [])


if __name__ == "__main__":
    unittest.main()
