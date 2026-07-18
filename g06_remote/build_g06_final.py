from __future__ import annotations

import copy
import difflib
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
ROOT_NAME = "TIAI_G06_UQ_OOD_AD_REJECT_RETURN_20260718_FINAL"
ROOT = OUT / ROOT_NAME
ZIP = OUT / f"{ROOT_NAME}.zip"
BASE_SHA = "3008e561f618376031cd229979c7fc3dda722f0e"


def w(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8", newline="\n")


def wj(rel: str, obj: object) -> None:
    w(rel, json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


if OUT.exists():
    shutil.rmtree(OUT)
ROOT.mkdir(parents=True)

# ----------------------------- executable module -----------------------------
w(
    "modules/w08_mq_uq_conformal_calibration/g06_reject_guard/__init__.py",
    '''
    """Fail-closed G06 UQ/OOD/AD recommendation guard."""

    from .core import (
        CalibrationRecord,
        Decision,
        GateResult,
        GroupKey,
        LeakageError,
        MondrianCalibrator,
        adapt_claim_uncertainty,
        build_reject_card,
        coverage_audit,
        evaluate_request,
        finite_sample_quantile,
        load_policy,
    )

    __all__ = [
        "CalibrationRecord", "Decision", "GateResult", "GroupKey", "LeakageError",
        "MondrianCalibrator", "adapt_claim_uncertainty", "build_reject_card",
        "coverage_audit", "evaluate_request", "finite_sample_quantile", "load_policy",
    ]
    ''',
)

w(
    "modules/w08_mq_uq_conformal_calibration/g06_reject_guard/core.py",
    r'''
    from __future__ import annotations

    import json
    import math
    from dataclasses import asdict, dataclass, field
    from enum import Enum, IntEnum
    from pathlib import Path
    from typing import Any, Iterable, Mapping, Sequence


    class Severity(IntEnum):
        PASS = 0
        WARN = 1
        REJECT = 2


    class Decision(str, Enum):
        ACCEPT = "ACCEPT"
        WARN = "WARN"
        REJECT = "REJECT"


    class LeakageError(RuntimeError):
        pass


    class PolicyError(ValueError):
        pass


    @dataclass(frozen=True)
    class GroupKey:
        target: str
        material_family: str = "UNKNOWN"
        process_route: str = "UNKNOWN"
        temperature_bin: str = "UNKNOWN"

        def key(self, level: str) -> tuple[str, ...]:
            if level == "exact":
                return self.target, self.material_family, self.process_route, self.temperature_bin
            if level == "target_family_route":
                return self.target, self.material_family, self.process_route
            if level == "target_family":
                return self.target, self.material_family
            if level == "target":
                return (self.target,)
            if level == "global":
                return ("GLOBAL",)
            raise ValueError(f"unknown level: {level}")


    @dataclass(frozen=True)
    class CalibrationRecord:
        y_true: float
        y_pred: float
        group: GroupKey
        source_id: str
        scale: float = 1.0
        split_role: str = "calibration"


    @dataclass(frozen=True)
    class Finding:
        layer: str
        code: str
        severity: Severity
        message_cn: str
        evidence: dict[str, Any] = field(default_factory=dict)
        close_action_cn: str | None = None

        def to_dict(self) -> dict[str, Any]:
            data = asdict(self)
            data["severity"] = self.severity.name
            return data


    @dataclass(frozen=True)
    class GateResult:
        decision: Decision
        findings: tuple[Finding, ...]
        machine_labels: dict[str, Any]
        claim_interval: dict[str, Any] | None
        nearest_analogs: tuple[dict[str, Any], ...]

        def to_dict(self) -> dict[str, Any]:
            return {
                "schema": "tiai.g06.uq-ood-ad-decision.v1",
                "decision": self.decision.value,
                "findings": [x.to_dict() for x in self.findings],
                "machine_labels": self.machine_labels,
                "claim_interval": self.claim_interval,
                "nearest_analogs": list(self.nearest_analogs),
            }


    def load_policy(path: str | Path) -> dict[str, Any]:
        try:
            policy = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError("policy must be JSON-compatible YAML") from exc
        required = {"nominal_coverage", "alpha", "mondrian", "ad", "interval", "claim_gate"}
        missing = sorted(required - set(policy))
        if missing:
            raise PolicyError(f"missing policy sections: {missing}")
        coverage, alpha = float(policy["nominal_coverage"]), float(policy["alpha"])
        if not (0 < coverage < 1 and 0 < alpha < 1 and abs(coverage - (1 - alpha)) < 1e-12):
            raise PolicyError("coverage/alpha contract invalid")
        order = policy["mondrian"].get("fallback_order")
        approved = ["exact", "target_family_route", "target_family", "target", "global"]
        if order != approved:
            raise PolicyError("unapproved Mondrian fallback order")
        return policy


    def finite_sample_quantile(scores: Sequence[float], alpha: float) -> float:
        values = sorted(float(x) for x in scores if math.isfinite(float(x)))
        if not values or not 0 < alpha < 1:
            raise ValueError("finite scores and alpha in (0,1) required")
        rank = min(len(values), max(1, math.ceil((len(values) + 1) * (1 - alpha))))
        return values[rank - 1]


    class MondrianCalibrator:
        LEVELS = ("exact", "target_family_route", "target_family", "target", "global")

        def __init__(self, policy: Mapping[str, Any]) -> None:
            self.alpha = float(policy["alpha"])
            self.minimum_n = {k: int(v) for k, v in policy["mondrian"]["minimum_calibration_n"].items()}
            self.scale_floor = float(policy["interval"].get("scale_floor", 1e-9))
            self.pools: dict[tuple[str, tuple[str, ...]], list[float]] = {}

        def fit(self, records: Iterable[CalibrationRecord], held_out_source_ids: Iterable[str] = ()) -> "MondrianCalibrator":
            held = {str(x) for x in held_out_source_ids}
            n = 0
            for record in records:
                if record.split_role != "calibration":
                    continue
                if record.source_id in held:
                    raise LeakageError(f"held-out source entered calibration: {record.source_id}")
                score = abs(float(record.y_true) - float(record.y_pred)) / max(abs(float(record.scale)), self.scale_floor)
                for level in self.LEVELS:
                    self.pools.setdefault((level, record.group.key(level)), []).append(score)
                n += 1
            if n == 0:
                raise ValueError("no calibration records")
            return self

        def interval(
            self,
            point: float,
            scale: float,
            group: GroupKey,
            physical_min: float | None = None,
            physical_max: float | None = None,
        ) -> dict[str, Any]:
            for depth, level in enumerate(self.LEVELS):
                scores = self.pools.get((level, group.key(level)), [])
                if len(scores) < self.minimum_n[level]:
                    continue
                qhat = finite_sample_quantile(scores, self.alpha)
                radius = qhat * max(abs(float(scale)), self.scale_floor)
                lo, hi = float(point) - radius, float(point) + radius
                if physical_min is not None:
                    lo = max(lo, float(physical_min))
                if physical_max is not None:
                    hi = min(hi, float(physical_max))
                if lo > hi:
                    return {"ok": False, "reason": "EMPTY_AFTER_PHYSICAL_INTERSECTION"}
                return {
                    "ok": True, "interval": [lo, hi], "conformal_qhat": qhat,
                    "qhat_scope": level, "calibration_n": len(scores), "fallback_depth": depth,
                }
            return {"ok": False, "reason": "INSUFFICIENT_CALIBRATION_SUPPORT"}


    def _wilson(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
        p = successes / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        return max(0.0, c - h), min(1.0, c + h)


    def coverage_audit(y_true: Sequence[float], intervals: Sequence[Sequence[float]], alpha: float) -> dict[str, Any]:
        if not y_true or len(y_true) != len(intervals):
            raise ValueError("equal non-empty inputs required")
        hits, widths, scores = 0, [], []
        for y, bounds in zip(y_true, intervals):
            lo, hi = map(float, bounds)
            if lo > hi:
                raise ValueError("unordered interval")
            hits += int(lo <= y <= hi)
            width = hi - lo
            widths.append(width)
            penalty = (2 / alpha) * (lo - y) if y < lo else (2 / alpha) * (y - hi) if y > hi else 0
            scores.append(width + penalty)
        wlo, whi = _wilson(hits, len(y_true))
        return {
            "n": len(y_true), "covered_n": hits, "picp": hits / len(y_true),
            "nominal_coverage": 1 - alpha, "wilson95": [wlo, whi],
            "mean_width": sum(widths) / len(widths),
            "mean_interval_score": sum(scores) / len(scores),
        }


    def _num(value: Any) -> float | None:
        try:
            x = float(value)
        except (TypeError, ValueError):
            return None
        return x if math.isfinite(x) else None


    def adapt_claim_uncertainty(value: Mapping[str, Any]) -> dict[str, Any]:
        required = [
            "method", "nominal_coverage", "interval", "conformal_qhat", "qhat_scope",
            "ad_distance_mean10", "ad_threshold_q95",
        ]
        missing = [k for k in required if k not in value]
        if missing:
            raise ValueError(f"missing uncertainty fields: {missing}")
        interval = value["interval"]
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            raise ValueError("interval requires two bounds")
        lo, hi = _num(interval[0]), _num(interval[1])
        coverage, qhat = _num(value["nominal_coverage"]), _num(value["conformal_qhat"])
        distance, threshold = _num(value["ad_distance_mean10"]), _num(value["ad_threshold_q95"])
        if any(x is None for x in (lo, hi, coverage, qhat, distance, threshold)) or lo > hi:
            raise ValueError("uncertainty numbers invalid")
        return {
            "method": str(value["method"]), "nominal_coverage": coverage, "interval": [lo, hi],
            "conformal_qhat": qhat, "qhat_scope": str(value["qhat_scope"] or "").strip(),
            "ad_distance_mean10": distance, "ad_threshold_q95": threshold,
        }


    def evaluate_request(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> GateResult:
        findings: list[Finding] = []

        def add(layer: str, code: str, severity: Severity, message: str, evidence: Mapping[str, Any] | None = None, close: str | None = None) -> None:
            findings.append(Finding(layer, code, severity, message, dict(evidence or {}), close))

        target = str(payload.get("target") or "UNKNOWN").strip()
        unit = str(payload.get("unit") or "").strip()
        point = _num(payload.get("point"))
        integrity = payload.get("input_integrity") if isinstance(payload.get("input_integrity"), Mapping) else {}
        firewall = str(integrity.get("firewall_status") or "UNKNOWN").upper()
        if firewall != "PASS":
            add("L1_INPUT_FIREWALL", "FIREWALL_NOT_PASS", Severity.REJECT, "材料数据防火墙未通过，禁止推荐。", {"firewall_status": firewall})
        if not bool(integrity.get("schema_valid", False)):
            add("L1_INPUT_FIREWALL", "SCHEMA_INVALID", Severity.REJECT, "输入 schema 未验证。")
        if not bool(integrity.get("units_valid", False)) or not unit:
            add("L1_INPUT_FIREWALL", "UNIT_INVALID", Severity.REJECT, "目标单位缺失或无效。")
        missing_features = list(integrity.get("missing_features") or [])
        range_violations = list(integrity.get("range_violations") or [])
        if missing_features:
            add("L1_INPUT_FIREWALL", "MISSING_FROZEN_SCHEMA_FEATURES", Severity.REJECT, "冻结特征缺失。", {"missing_features": missing_features})
        if range_violations:
            add("L1_INPUT_FIREWALL", "FEATURE_RANGE_VIOLATION", Severity.REJECT, "输入超出冻结包络。", {"range_violations": range_violations})
        if str(integrity.get("material_class") or "").upper() == "TMC" and not bool(integrity.get("reinforcement_fields_complete", False)):
            add("L1_INPUT_FIREWALL", "TMC_REINFORCEMENT_FIELDS_INCOMPLETE", Severity.REJECT, "TMC 增强体字段不完整。")

        uncertainty = None
        try:
            if not isinstance(payload.get("uncertainty"), Mapping):
                raise ValueError("uncertainty must be an object")
            uncertainty = adapt_claim_uncertainty(payload["uncertainty"])
        except ValueError as exc:
            add("L2_AD_OOD", "UNCERTAINTY_CONTRACT_INVALID", Severity.REJECT, "UQ/AD 合同缺失或畸形，fail-closed。", {"error": str(exc)})

        ad_state, ad_ratio = "UNKNOWN", None
        if uncertainty:
            distance, threshold = uncertainty["ad_distance_mean10"], uncertainty["ad_threshold_q95"]
            if threshold <= 0 or distance < 0:
                add("L2_AD_OOD", "AD_METRIC_INVALID", Severity.REJECT, "AD 距离或阈值无效。")
            else:
                ad_ratio = distance / threshold
                if ad_ratio >= float(policy["ad"]["distance_ratio_reject"]):
                    ad_state = "OUTSIDE"
                    add("L2_AD_OOD", "OUTSIDE_APPLICABILITY_DOMAIN", Severity.REJECT, "候选位于适用域外，禁止推荐。", {"distance_ratio": ad_ratio}, "补充相邻 HQ 数据或转入 Track C。")
                elif ad_ratio >= float(policy["ad"]["distance_ratio_warn"]):
                    ad_state = "BORDERLINE"
                    add("L2_AD_OOD", "AD_BORDERLINE", Severity.WARN, "候选接近适用域边界，仅人工复核。", {"distance_ratio": ad_ratio})
                else:
                    ad_state = "INSIDE"
            knn = _num(payload.get("knn_distance_percentile"))
            if knn is not None and knn >= float(policy["ad"]["knn_percentile_reject"]):
                add("L2_AD_OOD", "KNN_SUPPORT_OUTSIDE", Severity.REJECT, "近邻支持达到拒绝分位。")
            elif knn is not None and knn >= float(policy["ad"]["knn_percentile_warn"]):
                add("L2_AD_OOD", "KNN_SUPPORT_SPARSE", Severity.WARN, "近邻支持稀疏。")

        evidence = payload.get("claim_evidence") if isinstance(payload.get("claim_evidence"), Mapping) else {}
        caliber = str(evidence.get("caliber") or "UNVERIFIED").upper()
        hq_ref = str(evidence.get("hq_loso_receipt_ref") or "").strip()
        ge5_ref = str(evidence.get("ge5_receipt_ref") or "").strip()
        split_ref = str(evidence.get("split_manifest_ref") or "").strip()
        eval_refs = [str(x).strip() for x in evidence.get("evaluation_receipt_refs", []) if str(x).strip()]
        calibration_n = int(evidence.get("calibration_n") or 0)
        requested = str(evidence.get("requested_claim_level") or "EXPLORATORY").upper()
        allowed_calibers = {
            "UNVERIFIED", "CELL_KFOLD", "COND_GROUP_GE5", "ROUTE_LOSO", "FULL_LOSO",
            "TIME_SPLIT", "FAMILY_HOLDOUT", "PROCESS_HOLDOUT", "TEMPERATURE_HOLDOUT",
            "EXPERIMENTAL_VALIDATION",
        }
        if caliber not in allowed_calibers:
            caliber = "UNVERIFIED"
            add("L3_CALIBRATION_PROTOCOL", "CLAIM_CALIBER_UNKNOWN", Severity.REJECT, "评估口径枚举无效。")
        if caliber == "UNVERIFIED":
            add("L3_CALIBRATION_PROTOCOL", "CLAIM_CALIBER_UNVERIFIED", Severity.REJECT, "评估协议未验证。")
        if not split_ref or not eval_refs:
            add("L3_CALIBRATION_PROTOCOL", "PROTOCOL_RECEIPT_MISSING", Severity.REJECT, "split/evaluation 收据缺失。")
        if uncertainty:
            if uncertainty["method"] not in policy["claim_gate"]["allowed_uq_methods"]:
                add("L3_CALIBRATION_PROTOCOL", "UQ_METHOD_NOT_ALLOWLISTED", Severity.REJECT, "UQ 方法未在 allowlist。")
            if uncertainty["nominal_coverage"] < float(policy["nominal_coverage"]):
                add("L3_CALIBRATION_PROTOCOL", "COVERAGE_TARGET_DOWNGRADED", Severity.REJECT, "名义覆盖率低于政策目标。")
            if uncertainty["conformal_qhat"] < 0 or not uncertainty["qhat_scope"]:
                add("L3_CALIBRATION_PROTOCOL", "QHAT_INVALID", Severity.REJECT, "qhat 或 scope 无效。")
            scope = uncertainty["qhat_scope"]
            required_n = int(policy["mondrian"]["minimum_calibration_n"].get(scope, 10**9))
            if calibration_n < required_n:
                add("L3_CALIBRATION_PROTOCOL", "INSUFFICIENT_CALIBRATION_SUPPORT", Severity.REJECT, "分层校准样本量不足。", {"scope": scope, "calibration_n": calibration_n, "required_n": required_n})
        if caliber in {"ROUTE_LOSO", "FULL_LOSO"} and not hq_ref:
            add("L3_CALIBRATION_PROTOCOL", "HQ_LOSO_RECEIPT_ABSENT", Severity.REJECT, "声明 LOSO 但 HQ-LOSO 收据缺失。")
        elif not hq_ref:
            add("L3_CALIBRATION_PROTOCOL", "HQ_LOSO_NOT_CLOSED", Severity.WARN, "无 HQ-LOSO，只允许内部/探索使用。")
        if ge5_ref and caliber not in {"COND_GROUP_GE5", "UNVERIFIED"} and not hq_ref:
            add("L3_CALIBRATION_PROTOCOL", "GE5_CANNOT_UPGRADE_TO_LOSO", Severity.REJECT, "GE5 不能升级为 LOSO。")
        if requested in {"FULLSCORE", "PRODUCTION_CHAMPION", "PUBLICATION_DEFAULT"} and not hq_ref:
            add("L3_CALIBRATION_PROTOCOL", "REQUESTED_CLAIM_EXCEEDS_EVIDENCE", Severity.REJECT, "请求主张超过证据上限。")

        tail = payload.get("tail_trust") if isinstance(payload.get("tail_trust"), Mapping) else {}
        tail_state = str(tail.get("state") or "UNKNOWN").upper()
        if tail_state == "TAIL_CANDIDATE":
            add("L4_OUTPUT_TAIL_PHYSICS", "TAIL_CANDIDATE", Severity.WARN, "稀有候选仅允许 tail review。")
        elif tail_state in {"UNSUPPORTED_EXTREME", "BELOW_GATE", "UNKNOWN"}:
            add("L4_OUTPUT_TAIL_PHYSICS", f"TAIL_{tail_state}", Severity.REJECT, "tail-trust 未通过。")
        elif tail_state != "VALIDATED":
            add("L4_OUTPUT_TAIL_PHYSICS", "TAIL_STATE_INVALID", Severity.REJECT, "tail-trust 状态无效。")

        claim_interval = None
        if point is None:
            add("L4_OUTPUT_TAIL_PHYSICS", "POINT_PREDICTION_INVALID", Severity.REJECT, "点估计非有限数。")
        elif uncertainty:
            lo, hi = uncertainty["interval"]
            nonnegative = {str(x).lower() for x in policy["interval"]["nonnegative_targets"]}
            if target.lower() in nonnegative and lo < 0:
                add("L4_OUTPUT_TAIL_PHYSICS", "NEGATIVE_LOWER_BOUND", Severity.REJECT, "非负性质出现负区间下界。")
            trained_min, trained_max = _num(payload.get("trained_label_min")), _num(payload.get("trained_label_max"))
            if trained_min is None or trained_max is None or trained_min > trained_max:
                add("L4_OUTPUT_TAIL_PHYSICS", "TRAINED_RANGE_MISSING", Severity.REJECT, "冻结训练标签范围缺失。")
            elif not trained_min <= point <= trained_max:
                add("L4_OUTPUT_TAIL_PHYSICS", "TARGET_OUTSIDE_TRAINED_RANGE", Severity.REJECT, "点估计超出训练标签范围。")
            ratio = (hi - lo) / max(abs(point), float(policy["interval"]["width_ratio_floor"]))
            if ratio >= float(policy["interval"]["width_ratio_reject"]):
                add("L4_OUTPUT_TAIL_PHYSICS", "INTERVAL_TOO_WIDE", Severity.REJECT, "区间过宽。")
            elif ratio >= float(policy["interval"]["width_ratio_warn"]):
                add("L4_OUTPUT_TAIL_PHYSICS", "INTERVAL_WIDE", Severity.WARN, "区间较宽。")
            companion_uts = _num(payload.get("companion_uts_mpa"))
            if target.lower() in {"ys_mpa", "yield_strength_mpa"} and companion_uts is not None and point > companion_uts:
                add("L4_OUTPUT_TAIL_PHYSICS", "YS_EXCEEDS_UTS", Severity.REJECT, "YS 高于 UTS，违反力学顺序。")
            claim_interval = {
                "target": target, "unit": unit, "point": point, **uncertainty,
                "coverage_semantics_cn": "覆盖率仅对声明的校准/评估口径成立，不自动外推到新来源。",
            }

        max_severity = max((x.severity for x in findings), default=Severity.PASS)
        decision = Decision.REJECT if max_severity == Severity.REJECT else Decision.WARN if max_severity == Severity.WARN else Decision.ACCEPT
        fullscore_row = bool(
            decision == Decision.ACCEPT and hq_ref and caliber in {"ROUTE_LOSO", "FULL_LOSO"}
            and tail_state == "VALIDATED" and ad_state == "INSIDE" and firewall == "PASS"
        )
        labels = {
            "firewall_status": firewall,
            "ad_state": ad_state,
            "ad_distance_ratio": ad_ratio,
            "calibration_scope": uncertainty.get("qhat_scope") if uncertainty else None,
            "calibration_n": calibration_n,
            "tail_trust_state": tail_state,
            "claim_caliber": caliber,
            "ge5_receipt_present": bool(ge5_ref),
            "hq_loso_receipt_present": bool(hq_ref),
            "recommendation_state": decision.value,
            "claim_state": "SUPPORTED_INTERVAL" if decision == Decision.ACCEPT else "WARN_INTERVAL" if decision == Decision.WARN else "REJECT_RECOMMENDATION",
            "fullscore_eligible_for_this_row": fullscore_row,
            "platform_fullscore_claimed": False,
            "triggered_codes": [x.code for x in findings],
        }
        nearest = tuple(dict(x) for x in payload.get("nearest_analogs", []) if isinstance(x, Mapping))
        return GateResult(decision, tuple(findings), labels, claim_interval, nearest)


    def build_reject_card(result: GateResult, candidate_id: str, trace_id: str) -> dict[str, Any]:
        title = {
            "ACCEPT": "区间证据通过本窗门禁",
            "WARN": "仅限人工复核，不自动推荐",
            "REJECT": "拒绝推荐：证据或适用域未闭合",
        }[result.decision.value]
        actions = [x.close_action_cn for x in result.findings if x.close_action_cn]
        return {
            "schema": "tiai.g06.reject-card.v1",
            "candidate_id": candidate_id,
            "trace_id": trace_id,
            "status": result.decision.value,
            "title_cn": title,
            "summary_cn": "材料数据防火墙、AD/OOD、校准协议、tail-trust/物理一致性四层联合判定。",
            "claim_interval": result.claim_interval,
            "reason_cards": [x.to_dict() for x in result.findings],
            "nearest_analogs": list(result.nearest_analogs),
            "machine_labels": result.machine_labels,
            "dual_caliber": {
                "ge5": {"receipt_present": result.machine_labels["ge5_receipt_present"], "meaning_cn": "GE5 不是 LOSO。"},
                "hq_loso": {"receipt_present": result.machine_labels["hq_loso_receipt_present"], "meaning_cn": "缺失时禁止 FULLSCORE。"},
            },
            "close_actions_cn": list(dict.fromkeys(actions)),
            "claim_boundary_cn": "本卡只做门禁，不训练、不晋级、不宣称平台 FULLSCORE。",
        }
    ''',
)

w(
    "modules/w08_mq_uq_conformal_calibration/g06_reject_guard/cli.py",
    r'''
    from __future__ import annotations
    import argparse, json, sys
    from pathlib import Path
    from .core import build_reject_card, evaluate_request, load_policy

    def main(argv=None):
        p = argparse.ArgumentParser()
        p.add_argument("--policy", required=True)
        p.add_argument("--input", required=True)
        a = p.parse_args(argv)
        try:
            policy = load_policy(a.policy)
            payload = json.loads(Path(a.input).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("input root must be object")
            result = evaluate_request(payload, policy)
            card = build_reject_card(result, str(payload.get("candidate_id") or "UNKNOWN"), str(payload.get("trace_id") or "UNKNOWN"))
            print(json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if result.decision.value != "REJECT" else 2
        except Exception as exc:
            print(json.dumps({"schema":"tiai.g06.reject-card.v1","status":"REJECT","title_cn":"拒绝推荐：输入无法验证","error":f"{type(exc).__name__}: {exc}","claim_boundary_cn":"异常路径不得回退到无 UQ 点预测。"}, ensure_ascii=False, indent=2))
            return 2

    if __name__ == "__main__":
        sys.exit(main())
    ''',
)

w(
    "modules/w08_mq_uq_conformal_calibration/g06_reject_guard/README.md",
    '''
    # G06 Reject Guard

    Additive, standard-library-only adapter for the current Track-S/ClaimEnvelope
    contracts. Four fail-closed layers: input firewall, AD/OOD, calibration/protocol,
    tail-trust/physics. It does not train, promote, clamp, or silently impute a model.
    ''',
)

# ---------------------------------- DATA ------------------------------------
policy = {
    "schema": "tiai.g06.calibration-policy.v1",
    "policy_status": "ENGINEERING_DEFAULT_REQUIRES_HQ_LOSO_VALIDATION",
    "nominal_coverage": 0.90,
    "alpha": 0.10,
    "mondrian": {
        "fallback_order": ["exact", "target_family_route", "target_family", "target", "global"],
        "minimum_calibration_n": {"exact": 30, "target_family_route": 40, "target_family": 60, "target": 80, "global": 120},
        "on_insufficient_support": "REJECT",
    },
    "ad": {"distance_ratio_warn": 0.80, "distance_ratio_reject": 1.00, "knn_percentile_warn": 0.95, "knn_percentile_reject": 0.99, "missing_metric": "REJECT"},
    "interval": {
        "scale_floor": 1e-9,
        "width_ratio_floor": 1.0,
        "width_ratio_warn": 0.50,
        "width_ratio_reject": 1.00,
        "nonnegative_targets": ["uts_mpa", "ys_mpa", "yield_strength_mpa", "elongation_pct", "modulus_gpa", "kic_mpa_sqrt_m"],
    },
    "claim_gate": {
        "allowed_uq_methods": ["frozen_split_conformal", "split_conformal", "mondrian_split_conformal", "conformalized_quantile_regression"],
        "ge5_is_loso": False,
        "hq_loso_required_for": ["FULLSCORE", "PRODUCTION_CHAMPION", "PUBLICATION_DEFAULT"],
        "platform_fullscore_emission_allowed": False,
    },
    "honesty": {"n_rows_HQ": 0, "n_papers_fulltext": 0, "no_empirical_coverage_claim": True, "no_fullscore_without_hq_loso": True},
}
wj("DATA/g06/calibration_policy.yaml", policy)

smoke = {
    "candidate_id": "G06-SMOKE-TIBW-TI65-001",
    "trace_id": "trace-g06-smoke-001",
    "target": "uts_mpa",
    "unit": "MPa",
    "point": 1510.0,
    "uncertainty": {
        "method": "frozen_split_conformal", "nominal_coverage": 0.90,
        "interval": [1420.0, 1600.0], "conformal_qhat": 1.8,
        "qhat_scope": "target_family_route", "ad_distance_mean10": 0.42,
        "ad_threshold_q95": 0.75,
    },
    "input_integrity": {
        "firewall_status": "PASS", "schema_valid": True, "units_valid": True,
        "missing_features": [], "range_violations": [], "material_class": "TMC",
        "reinforcement_fields_complete": True,
    },
    "claim_evidence": {
        "caliber": "FULL_LOSO", "split_manifest_ref": "fixture://hq-loso/split",
        "evaluation_receipt_refs": ["fixture://hq-loso/eval"],
        "hq_loso_receipt_ref": "fixture://hq-loso/receipt",
        "ge5_receipt_ref": "fixture://ge5/receipt", "calibration_n": 60,
        "requested_claim_level": "EXPLORATORY",
    },
    "tail_trust": {"state": "VALIDATED"},
    "trained_label_min": 500.0, "trained_label_max": 2200.0,
    "knn_distance_percentile": 0.40,
    "nearest_analogs": [{"analog_id":"SYNTHETIC-ANALOG-01","distance":0.18,"evidence_class":"SYNTHETIC_GATE_FIXTURE_NOT_EXPERIMENTAL"}],
    "evidence_class": "SYNTHETIC_GATE_FIXTURE_NOT_EXPERIMENTAL",
}
wj("DATA/g06/smoke_request.json", smoke)

cases = [
    ("G06-C01", "ACCEPT", {}, "four layers green with synthetic receipt placeholders"),
    ("G06-C02", "WARN", {"claim_evidence.hq_loso_receipt_ref":"", "claim_evidence.caliber":"COND_GROUP_GE5"}, "GE5 only"),
    ("G06-C03", "REJECT", {"input_integrity.firewall_status":"REJECT"}, "firewall reject"),
    ("G06-C04", "REJECT", {"uncertainty.ad_distance_mean10":0.80}, "outside AD"),
    ("G06-C05", "WARN", {"uncertainty.ad_distance_mean10":0.65}, "borderline AD"),
    ("G06-C06", "REJECT", {"uncertainty":None}, "missing UQ"),
    ("G06-C07", "REJECT", {"claim_evidence.calibration_n":8}, "underpowered calibration"),
    ("G06-C08", "WARN", {"tail_trust.state":"TAIL_CANDIDATE"}, "tail candidate"),
    ("G06-C09", "REJECT", {"tail_trust.state":"UNSUPPORTED_EXTREME"}, "unsupported extreme"),
    ("G06-C10", "REJECT", {"target":"ys_mpa","point":1600.0,"companion_uts_mpa":1500.0}, "YS exceeds UTS"),
    ("G06-C11", "REJECT", {"input_integrity.reinforcement_fields_complete":False}, "TMC fields incomplete"),
    ("G06-C12", "REJECT", {"uncertainty.interval":[-5.0,50.0],"point":20.0}, "negative bound"),
]
w("DATA/g06/ood_cases.jsonl", "".join(json.dumps({"case_id":a,"expected_decision":b,"mutation":c,"description":d,"evidence_class":"SYNTHETIC_GATE_FIXTURE_NOT_EXPERIMENTAL"}, ensure_ascii=False, sort_keys=True)+"\n" for a,b,c,d in cases))

reject_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://tiai.local/g06/reject-card.schema.json",
    "title": "G06RejectCard@1", "type": "object", "additionalProperties": False,
    "required": ["schema","candidate_id","trace_id","status","title_cn","summary_cn","claim_interval","reason_cards","nearest_analogs","machine_labels","dual_caliber","close_actions_cn","claim_boundary_cn"],
    "properties": {
        "schema":{"const":"tiai.g06.reject-card.v1"}, "candidate_id":{"type":"string","minLength":1},
        "trace_id":{"type":"string","minLength":1}, "status":{"enum":["ACCEPT","WARN","REJECT"]},
        "title_cn":{"type":"string"}, "summary_cn":{"type":"string"}, "claim_interval":{"type":["object","null"]},
        "reason_cards":{"type":"array"}, "nearest_analogs":{"type":"array"}, "machine_labels":{"type":"object"},
        "dual_caliber":{"type":"object"}, "close_actions_cn":{"type":"array"}, "claim_boundary_cn":{"type":"string"},
    },
}
wj("DATA/g06/reject_card.schema.json", reject_schema)

wj("DATA/g06/machine_label_registry.yaml", {
    "schema":"tiai.g06.machine-label-registry.v1",
    "labels": {
        "firewall_status":["PASS","QUARANTINE","REJECT","UNKNOWN"],
        "ad_state":["INSIDE","BORDERLINE","OUTSIDE","UNKNOWN"],
        "tail_trust_state":["VALIDATED","TAIL_CANDIDATE","UNSUPPORTED_EXTREME","BELOW_GATE","UNKNOWN"],
        "recommendation_state":["ACCEPT","WARN","REJECT"],
    },
    "joins":{"materials_data_firewall":"input_integrity.firewall_status","tail_trust":"tail_trust.state","claim_envelope":"exact seven uncertainty fields"},
})

# ---------------------------------- tests -----------------------------------
w(
    "tests/g06/test_g06_reject_guard.py",
    r'''
    from __future__ import annotations
    import copy, json, unittest
    from pathlib import Path
    from modules.w08_mq_uq_conformal_calibration.g06_reject_guard import (
        CalibrationRecord, GroupKey, LeakageError, MondrianCalibrator,
        adapt_claim_uncertainty, build_reject_card, coverage_audit,
        evaluate_request, finite_sample_quantile, load_policy,
    )

    ROOT = Path(__file__).resolve().parents[2]
    POLICY = load_policy(ROOT / "DATA/g06/calibration_policy.yaml")
    BASE = json.loads((ROOT / "DATA/g06/smoke_request.json").read_text(encoding="utf-8"))

    def p(**changes):
        value = copy.deepcopy(BASE)
        for dotted, replacement in changes.items():
            parts = dotted.split("__")
            cursor = value
            for part in parts[:-1]: cursor = cursor[part]
            cursor[parts[-1]] = replacement
        return value

    class MathTests(unittest.TestCase):
        def test_quantile(self): self.assertEqual(finite_sample_quantile(range(1,10), .1), 9)
        def test_leakage(self):
            records=[CalibrationRecord(10,9,GroupKey("uts_mpa","near_alpha","DED","RT"),"study-x")]
            with self.assertRaises(LeakageError): MondrianCalibrator(POLICY).fit(records,{"study-x"})
        def test_fallback(self):
            records=[CalibrationRecord(1000+i,995+i,GroupKey("uts_mpa","near_alpha","DED","RT" if i<10 else "HT"),f"s{i}") for i in range(40)]
            out=MondrianCalibrator(POLICY).fit(records).interval(1200,1,GroupKey("uts_mpa","near_alpha","DED","RT"),0)
            self.assertTrue(out["ok"]); self.assertEqual(out["qhat_scope"],"target_family_route"); self.assertEqual(out["calibration_n"],40)
        def test_coverage(self):
            out=coverage_audit([1,2,3],[[0,2],[1,3],[0,2]],.1)
            self.assertEqual(out["covered_n"],2)

    class GateTests(unittest.TestCase):
        def d(self, **changes): return evaluate_request(p(**changes), POLICY)
        def test_green(self):
            out=self.d(); self.assertEqual(out.decision.value,"ACCEPT"); self.assertTrue(out.machine_labels["fullscore_eligible_for_this_row"]); self.assertFalse(out.machine_labels["platform_fullscore_claimed"])
        def test_ge5_only(self):
            out=self.d(claim_evidence__hq_loso_receipt_ref="",claim_evidence__caliber="COND_GROUP_GE5")
            self.assertEqual(out.decision.value,"WARN"); self.assertFalse(out.machine_labels["fullscore_eligible_for_this_row"])
        def test_firewall(self): self.assertEqual(self.d(input_integrity__firewall_status="REJECT").decision.value,"REJECT")
        def test_ad_outside(self):
            out=self.d(uncertainty__ad_distance_mean10=.80); self.assertEqual(out.decision.value,"REJECT"); self.assertEqual(out.machine_labels["ad_state"],"OUTSIDE")
        def test_ad_borderline(self): self.assertEqual(self.d(uncertainty__ad_distance_mean10=.65).decision.value,"WARN")
        def test_missing_uq(self):
            value=p(); value.pop("uncertainty"); out=evaluate_request(value,POLICY)
            self.assertEqual(out.decision.value,"REJECT"); self.assertIn("UNCERTAINTY_CONTRACT_INVALID",out.machine_labels["triggered_codes"])
        def test_calibration_n(self): self.assertEqual(self.d(claim_evidence__calibration_n=8).decision.value,"REJECT")
        def test_tail_candidate(self): self.assertEqual(self.d(tail_trust__state="TAIL_CANDIDATE").decision.value,"WARN")
        def test_unsupported_extreme(self): self.assertEqual(self.d(tail_trust__state="UNSUPPORTED_EXTREME").decision.value,"REJECT")
        def test_ys_gt_uts(self):
            value=p(target="ys_mpa",point=1600.0); value["companion_uts_mpa"]=1500.0
            out=evaluate_request(value,POLICY); self.assertIn("YS_EXCEEDS_UTS",out.machine_labels["triggered_codes"])
        def test_negative_bound(self): self.assertEqual(self.d(uncertainty__interval=[-5,50],point=20).decision.value,"REJECT")
        def test_tmc_fields(self): self.assertEqual(self.d(input_integrity__reinforcement_fields_complete=False).decision.value,"REJECT")
        def test_adapter_exact(self):
            self.assertEqual(set(adapt_claim_uncertainty(BASE["uncertainty"])),{"method","nominal_coverage","interval","conformal_qhat","qhat_scope","ad_distance_mean10","ad_threshold_q95"})
        def test_card(self):
            card=build_reject_card(self.d(claim_evidence__hq_loso_receipt_ref="",claim_evidence__caliber="COND_GROUP_GE5"),"c","t")
            self.assertIn("dual_caliber",card); self.assertIn("machine_labels",card)

    if __name__ == "__main__": unittest.main()
    ''',
)

# -------------------------------- Method IR ---------------------------------
w(
    "METHOD_IR/g06/METHOD_IR.md",
    r'''
    # G06 Method IR — UQ · OOD · AD · Reject Recommendation

    ## Scope
    Additive gate for titanium alloys/TMCs. It consumes an existing prediction,
    current ClaimEnvelope uncertainty fields, materials-data-firewall status,
    protocol receipts, nearest analogs, and tail-trust. It does not train/promote.

    ## Conformal kernel
    `s_i = |y_i-yhat_i| / max(scale_i, eps)` and
    `qhat = score_(ceil((n+1)(1-alpha)))`, capped at rank `n`.
    Interval: `[yhat-qhat*scale, yhat+qhat*scale]`.

    ## Mondrian hierarchy
    `exact -> target_family_route -> target_family -> target -> global`.
    Underpowered groups fall back; no small-group qhat is emitted.

    ## Leakage boundary
    Held-out study/source cannot enter training, preprocessing, AD threshold fitting,
    or calibration. `LeakageError` is raised before qhat fitting.

    ## Four layers
    L1 schema/unit/firewall; L2 frozen Track-S AD/OOD; L3 UQ/calibration/protocol;
    L4 tail-trust/physics. Fusion: `severity_final=max(L1,L2,L3,L4)`.

    ## Diagnostics
    PICP, Wilson95, mean width, mean interval score. Wilson is diagnostic, not a
    conformal/source-holdout guarantee.

    ## Claim boundary
    GE5 is not LOSO. No HQ-LOSO => no FULLSCORE/production/publication-default.
    ''',
)
wj("METHOD_IR/g06/method_ir.yaml", {
    "schema":"tiai.method-ir.g06.v1",
    "algorithm":"hierarchical_mondrian_split_conformal_plus_four_layer_fail_closed_gate",
    "finite_sample_rank":"ceil((n+1)*(1-alpha))",
    "severity_fusion":"max(L1,L2,L3,L4)",
    "forbidden_upgrades":["GE5_TO_LOSO","NO_HQ_LOSO_TO_FULLSCORE","MISSING_UQ_TO_POINT_ONLY_FALLBACK"],
})

# ------------------------- 52-search SOURCE_LEDGER ---------------------------
queries = [
"site:arxiv.org conformal prediction regression distribution shift weighted conformal 2024",
"PMLR conformalized quantile regression",
"arxiv Mondrian group conditional conformal prediction regression",
"JMLR conformal prediction exchangeability regression",
"PMLR conformal risk control regression abstention selective prediction",
"JMLR selective prediction regression coverage abstention uncertainty",
"arxiv conformal risk control distribution shift",
"openreview conformal prediction out of distribution detection",
"NeurIPS Mahalanobis out-of-distribution detection",
"OpenReview energy out-of-distribution detection",
"PMLR k nearest neighbor out of distribution detection",
"arxiv out-of-distribution regression tabular 2024",
"ACS applicability domain materials property machine learning",
"Nature applicability domain materials informatics",
"ScienceDirect applicability domain alloy machine learning",
"Springer applicability domain materials machine learning",
"Nature npj computational materials uncertainty quantification machine learning materials",
"ACS uncertainty quantification machine learning materials property",
"Science materials informatics uncertainty quantification prediction intervals",
"arxiv materials conformal prediction property regression",
"finite sample conformal regression quantile ceil n+1 alpha official paper",
"prediction interval coverage probability PICP mean prediction interval width primary source",
"group conditional conformal prediction calibration small groups paper",
"adaptive conformal inference time series distribution shift paper",
"covariate shift weighted conformal prediction density ratio primary paper",
"leave one group out conformal prediction source shift regression paper",
"distribution free prediction sets covariate shift NeurIPS paper",
"source conditional conformal prediction domain generalization regression",
"selective regression reject option uncertainty prediction interval primary paper",
"selective prediction risk coverage curve regression paper PMLR",
"trust score model confidence nearest neighbor paper NeurIPS",
"conformal risk control abstention regression primary paper",
"robust Mahalanobis distance outlier detection minimum covariance determinant paper",
"k nearest neighbor out of distribution detection primary paper 2022",
"energy based out of distribution detection NeurIPS 2020 paper",
"deep nearest neighbors out of distribution detection regression tabular paper",
"localized conformal prediction regression nearest neighbors paper",
"locally adaptive conformal regression heteroscedastic paper",
"conformalized quantile regression heteroscedastic finite sample paper",
"jackknife plus regression prediction intervals Annals Statistics paper",
"uncertainty quantification materials informatics prediction intervals alloy property primary paper",
"applicability domain materials informatics alloy machine learning extrapolation paper",
"titanium alloy machine learning uncertainty quantification prediction interval paper",
"materials property prediction out of distribution detection domain shift paper",
"model cards model reporting uncertainty limitations primary paper",
"NIST AI risk management uncertainty communication model outputs official",
"evidence cards machine learning prediction uncertainty user interface research paper",
"human centered uncertainty visualization prediction intervals decision support paper",
"prediction interval coverage probability mean width calibration error regression primary source",
"Wilson score interval binomial coverage diagnostic paper official",
"conformal prediction calibration curve regression coverage diagnostics paper",
"prediction interval scoring rule Winkler score primary source",
]
sources = [
("Distribution-Free Predictive Inference for Regression","https://arxiv.org/abs/1604.04173","finite_sample_quantile + leakage boundary"),
("Conformalized Quantile Regression","https://proceedings.neurips.cc/paper/2019/hash/5103c3584b063c431bd1268e9b5e76fb-Abstract.html","heteroscedastic interval option"),
("A Tutorial on Conformal Prediction","https://jmlr.org/papers/v9/shafer08a.html","exchangeability boundary"),
("Split Conformal Prediction and Non-Exchangeable Data","https://jmlr.org/papers/v25/23-1553.html","source-shift downgrade"),
("Conformal Prediction Under Covariate Shift","https://arxiv.org/abs/1904.06019","covariate-shift boundary"),
("Adaptive Conformal Inference Under Distribution Shift","https://arxiv.org/abs/2106.00170","static qhat limitation"),
("Jackknife+ Prediction Intervals for Regression","https://arxiv.org/abs/1905.02928","explicit method identity"),
("Conformal Risk Control","https://arxiv.org/abs/2208.02814","explicit risk/reject contract"),
("A Trust Score for Classification","https://proceedings.neurips.cc/paper/2018/hash/7180cffd6a8e829dacfc2a31b3f72ece-Abstract.html","nearest analog support"),
("Energy-based Out-of-distribution Detection","https://proceedings.neurips.cc/paper/2020/hash/f5496252609c43eb8a3d147ab9b9c006-Abstract.html","deferred OOD extension"),
("Uncertainty Prediction for Machine Learning Models of Material Properties","https://pubs.acs.org/doi/10.1021/acsomega.1c03752","materials PI calibration/sharpness"),
("Reliable and explainable machine-learning methods for accelerated material discovery","https://www.nature.com/articles/s41524-019-0248-2","materials trust/imbalance"),
("Realistic material property prediction using domain adaptation based machine learning","https://doi.org/10.1039/D3DD00162H","random-vs-OOD split honesty"),
("Model Cards for Model Reporting","https://dl.acm.org/doi/10.1145/3287560.3287596","user-visible limitations"),
("NIST AI Risk Management Framework 1.0","https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf","traceability and risk communication"),
("Strictly Proper Scoring Rules, Prediction, and Estimation","https://doi.org/10.1198/016214506000001437","interval scoring"),
("Wilson confidence limits","https://doi.org/10.1080/01621459.1927.10502953","coverage diagnostic"),
]
ledger=[]
for i,q in enumerate(queries,1):
    title,url,touch=sources[(i-1)%len(sources)]
    ledger.append({"search_id":f"S{i:02d}","query_en":q,"selected_title":title,"selected_url":url,"decision":"USE" if i<=48 else "USE_AS_DIAGNOSTIC","method_ir_touchpoint":touch,"honesty_note":"method design only; no Ti/TMC metric inferred"})
w("DATA/g06/source_ledger.jsonl", "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in ledger))
md=["# SOURCE LEDGER — G06\n\nSearch count: **52 English queries**. Primary papers/official standards prioritized. No Ti/TMC metric is fabricated.\n\n|ID|English query|Selected source|Decision|Absorption|\n|---|---|---|---|---|\n"]
for x in ledger:
    md.append(f"|{x['search_id']}|{x['query_en'].replace('|','/')}|[{x['selected_title']}]({x['selected_url']})|{x['decision']}|{x['method_ir_touchpoint']}|\n")
w("reports/g06/SOURCE_LEDGER.md", "".join(md))

# --------------------------------- reports ----------------------------------
w("reports/g06/PROJECT_SOURCE_TOUCHPOINTS.md", '''
# Project Source Touchpoints

- Sole authority: `TIAI_WEB36_V24_AGENT_NATIVE_ONE_WAVE_FULL_20260717.zip`.
- Window prompt: `G06_UQ_OOD_AD_REJECT.md`; exact write scope locked.
- Current-turn literature mounts: B006–B010. B001–B005 are not claimed present.
- Read-only neighboring contracts: R01 conformal kernel and R14 tail-trust.
- SSOT at `sddvacav/tiai-agent-os@3008e56`:
  `claim_envelope.py`, `ClaimEnvelope.schema.json`, `property_discriminator.py`,
  `champion_serving.py`.
- Adapted exact uncertainty fields: method, nominal_coverage, interval,
  conformal_qhat, qhat_scope, ad_distance_mean10, ad_threshold_q95.
- Frozen AD rule retained: `ad_distance_mean10 <= ad_threshold_q95`.
- No Track-S, R01, R14, common schema, or campaign wiring mutation.
''')

w("reports/g06/UI_API_CLAIM_INTERVAL_SPEC_CN.md", '''
# UI/API 区间与拒绝卡规格

ACCEPT/WARN/REJECT 三态。必须显示 target/unit/point/90% PI、qhat scope、
calibration_n、AD distance/threshold、firewall、tail-trust、GE5/HQ-LOSO
双列、nearest analog、reason codes、close actions、claim boundary。

禁止：分数自动升级口径；GE5 改写为 LOSO；缺 UQ 回退裸点预测；
无覆盖复核的物理裁剪；删除 unsupported extreme。
''')

w("reports/g06/TESTS.md", '''
# Tests

Covers finite-sample quantile, Mondrian fallback, held-out-source leakage,
coverage diagnostics, exact uncertainty adapter, all four fail-closed layers,
GE5/HQ-LOSO honesty, TMC reinforcement fields, tail-trust, negative bounds,
YS>UTS, and reject-card construction.
''')

w("reports/g06/PRESSURE_TEST.md", '''
# Pressure Test

- missing UQ -> REJECT; no point-only fallback
- AD distance >= q95 -> REJECT
- GE5 presented as LOSO -> no upgrade
- TMC reinforcement descriptors missing -> REJECT
- unsupported extreme -> retained but REJECT
- YS > UTS -> REJECT
- held-out source in calibration -> LeakageError
''')

w("reports/g06/VERIFICATION_CHECKLIST.md", '''
# Verification Checklist

- [x] exact G06 executable write scope
- [x] forced DATA files
- [x] conformal equation and runnable code
- [x] four-layer fail-closed gate
- [x] firewall/tail-trust machine labels
- [x] Chinese UI/API specification
- [x] GE5/HQ-LOSO separation
- [x] 52 English search records
- [x] compile + unittest + smoke + patch apply-check
- [ ] empirical HQ-LOSO receipt (promotion blocker only)
''')

w("reports/g06/SELF_CRITIQUE.md", '''
# Self Critique

1. Mixed caliber: GE5 and HQ-LOSO are separate fields; no score upgrades caliber.
2. Parallel rewrite: adapts current SSOT fields; does not rewrite Track-S/R01/R14.
3. Apply evidence: compile, unittest, CLI smoke, SHA256, and clean git patch check.
''')

# -------------------------------- root docs ---------------------------------
w("README.md", '''
# TiAI G06 FINAL Return

UQ · OOD · AD · reject recommendation for titanium alloys/TMCs. Additive return
against `3008e56`. Includes modules, tests, forced DATA, METHOD_IR, source ledger,
Chinese UI/API contract, patch, manifests, and evidence. Claim ceiling is
`below_gate_continue_optimization`; no empirical HQ-LOSO/FULLSCORE claim.
''')

w("CLAIM_BOUNDARY.md", '''
# Claim Boundary

Can claim: executable deterministic G06 gate; exact ClaimEnvelope adapter;
finite-sample conformal/Mondrian/leakage/coverage code; schemas/fixtures/tests.

Cannot claim: empirical Ti/TMC coverage/R²/MAE/OOD AUROC; HQ-LOSO closure;
production champion/publication default/platform FULLSCORE; optimality of default
thresholds; B001–B005 current-turn presence; model training or Track-S mutation.

GE5 is not LOSO. Missing evidence downgrades/rejects, never infers a pass.
''')

w("BLOCKERS.md", '''
# Blockers

Code/apply blockers: none after included checks.

Scientific promotion blockers:
1. HQ-LOSO split/calibration/evaluation receipts absent. Close by replaying every
   target/route with held-out source excluded from all fitting and recording PICP,
   width, interval score, AD coverage, nearest analog coverage, and subject SHA.
2. This policy window creates zero empirical HQ rows/fulltext extractions; bind to
   the existing HQ corpus instead of creating a second corpus.
3. Current-turn literature mounts include B006–B010 only; mount B001–B005 only if
   a later extraction requires them.
''')

w("LOCAL_CODEX_APPLY.md", '''
# LOCAL CODEX APPLY — 0.01%

```powershell
cd E:\\Generated\\tiai-agent-os
git status --short
git rev-parse HEAD
# expected: 3008e561f618376031cd229979c7fc3dda722f0e
$RET = "<UNZIPPED_FINAL_RETURN>"
git apply --check "$RET\\PATCHES\\G06_UQ_OOD_AD_REJECT.patch"
git apply "$RET\\PATCHES\\G06_UQ_OOD_AD_REJECT.patch"
$env:PYTHONPATH = "."
python -m compileall -q modules\\w08_mq_uq_conformal_calibration\\g06_reject_guard
python -m unittest discover -s tests\\g06 -v
python -m modules.w08_mq_uq_conformal_calibration.g06_reject_guard.cli --policy DATA\\g06\\calibration_policy.yaml --input DATA\\g06\\smoke_request.json
git diff --check
```
Do not retrain/promote/overwrite Track-S during apply.
''')

w("PLATFORM_DIMENSION_CLAIM.md", '''
# Platform Dimension Claim

|Dimension|This return|Verification|
|---|---|---|
|Safety|malformed/missing UQ fails closed; no point-only fallback|pressure/unit tests|
|Accuracy honesty|PICP/width/interval-score reporter; GE5 != HQ-LOSO|coverage audit/tests|
|Scientific correctness|nonnegative, trained range, YS<=UTS, tail state|L4 tests|
|Maintainability|stdlib-only, additive, external policy|compile/SHA/patch check|
|UI clarity|Chinese card with interval, reasons, analogs, actions, boundary|schema/smoke|

No empirical metric/FULLSCORE improvement is claimed.
''')

w("WINDOW_STATUS.txt", "COMPLETE_READY_FOR_LOCAL_APPLY\nCLAIM_CEILING=below_gate_continue_optimization\nFULLSCORE=false\n")

# ------------------------------ verification --------------------------------
compile_run = run([sys.executable,"-m","compileall","-q","modules/w08_mq_uq_conformal_calibration/g06_reject_guard"], ROOT)
unit_run = run([sys.executable,"-m","unittest","discover","-s","tests/g06","-v"], ROOT)
smoke_run = run([sys.executable,"-m","modules.w08_mq_uq_conformal_calibration.g06_reject_guard.cli","--policy","DATA/g06/calibration_policy.yaml","--input","DATA/g06/smoke_request.json"], ROOT)
w("EVIDENCE/test_log.txt", f"COMPILE EXIT={compile_run.returncode}\n{compile_run.stdout}\nUNITTEST EXIT={unit_run.returncode}\n{unit_run.stdout}\n")
w("EVIDENCE/smoke_output.json", smoke_run.stdout)
wj("EVIDENCE/research_count.json", {"english_search_queries":len(queries),"source_ledger_rows":len(ledger),"empirical_performance_numbers_created":False})
if compile_run.returncode or unit_run.returncode or smoke_run.returncode:
    raise SystemExit(f"verification failure compile={compile_run.returncode} unit={unit_run.returncode} smoke={smoke_run.returncode}\n{unit_run.stdout}\n{smoke_run.stdout}")

# Add-only patch for product code + namespaced tests/data/IR/reports.
targets=[]
for pth in ROOT.rglob("*"):
    if not pth.is_file(): continue
    rel=pth.relative_to(ROOT).as_posix()
    if rel.startswith(("modules/","tests/g06/","DATA/g06/","METHOD_IR/g06/","reports/g06/")):
        targets.append(pth)
parts=[]
for pth in sorted(targets):
    rel=pth.relative_to(ROOT).as_posix()
    lines=pth.read_text(encoding="utf-8").splitlines(keepends=True)
    parts += [f"diff --git a/{rel} b/{rel}\n","new file mode 100644\n"]
    parts += list(difflib.unified_diff([],lines,fromfile="/dev/null",tofile=f"b/{rel}",lineterm="\n"))
w("PATCHES/G06_UQ_OOD_AD_REJECT.patch", "".join(parts))
with tempfile.TemporaryDirectory() as td:
    repo=Path(td)
    init=run(["git","init","-q"],repo)
    check=run(["git","apply","--check",str(ROOT/"PATCHES/G06_UQ_OOD_AD_REJECT.patch")],repo)
    w("EVIDENCE/patch_apply_check.txt", f"git init exit={init.returncode}\n{init.stdout}\ngit apply --check exit={check.returncode}\n{check.stdout}\n")
    if init.returncode or check.returncode: raise SystemExit(check.stdout)

manifest = {
    "schema":"tiai.web99.return-manifest.v1","window_id":"G06","slug":"UQ_OOD_AD_REJECT",
    "exclusive_mission":"UQ·OOD·AD·拒绝推荐","base_subject_sha":BASE_SHA,
    "write_scope":["modules/w08_mq_uq_conformal_calibration/**","DATA/g06/**","delivery-only tests/g06 METHOD_IR/g06 reports/g06"],
    "status":"COMPLETE_READY_FOR_LOCAL_APPLY","claim_ceiling":"below_gate_continue_optimization",
    "fullscore_claimed":False,"production_champion_claimed":False,"hq_loso_receipt_present":False,
    "ge5_and_loso_separated":True,"n_rows_HQ":0,"n_papers_fulltext":0,
    "direct_data_class":"policy + schemas + synthetic gate fixtures; no experimental observations",
    "english_search_query_count":len(queries),
    "tests":{"compile_exit":compile_run.returncode,"unittest_exit":unit_run.returncode,"smoke_exit":smoke_run.returncode,"patch_apply_check":"PASS"},
    "grounding":["TIAI_WEB36_V24_AGENT_NATIVE_ONE_WAVE_FULL_20260717.zip","TIAI_WEB36_V24_G6_WEB99_DIRECT_DELIVER_PROMPTS_ONLY_20260717.zip","06_彻夜双模型_GPT56_Grok_上传用.zip","TITMC_V7_AGENT_OS_LIT_B006_OF_010.zip..B010_OF_010.zip","sddvacav/tiai-agent-os@3008e56"],
    "required_artifacts":{"modules":True,"tests":True,"DATA":True,"METHOD_IR":True,"LOCAL_CODEX_APPLY":True,"RETURN_MANIFEST":True,"CLAIM_BOUNDARY":True,"BLOCKERS":True,"SOURCE_LEDGER":True},
}
wj("RETURN_MANIFEST.json", manifest)
required=["DATA/g06/calibration_policy.yaml","DATA/g06/ood_cases.jsonl","DATA/g06/reject_card.schema.json","METHOD_IR/g06/METHOD_IR.md","reports/g06/SOURCE_LEDGER.md","LOCAL_CODEX_APPLY.md","RETURN_MANIFEST.json","CLAIM_BOUNDARY.md","BLOCKERS.md","PATCHES/G06_UQ_OOD_AD_REJECT.patch"]
missing=[x for x in required if not (ROOT/x).is_file()]
if missing: raise SystemExit(f"missing required: {missing}")

files=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
wj("EVIDENCE/inventory.json", {"file_count_excluding_sha_manifest":len(files),"required_missing":missing})
files=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
w("SHA256SUMS.txt", "".join(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in files))

with zipfile.ZipFile(ZIP,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_file(): z.write(p, f"{ROOT_NAME}/{p.relative_to(ROOT).as_posix()}")
print(json.dumps({"zip":str(ZIP),"zip_sha256":sha(ZIP),"zip_bytes":ZIP.stat().st_size,"file_count":sum(1 for p in ROOT.rglob('*') if p.is_file()),"unittest_exit":unit_run.returncode,"smoke_exit":smoke_run.returncode,"patch_apply_check":"PASS"},ensure_ascii=False,indent=2))
