import json
import unittest

from zubumafu.catalog import search_products


class CatalogTests(unittest.TestCase):
    def test_invalid_argument_types_return_structured_errors(self):
        for arguments in [
            {"category": 123},
            {"query": ["Fender"]},
            {"available_only": "false"},
            {"max_price_brl": True},
        ]:
            with self.subTest(arguments=arguments):
                self.assertIn("error", json.loads(search_products(**arguments)))

    def test_search_includes_technical_specifications(self):
        result = json.loads(search_products(query="Basswood", available_only=False))
        self.assertGreater(result["total_matches"], 0)
        self.assertTrue(all(item["specs"].get("body") == "Basswood" for item in result["products"]))

    def test_available_guitars_below_budget(self):
        result = json.loads(search_products(category="guitarra", max_price_brl=8000))
        self.assertGreater(result["total_matches"], 0)
        self.assertTrue(result["products"])
        for item in result["products"]:
            self.assertEqual(item["category"], "Guitarras")
            self.assertLessEqual(float(item["price_brl"]), 8000)
            self.assertGreater(item["stock_quantity"], 0)
            self.assertEqual(item["status"], "active")

    def test_violao_category_singular_works(self):
        result = json.loads(search_products(category="violão", max_price_brl=1000))
        self.assertGreater(result["total_matches"], 0)
        self.assertEqual({item["category"] for item in result["products"]}, {"Violões"})
        self.assertEqual(result["products"][0]["name"], "Tagima Memphis AC-39 Nylon Natural")
        self.assertEqual(result["products"][0]["price_display_brl"], "R$ 429,90")

    def test_unknown_model_does_not_generate_fake_item(self):
        result = json.loads(search_products(query="inexistente-xyz-000"))
        self.assertEqual(result["total_matches"], 0)
        self.assertEqual(result["products"], [])

    def test_invalid_budget_rejected(self):
        self.assertIn("error", json.loads(search_products(max_price_brl=-100)))
        self.assertIn("error", json.loads(search_products(max_price_brl=float("nan"))))


if __name__ == "__main__":
    unittest.main()
