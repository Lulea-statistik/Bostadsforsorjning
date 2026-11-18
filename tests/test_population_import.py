"""Regression tests for SCB PxWeb JSON dimension and measure handling."""
import unittest
from unittest.mock import patch
from scripts import update_population

class PxWebDimensionTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {"variables": [
            {"code": "Region", "values": ["2580"], "valueTexts": ["Luleå"]},
            {"code": "Tid", "values": ["1968", "1969"], "valueTexts": ["1968", "1969"]},
            {"code": "ContentsCode", "values": ["BE0101N1"], "valueTexts": ["Folkmängd"]},
            {"code": "Civilstand", "elimination": True, "values": ["OG", "G"], "valueTexts": ["ogifta", "gifta"]},
        ]}
        self.response = {"columns": [
            {"code": "Region", "type": "d"},
            {"code": "Tid", "type": "t"},
            {"code": "BE0101N1", "type": "c"}],
            "data": [
                {"key": ["2580", "1968"], "values": ["63000"]},
                {"key": ["2580", "1969"], "values": ["63500"]}]}

    def test_measure_column_not_counted_as_key(self):
        with patch.object(update_population, "request", side_effect=[self.metadata, self.response]):
            self.assertEqual(update_population.fetch_table("BefolkningNy"), {1968: 63000, 1969: 63500})

    def test_dimensions_can_be_reordered(self):
        self.response["columns"][0], self.response["columns"][1] = self.response["columns"][1], self.response["columns"][0]
        self.response["data"] = [
            {"key": ["1968", "2580"], "values": ["63000"]},
            {"key": ["1969", "2580"], "values": ["63500"]}]
        with patch.object(update_population, "request", side_effect=[self.metadata, self.response]):
            self.assertEqual(update_population.fetch_table("BefolkningNy"), {1968: 63000, 1969: 63500})

    def test_wrong_municipality_fails_closed(self):
        self.response["data"][0]["key"][0] = "2582"
        with patch.object(update_population, "request", side_effect=[self.metadata, self.response]):
            with self.assertRaisesRegex(ValueError, "Unexpected SCB dimensions"):
                update_population.fetch_table("BefolkningNy")

if __name__ == "__main__":
    unittest.main()
