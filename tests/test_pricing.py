import json
import unittest
from decimal import Decimal

from zubumafu.catalog import search_products
from zubumafu.pricing import calculate_price, get_product_pricing


def promo(discount: str, active: str = "1", identifier: str = "test") -> dict[str, str]:
    return {
        "promotion_id": identifier,
        "product_id": "synthetic",
        "discount_percent": discount,
        "description": "Test offer",
        "is_active": active,
    }


class PricingTests(unittest.TestCase):
    def test_1100_with_10_percent_discount_is_990(self):
        result = calculate_price("1100.00", [promo("10")])
        self.assertEqual(result["list_price_brl"], "1100.00")
        self.assertEqual(result["discount_amount_brl"], "110.00")
        self.assertEqual(result["final_price_brl"], "990.00")

    def test_real_active_promotion_is_not_cumulative_with_pix(self):
        usual = json.loads(get_product_pricing(product_id=127))
        pix = json.loads(get_product_pricing(product_id=127, payment_method="pix"))
        self.assertEqual(usual["pricing"]["list_price_brl"], "359.00")
        self.assertEqual(usual["pricing"]["active_promotion"]["discount_percent"], "10")
        self.assertEqual(usual["pricing"]["final_price_brl"], "323.10")
        self.assertEqual(pix["pricing"]["final_price_brl"], "323.10")
        self.assertTrue(pix["pricing"]["pix_non_cumulative"])
        self.assertFalse(pix["pricing"]["pix_discount_applied"])
        self.assertIsNone(pix["pricing"]["promotion_validity_dates"])

    def test_inactive_promotion_is_ignored(self):
        result = calculate_price("1100", [promo("30", active="0")], "standard")
        self.assertEqual(result["discount_type"], "none")
        self.assertEqual(result["final_price_brl"], "1100.00")

    def test_pix_applies_to_nonpromotional_product(self):
        result = json.loads(get_product_pricing(product_id=145, payment_method="pix"))
        self.assertEqual(result["pricing"]["list_price_brl"], "12500.00")
        self.assertEqual(result["pricing"]["final_price_brl"], "11875.00")
        self.assertTrue(result["pricing"]["pix_discount_applied"])

    def test_budget_uses_discounted_price_even_when_table_price_exceeds_budget(self):
        result = json.loads(search_products(query="Kalani KAL-700T", max_price_brl=340))
        self.assertEqual(result["total_matches"], 1)
        product = result["products"][0]
        self.assertEqual(product["price_brl"], "359.00")
        self.assertEqual(product["final_price_brl"], "323.10")

    def test_rounding_half_up_at_half_cent_and_discount_reconciliation(self):
        result = calculate_price(Decimal("1.10"), [], "pix")
        self.assertEqual(result["final_price_brl"], "1.05")
        self.assertEqual(result["discount_amount_brl"], "0.05")

    def test_product_not_found_and_no_promotion(self):
        missing = json.loads(get_product_pricing(product_id=999999))
        self.assertEqual(missing["status"], "not_found")
        no_promo = json.loads(get_product_pricing(product_id=145))
        self.assertIsNone(no_promo["pricing"]["active_promotion"])
        self.assertEqual(no_promo["pricing"]["discount_amount_brl"], "0.00")

    def test_multiple_active_promotions_are_not_silently_stacked(self):
        result = calculate_price("100.00", [promo("10", identifier="a"), promo("15", identifier="b")])
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["reason"], "multiple_active_promotions")

    def test_bad_input_and_invalid_payment_method(self):
        self.assertEqual(calculate_price("NaN", [])["status"], "error")
        self.assertEqual(calculate_price("100", [], "unknown")["status"], "error")

    def test_malformed_tool_arguments_are_rejected_without_coercing_ids(self):
        for arguments in [{"product_id": True}, {"product_id": 127.9},
                          {"product_id": "127.9"}, {"product_id": -1},
                          {"product_name": []}, {"payment_method": None}]:
            with self.subTest(arguments=arguments):
                self.assertEqual(json.loads(get_product_pricing(**arguments))["status"], "error")
        for method in [None, [], True]:
            self.assertEqual(calculate_price("100", [], method)["status"], "error")
            self.assertIn("error", json.loads(search_products(payment_method=method)))

    def test_ambiguous_or_missing_product_does_not_quote_an_arbitrary_price(self):
        for arguments, status in [({}, "missing_product"), ({"product_name": "Yamaha"}, "ambiguous_product")]:
            result = json.loads(get_product_pricing(**arguments))
            self.assertEqual(result["status"], status)
            self.assertNotIn("pricing", result)

    def test_invalid_promotion_percent_does_not_produce_price(self):
        for percent in ["-1", "101", "NaN", "invalid"]:
            result = calculate_price("100", [promo(percent)])
            self.assertEqual(result["status"], "error")
            self.assertNotIn("final_price_brl", result)
        self.assertEqual(calculate_price("100", [{"is_active": "1"}])["status"], "error")

    def test_pix_budget_includes_only_eligible_discounted_products(self):
        usual = json.loads(search_products(query="Fender Stratocaster American Pro II", max_price_brl=12000))
        pix = json.loads(search_products(query="Fender Stratocaster American Pro II", max_price_brl=12000, payment_method="pix"))
        self.assertEqual(usual["total_matches"], 0)
        self.assertEqual(pix["total_matches"], 1)
        self.assertEqual(pix["products"][0]["final_price_brl"], "11875.00")
        self.assertEqual(pix["filters"]["budget_applies_to"], "final_price_brl")

    def test_real_ohana_offer_and_brazilian_currency_display(self):
        result = json.loads(get_product_pricing(product_name="Ohana CK-20 Concert"))
        price = result["pricing"]
        self.assertEqual(price["list_price_brl"], "549.00")
        self.assertEqual(price["discount_percent"], "20")
        self.assertEqual(price["final_price_brl"], "439.20")
        self.assertEqual(price["final_price_display_brl"], "R$ 439,20")


if __name__ == "__main__":
    unittest.main()
