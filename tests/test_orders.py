"""Security and integrity checks for the demo-only order consultation."""

import csv
import json
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from zubumafu.agent import respond
from zubumafu.orders import get_order_status


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def rows(name):
    with (DATA_DIR / f"desafio_tecnico_ai_eng - {name}.csv").open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def call(name, **kwargs):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=kwargs))


class OrderLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orders = rows("orders")
        cls.customers = {row["customer_id"]: row for row in rows("customers")}
        cls.items = rows("order_items")
        cls.products = {row["product_id"]: row for row in rows("products")}
        cls.order = next(row for row in cls.orders if row["order_id"] in {item["order_id"] for item in cls.items})
        cls.email = cls.customers[cls.order["customer_id"]]["email"]

    def lookup(self, order=None, email=None):
        return json.loads(get_order_status(
            order_id=self.order["order_id"] if order is None else order,
            email=self.email if email is None else email,
        ))

    def test_asks_for_order_number_first_without_leaking_data(self):
        result = json.loads(get_order_status())
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["next_field"], "order_id")
        self.assertIn("número do pedido", result["message"])
        self.assertNotIn("items", result)
        self.assertNotIn("e-mail", result["message"])

    def test_asks_only_for_email_second_without_checking_order_existence(self):
        existing = json.loads(get_order_status(self.order["order_id"]))
        nonexistent = json.loads(get_order_status("999999"))
        self.assertEqual(existing, nonexistent)
        self.assertEqual(existing["status"], "needs_input")
        self.assertEqual(existing["next_field"], "email")
        self.assertNotIn("order_status", existing)

    def test_matches_email_case_insensitively_and_trims_spaces(self):
        result = self.lookup(email="  " + self.email.upper() + "  ")
        self.assertEqual(result["status"], "verified")

    def test_valid_order_contains_only_necessary_fields(self):
        result = self.lookup()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["order_id"], self.order["order_id"])
        self.assertEqual(result["order_status"], self.order["status"])
        self.assertEqual(result["tracking_code"], self.order["tracking_code"] or None)
        self.assertEqual(result["estimated_delivery"], self.order["estimated_delivery"] or None)
        self.assertEqual(result["source_type"], "historical_csv_snapshot_not_live_tracking")
        self.assertFalse(set(result).intersection({"email", "customer_id", "name", "phone", "notes", "payment_method"}))
        self.assertNotIn(self.email.casefold(), json.dumps(result, ensure_ascii=False).casefold())

    def test_original_total_preserved_not_repriced(self):
        result = self.lookup()
        self.assertEqual(Decimal(result["recorded_total_brl"]), Decimal(self.order["total_brl"]))
        self.assertNotIn("price_brl", json.dumps(result))

    def test_order_items_quantities_and_product_names_are_joined(self):
        result = self.lookup()
        source_items = [item for item in self.items if item["order_id"] == self.order["order_id"]]
        expected = [
            {"product_name": self.products[item["product_id"]]["name"], "quantity": int(item["quantity"])}
            for item in source_items
        ]
        self.assertEqual(result["items"], expected)

    def test_wrong_email_and_nonexistent_order_are_indistinguishable(self):
        other_customer = next(person for person in self.customers.values() if person["email"] != self.email)
        wrong_email = self.lookup(email=other_customer["email"])
        missing_order = self.lookup(order="999999999999", email=self.email)
        self.assertEqual(wrong_email, missing_order)
        self.assertEqual(wrong_email["status"], "not_verified")
        self.assertEqual(set(wrong_email), {"status", "message"})

    def test_invalid_order_ids_share_same_generic_response(self):
        for invalid in ["0", "-1", "1.0", " 01 ", "1e0", "abc", 1.5, True, [], {}]:
            with self.subTest(order_id=repr(invalid)):
                invalid_result = self.lookup(order=invalid)
                unknown_result = self.lookup(order="999999999999")
                self.assertEqual(invalid_result, unknown_result)

    def test_invalid_email_type_does_not_expose_data(self):
        self.assertEqual(self.lookup(email=[self.email]), self.lookup(order="999999999999"))

    def test_missing_tracking_and_estimate_remain_absent(self):
        order = next(row for row in self.orders if not row["tracking_code"] and not row["estimated_delivery"])
        email = self.customers[order["customer_id"]]["email"]
        result = self.lookup(order=order["order_id"], email=email)
        self.assertEqual(result["status"], "verified")
        self.assertIsNone(result["tracking_code"])
        self.assertIsNone(result["estimated_delivery"])
        self.assertIn("not proof", result["delivery_note"])

    def test_mocked_tool_cycle_returns_recorded_fields_to_model(self):
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(message=SimpleNamespace(
                    content="", tool_calls=[call("get_order_status", order_id=self.order["order_id"], email=self.email)]
                ))
            return SimpleNamespace(message=SimpleNamespace(
                # Deliberately unreliable LLM final text must be overridden.
                content="O total mudou para R$ 1,00 e entrega amanhã.", tool_calls=[]
            ))

        reply, trace = respond(f"Quero ver meu pedido {self.order['order_id']}, e-mail {self.email}", chat_fn=fake_chat)
        self.assertEqual(len(calls), 2)
        self.assertEqual(trace[0]["tool"], "get_order_status")
        self.assertEqual(trace[0]["status"], "verified")
        self.assertNotIn("email", trace[0])
        self.assertNotIn(self.email, str(trace))
        tool_messages = [msg for msg in calls[1]["messages"] if isinstance(msg, dict) and msg.get("role") == "tool"]
        self.assertEqual(len(tool_messages), 1)
        tool_result = json.loads(tool_messages[0]["content"])
        self.assertEqual(tool_result["recorded_total_brl"], self.lookup()["recorded_total_brl"])
        self.assertIn("Total registrado na compra", reply)
        self.assertNotIn("entrega amanhã", reply)
        self.assertTrue(all(attempt["think"] is False for attempt in calls))

    def test_wrong_email_mocked_model_cannot_leak_order_details(self):
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(message=SimpleNamespace(
                    content="", tool_calls=[call("get_order_status", order_id=self.order["order_id"], email="wrong@example.invalid")]
                ))
            return SimpleNamespace(message=SimpleNamespace(content="Seu pedido foi entregue ontem.", tool_calls=[]))

        reply, trace = respond(f"Onde está o pedido {self.order['order_id']}? E-mail wrong@example.invalid", chat_fn=fake_chat)
        self.assertEqual(reply, self.lookup(email="wrong@example.invalid")["message"])
        self.assertEqual(trace[0]["status"], "error")
        self.assertNotIn(self.order["total_brl"], reply)

    def test_mocked_missing_inputs_ask_only_one_thing(self):
        for arguments, next_expected in [({}, "número do pedido"), ({"order_id": self.order["order_id"]}, "e-mail cadastrado")]:
            with self.subTest(arguments=arguments):
                messages = []

                def fake_chat(**kwargs):
                    messages.append(kwargs)
                    if len(messages) == 1:
                        return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[call("get_order_status", **arguments)]))
                    return SimpleNamespace(message=SimpleNamespace(content="Conte o número e o e-mail!", tool_calls=[]))

                question = "Quero consultar meu pedido" + (" " + self.order["order_id"] if arguments else "")
                reply, trace = respond(question, chat_fn=fake_chat)
                self.assertIn(next_expected, reply)
                self.assertNotIn("Conte o número e o e-mail!", reply)
                self.assertEqual(trace[0]["status"], "needs_input")

    def test_three_turn_mocked_conversation_requests_id_then_email_then_data(self):
        history = []
        steps = [
            ("Onde está meu pedido?", {}, "número do pedido"),
            (self.order["order_id"], {"order_id": self.order["order_id"]}, "e-mail cadastrado"),
            (self.email, {"order_id": self.order["order_id"], "email": self.email}, "Total registrado"),
        ]
        for question, arguments, expected in steps:
            turns = []

            def fake_chat(**kwargs):
                turns.append(kwargs)
                if len(turns) == 1:
                    return SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[call("get_order_status", **arguments)]))
                return SimpleNamespace(message=SimpleNamespace(content="Resposta do modelo", tool_calls=[]))

            reply, trace = respond(question, history=history, chat_fn=fake_chat)
            self.assertIn(expected, reply)
            self.assertEqual(trace[0]["tool"], "get_order_status")
            self.assertEqual(len(turns), 2)
            history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": reply}])
        self.assertNotIn(self.email, history[-1]["content"])

    def test_rejects_unverified_order_claim_without_tool(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="Seu pedido foi entregue.", tool_calls=[]))

        reply, trace = respond("Pode consultar meu pedido?", chat_fn=fake_chat)
        self.assertIn("número do pedido", reply)
        self.assertEqual(trace, [])

    def test_rejects_unverified_followup_claim_without_tool(self):
        def fake_chat(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="O pedido já foi entregue.", tool_calls=[]))

        history = [{"role": "assistant", "content": "Obrigado! Agora, qual é o e-mail cadastrado nesse pedido?"}]
        reply, trace = respond("wrong@example.invalid", history=history, chat_fn=fake_chat)
        self.assertIn("número do pedido", reply)
        self.assertEqual(trace, [])


if __name__ == "__main__":
    unittest.main()
