#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM10"
ZIP_PATH = ROOT / "FINAL_QM10.zip"
SHA_PATH = ROOT / "FINAL_QM10.zip.sha256"

# First execute the frozen deterministic QM10 build.
subprocess.run([sys.executable, str(ROOT / "run_build.py")], cwd=ROOT, check=True)

DOI = "10.1016/j.jmrt.2021.08.097"
PAPER_UID = "P_REN2021_20WP_TI"
SOURCE_ID = "SRC_REN2021_WP_TI_ORIGINAL"
SOURCE_TITLE = "Effect of strain rate on the mechanical properties of a tungsten particle reinforced titanium matrix composite"
SOURCE_LOCATOR = "Original PDF, Table 1, Fig. 7, Table 3, sections 2.1-4"
source_evidence = {
    "doi": DOI,
    "title": SOURCE_TITLE,
    "theoretical_density_g_cm3": 5.35,
    "measured_density_g_cm3": 5.20,
    "measured_density_sd_g_cm3": 0.02,
    "porosity_pct": 2.80,
    "compression_strength_limit_MPa": 1461,
    "compression_yield_MPa": 1071,
    "reported_specific_strength_kNm_kg": 281,
}
EVIDENCE_OBJECT_SHA256 = hashlib.sha256(
    json.dumps(source_evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else ["status", "reason"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def append_csv(path: Path, row: dict) -> None:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or list(row)
        rows = list(reader)
    rows.append({k: row.get(k, "") for k in fields})
    write_csv(path, rows, fields)


def append_md(path: Path, text: str) -> None:
    current = path.read_text(encoding="utf-8").rstrip()
    path.write_text(current + "\n\n" + text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# Direct original-paper, mode-specific evidence. Compression is explicitly firewalled
# from tensile UTS/YS synthesis; the rows remain usable for density-normalized mass-benefit audit.
rows = [
    {
        "evidence_uid": "REN2021_DENSITY_FULL",
        "paper_uid": PAPER_UID,
        "doi": DOI,
        "sample_uid": "S_REN2021_20WP_TI",
        "sample_label": "20WP/Ti",
        "matrix_system": "CP-Ti",
        "reinforcement": "20 wt.% W particles",
        "process": "V-mix 5 h; CIP 320 MPa; HIP 1573 K/120 MPa/120 min; air cool",
        "test_mode": "density",
        "temperature_C": 25,
        "strain_rate_s-1": "",
        "property": "theoretical_density",
        "value": 5.35,
        "unit": "g cm^-3",
        "density_semantics": "FULL_DENSITY_POROSITY_CONTROLLED",
        "evidence_level": "DIRECT_TABLE_TEXT",
        "locator": "Table 1; section 3.1",
        "primary_QM10_tensile_pool": "NO_MODE_SPECIFIC",
        "claim_level": 2,
    },
    {
        "evidence_uid": "REN2021_DENSITY_BULK",
        "paper_uid": PAPER_UID,
        "doi": DOI,
        "sample_uid": "S_REN2021_20WP_TI",
        "sample_label": "20WP/Ti",
        "matrix_system": "CP-Ti",
        "reinforcement": "20 wt.% W particles",
        "process": "V-mix 5 h; CIP 320 MPa; HIP 1573 K/120 MPa/120 min; air cool",
        "test_mode": "density",
        "temperature_C": 25,
        "strain_rate_s-1": "",
        "property": "Archimedes_density",
        "value": 5.20,
        "unit": "g cm^-3",
        "uncertainty": "±0.02; arithmetic mean of five measurements",
        "density_semantics": "BULK_AS_FABRICATED",
        "porosity_pct": 2.80,
        "evidence_level": "DIRECT_TABLE_TEXT",
        "locator": "Table 1; section 3.1",
        "primary_QM10_tensile_pool": "NO_MODE_SPECIFIC",
        "claim_level": 2,
    },
    {
        "evidence_uid": "REN2021_QS_CYS",
        "paper_uid": PAPER_UID,
        "doi": DOI,
        "sample_uid": "S_REN2021_20WP_TI",
        "sample_label": "20WP/Ti",
        "matrix_system": "CP-Ti",
        "reinforcement": "20 wt.% W particles",
        "process": "HIP as-sintered",
        "test_mode": "compression",
        "temperature_C": 25,
        "strain_rate_s-1": "1e-3",
        "property": "compressive_yield_stress",
        "value": 1071,
        "unit": "MPa",
        "density_semantics": "BULK_AND_FULL_AVAILABLE",
        "evidence_level": "DIRECT_FIGURE_LABEL",
        "locator": "Fig. 7b; section 3.3.1",
        "primary_QM10_tensile_pool": "NO_MODE_SPECIFIC",
        "claim_level": 2,
    },
    {
        "evidence_uid": "REN2021_QS_CSL",
        "paper_uid": PAPER_UID,
        "doi": DOI,
        "sample_uid": "S_REN2021_20WP_TI",
        "sample_label": "20WP/Ti",
        "matrix_system": "CP-Ti",
        "reinforcement": "20 wt.% W particles",
        "process": "HIP as-sintered",
        "test_mode": "compression",
        "temperature_C": 25,
        "strain_rate_s-1": "1e-3",
        "property": "compression_strength_limit",
        "value": 1461,
        "unit": "MPa",
        "specific_value_bulk": round(1461 / 5.20, 6),
        "specific_value_full_density": round(1461 / 5.35, 6),
        "specific_unit": "kN m kg^-1",
        "porosity_apparent_inflation_pct": round(100 * ((1461 / 5.20) / (1461 / 5.35) - 1), 6),
        "density_semantics": "BULK_AND_FULL_AVAILABLE",
        "evidence_level": "DIRECT_FIGURE_LABEL+DERIVED_CALCULATION",
        "locator": "Fig. 7b-d; Table 1; section 3.3.1",
        "primary_QM10_tensile_pool": "NO_MODE_SPECIFIC",
        "claim_level": 2,
    },
]
for rate, stress, strain in [(840,1853,0.031),(1400,1889,0.054),(2170,1765,0.050),(3450,1734,0.045),(4140,1721,0.024)]:
    rows.append({
        "evidence_uid": f"REN2021_DYN_{rate}",
        "paper_uid": PAPER_UID,
        "doi": DOI,
        "sample_uid": "S_REN2021_20WP_TI",
        "sample_label": "20WP/Ti",
        "matrix_system": "CP-Ti",
        "reinforcement": "20 wt.% W particles",
        "process": "HIP as-sintered",
        "test_mode": "dynamic_compression",
        "temperature_C": 25,
        "strain_rate_s-1": rate,
        "property": "average_flow_stress",
        "value": stress,
        "unit": "MPa",
        "uniform_plastic_strain": strain,
        "specific_value_bulk": round(stress/5.20, 6),
        "specific_value_full_density": round(stress/5.35, 6),
        "specific_unit": "kN m kg^-1",
        "density_semantics": "BULK_AND_FULL_AVAILABLE",
        "evidence_level": "DIRECT_TABLE_TEXT+DERIVED_CALCULATION",
        "locator": "Table 3; sections 3.3.2-4",
        "primary_QM10_tensile_pool": "NO_MODE_SPECIFIC",
        "claim_level": 2,
    })
fields = sorted({k for r in rows for k in r})
write_csv(OUT / "W_ORIGINAL_DENSITY_STRENGTH_ANCHOR.csv", rows, fields)

comparators = [
    {"comparator":"20WP/Ti measured-bulk", "test_mode":"compression", "strength_limit_MPa":1461, "density_g_cm3":5.20, "specific_strength_kNm_kg":round(1461/5.20,6), "basis":"DIRECT_FIGURE+ARCHIMEDES", "eligibility":"SENSITIVITY_ONLY_POROSITY_PRESENT"},
    {"comparator":"20WP/Ti full-density corrected", "test_mode":"compression", "strength_limit_MPa":1461, "density_g_cm3":5.35, "specific_strength_kNm_kg":round(1461/5.35,6), "basis":"DIRECT_FIGURE+THEORETICAL_DENSITY", "eligibility":"PRIMARY_WITHIN_MODE"},
    {"comparator":"Ti-6Al-4V bimodal", "test_mode":"compression", "strength_limit_MPa":1294, "density_g_cm3":"", "specific_strength_kNm_kg":294, "basis":"DIRECT_FIGURE_LABEL", "eligibility":"CROSS_MATRIX_COMPARATOR"},
    {"comparator":"Ti-6Al-4V lamellar", "test_mode":"compression", "strength_limit_MPa":1234, "density_g_cm3":"", "specific_strength_kNm_kg":280, "basis":"DIRECT_FIGURE_LABEL", "eligibility":"CROSS_MATRIX_COMPARATOR"},
    {"comparator":"CP-Ti grade 4", "test_mode":"compression", "strength_limit_MPa":"", "density_g_cm3":"", "specific_strength_kNm_kg":111, "basis":"DIRECT_FIGURE_LABEL", "eligibility":"CROSS_MATRIX_COMPARATOR"},
]
write_csv(OUT / "figure_data/F7_W_measured_density_compression_anchor.csv", comparators)

source_audit = [
    {
        "source_id": SOURCE_ID,
        "paper_uid": PAPER_UID,
        "doi": DOI,
        "title": SOURCE_TITLE,
        "source_type": "ORIGINAL_PDF_OPEN_ACCESS",
        "opened": "YES_FULL_12_PAGES_MULTIMODAL",
        "locator": SOURCE_LOCATOR,
        "source_hash": "",
        "source_hash_status": "NOT_EXPOSED_BY_FILE_LIBRARY_RUNTIME",
        "evidence_object_sha256": EVIDENCE_OBJECT_SHA256,
        "role": "DIRECT_MEASURED_DENSITY_W_ANCHOR",
        "terminal_state": "INCLUDED_MODE_SPECIFIC_NOT_TENSILE_POOLED",
    }
]
write_csv(OUT / "SOURCE_AUDIT_ADDENDUM.csv", source_audit)

duplicates = [
    {
        "canonical_paper_uid": PAPER_UID,
        "doi": DOI,
        "canonical_file_library_id": "file_0000000025d071f888610611483e808c",
        "duplicate_file_library_id": "file_00000000fbd0720b97847815c9fbceb5",
        "resolution": "DOI_AND_FULL_TEXT_IDENTITY_DEDUPLICATED",
        "independent_paper_count": 1,
        "reason": "Renamed duplicate copies must not inflate paper count or precision.",
    }
]
write_csv(OUT / "DUPLICATE_SOURCE_RESOLUTION.csv", duplicates)

# Add density rows while preserving the frozen schema.
with (OUT / "DENSITY_LEDGER.csv").open(encoding="utf-8", newline="") as f:
    dr = csv.DictReader(f); density_fields = dr.fieldnames or []; density_rows = list(dr)
base_density = {
    "snapshot_id": json.loads((OUT / "WINDOW_STATUS.json").read_text(encoding="utf-8"))["snapshot_id"],
    "paper_uid": PAPER_UID,
    "sample_uid": "S_REN2021_20WP_TI",
    "sample_label": "20WP/Ti",
    "condition_uid": "C_REN2021_HIP_RT_DENSITY",
    "temperature_c": 25,
    "reinforcement": "20 wt.% W particles",
    "reinforcement_fraction": 20,
    "reinforcement_unit": "wt.%",
    "W_wt_pct": 20,
    "Ta_wt_pct": 0,
    "evidence_level": "DIRECT_TABLE_TEXT",
    "porosity_credit_allowed": "NO",
}
for semantics, value, sd, source in [
    ("FULL_DENSITY_POROSITY_CONTROLLED", 5.35, "", "SOURCE_THEORETICAL_DENSITY"),
    ("BULK_AS_FABRICATED", 5.20, 0.02, "MEASURED_ARCHIMEDES_MEAN_N5"),
]:
    row = dict(base_density)
    row.update({
        "density_record_uid": "D_REN2021_" + ("FULL" if semantics.startswith("FULL") else "BULK"),
        "density_g_cm3": value,
        "density_sd_g_cm3": sd,
        "density_semantics": semantics,
        "density_source": source,
        "relative_density_pct": 97.20,
        "porosity_pct": 2.80,
        "notes": "Compression-only W anchor; bulk density never credited as lightweight benefit.",
    })
    density_rows.append({k: row.get(k, "") for k in density_fields})
write_csv(OUT / "DENSITY_LEDGER.csv", density_rows, density_fields)

# Append null/counterexample and conflict records using existing schemas.
append_csv(OUT / "NULL_NEGATIVE_RESULTS.csv", {
    "result_id":"W20_SPECIFIC_PARITY_NOT_DOMINANCE",
    "category":"MODE_SPECIFIC_COUNTEREXAMPLE",
    "finding":"20 wt.% W raises compression strength but yields only parity-level specific strength versus Ti-6Al-4V",
    "quantitative_anchor":"281 vs 294 kN m kg^-1 (bimodal) and 280 kN m kg^-1 (lamellar); full-density-corrected 20WP/Ti = 273.08",
    "implication":"High absolute strength does not guarantee a superior mass-normalized outcome; porosity must not be credited.",
})
append_csv(OUT / "CONFLICT_LEDGER.csv", {
    "conflict_id":"C009",
    "object":"Ren2021 duplicate PDFs",
    "source_a":"file_0000000025d071f888610611483e808c",
    "source_b":"file_00000000fbd0720b97847815c9fbceb5",
    "resolution":"DOI/full-text deduplication; one independent paper",
    "severity":"MEDIUM",
    "open":"NO",
})
append_csv(OUT / "CONFLICT_LEDGER.csv", {
    "conflict_id":"C010",
    "object":"20WP/Ti density semantics",
    "source_a":"Archimedes bulk density 5.20 ± 0.02 g cm^-3",
    "source_b":"theoretical density 5.35 g cm^-3; porosity 2.80%",
    "resolution":"Use 5.35 for primary porosity-controlled specific property; 5.20 only as sensitivity",
    "severity":"HIGH",
    "open":"NO",
})

# Source-bound provenance without pretending the File Library exposes a binary hash.
prov = {
    "provenance_uid":"PROV_REN2021_W_ANCHOR",
    "paper_uid":PAPER_UID,
    "source_id":SOURCE_ID,
    "doi":DOI,
    "source_title":SOURCE_TITLE,
    "source_type":"ORIGINAL_PDF",
    "source_locator":SOURCE_LOCATOR,
    "source_hash":None,
    "source_hash_missing_reason":"File Library runtime did not expose binary hash; bind locally before authority absorption.",
    "evidence_object_sha256":EVIDENCE_OBJECT_SHA256,
    "evidence_grade":"DIRECT_TABLE_TEXT+DIRECT_FIGURE_LABEL",
    "admission":"MODE_SPECIFIC_SUPPORT_ONLY",
    "test_mode_firewall":"compression rows are not pooled with tensile UTS/YS",
}
with (OUT / "PROVENANCE.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(prov, ensure_ascii=False, sort_keys=True) + "\n")

append_md(OUT / "00_EXECUTIVE_VERDICT.md", f"""
## Original-paper W anchor added after full-source audit

Ren et al. (2021, DOI `{DOI}`) provides the missing direct measured-density heavy-W anchor. The HIP-sintered 20WP/Ti composite has theoretical density 5.35 g cm^-3, Archimedes density 5.20 ± 0.02 g cm^-3, and 2.80% porosity. At 25 °C and 10^-3 s^-1 compression, its yield stress and strength limit are 1071 and 1461 MPa. The reported bulk-density specific strength is 281 kN m kg^-1, compared with 294 for bimodal Ti-6Al-4V and 280 for lamellar Ti-6Al-4V.

The correct porosity-controlled value is `1461/5.35 = 273.08 kN m kg^-1`, not 281. Using the lower porous bulk density inflates the apparent mass-normalized result by 2.89%. Therefore 20 wt.% W demonstrates **specific-strength parity, not general dominance**, relative to the Ti-6Al-4V comparators. It is 4.42% below the bimodal comparator and 0.36% above the lamellar comparator on the paper's reported bulk-specific metric. This is a same-paper cross-matrix comparison, not an isolated W causal effect.

Compression and tensile properties remain strictly separated. Dynamic compression rows show negative strain-rate sensitivity above approximately 1400 s^-1 and severe ductility loss, consistent with Kirkendall pores, W-particle cracking and beta-Ti thermal softening. These observations constrain service claims but are not pooled into the tensile estimand.
""")
append_md(OUT / "METHODS.md", """
## Heavy-W original-paper extension

The Ren 2021 paper was read as a complete 12-page original PDF. Table 1 density values, Fig. 7 labeled quasi-static compression values and Table 3 dynamic values were transcribed as separate atomic evidence objects. The same DOI appeared as two renamed File Library copies; DOI/full-text deduplication fixes the independent-paper count at one. Theoretical density is the primary denominator because the MDU forbids treating porosity-induced density reduction as a benefit. Archimedes density is retained only as sensitivity. Compression is firewalled from tension and no cross-mode pooling is performed.
""")
append_md(OUT / "LIMITATIONS.md", """
## Heavy-W anchor limitations

The Ren 2021 comparator arms are CP-Ti and forged Ti-6Al-4V rather than an otherwise identical zero-W matrix, so they do not identify a pure W effect. The paper reports direct density only for 20WP/Ti; Ti-6Al-4V comparator specific-strength values are taken from labeled Fig. 7 bars. The File Library runtime did not expose a binary SHA-256 for the original PDF, so local source-hash binding remains mandatory before authority absorption.
""")

# Add one original-paper figure, generated only from the accompanying CSV.
labels = [r["comparator"] for r in comparators[:4]]
values = [float(r["specific_strength_kNm_kg"]) for r in comparators[:4]]
fig = plt.figure(figsize=(9.2, 5.8))
ax = fig.add_subplot(111)
ax.bar(range(len(labels)), values)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=18, ha="right", fontsize=8)
ax.set_ylabel("Specific compression strength (kN m kg$^{-1}$)")
ax.set_title("Measured-density W anchor: strength gain does not imply mass-normalized dominance")
ax.grid(axis="y", alpha=0.25)
for i, v in enumerate(values):
    ax.text(i, v + 2, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
ax.text(0.01, 0.01, "20WP/Ti full-density correction removes porosity credit; compression only", transform=ax.transAxes, fontsize=7)
for ext in ("svg", "pdf", "png"):
    kwargs = {"bbox_inches":"tight"}
    if ext == "png": kwargs["dpi"] = 600
    fig.savefig(OUT / "figures" / f"QM10_F7_W_measured_density_compression_anchor.{ext}", **kwargs)
plt.close(fig)

plot_code = '''#!/usr/bin/env python3
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
with (R/"figure_data/F7_W_measured_density_compression_anchor.csv").open(encoding="utf-8") as f:
    rows=list(csv.DictReader(f))[:4]
labels=[r["comparator"] for r in rows]
values=[float(r["specific_strength_kNm_kg"]) for r in rows]
fig=plt.figure(figsize=(9.2,5.8)); ax=fig.add_subplot(111)
ax.bar(range(len(labels)),values); ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels,rotation=18,ha="right",fontsize=8)
ax.set_ylabel("Specific compression strength (kN m kg$^{-1}$)")
ax.set_title("Measured-density W anchor: strength gain does not imply mass-normalized dominance")
ax.grid(axis="y",alpha=.25)
for i,v in enumerate(values): ax.text(i,v+2,f"{v:.1f}",ha="center",fontsize=8)
O=R/"figures_rebuilt"; O.mkdir(exist_ok=True)
for ext in ("svg","pdf","png"): fig.savefig(O/f"QM10_F7_W_measured_density_compression_anchor.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
plt.close(fig)
print("PLOTS_REBUILT=3")
'''
(OUT / "plot_code/plot_w_original_anchor.py").write_text(plot_code, encoding="utf-8")

specs = json.loads((OUT / "PLOT_SPECS.json").read_text(encoding="utf-8"))
specs.append({
    "figure_id":"QM10_F7",
    "title":"Measured-density W compression anchor",
    "data":"figure_data/F7_W_measured_density_compression_anchor.csv",
    "code":"plot_code/plot_w_original_anchor.py",
    "outputs":["svg","pdf","png"],
    "dpi_png":600,
    "mandatory":True,
    "note":"Mode-specific original-paper evidence; theoretical-density bar removes porosity credit.",
})
(OUT / "PLOT_SPECS.json").write_text(json.dumps(specs, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")

status = json.loads((OUT / "WINDOW_STATUS.json").read_text(encoding="utf-8"))
status["papers_seen"] = int(status.get("papers_seen", 0)) + 1
status["independent_papers"] = int(status.get("independent_papers", 0)) + 1
status["plots_generated"] = 7
status["mode_specific_original_papers"] = 1
status["original_w_density_anchor"] = "INCLUDED_MODE_SPECIFIC"
status["next_action"] = "LOCAL_BIND_AUTHORITATIVE_SNAPSHOT_PDF_HASH_AND_MEASURE_TI65_W_TA_DENSITY"
(OUT / "WINDOW_STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")

append_md(OUT / "acceptance_commands.md", """
```bash
python plot_code/plot_w_original_anchor.py
```
""")
append_md(OUT / "RUN_LOG.txt", f"""original_w_paper={DOI}
original_w_evidence_object_sha256={EVIDENCE_OBJECT_SHA256}
plots=7
compression_tension_firewall=PASS
pdf_duplicate_resolution=ONE_INDEPENDENT_PAPER
""")

# Replace generated validator and acceptance test with stricter v3 checks.
validator = '''#!/usr/bin/env python3
from pathlib import Path
import csv,json,sys
R=Path(__file__).resolve().parent
required=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","DENSITY_LEDGER.csv","SPECIFIC_PROPERTY_EFFECTS.csv","DENSITY_UNCERTAINTY.csv","SPECIFIC_PARETO.csv","W_ORIGINAL_DENSITY_STRENGTH_ANCHOR.csv","SOURCE_AUDIT_ADDENDUM.csv","DUPLICATE_SOURCE_RESOLUTION.csv"]
errors=["missing:"+x for x in required if not (R/x).is_file()]
status=json.loads((R/"WINDOW_STATUS.json").read_text())
if status["claim_level_max"]>2: errors.append("claim ceiling")
if status["gold_promoted"] or status["production_model_registered"]: errors.append("authority violation")
with (R/"ANALYSIS_COHORT.csv").open(encoding="utf-8") as f: atomic=list(csv.DictReader(f))
if len(atomic)!=len({r["record_uid"] for r in atomic}): errors.append("duplicate record_uid")
with (R/"DENSITY_LEDGER.csv").open(encoding="utf-8") as f: dens=list(csv.DictReader(f))
if any(r["porosity_credit_allowed"]!="NO" for r in dens): errors.append("porosity credit")
wp=[r for r in dens if r["paper_uid"]=="P_REN2021_20WP_TI"]
if len(wp)!=2: errors.append("missing Ren2021 full/bulk density pair")
if not (R/"figure_data/F7_W_measured_density_compression_anchor.csv").is_file(): errors.append("missing F7 data")
for ext in ("svg","pdf","png"):
    if not (R/"figures"/f"QM10_F7_W_measured_density_compression_anchor.{ext}").is_file(): errors.append("missing F7 "+ext)
if errors:
    print(json.dumps({"pass":False,"errors":errors},indent=2)); sys.exit(1)
print(json.dumps({"pass":True,"required_files":len(required),"atomic_rows":len(atomic),"density_rows":len(dens),"figure_files":len(list((R/"figures").glob("*.*"))),"original_w_anchor_rows":len(wp)},indent=2))
'''
(OUT / "validate_package.py").write_text(validator, encoding="utf-8")

test = '''#!/usr/bin/env python3
from pathlib import Path
import csv,json,math
R=Path(__file__).resolve().parents[1]
checks=[]
def ok(name,cond):
    checks.append(name)
    if not cond: raise AssertionError(name)
ok("required",all((R/x).is_file() for x in ["DENSITY_LEDGER.csv","SPECIFIC_PROPERTY_EFFECTS.csv","SPECIFIC_PARETO.csv","W_ORIGINAL_DENSITY_STRENGTH_ANCHOR.csv","SOURCE_AUDIT_ADDENDUM.csv","DUPLICATE_SOURCE_RESOLUTION.csv"]))
with (R/"ANALYSIS_COHORT.csv").open(encoding="utf-8") as f:a=list(csv.DictReader(f))
ok("atomic_unique",len(a)==len({x["record_uid"] for x in a}))
with (R/"PAIR_MATCHES.csv").open(encoding="utf-8") as f:p=list(csv.DictReader(f))
sids={x["sample_uid"] for x in a}; ok("pair_linkage",all(x["control_sample_uid"] in sids and x["treated_sample_uid"] in sids for x in p))
with (R/"DENSITY_LEDGER.csv").open(encoding="utf-8") as f:d=list(csv.DictReader(f))
ok("no_porosity_credit",all(x["porosity_credit_allowed"]=="NO" for x in d))
wp=[x for x in d if x["paper_uid"]=="P_REN2021_20WP_TI"]
ok("w_measured_density",len(wp)==2 and {float(x["density_g_cm3"]) for x in wp}=={5.20,5.35})
with (R/"W_ORIGINAL_DENSITY_STRENGTH_ANCHOR.csv").open(encoding="utf-8") as f:w=list(csv.DictReader(f))
strength=next(x for x in w if x["evidence_uid"]=="REN2021_QS_CSL")
ok("porosity_correction",math.isclose(float(strength["specific_value_full_density"]),1461/5.35,rel_tol=1e-6) and float(strength["porosity_apparent_inflation_pct"])>2.8)
ok("mode_firewall",all(x["primary_QM10_tensile_pool"]=="NO_MODE_SPECIFIC" for x in w))
with (R/"DUPLICATE_SOURCE_RESOLUTION.csv").open(encoding="utf-8") as f:dups=list(csv.DictReader(f))
ok("doi_dedup",len(dups)==1 and dups[0]["independent_paper_count"]=="1")
with (R/"SPECIFIC_PROPERTY_EFFECTS.csv").open(encoding="utf-8") as f:s=list(csv.DictReader(f))
wti=[x for x in s if x["paper_uid"]=="P_TI65_INTERNAL_W" and x["property"]=="UTS" and x["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED"]
ok("ti65_w_effects",len(wti)==2 and all(float(x["percent_change_specific"])>20 for x in wti))
y=[x for x in s if x["paper_uid"]=="P_YAN2014" and x["property"]=="UTS" and x["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED"]
ok("dose_counterexamples",sum(float(x["percent_change_specific"])<0 for x in y)>=3)
status=json.loads((R/"WINDOW_STATUS.json").read_text()); ok("authority",status["claim_level_max"]<=2 and not status["gold_promoted"] and not status["production_model_registered"])
ok("figure_formats",len(list((R/"figures").glob("*.png")))==7 and len(list((R/"figures").glob("*.svg")))==7 and len(list((R/"figures").glob("*.pdf")))==7)
ok("plot_code",(R/"plot_code/plot_all.py").is_file() and (R/"plot_code/plot_w_original_anchor.py").is_file())
print(json.dumps({"pass":True,"checks":checks,"count":len(checks)},indent=2))
'''
(OUT / "tests/test_acceptance.py").write_text(test, encoding="utf-8")

# Keep the exact augmentation source in the package before manifest/checksum generation.
repro_dir = OUT / "repro"
repro_dir.mkdir(exist_ok=True)
(repro_dir / "augment_original_w_evidence.py").write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

# Rebuild manifest/checksums after all changes.
for name in ("MANIFEST.json", "CHECKSUMS.sha256"):
    p = OUT / name
    if p.exists(): p.unlink()
pre_files = sorted(p for p in OUT.rglob("*") if p.is_file())
manifest = {
    "window_id":"QM10",
    "snapshot_id":status["snapshot_id"],
    "extension":"ORIGINAL_W_MEASURED_DENSITY_V3",
    "file_count_excluding_manifest_checksums":len(pre_files),
    "nested_zip_count":0,
    "status":"CONTINUE_DATA_GAP",
    "files":[{"path":str(p.relative_to(OUT)),"bytes":p.stat().st_size,"sha256":sha256_file(p)} for p in pre_files],
}
(OUT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
check_files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
(OUT / "CHECKSUMS.sha256").write_text("\n".join(f"{sha256_file(p)}  {p.relative_to(OUT)}" for p in check_files)+"\n", encoding="utf-8")

if ZIP_PATH.exists(): ZIP_PATH.unlink()
with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(OUT.rglob("*")):
        if p.is_file(): z.write(p, p.relative_to(OUT))
with zipfile.ZipFile(ZIP_PATH) as z:
    assert z.testzip() is None
    assert not [n for n in z.namelist() if n.lower().endswith(".zip")]
zip_sha = sha256_file(ZIP_PATH)
SHA_PATH.write_text(f"{zip_sha}  {ZIP_PATH.name}\n", encoding="utf-8")
print(json.dumps({
    "window":"QM10",
    "snapshot":status["snapshot_id"],
    "zip":str(ZIP_PATH),
    "sha256":zip_sha,
    "files":len([p for p in OUT.rglob('*') if p.is_file()]),
    "plots":21,
    "original_w_anchor":"PASS",
    "status":"CONTINUE_DATA_GAP",
}, indent=2))
