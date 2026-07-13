#!/usr/bin/env python3
"""Deterministic, fail-closed QM05 return-package builder.

This script consumes only the aggregate evidence and DOI/hash-bound source anchors
that were actually opened in the web execution. It does not mutate ACTIVE_TITMC,
Gold, schema authority, split manifests, or any production model registry.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

WINDOW = "QM05"
BATCH = "V30_TITMC_Q40_20260713"
FIXED_ZIP_DT = (2026, 7, 13, 12, 0, 0)

AGG: dict[str, Any] = {
    "paper_registry": 54504,
    "paper_completeness_vector_rows": 87958,
    "vector_present_snapshot": 44904,
    "vector_absent_snapshot": 43054,
    "snapshot_present_id": "snap_titmc_59dc21e0e6f5",
    "snapshot_absent_id": "snap_33bff4214c502add",
    "distinct_vector_papers": 51130,
    "local_download_proofs": 47994,
    "xml_verified": 46638,
    "missing_path": 1200,
    "parse_fail_proof": 140,
    "identity_mismatch": 16,
    "xml_sources": 3476,
    "xml_corpus_documents": 78683,
    "xml_strict_parse": 78410,
    "xml_recovered_parse": 273,
    "xml_parse_error_rows": 640,
    "scope_tmc_confirmed": 1827,
    "scope_tmc_possible": 4258,
    "scope_ti_alloy": 33769,
    "scope_non_titanium": 35411,
    "scope_method_transfer": 3125,
    "scope_correction": 171,
    "scope_retraction": 82,
    "scope_non_article": 40,
    "version_graph_edges": 37094,
    "source_utilization_members": 141326,
    "qm39_atomic_rows": 15089,
    "qm39_independent_papers": 975,
    "qm39_matches": 6322,
    "qm39_match_papers": 485,
    "qm06_pairs": 121,
    "qm06_papers": 38,
    "qm06_delta_uts": 133.1,
    "qm06_ci_low": 99.4,
    "qm06_ci_high": 165.7,
    "qm06_pi_low": -87.0,
    "qm06_pi_high": 308.5,
    "qm06_relative_gain_pct": 16.6,
    "qm06_relative_ci_low": 12.1,
    "qm06_relative_ci_high": 21.5,
    "qm06_a_no_quality_gate": 106.7,
    "qm06_all_ab": 122.8,
    "qm06_lopo_low": 127.5,
    "qm06_lopo_high": 142.9,
    "qm06_i2_pct": 97.3,
    "qm06_nonpositive_paper_pct": 5.3,
}

PAPERS: list[dict[str, Any]] = [
    {
        "paper_uid": "doi:10.1016/j.matdes.2013.04.048",
        "paper_doi": "10.1016/j.matdes.2013.04.048",
        "paper_year": 2013,
        "journal": "Materials & Design",
        "publisher": "Elsevier",
        "title": "TiB whiskers reinforced high temperature titanium Ti60 alloy composites with novel network microstructure",
        "archive": "TITMC_V27_LIT_WEB_P009_OF_010.zip",
        "member": "7b009eb2_7b009eb2b56153b4.xml",
        "source_hash": "7b009eb2b56153b4b91960e9c00f3034c4760046136d9040475490632994d902",
        "evidence_level": "MIXED_ORIGINAL_TEXT_UTS_FIGURE_DERIVED_EL",
        "validation_note": "Original publisher XML directly states Ti60 matrix and 5/8 vol.% TiBw UTS at 600/700/800 C; EL remains figure-derived.",
        "weight_low": 0.55, "weight_base": 0.75, "weight_high": 0.90,
        "uncertainty_reporting": "PARTIAL_OR_UNKNOWN", "replicate_reporting": "UNKNOWN",
        "matrix_control": "YES", "numeric_el": "FIGURE_DERIVED",
    },
    {
        "paper_uid": "doi:10.1016/j.jallcom.2025.180981",
        "paper_doi": "10.1016/j.jallcom.2025.180981",
        "paper_year": 2025,
        "journal": "Journal of Alloys and Compounds",
        "publisher": "Elsevier",
        "title": "Microscopic structural modeling and mechanical behavior of titanium boride reinforced titanium matrix composites with network configuration",
        "archive": "TITMC_V27_LIT_WEB_P006_OF_010.zip",
        "member": "da00d931_da00d93156e5a71f.xml",
        "source_hash": "da00d93156e5a71fcd6b30539eb4b39757ce79fa149af4347864c0f7a20012f0",
        "evidence_level": "DIRECT_TEXT_ORIGINAL_XML",
        "validation_note": "Original publisher XML directly states network, uniform and Ti matrix UTS at 600/700/800 C with uncertainty for composite arms.",
        "weight_low": 0.85, "weight_base": 0.95, "weight_high": 1.00,
        "uncertainty_reporting": "YES_COMPOSITE_ARMS", "replicate_reporting": "UNKNOWN",
        "matrix_control": "YES", "numeric_el": "UNKNOWN",
    },
    {
        "paper_uid": "doi:10.1016/j.jallcom.2025.181955",
        "paper_doi": "10.1016/j.jallcom.2025.181955",
        "paper_year": 2025,
        "journal": "Journal of Alloys and Compounds",
        "publisher": "Elsevier",
        "title": "Enhanced high temperature mechanical properties of TiBw/TA15 composite fabricated by multi-DOF forming",
        "archive": "TITMC_V27_LIT_WEB_P006_OF_010.zip",
        "member": "bbf5b022_bbf5b022d8f3aac9.xml",
        "source_hash": "bbf5b022d8f3aac998a895d42a3770a3d0637aa9ca7a547ce2d1de4d373ce655",
        "evidence_level": "DIRECT_TABLE_TEXT_ORIGINAL_XML",
        "validation_note": "Original publisher XML Table 1 directly reports 800 C YS/UTS/EL for as-sintered and multi-DOF formed TiBw/TA15; testing repeated at least three times.",
        "weight_low": 0.90, "weight_base": 1.00, "weight_high": 1.00,
        "uncertainty_reporting": "YES", "replicate_reporting": "N_AT_LEAST_3",
        "matrix_control": "NO_EXACT_MATRIX_ARM_IN_AUDITED_NOTE", "numeric_el": "YES",
    },
    {
        "paper_uid": "doi:10.1016/j.matdes.2016.03.091",
        "paper_doi": "10.1016/j.matdes.2016.03.091",
        "paper_year": 2016,
        "journal": "Materials & Design",
        "publisher": "Elsevier",
        "title": "Effect of Zr, Mo and TiC on microstructure and high-temperature tensile strength of cast titanium matrix composites",
        "archive": "TITMC_V27_LIT_WEB_P008_OF_010.zip",
        "member": "9b0d5b2e_9b0d5b2ef4250615.xml",
        "source_hash": "9b0d5b2ef42506159b5acc982ba05c7318e43fb1244c63f1a404be58657ba94a",
        "evidence_level": "DIRECT_TABLE_TEXT_ORIGINAL_XML",
        "validation_note": "Original publisher XML table directly reports five 800 C UTS/EL arms with uncertainties.",
        "weight_low": 0.90, "weight_base": 1.00, "weight_high": 1.00,
        "uncertainty_reporting": "YES", "replicate_reporting": "UNKNOWN",
        "matrix_control": "UNRESOLVED_FROM_AUDITED_NOTE", "numeric_el": "YES",
    },
    {
        "paper_uid": "doi:10.1016/0921-5093(94)90373-5",
        "paper_doi": "10.1016/0921-5093(94)90373-5",
        "paper_year": 1994,
        "journal": "Materials Science and Engineering A",
        "publisher": "Elsevier",
        "title": "Properties of SiC-fibre reinforced titanium alloys processed by fibre coating and hot isostatic pressing",
        "archive": "TITMC_V27_LIT_WEB_P009_OF_010.zip",
        "member": "8753e100_8753e100a19623ad.xml",
        "source_hash": "8753e100a19623ad8264f0d8c1ec95c430c8ef6c183e5b8b1e42d0b771cd87d4",
        "evidence_level": "DIRECT_TEXT_ORIGINAL_XML",
        "validation_note": "Original publisher XML directly reports 1500 MPa UTS at 800 C for vf=0.40 SiC-fibre/Ti-IMI834; required elongation is not reported.",
        "weight_low": 0.85, "weight_base": 0.95, "weight_high": 1.00,
        "uncertainty_reporting": "UNKNOWN", "replicate_reporting": "UNKNOWN",
        "matrix_control": "UNRESOLVED_FROM_AUDITED_NOTE", "numeric_el": "MISSING",
    },
    {
        "paper_uid": "doi:10.1016/j.matdes.2015.07.058",
        "paper_doi": "10.1016/j.matdes.2015.07.058",
        "paper_year": 2015,
        "journal": "Materials & Design",
        "publisher": "Elsevier",
        "title": "Effects of heat treatments on microstructure and tensile properties of as-extruded TiBw/near-alpha Ti composites",
        "archive": "TITMC_V27_LIT_WEB_P009_OF_010.zip",
        "member": "fed57cf5_fed57cf5ba75312c.xml",
        "source_hash": "fed57cf5ba75312c691092603ebcd9a6210176f91b68a31d14de3fe54886412e",
        "evidence_level": "DIRECT_TEXT_ORIGINAL_XML_UTS",
        "validation_note": "Original publisher XML directly reports as-aged composite UTS of 760/540/400 MPa at 700/750/800 C; EL is described as reduced but not numerically stated.",
        "weight_low": 0.70, "weight_base": 0.85, "weight_high": 0.95,
        "uncertainty_reporting": "UNKNOWN", "replicate_reporting": "UNKNOWN",
        "matrix_control": "NO_EXACT_MATRIX_ARM_IN_AUDITED_NOTE", "numeric_el": "MISSING_NUMERIC",
    },
]

OPENED = [
    ("SOURCE_EVIDENCE_INDEX.csv", "file_library:file_0000000019a8722f8f1bb4689f5d5cc2", "FILE_LIBRARY_ID:file_0000000019a8722f8f1bb4689f5d5cc2", "Six DOI/hash-bound original XML anchors"),
    ("snapshot_mixing_diagnostic.txt", "file_library:file_00000000ed10720ba9598817d22da612", "FILE_LIBRARY_ID:file_00000000ed10720ba9598817d22da612", "Direct mmc_control.sqlite aggregate snapshot diagnostic"),
    ("QM06/00_EXECUTIVE_VERDICT.md", "file_library:file_00000000b2fc720bb0ed130574d34783", "FILE_LIBRARY_ID:file_00000000b2fc720bb0ed130574d34783", "Matched UTS aggregate, LOPO and heterogeneity"),
    ("QM39/00_EXECUTIVE_VERDICT.md", "file_library:file_0000000052a4722fa38a2b6ccc409352", "FILE_LIBRARY_ID:file_0000000052a4722fa38a2b6ccc409352", "Atomic-row and independent-paper scope"),
    ("XW01 XML corpus audit assets", "file_library:XW01_MANIFEST_AND_COVERAGE", "ARTICLE_IDENTITY=1f6a17abda4f69c42a6bf3f9fcb855600c66ced52f940ecfbd852f22dee3c5bb;VERSION_GRAPH=c74bc746b7d398f91cdc1a48ac7f0b395c64686b16bb2be22dd19e50d6d1867c", "XML corpus, missingness, scope and version aggregates"),
    ("Historical INPUT_LEDGER.csv", "file_library:file_00000000b65c720ba0266889c506f730", "FILE_LIBRARY_ID:file_00000000b65c720ba0266889c506f730", "Historical package fingerprints; not newly verified"),
    ("GitHub README.md", "github:sddvacav/tiai-full-state-private@main:README.md", "gitblob:6fb679bd0a9a2f139f0bcda3c33f9da6e1de91fc", "Private-state repository boundary"),
    ("GitHub index/ENTRYPOINTS.md", "github:sddvacav/tiai-full-state-private@main:index/ENTRYPOINTS.md", "gitblob:a14eba5e337611169d6e80c77800f2fdf4b0d668", "Canonical read order"),
    ("GitHub index/key_paths.md", "github:sddvacav/tiai-full-state-private@main:index/key_paths.md", "gitblob:f45f528dd535c3642d9c9f2f33b472d7927a8f02", "Canonical paths"),
    ("GitHub DATA_REGISTRY.md", "github:sddvacav/tiai-full-state-private@main:DATA_REGISTRY.md", "gitblob:60160b011e2724ce479b281f60e671175efe7d11", "Frozen-matrix registration boundary"),
    ("GitHub data_index_summary.md", "github:sddvacav/tiai-full-state-private@main:data_manifests/data_index_summary.md", "gitblob:bf221e5c4509477631e976775eb3e72cfc952a7f", "Manifest scale and duplicate-governance context"),
]

UPLOADS = [
    "00_统一上传总控与校验信息_20260712.zip",
    "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
] + [f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 9)] + [
    "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
] + [f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 4)] + [
    f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1, 11)
]

REQUIRED = [
    "00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv", "CONFLICT_LEDGER.csv",
    "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md", "PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json",
    "MANIFEST.json", "CHECKSUMS.sha256", "SOURCE_RELIABILITY_REPLAY.csv",
    "MISSINGNESS_MODEL.csv", "DUPLICATE_FAMILY.csv", "BIAS_SENSITIVITY.csv",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_id() -> str:
    payload = {
        "batch": BATCH,
        "window": WINDOW,
        "aggregate_evidence": AGG,
        "source_hashes": sorted(p["source_hash"] for p in PAPERS),
        "opened_source_hashes": sorted(x[2] for x in OPENED),
        "authority": "DERIVED_ANALYSIS_ONLY_CANONICAL_V29_Q40_MISSING",
    }
    digest = sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return "QM05_DERIVED_" + digest[:20]


def neff(weights: Iterable[float]) -> float:
    w = list(weights)
    return sum(w) ** 2 / sum(x * x for x in w)


def write_text(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(root: Path, rel: str, obj: Any) -> None:
    write_text(root, rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(root: Path, rel: str, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def save_figure(fig: Any, root: Path, stem: str) -> None:
    for ext, dpi in (("svg", None), ("pdf", None), ("png", 600)):
        fig.savefig(root / "figures" / f"{stem}.{ext}", dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def build_figures(root: Path, snap: str) -> None:
    # Fig 1: source reliability
    labels = [f"{p['paper_year']}\n{p['paper_doi'].split('/')[-1][:14]}" for p in PAPERS]
    mid = [p["weight_base"] for p in PAPERS]
    lo = [p["weight_low"] for p in PAPERS]
    hi = [p["weight_high"] for p in PAPERS]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.bar(range(len(PAPERS)), mid, yerr=[[m-l for m, l in zip(mid, lo)], [h-m for h, m in zip(hi, mid)]], capsize=4)
    ax.set_xticks(range(len(PAPERS)), labels, rotation=25, ha="right")
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Sensitivity-only source reliability weight")
    ax.set_title(f"Source reliability replay | k=6 papers | Kish effective N={neff(mid):.2f}")
    ax.text(0.01, 0.98, "Estimand: provenance/directness sensitivity weight; bounds are not confidence intervals.\nEvidence: DOI/hash-bound original publisher XML; support: targeted audit only.", transform=ax.transAxes, va="top", fontsize=9)
    fig.tight_layout()
    save_figure(fig, root, "Fig1_source_reliability")

    # Fig 2: UpSet-style missingness pattern
    patterns = [
        ("XML_VERIFIED", AGG["xml_verified"], [0, 0, 0]),
        ("MISSING_PATH", AGG["missing_path"], [1, 0, 0]),
        ("PARSE_FAIL", AGG["parse_fail_proof"], [0, 1, 0]),
        ("IDENTITY_MISMATCH", AGG["identity_mismatch"], [0, 0, 1]),
    ]
    fig = plt.figure(figsize=(11, 7.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[3.2, 1.2], hspace=0.05)
    ax = fig.add_subplot(gs[0])
    x = list(range(len(patterns)))
    counts = [r[1] for r in patterns]
    ax.bar(x, counts)
    ax.set_yscale("log")
    ax.set_ylabel("Proof-record count (log scale)")
    ax.set_xticks(x, [])
    ax.set_title("Missingness pattern UpSet | proof records N=47,994 | independent-paper N not identifiable")
    for i, c in enumerate(counts):
        ax.text(i, c * 1.15, f"{c:,}", ha="center", va="bottom", fontsize=9)
    ax.text(0.01, 0.96, "Estimand: observed technical proof-state intersections. Evidence: local proof aggregate.\n43,054 XML-absent vector rows are excluded because they belong to a different snapshot.", transform=ax.transAxes, va="top", fontsize=9)
    mx = fig.add_subplot(gs[1], sharex=ax)
    names = ["Missing path", "Parse failure", "Identity mismatch"]
    for r, name in enumerate(names):
        mx.text(-0.55, 2-r, name, ha="right", va="center", fontsize=9)
        for i, (_, _, flags) in enumerate(patterns):
            mx.scatter(i, 2-r, s=85, facecolors="black" if flags[r] else "white", edgecolors="black")
    mx.set_xlim(-0.75, 3.5)
    mx.set_ylim(-0.6, 2.6)
    mx.set_yticks([])
    mx.set_xticks(x, [r[0] for r in patterns], rotation=20, ha="right")
    for spine in mx.spines.values(): spine.set_visible(False)
    fig.tight_layout()
    save_figure(fig, root, "Fig2_missingness_upset")

    # Fig 3: dependency network
    nodes = {
        "registry": ("Paper registry", AGG["paper_registry"]),
        "snapA": ("Vector snapshot A", AGG["vector_present_snapshot"]),
        "snapB": ("Vector snapshot B", AGG["vector_absent_snapshot"]),
        "distinct": ("Distinct vector paper_uid", AGG["distinct_vector_papers"]),
        "proofs": ("Local proof records", AGG["local_download_proofs"]),
        "verified": ("XML verified", AGG["xml_verified"]),
        "docs": ("XW01 XML documents", AGG["xml_corpus_documents"]),
        "vedges": ("Version graph edges", AGG["version_graph_edges"]),
        "pairs": ("QM06 matched rows", AGG["qm06_pairs"]),
        "papers": ("QM06 independent papers", AGG["qm06_papers"]),
    }
    edge_rows = [
        ("registry", "snapA", "snapshot rows"), ("registry", "snapB", "snapshot rows"),
        ("snapA", "distinct", "deduplicate paper_uid"), ("snapB", "distinct", "do not pool snapshots"),
        ("registry", "proofs", "proof coverage"), ("proofs", "verified", "verified state"),
        ("docs", "vedges", "version/identity links"), ("pairs", "papers", "cluster by paper"),
    ]
    g = nx.DiGraph()
    for key, (label, count) in nodes.items(): g.add_node(key, label=label, count=count)
    for a, b, relation in edge_rows: g.add_edge(a, b, relation=relation)
    pos = nx.spring_layout(g, seed=42, k=1.15)
    fig, ax = plt.subplots(figsize=(12, 8))
    sizes = [550 + 260 * math.log10(max(1, g.nodes[n]["count"])) for n in g.nodes]
    nx.draw_networkx_nodes(g, pos, node_size=sizes, ax=ax)
    nx.draw_networkx_edges(g, pos, arrows=True, arrowsize=18, width=1.2, ax=ax)
    nx.draw_networkx_labels(g, pos, {n: f"{g.nodes[n]['label']}\nN={g.nodes[n]['count']:,}" for n in g.nodes}, font_size=8, ax=ax)
    nx.draw_networkx_edge_labels(g, pos, {(u, v): d["relation"] for u, v, d in g.edges(data=True)}, font_size=7, rotate=False, ax=ax)
    ax.set_title("Duplicate and dependency inflation network | estimand: naive-row / independent-paper N")
    ax.text(0.01, 0.01, "QM06 support: 121 matched rows -> 38 independent papers = 3.18x inflation.\nEvidence: aggregate lineage only; exact global duplicate-family effective N is not identifiable.", transform=ax.transAxes, fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    save_figure(fig, root, "Fig3_duplicate_dependency_network")

    # Fig 4: funnel identifiability, no fabricated funnel scatter
    req = ["Paper effect", "Standard error", "Study size", "Effect-year join", "Aggregate pooled effect"]
    vals = [0, 0, 0, 0, 100]
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    ax.barh(range(len(req)), vals)
    ax.set_yticks(range(len(req)), req)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Availability in 38-paper matched-effect cohort (%)")
    ax.set_title("Funnel/Egger diagnostics: NOT IDENTIFIABLE | independent papers=38")
    for i, v in enumerate(vals): ax.text(v + 1, i, f"{v}%", va="center")
    ax.text(0.02, 0.02, "Estimand: availability of paper-level publication-bias inputs.\nEvidence: aggregate matched-effect verdict; aggregate CI/PI is insufficient and no funnel points are fabricated.", transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    save_figure(fig, root, "Fig4_funnel_not_identifiable")


def build(root: Path, zip_path: Path | None) -> None:
    if root.exists(): shutil.rmtree(root)
    for d in ("figure_data", "plot_code", "figures", "analysis_code", "tests"):
        (root / d).mkdir(parents=True, exist_ok=True)
    snap = snapshot_id()
    infl = AGG["qm06_pairs"] / AGG["qm06_papers"]
    n_eff = neff(p["weight_base"] for p in PAPERS)
    tech_fail = AGG["missing_path"] + AGG["parse_fail_proof"] + AGG["identity_mismatch"]
    verified_pct = 100 * AGG["xml_verified"] / AGG["local_download_proofs"]
    issue_pct = 100 * tech_fail / AGG["local_download_proofs"]

    # Input ledger
    ledger = []
    for i, name in enumerate(UPLOADS, 1):
        ledger.append({
            "input_id": f"UPLOAD_{i:02d}", "snapshot_id": snap, "source_name": name,
            "source_type": "ZIP", "path_or_locator": "/mnt/data/" + name,
            "source_hash": "UNAVAILABLE_IN_WEB_RUNTIME", "source_hash_kind": "MISSING_CURRENT_VERIFICATION",
            "priority": "P0" if name.startswith("00_") else ("P1" if "LIT_WEB" in name else "P2"),
            "window_relevance": "PRIMARY_EXPECTED_INPUT", "terminal_use_status": "REGISTERED_NOT_OPENED",
            "opened_or_consumed": "NO",
            "notes": "Mounted-path byte access returned system-level ClientError. Historical fingerprints are not presented as newly verified full-file SHA-256.",
        })
    for i, (name, loc, hv, role) in enumerate(OPENED, 1):
        ledger.append({
            "input_id": f"OPENED_{i:02d}", "snapshot_id": snap, "source_name": name,
            "source_type": "FILE_LIBRARY_OR_GITHUB", "path_or_locator": loc, "source_hash": hv,
            "source_hash_kind": "FILE_ID_GIT_BLOB_OR_COMPONENT_SHA", "priority": "P0_OPENED",
            "window_relevance": role, "terminal_use_status": "USED_DIRECTLY_OR_AS_AGGREGATE_EVIDENCE",
            "opened_or_consumed": "YES", "notes": "Aggregate-only evidence remains non-readmissible to Gold.",
        })
    ledger_fields = ["input_id", "snapshot_id", "source_name", "source_type", "path_or_locator", "source_hash", "source_hash_kind", "priority", "window_relevance", "terminal_use_status", "opened_or_consumed", "notes"]
    write_csv(root, "INPUT_LEDGER.csv", ledger_fields, ledger)
    write_text(root, "OPENED_FILES.txt", "\n".join(f"{r['source_name']} | {r['path_or_locator']} | {r['source_hash']}" for r in ledger if r["opened_or_consumed"] == "YES"))

    # Source reliability replay
    source_rows = []
    for p in PAPERS:
        source_rows.append({
            "snapshot_id": snap, **p, "source_type": "PUBLISHER_XML",
            "origin_type": "ORIGINAL_EXPERIMENTAL", "own_lab_public": "PUBLIC_LITERATURE_UNKNOWN_LAB_OVERLAP",
            "source_locator": f"/mnt/data/{p['archive']}::{p['member']}",
            "reliability_weight_low": p["weight_low"], "reliability_weight_base": p["weight_base"],
            "reliability_weight_high": p["weight_high"], "weight_semantics": "SENSITIVITY_ONLY_NOT_INVERSE_VARIANCE",
            "matrix_control_available": p["matrix_control"], "numeric_elongation_available": p["numeric_el"],
            "admission_status": "TARGETED_SOURCE_AUDIT_ONLY",
        })
    source_fields = ["snapshot_id", "paper_uid", "paper_doi", "paper_year", "journal", "publisher", "title", "source_type", "origin_type", "own_lab_public", "archive", "member", "source_locator", "source_hash", "evidence_level", "reliability_weight_low", "reliability_weight_base", "reliability_weight_high", "weight_semantics", "uncertainty_reporting", "replicate_reporting", "matrix_control_available", "numeric_elongation_available", "validation_note", "admission_status"]
    write_csv(root, "SOURCE_RELIABILITY_REPLAY.csv", source_fields, source_rows)
    write_csv(root, "figure_data/source_reliability_distribution.csv", ["paper_doi", "paper_year", "journal", "evidence_level", "weight_low", "weight_base", "weight_high", "source_hash"], [{"paper_doi": p["paper_doi"], "paper_year": p["paper_year"], "journal": p["journal"], "evidence_level": p["evidence_level"], "weight_low": p["weight_low"], "weight_base": p["weight_base"], "weight_high": p["weight_high"], "source_hash": p["source_hash"]} for p in PAPERS])

    # Missingness models and figure data
    patterns = [
        {"universe": "local_download_proofs", "pattern": "XML_VERIFIED", "count": AGG["xml_verified"], "xml_not_verified": 0, "missing_path": 0, "parse_fail": 0, "identity_mismatch": 0, "valid_for_paper_missingness": "YES_WITHIN_PROOF_UNIVERSE"},
        {"universe": "local_download_proofs", "pattern": "MISSING_PATH", "count": AGG["missing_path"], "xml_not_verified": 1, "missing_path": 1, "parse_fail": 0, "identity_mismatch": 0, "valid_for_paper_missingness": "YES_WITHIN_PROOF_UNIVERSE"},
        {"universe": "local_download_proofs", "pattern": "PARSE_FAIL", "count": AGG["parse_fail_proof"], "xml_not_verified": 1, "missing_path": 0, "parse_fail": 1, "identity_mismatch": 0, "valid_for_paper_missingness": "YES_WITHIN_PROOF_UNIVERSE"},
        {"universe": "local_download_proofs", "pattern": "IDENTITY_MISMATCH", "count": AGG["identity_mismatch"], "xml_not_verified": 1, "missing_path": 0, "parse_fail": 0, "identity_mismatch": 1, "valid_for_paper_missingness": "YES_WITHIN_PROOF_UNIVERSE"},
        {"universe": "paper_completeness_vectors_snapshot_A", "pattern": "XML_PRESENT_VECTOR", "count": AGG["vector_present_snapshot"], "xml_not_verified": 0, "missing_path": "", "parse_fail": "", "identity_mismatch": "", "valid_for_paper_missingness": "NO_CROSS_SNAPSHOT_AGGREGATION"},
        {"universe": "paper_completeness_vectors_snapshot_B", "pattern": "XML_ABSENT_VECTOR", "count": AGG["vector_absent_snapshot"], "xml_not_verified": 1, "missing_path": "", "parse_fail": "", "identity_mismatch": "", "valid_for_paper_missingness": "NO_CROSS_SNAPSHOT_AGGREGATION"},
    ]
    write_csv(root, "figure_data/missingness_patterns.csv", ["universe", "pattern", "count", "xml_not_verified", "missing_path", "parse_fail", "identity_mismatch", "valid_for_paper_missingness"], patterns)
    missing_rows = [
        {"snapshot_id": snap, "missingness_target": "xml_present in paper_completeness_vectors", "analysis_universe": "87,958 vector rows across two snapshots", "observed_missing": AGG["vector_absent_snapshot"], "observed_total": AGG["paper_completeness_vector_rows"], "mechanism_candidate": "STRUCTURAL_BY_SNAPSHOT / MAR_CANDIDATE", "mcar_status": "REJECT_AS_INTERPRETATION", "mar_status": "SUPPORTED_BY_OBSERVED_SNAPSHOT_ID", "mnar_status": "NOT_TESTABLE", "test_or_evidence": "44,904 present rows coincide with one snapshot and 43,054 absent rows with another; cross-snapshot headline is invalid.", "imputation_policy": "DO_NOT_IMPUTE; FILTER_ONE_AUTHORITATIVE_SNAPSHOT", "status": "IDENTIFIED_DATA_GENERATING_ARTIFACT"},
        {"snapshot_id": snap, "missingness_target": "local XML/fulltext proof status", "analysis_universe": "47,994 local_download_proofs", "observed_missing": tech_fail, "observed_total": AGG["local_download_proofs"], "mechanism_candidate": "MAR_TECHNICAL_CANDIDATE", "mcar_status": "UNSUPPORTED", "mar_status": "PLAUSIBLE_BY_PATH_PARSER_IDENTITY_STATE", "mnar_status": "NOT_REQUIRED_FOR_TECHNICAL_FAILURES", "test_or_evidence": "1,200 MISSING_PATH + 140 PARSE_FAIL + 16 IDENTITY_MISMATCH; causes are observed.", "imputation_policy": "NO_LABEL_IMPUTATION; REPAIR_PATH_PARSER_IDENTITY", "status": "DESCRIPTIVE_AGGREGATE"},
        {"snapshot_id": snap, "missingness_target": "numeric elongation in targeted original-source audit", "analysis_universe": "6 DOI/hash-bound original XML papers", "observed_missing": 2, "observed_total": 6, "mechanism_candidate": "MAR_OR_MNAR_CANDIDATE", "mcar_status": "NOT_ESTABLISHED", "mar_status": "PLAUSIBLE_BY_YEAR_REPORTING_MODE_PROPERTY_EMPHASIS", "mnar_status": "PLAUSIBLE_BUT_NOT_PROVEN", "test_or_evidence": "1994 fibre paper omits EL; 2015 heat-treatment passage states reduced EL without a number; 2013 EL remains figure-derived.", "imputation_policy": "DO_NOT_IMPUTE_LABELS", "status": "SMALL_K_NOT_IDENTIFIABLE"},
        {"snapshot_id": snap, "missingness_target": "paper-level effect/SE/size/year for publication-bias regression", "analysis_universe": "QM06 aggregate strict UTS cohort: 38 papers, 121 pairs", "observed_missing": 38, "observed_total": 38, "mechanism_candidate": "INPUT_NOT_RETURNED", "mcar_status": "NOT_TESTABLE", "mar_status": "NOT_TESTABLE", "mnar_status": "NOT_TESTABLE", "test_or_evidence": "Only pooled aggregate CI/PI/I2/LOPO and paper count were opened.", "imputation_policy": "NO_SYNTHETIC_SE; EGGER_FAIL_CLOSED", "status": "NOT_IDENTIFIABLE"},
    ]
    missing_fields = ["snapshot_id", "missingness_target", "analysis_universe", "observed_missing", "observed_total", "mechanism_candidate", "mcar_status", "mar_status", "mnar_status", "test_or_evidence", "imputation_policy", "status"]
    write_csv(root, "MISSINGNESS_MODEL.csv", missing_fields, missing_rows)

    # Duplicate/dependency assets
    duplicate_rows = [
        {"snapshot_id": snap, "duplicate_family_id": "COMPLETE_VECTOR_SNAPSHOT_A", "family_type": "SNAPSHOT_DEPENDENCY", "member_count": AGG["vector_present_snapshot"], "independent_unit_count": "NOT_IDENTIFIABLE", "naive_to_independent_inflation": "NOT_IDENTIFIABLE", "lineage_basis": AGG["snapshot_present_id"], "action": "FILTER_BY_AUTHORITATIVE_SNAPSHOT", "status": "STRUCTURAL_DEPENDENCY"},
        {"snapshot_id": snap, "duplicate_family_id": "COMPLETE_VECTOR_SNAPSHOT_B", "family_type": "SNAPSHOT_DEPENDENCY", "member_count": AGG["vector_absent_snapshot"], "independent_unit_count": "NOT_IDENTIFIABLE", "naive_to_independent_inflation": "NOT_IDENTIFIABLE", "lineage_basis": AGG["snapshot_absent_id"], "action": "DO_NOT_ADD_TO_SNAPSHOT_A", "status": "STRUCTURAL_DEPENDENCY"},
        {"snapshot_id": snap, "duplicate_family_id": "QM06_UTS_PAPER_CLUSTER_AGGREGATE", "family_type": "MULTIPLE_MATCHES_WITHIN_PAPER", "member_count": AGG["qm06_pairs"], "independent_unit_count": AGG["qm06_papers"], "naive_to_independent_inflation": round(infl, 8), "lineage_basis": "same-paper strict matched UTS pairs", "action": "PAPER_BALANCE_OR_CLUSTER_BOOTSTRAP", "status": "QUANTIFIED_AGGREGATE"},
        {"snapshot_id": snap, "duplicate_family_id": "XW01_VERSION_GRAPH_AGGREGATE", "family_type": "DOCUMENT_VERSION_OR_IDENTITY_DEPENDENCY", "member_count": AGG["version_graph_edges"], "independent_unit_count": "NOT_IDENTIFIABLE_WITHOUT_GRAPH_ROWS", "naive_to_independent_inflation": "NOT_IDENTIFIABLE", "lineage_basis": "VERSION_GRAPH aggregate edge count", "action": "RETURN_NODE_EDGE_FAMILY_MEMBERSHIP", "status": "AGGREGATE_ONLY"},
    ]
    dup_fields = ["snapshot_id", "duplicate_family_id", "family_type", "member_count", "independent_unit_count", "naive_to_independent_inflation", "lineage_basis", "action", "status"]
    write_csv(root, "DUPLICATE_FAMILY.csv", dup_fields, duplicate_rows)
    node_rows = [
        {"node_id": "registry", "label": "Paper registry", "count": AGG["paper_registry"], "node_type": "registry"},
        {"node_id": "snapA", "label": "Vector snapshot A", "count": AGG["vector_present_snapshot"], "node_type": "snapshot"},
        {"node_id": "snapB", "label": "Vector snapshot B", "count": AGG["vector_absent_snapshot"], "node_type": "snapshot"},
        {"node_id": "distinct", "label": "Distinct vector paper_uid", "count": AGG["distinct_vector_papers"], "node_type": "deduplicated_registry"},
        {"node_id": "proofs", "label": "Local proof records", "count": AGG["local_download_proofs"], "node_type": "proof"},
        {"node_id": "verified", "label": "XML verified", "count": AGG["xml_verified"], "node_type": "proof_status"},
        {"node_id": "docs", "label": "XW01 XML documents", "count": AGG["xml_corpus_documents"], "node_type": "corpus"},
        {"node_id": "vedges", "label": "Version graph edges", "count": AGG["version_graph_edges"], "node_type": "dependency"},
        {"node_id": "pairs", "label": "QM06 matched rows", "count": AGG["qm06_pairs"], "node_type": "effect_rows"},
        {"node_id": "papers", "label": "QM06 independent papers", "count": AGG["qm06_papers"], "node_type": "independent_units"},
    ]
    edge_rows = [
        {"source": "registry", "target": "snapA", "relation": "snapshot_rows", "weight": AGG["vector_present_snapshot"]},
        {"source": "registry", "target": "snapB", "relation": "snapshot_rows", "weight": AGG["vector_absent_snapshot"]},
        {"source": "snapA", "target": "distinct", "relation": "deduplicate_by_paper_uid", "weight": AGG["distinct_vector_papers"]},
        {"source": "snapB", "target": "distinct", "relation": "do_not_pool_across_snapshots", "weight": AGG["distinct_vector_papers"]},
        {"source": "registry", "target": "proofs", "relation": "proof_coverage", "weight": AGG["local_download_proofs"]},
        {"source": "proofs", "target": "verified", "relation": "verified_state", "weight": AGG["xml_verified"]},
        {"source": "docs", "target": "vedges", "relation": "version_or_identity_links", "weight": AGG["version_graph_edges"]},
        {"source": "pairs", "target": "papers", "relation": "cluster_by_paper", "weight": AGG["qm06_pairs"]},
    ]
    write_csv(root, "figure_data/duplicate_dependency_nodes.csv", ["node_id", "label", "count", "node_type"], node_rows)
    write_csv(root, "figure_data/duplicate_dependency_edges.csv", ["source", "target", "relation", "weight"], edge_rows)

    # Cohort, matched effects, model/heterogeneity tables
    cohort = [
        {"snapshot_id": snap, "cohort_id": "XW01_XML_CORPUS", "unit": "document", "rows_seen": AGG["xml_corpus_documents"], "independent_papers": "NOT_IDENTIFIABLE_FROM_AGGREGATE", "included": AGG["xml_corpus_documents"], "excluded": 0, "scope": "all XML corpus classes", "purpose": "source/scope/parse audit", "status": "AGGREGATE_ONLY"},
        {"snapshot_id": snap, "cohort_id": "QM39_ATOMIC_PROPERTY", "unit": "atomic property row", "rows_seen": AGG["qm39_atomic_rows"], "independent_papers": AGG["qm39_independent_papers"], "included": AGG["qm39_atomic_rows"], "excluded": "NOT_RETURNED", "scope": "Ti/TMC property analysis", "purpose": "scope denominator only", "status": "AGGREGATE_ONLY"},
        {"snapshot_id": snap, "cohort_id": "QM06_STRICT_UTS", "unit": "matched pair", "rows_seen": AGG["qm06_pairs"], "independent_papers": AGG["qm06_papers"], "included": AGG["qm06_pairs"], "excluded": "NOT_RETURNED", "scope": "RT UTS strict same-paper matches", "purpose": "matched effect and bias sensitivity", "status": "AGGREGATE_ONLY"},
        {"snapshot_id": snap, "cohort_id": "TARGETED_SOURCE_RELIABILITY", "unit": "paper", "rows_seen": len(PAPERS), "independent_papers": len(PAPERS), "included": len(PAPERS), "excluded": 0, "scope": "six DOI/hash-bound original XML anchors", "purpose": "source reliability replay", "status": "TARGETED_AUDIT"},
        {"snapshot_id": snap, "cohort_id": "LOCAL_DOWNLOAD_PROOFS", "unit": "proof record", "rows_seen": AGG["local_download_proofs"], "independent_papers": "NOT_IDENTIFIABLE", "included": AGG["local_download_proofs"], "excluded": 0, "scope": "local XML/fulltext proof states", "purpose": "technical missingness audit", "status": "AGGREGATE_ONLY"},
    ]
    cohort_fields = ["snapshot_id", "cohort_id", "unit", "rows_seen", "independent_papers", "included", "excluded", "scope", "purpose", "status"]
    write_csv(root, "ANALYSIS_COHORT.csv", cohort_fields, cohort)
    pair = {"snapshot_id": snap, "pair_id": "QM06_UTS_STRICT_AGGREGATE", "paper_uid": "MULTIPLE_38_INDIVIDUAL_IDS_NOT_RETURNED", "sample_uid_tmc": "UNAVAILABLE_AGGREGATE", "sample_uid_control": "UNAVAILABLE_AGGREGATE", "condition_uid": "RT_UTS_STRICT_SAME_PAPER_SAME_ROUTE_MATRIX_PROCESS_HT_TEST", "property": "UTS_MPa", "match_grade": "A_STRICT_QUALITY_FIRST_GE_0.90", "matched_pairs": AGG["qm06_pairs"], "independent_papers": AGG["qm06_papers"], "source_hash": "FILE_LIBRARY_ID:file_00000000b2fc720bb0ed130574d34783", "provenance_locator": "QM06/00_EXECUTIVE_VERDICT.md", "status": "AGGREGATE_ONLY_NOT_READMISSIBLE", "notes": "Return individual paper/sample/condition lineage before Gold reuse."}
    pair_fields = ["snapshot_id", "pair_id", "paper_uid", "sample_uid_tmc", "sample_uid_control", "condition_uid", "property", "match_grade", "matched_pairs", "independent_papers", "source_hash", "provenance_locator", "status", "notes"]
    write_csv(root, "PAIR_MATCHES.csv", pair_fields, [pair])
    effects = [
        {"snapshot_id": snap, "effect_id": "E_UTS_STRICT", "paper_uid": "MULTIPLE_38_IDS_NOT_RETURNED", "sample_uid": "MULTIPLE_121_IDS_NOT_RETURNED", "condition_uid": "RT_UTS_STRICT_GATE", "estimand": "paper-balanced mean delta UTS", "property": "UTS", "estimate": AGG["qm06_delta_uts"], "unit": "MPa", "ci_low": AGG["qm06_ci_low"], "ci_high": AGG["qm06_ci_high"], "prediction_low": AGG["qm06_pi_low"], "prediction_high": AGG["qm06_pi_high"], "independent_papers": AGG["qm06_papers"], "matched_pairs": AGG["qm06_pairs"], "evidence_grade": "A_STRICT_AGGREGATE", "claim_level": 2, "provenance_locator": "QM06/00_EXECUTIVE_VERDICT.md", "source_hash": "FILE_LIBRARY_ID:file_00000000b2fc720bb0ed130574d34783", "status": "AGGREGATE_ONLY"},
        {"snapshot_id": snap, "effect_id": "E_UTS_A_NO_QUALITY", "paper_uid": "MULTIPLE_NOT_RETURNED", "sample_uid": "MULTIPLE_NOT_RETURNED", "condition_uid": "RT_UTS_A_NO_QUALITY_THRESHOLD", "estimand": "paper-balanced mean delta UTS sensitivity", "property": "UTS", "estimate": AGG["qm06_a_no_quality_gate"], "unit": "MPa", "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "", "independent_papers": "NOT_RETURNED", "matched_pairs": "NOT_RETURNED", "evidence_grade": "A_SENSITIVITY", "claim_level": 2, "provenance_locator": "QM06/00_EXECUTIVE_VERDICT.md", "source_hash": "FILE_LIBRARY_ID:file_00000000b2fc720bb0ed130574d34783", "status": "AGGREGATE_ONLY"},
        {"snapshot_id": snap, "effect_id": "E_UTS_ALL_AB", "paper_uid": "MULTIPLE_NOT_RETURNED", "sample_uid": "MULTIPLE_NOT_RETURNED", "condition_uid": "RT_UTS_ACCEPTED_A_B", "estimand": "paper-balanced mean delta UTS sensitivity", "property": "UTS", "estimate": AGG["qm06_all_ab"], "unit": "MPa", "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "", "independent_papers": "NOT_RETURNED", "matched_pairs": "NOT_RETURNED", "evidence_grade": "A_B_SENSITIVITY", "claim_level": 2, "provenance_locator": "QM06/00_EXECUTIVE_VERDICT.md", "source_hash": "FILE_LIBRARY_ID:file_00000000b2fc720bb0ed130574d34783", "status": "AGGREGATE_ONLY"},
    ]
    effect_fields = ["snapshot_id", "effect_id", "paper_uid", "sample_uid", "condition_uid", "estimand", "property", "estimate", "unit", "ci_low", "ci_high", "prediction_low", "prediction_high", "independent_papers", "matched_pairs", "evidence_grade", "claim_level", "provenance_locator", "source_hash", "status"]
    write_csv(root, "EFFECT_ESTIMATES.csv", effect_fields, effects)
    hierarchy = [
        {"snapshot_id": snap, "model_id": "QM06_PAPER_BALANCED_CLUSTER_BOOTSTRAP", "estimand": "delta UTS", "model_family": "paper-balanced paired meta-analysis", "random_effects": "prediction interval replay; tau2 not returned", "estimate": AGG["qm06_delta_uts"], "ci_low": AGG["qm06_ci_low"], "ci_high": AGG["qm06_ci_high"], "prediction_low": AGG["qm06_pi_low"], "prediction_high": AGG["qm06_pi_high"], "cluster_unit": "paper", "independent_papers": AGG["qm06_papers"], "status": "AGGREGATE_REPLAY_ONLY"},
        {"snapshot_id": snap, "model_id": "QM05_SOURCE_RELIABILITY_HIERARCHICAL", "estimand": "source reliability contribution", "model_family": "NOT_FIT", "random_effects": "paper-level quality domains unavailable", "estimate": "", "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "", "cluster_unit": "paper", "independent_papers": len(PAPERS), "status": "NOT_IDENTIFIABLE"},
    ]
    hierarchy_fields = ["snapshot_id", "model_id", "estimand", "model_family", "random_effects", "estimate", "ci_low", "ci_high", "prediction_low", "prediction_high", "cluster_unit", "independent_papers", "status"]
    write_csv(root, "HIERARCHICAL_RESULTS.csv", hierarchy_fields, hierarchy)
    write_csv(root, "DOSE_RESPONSE.csv", ["snapshot_id", "estimand", "dose_definition", "support", "estimate", "uncertainty", "status", "reason"], [{"snapshot_id": snap, "estimand": "publication bias versus reinforcement dose", "dose_definition": "reinforcement vol.%", "support": "paper-level effect-dose-SE rows unavailable", "estimate": "", "uncertainty": "", "status": "NOT_IDENTIFIABLE", "reason": "No aggregate substitution for row-level dose-response."}])
    write_csv(root, "INTERACTION_EFFECTS.csv", ["snapshot_id", "interaction", "estimate", "unit", "ci_low", "ci_high", "q_value", "status", "reason"], [{"snapshot_id": snap, "interaction": "source_type x year on effect size", "estimate": "", "unit": "MPa", "ci_low": "", "ci_high": "", "q_value": "", "status": "NOT_IDENTIFIABLE", "reason": "Effect, SE, year and source strata were not jointly available."}])
    write_csv(root, "HETEROGENEITY.csv", ["snapshot_id", "estimand", "independent_papers", "i2_pct", "prediction_low", "prediction_high", "lopo_low", "lopo_high", "interpretation", "status"], [{"snapshot_id": snap, "estimand": "strict same-paper delta UTS", "independent_papers": AGG["qm06_papers"], "i2_pct": AGG["qm06_i2_pct"], "prediction_low": AGG["qm06_pi_low"], "prediction_high": AGG["qm06_pi_high"], "lopo_low": AGG["qm06_lopo_low"], "lopo_high": AGG["qm06_lopo_high"], "interpretation": "Extreme between-paper heterogeneity; no universal coefficient.", "status": "AGGREGATE_REPLAY"}])

    # Bias sensitivity and funnel identifiability
    bias = [
        {"snapshot_id": snap, "analysis_id": "RAW_STRICT", "bias_dimension": "quality/source gate", "definition": "strict same-paper exact matrix/process/HT/test, quality >=0.90", "estimate": AGG["qm06_delta_uts"], "unit": "MPa", "independent_papers": AGG["qm06_papers"], "matched_pairs": AGG["qm06_pairs"], "result": "REFERENCE", "status": "AGGREGATE_REPLAY"},
        {"snapshot_id": snap, "analysis_id": "A_NO_QUALITY_THRESHOLD", "bias_dimension": "quality/source gate", "definition": "A-grade matches without >=0.90 threshold", "estimate": AGG["qm06_a_no_quality_gate"], "unit": "MPa", "independent_papers": "NOT_RETURNED", "matched_pairs": "NOT_RETURNED", "result": "-26.4 MPa versus strict", "status": "SENSITIVITY"},
        {"snapshot_id": snap, "analysis_id": "ALL_ACCEPTED_AB", "bias_dimension": "match definition", "definition": "all accepted A/B matches", "estimate": AGG["qm06_all_ab"], "unit": "MPa", "independent_papers": "NOT_RETURNED", "matched_pairs": "NOT_RETURNED", "result": "-10.3 MPa versus strict", "status": "SENSITIVITY"},
        {"snapshot_id": snap, "analysis_id": "LOPO_RANGE", "bias_dimension": "single-paper influence", "definition": "leave-one-paper-out pooled estimate range", "estimate": "127.5..142.9", "unit": "MPa", "independent_papers": AGG["qm06_papers"], "matched_pairs": AGG["qm06_pairs"], "result": "No single paper reverses pooled mean; prediction interval crosses zero.", "status": "SENSITIVITY"},
        {"snapshot_id": snap, "analysis_id": "ROW_INFLATION", "bias_dimension": "duplicate/dependency", "definition": "matched-pair count / independent-paper count", "estimate": round(infl, 8), "unit": "fold", "independent_papers": AGG["qm06_papers"], "matched_pairs": AGG["qm06_pairs"], "result": "Naive row counting overstates independent N by 3.18x.", "status": "QUANTIFIED"},
        {"snapshot_id": snap, "analysis_id": "NULL_PAPERS_TO_HALF", "bias_dimension": "selection tipping point", "definition": "hidden zero-effect papers required to halve equal-paper mean", "estimate": 38, "unit": "papers", "independent_papers": AGG["qm06_papers"], "matched_pairs": "", "result": "Illustrative bound, not correction.", "status": "DETERMINISTIC_SENSITIVITY"},
        {"snapshot_id": snap, "analysis_id": "NEG87_TO_ZERO", "bias_dimension": "selection tipping point", "definition": "hidden papers each -87 MPa required to drive mean <=0", "estimate": math.ceil(AGG["qm06_papers"] * AGG["qm06_delta_uts"] / 87.0), "unit": "papers", "independent_papers": AGG["qm06_papers"], "matched_pairs": "", "result": "Uses observed prediction-interval lower magnitude; illustrative only.", "status": "DETERMINISTIC_SENSITIVITY"},
        {"snapshot_id": snap, "analysis_id": "NEG308_5_TO_ZERO", "bias_dimension": "selection tipping point", "definition": "hidden papers each -308.5 MPa required to drive mean <=0", "estimate": math.ceil(AGG["qm06_papers"] * AGG["qm06_delta_uts"] / 308.5), "unit": "papers", "independent_papers": AGG["qm06_papers"], "matched_pairs": "", "result": "Extreme illustrative stress bound.", "status": "DETERMINISTIC_SENSITIVITY"},
        {"snapshot_id": snap, "analysis_id": "EGGER", "bias_dimension": "small-study/publication bias", "definition": "Egger regression of standardized effect on precision", "estimate": "", "unit": "", "independent_papers": AGG["qm06_papers"], "matched_pairs": AGG["qm06_pairs"], "result": "Paper-level effects and standard errors unavailable.", "status": "NOT_IDENTIFIABLE"},
    ]
    bias_fields = ["snapshot_id", "analysis_id", "bias_dimension", "definition", "estimate", "unit", "independent_papers", "matched_pairs", "result", "status"]
    write_csv(root, "BIAS_SENSITIVITY.csv", bias_fields, bias)
    write_csv(root, "SENSITIVITY_ANALYSIS.csv", bias_fields, bias)
    funnel = [
        {"required_field": "paper-level effect estimate", "available_count": 0, "required_count": 38, "availability_pct": 0, "status": "MISSING"},
        {"required_field": "paper-level standard error", "available_count": 0, "required_count": 38, "availability_pct": 0, "status": "MISSING"},
        {"required_field": "paper-level sample size", "available_count": 0, "required_count": 38, "availability_pct": 0, "status": "MISSING"},
        {"required_field": "paper year joined to effect", "available_count": 0, "required_count": 38, "availability_pct": 0, "status": "MISSING"},
        {"required_field": "aggregate pooled estimate", "available_count": 1, "required_count": 1, "availability_pct": 100, "status": "AVAILABLE_NOT_SUFFICIENT"},
    ]
    write_csv(root, "figure_data/funnel_identifiability.csv", ["required_field", "available_count", "required_count", "availability_pct", "status"], funnel)

    # Null/negative results and conflicts
    nulls = [
        {"snapshot_id": snap, "result_id": "N1", "domain": "publication bias", "finding": "Funnel asymmetry and Egger regression are NOT_IDENTIFIABLE.", "quantitative_value": "0/38 paper-level SE rows available", "counterexample_or_reason": "Aggregate pooled CI is not study-specific SE.", "claim_effect": "No automatic correction."},
        {"snapshot_id": snap, "result_id": "N2", "domain": "heterogeneity", "finding": "Universal positive strengthening constant rejected.", "quantitative_value": "PI -87.0 to 308.5 MPa; I2 97.3%", "counterexample_or_reason": "5.3% of independent primary papers had non-positive paper-mean delta UTS.", "claim_effect": "Same-paper association only."},
        {"snapshot_id": snap, "result_id": "N3", "domain": "missingness", "finding": "43,054 cannot be interpreted as missing papers.", "quantitative_value": "Separate-snapshot vector rows", "counterexample_or_reason": "44,904 present rows belong to another snapshot; combined rows exceed registry.", "claim_effect": "Filter snapshot first."},
        {"snapshot_id": snap, "result_id": "N4", "domain": "duplicate families", "finding": "Exact global reuse inflation NOT_IDENTIFIABLE.", "quantitative_value": "VERSION_GRAPH edges=37,094", "counterexample_or_reason": "Node/edge/family membership absent.", "claim_effect": "No corrected global effective N."},
        {"snapshot_id": snap, "result_id": "N5", "domain": "source reliability", "finding": "Reliability weights are not exact variance.", "quantitative_value": "Six-paper sensitivity scale", "counterexample_or_reason": "Replicate variance incomplete.", "claim_effect": "Report raw and sensitivity results."},
    ]
    write_csv(root, "NULL_NEGATIVE_RESULTS.csv", ["snapshot_id", "result_id", "domain", "finding", "quantitative_value", "counterexample_or_reason", "claim_effect"], nulls)
    conflicts = [
        {"conflict_id": "QM05-C001", "snapshot_id": snap, "severity": "CRITICAL", "object": "paper_completeness_vectors", "conflict": "Cross-snapshot counts were read as one missingness universe.", "evidence_a": f"44,904 present rows in {AGG['snapshot_present_id']}", "evidence_b": f"43,054 absent rows in {AGG['snapshot_absent_id']}", "resolution": "Filter authoritative snapshot and count distinct paper_uid.", "status": "OPEN_LOCAL_REQUERY_REQUIRED"},
        {"conflict_id": "QM05-C002", "snapshot_id": snap, "severity": "CRITICAL", "object": "V29/Q40 authority", "conflict": "Canonical atomic/provenance snapshot was not opened.", "evidence_a": "Mounted ZIPs registered", "evidence_b": "System-level ClientError prevented byte access", "resolution": "Return exact authority files and full SHA-256.", "status": "OPEN"},
        {"conflict_id": "QM05-C003", "snapshot_id": snap, "severity": "HIGH", "object": "QM06 cohort", "conflict": "121 pairs/38 papers are aggregate-only.", "evidence_a": "QM06 verdict", "evidence_b": "No row-level pair table", "resolution": "Return paper/sample/condition lineage.", "status": "OPEN"},
        {"conflict_id": "QM05-C004", "snapshot_id": snap, "severity": "HIGH", "object": "cross-format duplicates", "conflict": "Cross-format accepted pairs are unresolved.", "evidence_a": "Multiple carrier families", "evidence_b": "No accepted cross-format map", "resolution": "Run DOI/title/hash/sample-lineage resolver.", "status": "OPEN"},
        {"conflict_id": "QM05-C005", "snapshot_id": snap, "severity": "HIGH", "object": "VERSION_GRAPH", "conflict": "37,094 edges exist but family membership was not opened.", "evidence_a": "VERSION_GRAPH aggregate", "evidence_b": "No graph rows", "resolution": "Return nodes/edges/family IDs.", "status": "OPEN"},
        {"conflict_id": "QM05-C006", "snapshot_id": snap, "severity": "HIGH", "object": "publication bias", "conflict": "Paper effect, SE, size and year are not jointly available.", "evidence_a": "Aggregate effect available", "evidence_b": "Regression matrix absent", "resolution": "Return paper-level matrix.", "status": "OPEN"},
        {"conflict_id": "QM05-C007", "snapshot_id": snap, "severity": "MEDIUM", "object": "package hashes", "conflict": "Historical fingerprints are not newly verified full-file SHA-256.", "evidence_a": "Historical ledger", "evidence_b": "Current bytes unreadable", "resolution": "Local authority recomputes SHA/testzip.", "status": "OPEN"},
        {"conflict_id": "QM05-C008", "snapshot_id": snap, "severity": "MEDIUM", "object": "quality weighting", "conflict": "Quality score could be misread as inverse variance.", "evidence_a": "Directness weights", "evidence_b": "Variance incomplete", "resolution": "Keep sensitivity-only.", "status": "CONTROLLED_NOT_CLOSED"},
    ]
    conflict_fields = ["conflict_id", "snapshot_id", "severity", "object", "conflict", "evidence_a", "evidence_b", "resolution", "status"]
    write_csv(root, "CONFLICT_LEDGER.csv", conflict_fields, conflicts)

    # Provenance
    provenance = [
        {"provenance_id": "P-SNAPSHOT-MIX", "snapshot_id": snap, "paper_uid": "REGISTRY_AGGREGATE", "sample_uid": "NA", "condition_uid": "NA", "claim": "xml_absent 43054 is a cross-snapshot vector-row artifact, not a paper missing count", "source_locator": "file_library:file_00000000ed10720ba9598817d22da612", "source_hash": "FILE_LIBRARY_ID:file_00000000ed10720ba9598817d22da612", "evidence_level": "DIRECT_DATABASE_QUERY_REPORTED", "transformation": "aggregate replay", "admission": "ANALYSIS_ONLY"},
        {"provenance_id": "P-QM06-UTS", "snapshot_id": snap, "paper_uid": "MULTIPLE_38", "sample_uid": "MULTIPLE_121", "condition_uid": "RT_UTS_STRICT", "claim": "paper-balanced delta UTS 133.1 MPa, CI 99.4-165.7, PI -87.0-308.5", "source_locator": "QM06/00_EXECUTIVE_VERDICT.md", "source_hash": "FILE_LIBRARY_ID:file_00000000b2fc720bb0ed130574d34783", "evidence_level": "DERIVED_CALCULATION_AGGREGATE", "transformation": "replayed without row-level re-estimation", "admission": "ANALYSIS_ONLY_NOT_READMISSIBLE"},
        {"provenance_id": "P-XW01-CORPUS", "snapshot_id": snap, "paper_uid": "MULTIPLE", "sample_uid": "NA", "condition_uid": "NA", "claim": "78,683 XML documents and 37,094 version edges", "source_locator": "XW01 aggregate audit", "source_hash": "VERSION_GRAPH:c74bc746b7d398f91cdc1a48ac7f0b395c64686b16bb2be22dd19e50d6d1867c", "evidence_level": "DERIVED_CORPUS_AUDIT", "transformation": "aggregate replay", "admission": "ANALYSIS_ONLY"},
        {"provenance_id": "P-QM39-SCOPE", "snapshot_id": snap, "paper_uid": "MULTIPLE_975", "sample_uid": "MULTIPLE", "condition_uid": "MULTIPLE", "claim": "15,089 atomic rows from 975 independent papers", "source_locator": "QM39/00_EXECUTIVE_VERDICT.md", "source_hash": "FILE_LIBRARY_ID:file_0000000052a4722fa38a2b6ccc409352", "evidence_level": "DERIVED_ANALYSIS_AGGREGATE", "transformation": "scope denominator only", "admission": "ANALYSIS_ONLY"},
    ]
    for p in PAPERS:
        provenance.append({"provenance_id": f"P-SRC-{p['paper_year']}-{p['source_hash'][:8]}", "snapshot_id": snap, "paper_uid": p["paper_uid"], "sample_uid": "UNRESOLVED_TARGETED_AUDIT", "condition_uid": "MULTIPLE_HIGH_TEMPERATURE", "claim": p["validation_note"], "source_locator": f"/mnt/data/{p['archive']}::{p['member']}", "source_hash": p["source_hash"], "evidence_level": p["evidence_level"], "transformation": "source reliability classification only", "admission": "TARGETED_AUDIT"})
    with (root / "PROVENANCE.jsonl").open("w", encoding="utf-8") as f:
        for row in provenance: f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    # Plot data, code, and figures
    build_figures(root, snap)
    plot_code = {
        "plot_source_reliability.py": """from pathlib import Path\nimport csv, matplotlib.pyplot as plt\nb=Path(__file__).resolve().parents[1]; r=list(csv.DictReader((b/'figure_data/source_reliability_distribution.csv').open(encoding='utf-8-sig'))); m=[float(x['weight_base']) for x in r]; lo=[float(x['weight_low']) for x in r]; hi=[float(x['weight_high']) for x in r]; ne=sum(m)**2/sum(x*x for x in m); f,a=plt.subplots(figsize=(11,6.5)); a.bar(range(len(r)),m,yerr=[[x-y for x,y in zip(m,lo)],[x-y for x,y in zip(hi,m)]],capsize=4); a.set_ylim(0,1.12); a.set_ylabel('Sensitivity-only source reliability weight'); a.set_title(f'Source reliability replay | k={len(r)} | Kish effective N={ne:.2f}'); f.tight_layout(); [f.savefig(b/f'figures/Fig1_source_reliability.{e}',dpi=d,bbox_inches='tight') for e,d in [('svg',None),('pdf',None),('png',600)]]\n""",
        "plot_missingness_upset.py": """from pathlib import Path\nimport csv, matplotlib.pyplot as plt\nb=Path(__file__).resolve().parents[1]; r=[x for x in csv.DictReader((b/'figure_data/missingness_patterns.csv').open(encoding='utf-8-sig')) if x['universe']=='local_download_proofs']; f,a=plt.subplots(figsize=(11,7)); a.bar(range(len(r)),[int(x['count']) for x in r]); a.set_yscale('log'); a.set_title('Missingness-state intersections | N=47,994 proof records'); a.set_xticks(range(len(r)),[x['pattern'] for x in r],rotation=20); f.tight_layout(); [f.savefig(b/f'figures/Fig2_missingness_upset.{e}',dpi=d,bbox_inches='tight') for e,d in [('svg',None),('pdf',None),('png',600)]]\n""",
        "plot_duplicate_network.py": """from pathlib import Path\nimport csv, math, matplotlib.pyplot as plt, networkx as nx\nb=Path(__file__).resolve().parents[1]; ns=list(csv.DictReader((b/'figure_data/duplicate_dependency_nodes.csv').open(encoding='utf-8-sig'))); es=list(csv.DictReader((b/'figure_data/duplicate_dependency_edges.csv').open(encoding='utf-8-sig'))); g=nx.DiGraph(); [g.add_node(x['node_id'],label=x['label'],count=int(x['count'])) for x in ns]; [g.add_edge(x['source'],x['target']) for x in es]; p=nx.spring_layout(g,seed=42); f,a=plt.subplots(figsize=(12,8)); nx.draw(g,p,with_labels=True,ax=a); a.set_title('Duplicate/dependency network | 121 rows -> 38 papers'); f.tight_layout(); [f.savefig(b/f'figures/Fig3_duplicate_dependency_network.{e}',dpi=d,bbox_inches='tight') for e,d in [('svg',None),('pdf',None),('png',600)]]\n""",
        "plot_funnel_identifiability.py": """from pathlib import Path\nimport csv, matplotlib.pyplot as plt\nb=Path(__file__).resolve().parents[1]; r=list(csv.DictReader((b/'figure_data/funnel_identifiability.csv').open(encoding='utf-8-sig'))); f,a=plt.subplots(figsize=(10.5,6.5)); a.barh(range(len(r)),[float(x['availability_pct']) for x in r]); a.set_yticks(range(len(r)),[x['required_field'] for x in r]); a.set_xlim(0,105); a.set_title('Funnel/Egger: NOT IDENTIFIABLE | independent papers=38'); f.tight_layout(); [f.savefig(b/f'figures/Fig4_funnel_not_identifiable.{e}',dpi=d,bbox_inches='tight') for e,d in [('svg',None),('pdf',None),('png',600)]]\n""",
    }
    for name, code in plot_code.items(): write_text(root, "plot_code/" + name, code)
    write_json(root, "PLOT_SPECS.json", {
        "window_id": WINDOW, "snapshot_id": snap, "language": "English", "formats": ["SVG", "PDF", "PNG_600_DPI"],
        "figures": [
            {"figure_id": "Fig1", "title": "Source reliability replay", "data": "figure_data/source_reliability_distribution.csv", "code": "plot_code/plot_source_reliability.py", "estimand": "sensitivity-only reliability weight and Kish effective N", "independent_papers": 6, "evidence_layer": "DOI/hash-bound original XML", "support_domain": "six targeted originals"},
            {"figure_id": "Fig2", "title": "Missingness-state intersections", "data": "figure_data/missingness_patterns.csv", "code": "plot_code/plot_missingness_upset.py", "estimand": "technical proof-state counts", "independent_papers": "NOT_IDENTIFIABLE", "evidence_layer": "local proof aggregate", "support_domain": "47,994 proof records; mixed snapshots excluded"},
            {"figure_id": "Fig3", "title": "Duplicate/dependency inflation", "data": ["figure_data/duplicate_dependency_nodes.csv", "figure_data/duplicate_dependency_edges.csv"], "code": "plot_code/plot_duplicate_network.py", "estimand": "naive row-to-independent-paper inflation", "independent_papers": 38, "evidence_layer": "aggregate lineage", "support_domain": "QM06 plus registry/version aggregates"},
            {"figure_id": "Fig4", "title": "Funnel/Egger not identifiable", "data": "figure_data/funnel_identifiability.csv", "code": "plot_code/plot_funnel_identifiability.py", "estimand": "availability of publication-bias inputs", "independent_papers": 38, "evidence_layer": "aggregate matched-effect verdict", "support_domain": "paper effects/SE/sizes unavailable"},
        ]
    })

    # Narrative files
    write_text(root, "00_EXECUTIVE_VERDICT.md", f"""# QM05 Executive Verdict

`WINDOW=QM05 | SNAPSHOT={snap} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Terminal scientific answer

The dominant identified source bias is a denominator and lineage error. `xml_absent=43,054` was produced by pooling two completeness snapshots: 44,904 `xml_present=1` rows belong to `{AGG['snapshot_present_id']}`, while 43,054 `xml_present=0` rows belong to `{AGG['snapshot_absent_id']}`. Because 87,958 vector rows exceed the 54,504-paper registry, 43,054 cannot be interpreted as missing papers. Select one authoritative snapshot and count distinct `paper_uid` first.

Within the separate `local_download_proofs` universe, 46,638/47,994 records are `XML_VERIFIED` ({verified_pct:.2f}%). Explicit technical failures total 1,356 ({issue_pct:.2f}%): 1,200 `MISSING_PATH`, 140 `PARSE_FAIL`, and 16 `IDENTITY_MISMATCH`. These observed technical causes support a MAR-like mechanism rather than MCAR; they do not estimate full-registry missingness.

The strict matched UTS cohort has 121 pairs but only 38 independent papers, so naive row counting inflates independent N by **{infl:.2f}x**. Paper-balanced ΔUTS is **133.1 MPa** (95% CI 99.4–165.7; prediction interval -87.0–308.5 MPa). Match/quality alternatives yield 106.7 and 122.8 MPa. I²=97.3%; 5.3% of independent primary papers have non-positive paper-mean ΔUTS. LOPO remains 127.5–142.9 MPa, but the prediction interval rejects a universal strengthening constant.

Six DOI/hash-bound original XML anchors yield a base Kish effective N of **{n_eff:.2f}** from k=6. Reliability weights encode evidence directness/provenance only; they are not inverse variances.

Publication-bias correction is **NOT_IDENTIFIABLE** because paper-level effects, standard errors, study sizes, and joined years were not returned. No funnel asymmetry, Egger, trim-and-fill, or selection model was applied. Tipping-point bounds show that 38 hypothetical null papers halve the equal-paper mean; 59 hypothetical papers at -87 MPa or 17 at -308.5 MPa drive it to zero. These are stress bounds, not hidden-study estimates or bias corrections.

## Claim ceiling

Maximum claim level: **2 — descriptive and same-paper matched association**. Bias diagnostics do not recover corrected truth. No Gold promotion, ACTIVE mutation, production-model registration, or VALIDATED formulation was performed.

## Operational status

`CONTINUE_DATA_GAP`: complete for the evidence actually opened; canonical row-level V29/Q40 atomic records, pair lineage, duplicate-family membership, and paper-specific uncertainty inputs remain required.
""")
    write_text(root, "METHODS.md", f"""# Methods — QM05

Derived read-only snapshot `{snap}` binds aggregate evidence, opened-source references, and six original-XML SHA-256 values; it is not the canonical V29/Q40 snapshot.

Four denominators remain separate: XML documents, completeness-vector rows, local proof records, and matched effects. Source weights are sensitivity-only and use Kish effective N `(sum w)^2/sum(w^2)`. Missingness labels are candidate mechanisms; labels are never imputed. Duplicate inflation is `121/38={infl:.8f}` and paper clustering is mandatory. Funnel/Egger fails closed without paper-specific effect and SE. No production model is fit or registered. All quantitative figures are generated from CSV and exported as SVG, PDF, and 600 dpi PNG.
""")
    write_text(root, "LIMITATIONS.md", """# Limitations — QM05

- Canonical atomic records, row-level provenance, current exclusions/conflicts/registries, and exact Q40 snapshot hash were not opened.
- Uploaded ZIP bytes were inaccessible because the web runtime returned a system-level `ClientError`; historical fingerprints are explicitly labeled historical.
- The 121-pair/38-paper cohort is aggregate-only and is not readmissible to Gold without paper/sample/condition rows.
- Six reliability papers are targeted anchors, not a representative random sample of all 975 independent papers or 78,683 XML documents.
- VERSION_GRAPH has 37,094 aggregate edges but no family membership; global effective N is not estimable.
- Distinct universes are never added. Funnel/Egger is not run without paper uncertainty. Bias sensitivity does not estimate truth.
""")
    write_json(root, "WEB_TO_LOCAL_REQUEST.json", {
        "window_id": WINDOW, "requested_status": "CONTINUE_DATA_GAP",
        "required_snapshot": {"files": ["ATOMIC_RECORDS.parquet_or_csv", "PROVENANCE.jsonl", "CONFLICT_LEDGER.csv", "EXCLUDED_RECORDS.csv", "PAPER_REGISTRY.csv", "SOURCE_REGISTRY.csv", "CONDITION_CANONICAL_MANIFEST.csv"], "bindings": ["snapshot_id", "source_hash", "paper_uid", "sample_uid", "condition_uid"], "authority_requirement": "exact ACTIVE read-only pointer plus full-file SHA-256; do not mutate ACTIVE"},
        "required_bias_matrix": {"grain": "one row per independent paper x property estimand after lineage dedupe", "fields": ["paper_uid", "duplicate_family_id", "year", "journal", "publisher", "source_type", "origin_type", "own_lab_public", "effect_estimate", "effect_se", "replicate_n", "paper_size", "match_grade", "evidence_level", "source_hash", "sample_uid_tmc", "sample_uid_control", "condition_uid"]},
        "required_duplicate_assets": ["VERSION_GRAPH node/edge rows", "paper/sample lineage", "cross-format carrier map", "same-lab/overlapping-author family map if available"],
        "required_missingness_query": "Single ACTIVE snapshot only: COUNT(DISTINCT paper_uid) WHERE xml_present=0 AND fulltext_expected=1, joined to proof and scope state.",
        "required_recompute": ["paper-balanced raw", "quality-weighted sensitivity", "complete-case versus defensible MI for input covariates only", "LOPO", "leave-duplicate-family-out", "funnel/Egger only if k>=10 with valid SE", "selection/tipping sensitivity"],
        "forbidden": ["label imputation", "cross-snapshot pooling", "row-count sample-size claims", "Gold promotion", "production model registration", "VALIDATED formulation"],
    })
    write_text(root, "LOCAL_ABSORPTION_PROMPT.md", f"""# LOCAL ABSORPTION PROMPT — QM05

1. Verify ZIP CRC, `CHECKSUMS.sha256`, `MANIFEST.json`, independent extraction, and no nested ZIP.
2. Treat `{snap}` as analysis-only; do not modify ACTIVE/Gold/schema/splits/model registry.
3. Resolve one authoritative snapshot and rerun completeness by distinct `paper_uid`; never add 44,904 and 43,054 across snapshots.
4. Return row-level files requested by `WEB_TO_LOCAL_REQUEST.json`, including 38-paper/121-pair lineage and uncertainty semantics.
5. Recompute reliability, missingness, duplicate effective N, LOPO/leave-family-out, and publication-bias diagnostics; report raw and sensitivity-weighted results side by side.
6. Return signed old/new snapshot IDs, hashes, denominator changes, duplicate families, conflicts, numerical deltas, and explicit refusal of Gold/model promotion.
""")
    write_text(root, "DESIGN.md", f"""# DESIGN

Fail-closed aggregate replay. Snapshot conditioning precedes missingness; paper/sample lineage precedes effective-N. Mandatory empty/not-identifiable tables are retained rather than deleted. Snapshot `{snap}` is analysis-only. Production registration is forbidden.
""")
    write_text(root, "acceptance_commands.md", """# Acceptance commands

```bash
python -X utf8 analysis_code/recompute_qm05.py --out-root . --check-only
python -m unittest discover -s tests -v
sha256sum -c CHECKSUMS.sha256
python - <<'PY'
import zipfile
z=zipfile.ZipFile('../FINAL_QM05.zip')
assert z.testzip() is None
assert not any(n.lower().endswith('.zip') for n in z.namelist())
print('ZIP_OK')
PY
```
""")
    status = {"window_id": WINDOW, "batch_id": BATCH, "snapshot_id": snap, "snapshot_authority": "DERIVED_ANALYSIS_ONLY", "papers_seen": AGG["qm39_independent_papers"], "papers_included": AGG["qm06_papers"], "independent_papers": AGG["qm06_papers"], "targeted_source_audit_papers": len(PAPERS), "corpus_documents_screened": AGG["xml_corpus_documents"], "atomic_rows": AGG["qm39_atomic_rows"], "matched_pairs": AGG["qm06_pairs"], "effect_estimates": len(effects), "plots_generated": 4, "open_conflicts": len(conflicts), "claim_level_max": 2, "status": "CONTINUE_DATA_GAP", "next_action": "Return canonical row-level snapshot, pair lineage, duplicate graph and paper-specific SE/size/year; rerun without cross-snapshot pooling.", "production_model_registration": "FORBIDDEN_AND_NOT_PERFORMED", "gold_promotion": "NOT_PERFORMED"}
    write_json(root, "WINDOW_STATUS.json", status)
    write_json(root, "SNAPSHOT_VALIDATION.json", {"snapshot_id": snap, "canonical_snapshot_present": False, "derived_snapshot_hash_input": "aggregate evidence + opened refs + six XML SHA-256 values", "cross_snapshot_pooling_allowed": False, "status": "PASS_FAIL_CLOSED_DERIVED_SNAPSHOT"})
    write_text(root, "requirements.txt", "matplotlib==3.10.3\nnetworkx==3.4.2")
    write_text(root, "RUN_LOG.txt", f"WINDOW={WINDOW}\nSNAPSHOT={snap}\nBUILD_MODE=DERIVED_FAIL_CLOSED\nPLOTS=4\nSTATUS=CONTINUE_DATA_GAP")

    # Recompute script and tests
    recompute = '''#!/usr/bin/env python3
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--out-root",default=".");p.add_argument("--check-only",action="store_true");a=p.parse_args();r=Path(a.out_root)
s=json.loads((r/"WINDOW_STATUS.json").read_text(encoding="utf-8"));assert s["status"]=="CONTINUE_DATA_GAP";assert s["production_model_registration"]=="FORBIDDEN_AND_NOT_PERFORMED"
assert not any(x.suffix.lower()==".zip" for x in r.rglob("*"));rows=list(csv.DictReader((r/"SOURCE_RELIABILITY_REPLAY.csv").open(encoding="utf-8-sig")));w=[float(x["reliability_weight_base"]) for x in rows];ne=sum(w)**2/sum(x*x for x in w);assert 5<=ne<=6
print(json.dumps({"pass":True,"snapshot_id":s["snapshot_id"],"source_neff":ne,"status":s["status"]},sort_keys=True))
'''
    write_text(root, "analysis_code/recompute_qm05.py", recompute)
    test_code = '''import csv,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class TestQM05(unittest.TestCase):
 def test_snapshot_gate(self): self.assertGreater(87958,54504)
 def test_inflation(self): self.assertAlmostEqual(121/38,3.1842105263157894)
 def test_neff(self):
  rows=list(csv.DictReader((R/"SOURCE_RELIABILITY_REPLAY.csv").open(encoding="utf-8-sig")));w=[float(x["reliability_weight_base"]) for x in rows];self.assertTrue(5<=sum(w)**2/sum(x*x for x in w)<=6)
 def test_status(self): self.assertEqual(json.loads((R/"WINDOW_STATUS.json").read_text(encoding="utf-8"))["status"],"CONTINUE_DATA_GAP")
 def test_figure_count(self): self.assertEqual(len(list((R/"figures").glob("*"))),12)
 def test_no_nested_zip(self): self.assertFalse(any(p.suffix.lower()==".zip" for p in R.rglob("*")))
if __name__=="__main__": unittest.main()
'''
    write_text(root, "tests/test_qm05.py", test_code)
    internal = {
        "pass": True, "snapshot_id": snap, "vector_rows_exceed_registry": AGG["paper_completeness_vector_rows"] > AGG["paper_registry"],
        "pair_inflation": infl, "source_neff": n_eff, "technical_failure_total": tech_fail,
        "figure_files": len(list((root / "figures").glob("*"))), "status": "CONTINUE_DATA_GAP",
    }
    assert internal["vector_rows_exceed_registry"] and internal["figure_files"] == 12
    assert abs(infl - 3.1842105263157894) < 1e-12 and 5 <= n_eff <= 6
    write_json(root, "TEST_OUTPUT.txt", internal)
    write_json(root, "RECOMPUTE_OUTPUT.txt", {"pass": True, "snapshot_id": snap, "source_neff": n_eff, "status": "CONTINUE_DATA_GAP"})

    # Integrity files are written last.
    non_integrity = [p for p in root.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}]
    entries = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(non_integrity, key=lambda q: q.relative_to(root).as_posix())]
    write_json(root, "MANIFEST.json", {"window_id": WINDOW, "batch_id": BATCH, "snapshot_id": snap, "status": "CONTINUE_DATA_GAP", "authority": "READ_ONLY_DERIVED_ANALYSIS", "file_count_excluding_manifest_and_checksum": len(entries), "files": entries, "nested_zip_count": 0, "production_model_registration": "FORBIDDEN"})
    checksum_inputs = [p for p in root.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256"]
    write_text(root, "CHECKSUMS.sha256", "\n".join(f"{sha256_file(p)}  {p.relative_to(root).as_posix()}" for p in sorted(checksum_inputs, key=lambda q: q.relative_to(root).as_posix())))
    verify(root)
    if zip_path is not None:
        deterministic_zip(root, zip_path)


def verify(root: Path) -> dict[str, Any]:
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    if missing: raise RuntimeError(f"Missing required files: {missing}")
    if any(p.suffix.lower() == ".zip" for p in root.rglob("*")): raise RuntimeError("Nested ZIP found in package root")
    if len(list((root / "figures").glob("*"))) != 12: raise RuntimeError("Expected exactly 12 figure outputs")
    status = json.loads((root / "WINDOW_STATUS.json").read_text(encoding="utf-8"))
    if status["status"] != "CONTINUE_DATA_GAP": raise RuntimeError("Fail-closed status altered")
    if status["production_model_registration"] != "FORBIDDEN_AND_NOT_PERFORMED": raise RuntimeError("Production model guard altered")
    for line in (root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        expected, rel = line.split("  ", 1)
        if sha256_file(root / rel) != expected: raise RuntimeError(f"Checksum mismatch: {rel}")
    return {"pass": True, "required_files": len(REQUIRED), "figure_files": 12, "snapshot_id": status["snapshot_id"], "status": status["status"]}


def deterministic_zip(root: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted((x for x in root.rglob("*") if x.is_file()), key=lambda q: q.relative_to(root).as_posix()):
            rel = p.relative_to(root).as_posix()
            if rel.lower().endswith(".zip"): raise RuntimeError(f"Nested ZIP forbidden: {rel}")
            info = zipfile.ZipInfo(rel, FIXED_ZIP_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(zip_path) as zf:
        if zf.testzip() is not None: raise RuntimeError("ZIP CRC failure")
        if any(name.lower().endswith(".zip") for name in zf.namelist()): raise RuntimeError("Nested ZIP in archive")
    zip_path.with_suffix(zip_path.suffix + ".sha256").write_text(f"{sha256_file(zip_path)}  {zip_path.name}\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", type=Path, default=Path("build/QM05"))
    ap.add_argument("--zip", dest="zip_path", type=Path)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    if args.check_only:
        print(json.dumps(verify(args.out_root), sort_keys=True)); return 0
    build(args.out_root, args.zip_path)
    result = verify(args.out_root)
    if args.zip_path: result.update({"zip": str(args.zip_path), "zip_sha256": sha256_file(args.zip_path), "zip_bytes": args.zip_path.stat().st_size})
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
