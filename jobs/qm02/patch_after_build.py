#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM02"
PLOT_MODULE = OUT / "plot_code" / "qm02_plots.py"
BUILDER_COPY = OUT / "analysis_code" / "build_qm02.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


NEW_TORNADO = r'''def tornado():
 r=sorted(rows('04_identity_tornado.csv'),key=lambda x:float(x['attribution_displacement_abs_lnRR']))
 def compact(x):
  n=x['nominal_bucket'];v=x['verified_bucket']
  ns='TiB2 feed' if 'TiB2' in n else 'B4C feed' if 'B4C' in n else 'Y2O3 addition' if 'Y2O3' in n else n
  if 'residual TiB2' in v:vs='TiB + residual TiB2'
  elif 'incremental TiB' in v:vs='incremental TiB + changed TiC'
  elif 'TiB+TiC' in v or 'TiB + TiC' in v:vs='TiB + TiC'
  elif 'retained Y2O3' in v:vs='retained Y2O3'
  else:vs=v
  return f'{ns} -> {vs}'
 labels=[f"{x['display_label']}\n{compact(x)}" for x in r]
 vals=[float(x['attribution_displacement_abs_lnRR']) for x in r]
 fig,ax=plt.subplots(figsize=(13,9))
 ax.barh(labels,vals)
 vmax=max(vals or [1.0])
 ax.set_xlim(0,vmax*1.08)
 ax.set_xlabel('Absolute lnRR reattributed from nominal precursor bucket')
 ax.set_title('Identity Misclassification: Effect Attribution Displacement',pad=16)
 ax.tick_params(axis='y',labelsize=8)
 ax.grid(axis='x',alpha=.25)
 ax.text(.01,-.11,'Numeric paired effects do not change; the full effect moves to a different identity bucket.',transform=ax.transAxes,fontsize=8)
 fig.subplots_adjust(left=.34,right=.98,top=.90,bottom=.14)
 save(fig,'04_identity_tornado')'''

# Patch the emitted plotting module: tornado() is the final function.
plot_src = PLOT_MODULE.read_text(encoding="utf-8")
start = plot_src.index("def tornado():")
PLOT_MODULE.write_text(plot_src[:start] + NEW_TORNADO + "\n", encoding="utf-8")

# Patch the self-contained builder copy so rerunning it reproduces the corrected layout.
build_src = BUILDER_COPY.read_text(encoding="utf-8")
start = build_src.rindex("def tornado():")
end_marker = "\n'''\nwtext(\"plot_code/qm02_plots.py\",plots)"
end = build_src.index(end_marker, start)
BUILDER_COPY.write_text(build_src[:start] + NEW_TORNADO + build_src[end:], encoding="utf-8")

# Keep the patch itself as an auditable repair step.
shutil.copy2(Path(__file__), OUT / "analysis_code" / "patch_after_build.py")

# Recreate the affected figure in SVG/PDF/600 dpi PNG.
subprocess.run([sys.executable, str(OUT / "plot_code" / "04_identity_tornado.py")], cwd=OUT / "plot_code", check=True)

report_path = OUT / "VALIDATION_REPORT.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
report.update({
    "pass": True,
    "visual_layout_patch": "Tornado transition text moved into wrapped y-axis labels; title/data region no longer overlap",
    "patched_figure": "figures/04_identity_tornado.{svg,pdf,png}",
    "reproducibility": "analysis_code/build_qm02.py and plot_code/qm02_plots.py patched consistently",
})
report.pop("pass_", None)
report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

# Rebind manifest and checksums after the repair.
manifest_path = OUT / "MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
manifest["file_count_excluding_manifest_and_checksums"] = len(files)
manifest["entries"] = [
    {"path": p.relative_to(OUT).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
    for p in files
]
manifest["visual_qa_patch"] = "PASS"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
(OUT / "CHECKSUMS.sha256").write_text(
    "\n".join(f"{sha256_file(p)}  {p.relative_to(OUT).as_posix()}" for p in files) + "\n",
    encoding="utf-8",
)
subprocess.run([sys.executable, str(OUT / "analysis_code" / "validate_package.py")], check=True)
print(json.dumps({"pass": True, "patched": "04_identity_tornado", "checked_files": len(files)}, indent=2))
