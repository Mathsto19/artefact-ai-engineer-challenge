import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from zubumafu.agent import respond
from zubumafu.orders import _order_records, get_order_status, order_context


class OrderGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        orders, customers, _, _ = _order_records()
        cls.order = next(iter(orders.values()))
        cls.identifier = cls.order["order_id"]
        cls.email = customers[cls.order["customer_id"]]["email"]

    def run_model(self, question, arguments, history=None, tool="get_order_status", truncated=False):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name=tool, arguments=arguments)
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="Seu pedido foi entregue amanhã por R$ 1,00.", tool_calls=[]),
                                   done_reason="length" if truncated else "stop")

        return respond(question, history, chat_fn=chat)

    def test_model_cannot_supply_email_not_provided_by_customer(self):
        reply, trace = self.run_model(f"Quero ver o pedido {self.identifier}",
                                     {"order_id": self.identifier, "email": self.email})
        self.assertIn("Não consegui confirmar", reply)
        self.assertNotIn("Total registrado", reply)
        self.assertEqual(trace[0]["status"], "error")

    def test_assistant_text_cannot_supply_customer_credentials(self):
        reply, _ = self.run_model(f"Quero ver o pedido {self.identifier}",
                                 {"order_id": self.identifier, "email": self.email},
                                 [{"role": "assistant", "content": f"Seu e-mail é {self.email}"}])
        self.assertNotIn("Total registrado", reply)

    def test_latest_wrong_email_cannot_be_replaced_with_previous_valid_one(self):
        history = [{"role": "user", "content": f"Pedido {self.identifier}, {self.email}"},
                   {"role": "assistant", "content": "Conferi o registro demonstrativo do seu pedido."}]
        reply, _ = self.run_model("wrong@example.invalid", {"order_id": self.identifier, "email": self.email}, history)
        self.assertIn("Não consegui confirmar", reply)
        self.assertNotIn("Total registrado", reply)

    def test_new_order_number_requires_email_again(self):
        history = [{"role": "user", "content": f"Pedido {self.identifier}, {self.email}"}]
        context = order_context("E o pedido 999999?", history)
        self.assertEqual(context, {"order_id": "999999", "email": ""})

    def test_context_does_not_truncate_invalid_customer_identifiers(self):
        for identifier in ["1.5", "1e0", "01", "1-2", "1_invalid"]:
            with self.subTest(identifier=identifier):
                context = order_context(f"Pedido {identifier}, {self.email}", [])
                self.assertEqual(context["order_id"], "")

    def test_subject_change_closes_order_context(self):
        history = [{"role": "user", "content": f"Pedido {self.identifier}, {self.email}"}]
        self.assertIsNone(order_context("Quais violões custam até R$ 1000?", history))

    def test_email_local_part_cannot_change_order_number(self):
        context = order_context("pedido999@example.invalid", [{"role": "user", "content": f"Pedido {self.identifier}"}])
        self.assertEqual(context["order_id"], self.identifier)
        self.assertEqual(context["email"], "pedido999@example.invalid")

    def test_order_word_in_general_return_question_keeps_pdf_flow(self):
        calls = []

        def chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                function = SimpleNamespace(name="search_store_policies", arguments={"question": "Devolução por arrependimento", "topic": "returns"})
                return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[SimpleNamespace(function=function)]))
            return SimpleNamespace(message=SimpleNamespace(content="A compra foi online ou na loja física?", tool_calls=[]))

        reply, trace = respond("Me arrependi do meu pedido. Posso devolver?", chat_fn=chat)
        self.assertIn("online ou na loja física", reply)
        self.assertIn("Fonte consultada", reply)
        self.assertEqual(trace[0]["tool"], "search_store_policies")
        self.assertNotIn("número do pedido", reply)

    def test_unsolicited_order_tool_call_cannot_reveal_data(self):
        reply, trace = self.run_model("Oi", {"order_id": self.identifier, "email": self.email})
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace[0]["status"], "error")
        reply, trace = self.run_model(f"Pedido {self.identifier}, {self.email}", ["email"])
        self.assertIn("Não consegui confirmar", reply)
        self.assertEqual(trace[0]["status"], "error")

    def test_other_successful_source_cannot_authorize_order_details(self):
        reply, _ = self.run_model(f"Pedido {self.identifier}, {self.email}",
                                 {"product_id": 127}, tool="get_product_pricing")
        self.assertIn("Não consegui confirmar", reply)
        self.assertNotIn("Seu pedido foi entregue", reply)

    def test_source_read_failure_is_structured_without_customer_data(self):
        with patch("zubumafu.orders._order_records", side_effect=OSError("simulated source failure")):
            result = json.loads(get_order_status(self.identifier, self.email))
        self.assertEqual(result["status"], "source_error")
        self.assertNotIn("items", result)
        self.assertNotIn(self.email, str(result))

    def test_truncated_order_draft_cannot_replace_verified_fields(self):
        reply, trace = self.run_model(f"Pedido {self.identifier}, {self.email}",
                                     {"order_id": self.identifier, "email": self.email}, truncated=True)
        self.assertIn("Total registrado na compra", reply)
        self.assertNotIn("entregue amanhã", reply)
        self.assertEqual(trace[0]["reply_origin"], "python_order_result_template")


if __name__ == "__main__":
    unittest.main()
