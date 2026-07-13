from __future__ import annotations

import csv
import hashlib
import json
import py_compile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
BUILD = BASE / "build"
OUT = BUILD / "FINAL_QM21"
ZIP = BUILD / "FINAL_QM21.zip"

REQUIRED = {
    "00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv", "CONFLICT_LEDGER.csv",
    "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md", "PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json",
    "MATRIX_CATE.csv", "GRADE_TRANSFER_MATRIX.csv", "BASELINE_MODERATION.csv",
    "MATRIX_OVERLAP.csv", "MANIFEST.json", "CHECKSUMS.sha256",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class QM21ContractTests(unittest.TestCase):
    def test_01_required_files_exist(self) -> None:
        self.assertTrue(OUT.is_dir())
        missing = sorted(name for name in REQUIRED if not (OUT / name).is_file())
        self.assertEqual(missing, [])

    def test_02_source_ledger_has_terminal_states(self) -> None:
        d = pd.read_csv(OUT / "INPUT_LEDGER.csv")
        self.assertGreaterEqual(len(d), 27)
        self.assertNotIn("PENDING", set(d["terminal_use_status"].astype(str)))
        allowed = {"USED_DIRECTLY", "USED_AS_REFERENCE", "SUPERSEDED_BY_HASH", "OUT_OF_SCOPE", "BLOCKED_CORRUPT", "NOT_RELEVANT_TO_WINDOW"}
        self.assertTrue(set(d["terminal_use_status"]).issubset(allowed))

    def test_03_effects_are_bound_and_atomic(self) -> None:
        e = pd.read_csv(OUT / "EFFECT_ESTIMATES.csv")
        a = pd.read_csv(OUT / "ATOMIC_RECORDS.csv")
        self.assertEqual(len(a), 2 * len(e))
        for col in ["snapshot_id", "paper_uid", "sample_uid_control", "sample_uid_treated", "condition_uid", "effect_uid", "source_hash"]:
            self.assertTrue(e[col].astype(str).str.len().gt(0).all(), col)
        self.assertEqual(e["matrix_family"].nunique(), 5)

    def test_04_cate_claim_ceiling(self) -> None:
        c = pd.read_csv(OUT / "MATRIX_CATE.csv")
        self.assertGreater(len(c), 0)
        self.assertTrue(c["estimand"].str.contains("CATE").all())
        self.assertTrue(c["identifiability"].str.contains("NOT_IDENTIFIABLE|DESCRIPTIVE", regex=True).all())
        self.assertLessEqual(c["claim_level"].max(), 2)

    def test_05_cross_family_transfer_is_not_accepted(self) -> None:
        t = pd.read_csv(OUT / "GRADE_TRANSFER_MATRIX.csv")
        cross = t[t["source_family"] != t["target_family"]]
        self.assertGreater(len(cross), 0)
        self.assertFalse(cross["accepted_transfer"].astype(bool).any())
        self.assertTrue(cross["validation_status"].eq("EXTRAPOLATION_ONLY").all())

    def test_06_overlap_map_complete(self) -> None:
        o = pd.read_csv(OUT / "MATRIX_OVERLAP.csv")
        families = sorted(set(o["source_family"]) | set(o["target_family"]))
        self.assertEqual(len(families), 5)
        self.assertEqual(len(o), 25)
        diag = o[o["source_family"] == o["target_family"]]
        self.assertTrue((diag["gower_distance"].abs() < 1e-12).all())

    def test_07_plot_bundle_complete_and_code_compiles(self) -> None:
        stems = ["matrix_cate_caterpillar", "baseline_strength_gain", "transfer_error_matrix", "overlap_ad_map"]
        for stem in stems:
            self.assertTrue((OUT / "figure_data" / f"{stem}.csv").is_file())
            for ext in ["svg", "pdf", "png"]:
                p = OUT / "figures" / f"{stem}.{ext}"
                self.assertTrue(p.is_file())
                self.assertGreater(p.stat().st_size, 100)
        for p in sorted((OUT / "plot_code").glob("*.py")):
            py_compile.compile(str(p), doraise=True)
        self.assertEqual(len(list((OUT / "plot_code").glob("*.py"))), 4)

    def test_08_checksums_and_manifest_cover_outputs(self) -> None:
        manifest = json.loads((OUT / "MANIFEST.json").read_text(encoding="utf-8"))
        listed = {x["path"]: x for x in manifest["files"]}
        for rel, item in listed.items():
            p = OUT / rel
            self.assertTrue(p.is_file(), rel)
            self.assertEqual(sha256(p), item["sha256"], rel)
        checksum_lines = (OUT / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
        for line in checksum_lines:
            digest, rel = line.split("  ", 1)
            self.assertEqual(sha256(OUT / rel), digest, rel)

    def test_09_zip_crc_flatness_and_external_hash(self) -> None:
        self.assertTrue(ZIP.is_file())
        with zipfile.ZipFile(ZIP) as zf:
            self.assertIsNone(zf.testzip())
            names = zf.namelist()
            self.assertFalse(any(name.lower().endswith(".zip") for name in names))
            self.assertTrue(REQUIRED.issubset(set(names)))
        external = (BUILD / "FINAL_QM21.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(sha256(ZIP), external)

    def test_10_status_forbids_premature_promotion(self) -> None:
        s = json.loads((OUT / "WINDOW_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(s["window_id"], "QM21")
        self.assertEqual(s["status"], "CONTINUE_DATA_GAP")
        self.assertFalse(s["production_model_registered"])
        self.assertFalse(s["gold_promoted"])
        self.assertEqual(s["plots_generated"], 4)
        self.assertEqual(s["atomic_rows"], 2 * s["effect_estimates"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
