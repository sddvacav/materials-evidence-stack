#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
import unittest
from pathlib import Path

# This runner is executed explicitly after the package builder. It is not a
# repository-level pytest module because the generated output does not exist at collection time.
__test__ = False
ROOT_ARG = Path(".").resolve()

MANDATORY = [
    "00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv", "CONFLICT_LEDGER.csv",
    "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md", "PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json",
    "MANIFEST.json", "CHECKSUMS.sha256", "CTE_GND_INPUTS.csv",
    "DISLOCATION_DENSITY_CALIBRATION.csv", "DISLOCATION_CONTRIBUTIONS.csv",
    "GND_APPLICABILITY.csv", "OPENED_FILES.txt", "SOURCE_COVERAGE_MATRIX.csv",
    "SNAPSHOT_VALIDATION.json", "VALIDATION_REPORT.json", "RECOMPUTE_OUTPUT.txt",
    "RUN_LOG.txt", "README.md", "requirements.lock", "acceptance_commands.md"
]


class QM34OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = ROOT_ARG

    def read_csv(self, name: str) -> list[dict[str, str]]:
        with (self.root / name).open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def test_01_mandatory_files_exist(self) -> None:
        missing = [p for p in MANDATORY if not (self.root / p).is_file()]
        self.assertEqual(missing, [])

    def test_02_counts_and_status(self) -> None:
        pairs = self.read_csv("PAIR_MATCHES.csv")
        effects = self.read_csv("EFFECT_ESTIMATES.csv")
        self.assertEqual(len(pairs), 10)
        self.assertGreaterEqual(len(effects), 17)
        status = json.loads((self.root / "WINDOW_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(status["window_id"], "QM34")
        self.assertEqual(status["matched_pairs"], 10)
        self.assertEqual(status["plots_generated"], 4)
        self.assertEqual(status["status"], "CONTINUE_DATA_GAP")
        self.assertEqual(status["claim_level_max"], 2)

    def test_03_provenance_binding(self) -> None:
        rows = self.read_csv("EFFECT_ESTIMATES.csv")
        required = ["paper_uid", "sample_uid", "condition_uid", "source_hash", "source_hash_kind", "evidence_level"]
        for i, row in enumerate(rows, 1):
            for key in required:
                self.assertTrue(row.get(key), f"row {i} missing {key}")

    def test_04_plot_triplets_and_data(self) -> None:
        stems = [
            "QM34_F1_rho_delta_sigma_distribution",
            "QM34_F2_cte_dt_sensitivity_surface",
            "QM34_F3_measurement_proxy_calibration",
            "QM34_F4_dislocation_contribution_share_forest",
        ]
        for stem in stems:
            for ext in ("png", "svg", "pdf"):
                p = self.root / "figures" / f"{stem}.{ext}"
                self.assertTrue(p.is_file() and p.stat().st_size > 1000, str(p))
        specs = json.loads((self.root / "PLOT_SPECS.json").read_text(encoding="utf-8"))
        self.assertEqual(len(specs["plots"]), 4)
        self.assertEqual(len(list((self.root / "figure_data").glob("*.csv"))), 4)

    def test_05_checksums(self) -> None:
        for line in (self.root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, rel = line.split("  ", 1)
            p = self.root / rel
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(actual, expected, rel)

    def test_06_formula_recompute_passed(self) -> None:
        result = json.loads((self.root / "RECOMPUTE_OUTPUT.txt").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["formula_rows_recomputed"], 3)
        self.assertEqual(result["matched_pair_rows"], 10)
        self.assertLess(result["max_relative_error"], 1.0e-9)

    def test_07_claim_firewall(self) -> None:
        verdict = (self.root / "00_EXECUTIVE_VERDICT.md").read_text(encoding="utf-8")
        self.assertIn("NOT_IDENTIFIABLE", verdict)
        self.assertIn("model estimate", verdict.lower())
        self.assertIn("No Gold promotion", verdict)
        status = json.loads((self.root / "WINDOW_STATUS.json").read_text(encoding="utf-8"))
        self.assertFalse(status.get("production_model_registered", True))
        self.assertFalse(status.get("gold_promoted", True))
        self.assertFalse(status.get("active_titmc_modified", True))

    def test_08_manifest_and_no_nested_zip(self) -> None:
        manifest = json.loads((self.root / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["window_id"], "QM34")
        self.assertGreaterEqual(manifest["file_count"], 45)
        nested = [p for p in self.root.rglob("*.zip")]
        self.assertEqual(nested, [])


if __name__ == "__main__":
    ROOT_ARG = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    sys.argv[:] = [sys.argv[0]]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(QM34OutputTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
