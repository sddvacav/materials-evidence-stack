#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def numeric_values(row: dict[str, str], keys: list[str]) -> list[float] | None:
    values: list[float] = []
    try:
        for key in keys:
            values.append(float(row[key]))
    except (KeyError, TypeError, ValueError):
        return None
    return values


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rows = read_csv(root / "CTE_GND_INPUTS.csv")
    pair_rows = read_csv(root / "PAIR_MATCHES.csv")
    keys = ["delta_alpha_per_k", "delta_t_k", "vf", "burgers_m", "diameter_m", "density_factor", "shear_modulus_pa", "taylor_alpha", "rho_cte_m2", "delta_sigma_mpa"]
    checked = 0
    max_rel = 0.0
    for r in rows:
        values = numeric_values(r, keys)
        if values is None:
            continue
        da, dt, vf, b, d, factor, g, alpha, stored_rho, stored_ds = values
        rho = factor * abs(da) * dt * vf / ((1.0 - vf) * b * d)
        ds = alpha * g * b * math.sqrt(rho) / 1.0e6
        max_rel = max(max_rel, abs(rho - stored_rho) / max(abs(stored_rho), 1.0), abs(ds - stored_ds) / max(abs(stored_ds), 1.0e-12))
        checked += 1
    result = {
        "formula_rows_recomputed": checked,
        "matched_pair_rows": len(pair_rows),
        "max_relative_error": round(max_rel, 12),
        "status": "PASS" if checked == 3 and len(pair_rows) == 10 and max_rel < 1.0e-9 else "FAIL"
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
