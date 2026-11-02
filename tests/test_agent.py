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
