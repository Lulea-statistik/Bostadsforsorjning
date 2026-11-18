"""Synthetic regression tests for SCB rent extraction."""
import unittest
from scripts import update_rent as rent

class RentTests(unittest.TestCase):
    def setUp(self):
        self.meta={"variables":[
            {"code":"Region","values":["2580"],"valueTexts":["Luleå"]},
            {"code":"Hyresuppg","values":["Ah_kvm","Mh_kvm"],"valueTexts":["Årshyra per kvm","Ny månadshyra per kvm"]},
            {"code":"ContentsCode","values":["000000J4","000000J3","000000RZ","000000MQ"],
             "valueTexts":["Medianhyra i hyreslägenhet","± Felmarginal, medianhyra","Medelhyra i hyreslägenhet","± Felmarginal, medelhyra"]},
            {"code":"Tid","values":["2024","2025"],"valueTexts":["2024","2025"]}]}
        self.result={"columns":[{"code":"Region","type":"d"},{"code":"Hyresuppg","type":"d"},{"code":"Tid","type":"t"},
                                {"code":"000000J4","type":"c"},{"code":"000000J3","type":"c"},
                                {"code":"000000RZ","type":"c"},{"code":"000000MQ","type":"c"}],
                     "data":[{"key":["2580",unit,year],"values":[str(med),"12",str(mean),"14"]}
                             for year,med,mean in [("2024",1200,1230),("2025",1260,1290)]
                             for unit in ["Ah_kvm","Mh_kvm"]]}
    def test_means_medians_and_units(self):
        rows=rent.convert(self.meta,self.result)
        self.assertEqual(rows[1]["annual"]["mean"],1290)
        self.assertEqual(rows[1]["annual"]["median"],1260)
        self.assertEqual(rows[1]["annual"]["mean_margin"],14)
        self.assertEqual(rows[1]["new_monthly"]["median_margin"],12)
    def test_wrong_municipality(self):
        self.result["data"][0]["key"][0]="2582"
        with self.assertRaisesRegex(ValueError,"municipality"):
            rent.convert(self.meta,self.result)
    def test_missing_cell_preserved(self):
        self.result["data"][0]["values"][2]=".."
        self.assertIsNone(rent.convert(self.meta,self.result)[0]["annual"]["mean"])
    def test_duplicate_row_rejected(self):
        self.result["data"].append(self.result["data"][0])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            rent.convert(self.meta,self.result)
    def test_missing_unit_rejected(self):
        del self.result["data"][0]
        with self.assertRaisesRegex(ValueError,"Missing annual"):
            rent.convert(self.meta,self.result)
    def test_measure_columns_can_reorder(self):
        self.result["columns"][-1],self.result["columns"][-2]=self.result["columns"][-2],self.result["columns"][-1]
        for row in self.result["data"]:
            row["values"][-1],row["values"][-2]=row["values"][-2],row["values"][-1]
        self.assertEqual(rent.convert(self.meta,self.result)[1]["annual"]["mean"],1290)

if __name__=="__main__":
    unittest.main()
