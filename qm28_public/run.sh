#!/usr/bin/env bash
set -euxo pipefail
mkdir -p qm28_public/out
printf 'QM28 public runner OK\n' > qm28_public/out/smoke.txt
python - <<'PY'
import zipfile, pathlib
p=pathlib.Path('qm28_public/out/SMOKE.zip')
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
    z.write('qm28_public/out/smoke.txt','smoke.txt')
PY
