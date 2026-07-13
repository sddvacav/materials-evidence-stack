#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_triplet(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def finite(value: str | None) -> bool:
    if value in (None, "", "NA", "NOT_IDENTIFIABLE"):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def plot_distribution(root: Path) -> None:
    rows = [r for r in read_csv(root / "figure_data" / "rho_delta_sigma_distribution.csv") if finite(r.get("rho_m2"))]
    fig, ax = plt.subplots(figsize=(8.4, 5.8))
    groups: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        groups.setdefault(r["source_group"], []).append(r)
    for group, items in groups.items():
        xs = [float(r["rho_m2"]) for r in items]
        ys = [float(r["delta_sigma_mpa"]) for r in items]
        xlo = [x - float(r["rho_retention_low_m2"]) for x, r in zip(xs, items)]
        xhi = [float(r["rho_retention_high_m2"]) - x for x, r in zip(xs, items)]
        ylo = [y - float(r["delta_sigma_retention_low_mpa"]) for y, r in zip(ys, items)]
        yhi = [float(r["delta_sigma_retention_high_mpa"]) - y for y, r in zip(ys, items)]
        ax.errorbar(xs, ys, xerr=[xlo, xhi], yerr=[ylo, yhi], fmt="o", capsize=2.5, label=group)
    ax.set_xscale("log")
    ax.set_xlabel(r"Equivalent or model-estimated dislocation density, $\rho$ (m$^{-2}$)")
    ax.set_ylabel(r"Dislocation-strengthening term, $\Delta\sigma$ (MPa)")
    ax.set_title("CTE/GND model estimates across the bound Ti/TMC evidence")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(title="Evidence family", fontsize=8)
    ax.text(0.01, -0.22,
            "n=3 independent quantitative papers; 13 estimable scenarios. Error bars are the declared 10–100% retained-density envelope, not a statistical CI. Statistical cross-paper CI/PI: NOT IDENTIFIABLE.",
            transform=ax.transAxes, fontsize=8, va="top", wrap=True)
    fig.subplots_adjust(bottom=0.25)
    save_triplet(fig, root / "figures" / "QM34_F1_rho_delta_sigma_distribution")


def plot_surface(root: Path) -> None:
    rows = read_csv(root / "figure_data" / "cte_dt_sensitivity_surface.csv")
    alphas = sorted({float(r["delta_alpha_microstrain_per_k"]) for r in rows})
    dts = sorted({float(r["delta_t_k"]) for r in rows})
    lookup = {(float(r["delta_alpha_microstrain_per_k"]), float(r["delta_t_k"])): float(r["delta_sigma_mpa"]) for r in rows}
    z = [[lookup[(a, dt)] for a in alphas] for dt in dts]
    fig, ax = plt.subplots(figsize=(8.2, 5.8))
    image = ax.imshow(z, origin="lower", aspect="auto",
                      extent=[min(alphas), max(alphas), min(dts), max(dts)])
    fig.colorbar(image, ax=ax, label=r"$\Delta\sigma_{CTE}$ (MPa)")
    ax.set_xlabel(r"CTE mismatch, $|\Delta\alpha|$ ($10^{-6}$ K$^{-1}$)")
    ax.set_ylabel(r"Cooling interval, $\Delta T$ (K)")
    ax.set_title(r"Sensitivity of $\Delta\sigma_{CTE}$ to CTE mismatch and cooling interval")
    ax.text(0.01, -0.20,
            "Zhao-model anchor: Vf=3.5 vol.%, d=5 µm, B=6, G=41.903 GPa, b=0.295 nm, α=1. n=1 paper; 2,601 grid points. This is a constrained response surface, not a confidence or prediction interval.",
            transform=ax.transAxes, fontsize=8, va="top", wrap=True)
    fig.subplots_adjust(bottom=0.23)
    save_triplet(fig, root / "figures" / "QM34_F2_cte_dt_sensitivity_surface")


def plot_proxy(root: Path) -> None:
    rows = read_csv(root / "figure_data" / "measurement_proxy_calibration.csv")
    points = [r for r in rows if finite(r.get("kam_deg")) and finite(r.get("cte_term_mpa"))]
    x = [float(r["kam_deg"]) for r in points]
    y = [float(r["cte_term_mpa"]) for r in points]
    xm = sum(x) / len(x)
    ym = sum(y) / len(y)
    denom = sum((v - xm) ** 2 for v in x)
    slope = sum((a - xm) * (b - ym) for a, b in zip(x, y)) / denom
    intercept = ym - slope * xm
    xline = [min(x), max(x)]
    yline = [intercept + slope * v for v in xline]
    fig, ax = plt.subplots(figsize=(7.8, 5.6))
    ax.scatter(x, y, s=42)
    ax.plot(xline, yline, linewidth=1.2)
    for r in points:
        ax.annotate(r["sample_uid"], (float(r["kam_deg"]), float(r["cte_term_mpa"])), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set_xlabel("Kernel average misorientation, KAM (degrees)")
    ax.set_ylabel(r"Source thermal-mismatch term, $\Delta\sigma_{CTE}$ (MPa)")
    ax.set_title("KAM–CTE-term proxy comparison (not a cross-method calibration)")
    ax.grid(True, alpha=0.25)
    ax.text(0.01, -0.25,
            "n=4 samples from 1 independent paper; Pearson r=0.832, Spearman ρ=0.800. The association is fully confounded by powder/process route. TEM/XRD-to-KAM calibration and statistical CI/PI are NOT IDENTIFIABLE.",
            transform=ax.transAxes, fontsize=8, va="top", wrap=True)
    fig.subplots_adjust(bottom=0.28)
    save_triplet(fig, root / "figures" / "QM34_F3_measurement_proxy_calibration")


def plot_forest(root: Path) -> None:
    rows = read_csv(root / "figure_data" / "contribution_share_forest.csv")
    labels = [r["pair_uid"] for r in rows]
    y = list(range(len(rows)))
    points = [float(r["share_pct"]) for r in rows]
    low = [float(r["retention_share_low_pct"]) for r in rows]
    high = [float(r["retention_share_high_pct"]) for r in rows]
    xerr_lo = [p - l for p, l in zip(points, low)]
    xerr_hi = [h - p for p, h in zip(points, high)]
    fig, ax = plt.subplots(figsize=(9.0, 6.6))
    for i, r in enumerate(rows):
        marker = "o" if r["audit_status"] == "ADMISSIBLE_SOURCE_TERM" else "x"
        ax.errorbar(points[i], y[i], xerr=[[xerr_lo[i]], [xerr_hi[i]]], fmt=marker, capsize=2.5)
    ax.axvline(0, linewidth=1.0)
    ax.axvline(100, linewidth=1.0, linestyle="--")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel(r"Source $\Delta\sigma_{CTE}$ / observed matched $\Delta$YS (%)")
    ax.set_title("Thermal-mismatch contribution-share audit")
    ax.grid(True, axis="x", alpha=0.25)
    ax.text(0.01, -0.18,
            "10 matched pairs from 2 independent papers. Circles: source terms retained for descriptive audit; crosses: circular/inconsistent source budgets. Bars show 10–100% retained-density scenarios, not statistical CI. Universal pooled share and new-paper PI: NOT IDENTIFIABLE.",
            transform=ax.transAxes, fontsize=8, va="top", wrap=True)
    fig.subplots_adjust(left=0.20, bottom=0.21)
    save_triplet(fig, root / "figures" / "QM34_F4_dislocation_contribution_share_forest")


PLOTS = {
    "distribution": plot_distribution,
    "surface": plot_surface,
    "proxy": plot_proxy,
    "forest": plot_forest,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--only", choices=sorted(PLOTS))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.only:
        PLOTS[args.only](root)
    else:
        for func in PLOTS.values():
            func(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
