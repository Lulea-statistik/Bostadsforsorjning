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


    def test_ckm_real_civilstand_total_label(self):
        # Exact code and description documented in failed GitHub run #6.
        metadata = {"code": "Civilstand", "values": ["SC", "OG", "G", "SK", "ÄNKL"],
                    "valueTexts": ["totalt, samtliga civilstånd", "ogifta",
                                   "gifta", "skilda", "änkor/änklingar"]}
        self.assertEqual(update_population.total_code(metadata), "SC")

    def test_total_label_must_be_unique(self):
        metadata = {"code": "Civilstand", "values": ["SC", "TOT"],
                    "valueTexts": ["totalt, samtliga civilstånd", "Totalt"]}
        with self.assertRaisesRegex(ValueError, "No unique published total"):
            update_population.total_code(metadata)

    def test_real_ckm_age_total_preferred_over_other_total_candidates(self):
        # SCB metadata code and label from failed GitHub Actions run #7.
        metadata = {"code": "Alder",
                    "values": ["0", "TotSA", "-4", "tot"],
                    "valueTexts": ["0 år", "totalt, samtliga åldrar",
                                   "0–4 år", "Totalt"]}
        self.assertEqual(update_population.total_code(metadata), "TotSA")

    def test_ckm_age_total_label_mismatch_is_rejected(self):
        metadata = {"code": "Alder", "values": ["TotSA"],
                    "valueTexts": ["5–9 år"]}
        with self.assertRaisesRegex(ValueError, "Unexpected label"):
            update_population.total_code(metadata)

    def test_ckm_required_aggregate_dimensions(self):
        # Synthetic example of mandatory CKM dimensions with published totals.
        self.metadata["variables"].append({
            "code": "Alder", "values": ["0", "tot"],
            "valueTexts": ["0 år", "Totalt"]})
        self.metadata["variables"][-2] = {
            "code": "Civilstand", "elimination": False,
            "values": ["OG", "G", "TOT"],
            "valueTexts": ["ogifta", "gifta", "Totalt"]}
        self.response["columns"] = [
            {"code": "Region", "type": "d"},
            {"code": "Civilstand", "type": "d"},
            {"code": "Alder", "type": "d"},
            {"code": "Tid", "type": "t"},
            {"code": "BE0101N1", "type": "c"}]
        self.response["data"] = [
            {"key": ["2580", "TOT", "tot", "1968"], "values": ["63000"]},
            {"key": ["2580", "TOT", "tot", "1969"], "values": ["63500"]}]
        def fake_request(url, payload=None):
            if payload is None:
                return self.metadata
            requested = {q["code"]: q["selection"]["values"] for q in payload["query"]}
            self.assertEqual(requested["Civilstand"], ["TOT"])
            self.assertEqual(requested["Alder"], ["tot"])
            return self.response
        with patch.object(update_population, "request", side_effect=fake_request):
            self.assertEqual(update_population.fetch_table("BefolkningCKM"), {1968: 63000, 1969: 63500})

    def test_ckm_without_published_total_fails_closed(self):
        self.metadata["variables"][-1] = {
            "code": "Civilstand", "elimination": False,
            "values": ["OG", "G"], "valueTexts": ["ogifta", "gifta"]}
        with patch.object(update_population, "request", return_value=self.metadata):
            with self.assertRaisesRegex(ValueError, "No unique published total"):
                update_population.fetch_table("BefolkningCKM")

    def test_ckm_rejects_unexpected_subgroup_result(self):
        self.metadata["variables"][-1] = {
            "code": "Civilstand", "elimination": False,
            "values": ["OG", "TOT"], "valueTexts": ["ogifta", "Totalt"]}
        self.response["columns"] = [
            {"code": "Region", "type": "d"},
            {"code": "Civilstand", "type": "d"},
            {"code": "Tid", "type": "t"},
            {"code": "BE0101N1", "type": "c"}]
        self.response["data"] = [
            {"key": ["2580", "OG", "1968"], "values": ["63000"]}]
        with patch.object(update_population, "request", side_effect=[self.metadata, self.response]):
            with self.assertRaisesRegex(ValueError, "Unexpected SCB dimensions"):
                update_population.fetch_table("BefolkningCKM")

if __name__ == "__main__":
    unittest.main()
