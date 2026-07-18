from __future__ import annotations

import compileall
import csv
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

NAME = "TIAI_G06_UQ_OOD_AD_REJECT_FINAL_20260718"
ROOT = Path("g06_remote/output") / NAME
MOD = Path("modules/w08_mq_uq_conformal_calibration")
DATA = Path("DATA/g06")


def norm(s: str) -> str:
    s = textwrap.dedent(s).lstrip("\n")
    return s if s.endswith("\n") else s + "\n"


def put(rel: str | Path, text: str) -> Path:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(norm(text), encoding="utf-8", newline="\n")
    return p


def put_json(rel: str | Path, obj: object) -> Path:
    return put(rel, json.dumps(obj, ensure_ascii=False, indent=2))


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def all_files() -> list[Path]:
    return sorted((p for p in ROOT.rglob("*") if p.is_file()), key=lambda p: p.as_posix())


def patch_for(paths: list[Path]) -> str:
    out: list[str] = []
    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        out += [f"diff --git a/{rel} b/{rel}\n", "new file mode 100644\n"]
        out += list(difflib.unified_diff([], lines, fromfile="/dev/null", tofile=f"b/{rel}", n=3))
    return "".join(out)


def main() -> int:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)

    put(MOD / "__init__.py", r'''
    """G06 fail-closed UQ/OOD/AD policy for titanium alloys and Ti-matrix composites."""
    from .conformal import (
        CalibrationRecord, CalibrationResult, GroupRule, MondrianCalibrator,
        coverage_audit, cqr_interval, cqr_scores, finite_sample_quantile,
        split_interval, wilson_lower_bound,
    )
    from .decision import evaluate_four_layers
    from .contracts import build_claim_response, build_reject_card, validate_reject_card
    from .types import Action, ClaimTier, Decision, LayerAssessment, Status

    __all__ = [
        "CalibrationRecord", "CalibrationResult", "GroupRule", "MondrianCalibrator",
        "coverage_audit", "cqr_interval", "cqr_scores", "finite_sample_quantile",
        "split_interval", "wilson_lower_bound", "evaluate_four_layers",
        "build_claim_response", "build_reject_card", "validate_reject_card",
        "Action", "ClaimTier", "Decision", "LayerAssessment", "Status",
    ]
    ''')

    put(MOD / "types.py", r'''
    from __future__ import annotations
    from dataclasses import asdict, dataclass, field
    from enum import Enum
    from typing import Any

    class Status(str, Enum):
        PASS = "PASS"
        WARN = "WARN"
        BLOCK = "BLOCK"
        UNASSESSED = "UNASSESSED"

    class Action(str, Enum):
        ACCEPT_BOUNDED = "ACCEPT_BOUNDED"
        SCREENING_ONLY = "SCREENING_ONLY"
        REJECT_RECOMMENDATION = "REJECT_RECOMMENDATION"

    class ClaimTier(str, Enum):
        T0_WITHHOLD = "T0_WITHHOLD"
        T1_SCREENING = "T1_SCREENING"
        T2_BOUNDED_INTERNAL = "T2_BOUNDED_INTERNAL"
        T3_EXTERNAL_CANDIDATE = "T3_EXTERNAL_CANDIDATE"

    @dataclass(frozen=True)
    class LayerAssessment:
        layer: str
        status: Status
        reason_codes: tuple[str, ...] = ()
        evidence: dict[str, Any] = field(default_factory=dict)
        message_zh: str = ""

        def to_dict(self) -> dict[str, Any]:
            d = asdict(self)
            d["status"] = self.status.value
            d["reason_codes"] = list(self.reason_codes)
            return d

    @dataclass(frozen=True)
    class Decision:
        action: Action
        claim_tier: ClaimTier
        layers: tuple[LayerAssessment, ...]
        reason_codes: tuple[str, ...]
        public_message_zh: str
        external_claim_eligible: bool = False

        def to_dict(self) -> dict[str, Any]:
            return {
                "action": self.action.value,
                "claim_tier": self.claim_tier.value,
                "layers": [x.to_dict() for x in self.layers],
                "reason_codes": list(self.reason_codes),
                "public_message_zh": self.public_message_zh,
                "external_claim_eligible": self.external_claim_eligible,
            }
    ''')

    put(MOD / "conformal.py", r'''
    from __future__ import annotations
    import math
    from dataclasses import dataclass
    from typing import Iterable, Mapping, Sequence

    def _alpha(alpha: float) -> None:
        if not 0.0 < alpha < 1.0:
            raise ValueError("alpha must be in (0,1)")

    def _scores(values: Iterable[float]) -> list[float]:
        x = [float(v) for v in values]
        if not x or any(not math.isfinite(v) or v < 0 for v in x):
            raise ValueError("scores must be non-empty, finite and non-negative")
        return x

    def finite_sample_quantile(scores: Iterable[float], alpha: float) -> float:
        """q = sorted(scores)[min(ceil((n+1)*(1-alpha)), n)-1]."""
        _alpha(alpha)
        s = sorted(_scores(scores))
        k = min(len(s), max(1, math.ceil((len(s) + 1) * (1 - alpha))))
        return s[k - 1]

    def split_interval(point: float, q: float, physical_lower: float | None = None) -> tuple[float, float, bool]:
        p, q = float(point), float(q)
        if not math.isfinite(p) or not math.isfinite(q) or q < 0:
            raise ValueError("invalid interval input")
        lo, hi, clipped = p - q, p + q, False
        if physical_lower is not None and lo < physical_lower:
            lo, clipped = float(physical_lower), True
        return lo, hi, clipped

    def cqr_scores(y: Sequence[float], lo: Sequence[float], hi: Sequence[float]) -> list[float]:
        if not y or not (len(y) == len(lo) == len(hi)):
            raise ValueError("CQR arrays must have equal non-zero length")
        out: list[float] = []
        for yy, ll, hh in zip(y, lo, hi):
            yy, ll, hh = float(yy), float(ll), float(hh)
            if ll > hh:
                raise ValueError("lower quantile exceeds upper quantile")
            out.append(max(ll - yy, yy - hh, 0.0))
        return out

    def cqr_interval(lo: float, hi: float, q: float, physical_lower: float | None = None) -> tuple[float, float, bool]:
        lo, hi, q = float(lo), float(hi), float(q)
        if lo > hi or q < 0 or not all(math.isfinite(v) for v in (lo, hi, q)):
            raise ValueError("invalid CQR input")
        a, b, clipped = lo - q, hi + q, False
        if physical_lower is not None and a < physical_lower:
            a, clipped = float(physical_lower), True
        return a, b, clipped

    def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
        if total <= 0 or successes < 0 or successes > total or z <= 0:
            raise ValueError("invalid Wilson inputs")
        p = successes / total
        den = 1 + z*z/total
        centre = p + z*z/(2*total)
        margin = z * math.sqrt((p*(1-p) + z*z/(4*total))/total)
        return max(0.0, (centre - margin) / den)

    def coverage_audit(intervals: Sequence[tuple[float,float]], truths: Sequence[float], nominal: float, floor: float) -> dict[str, float | int | bool]:
        if not intervals or len(intervals) != len(truths):
            raise ValueError("audit arrays must have equal non-zero length")
        if not (0 < nominal < 1 and 0 < floor < 1):
            raise ValueError("coverage targets must be in (0,1)")
        covered, widths = 0, []
        for (lo, hi), y in zip(intervals, truths):
            if lo > hi:
                raise ValueError("invalid interval")
            covered += int(lo <= y <= hi)
            widths.append(hi-lo)
        n = len(truths)
        empirical = covered/n
        return {
            "n": n, "covered": covered, "empirical_coverage": empirical,
            "wilson_lower_95": wilson_lower_bound(covered,n),
            "nominal_coverage": nominal, "coverage_floor": floor,
            "mean_width": sum(widths)/n, "audit_pass": empirical >= floor,
        }

    @dataclass(frozen=True)
    class CalibrationRecord:
        y_true: float
        y_pred: float
        target: str
        family: str
        route: str
        protocol_class: str
        quality: str = "HQ"

    @dataclass(frozen=True)
    class GroupRule:
        name: str
        fields: tuple[str,...]
        min_n: int

        def __post_init__(self) -> None:
            if self.min_n < 1:
                raise ValueError("min_n must be positive")

    @dataclass(frozen=True)
    class CalibrationResult:
        quantile: float
        group_name: str
        group_key: tuple[str,...]
        n_calibration: int
        nominal_coverage: float
        status: str

        def to_dict(self) -> dict[str, object]:
            return {"quantile": self.quantile, "group_name": self.group_name,
                    "group_key": list(self.group_key), "n_calibration": self.n_calibration,
                    "nominal_coverage": self.nominal_coverage, "status": self.status}

    DEFAULT_RULES = (
        GroupRule("target_family_route_protocol", ("target","family","route","protocol_class"), 40),
        GroupRule("target_family_route", ("target","family","route"), 60),
        GroupRule("target_family", ("target","family"), 80),
        GroupRule("target_global", ("target",), 100),
    )

    class MondrianCalibrator:
        """Hard fallback over HQ residual groups; never pools unsupported groups."""
        def __init__(self, alpha: float = .10, rules: Sequence[GroupRule] = DEFAULT_RULES):
            _alpha(alpha)
            if not rules:
                raise ValueError("rules required")
            self.alpha, self.rules, self.records = float(alpha), tuple(rules), ()

        def fit(self, records: Iterable[CalibrationRecord]) -> "MondrianCalibrator":
            r = tuple(records)
            if not r or any(not math.isfinite(float(x.y_true)) or not math.isfinite(float(x.y_pred)) for x in r):
                raise ValueError("valid calibration records required")
            self.records = r
            return self

        @staticmethod
        def _key(obj: CalibrationRecord | Mapping[str,str], fields: Sequence[str]) -> tuple[str,...]:
            if isinstance(obj, CalibrationRecord):
                return tuple(str(getattr(obj, f)) for f in fields)
            return tuple(str(obj.get(f, "unknown")) for f in fields)

        def quantile_for(self, query: Mapping[str,str]) -> CalibrationResult:
            if not self.records:
                raise RuntimeError("fit first")
            for i, rule in enumerate(self.rules):
                key = self._key(query, rule.fields)
                selected = [r for r in self.records if r.quality.upper()=="HQ" and self._key(r,rule.fields)==key]
                if len(selected) >= rule.min_n:
                    q = finite_sample_quantile((abs(r.y_true-r.y_pred) for r in selected), self.alpha)
                    return CalibrationResult(q, rule.name, key, len(selected), 1-self.alpha,
                                             "CALIBRATED_GROUP" if i==0 else "CALIBRATED_FALLBACK")
            raise LookupError("no HQ group meets min_n")
    ''')

    put(MOD / "decision.py", r'''
    from __future__ import annotations
    from typing import Any
    from .types import Action, ClaimTier, Decision, LayerAssessment, Status

    ALLOWED_FAMILIES = {"cp-Ti","alpha","near-alpha","alpha+beta","beta","metastable-beta","TiAl","TMC"}
    ALLOWED_ROUTES = {"cast","wrought","AM","PM","HIP","DED"}
    ZH = {
      "FIREWALL_BLOCK":"材料数据防火墙拒绝该输入。", "FIREWALL_UNASSESSED":"材料数据防火墙缺少收据。",
      "UNITS_UNRESOLVED":"性质单位或换算链未解析。", "PROTOCOL_NOT_ADMITTED":"试验协议未通过准入。",
      "MODULUS_SUBTYPE_UNRESOLVED":"弹性模量子类型未解析。", "TARGET_OUT_OF_SCOPE_KIC":"KIC 当前主计划范围外。",
      "PHYSICAL_CONSTRAINT_VIOLATION":"违反成分或性质物理硬约束。", "COMPOSITION_SIMPLEX_INVALID":"成分和超出 simplex 容差。",
      "CHEMICALLY_REMOTE_FAMILY":"未知家族且化学空间远离证据包络。", "UNKNOWN_FAMILY_OR_ROUTE":"家族或工艺未知。",
      "NOVEL_REINFORCEMENT":"增强体类型/尺度超出验证域。", "MANIFOLD_HARD_OOD":"潜空间与最近证据共同硬 OOD。",
      "MANIFOLD_BORDERLINE":"适用域距离进入警戒区。", "MANIFOLD_UNASSESSED":"缺少适用域距离收据。",
      "CALIBRATION_FAILED_AUDIT":"校准覆盖审计失败。", "CALIBRATION_INSUFFICIENT":"校准样本不足。",
      "CALIBRATION_FALLBACK":"仅能使用粗粒度校准回退。", "NO_CALIBRATION_RECEIPT":"缺少校准收据。",
      "HQ_LOSO_REQUIRED":"外部主张缺少 HQ-LOSO 收据。", "INTERVAL_TOO_WIDE":"区间宽度超过硬门。",
      "INTERVAL_WIDE":"区间较宽，仅供筛选。", "NEAREST_EVIDENCE_SPARSE":"同协议最近证据不足。",
      "TAIL_UNSUPPORTED_EXTREME":"尾部信任为 unsupported_extreme。", "TAIL_CANDIDATE_ONLY":"尾部状态低于发布门。",
    }

    def _f(p: dict[str,Any], k: str) -> float | None:
        try:
            return None if p.get(k) is None else float(p[k])
        except (TypeError,ValueError):
            return None

    def _layer(name: str, reasons: list[str], blockers: set[str], evidence: dict[str,Any]) -> LayerAssessment:
        status = Status.BLOCK if any(r in blockers for r in reasons) else (Status.WARN if reasons else Status.PASS)
        return LayerAssessment(name,status,tuple(reasons),evidence,"；".join(ZH.get(r,r) for r in reasons) or "通过")

    def evaluate_four_layers(p: dict[str,Any]) -> Decision:
        target = str(p.get("target_property","unknown")).upper()
        external = str(p.get("requested_claim_mode","internal")).lower() in {"external","publication","public"}

        r1=[]
        fw=str(p.get("firewall_status","UNASSESSED")).upper()
        if fw=="BLOCK": r1.append("FIREWALL_BLOCK")
        elif fw not in {"PASS","WARN"}: r1.append("FIREWALL_UNASSESSED")
        if p.get("units_resolved") is not True: r1.append("UNITS_UNRESOLVED")
        if target=="KIC": r1.append("TARGET_OUT_OF_SCOPE_KIC")
        if target in {"EL","ELONGATION"} and p.get("protocol_admitted") is not True: r1.append("PROTOCOL_NOT_ADMITTED")
        if target in {"MODULUS","E","YOUNGS_MODULUS"} and p.get("modulus_subtype_resolved") is not True: r1.append("MODULUS_SUBTYPE_UNRESOLVED")
        l1=_layer("L1_DATA_PROTOCOL_FIREWALL",r1,{"FIREWALL_BLOCK","UNITS_UNRESOLVED","TARGET_OUT_OF_SCOPE_KIC","PROTOCOL_NOT_ADMITTED","MODULUS_SUBTYPE_UNRESOLVED"},{"firewall_status":fw})

        r2=[]
        if p.get("physical_violation") is True: r2.append("PHYSICAL_CONSTRAINT_VIOLATION")
        simplex=_f(p,"composition_simplex_error")
        if simplex is not None and simplex>1e-6: r2.append("COMPOSITION_SIMPLEX_INVALID")
        family,route=str(p.get("family","unknown")),str(p.get("route","unknown"))
        if family not in ALLOWED_FAMILIES and p.get("chemistry_remote") is True: r2.append("CHEMICALLY_REMOTE_FAMILY")
        elif family not in ALLOWED_FAMILIES or route not in ALLOWED_ROUTES: r2.append("UNKNOWN_FAMILY_OR_ROUTE")
        if p.get("novel_reinforcement") is True: r2.append("NOVEL_REINFORCEMENT")
        l2=_layer("L2_PHYSICAL_STRUCTURAL_ENVELOPE",r2,{"PHYSICAL_CONSTRAINT_VIOLATION","COMPOSITION_SIMPLEX_INVALID","CHEMICALLY_REMOTE_FAMILY"},{"family":family,"route":route})

        r3=[]
        latent,knn=_f(p,"latent_distance_percentile"),_f(p,"knn_distance_percentile")
        if latent is None or knn is None: r3.append("MANIFOLD_UNASSESSED")
        elif (latent>=.995 and knn>=.995) or latent>=1 or knn>=1: r3.append("MANIFOLD_HARD_OOD")
        elif latent>=.95 or knn>=.95: r3.append("MANIFOLD_BORDERLINE")
        l3=_layer("L3_LEARNED_MANIFOLD_AD",r3,{"MANIFOLD_HARD_OOD"},{"latent_distance_percentile":latent,"knn_distance_percentile":knn})

        r4=[]
        cal=str(p.get("calibration_status","INSUFFICIENT")).upper()
        caliber=str(p.get("coverage_caliber","NONE")).upper()
        receipt=p.get("calibration_receipt_ref")
        width=_f(p,"interval_width_ratio")
        neigh=int(p.get("same_protocol_neighbor_count",0) or 0)
        tail=str(p.get("tail_trust_state","below_gate")).lower()
        if cal=="FAILED_AUDIT": r4.append("CALIBRATION_FAILED_AUDIT")
        elif cal=="INSUFFICIENT": r4.append("CALIBRATION_INSUFFICIENT")
        elif cal=="CALIBRATED_FALLBACK": r4.append("CALIBRATION_FALLBACK")
        if not receipt: r4.append("NO_CALIBRATION_RECEIPT")
        if external and caliber!="HQ_LOSO": r4.append("HQ_LOSO_REQUIRED")
        if width is None or width>=.35: r4.append("INTERVAL_TOO_WIDE" if width is not None and width>=.60 else "INTERVAL_WIDE")
        if neigh<3: r4.append("NEAREST_EVIDENCE_SPARSE")
        if tail=="unsupported_extreme": r4.append("TAIL_UNSUPPORTED_EXTREME")
        elif tail in {"tail_candidate","below_gate","unknown","unassessed"}: r4.append("TAIL_CANDIDATE_ONLY")
        blocks={"CALIBRATION_FAILED_AUDIT","INTERVAL_TOO_WIDE","TAIL_UNSUPPORTED_EXTREME"}
        if external: blocks.add("CALIBRATION_INSUFFICIENT")
        l4=_layer("L4_CALIBRATION_EVIDENCE_TAIL",r4,blocks,{"calibration_status":cal,"coverage_caliber":caliber,"interval_width_ratio":width,"tail_trust_state":tail})

        layers=(l1,l2,l3,l4)
        reasons=tuple(dict.fromkeys(r for x in layers for r in x.reason_codes))
        if any(x.status is Status.BLOCK for x in layers):
            return Decision(Action.REJECT_RECOMMENDATION,ClaimTier.T0_WITHHOLD,layers,reasons,"拒绝推荐：输入触发数据、协议、适用域或校准硬门。",False)
        if any(x.status in {Status.WARN,Status.UNASSESSED} for x in layers):
            return Decision(Action.SCREENING_ONLY,ClaimTier.T1_SCREENING,layers,reasons,"仅供筛选：点估已隐藏，不得用于性能承诺。",False)
        if external and caliber=="HQ_LOSO":
            return Decision(Action.ACCEPT_BOUNDED,ClaimTier.T3_EXTERNAL_CANDIDATE,layers,reasons,"外部主张候选：仅在 HQ-LOSO 收据边界内有效。",True)
        return Decision(Action.ACCEPT_BOUNDED,ClaimTier.T2_BOUNDED_INTERNAL,layers,reasons,"有界内部预测：仅在当前家族、工艺和协议边界内有效。",False)
    ''')

    put(MOD / "contracts.py", r'''
    from __future__ import annotations
    from datetime import datetime, timezone
    from typing import Any, Iterable
    from .types import Action, ClaimTier, Decision, Status

    def machine_labels(d: Decision, p: dict[str,Any]) -> dict[str,Any]:
        l3=next(x for x in d.layers if x.layer=="L3_LEARNED_MANIFOLD_AD")
        ad={Status.PASS:"IN_DOMAIN",Status.WARN:"BORDERLINE",Status.BLOCK:"OOD",Status.UNASSESSED:"UNASSESSED"}[l3.status]
        release=("external_claim_candidate" if d.claim_tier is ClaimTier.T3_EXTERNAL_CANDIDATE else
                 "bounded_internal_candidate" if d.claim_tier is ClaimTier.T2_BOUNDED_INTERNAL else
                 "below_gate_continue_optimization")
        return {
          "firewall_status":str(p.get("firewall_status","UNASSESSED")).upper(),
          "firewall_reason_codes":list(p.get("firewall_reason_codes",[])),
          "tail_trust_state":str(p.get("tail_trust_state","below_gate")),
          "ad_status":ad,"calibration_status":str(p.get("calibration_status","INSUFFICIENT")).upper(),
          "coverage_caliber":str(p.get("coverage_caliber","NONE")).upper(),
          "recommendation_action":d.action.value,"claim_tier":d.claim_tier.value,
          "release_label":release,"hq_loso_receipt_present":bool(p.get("hq_loso_receipt_present",False)),
          "external_claim_eligible":d.external_claim_eligible,
          "fullscore_allowed":False,"production_champion_allowed":False,
        }

    def build_claim_response(p: dict[str,Any], d: Decision, point: float|None, interval: tuple[float,float]|None, unit: str|None, request_id: str="unknown", model_id: str="unknown") -> dict[str,Any]:
        show_point=d.claim_tier in {ClaimTier.T2_BOUNDED_INTERNAL,ClaimTier.T3_EXTERNAL_CANDIDATE}
        iv=None
        if interval is not None and d.action is not Action.REJECT_RECOMMENDATION:
            lo,hi=map(float,interval)
            if lo>hi: raise ValueError("invalid interval")
            iv={"lower":lo,"upper":hi,"unit":unit,"nominal_coverage":p.get("nominal_coverage"),
                "calibration_scope":p.get("calibration_scope"),"coverage_caliber":str(p.get("coverage_caliber","NONE")).upper(),
                "receipt_ref":p.get("calibration_receipt_ref"),"is_claim_interval":show_point,
                "clipped_to_physical_domain":bool(p.get("interval_clipped",False))}
        return {"schema_version":"g06-claim-response-1.0.0","created_at":datetime.now(timezone.utc).isoformat(),
                "request_id":request_id,"model_id":model_id,"target_property":p.get("target_property"),
                "action":d.action.value,"claim_tier":d.claim_tier.value,"headline_zh":d.public_message_zh,
                "point_estimate":point if show_point else None,"unit":unit,"interval":iv,
                "four_layer_assessment":[x.to_dict() for x in d.layers],"reason_codes":list(d.reason_codes),
                "machine_labels":machine_labels(d,p),"claim_boundary":{"candidate_domain":"Ti alloys and Ti-matrix composites only",
                "external_claim_requires_hq_loso":True,"no_fullscore_without_receipt":True}}

    def validate_reject_card(c: dict[str,Any]) -> list[str]:
        req={"schema_version","card_id","created_at","request_id","model_id","target_property","action","claim_tier","headline_zh","reason_codes","point_estimate","interval","four_layer_assessment","machine_labels","claim_boundary","trace"}
        e=[f"missing:{x}" for x in sorted(req-c.keys())]
        if c.get("action") in {"SCREENING_ONLY","REJECT_RECOMMENDATION"} and c.get("point_estimate") is not None: e.append("unsafe_point_exposure")
        if c.get("action")=="REJECT_RECOMMENDATION" and c.get("interval") is not None: e.append("reject_interval_exposure")
        if len(c.get("four_layer_assessment",[]))!=4: e.append("four_layers_required")
        return e

    def build_reject_card(resp: dict[str,Any], d: Decision, nearest: Iterable[dict[str,Any]]=(), remediation: Iterable[dict[str,str]]=(), trace: dict[str,Any]|None=None, card_id: str="unknown") -> dict[str,Any]:
        c={"schema_version":"g06-reject-card-1.0.0","card_id":card_id,"created_at":datetime.now(timezone.utc).isoformat(),
           "request_id":resp.get("request_id"),"model_id":resp.get("model_id"),"target_property":resp.get("target_property"),
           "action":d.action.value,"claim_tier":d.claim_tier.value,"headline_zh":resp.get("headline_zh"),
           "reason_summary_zh":[x.message_zh for x in d.layers if x.reason_codes],"reason_codes":list(d.reason_codes),
           "point_estimate":resp.get("point_estimate"),"interval":resp.get("interval"),
           "four_layer_assessment":resp.get("four_layer_assessment",[]),"machine_labels":resp.get("machine_labels",{}),
           "nearest_evidence":list(nearest),"remediation":list(remediation),"claim_boundary":resp.get("claim_boundary",{}),"trace":trace or {}}
        err=validate_reject_card(c)
        if err: raise ValueError("invalid reject card: "+";".join(err))
        return c
    ''')

    put(MOD / "cli.py", r'''
    from __future__ import annotations
    import argparse, json
    from pathlib import Path
    from .decision import evaluate_four_layers
    from .contracts import build_claim_response

    def main() -> int:
        ap=argparse.ArgumentParser()
        ap.add_argument("--case",type=Path,required=True); ap.add_argument("--point",type=float)
        ap.add_argument("--lower",type=float); ap.add_argument("--upper",type=float); ap.add_argument("--unit")
        a=ap.parse_args(); obj=json.loads(a.case.read_text(encoding="utf-8")); p=obj.get("payload",obj)
        iv=None if a.lower is None and a.upper is None else (a.lower,a.upper)
        if iv is not None and None in iv: raise SystemExit("--lower and --upper required together")
        print(json.dumps(build_claim_response(p,evaluate_four_layers(p),a.point,iv,a.unit,str(obj.get("case_id","cli")),"g06-smoke"),ensure_ascii=False,indent=2))
        return 0
    if __name__=="__main__": raise SystemExit(main())
    ''')

    put(MOD / "README.md", r'''
    # G06 UQ/OOD/AD/拒绝推荐

    本模块消费冻结预测器、materials-data-firewall、训练域 AD 百分位、最近证据、校准收据和 tail-trust 状态。
    它不重训模型，不重造最近邻索引，不覆盖其他窗口。

    ```bash
    PYTHONPATH=modules python -m unittest discover -s modules/w08_mq_uq_conformal_calibration/tests -v
    ```
    ''')
    put(MOD / "tests/__init__.py", "")

    put(MOD / "tests/test_g06.py", r'''
    from __future__ import annotations
    import json, unittest
    from pathlib import Path
    from w08_mq_uq_conformal_calibration.conformal import *
    from w08_mq_uq_conformal_calibration.decision import evaluate_four_layers
    from w08_mq_uq_conformal_calibration.contracts import build_claim_response, build_reject_card, validate_reject_card

    def base():
        return {"target_property":"UTS","requested_claim_mode":"internal","firewall_status":"PASS","firewall_reason_codes":[],
        "units_resolved":True,"protocol_admitted":True,"modulus_subtype_resolved":True,"physical_violation":False,
        "composition_simplex_error":0.0,"family":"near-alpha","route":"wrought","chemistry_remote":False,
        "novel_reinforcement":False,"latent_distance_percentile":.4,"knn_distance_percentile":.45,
        "calibration_status":"CALIBRATED_GROUP","coverage_caliber":"GROUPED_SOURCE","calibration_receipt_ref":"synthetic://pass",
        "nominal_coverage":.9,"calibration_scope":"UTS|near-alpha|wrought|ASTM_E8","interval_width_ratio":.2,
        "same_protocol_neighbor_count":5,"tail_trust_state":"validated","hq_loso_receipt_present":False}

    class T(unittest.TestCase):
        def test_quantile(self): self.assertEqual(finite_sample_quantile(range(1,10),.1),9.)
        def test_bad_scores(self):
            for x in ([],[1,-1],[float("nan")]):
                with self.assertRaises(ValueError): finite_sample_quantile(x,.1)
        def test_cqr(self): self.assertEqual(cqr_scores([5,8],[4,4],[6,7]),[0.,1.])
        def test_wilson(self): self.assertLess(wilson_lower_bound(9,10),.9)
        def test_audit(self): self.assertTrue(coverage_audit([(0,2)]*10,[1]*9+[3],.9,.87)["audit_pass"])
        def test_mondrian_fallback(self):
            rules=(GroupRule("exact",("target","family","route"),3),GroupRule("family",("target","family"),4))
            rec=[CalibrationRecord(100+i,99+i,"UTS","near-alpha","wrought","E8") for i in range(4)]
            r=MondrianCalibrator(.1,rules).fit(rec).quantile_for({"target":"UTS","family":"near-alpha","route":"AM"})
            self.assertEqual(r.status,"CALIBRATED_FALLBACK")
        def test_no_group_refuses(self):
            with self.assertRaises(LookupError):
                MondrianCalibrator(.1,(GroupRule("x",("target",),3),)).fit([CalibrationRecord(1,1,"UTS","alpha","wrought","p")]).quantile_for({"target":"UTS"})
        def test_clean(self): self.assertEqual(evaluate_four_layers(base()).claim_tier.value,"T2_BOUNDED_INTERNAL")
        def test_external_no_hq(self):
            p=base(); p["requested_claim_mode"]="external"; d=evaluate_four_layers(p)
            self.assertEqual(d.action.value,"SCREENING_ONLY"); self.assertIn("HQ_LOSO_REQUIRED",d.reason_codes)
        def test_firewall(self):
            p=base(); p["firewall_status"]="BLOCK"; self.assertEqual(evaluate_four_layers(p).action.value,"REJECT_RECOMMENDATION")
        def test_ood(self):
            p=base(); p.update(latent_distance_percentile=.999,knn_distance_percentile=.999)
            self.assertIn("MANIFOLD_HARD_OOD",evaluate_four_layers(p).reason_codes)
        def test_tail(self):
            p=base(); p["tail_trust_state"]="unsupported_extreme"; self.assertEqual(evaluate_four_layers(p).claim_tier.value,"T0_WITHHOLD")
        def test_kic(self):
            p=base(); p["target_property"]="KIC"; self.assertIn("TARGET_OUT_OF_SCOPE_KIC",evaluate_four_layers(p).reason_codes)
        def test_screen_hides_point(self):
            p=base(); p["calibration_status"]="CALIBRATED_FALLBACK"; d=evaluate_four_layers(p)
            r=build_claim_response(p,d,1300,(1200,1400),"MPa"); self.assertIsNone(r["point_estimate"]); self.assertFalse(r["interval"]["is_claim_interval"])
        def test_reject_hides_all(self):
            p=base(); p["firewall_status"]="BLOCK"; d=evaluate_four_layers(p); r=build_claim_response(p,d,1300,(1200,1400),"MPa")
            self.assertIsNone(r["point_estimate"]); self.assertIsNone(r["interval"]); self.assertEqual(validate_reject_card(build_reject_card(r,d,card_id="t")),[])
        def test_data_cases(self):
            root=Path(__file__).resolve().parents[3]; rows=[json.loads(x) for x in (root/"DATA/g06/ood_cases.jsonl").read_text(encoding="utf-8").splitlines() if x]
            self.assertGreaterEqual(len(rows),12)
            for c in rows:
                d=evaluate_four_layers(c["payload"]); self.assertEqual(d.action.value,c["expected"]["action"],c["case_id"]); self.assertEqual(d.claim_tier.value,c["expected"]["claim_tier"],c["case_id"])
        def test_mandatory_data(self):
            root=Path(__file__).resolve().parents[3]
            for n in ("calibration_policy.yaml","ood_cases.jsonl","reject_card.schema.json"): self.assertTrue((root/"DATA/g06"/n).is_file())
    if __name__=="__main__": unittest.main()
    ''')

    policy = r'''
    schema_version: g06-calibration-policy-1.0.0
    candidate_domain: [Ti_alloys, Ti_matrix_composites]
    active_targets: [UTS, YS, EL, Modulus, Hardness]
    out_of_scope_targets: [KIC]
    internal:
      nominal_coverage: 0.90
      grouped_validation_floor: 0.87
      claim_tier_ceiling: T2_BOUNDED_INTERNAL
    external_candidate:
      nominal_coverage: 0.95
      requires_coverage_caliber: HQ_LOSO
      requires_receipt: true
      claim_tier_ceiling: T3_EXTERNAL_CANDIDATE
    quantile_formula: "k=ceil((n+1)*(1-alpha)); q=sorted(scores)[min(k,n)-1]"
    calibration_model_must_be_frozen: true
    calibration_labels_must_not_enter_training_or_tuning: true
    mondrian_hierarchy:
      - {name: target_family_route_protocol, fields: [target, family, route, protocol_class], min_n_hq: 40}
      - {name: target_family_route, fields: [target, family, route], min_n_hq: 60}
      - {name: target_family, fields: [target, family], min_n_hq: 80}
      - {name: target_global, fields: [target], min_n_hq: 100}
    fallback: hard_hierarchy_without_cross_group_pooling
    failure_degradation:
      calibration_failed_audit: REJECT_RECOMMENDATION
      insufficient_group: SCREENING_ONLY
      fallback_group: SCREENING_ONLY
      external_without_hq_loso: SCREENING_ONLY
      interval_width_ratio_ge_0_60: REJECT_RECOMMENDATION
      interval_width_ratio_ge_0_35: SCREENING_ONLY
    dual_caliber_never_merge: [TRAIN_OR_GE5, GROUPED_SOURCE, HQ_LOSO]
    no_hq_loso_no_fullscore: true
    provenance: policy_defaults_not_empirical_results
    '''
    put(DATA/"calibration_policy.yaml",policy)
    put(DATA/"four_layer_policy.yaml",r'''
    schema_version: g06-four-layer-policy-1.0.0
    aggregation: lexicographic_worst_layer
    weighted_average_for_vetoes: forbidden
    layers:
      L1_DATA_PROTOCOL_FIREWALL: [firewall, units, endpoint_protocol, modulus_subtype]
      L2_PHYSICAL_STRUCTURAL_ENVELOPE: [simplex, physical_constraints, family, route, reinforcement]
      L3_LEARNED_MANIFOLD_AD: [latent_distance_percentile, knn_distance_percentile]
      L4_CALIBRATION_EVIDENCE_TAIL: [coverage_caliber, receipt, width, nearest_evidence, tail_trust]
    actions: [ACCEPT_BOUNDED, SCREENING_ONLY, REJECT_RECOMMENDATION]
    ''')

    b={"target_property":"UTS","requested_claim_mode":"internal","firewall_status":"PASS","firewall_reason_codes":[],"units_resolved":True,"protocol_admitted":True,"modulus_subtype_resolved":True,"physical_violation":False,"composition_simplex_error":0.0,"family":"near-alpha","route":"wrought","chemistry_remote":False,"novel_reinforcement":False,"latent_distance_percentile":.4,"knn_distance_percentile":.45,"calibration_status":"CALIBRATED_GROUP","coverage_caliber":"GROUPED_SOURCE","calibration_receipt_ref":"synthetic://grouped-pass","nominal_coverage":.9,"calibration_scope":"UTS|near-alpha|wrought|ASTM_E8","interval_width_ratio":.2,"same_protocol_neighbor_count":5,"tail_trust_state":"validated","hq_loso_receipt_present":False}
    cases=[]
    def case(i,desc,upd,action,tier):
        p=dict(b);p.update(upd);cases.append({"case_id":f"G06-SYN-{i:03d}","description_zh":desc,"synthetic_fixture":True,"payload":p,"expected":{"action":action,"claim_tier":tier},"provenance":"policy_fixture_not_material_measurement"})
    case(1,"近α锻造 UTS 全门通过",{},"ACCEPT_BOUNDED","T2_BOUNDED_INTERNAL")
    case(2,"校准回退",{"calibration_status":"CALIBRATED_FALLBACK"},"SCREENING_ONLY","T1_SCREENING")
    case(3,"潜空间和 kNN 共同硬 OOD",{"family":"TMC","novel_reinforcement":True,"latent_distance_percentile":.999,"knn_distance_percentile":.999},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    case(4,"EL 协议缺失",{"target_property":"EL","protocol_admitted":False},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    case(5,"Modulus 子类型缺失",{"target_property":"Modulus","modulus_subtype_resolved":False},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    case(6,"单位未解析",{"units_resolved":False},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    case(7,"unsupported extreme",{"tail_trust_state":"unsupported_extreme"},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    case(8,"校准样本不足",{"calibration_status":"INSUFFICIENT"},"SCREENING_ONLY","T1_SCREENING")
    case(9,"防火墙来源冲突",{"firewall_status":"BLOCK","firewall_reason_codes":["SOURCE_CONFLICT"]},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    case(10,"距离边界且最近证据稀疏",{"latent_distance_percentile":.97,"knn_distance_percentile":.92,"same_protocol_neighbor_count":1},"SCREENING_ONLY","T1_SCREENING")
    case(11,"外部请求无 HQ-LOSO",{"requested_claim_mode":"external"},"SCREENING_ONLY","T1_SCREENING")
    case(12,"KIC 当前范围外",{"target_property":"KIC"},"REJECT_RECOMMENDATION","T0_WITHHOLD")
    put(DATA/"ood_cases.jsonl","".join(json.dumps(x,ensure_ascii=False)+"\n" for x in cases))
    put_json(DATA/"smoke_case.json",cases[0])

    reject_schema={"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"https://tiai.local/g06/reject-card.schema.json","title":"G06 rejection evidence card","type":"object","additionalProperties":False,"required":["schema_version","card_id","created_at","request_id","model_id","target_property","action","claim_tier","headline_zh","reason_codes","point_estimate","interval","four_layer_assessment","machine_labels","nearest_evidence","remediation","claim_boundary","trace"],"properties":{"schema_version":{"const":"g06-reject-card-1.0.0"},"card_id":{"type":"string","minLength":1},"created_at":{"type":"string","format":"date-time"},"request_id":{"type":["string","null"]},"model_id":{"type":["string","null"]},"target_property":{"type":["string","null"]},"action":{"enum":["SCREENING_ONLY","REJECT_RECOMMENDATION"]},"claim_tier":{"enum":["T0_WITHHOLD","T1_SCREENING"]},"headline_zh":{"type":["string","null"]},"reason_summary_zh":{"type":"array","items":{"type":"string"}},"reason_codes":{"type":"array","minItems":1,"items":{"type":"string"}},"point_estimate":{"type":"null"},"interval":{"type":["object","null"]},"four_layer_assessment":{"type":"array","minItems":4,"maxItems":4,"items":{"type":"object"}},"machine_labels":{"type":"object"},"nearest_evidence":{"type":"array","items":{"type":"object"}},"remediation":{"type":"array","items":{"type":"object"}},"claim_boundary":{"type":"object"},"trace":{"type":"object"}}}
    put_json(DATA/"reject_card.schema.json",reject_schema)
    put_json(DATA/"machine_labels.schema.json",{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","required":["firewall_status","tail_trust_state","ad_status","calibration_status","coverage_caliber","recommendation_action","claim_tier","release_label","fullscore_allowed"],"properties":{"fullscore_allowed":{"const":False},"production_champion_allowed":{"const":False}}})
    put_json(DATA/"claim_interval.schema.json",{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","required":["lower","upper","unit","nominal_coverage","calibration_scope","coverage_caliber","receipt_ref","is_claim_interval","clipped_to_physical_domain"],"properties":{"lower":{"type":"number"},"upper":{"type":"number"},"coverage_caliber":{"enum":["TRAIN_OR_GE5","GROUPED_SOURCE","HQ_LOSO","NONE"]},"is_claim_interval":{"type":"boolean"}}})
    put_json(DATA/"ui_examples.zh-CN.json",{"bounded":{"title":"有界预测","rule":"显示点估+校准区间+适用域+收据"},"screening":{"title":"仅供筛选","rule":"隐藏点估；区间不得作为主张"},"rejected":{"title":"拒绝推荐","rule":"隐藏点估和区间；仅返回原因、证据、修复路径"}})

    put("METHOD_IR/G06_METHOD_IR.md",r'''
    # G06 Method IR

    ## Split conformal
    对冻结预测器校准残差 `s_i=|y_i-yhat_i|`，采用有限样本 higher order statistic：
    `k=ceil((n+1)(1-alpha)); q=s_(min(k,n))`，区间 `[yhat-q,yhat+q]`。

    ## CQR
    `s_i=max(q_lo(x_i)-y_i, y_i-q_hi(x_i), 0)`；新区间 `[q_lo-q,q_hi+q]`。

    ## Mondrian hard fallback
    `target+family+route+protocol` → `target+family+route` → `target+family` → `target`。
    每层独立满足 HQ 最小样本数；禁止跨组无收据加权池化。

    ## Four-layer gate
    L1 数据/协议防火墙；L2 物理/结构包络；L3 潜空间+kNN；L4 校准/最近证据/tail/区间宽度。
    聚合为最坏层优先，不做加权平均。BLOCK→T0；WARN/UNASSESSED→T1；全过→T2；外部且 HQ-LOSO→T3。

    ## Leakage firewall
    校准标签不得进入训练、特征选择、超参搜索或阈值优化；AD 阈值仅由训练参考域产生；
    HQ-LOSO 测试源不得参与组选择或分位拟合；测试 coverage 不回写参数；三种 coverage caliber 永久分列。
    ''')
    put("METHOD_IR/PSEUDOCODE.md",r'''
    ```text
    L1 = data_protocol_firewall(input)
    L2 = physical_structural_envelope(input)
    L3 = latent_and_knn_applicability(input, training_reference_receipt)
    L4 = calibration_evidence_tail(input, calibration_receipt, nearest_evidence, tail_trust)
    if any BLOCK: reject; hide point and interval
    elif any WARN/UNASSESSED: screening; hide point; interval non-claim
    elif external and HQ_LOSO: bounded T3
    else: bounded T2
    ```
    ''')

    sources=[
    ("Distribution-Free Predictive Inference for Regression","JASA/arXiv","https://arxiv.org/abs/1604.04173","ADOPT","finite-sample split conformal"),
    ("Conformalized Quantile Regression","NeurIPS","https://arxiv.org/abs/1905.03222","ADOPT","CQR scores and intervals"),
    ("Predictive Inference with the Jackknife+","Annals of Statistics","https://arxiv.org/abs/1905.02928","REFERENCE","costlier alternative"),
    ("Conformal Prediction Under Covariate Shift","NeurIPS","https://arxiv.org/abs/1904.06019","ADAPT","shift assumptions explicit"),
    ("Adaptive Conformal Inference Under Distribution Shift","NeurIPS","https://arxiv.org/abs/2106.00170","REFERENCE","not static LOSO substitute"),
    ("Conformal Prediction Beyond Exchangeability","arXiv","https://arxiv.org/abs/2202.13415","REFERENCE","nonexchangeable caveat"),
    ("Conformal Risk Control","arXiv","https://arxiv.org/abs/2208.02814","ADAPT","risk audit concept"),
    ("Risk-Controlling Prediction Sets","JMLR","https://arxiv.org/abs/2101.02703","REFERENCE","held-out calibration"),
    ("Learn then Test","arXiv","https://arxiv.org/abs/2110.01052","ADOPT","separate learning/testing"),
    ("A Gentle Introduction to Conformal Prediction","arXiv","https://arxiv.org/abs/2107.07511","REFERENCE","assumption ledger"),
    ("Conformalized Selective Regression","arXiv","https://arxiv.org/abs/2402.16300","ADAPT","regression abstention"),
    ("Classification with Reject Option via Conformal Prediction","arXiv","https://arxiv.org/abs/2506.21802","ADAPT","explicit reject state"),
    ("Conformal Prediction with Learned Features","ICML","https://proceedings.mlr.press/v235/kiyani24a.html","ADAPT","split-safe latent features"),
    ("Deep Ensembles","NeurIPS","https://arxiv.org/abs/1612.01474","ADOPT_UPSTREAM","epistemic input not calibrated interval"),
    ("On Calibration of Modern Neural Networks","ICML","https://proceedings.mlr.press/v70/guo17a.html","REFERENCE","metric separation"),
    ("Accurate Uncertainties for Deep Learning Using Calibrated Regression","ICML","https://arxiv.org/abs/1807.00263","REFERENCE","regression calibration curves"),
    ("Can You Trust Your Model's Uncertainty?","NeurIPS","https://arxiv.org/abs/1906.02530","ADOPT","shift evaluation"),
    ("SelectiveNet","ICML","https://arxiv.org/abs/1901.09192","ADAPT","coverage-risk screening"),
    ("Deep Gamblers","NeurIPS","https://arxiv.org/abs/1907.00208","REJECT_MAINLINE","learned abstention cannot override hard gates"),
    ("Well-Calibrated Regression Uncertainty","MIDL","https://proceedings.mlr.press/v121/laves20a.html","REFERENCE","calibration plus sharpness"),
    ("A Baseline for Detecting Misclassified and OOD Examples","ICLR","https://arxiv.org/abs/1610.02136","REFERENCE","MSP insufficient for regression"),
    ("ODIN","ICLR","https://arxiv.org/abs/1706.02690","REFERENCE","image-specific"),
    ("Mahalanobis OOD Detection","NeurIPS","https://arxiv.org/abs/1807.03888","ADOPT_UPSTREAM","global latent score"),
    ("Energy-based OOD Detection","NeurIPS","https://arxiv.org/abs/2010.03759","REFERENCE","challenger score"),
    ("ReAct","NeurIPS","https://arxiv.org/abs/2111.12797","REFERENCE","not tabular policy kernel"),
    ("ViM","CVPR","https://arxiv.org/abs/2203.10807","REFERENCE","neural challenger"),
    ("DICE","ECCV","https://arxiv.org/abs/2111.09805","REFERENCE","model-specific"),
    ("ASH","NeurIPS","https://arxiv.org/abs/2306.13151","REFERENCE","activation shaping not evidence"),
    ("Deep Nearest Neighbors for OOD","ICML","https://arxiv.org/abs/2204.06507","ADOPT_UPSTREAM","local support score"),
    ("OpenMax","CVPR","https://arxiv.org/abs/1511.06233","REFERENCE","open-set concept"),
    ("Self-Supervised Learning for Robustness and Uncertainty","NeurIPS","https://arxiv.org/abs/1906.12340","REFERENCE","upstream representation"),
    ("CSI Novelty Detection","NeurIPS","https://arxiv.org/abs/2007.08176","REFERENCE","image-heavy"),
    ("SSD Self-Supervised Outlier Detection","ICLR","https://arxiv.org/abs/2103.12051","REFERENCE","future adapter"),
    ("Generalized ODIN","CVPR","https://arxiv.org/abs/2002.11297","REFERENCE","classification-specific"),
    ("Deep Anomaly Detection with Outlier Exposure","ICLR","https://arxiv.org/abs/1812.04606","ADAPT","pressure tests only"),
    ("MOS OOD Detection","CVPR","https://arxiv.org/abs/2105.01879","ADAPT","group-aware OOD"),
    ("OpenOOD","NeurIPS Datasets and Benchmarks","https://arxiv.org/abs/2210.07242","ADAPT","multi-shift evaluation"),
    ("OpenOOD official implementation","GitHub","https://github.com/Jingkang50/OpenOOD","REFERENCE","benchmark patterns"),
    ("PyOD","JMLR/GitHub","https://github.com/yzhao062/pyod","REFERENCE","challenger library"),
    ("scikit-learn Novelty and Outlier Detection","Official docs","https://scikit-learn.org/stable/modules/outlier_detection.html","REFERENCE","terminology"),
    ("scikit-learn Covariance Estimation","Official docs","https://scikit-learn.org/stable/modules/covariance.html","ADOPT_UPSTREAM","robust Mahalanobis"),
    ("scikit-learn Nearest Neighbors","Official docs","https://scikit-learn.org/stable/modules/neighbors.html","ADOPT_UPSTREAM","training-only index"),
    ("FAISS","GitHub","https://github.com/facebookresearch/faiss","REFERENCE","large evidence bank"),
    ("NNGuide","ICCV","https://openaccess.thecvf.com/content/ICCV2023/html/Park_NNGuide_Improving_Out-of-Distribution_Detection_Using_Nearest_Neighbor_Guidance_ICCV_2023_paper.html","ADAPT","multi-score consensus"),
    ("Matbench","npj Computational Materials","https://www.nature.com/articles/s41524-020-00406-3","ADOPT","reproducible grouped benchmark"),
    ("Matbench preprint","arXiv","https://arxiv.org/abs/2005.00707","REFERENCE","split context"),
    ("Matbench official code","GitHub","https://github.com/materialsproject/matbench","REFERENCE","manifest conventions"),
    ("Matbench Discovery","arXiv","https://arxiv.org/abs/2308.14920","REFERENCE","prospective evaluation"),
    ("CrabNet","npj Computational Materials","https://arxiv.org/abs/2103.09182","REFERENCE","model-agnostic policy"),
    ("Roost","npj Computational Materials","https://arxiv.org/abs/1910.00617","REFERENCE","source shift remains"),
    ("MEGNet","Chemistry of Materials","https://arxiv.org/abs/1812.05055","REFERENCE","latent adapter only"),
    ("ALIGNN","npj Computational Materials","https://arxiv.org/abs/2106.01829","REFERENCE","structure model still gated"),
    ("CGCNN","Physical Review Letters","https://arxiv.org/abs/1710.10324","REFERENCE","architecture decoupled"),
    ("MatSciBERT","npj Computational Materials","https://www.nature.com/articles/s41524-022-00784-w","REFERENCE","source spans mandatory"),
    ("NOMAD Laboratory","Scientific Data","https://www.nature.com/articles/sdata201876","ADAPT","provenance identifiers"),
    ("MAPIE documentation","Official docs","https://mapie.readthedocs.io/","REFERENCE","implementation comparison"),
    ("MAPIE repository","GitHub","https://github.com/scikit-learn-contrib/MAPIE","REFERENCE","dependency audit"),
    ("Fortuna","GitHub","https://github.com/awslabs/fortuna","REFERENCE","heavier framework"),
    ("Uncertainty Toolbox","GitHub","https://github.com/uncertainty-toolbox/uncertainty-toolbox","ADAPT","coverage and sharpness metrics"),
    ("JSON Schema Draft 2020-12","Official spec","https://json-schema.org/draft/2020-12","ADOPT","strict card schemas"),
    ("NIST AI RMF","NIST","https://www.nist.gov/itl/ai-risk-management-framework","ADAPT","traceable risk treatment"),
    ("OECD QSAR Validation Principles","OECD","https://www.oecd.org/chemicalsafety/risk-assessment/validationofqsarmodels.htm","ADAPT","endpoint and applicability domain"),
    ("ASTM E8/E8M","ASTM","https://www.astm.org/e0008_e0008m.html","ADAPT","tensile protocol identity"),
    ("ASTM E111","ASTM","https://www.astm.org/e0111.html","ADAPT","modulus protocol identity"),
    ("Materials Project API","Official docs","https://docs.materialsproject.org/","REFERENCE","stable evidence identifiers"),
    ("Automatminer","GitHub","https://github.com/hackingmaterials/automatminer","REFERENCE","pipeline provenance"),
    ("Conformal Prediction and Trustworthy AI","arXiv","https://arxiv.org/abs/2508.06885","REFERENCE","trust assumptions explicit"),
    ]
    ledger=ROOT/"reports/SOURCE_LEDGER.csv";ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["id","title","venue","url","decision","implementation_mapping"])
        for i,s in enumerate(sources,1):w.writerow([i,*s])
    put("reports/SOURCE_LEDGER.md","# SOURCE_LEDGER\n\n"+f"English sources screened: **{len(sources)}**. ADOPT/ADAPT items are mapped into code/contracts; reference/reject items are not promoted.\n\n"+"\n".join(f"{i}. [{s[0]}]({s[2]}) — {s[3]} — {s[4]}" for i,s in enumerate(sources,1)))

    put("reports/GROUNDING_AUDIT.md",r'''
    # Grounding audit
    Confirmed inputs: sole authority `TIAI_WEB36_V24_AGENT_NATIVE_ONE_WAVE_FULL_20260717.zip`; window `G06_UQ_OOD_AD_REJECT.md`; uploaded fleet carriers B006/B007/B009/B010; requested base subject `3008e56`.
    Exact write scope: `modules/w08_mq_uq_conformal_calibration/** ; DATA/g06/**`.
    R01 conformal, materials-data-firewall and R14 tail-trust remain read-only upstream owners. Current remote main is newer than the uploaded source-pack tip; local must apply in an isolated checkout and stop on conflict.
    ''')
    put("reports/DESIGN.md",r'''
    # Design verdict
    The main contradiction is forced prediction under missing protocol, shift, sparse evidence and absent coverage receipts—not lack of another point regressor.
    Delivered: finite-sample conformal/CQR reference code; hard Mondrian fallback; four-layer lexicographic gate; firewall+tail labels; Chinese API/UI suppression; strict schemas; 12 executable pressure fixtures.
    Deleted: learned weighted fusion without labeled OOD calibration; duplicate nearest-neighbor index; duplicate UQ trainer; confidence overriding firewall; unconditional T3/FULLSCORE.
    ''')
    put("reports/RESEARCH_SYNTHESIS.md",r'''
    # Research synthesis
    1. Conformal coverage is assumption-bound; IID marginal coverage is not source-holdout or conditional coverage.
    2. OOD is not one scalar: global latent distance, local neighbor evidence, protocol/source quality, calibration and tail evidence cover distinct failures.
    3. Abstention is a product state: unsafe point estimates must be suppressed by API, not hidden only by CSS.
    4. Materials evidence needs endpoint, protocol, source and applicability-domain provenance; chemistry similarity alone is insufficient.
    ''')
    put("reports/PRESSURE_TEST.md","# Pressure tests\n\n"+"\n".join(f"- {x['case_id']}: {x['description_zh']} → {x['expected']['action']}" for x in cases))
    put("reports/DATA_PROVENANCE.md",f"# DATA provenance\n\n- n_rows_HQ: 0 (policy/UQ window, no fabricated property extraction).\n- n_synthetic_policy_cases: {len(cases)}.\n- Every fixture is marked synthetic and forbidden from model training or scientific metrics.\n- Thresholds are configurable policy defaults, not observed Ti/TMC performance.\n")
    put("reports/VERIFICATION_CHECKLIST.md",r'''
    # Verification checklist
    - [x] exact G06 write scope only in product patch
    - [x] mandatory DATA files present
    - [x] runnable algorithms and tests
    - [x] T0/T1 point suppression
    - [x] TRAIN_OR_GE5 / GROUPED_SOURCE / HQ_LOSO kept separate
    - [x] no fabricated R², coverage, AUROC or LOSO score
    - [x] no FULLSCORE or PRODUCTION_CHAMPION
    - [x] >=50 English sources
    - [x] manifest, checksums, secret/public-safe scans, replay queue
    ''')
    put("reports/GITHUB_INTERNALIZATION_LEDGER.md",r'''
    # GitHub internalization ledger
    | Asset | Decision | Reason |
    |---|---|---|
    | MAPIE | reference | no new production dependency |
    | Fortuna | reference | broader than required |
    | uncertainty-toolbox | adapt metrics | coverage/sharpness reporting |
    | sklearn covariance/kNN | upstream adapter | existing platform supplies normalized scores |
    | OpenOOD/PyOD | benchmark/challenger | cannot replace material hard gates |
    | R01 conformal | read-only owner | no overwrite |
    | materials-data-firewall | read-only hard gate | no overwrite |
    | R14 tail-trust | read-only state | no overwrite |
    ''')

    put("CLAIM_BOUNDARY.md",r'''
    # Claim boundary
    Can claim: executable conformal/CQR utilities; executable four-layer fail-closed state machine; deterministic firewall/tail labels; Chinese API/UI suppression; synthetic policy fixtures pass.
    Cannot claim: empirical Ti/TMC coverage/sharpness/OOD AUROC/FPR95/R²/MAE/LOSO improvement; real HQ-LOSO validation; FULLSCORE; PRODUCTION_CHAMPION; production deployment; validity outside the selected family/route/protocol.
    Scientific status: `below_gate_continue_optimization` until frozen residuals, source-holdout tests and HQ-LOSO receipts are replayed.
    ''')
    put("BLOCKERS.md",r'''
    # Blockers
    1. Real frozen calibration residuals absent: replay existing frozen outputs; do not retrain.
    2. Real latent/kNN reference distributions absent: bind existing training-only AD receipts.
    3. HQ-LOSO receipt absent: external claim tier unavailable.
    4. Remote main is newer than base subject 3008e56: local `git apply --check` must pass in isolated checkout.
    5. Shared serving-route wiring is outside this window write scope and requires a later integration patch.
    ''')
    put("PLATFORM_DIMENSION_CLAIM.md",r'''
    # Platform dimension claim
    Mathematical accuracy: finite-sample quantile, exchangeability boundary, Wilson audit, hard Mondrian fallback and separate calibers; no empirical score claimed.
    Generality: explicit Ti/TMC family-route-protocol bounds; unknown/remote points downgrade or reject.
    Front-end intelligibility: stable Chinese bounded/screening/rejected states; T0/T1 point values are machine-hidden.
    ''')
    put("LOCAL_CODEX_APPLY.md",r'''
    # Local Codex apply (0.01%)
    Target `E:\Generated\tiai-agent-os`, intended source-pack base subject `3008e56`.
    ```powershell
    $ErrorActionPreference="Stop"
    cd E:\Generated\tiai-agent-os
    git status --short
    git rev-parse --short HEAD
    git apply --check E:\Generated\titmc_return_intake\G06_20260718\PATCHES\G06_UQ_OOD_AD_REJECT.patch
    git apply E:\Generated\titmc_return_intake\G06_20260718\PATCHES\G06_UQ_OOD_AD_REJECT.patch
    $env:PYTHONPATH="$PWD\modules"
    py -3 -m compileall -q modules\w08_mq_uq_conformal_calibration
    py -3 -m unittest discover -s modules\w08_mq_uq_conformal_calibration\tests -v
    py -3 -m w08_mq_uq_conformal_calibration.cli --case DATA\g06\smoke_case.json --point 1300 --lower 1200 --upper 1400 --unit MPa
    ```
    Stop on conflict, overwrite, failed test, or exposed point estimate in T0/T1. Rollback: `git apply -R <patch>`.
    ''')
    put("NEXT_LOCAL_CODEX_EXECUTION_PROMPT.md",r'''
    Apply only `PATCHES/G06_UQ_OOD_AD_REJECT.patch` in an isolated worktree aligned to the intended source pack. Run the exact compile, unittest and CLI smoke commands in `LOCAL_CODEX_APPLY.md`. Do not retrain, alter champions, relax gates, merge coverage calibers, or wire shared serving routes. Return `git apply --check` stdout, test stdout, CLI JSON, changed-path list, commit SHA if committed, and a promote/quarantine/reject decision.
    ''')
    put("LOCAL_REPLAY_QUEUE.jsonl",json.dumps({"id":"G06-R1","priority":"P0","action":"apply_check_compile_unittest_cli","inputs":["PATCHES/G06_UQ_OOD_AD_REJECT.patch","DATA/g06/smoke_case.json"],"promotion_rule":"all deterministic gates pass","forbidden":["retrain","champion swap","FULLSCORE","shared route mutation"]},ensure_ascii=False)+"\n")
    put("PROMOTION_QUARANTINE_REJECT_DECISIONS.csv","asset,decision,reason\nG06 additive patch,PROMOTE_AFTER_LOCAL_SMOKE,web tests pass; canonical checkout not mounted\nHQ-LOSO external claim,QUARANTINE,no HQ-LOSO receipt\nFULLSCORE,REJECT,forbidden without HQ-LOSO\nPRODUCTION_CHAMPION,REJECT,no production replay\n")
    put("README_FIRST.md",f"# {NAME}\n\nStatus: COMPLETE_READY_FOR_LOCAL_APPLY. Product patch writes only `{MOD}/**` and `{DATA}/**`. Read CLAIM_BOUNDARY, LOCAL_CODEX_APPLY and reports/GROUNDING_AUDIT first.\n")
    put("WINDOW_STATUS.txt","COMPLETE_READY_FOR_LOCAL_APPLY\n")

    authorized=[p for p in all_files() if p.relative_to(ROOT).as_posix().startswith((str(MOD)+"/",str(DATA)+"/"))]
    put("PATCHES/G06_UQ_OOD_AD_REJECT.patch",patch_for(authorized))

    receipts=ROOT/"reports/receipts";receipts.mkdir(parents=True,exist_ok=True)
    ok=compileall.compile_dir(str(ROOT/MOD),quiet=1)
    (receipts/"compileall_stdout.txt").write_text(f"compileall_ok={ok}\npython={sys.version}\n",encoding="utf-8")
    if not ok: raise SystemExit("compileall failed")
    env=dict(os.environ);env["PYTHONPATH"]=str((ROOT/"modules").resolve())
    cmd=[sys.executable,"-m","unittest","discover","-s",str((ROOT/MOD/"tests").resolve()),"-v"]
    r=subprocess.run(cmd,text=True,capture_output=True,env=env)
    (receipts/"tests_stdout.txt").write_text("$ "+" ".join(cmd)+"\n\nSTDOUT\n"+r.stdout+"\nSTDERR\n"+r.stderr,encoding="utf-8")
    if r.returncode: print(r.stdout,r.stderr);raise SystemExit(r.returncode)

    sys.path.insert(0,str((ROOT/"modules").resolve()))
    from w08_mq_uq_conformal_calibration.decision import evaluate_four_layers
    replay=[]
    for c in cases:
        d=evaluate_four_layers(c["payload"]);passed=d.action.value==c["expected"]["action"] and d.claim_tier.value==c["expected"]["claim_tier"]
        replay.append({"case_id":c["case_id"],"expected":c["expected"],"actual":{"action":d.action.value,"claim_tier":d.claim_tier.value},"pass":passed})
    put_json("reports/receipts/fixture_replay.json",replay)
    if not all(x["pass"] for x in replay): raise SystemExit("fixture replay failed")

    inventory=[]
    for p in all_files():
        if p.name not in {"RETURN_MANIFEST.json","SHA256SUMS.txt"}:
            inventory.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":digest(p)})
    manifest={"schema_version":"tiai-web-return-1.0.0","window_id":"G06","slug":"UQ_OOD_AD_REJECT","package_name":NAME,
      "generated_at":datetime.now(timezone.utc).isoformat(),"authoritative_pack":"TIAI_WEB36_V24_AGENT_NATIVE_ONE_WAVE_FULL_20260717.zip",
      "base_subject_sha":"3008e56","exclusive_mission":"UQ·OOD·AD·拒绝推荐","write_scope":[str(MOD)+"/**",str(DATA)+"/**"],
      "status":"COMPLETE_READY_FOR_LOCAL_APPLY","scientific_claim_status":"below_gate_continue_optimization","fullscore":False,"production_champion":False,
      "hq_loso_receipt_present":False,"direct_data":{"n_rows_HQ":0,"n_synthetic_policy_cases":len(cases),"mandatory_files":[str(DATA/"calibration_policy.yaml"),str(DATA/"ood_cases.jsonl"),str(DATA/"reject_card.schema.json")]},
      "source_ledger_count":len(sources),"tests":{"return_code":r.returncode,"fixture_replay_passed":True,"receipt":"reports/receipts/tests_stdout.txt"},
      "inventory_excluding_manifest_and_checksum":inventory}
    put_json("RETURN_MANIFEST.json",manifest)

    secret_patterns=[r"-----BEGIN (?:RSA|EC|OPENSSH|DSA) PRIVATE KEY-----",r"ghp_[A-Za-z0-9]{30,}",r"sk-[A-Za-z0-9]{20,}",r"AKIA[0-9A-Z]{16}"]
    hits=[]
    for p in all_files():
        if p.suffix.lower() in {".py",".md",".json",".jsonl",".yaml",".yml",".txt",".csv",".patch"}:
            t=p.read_text(encoding="utf-8",errors="replace")
            for pat in secret_patterns:
                if re.search(pat,t): hits.append({"path":p.relative_to(ROOT).as_posix(),"pattern":pat})
    put_json("reports/SECRET_SCAN_REPORT.json",{"status":"PASS" if not hits else "FAIL","hits":hits,"patterns":secret_patterns})
    if hits: raise SystemExit("secret scan failed")
    public_hits=[]
    banned=["E:/UserData","E:\\UserData","C:/Users/","C:\\Users\\"]
    for p in all_files():
        if p.suffix.lower() in {".py",".md",".json",".jsonl",".yaml",".yml",".txt",".csv",".patch"}:
            t=p.read_text(encoding="utf-8",errors="replace")
            for x in banned:
                if x in t: public_hits.append({"path":p.relative_to(ROOT).as_posix(),"token":x})
    put_json("reports/PUBLIC_SAFE_SCAN.json",{"status":"PASS" if not public_hits else "FAIL","hits":public_hits})
    if public_hits: raise SystemExit("public safe scan failed")

    sums=[]
    for p in all_files():
        if p.name!="SHA256SUMS.txt": sums.append(f"{digest(p)}  {p.relative_to(ROOT).as_posix()}")
    put("SHA256SUMS.txt","\n".join(sums))
    for line in (ROOT/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        h,rel=line.split("  ",1)
        if digest(ROOT/rel)!=h: raise SystemExit("checksum mismatch: "+rel)
    put("reports/receipts/checksum_validation.txt",f"validated_entries={len(sums)}\nstatus=PASS\n")
    sums=[]
    for p in all_files():
        if p.name!="SHA256SUMS.txt": sums.append(f"{digest(p)}  {p.relative_to(ROOT).as_posix()}")
    put("SHA256SUMS.txt","\n".join(sums))

    print(json.dumps({"package":NAME,"files":len(all_files()),"sources":len(sources),"synthetic_cases":len(cases),"tests":"PASS","secret_scan":"PASS","public_safe_scan":"PASS","status":"COMPLETE_READY_FOR_LOCAL_APPLY"},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
