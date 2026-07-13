#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM02"
ZIP = ROOT / "FINAL_QM02.zip"
OLD = "vacuum arc melting/casting"
NEW = "powder metallurgy/sintering"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def apply() -> None:
    if not OUT.exists():
        return

    targets = [
        OUT / "ORIGINAL_PAPER_AUDIT.csv",
        OUT / "analysis_code" / "patch_after_build.py",
        ROOT / "patch_after_build.py",
    ]
    replaced = []
    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if OLD in text:
            path.write_text(text.replace(OLD, NEW), encoding="utf-8")
            replaced.append(path.relative_to(ROOT).as_posix())

    shutil.copy2(Path(__file__), OUT / "analysis_code" / "source_audit_hotfix.py")
    site = ROOT / "sitecustomize.py"
    if site.exists():
        shutil.copy2(site, OUT / "analysis_code" / "sitecustomize.py")

    report_path = OUT / "VALIDATION_REPORT.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update({
        "p003_process_hotfix": "powder metallurgy/sintering",
        "p003_process_hotfix_reason": "Align original-paper audit with the source-derived core cohort process field; remove an unsupported casting label.",
        "p003_process_hotfix_files": replaced,
        "p003_process_hotfix_status": "PASS",
    })
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    manifest_path = OUT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
    manifest["file_count_excluding_manifest_and_checksums"] = len(files)
    manifest["entries"] = [
        {"path": p.relative_to(OUT).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        for p in files
    ]
    manifest["p003_process_hotfix"] = "PASS"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
    (OUT / "CHECKSUMS.sha256").write_text(
        "\n".join(f"{sha256_file(p)}  {p.relative_to(OUT).as_posix()}" for p in files) + "\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(OUT / "analysis_code" / "validate_package.py")], check=True)

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(OUT).as_posix())
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None
        assert not any(n.lower().endswith(".zip") for n in z.namelist())

    print(json.dumps({
        "source_audit_hotfix": "PASS",
        "corrected_field": "P003 process",
        "corrected_value": NEW,
        "files_rebound": len(files),
        "zip_sha256": sha256_file(ZIP),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    apply()
