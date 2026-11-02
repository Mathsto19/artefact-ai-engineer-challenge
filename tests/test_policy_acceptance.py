import unittest

from scripts.check_policies import asks_receipt_date


class PolicyAcceptanceChecks(unittest.TestCase):
    def test_old_packaging_reply_does_not_pass_as_receipt_date_question(self):
        answer = "Você pode solicitar em 7 dias após receber. O instrumento está na embalagem? Há sinais de uso?"
        self.assertFalse(asks_receipt_date(answer))

    def test_explicit_receipt_date_questions_are_recognized(self):
        for answer in ["Quando você recebeu o instrumento?", "Qual foi a data de recebimento?", "Que dia chegou o violão?"]:
            with self.subTest(answer=answer):
                self.assertTrue(asks_receipt_date(answer))

    def test_yes_no_receipt_question_does_not_establish_date(self):
        self.assertFalse(asks_receipt_date("Você já recebeu o instrumento?"))
