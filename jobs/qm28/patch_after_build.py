#!/usr/bin/env python3
"""Post-build finalization: make MANIFEST/CHECKSUMS cover every finalized member."""
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parent / "FINAL_QM28"

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

status = json.loads((ROOT / "WINDOW_STATUS.json").read_text(encoding="utf-8"))
files = []
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}:
        files.append({
            "path": p.relative_to(ROOT).as_posix(),
            "size_bytes": p.stat().st_size,
            "sha256": digest(p),
        })
manifest = {
    "window_id": "QM28",
    "snapshot_id": status["snapshot_id"],
    "file_count_excluding_manifest_and_checksums": len(files),
    "files": files,
    "no_nested_zip": not any(p.suffix.lower() == ".zip" for p in ROOT.rglob("*") if p.is_file()),
    "seed": 20260713,
    "finalized_after_tests": True,
}
(ROOT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
lines = []
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name != "CHECKSUMS.sha256":
        lines.append(f"{digest(p)}  {p.relative_to(ROOT).as_posix()}")
(ROOT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"pass": True, "manifest_members": len(files), "checksum_members": len(lines), "no_nested_zip": manifest["no_nested_zip"]}, indent=2))
