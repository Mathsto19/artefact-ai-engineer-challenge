import json
import unittest
from unittest.mock import patch

from zubumafu.policies import _sections, search_store_policies


class PolicyRetrievalTests(unittest.TestCase):
    def test_all_ten_chapters_are_indexed(self):
        sections = _sections()
        self.assertEqual(set(sections), set(range(1, 11)))
        self.assertEqual([part["page"] for part in sections[4]], [4])
        self.assertEqual([part["page"] for part in sections[5]], [4, 5])
        self.assertEqual([part["page"] for part in sections[7]], [6, 7])
        self.assertEqual([part["page"] for part in sections[9]], [7, 8])

    def test_invalid_argument_types_return_structured_errors(self):
        for arguments in [{"question": []}, {"question": "Horário", "topic": 123}]:
            with self.subTest(arguments=arguments):
                result = json.loads(search_store_policies(**arguments))
                self.assertEqual(result["status"], "invalid_arguments")
                self.assertIn("error", result)

    def test_defect_question_includes_warranty_section(self):
        result = json.loads(search_store_policies("Meu instrumento está com defeito"))
        self.assertEqual([section["chapter"] for section in result["sections"]], [4, 8])
        self.assertIn("90", result["sections"][1]["text"])

    def test_pdf_read_failure_is_reported_without_inventing_policy(self):
        with patch("zubumafu.policies._sections", side_effect=OSError("unavailable")):
            result = json.loads(search_store_policies("Quero devolver"))
        self.assertEqual(result["status"], "extraction_error")
        self.assertNotIn("sections", result)

    def test_returns_explains_online_cooling_off_and_missing_information(self):
        result = json.loads(search_store_policies("Comprei um violão e me arrependi, posso devolver?"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["topic"], "returns")
        self.assertEqual(result["sections"][0]["pages"], [4])
        self.assertIn("7 (sete) dias corridos", result["sections"][0]["text"])
        self.assertIn("Whether the purchase was online", result["information_needed_before_definitive_return_decision"][0])

    def test_hours_and_address_retrieve_correct_chapters(self):
        hours = json.loads(search_store_policies("Quais são os horários de funcionamento?"))
        self.assertEqual(hours["sections"][0]["chapter"], 2)
        self.assertIn("09:00 às 18:00", hours["sections"][0]["text"])
        address = json.loads(search_store_policies("Qual o endereço da loja?"))
        self.assertEqual(address["sections"][0]["chapter"], 1)
        self.assertIn("Rua 14 de Maio, 3200", address["sections"][0]["text"])
        self.assertEqual(address["ambiguities"], [])

    def test_payments_conflict_is_explicit(self):
        result = json.loads(search_store_policies("Posso pagar em 6x?"))
        self.assertEqual(result["sections"][0]["chapter"], 3)
        self.assertEqual(result["ambiguities"][0]["issue"], "installment_thresholds")

    def test_delivery_exactly_500_is_unresolved(self):
        result = json.loads(search_store_policies("Qual frete para pedido de R$ 500,00?"))
        self.assertEqual(result["sections"][0]["pages"], [4, 5])
        self.assertEqual(result["ambiguities"][0]["issue"], "exactly_500_brl")

    def test_whatsapp_conflict_is_explicit(self):
        result = json.loads(search_store_policies("Qual o WhatsApp da loja?"))
        self.assertEqual([item["chapter"] for item in result["sections"]], [1, 7])
        self.assertEqual(result["ambiguities"][0]["issue"], "contact_conflict")

    def test_unknown_question_does_not_guess_policy(self):
        result = json.loads(search_store_policies("Qual a cor favorita da banda?"))
        self.assertEqual(result["status"], "not_found")


if __name__ == "__main__":
    unittest.main()
