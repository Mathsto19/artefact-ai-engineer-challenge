import json
import unittest
from types import SimpleNamespace

from zubumafu.agent import respond


class PricingAgentTests(unittest.TestCase):
    history = [
        {"role": "user", "content": "Quanto custa o Kalani KAL-700T Tenor Natural?"},
        {"role": "assistant", "content": "O Kalani custa R$ 323,10 em promoção."},
    ]

    def test_pix_followup_receives_pricing_result_and_preserves_history(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name="get_product_pricing", arguments={"product_id": 127, "payment_method": "pix"})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="Continua em R$ 323,10: os descontos não são cumulativos.", tool_calls=[]))

        reply, trace = respond("E pagando no PIX, fica mais barato?", self.history, chat_fn=chat)
        self.assertIn("não são cumulativos", reply)
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

    def test_missing_promotion_fields_are_completed_from_catalog_source(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name="search_products", arguments={"query": "Kalani KAL-700T"})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="O preço final é R$ 323,10.", tool_calls=[]))

        reply, trace = respond("Quanto custa o Kalani KAL-700T?", chat_fn=chat)
        self.assertIn("Preço de tabela: R$ 359,00.", reply)
        self.assertIn("Promoção ativa: 10%.", reply)
        self.assertIn("O preço final é R$ 323,10.", reply)
        self.assertEqual(trace[0]["added_price_fields"], ["list_price", "discount_percent"])
        self.assertEqual(trace[0]["reply_origin"], "model_with_source_price_details")

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
