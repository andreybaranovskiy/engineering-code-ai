"""One test per rule: a clean record passes, a broken one is caught.

    python -m unittest -v
"""
from __future__ import annotations

import unittest
from dataclasses import replace

import rules
from model import Cable, Instrument, IOPoint, Project

PT = Instrument("100-PT-1001", "Separator pressure", "AI", 0.0, 10.0, "barg", "DCS", "BPCS",
                True, None, 2.0, 8.0, None)
PT_IO = IOPoint("100-PT-1001", "DCS", "CAB-01", "AI-01", "AI", True, 1, 0.0, 10.0, "barg")
PT_CABLE = Cable("C-1001", "100-PT-1001", 1, 1, "100-PT-1001", "JB-01", 40.0)


def project(index=(PT,), io=(PT_IO,), cables=(PT_CABLE,), per_card=16) -> Project:
    return Project(list(index), list(io), list(cables), per_card)


def ids(findings):
    return {f.rule for f in findings}


class CleanProject(unittest.TestCase):
    def test_clean_record_has_no_findings(self):
        self.assertEqual(rules.validate(project()), [])


class EachRule(unittest.TestCase):
    def check(self, rule, p, rule_id):
        self.assertEqual(rule(project()), [], f"{rule_id} fired on clean data")
        self.assertIn(rule_id, ids(rule(p)))

    def test_r01(self):
        self.check(rules.r01_duplicate_tags, project(index=(PT, PT)), "R01")

    def test_r02(self):
        self.check(rules.r02_tag_format, project(index=(replace(PT, tag="PT1001"),)), "R02")

    def test_r03(self):
        self.check(rules.r03_orphan_io, project(io=(PT_IO, replace(PT_IO, tag="100-PT-9999", channel=2))), "R03")

    def test_r04(self):
        self.check(rules.r04_unallocated_instrument, project(io=()), "R04")

    def test_r05(self):
        self.check(rules.r05_range_mismatch, project(io=(replace(PT_IO, urv=16.0),)), "R05")

    def test_r06(self):
        self.check(rules.r06_units_mismatch, project(io=(replace(PT_IO, units="kPa"),)), "R06")

    def test_r07(self):
        self.check(rules.r07_alarm_outside_range, project(index=(replace(PT, alarm_hh=12.0),)), "R07")

    def test_r08(self):
        self.check(rules.r08_alarm_order, project(index=(replace(PT, alarm_l=9.0),)), "R08")

    def test_r09(self):
        self.check(rules.r09_signal_vs_card, project(io=(replace(PT_IO, card_type="DI"),)), "R09")

    def test_r10(self):
        other = replace(PT, tag="100-PT-1002")
        self.check(rules.r10_double_allocated_channel,
                   project(index=(PT, other), io=(PT_IO, replace(PT_IO, tag="100-PT-1002"))), "R10")

    def test_r11(self):
        self.check(rules.r11_spare_capacity, project(per_card=1), "R11")

    def test_r12(self):
        self.check(rules.r12_sif_on_bpcs, project(index=(replace(PT, loop_class="SIF"),)), "R12")

    def test_r13(self):
        self.check(rules.r13_system_mismatch, project(io=(replace(PT_IO, system="SIS"),)), "R13")

    def test_r14(self):
        self.check(rules.r14_is_device_on_non_is_card, project(io=(replace(PT_IO, card_is=False),)), "R14")

    def test_r15(self):
        self.check(rules.r15_cable_checks, project(cables=(replace(PT_CABLE, pairs_used=2),)), "R15")


if __name__ == "__main__":
    unittest.main()
