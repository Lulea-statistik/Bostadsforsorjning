"""Synthetic regression fixtures for quarterly SCB housing construction."""
import unittest
from scripts import update_housing_construction as h

class HousingTests(unittest.TestCase):
    def setUp(self):
        self.meta = {"variables": [
            {"code":"Region","values":["2580"],"valueTexts":["Luleå"]},
            {"code":"Hustyp","values":["TOT","SM"],"valueTexts":["Totalt","Småhus"]},
            {"code":"Tid","values":["2025K1","2025K2","2025K3","2025K4","2026K1"],"valueTexts":["2025K1","2025K2","2025K3","2025K4","2026K1"]},
            {"code":"ContentsCode","values":["S","F"],"valueTexts":["Påbörjade lägenheter i nybyggda hus","Färdigställda lägenheter i nybyggda hus"]},
        ]}
        self.result = {"columns":[
            {"code":"Region","type":"d"},{"code":"Hustyp","type":"d"},
            {"code":"Tid","type":"t"},{"code":"S","type":"c"},{"code":"F","type":"c"}],
            "data":[{"key":["2580","TOT",f"2025K{i}"],"values":[str(i*10),str(i*20)]} for i in range(1,5)] +
                   [{"key":["2580","TOT","2026K1"],"values":["50","30"]}]}

    def test_complete_year_and_partial_2026(self):
        by_quarter = h.convert(self.meta,self.result)
        rows = h.aggregate(by_quarter)
        self.assertEqual(rows,[{"year":2025,"started":100,"completed":200,"partial":False,"through_quarter":4},
                               {"year":2026,"started":50,"completed":30,"partial":True,"through_quarter":1}])

    def test_2026_values_remain_partial_not_annualized(self):
        rows=h.aggregate(h.convert(self.meta,self.result))
        self.assertEqual(rows[-1]["started"],50)
        self.assertTrue(rows[-1]["partial"])

    def test_duplicate_quarter_fails(self):
        self.result["data"].append(self.result["data"][0])
        with self.assertRaisesRegex(ValueError,"Duplicate quarter"):
            h.convert(self.meta,self.result)

    def test_wrong_region_fails(self):
        self.result["data"][0]["key"][0]="2582"
        with self.assertRaisesRegex(ValueError,"municipality"):
            h.convert(self.meta,self.result)

    def test_missing_historic_quarter_fails(self):
        del self.result["data"][2]
        with self.assertRaisesRegex(ValueError,"Missing quarter"):
            h.aggregate(h.convert(self.meta,self.result))

    def test_missing_measure_is_not_zero(self):
        self.result["data"][-1]["values"]=["50",".."]
        with self.assertRaisesRegex(ValueError,"Missing/suppressed"):
            h.convert(self.meta,self.result)

    def test_measure_order_from_columns(self):
        self.result["columns"][-2],self.result["columns"][-1]=self.result["columns"][-1],self.result["columns"][-2]
        for row in self.result["data"]:
            row["values"].reverse()
        values=h.aggregate(h.convert(self.meta,self.result))
        self.assertEqual(values[0]["started"],100)

    def test_total_hustyp_is_not_summed_from_subgroups(self):
        self.assertEqual(h.select_total(self.meta["variables"][1]),"TOT")
        self.meta["variables"][1]["valueTexts"]=["Småhus","Flerbostadshus"]
        with self.assertRaisesRegex(ValueError,"No unique"):
            h.select_total(self.meta["variables"][1])

if __name__=="__main__":
    unittest.main()
