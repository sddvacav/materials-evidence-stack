from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE / "output" / "FINAL_QM36"
TEST = ROOT / "tests" / "test_qm36_outputs.py"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

s = TEST.read_text(encoding="utf-8")
TEST.write_text(s.replace("\\n", "\n"), encoding="utf-8", newline="\n")

manifest_path = ROOT / "MANIFEST.json"
old = json.loads(manifest_path.read_text(encoding="utf-8"))
payload = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
manifest = {
    "window_id": old["window_id"],
    "snapshot_id": old["snapshot_id"],
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "nested_zip_count": len(list(ROOT.rglob("*.zip"))),
    "file_count_excluding_manifest_and_checksums": len(payload),
    "total_payload_bytes": sum(p.stat().st_size for p in payload),
    "files": [
        {"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
        for p in payload
    ],
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

targets = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
(ROOT / "CHECKSUMS.sha256").write_text(
    "".join(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in targets),
    encoding="utf-8",
    newline="\n",
)
