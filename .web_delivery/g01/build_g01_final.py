#!/usr/bin/env python3
"""Build, test and package the G01 Ti/TMC HQ corpus fleet audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import zipfile

from g01_payload import FLEETS, GAPS, NEGATIVES, QUERIES, SOURCES

PACKAGE = "G01_DATA_HQ_CORPUS_FLEET_AUDIT_FINAL_20260718"
STATUS = "below_gate_continue_optimization"


def wt(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8", newline="\n")


def wjson(root: Path, rel: str, obj: object) -> None:
    wt(root, rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def wjsonl(root: Path, rel: str, rows: list[dict]) -> None:
    wt(root, rel, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def wcsv(root: Path, rel: str, rows: list[dict], fields: list[str] | None = None) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_modules(root: Path) -> None:
    wt(root, "modules/g01_data_hq_fleet_audit/__init__.py", r'''
        """Deterministic Ti/TMC HQ corpus governance and ten-fleet audit."""
        from .admission import admit_record
        from .firewall import audit_batch, audit_record, classify_target_semantics
        from .fleet import ArchiveIdentityError, profile_zip, safe_coverage, wilson_interval
        from .keys import make_condition_key, make_paper_key, normalize_doi

        __all__ = [
            "admit_record", "audit_batch", "audit_record", "classify_target_semantics",
            "ArchiveIdentityError", "profile_zip", "safe_coverage", "wilson_interval",
            "make_condition_key", "make_paper_key", "normalize_doi",
        ]
        __version__ = "1.0.0"
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/keys.py", r'''
        from __future__ import annotations
        import hashlib
        import json
        import re
        import unicodedata
        from urllib.parse import unquote

        DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
        DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", re.I)
        CONDITION_FIELDS = (
            "paper_key", "material_name", "material_family", "matrix_composition",
            "reinforcement", "reinforcement_fraction", "process_chain", "heat_treatment",
            "test_mode", "test_temperature_c", "strain_rate_s", "test_direction",
            "specimen_geometry", "gauge_length_mm", "target_family", "target_variant",
        )

        def norm(value: object) -> str:
            if value is None:
                return ""
            return " ".join(unicodedata.normalize("NFKC", str(value)).strip().lower().split())

        def normalize_doi(raw: object) -> str | None:
            if raw is None:
                return None
            value = DOI_PREFIX.sub("", unquote(str(raw)).strip()).strip().rstrip(".,;:)]}").lower()
            return value if DOI_RE.match(value) else None

        def stable(prefix: str, payload: dict) -> str:
            blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            return f"{prefix}_{hashlib.sha256(blob.encode('utf-8')).hexdigest()[:24]}"

        def make_paper_key(*, doi: object = None, title: object = None, year: object = None,
                           first_author: object = None, journal: object = None) -> str:
            doi_norm = normalize_doi(doi)
            if doi_norm:
                return stable("paper", {"doi": doi_norm})
            payload = {"title": norm(title), "year": norm(year),
                       "first_author": norm(first_author), "journal": norm(journal)}
            if not payload["title"]:
                raise ValueError("paper_key requires a valid DOI or non-empty title")
            return stable("paper", payload)

        def make_condition_key(record: dict) -> str:
            if not record.get("paper_key"):
                raise ValueError("condition_key requires paper_key")
            return stable("condition", {k: norm(record.get(k)) for k in CONDITION_FIELDS})
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/firewall.py", r'''
        from __future__ import annotations
        import re

        ALLOWED = {
            "cp_ti", "alpha_ti", "near_alpha_ti", "alpha_beta_ti", "beta_ti",
            "metastable_beta_ti", "titanium_aluminide", "titanium_matrix_composite",
        }
        HARD_REJECT = re.compile(
            r"\b(titanium dioxide|tio2|titanate|photocatal|catalyst|aluminium matrix|"
            r"aluminum matrix|steel matrix|iron casting|waste water|aerosol|pyrolysis|"
            r"cement|concrete|zirconium alloy|magnesium alloy)\b", re.I)
        TI_NAME = re.compile(
            r"\b(ti(?:[-–]?\d|\b)|titanium|tc\d+|ta\d+|tb\d+|vt\d+|imi\s*\d+|"
            r"ti[-–]?6al[-–]?4v|ti64|ti65|tial|gamma[- ]?ti|alpha[- ]?ti|beta[- ]?ti)\b", re.I)
        COMPOSITE = re.compile(r"\b(tibw?|tib2|tic|sic|b4c|cnt|vgcf|matrix composite|tmc)\b", re.I)

        def _text(record: dict) -> str:
            return " ".join(str(record.get(k, "")) for k in (
                "material_name", "material_name_raw", "paper_title", "matrix_base",
                "reinforcement", "material_family", "local_context") if record.get(k)).lower()

        def _composition(record: dict) -> dict[str, float]:
            raw = record.get("matrix_composition_wt_pct") or record.get("matrix_composition") or {}
            if not isinstance(raw, dict):
                return {}
            out = {}
            for key, value in raw.items():
                try:
                    out[str(key).strip().lower()] = float(value)
                except (TypeError, ValueError):
                    pass
            return out

        def _gate(gate: str, status: str, reason: str, evidence: dict | None = None) -> dict:
            return {"gate": gate, "status": status, "reason": reason, "evidence": evidence or {}}

        def _base_gate(record: dict) -> dict:
            text, comp = _text(record), _composition(record)
            family = str(record.get("material_family", "")).strip().lower()
            matrix = str(record.get("matrix_base", "")).strip().lower()
            if HARD_REJECT.search(text):
                return _gate("base_element", "FAIL", "non-Ti matrix or Ti compound/application context", {"matrix_base": matrix})
            if family == "titanium_matrix_composite" and matrix not in {"ti", "titanium"}:
                return _gate("base_element", "FAIL", "TMC requires explicit Ti matrix", {"matrix_base": matrix})
            if matrix in {"ti", "titanium"}:
                return _gate("base_element", "PASS", "explicit Ti matrix", {"matrix_base": matrix})
            if comp:
                ti = comp.get("ti", comp.get("titanium", 0.0))
                al = comp.get("al", comp.get("aluminium", comp.get("aluminum", 0.0)))
                total = sum(max(v, 0.0) for v in comp.values())
                if family == "titanium_aluminide" and total > 0 and ti > 0 and (ti + al) / total >= 0.80:
                    return _gate("base_element", "PASS", "Ti-Al intermetallic composition", {"ti": ti, "al": al})
                if total > 0 and ti / total >= 0.50:
                    return _gate("base_element", "PASS", "Ti is matrix majority", {"ti_fraction": ti / total})
                return _gate("base_element", "FAIL", "Ti is not matrix majority", {"ti": ti, "total": total})
            if TI_NAME.search(text):
                return _gate("base_element", "REVIEW", "Ti naming exists but matrix/composition incomplete")
            return _gate("base_element", "FAIL", "no Ti-matrix evidence")

        def _family_gate(record: dict) -> dict:
            family = str(record.get("material_family", "")).strip().lower()
            if family in ALLOWED:
                return _gate("family", "PASS", "registered Ti/TMC family", {"family": family})
            if not family or family in {"unknown", "ambiguous", "titanium_based_unspecified"}:
                return _gate("family", "REVIEW", "family unresolved", {"family": family})
            return _gate("family", "FAIL", "family outside direct Ti/TMC domain", {"family": family})

        def _name_gate(record: dict) -> dict:
            text = _text(record)
            family = str(record.get("material_family", "")).strip().lower()
            if HARD_REJECT.search(text):
                return _gate("naming_range", "FAIL", "hard-reject lexical pattern")
            if family == "titanium_matrix_composite":
                if TI_NAME.search(text) and COMPOSITE.search(text):
                    return _gate("naming_range", "PASS", "Ti matrix and reinforcement named")
                return _gate("naming_range", "REVIEW", "TMC name lacks resolvable matrix or reinforcement")
            if TI_NAME.search(text):
                return _gate("naming_range", "PASS", "recognized Ti naming")
            return _gate("naming_range", "REVIEW", "name is not canonical")

        def _ceiling_gate(record: dict) -> dict:
            use = str(record.get("corpus_use", "direct_evidence")).strip().lower()
            off = bool(record.get("off_domain", False))
            if use in {"direct_evidence", "training", "calibration", "evaluation"} and off:
                return _gate("other_alloy_ceiling", "FAIL", "direct corpus has zero off-domain ceiling", {"ceiling": 0.0})
            if use == "method_transfer_only":
                return _gate("other_alloy_ceiling", "PASS", "isolated method-transfer lane", {"batch_ceiling": 0.05})
            return _gate("other_alloy_ceiling", "PASS", "Ti/TMC direct lane", {"ceiling": 0.0})

        def audit_record(record: dict) -> dict:
            gates = [_base_gate(record), _family_gate(record), _name_gate(record), _ceiling_gate(record)]
            statuses = {g["status"] for g in gates}
            flags = sorted({f"{g['gate'].upper()}_{g['status']}" for g in gates if g["status"] != "PASS"})
            if "FAIL" in statuses:
                admitted, role = False, "excluded"
            elif "REVIEW" in statuses:
                admitted, role = False, "audit_repair"
            else:
                admitted, role = True, "support_only"
            out = dict(record)
            out.update({
                "admitted": admitted,
                "row_role": role,
                "direct_evidence_eligible": admitted and str(record.get("corpus_use", "direct_evidence")).lower() != "method_transfer_only",
                "risk_flags": flags,
                "gate_results": gates,
                "policy_version": "g01-firewall-1.0.0",
            })
            return out

        def audit_batch(records: list[dict], method_transfer_ceiling: float = 0.05) -> dict:
            decisions = [audit_record(r) for r in records]
            method = [d for d in decisions if str(d.get("corpus_use", "")).lower() == "method_transfer_only"]
            direct_bad = [d for d in decisions if str(d.get("corpus_use", "direct_evidence")).lower() != "method_transfer_only" and d.get("off_domain")]
            fraction = len(method) / len(decisions) if decisions else 0.0
            return {"passed": not direct_bad and fraction <= method_transfer_ceiling,
                    "records": decisions, "method_transfer_fraction": fraction,
                    "method_transfer_ceiling": method_transfer_ceiling,
                    "direct_off_domain_count": len(direct_bad)}

        def classify_target_semantics(record: dict) -> dict:
            raw = " ".join(str(record.get(k, "")) for k in
                           ("target_raw", "target_name", "test_mode", "local_context")).lower()
            result = {"target_family": "unknown", "target_variant": "unknown",
                      "semantic_block": False, "semantic_flags": []}
            if re.search(r"\b(uts|ultimate tensile|tensile strength)\b", raw):
                result.update(target_family="UTS", target_variant="tensile_ultimate")
                if re.search(r"compress|flexur|bend|shear|dynamic", raw):
                    result.update(semantic_block=True); result["semantic_flags"].append("UTS_NON_TENSILE_MODE")
            elif re.search(r"\b(yield strength|proof stress|ys|rp0[.,]?2|rp0[.,]?1)\b", raw):
                result.update(target_family="YS", target_variant="rp0.2" if re.search(r"rp0[.,]?2|0[.,]?2%", raw) else "yield_method_unresolved")
                if "compress" in raw:
                    result.update(semantic_block=True); result["semantic_flags"].append("YS_COMPRESSION")
            elif re.search(r"elong|ductility|reduction of area|\bra\b|\bagt?\b", raw):
                result["target_family"] = "EL"
                if re.search(r"reduction of area|\bra\b|\bz\b", raw):
                    result.update(target_variant="reduction_of_area", semantic_block=True); result["semantic_flags"].append("EL_IS_RA")
                elif re.search(r"\bagt\b|total uniform", raw):
                    result.update(target_variant="total_uniform_elongation", semantic_block=True); result["semantic_flags"].append("EL_IS_AGT")
                elif re.search(r"\bag\b|uniform elong", raw):
                    result.update(target_variant="uniform_elongation", semantic_block=True); result["semantic_flags"].append("EL_IS_AG")
                elif re.search(r"compress|flexur|bend", raw):
                    result.update(target_variant="non_tensile_strain", semantic_block=True); result["semantic_flags"].append("EL_NON_TENSILE")
                elif re.search(r"\bat\b|total elongation at fracture", raw):
                    result["target_variant"] = "total_elongation_at_fracture"
                else:
                    result["target_variant"] = "elongation_after_fracture_or_unresolved"
            elif "modulus" in raw or "young" in raw:
                result["target_family"] = "MODULUS"
                for token, variant in (("indent", "indentation_modulus"), ("reduced modulus", "reduced_modulus"),
                                       ("storage", "storage_modulus"), ("dynamic", "dynamic_modulus"),
                                       ("flexur", "flexural_modulus"), ("compress", "compression_modulus")):
                    if token in raw:
                        result.update(target_variant=variant, semantic_block=True); result["semantic_flags"].append("MODULUS_NON_TENSILE_STATIC"); break
                else:
                    result["target_variant"] = "youngs_modulus_tension" if ("tens" in raw or "young" in raw) else "elastic_modulus_mode_unresolved"
            elif re.search(r"hardness|\bhv\b|hrc|brinell|knoop", raw):
                result["target_family"] = "HARDNESS"
                if "hv" in raw or "vickers" in raw:
                    result["target_variant"] = "vickers_hv"
                    if not re.search(r"hv\s*\d|load|kgf|gf|newton", raw): result["semantic_flags"].append("HARDNESS_LOAD_MISSING")
                else:
                    result.update(target_variant="non_vickers_or_unknown", semantic_block=True); result["semantic_flags"].append("HARDNESS_SCALE_NOT_HV")
            elif re.search(r"\bkic\b|fracture toughness|\bji?c\b|ctod|charpy|\bkq\b", raw):
                result["target_family"] = "KIC"
                if re.search(r"\bkq\b|\bjic\b|j-integral|ctod|charpy", raw):
                    result.update(target_variant="non_kic_fracture_parameter", semantic_block=True); result["semantic_flags"].append("KIC_PARAMETER_MISMATCH")
                else:
                    result["target_variant"] = "kic_or_unresolved"
            return result
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/admission.py", r'''
        from __future__ import annotations
        from .firewall import audit_record, classify_target_semantics
        from .keys import make_condition_key, make_paper_key, normalize_doi

        def _complete(record: dict) -> bool:
            return bool((normalize_doi(record.get("doi")) or record.get("stable_source_id"))
                        and record.get("source_locator") and record.get("source_span")
                        and record.get("parser_version") and record.get("normalizer_version"))

        def admit_record(record: dict) -> dict:
            out = audit_record(record)
            sem = classify_target_semantics(record)
            out.update(sem)
            out["paper_key"] = make_paper_key(
                doi=record.get("doi"), title=record.get("paper_title"), year=record.get("paper_year"),
                first_author=record.get("first_author"), journal=record.get("journal"))
            payload = dict(record); payload.update(out); payload["paper_key"] = out["paper_key"]
            out["condition_key"] = make_condition_key(payload)
            flags = set(out.get("risk_flags", [])) | set(sem["semantic_flags"])
            if not out["admitted"]:
                role = out["row_role"]
            elif sem["semantic_block"]:
                role = "negative_evidence"
            elif record.get("source_conflict") or record.get("source_title_mismatch"):
                role = "audit_repair"; flags.add("SOURCE_CONFLICT")
            elif _complete(record) and sem["target_family"] != "unknown" and sem["target_variant"] not in {
                "yield_method_unresolved", "elastic_modulus_mode_unresolved", "kic_or_unresolved"}:
                role = "gold_train"
            elif normalize_doi(record.get("doi")) and record.get("source_locator") and sem["target_family"] != "unknown":
                role = "silver_train"
            else:
                role = "audit_repair"
            if sem["target_family"] == "KIC" and not record.get("kic_validity_receipt"):
                role = "audit_repair"; flags.add("KIC_FAIL_CLOSED_NO_VALIDITY_RECEIPT")
            out["row_role"] = role
            out["risk_flags"] = sorted(flags)
            out["admission_version"] = "g01-admission-1.0.0"
            return out
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/fleet.py", r'''
        from __future__ import annotations
        from collections import Counter
        import json
        import math
        from pathlib import Path
        import re
        import zipfile

        PACKAGE_RE = re.compile(r"(B\d{3})_OF_(\d{3})", re.I)
        CONTROL_PATH = "__PACKAGE_CONTROL__/PACKAGE_CONTROL.json"

        class ArchiveIdentityError(RuntimeError): pass

        def safe_coverage(numerator: int | None, denominator: int | None) -> dict:
            if denominator is None: return {"coverage": None, "status": "DENOMINATOR_NOT_FROZEN"}
            if denominator <= 0: return {"coverage": None, "status": "DENOMINATOR_INVALID"}
            if numerator is None: return {"coverage": None, "status": "NUMERATOR_NOT_VERIFIED"}
            if numerator < 0 or numerator > denominator: return {"coverage": None, "status": "COUNT_INCONSISTENT"}
            return {"coverage": numerator / denominator, "status": "VERIFIED"}

        def wilson_interval(successes: int, total: int, z: float = 1.959963984540054):
            if total <= 0 or successes < 0 or successes > total: return None
            p = successes / total; denom = 1 + z * z / total
            center = (p + z * z / (2 * total)) / denom
            margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
            return max(0.0, center - margin), min(1.0, center + margin)

        def profile_zip(path: str | Path) -> dict:
            path = Path(path); match = PACKAGE_RE.search(path.name)
            file_id = match.group(1).upper() if match else None
            with zipfile.ZipFile(path) as zf:
                names = {n.replace("\\", "/"): n for n in zf.namelist()}
                if CONTROL_PATH not in names: raise ArchiveIdentityError(f"missing {CONTROL_PATH}")
                try: control = json.loads(zf.read(names[CONTROL_PATH]).decode("utf-8-sig"))
                except Exception as exc: raise ArchiveIdentityError(f"invalid package control: {exc}") from exc
                package_id = str(control.get("package_id", "")).upper()
                if file_id and package_id and file_id != package_id:
                    raise ArchiveIdentityError(f"filename/control mismatch: {file_id} != {package_id}")
                ext, surfaces, payload = Counter(), Counter(), 0
                for info in zf.infolist():
                    if info.is_dir(): continue
                    name = info.filename.replace("\\", "/"); ext[Path(name).suffix.lower() or "[no_ext]"] += 1
                    if name.startswith("PAYLOAD/"):
                        payload += 1
                        surfaces["TABLES_DATA" if "/TABLES_DATA/" in name else "LITERATURE" if "/LITERATURE/" in name else "OTHER_PAYLOAD"] += 1
                return {"archive": path.name, "package_id": package_id or file_id,
                        "package_index": control.get("package_index"), "package_count": control.get("package_count"),
                        "domain": control.get("domain"), "default_mode": control.get("default_mode"),
                        "core_fingerprint": control.get("core_fingerprint"), "payload_members": payload,
                        "extension_counts": dict(sorted(ext.items())), "payload_surface_counts": dict(sorted(surfaces.items()))}
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/requeue.py", r'''
        from __future__ import annotations
        import json
        from pathlib import Path
        from .keys import normalize_doi
        PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

        def validate_gap_record(record: dict) -> dict:
            out = dict(record); doi = normalize_doi(out.get("doi"))
            if not doi: raise ValueError(f"invalid DOI: {out.get('doi')!r}")
            out["doi"] = doi
            if out.get("priority") not in PRIORITY: raise ValueError("priority must be P0..P3")
            required = {"gap_id", "material_family", "gap_types", "queue_action", "required_output"}
            missing = sorted(k for k in required if not out.get(k))
            if missing: raise ValueError(f"missing gap fields: {missing}")
            return out

        def load_gap_queue(path: str | Path) -> list[dict]:
            rows = []
            with Path(path).open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if line.strip():
                        try: rows.append(validate_gap_record(json.loads(line)))
                        except Exception as exc: raise ValueError(f"{path}:{line_no}: {exc}") from exc
            return sorted(rows, key=lambda r: (PRIORITY[r["priority"]], r["doi"]))
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/__main__.py", r'''
        from __future__ import annotations
        import argparse
        import json
        from pathlib import Path
        from .admission import admit_record
        from .firewall import audit_record
        from .fleet import profile_zip
        from .requeue import load_gap_queue

        def rows(path):
            with Path(path).open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip(): yield json.loads(line)

        def smoke(args):
            total = matched = 0
            for row in rows(args.examples):
                total += 1; out = audit_record(row)
                if bool(out["admitted"]) != bool(row["expected_admitted"]):
                    raise SystemExit(f"firewall mismatch: {row.get('example_id')}: {out}")
                matched += 1
            gaps = load_gap_queue(args.gaps) if args.gaps else []
            print(json.dumps({"status":"PASS","examples":total,"matched":matched,"validated_gap_dois":len(gaps)}, sort_keys=True)); return 0

        def transform(args, fn):
            out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", encoding="utf-8") as f:
                for row in rows(args.input): f.write(json.dumps(fn(row), ensure_ascii=False, sort_keys=True) + "\n")
            return 0

        def scan(args):
            Path(args.output).write_text(json.dumps([profile_zip(p) for p in args.archives], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); return 0

        def parser():
            p = argparse.ArgumentParser(prog="g01-data-hq-fleet-audit"); sub = p.add_subparsers(required=True)
            s = sub.add_parser("smoke"); s.add_argument("--examples", required=True); s.add_argument("--gaps"); s.set_defaults(func=smoke)
            f = sub.add_parser("firewall"); f.add_argument("--input", required=True); f.add_argument("--output", required=True); f.set_defaults(func=lambda a: transform(a, audit_record))
            a = sub.add_parser("admit"); a.add_argument("--input", required=True); a.add_argument("--output", required=True); a.set_defaults(func=lambda x: transform(x, admit_record))
            z = sub.add_parser("scan-fleet"); z.add_argument("archives", nargs="+"); z.add_argument("--output", required=True); z.set_defaults(func=scan)
            return p

        if __name__ == "__main__": raise SystemExit(parser().parse_args().func(parser().parse_args()))
    ''')

    wt(root, "modules/g01_data_hq_fleet_audit/README.md", '''
        # G01 module

        Standard-library-only Ti/TMC corpus governance: four-gate firewall,
        paper/condition keys, target-semantics fail-closed admission, fleet ZIP
        identity profiling, denominator-safe coverage and executable DOI requeue.
        It does not train a model and cannot produce an HQ-LOSO receipt.
    ''')


def build_data(root: Path) -> None:
    families = ["conventional_ti_alloy", "titanium_aluminide", "titanium_matrix_composite", "ambiguous_or_offdomain"]
    targets = ["UTS", "YS", "EL", "MODULUS", "HARDNESS", "KIC", "MULTIPROPERTY_OTHER"]
    surfaces = ["STRUCTURED_TABLE", "XML_FULLTEXT", "MD_FULLTEXT"]
    matrix = []
    for fid, mode, uploaded, members, kinds, note in FLEETS:
        for family in families:
            for target in targets:
                for surface in surfaces:
                    off = family == "ambiguous_or_offdomain"
                    matrix.append({
                        "fleet_id": fid, "default_mode": mode, "direct_archive_uploaded": str(uploaded).lower(),
                        "package_member_count_manifest_approx": members, "dominant_member_types": kinds,
                        "material_family": family, "target_family": target, "source_surface": surface,
                        "hq_structured_rows_verified": "", "fulltext_docs_verified": "", "fulltext_spans_verified": "",
                        "eligible_denominator": "", "coverage_pct": "", "denominator_status": "NOT_FROZEN",
                        "continue_extraction_yes_no": "NO" if off else "YES",
                        "decision_scope": "negative_evidence_only" if off else "reduce_and_reconcile" if fid == "B010" else "map_and_requeue",
                        "reason": "off-domain rows blocked from direct evidence" if off else "no frozen HQ family×target×source denominator and no verified row/span join receipt",
                        "evidence_class": "FLEET_MANIFEST_GROUNDED" + ("+DIRECT_UPLOAD_NAME_CONFIRMED" if uploaded else "+RAW_ARCHIVE_NOT_IN_WINDOW"),
                        "fleet_note": note,
                    })
    wcsv(root, "DATA/g01/fleet_coverage_matrix.csv", matrix)

    decisions = []
    for fid, mode, uploaded, members, kinds, note in FLEETS:
        decisions.append({
            "fleet_id": fid, "default_mode": mode, "direct_archive_uploaded": str(uploaded).lower(),
            "continue_extraction_yes_no": "YES",
            "allowed_next_action": "GLOBAL_REDUCE_AFTER_MAP_RECEIPTS" if fid == "B010" else "CARRIER_MAP_INCREMENTAL",
            "blind_full_reextract": "NO",
            "decision_reason": "continue map-return reconciliation/deduplication; no global completion before B001-B009 receipts" if fid == "B010" else "targeted map/requeue until HQ row and exact-span denominators are frozen",
            "member_count_manifest_approx": members, "dominant_member_types": kinds,
            "evidence_boundary": note, "status": STATUS,
        })
    wcsv(root, "DATA/g01/fleet_decisions.csv", decisions)

    gap_rows = [{
        "gap_id": gid, "doi": doi, "material_family": family,
        "target_families": targets.split("|"), "gap_types": types.split("|"),
        "queue_action": "REQUEUE_FULLTEXT_AND_STRUCTURED_ROW", "priority": priority,
        "evidence_locator": "project_source:frozen_plot_data.csv audit row(s)",
        "required_output": ["canonical_record_json", "exact_source_span", "paper_key", "condition_key", "admission_decision"],
        "admission_after_repair": "re-evaluate; never auto-promote", "reason": reason,
        "evidence_class": "PROJECT_SOURCE_AUDIT_ROW_GROUNDED", "not_hq_yet": True,
    } for gid, doi, family, targets, types, priority, reason in GAPS]
    wjsonl(root, "DATA/g01/hq_gap_dois.jsonl", gap_rows)

    neg = [{"doi": doi, "decision": "EXCLUDE_FROM_DIRECT_TITMC_EVIDENCE", "row_role": "negative_evidence",
            "reason_code": code, "reason": reason,
            "allowed_use": "admission-risk classifier and parser regression test only",
            "evidence_class": "PROJECT_SOURCE_AUDIT_ROW_GROUNDED"} for doi, code, reason in NEGATIVES]
    wjsonl(root, "DATA/g01/negative_evidence_dois.jsonl", neg)

    examples = [
        {"example_id":"PASS_TI64","material_name":"Ti-6Al-4V","paper_title":"Tensile properties of Ti-6Al-4V","matrix_base":"Ti","material_family":"alpha_beta_ti","matrix_composition_wt_pct":{"Ti":89.5,"Al":6,"V":4},"corpus_use":"direct_evidence","off_domain":False,"expected_admitted":True},
        {"example_id":"PASS_TIB_TMC","material_name":"TiB/Ti-6Al-4V titanium matrix composite","paper_title":"DED TiB reinforced Ti alloy","matrix_base":"Ti","reinforcement":"TiB","material_family":"titanium_matrix_composite","corpus_use":"direct_evidence","off_domain":False,"expected_admitted":True},
        {"example_id":"PASS_TIBW_TI65","material_name":"TiBw/Ti65","paper_title":"Laser DED TiBw reinforced Ti65","matrix_base":"Ti","reinforcement":"TiBw","material_family":"titanium_matrix_composite","corpus_use":"direct_evidence","off_domain":False,"expected_admitted":True},
        {"example_id":"PASS_TIAL","material_name":"gamma-TiAl","paper_title":"Mechanical properties of gamma TiAl","matrix_base":"Ti","material_family":"titanium_aluminide","matrix_composition_wt_pct":{"Ti":55,"Al":44},"corpus_use":"direct_evidence","off_domain":False,"expected_admitted":True},
        {"example_id":"FAIL_AA7050_TIO2","material_name":"AA7050-TiO2 aluminium matrix composite","paper_title":"AA7050 TiO2 reinforced aluminium matrix composite","matrix_base":"Al","material_family":"aluminium_matrix_composite","corpus_use":"direct_evidence","off_domain":True,"expected_admitted":False},
        {"example_id":"FAIL_TIO2","material_name":"TiO2 nanotube","paper_title":"Titanium dioxide photocatalyst","matrix_base":"oxide","material_family":"ceramic","corpus_use":"direct_evidence","off_domain":True,"expected_admitted":False},
        {"example_id":"FAIL_STEEL_MINOR_TI","material_name":"vermicular graphite iron with Ti addition","paper_title":"Role of titanium in iron casting","matrix_base":"Fe","material_family":"cast_iron","corpus_use":"direct_evidence","off_domain":True,"expected_admitted":False},
        {"example_id":"REVIEW_BARE_TMC","material_name":"TMC","paper_title":"Composite properties","matrix_base":"","reinforcement":"","material_family":"titanium_matrix_composite","corpus_use":"direct_evidence","off_domain":False,"expected_admitted":False},
        {"example_id":"FAIL_MOSI_TIC","material_name":"Mo-Si-B-TiC","paper_title":"Molybdenum borosilicate alloys with TiC","matrix_base":"Mo","material_family":"refractory_alloy","corpus_use":"direct_evidence","off_domain":True,"expected_admitted":False},
        {"example_id":"METHOD_TRANSFER_NOT_DIRECT","material_name":"Ni-based superalloy","paper_title":"Information extraction method","matrix_base":"Ni","material_family":"other","corpus_use":"method_transfer_only","off_domain":False,"expected_admitted":False},
    ]
    wjsonl(root, "DATA/g01/firewall_examples.jsonl", examples)

    targets = [
        {"target_family":"UTS","canonical_target":"uts_tension_mpa","unit":"MPa","gold_semantics":"maximum engineering tensile stress","hard_blocks":"compressive|flexural|shear|dynamic strength"},
        {"target_family":"YS","canonical_target":"ys_tension_mpa","unit":"MPa","gold_semantics":"tensile yield/proof stress with method","hard_blocks":"compressive yield|indentation yield|method absent for gold"},
        {"target_family":"EL","canonical_target":"elongation_after_fracture_percent","unit":"%","gold_semantics":"A/At tensile fracture elongation; variant preserved","hard_blocks":"RA/Z|Ag/Agt|compression strain|bend/flexural ductility"},
        {"target_family":"MODULUS","canonical_target":"youngs_modulus_tension_gpa","unit":"GPa","gold_semantics":"static tensile Young modulus","hard_blocks":"compression|flexural|dynamic|indentation|reduced|storage modulus"},
        {"target_family":"HARDNESS","canonical_target":"vickers_hardness_hv","unit":"HV","gold_semantics":"Vickers with test force and locator","hard_blocks":"scale unknown|Rockwell|Brinell|Knoop|load missing for gold"},
        {"target_family":"KIC","canonical_target":"plane_strain_kic_mpa_sqrt_m","unit":"MPa*sqrt(m)","gold_semantics":"KIC with validity receipt and precracked specimen","hard_blocks":"KQ|JIc|J-integral|CTOD|Charpy; fail closed"},
    ]
    wcsv(root, "DATA/g01/target_family_registry.csv", targets)

    profiles = [
        {"source_surface":"STRUCTURED_TABLE","extensions":"csv|xlsx|xls","potential_role":"gold_or_silver_after_evidence_join","minimum_evidence":"source document + sheet/table + row/cell locator + units","default_risk":"orphan row / merged cells / inherited unit"},
        {"source_surface":"XML_FULLTEXT","extensions":"xml|nxml|tei.xml","potential_role":"span source and structured extraction","minimum_evidence":"document identity + section/table/figure locator + exact span","default_risk":"schema/provider variation and citation-vs-result confusion"},
        {"source_surface":"MD_FULLTEXT","extensions":"md|markdown","potential_role":"retrieval/span support","minimum_evidence":"source identity + heading/block locator + original-carrier lineage","default_risk":"conversion loss and table flattening"},
        {"source_surface":"DOCX_FULLTEXT","extensions":"docx","potential_role":"retrieval/span support","minimum_evidence":"source identity + paragraph/table locator","default_risk":"relationship-part loss and image-only evidence"},
        {"source_surface":"REVIEW_SECONDARY","extensions":"any","potential_role":"support_only until primary trace","minimum_evidence":"original DOI and original table/figure","default_risk":"copied values and condition loss"},
    ]
    wcsv(root, "DATA/g01/source_profile_registry.csv", profiles)

    wt(root, "DATA/g01/admission_schema.yaml", r'''
        schema_version: "g01-admission-1.0.0"
        domain: "ti_tmc"
        status: "below_gate_continue_optimization"
        raw_rows_immutable: true
        append_only_governance: true
        direct_corpus_other_alloy_ceiling: 0.0
        method_transfer_only_batch_ceiling: 0.05
        identity:
          required_any: [doi, stable_source_id]
          fields:
            doi: {type: string, normalize: lowercase_doi, nullable: true}
            stable_source_id: {type: string, nullable: true}
            paper_title: {type: string, required: true}
            paper_year: {type: integer, nullable: true}
            first_author: {type: string, nullable: true}
            journal: {type: string, nullable: true}
            paper_key: {type: string, generated: "sha256(normalized DOI; fallback title+year+author+journal)", required_for_training: true}
        condition:
          required_for_gold: [material_name, material_family, process_chain, test_mode, target_family, target_variant, source_locator, source_span, parser_version, normalizer_version]
          fields:
            material_name: {type: string}
            material_family: {enum: [cp_ti, alpha_ti, near_alpha_ti, alpha_beta_ti, beta_ti, metastable_beta_ti, titanium_aluminide, titanium_matrix_composite]}
            matrix_base: {type: string, gold_constraint: "Ti/titanium"}
            matrix_composition: {type: "map[element, number]", basis_required: true}
            reinforcement: {type: string, nullable: true}
            reinforcement_fraction: {type: number, nullable: true, basis_required_if_present: true}
            process_chain: {type: "list[string]", ordered: true}
            heat_treatment: {type: "list[object]", ordered: true, nullable: true}
            test_mode: {type: string}
            test_temperature_c: {type: number, nullable: true}
            strain_rate_s: {type: number, nullable: true}
            test_direction: {type: string, nullable: true}
            specimen_geometry: {type: string, nullable: true}
            gauge_length_mm: {type: number, nullable: true}
            condition_key: {type: string, generated: "sha256(paper_key + normalized material/process/test/target semantics)", required_for_training: true}
        canonical_units: {UTS: MPa, YS: MPa, EL: "%", MODULUS: GPa, HARDNESS: HV, KIC: "MPa*sqrt(m)", temperature: degC, strain_rate: "s^-1"}
        target_semantics:
          EL:
            gold_allowed: [elongation_after_fracture, total_elongation_at_fracture]
            separate_tasks: [uniform_elongation, total_uniform_elongation, reduction_of_area]
            hard_block_maps: ["RA->EL", "Z->EL", "Ag->EL", "Agt->EL", "compression_strain->EL", "flexural_strain->EL"]
          MODULUS:
            gold_allowed: [youngs_modulus_static_tension]
            hard_block_maps: [compression_modulus, flexural_modulus, dynamic_modulus, indentation_modulus, reduced_modulus, storage_modulus]
          HARDNESS: {gold_requires: [vickers_scale, test_force, exact_source_locator]}
          KIC:
            policy: fail_closed
            gold_requires: [KIC_parameter, validity_receipt, precracked_specimen, exact_source_locator]
            hard_block_maps: [KQ, JIc, J_integral, CTOD, Charpy]
        source_evidence:
          gold_requires: [source_title, doi_or_stable_id, page_table_figure_locator, exact_source_span, parser_version, normalizer_version]
          review_rows: support_only_until_primary_source_trace
          figure_ocr_ambiguous: audit_repair
        row_roles:
          priority: [excluded, audit_repair, negative_evidence, calibration_only, support_only, silver_train, gold_train]
          gold_train: "all semantic, source, unit, duplicate/conflict and split gates pass"
          silver_train: "target family and unit recoverable; residual auxiliary metadata gap"
          support_only: "retrieval/features/method evidence; no primary target loss"
          calibration_only: "source-group-disjoint, at least silver quality, no weight updates"
          audit_repair: "recoverable ambiguity/conflict/OCR/source mismatch"
          negative_evidence: "confirmed admission failure retained for risk/parser models"
          excluded: "off-domain, irrecoverable, duplicate noncanonical or unresolved hard conflict"
        negative_sample_strategy:
          classes: [off_domain_base_matrix, titanium_compound_not_structural_ti_alloy, target_semantic_mismatch, source_title_doi_mismatch, review_value_without_primary_trace, duplicate_noncanonical, unresolved_conflict, ocr_decimal_or_unit_anomaly]
          allowed_uses: [admission_risk_classifier, parser_regression_tests, audit_prioritization, OOD_flagger]
          forbidden_uses: [primary_target_fit, calibration, direct_scientific_evidence, candidate_ranking]
          sampling: "stratify by failure class and source surface; group by source_document_id"
        split_policy:
          primary_group: source_document_id
          nested_groups: [paper_key, table_id, figure_id, specimen_group_id, duplicate_cluster_id]
          required_tests: [source_holdout_LOSO, process_holdout, alloy_family_holdout, reinforcement_holdout, temperature_holdout]
          train_calibration_test_group_intersection: 0
    ''')

    wt(root, "DATA/g01/requeue_policy.yaml", '''
        version: g01-requeue-1.0.0
        priorities:
          P0: blocks target semantics, primary-source trace, duplicate/conflict resolution or suspicious values
          P1: missing process/test condition or exact evidence span
          P2: useful context gap not immediately blocking highest-value rows
          P3: low-value/deferred
        queue_contract:
          required_inputs: [doi, material_family, target_families, gap_types]
          required_outputs: [canonical_record_json, exact_source_span, paper_key, condition_key, admission_decision]
          auto_promotion: false
          idempotency_key: "doi + source_locator + target_family + condition_key"
          completion_gate: "exact span and structured row point to the same condition"
    ''')


def build_ir(root: Path) -> None:
    ledger = []
    for i, (title, ident, kind, url, decision, wired) in enumerate(SOURCES, 1):
        ledger.append({"source_id": f"S{i:03d}", "language": "English", "title": title,
                       "identifier": ident, "source_type": kind, "url": url,
                       "g01_absorption_decision": decision,
                       "code_wired_in_g01": "yes" if wired else "no",
                       "claim_scope": "method/schema/governance only; not a Ti/TMC HQ-LOSO receipt",
                       "review_status": "SURVEYED_AND_LEDGERED"})
    wcsv(root, "METHOD_IR/g01/SOURCE_LEDGER.csv", ledger)
    wjsonl(root, "METHOD_IR/g01/SOURCE_LEDGER.jsonl", ledger)
    qrows = [{"query_id":f"Q{i:03d}", "query_en":q, "language":"English",
              "result_disposition":"source reviewed and represented in SOURCE_LEDGER",
              "claim_scope":"research support only"} for i, q in enumerate(QUERIES, 1)]
    wcsv(root, "METHOD_IR/g01/SEARCH_QUERY_LOG.csv", qrows)

    methods = [
        ("deterministic four-gate firewall","USE","implemented","blocks non-Ti/TMC direct evidence"),
        ("DOI normalization and paper_key","USE","implemented","stable source identity"),
        ("condition_key hashing","USE","implemented","condition-level dedup/split grouping"),
        ("target semantic firewall","USE","implemented","EL/modulus/hardness/KIC fail closed"),
        ("group-disjoint source split","USE","schema/test contract","prevents source leakage"),
        ("Wilson interval","USE","implemented","uncertainty for verified coverage proportions"),
        ("denominator-safe coverage","USE","implemented","forbids invented coverage percentage"),
        ("source-tracked multi-stage extraction","USE","IR contract","exact span and row co-lineage"),
        ("review-to-primary trace","USE","requeue policy","secondary values not gold"),
        ("confident-learning risk score","DEFER","not implemented in G01","requires labeled audit receipts"),
        ("dataset cartography","DEFER","not implemented in G01","requires training dynamics/model window"),
        ("capture-recapture corpus size","DROP","not implemented","dependent duplicated fleets violate assumptions"),
        ("LLM single-pass auto-admission","DROP","blocked","non-deterministic and insufficient evidence trace"),
        ("random row split","DROP","blocked","source/specimen leakage"),
        ("review value as gold row","DROP","blocked","condition and primary evidence loss"),
    ]
    wcsv(root, "METHOD_IR/g01/algorithm_absorption_matrix.csv",
         [{"method":a,"decision":b,"status":c,"reason":d} for a,b,c,d in methods])

    wt(root, "METHOD_IR/g01/METHOD_IR.md", '''
        # G01 METHOD_IR — HQ corpus completeness versus ten fleets

        ## Deleted invalid requirement
        A single coverage percentage based on file/member counts is invalid. Fleet members are carriers, not eligible HQ rows. Coverage is legal only after freezing eligible `(paper_key, condition_key, target_family, source_surface)` obligations and verifying the exact row/span join. The matrix therefore reports blank coverage with `NOT_FROZEN` rather than manufactured precision.

        ## Evidence ladder
        Package control → direct archive member profile → source identity and exact table/figure/text span → canonical structured row joined to the same condition → HQ admission/source-group split receipt → HQ-LOSO metric receipt. This window implements the first four control surfaces; it does not claim the last two.

        ## Canonical grain
        The irreducible row is `paper_key × condition_key × target_family × target_variant × source_locator`. DOI is preferred for `paper_key`; normalized bibliographic fields are the fallback. `condition_key` binds matrix, reinforcement, ordered process chain, heat treatment, specimen/test condition and target semantics.

        ## Four gates
        1. Base element: direct evidence requires Ti matrix; Ti compounds/catalysts/minor Ti additions fail.
        2. Family: only registered Ti alloy, TiAl and Ti-matrix-composite families pass.
        3. Naming range: canonical Ti naming and, for TMC, both matrix and reinforcement evidence.
        4. Other-alloy ceiling: 0% in direct training/calibration/evaluation. A separate method-transfer lane may be ≤5% per controlled batch and never contributes direct evidence or ranking.

        ## Target semantics
        EL separates A/At from Ag/Agt and reduction of area. Static tensile Young modulus is separated from compression, flexural, dynamic, indentation, reduced and storage modulus. Vickers requires scale/load. KIC fails closed without parameter and validity evidence; KQ/J/CTOD/Charpy are never renamed KIC.

        ## Negative evidence and requeue
        Confirmed failures remain immutable typed negative evidence and are allowed only for admission-risk/parser/OOD diagnostics. The DOI queue is executable and idempotent; each result must return a canonical row and exact source span joined by `condition_key`. No result is auto-promoted.

        ## Fleet verdict
        B001–B010 are YES for incremental work, not blind full re-extraction. B001–B009 continue MAP/requeue until the denominator is frozen. B010 performs own MAP reconciliation and GLOBAL_REDUCE only after upstream receipts. Status remains `below_gate_continue_optimization`.
    ''')
    wt(root, "METHOD_IR/g01/COVERAGE_FORMULAS.md", '''
        # Coverage formulas
        For frozen obligation set `E` and verified evidence-joined subset `V`, `coverage=|V|/|E|`, with `V⊆E`. Package files, members and raw numbers are not eligible denominators. Unknown denominator returns `coverage=null; status=DENOMINATOR_NOT_FROZEN`.

        Wilson 95% interval uses `center=(p+z²/(2n))/(1+z²/n)` and `half=z*sqrt((p(1-p)+z²/(4n))/n)/(1+z²/n)`, `z≈1.96`. Capture-recapture is dropped because fleet corpora are dependent and duplicated.
    ''')
    wjson(root, "reports/SOURCE_LEDGER_SUMMARY.json", {
        "english_sources": len(ledger), "minimum_required": 50, "requirement_met": len(ledger) >= 50,
        "english_search_intents_logged": len(qrows),
        "code_wired_sources": sum(r["code_wired_in_g01"] == "yes" for r in ledger),
        "scope": "method/schema/data governance; no HQ-LOSO receipt",
    })


def build_tests(root: Path) -> None:
    wt(root, "tests/g01_data_hq_fleet_audit/test_firewall.py", r'''
        import sys, unittest
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
        from modules.g01_data_hq_fleet_audit.firewall import audit_batch, audit_record, classify_target_semantics

        class FirewallTests(unittest.TestCase):
            def test_ti64(self): self.assertTrue(audit_record({"material_name":"Ti-6Al-4V","matrix_base":"Ti","material_family":"alpha_beta_ti"})["admitted"])
            def test_tibw_ti65(self): self.assertTrue(audit_record({"material_name":"TiBw/Ti65","matrix_base":"Ti","reinforcement":"TiBw","material_family":"titanium_matrix_composite"})["admitted"])
            def test_tio2(self): self.assertFalse(audit_record({"material_name":"TiO2","paper_title":"titanium dioxide photocatalyst","matrix_base":"oxide","material_family":"ceramic","off_domain":True})["admitted"])
            def test_al_matrix_tmc(self): self.assertFalse(audit_record({"material_name":"TiB reinforced Al","matrix_base":"Al","reinforcement":"TiB","material_family":"titanium_matrix_composite","off_domain":True})["admitted"])
            def test_bare_tmc_review(self):
                out=audit_record({"material_name":"TMC","matrix_base":"","material_family":"titanium_matrix_composite"}); self.assertFalse(out["admitted"]); self.assertEqual(out["row_role"],"audit_repair")
            def test_batch_ceiling(self):
                direct=[{"material_name":"Ti64","matrix_base":"Ti","material_family":"alpha_beta_ti"} for _ in range(19)]
                method={"material_name":"Ni superalloy","matrix_base":"Ni","material_family":"other","corpus_use":"method_transfer_only"}
                self.assertTrue(audit_batch(direct+[method],0.05)["passed"]); self.assertFalse(audit_batch(direct+[method,method],0.05)["passed"])
            def test_el_agt_blocked(self):
                out=classify_target_semantics({"target_raw":"total uniform elongation Agt in tensile test"}); self.assertTrue(out["semantic_block"]); self.assertEqual(out["target_variant"],"total_uniform_elongation")
            def test_modulus_indentation_blocked(self): self.assertTrue(classify_target_semantics({"target_raw":"indentation modulus"})["semantic_block"])
            def test_kq_not_kic(self): self.assertTrue(classify_target_semantics({"target_raw":"fracture toughness KQ"})["semantic_block"])
        if __name__ == "__main__": unittest.main()
    ''')

    wt(root, "tests/g01_data_hq_fleet_audit/test_keys.py", r'''
        import sys, unittest
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
        from modules.g01_data_hq_fleet_audit.keys import make_condition_key, make_paper_key, normalize_doi

        class KeyTests(unittest.TestCase):
            def test_doi(self): self.assertEqual(normalize_doi("https://doi.org/10.1016/J.MSEA.2020.140426."),"10.1016/j.msea.2020.140426")
            def test_bad_doi(self): self.assertIsNone(normalize_doi("not-a-doi"))
            def test_paper_stable(self): self.assertEqual(make_paper_key(doi="doi:10.1000/ABC"),make_paper_key(doi="https://doi.org/10.1000/abc"))
            def test_fallback(self): self.assertEqual(make_paper_key(title="A  Paper",year=2024),make_paper_key(title="a paper",year="2024"))
            def test_condition_changes(self):
                a={"paper_key":"paper_x","material_name":"Ti64","target_family":"UTS","test_temperature_c":25}; b=dict(a,test_temperature_c=700)
                self.assertNotEqual(make_condition_key(a),make_condition_key(b))
        if __name__ == "__main__": unittest.main()
    ''')

    wt(root, "tests/g01_data_hq_fleet_audit/test_fleet.py", r'''
        import json, sys, tempfile, unittest, zipfile
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
        from modules.g01_data_hq_fleet_audit.fleet import ArchiveIdentityError, profile_zip, safe_coverage, wilson_interval

        class FleetTests(unittest.TestCase):
            def make_zip(self, package="B006"):
                tmp=tempfile.TemporaryDirectory(); p=Path(tmp.name)/"TITMC_V7_AGENT_OS_LIT_B006_OF_010.zip"
                control={"package_id":package,"package_index":6,"package_count":10,"domain":"ti_tmc","default_mode":"CARRIER_MAP","core_fingerprint":"abc"}
                with zipfile.ZipFile(p,"w") as z:
                    z.writestr("__PACKAGE_CONTROL__/PACKAGE_CONTROL.json",json.dumps(control)); z.writestr("PAYLOAD/LITERATURE/a.xml","<x/>"); z.writestr("PAYLOAD/TABLES_DATA/b.csv","a,b\n")
                return tmp,p
            def test_profile(self):
                tmp,p=self.make_zip()
                try: out=profile_zip(p); self.assertEqual(out["package_id"],"B006"); self.assertEqual(out["payload_members"],2)
                finally: tmp.cleanup()
            def test_mismatch(self):
                tmp,p=self.make_zip("B007")
                try:
                    with self.assertRaises(ArchiveIdentityError): profile_zip(p)
                finally: tmp.cleanup()
            def test_unknown_denominator(self): self.assertEqual(safe_coverage(5,None)["status"],"DENOMINATOR_NOT_FROZEN")
            def test_verified(self): self.assertEqual(safe_coverage(5,10)["coverage"],0.5)
            def test_wilson(self): lo,hi=wilson_interval(5,10); self.assertLess(lo,0.5); self.assertGreater(hi,0.5)
        if __name__ == "__main__": unittest.main()
    ''')


def build_reports(root: Path) -> None:
    wt(root, "reports/G01_EXECUTIVE_REPORT.md", '''
        # G01 Executive Report

        Inputs grounded: sole authority pack `TIAI_WEB36_V24_AGENT_NATIVE_ONE_WAVE_FULL_20260717.zip`; prompt/control packs; G01 mission MD; direct B006–B010 archive names. B001–B005 are manifest-grounded only and are not falsely represented as raw archives scanned in this window.

        The primary gap is not file volume. It is the absence of a frozen eligible obligation set and verified join among source identity, exact fulltext span and canonical condition row. Therefore the coverage matrix contains no invented percentage. Every legal coverage cell is `NOT_FROZEN`.

        Delivered: executable four-gate firewall; paper/condition keys; target-semantics firewall; fleet ZIP identity profiler; denominator-safe coverage/Wilson interval; 30-DOI requeue; 15-DOI negative-evidence queue; machine-readable admission schema; 60+ English source ledger; tests, compile/smoke receipts, apply instructions and checksums.

        No model was trained. No HQ-LOSO receipt exists. FULLSCORE and PRODUCTION_CHAMPION are prohibited. Status: `below_gate_continue_optimization`.
    ''')
    wjson(root, "reports/INPUT_AUDIT.json", {
        "authority":{"name":"TIAI_WEB36_V24_AGENT_NATIVE_ONE_WAVE_FULL_20260717.zip","uploaded":True,"role":"sole authority pack","repository_baseline":"sddvacav/tiai-agent-os@3008e56"},
        "prompt_packs":[{"name":"TIAI_WEB36_V24_G6_WEB99_DIRECT_DELIVER_PROMPTS_ONLY_20260717.zip","uploaded":True},{"name":"06_彻夜双模型_GPT56_Grok_上传用.zip","uploaded":True}],
        "exclusive_md":{"name":"G01_DATA_HQ_CORPUS_FLEET_AUDIT.md","uploaded":True},
        "fleet":{"direct_archive_names_confirmed":["B006","B007","B008","B009","B010"],"raw_archives_not_directly_uploaded_in_window":["B001","B002","B003","B004","B005"],"all_ten_grounded_by_fleet_manifest":True,"member_profile_counts_are_approximate_manifest_values":True,"raw_byte_scan_in_build_runner":False},
        "existing_module_grep":{"query":"g01_data_hq_fleet_audit","result":"no matching module at authority baseline; additive implementation"},
        "evidence_classes":["DIRECT_UPLOAD_NAME_CONFIRMED","FLEET_MANIFEST_GROUNDED","PROJECT_SOURCE_AUDIT_ROW_GROUNDED","WEB_PRIMARY_SOURCE_SURVEYED"],
    })

    wt(root, "CLAIM_BOUNDARY.md", '''
        # CLAIM BOUNDARY
        - Domain is Ti alloys and Ti-matrix composites only. Other materials are method-transfer-only or negative evidence.
        - B006–B010 archive names were directly uploaded. B001–B005 were not; their profiles are manifest-grounded, not raw-scan claims.
        - Fleet member counts are approximate carrier-manifest values, never HQ row counts or coverage denominators.
        - No family×target×source denominator is frozen; coverage remains null/blank with `NOT_FROZEN`.
        - Existing audit rows are diagnostic candidates, not automatically HQ. Off-domain, review-derived, duplicate/conflicted and semantic failures are blocked.
        - No model training, calibration, source holdout or HQ-LOSO run is included.
        - No R², FULLSCORE, PRODUCTION_CHAMPION or platform/publication performance claim is made.
        - KIC is retained in schema but fails closed without a dedicated validity receipt.
        - Final status: `below_gate_continue_optimization`.
    ''')
    wt(root, "BLOCKERS.md", '''
        # BLOCKERS
        1. B001–B005 raw archives are absent from this window; only manifest/control profiles are grounded.
        2. The global eligible DOI/condition/target/source denominator is not frozen.
        3. No all-fleet exact join receipt links canonical structured rows to fulltext spans.
        4. Review-derived values require primary-source trace; 30 priority DOI tasks are queued.
        5. Audit rows contain off-domain/semantic contamination; 15 representative failures are negative evidence.
        6. No HQ-LOSO model receipt exists; FULLSCORE remains blocked.
    ''')
    wt(root, "LOCAL_CODEX_APPLY.md", r'''
        # LOCAL CODEX APPLY
        Product destination: `E:\Generated\tiai-agent-os`
        ```powershell
        $Pkg = Resolve-Path ".\G01_DATA_HQ_CORPUS_FLEET_AUDIT_FINAL_20260718"
        $Dst = "E:\Generated\tiai-agent-os"
        Get-Content "$Pkg\SHA256SUMS.txt" | ForEach-Object {
          $parts = $_ -split "  ", 2
          $actual = (Get-FileHash -Algorithm SHA256 (Join-Path $Pkg $parts[1])).Hash.ToLower()
          if ($actual -ne $parts[0]) { throw "SHA256 mismatch: $($parts[1])" }
        }
        New-Item -ItemType Directory -Force "$Dst\modules", "$Dst\DATA", "$Dst\METHOD_IR", "$Dst\tests" | Out-Null
        Copy-Item "$Pkg\modules\g01_data_hq_fleet_audit" "$Dst\modules\" -Recurse -Force
        Copy-Item "$Pkg\DATA\g01" "$Dst\DATA\" -Recurse -Force
        Copy-Item "$Pkg\METHOD_IR\g01" "$Dst\METHOD_IR\" -Recurse -Force
        Copy-Item "$Pkg\tests\g01_data_hq_fleet_audit" "$Dst\tests\" -Recurse -Force
        Set-Location $Dst
        python -m unittest discover -s tests/g01_data_hq_fleet_audit -p "test_*.py" -v
        python -m compileall -q modules/g01_data_hq_fleet_audit
        python -m modules.g01_data_hq_fleet_audit smoke --examples DATA/g01/firewall_examples.jsonl --gaps DATA/g01/hq_gap_dois.jsonl
        ```
        Local work ends after copy, tests and receipt return. Do not re-extract literature, invent denominators or claim HQ-LOSO.
    ''')
    wt(root, "README.md", '''
        # G01 FINAL delivery
        Apply-ready Ti/TMC data/HQ/fleet audit. Product write scope is limited to `modules/g01_data_hq_fleet_audit/**`, `DATA/g01/**`, and `METHOD_IR/g01/**`. Tests/reports/root governance files are delivery verification artifacts.
    ''')


def validate_static(root: Path) -> dict:
    with (root / "DATA/g01/fleet_coverage_matrix.csv").open(encoding="utf-8") as f:
        matrix_rows = sum(1 for _ in csv.DictReader(f))
    gaps = sum(1 for line in (root / "DATA/g01/hq_gap_dois.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
    sources = sum(1 for _ in csv.DictReader((root / "METHOD_IR/g01/SOURCE_LEDGER.csv").open(encoding="utf-8")))
    queries = sum(1 for _ in csv.DictReader((root / "METHOD_IR/g01/SEARCH_QUERY_LOG.csv").open(encoding="utf-8")))
    required = ["DATA/g01/fleet_coverage_matrix.csv","DATA/g01/hq_gap_dois.jsonl","DATA/g01/admission_schema.yaml","LOCAL_CODEX_APPLY.md","CLAIM_BOUNDARY.md","BLOCKERS.md"]
    missing = [p for p in required if not (root / p).exists()]
    checks = {"matrix_rows":matrix_rows,"gap_dois":gaps,"english_sources":sources,"english_queries":queries,"missing":missing}
    if matrix_rows != 840 or gaps < 20 or sources < 50 or queries < 50 or missing:
        raise RuntimeError(f"static acceptance failed: {checks}")
    return checks


def run_receipts(root: Path) -> None:
    env = os.environ.copy(); env["PYTHONPATH"] = str(root)
    commands = [
        ("TEST_RECEIPT.txt", [sys.executable,"-m","unittest","discover","-s","tests/g01_data_hq_fleet_audit","-p","test_*.py","-v"]),
        ("PYCOMPILE_RECEIPT.txt", [sys.executable,"-m","compileall","-q","modules/g01_data_hq_fleet_audit"]),
        ("SMOKE_RECEIPT.txt", [sys.executable,"-m","modules.g01_data_hq_fleet_audit","smoke","--examples","DATA/g01/firewall_examples.jsonl","--gaps","DATA/g01/hq_gap_dois.jsonl"]),
    ]
    for name, cmd in commands:
        proc = subprocess.run(cmd, cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        wt(root, f"reports/{name}", "$ " + " ".join(cmd) + "\n\n" + proc.stdout + f"\nexit_code={proc.returncode}\n")
        if proc.returncode: raise RuntimeError(f"{name} failed\n{proc.stdout}")


def finalize(root: Path, out: Path) -> Path:
    checks = validate_static(root)
    run_receipts(root)
    files = []
    for p in sorted(x for x in root.rglob("*") if x.is_file() and "__pycache__" not in x.parts and x.name not in {"RETURN_MANIFEST.json","SHA256SUMS.txt"}):
        files.append({"path":p.relative_to(root).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha256(p)})
    manifest = {
        "package_name":PACKAGE,"status":STATUS,"domain":"ti_tmc",
        "authority_baseline":"sddvacav/tiai-agent-os@3008e56",
        "write_scope":["modules/g01_data_hq_fleet_audit/**","DATA/g01/**","METHOD_IR/g01/**"],
        "delivery_only":["tests/**","reports/**","LOCAL_CODEX_APPLY.md","CLAIM_BOUNDARY.md","BLOCKERS.md","SHA256SUMS.txt"],
        "acceptance":checks,
        "hard_requirements":{"coverage_matrix":True,"hq_gap_doi_queue":True,"admission_schema":True,"four_gate_firewall":True,"fleet_yes_no_decisions":True,"english_source_ledger_ge_50":True,"tests":"PASS","pycompile":"PASS","smoke":"PASS"},
        "claims":{"model_trained":False,"hq_loso_receipt":False,"fullscore":False,"production_champion":False},
        "files_excluding_manifest_and_checksums":files,
    }
    wjson(root,"RETURN_MANIFEST.json",manifest)
    sums=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file() and "__pycache__" not in x.parts and x.name != "SHA256SUMS.txt"):
        sums.append(f"{sha256(p)}  {p.relative_to(root).as_posix()}")
    wt(root,"SHA256SUMS.txt","\n".join(sums)+"\n")
    zip_path=out/f"{PACKAGE}.zip"
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(x for x in root.rglob("*") if x.is_file() and "__pycache__" not in x.parts):
            z.write(p,arcname=f"{PACKAGE}/{p.relative_to(root).as_posix()}")
    print(json.dumps({"status":STATUS,"package_dir":str(root),"zip":str(zip_path),"zip_sha256":sha256(zip_path),"acceptance":checks},sort_keys=True))
    return zip_path


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir",required=True); args=ap.parse_args()
    out=Path(args.output_dir).resolve(); out.mkdir(parents=True,exist_ok=True); root=out/PACKAGE
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    build_modules(root); build_data(root); build_ir(root); build_tests(root); build_reports(root); finalize(root,out)
    return 0

if __name__ == "__main__": raise SystemExit(main())
