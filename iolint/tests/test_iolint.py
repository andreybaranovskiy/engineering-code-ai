"""python -m unittest discover -s tests"""
import io, json, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

from iolint import Config, Project, validate
from iolint import rules as R
from iolint.cli import main
from iolint.model import Cable, DataError, Instrument, IOPoint

PT = Instrument("100-PT-1001", "Separator pressure", "AI", 0.0, 10.0, "barg", "DCS", "BPCS", True, None, 2.0, 8.0, None)
IO = IOPoint("100-PT-1001", "DCS", "CAB-01", "AI-01", "AI", True, 1, 0.0, 10.0, "barg")
CB = Cable("C-1001", "100-PT-1001", 1, 1, "100-PT-1001", "JB-01", 40.0)


def proj(index=(PT,), io=(IO,), cables=(CB,), **cfg):
    return Project(list(index), list(io), list(cables), Config(**cfg))


class Rules(unittest.TestCase):
    def fires(self, rule, p, rid):
        self.assertEqual(rule(proj()), [], f"{rid} fired on clean data")
        self.assertIn(rid, {f.rule for f in rule(p)})

    def test_clean(self): self.assertEqual(validate(proj()), [])
    def test_r01(self): self.fires(R.r01_duplicate_tags, proj(index=(PT, PT)), "R01")
    def test_r02(self): self.fires(R.r02_tag_format, proj(index=(replace(PT, tag="PT1001"),)), "R02")
    def test_r03(self): self.fires(R.r03_orphan_io, proj(io=(IO, replace(IO, tag="100-PT-9999", channel=2))), "R03")
    def test_r04(self): self.fires(R.r04_unallocated_instrument, proj(io=()), "R04")
    def test_r05(self): self.fires(R.r05_range_mismatch, proj(io=(replace(IO, urv=16.0),)), "R05")
    def test_r06(self): self.fires(R.r06_units_mismatch, proj(io=(replace(IO, units="kPa"),)), "R06")
    def test_r07(self): self.fires(R.r07_alarm_outside_range, proj(index=(replace(PT, alarm_hh=12.0),)), "R07")
    def test_r08(self): self.fires(R.r08_alarm_order, proj(index=(replace(PT, alarm_l=9.0),)), "R08")
    def test_r09(self): self.fires(R.r09_signal_vs_card, proj(io=(replace(IO, card_type="DI"),)), "R09")
    def test_r10(self):
        o = replace(PT, tag="100-PT-1002")
        self.fires(R.r10_double_allocated_channel, proj(index=(PT, o), io=(IO, replace(IO, tag="100-PT-1002"))), "R10")
    def test_r11(self): self.fires(R.r11_spare_capacity, proj(channels_per_card=1), "R11")
    def test_r12(self): self.fires(R.r12_sif_on_bpcs, proj(index=(replace(PT, loop_class="SIF"),)), "R12")
    def test_r13(self): self.fires(R.r13_system_mismatch, proj(io=(replace(IO, system="SIS"),)), "R13")
    def test_r14(self): self.fires(R.r14_is_device_on_non_is_card, proj(io=(replace(IO, card_is=False),)), "R14")
    def test_r15(self): self.fires(R.r15_cable_checks, proj(cables=(replace(CB, pairs_used=2),)), "R15")
    def test_config_tag_pattern(self):
        self.assertEqual(R.r02_tag_format(proj(index=(replace(PT, tag="PT1001"),), tag_pattern=r"^PT\d+$")), [])
    def test_skip(self):
        self.assertEqual(validate(proj(index=(replace(PT, tag="PT1001"),), io=(replace(IO, tag="PT1001"),),
                                       cables=(replace(CB, tag="PT1001"),)), skip={"R02"}), [])


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, buf.getvalue()

    def test_example_and_check(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_cli("example", d)[0], 0)
            code, out = self.run_cli("check", d)
            self.assertEqual(code, 1)
            self.assertIn("12 errors, 1 warnings", out)
            code, out = self.run_cli("check", d, "--format", "json", "--fail-on", "never")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["errors"], 12)
            code, out = self.run_cli("loopsheets", d, "--out", str(Path(d) / "ls"))
            self.assertEqual(len(list((Path(d) / "ls").glob("*.md"))), 12)

    def test_bad_value_reports_location(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_cli("example", d)
            p = Path(d) / "io_list.csv"
            p.write_text(p.read_text().replace(",0,10,barg", ",zero,10,barg", 1))
            with self.assertRaises(DataError) as e:
                Project.load_folder(Path(d))
            self.assertIn("io_list.csv line 2", str(e.exception))


if __name__ == "__main__":
    unittest.main()
