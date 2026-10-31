"""Tests for the deterministic checks: python -m unittest -v"""
import unittest

from checks import check_datasheet, compare, number_forms, unit

INDEX = {"100-PT-1001": {"tag": "100-PT-1001", "lrv": "0", "urv": "10", "units": "barg"},
         "100-PDT-1007": {"tag": "100-PDT-1007", "lrv": "0", "urv": "2", "units": "bar"}}
DOC = ("Tag 100-PT-1001  Calibrated range 0 to 10 barg  Sensor limits -1 ... 40 bar  Output 4-20 mA HART "
       'Ex ia IIC T4 Ga  1/2" NPT F  SS316L')


def rec(**kw):
    base = dict(tag="100-PT-1001", lrv=0, urv=10, units="barg", output_signal="4-20 mA HART",
                ex_protection="Ex ia IIC T4 Ga", process_connection='1/2" NPT F', wetted_material="SS316L")
    ev = dict(tag="100-PT-1001", lrv="0 to 10 barg", urv="0 to 10 barg", units="0 to 10 barg",
              output_signal="4-20 mA HART", ex_protection="Ex ia IIC T4 Ga", process_connection='1/2" NPT F',
              wetted_material="SS316L")
    base.update(kw)
    r = {k: {"value": v, "evidence": ev.get(k, "")} for k, v in base.items()}
    r["uncertain"] = []
    return r


class Checks(unittest.TestCase):
    def test_clean_record_passes(self):
        self.assertEqual(check_datasheet(rec(), DOC, INDEX), {})

    def test_sensor_limit_instead_of_range(self):
        r = rec(urv=40); r["urv"]["evidence"] = "-1 ... 40 bar"
        self.assertIn("X2", check_datasheet(r, DOC, INDEX)["urv"][0])

    def test_value_not_in_evidence(self):
        r = rec(urv=16)
        self.assertTrue(any(w.startswith("E1") for w in check_datasheet(r, DOC, INDEX)["urv"]))

    def test_value_not_in_document(self):
        r = rec(output_signal="4-20 mA HART, SIL 3"); r["output_signal"]["evidence"] = "4-20 mA HART, SIL 3"
        self.assertIn("E2 value not found in document", check_datasheet(r, DOC, INDEX)["output_signal"])

    def test_unit_conversion_kpa_to_bar(self):
        r = rec(tag="100-PDT-1007", urv=200, units="kPa")
        r["urv"]["evidence"] = r["units"]["evidence"] = "0 ... 200 kPa"; r["tag"]["evidence"] = "100-PDT-1007"
        doc = '100-PDT-1007 0 ... 200 kPa 4-20 mA HART Ex ia IIC T4 Ga 1/2" NPT F SS316L'
        self.assertEqual(check_datasheet(r, doc, INDEX), {})

    def test_unknown_tag_flags_record(self):
        r = rec(tag="100-PT-1013"); r["tag"]["evidence"] = "100-PT-1013"
        self.assertIn("X1 tag not in instrument index", check_datasheet(r, "", INDEX)["tag"])

    def test_missing_value_goes_to_a_person(self):
        r = rec(ex_protection=None)
        self.assertIn("N1 required value missing", check_datasheet(r, DOC, INDEX)["ex_protection"])

    def test_number_printing(self):
        self.assertIn("50 000", number_forms(50000))
        self.assertIn("16,0", number_forms(16))

    def test_units(self):
        self.assertEqual(unit("bar g"), "barg")
        self.assertEqual(unit("Sm³/h"), "Sm3/h")

    def test_compare(self):
        self.assertEqual(compare(rec(), rec(urv=12)), ["urv"])
        self.assertEqual(compare(rec(), rec(output_signal="4–20mA HART")), [])


if __name__ == "__main__":
    unittest.main()
