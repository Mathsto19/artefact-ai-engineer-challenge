import copy
import json
from types import SimpleNamespace
import unittest

from zubumafu.agent import respond


class SimulatedToolChat:
    def __init__(self, name, arguments, answer):
        self.name, self.arguments, self.answer = name, arguments, answer
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        tools = []
        if len(self.calls) == 1:
            tools = [SimpleNamespace(function=SimpleNamespace(name=self.name, arguments=self.arguments))]
        return SimpleNamespace(message=SimpleNamespace(content="" if tools else self.answer, tool_calls=tools))


class PolicyAgentTests(unittest.TestCase):
    def test_switching_to_warranty_does_not_force_regret_clarification(self):
        history = [{"role": "user", "content": "Me arrependi da compra"}]
        fake = SimulatedToolChat("search_store_policies", {"question": "Qual a garantia?", "topic": "warranty"},
                                 "O manual descreve a garantia legal na seção 8.")
        answer, trace = respond("Qual a garantia?", history, chat_fn=fake)
        self.assertIn("garantia legal", answer)
        self.assertNotIn("clarification_field", trace[0])

    def test_regret_flow_overrides_draft_that_skips_channel_and_invents_action(self):
        fake = SimulatedToolChat("search_store_policies", {"question": "Me arrependi da compra"},
                                 "Sua devolução foi autorizada; siga o processo na loja virtual.")
        answer, trace = respond("Comprei um violão e me arrependi. Posso devolver?", chat_fn=fake)
        self.assertIn("a compra foi online ou na loja física?", answer)
        self.assertNotIn("autorizada", answer)
        self.assertNotIn("loja virtual", answer)
        self.assertEqual(trace[0]["clarification_field"], "purchase_channel")
        self.assertEqual(trace[0]["reply_origin"], "source_verified_clarification_template")

    def test_receipt_question_is_not_replaced_by_packaging_questions(self):
        history = [{"role": "user", "content": "Me arrependi da compra"},
                   {"role": "assistant", "content": "Foi online ou presencial?"}]
        fake = SimulatedToolChat("search_store_policies", {"question": "Devolução online", "topic": "returns"},
                                 "A embalagem está intacta? Basta seguir o processo na loja virtual.")
        answer, trace = respond("Foi online.", history, chat_fn=fake)
        self.assertIn("Quando você recebeu o instrumento?", answer)
        self.assertNotIn("loja virtual", answer)
        self.assertEqual(trace[0]["clarification_field"], "receipt_date")

    def test_already_provided_channel_and_receipt_date_are_not_asked_again(self):
        fake = SimulatedToolChat("search_store_policies", {"question": "Arrependimento online", "topic": "returns"},
                                 "Obrigado pelas informações; vou orientar pelos requisitos do manual.")
        answer, trace = respond("Comprei online, recebi ontem e me arrependi", chat_fn=fake)
        self.assertNotIn("Quando você recebeu", answer)
        self.assertNotIn("clarification_field", trace[0])

    def test_assistant_text_does_not_establish_customer_purchase_channel(self):
        history = [{"role": "assistant", "content": "Você fez uma compra online."}]
        fake = SimulatedToolChat("search_store_policies", {"question": "Arrependimento", "topic": "returns"}, "Pode devolver.")
        answer, trace = respond("Me arrependi da compra", history, chat_fn=fake)
        self.assertEqual(trace[0]["clarification_field"], "purchase_channel")
        self.assertIn("online ou na loja física", answer)

    def test_policy_cycle_returns_pdf_result_and_verified_reference(self):
        fake = SimulatedToolChat("search_store_policies", {"question": "Quero devolver minha compra"},
                                 "Entendo. A compra foi online ou presencial?")
        answer, trace = respond("Quero devolver minha compra", chat_fn=fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("A compra foi online", answer)
        self.assertIn("seção(ões) 4, página(s) 4", answer)
        self.assertEqual(trace[0]["pages"], [4])
        self.assertEqual(trace[0]["chapters"], [4])
        self.assertEqual(trace[0]["status"], "ok")
        returned = [message for message in fake.calls[1]["messages"] if message["role"] == "tool"]
        self.assertIn("7 (sete) dias", json.loads(returned[0]["content"])["sections"][0]["text"])
        self.assertTrue(all(call["think"] is False for call in fake.calls))

    def test_policy_question_requires_policy_lookup(self):
        def fake(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="A loja abre às 8h.", tool_calls=[]))

        answer, trace = respond("Qual o horário da loja?", chat_fn=fake)
        self.assertIn("Não consegui confirmar", answer)
        self.assertEqual(trace, [])

    def test_catalog_success_does_not_authorize_policy_answer(self):
        fake = SimulatedToolChat("search_products", {}, "A devolução está autorizada.")
        answer, trace = respond("Posso devolver minha compra?", chat_fn=fake)
        self.assertEqual(trace[0]["status"], "ok")
        self.assertIn("Não consegui confirmar", answer)
        self.assertNotIn("autorizada", answer)

    def test_policy_success_does_not_authorize_catalog_answer(self):
        fake = SimulatedToolChat("search_store_policies", {"question": "Qual o horário?"}, "A guitarra custa R$ 1.")
        answer, _ = respond("Quanto custa a guitarra?", chat_fn=fake)
        self.assertIn("Não consegui confirmar", answer)

    def test_failed_policy_search_does_not_authorize_answer_or_reference(self):
        fake = SimulatedToolChat("search_store_policies", {"question": "xyz-unknown"}, "A loja abre às 8h.")
        answer, trace = respond("Qual o horário?", chat_fn=fake)
        self.assertEqual(trace[0]["status"], "error")
        self.assertIn("Não consegui confirmar", answer)
        self.assertNotIn("Fonte consultada", answer)

    def test_online_followup_keeps_context_and_requires_fresh_policy_lookup(self):
        history = [{"role": "user", "content": "Comprei um violão e me arrependi. Posso devolver?"},
                   {"role": "assistant", "content": "A compra foi online ou presencial?"}]

        def no_tool(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="Pode devolver.", tool_calls=[]))

        blocked, _ = respond("Foi online.", history, chat_fn=no_tool)
        self.assertIn("Não consegui confirmar", blocked)
        fake = SimulatedToolChat("search_store_policies", {"question": "Arrependimento de compra online", "topic": "returns"},
                                 "Quando você recebeu o instrumento?")
        answer, trace = respond("Foi online.", history, chat_fn=fake)
        self.assertEqual(fake.calls[0]["messages"][1:3], history)
        self.assertIn("Quando você recebeu", answer)
        self.assertEqual(trace[0]["chapters"], [4])

    def test_thanks_after_return_discussion_does_not_force_lookup(self):
        history = [{"role": "user", "content": "Posso devolver minha compra?"}]

        def fake(**kwargs):
            return SimpleNamespace(message=SimpleNamespace(content="Por nada!", tool_calls=[]))

        answer, trace = respond("Obrigado", history, chat_fn=fake)
        self.assertEqual(answer, "Por nada!")
        self.assertEqual(trace, [])
