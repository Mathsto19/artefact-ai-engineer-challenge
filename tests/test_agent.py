import json
import unittest
from types import SimpleNamespace

from zubumafu.agent import respond


def tool_call(name, **kwargs):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=kwargs))


class FakeChat:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call("search_products", category="violão", max_price_brl=1000)]))
        return SimpleNamespace(message=SimpleNamespace(content="Encontrei opções de violão conforme o catálogo.", tool_calls=[]))


class AgentTests(unittest.TestCase):
    def test_truncated_generation_returns_fallback(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(
                message=SimpleNamespace(content="Resposta incompleta", tool_calls=[]),
                done_reason="length",
            )

        reply, _ = respond("Oi", chat_fn=fake_chat)
        self.assertIn("Não consegui concluir", reply)
        self.assertNotIn("Resposta incompleta", reply)

    def test_reasoning_markup_is_not_returned_to_customer(self):
        for content in [
            "<think>Private planning.</think>Olá! Como posso ajudar?",
            "Private planning from a prefilled block.</think>Olá! Como posso ajudar?",
        ]:
            with self.subTest(content=content):
                def fake_chat(**kwargs):
                    return SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=[]))

                reply, _ = respond("Oi", chat_fn=fake_chat)
                self.assertEqual(reply, "Olá! Como posso ajudar?")

    def test_incomplete_reasoning_is_not_returned_to_customer(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="<think>Unfinished private planning", tool_calls=[]))

        reply, _ = respond("Oi", chat_fn=fake_chat)
        self.assertIn("Não consegui preparar", reply)

    def test_too_many_tool_calls_are_not_partially_executed(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call("search_products")] * 6))

        reply, trace = respond("Quero uma guitarra", chat_fn=fake_chat)
        self.assertIn("operações demais", reply)
        self.assertEqual(trace, [])

    def test_rejected_tool_does_not_authorize_catalog_answer(self):
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call("invent_inventory")]))
            return SimpleNamespace(message=SimpleNamespace(content="A guitarra custa R$ 100.", tool_calls=[]))

        reply, trace = respond("Quanto custa a guitarra?", chat_fn=fake_chat)
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace[0]["status"], "rejected")

    def test_failed_lookup_does_not_authorize_catalog_answer(self):
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call("search_products", max_price_brl=-1)]))
            return SimpleNamespace(message=SimpleNamespace(content="A guitarra custa R$ 100.", tool_calls=[]))

        reply, trace = respond("Quanto custa a guitarra?", chat_fn=fake_chat)
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace[0]["status"], "error")

    def test_other_instrument_queries_also_require_lookup(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="Temos opções por R$ 100.", tool_calls=[]))

        for question in ["Quais baixos vocês têm?", "Me indique um teclado", "Busco um violao"]:
            with self.subTest(question=question):
                reply, _ = respond(question, chat_fn=fake_chat)
                self.assertIn("Não consegui confirmar", reply)

    def test_repeated_tool_requests_are_bounded(self):
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call("search_products", category="violão")]))

        reply, trace = respond("Quero um violão", chat_fn=fake_chat)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(trace), 3)
        self.assertIn("mais específica", reply)

    def test_full_tool_cycle_with_mocked_llm(self):
        fake = FakeChat()
        reply, trace = respond("Quais violões disponíveis custam até R$ 1000?", chat_fn=fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("Encontrei opções", reply)
        self.assertEqual(trace[0]["tool"], "search_products")
        self.assertEqual(trace[0]["status"], "ok")
        self.assertGreater(trace[0]["matches"], 0)
        tool_messages = [message for message in fake.calls[1]["messages"] if isinstance(message, dict) and message["role"] == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertTrue(json.loads(tool_messages[0]["content"])["products"])
        self.assertTrue(all(call["think"] is False for call in fake.calls))

    def test_prevent_unsupported_catalog_answer_without_tool(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="Custa R$ 100.", tool_calls=[]))

        reply, trace = respond("Quanto custa a guitarra?", chat_fn=fake_chat)
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace, [])


if __name__ == "__main__":
    unittest.main()
