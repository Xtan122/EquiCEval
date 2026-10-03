"""Meta-evaluation of EquiCEval itself (upgrade paper tier 2, §6/§7/§8).

Evaluates the evaluator: independent labels from the exhaustive oracle in
``src/benchmark/verified_evaluation``, EquiCEval verdicts from the verified
pipeline, and reference-form baselines. Produces FPR / recall / AUROC-AUPRC /
unresolved / cost with clustered-bootstrap intervals, plus the mode ablation.

Run from the repository root (PYTHONPATH=. is set by cli.py, or pass it):

    PYTHONPATH=. .venv/bin/python -m experiments.evaluate_equiceval \
        --dataset data/equiceval_pilot_benchmark.json \
        --output output/meta_eval_pilot.json

Nothing is overwritten: ``--output`` must be a new path.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from experiments.run_verified_evaluation import run
from src.benchmark.analysis import (
    RobustStatsCalculator,
    bonferroni_level,
    compute_auroc_auprc,
    compute_localization_accuracy,
    cost_profiling_by_size,
    leave_one_family_out_metrics,
    paired_difference_ci,
)
from src.benchmark.independent_oracle import independent_label
from src.benchmark.baselines import build_baselines
from src.benchmark.splits import family_split, split_summary
from src.benchmark.witness_metrics import witness_metrics
from src.benchmark.verified_evaluation import ir_from_dict
from src.equiceval.contracts import PRIMARY_EQUIVAFORMULATION_CONTRACT, SUPPORTED_CONTRACTS
from src.equiceval.metrics import verification_metrics

BASELINE_MODES = ("refform", "strong")
# ``refform_strong`` (``reference_form_baseline.py``) is the canonicalized rewrite
# that reports a binary verdict. The faithful Refai--Ahmed component-metric
# baseline (``ra_original``) is compared against the engine in the separate
# ``equiceval-llm-eval`` experiment repo, not here.
_FAULT_TOL = 1e-9
# Non-decisive verdicts carry no positive/negative decision; scoring them as
# "not faulty" (0) is exactly what paper §8.2 forbids. They are excluded from
# AUROC/AUPRC instead.
_DECISIVE_VERDICTS = frozenset({"certified", "within_tolerance", "disproved", "within_scope"})


# ─────────────────────────────────────────────────────────────────────────────
# Dataset helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_dataset(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text())
    if isinstance(raw, list):
        return raw
    return (raw.get("equivalent_records", []) + raw.get("mutant_records", [])
            + raw.get("natural_records", []))


def stratified_limit(records: List[Dict[str, Any]], limit: int, seed: int = 42) -> List[Dict[str, Any]]:
    """Keep the equivalent/mutant ratio when evaluating a subset."""
    if not limit or limit >= len(records):
        return records
    eq = [r for r in records if r.get("is_semantically_equivalent")]
    mut = [r for r in records if not r.get("is_semantically_equivalent")]
    n_eq = min(len(eq), max(1, limit // 2))
    n_mut = min(len(mut), limit - n_eq)
    rng = np.random.RandomState(seed)
    pick = lambda seq, n: [seq[i] for i in rng.permutation(len(seq))[:n]]
    return pick(eq, n_eq) + pick(mut, n_mut)


def _ir_size(candidate_ir: Dict[str, Any]) -> int:
    return len(candidate_ir.get("variables", {})) + len(candidate_ir.get("constraints", []))


# ─────────────────────────────────────────────────────────────────────────────
# EquiCEval anomaly score + metric adapters
# ─────────────────────────────────────────────────────────────────────────────

def anomaly_score(diagnostic: Dict[str, Any]) -> float:
    """Continuous ``higher = more likely faulty`` score for AUROC/AUPRC.

    Maximum of the directed feasibility/objective discrepancy values and the
    missing certified row coverage. Purely descriptive: the discrete
    ``verdict`` stays the source of truth for the paper metrics.
    """
    def finite(value) -> Optional[float]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value) if math.isfinite(value) else None

    values = [finite(diagnostic.get(k)) for k in ("Delta_right", "Delta_left", "Delta_f")]
    values = [v for v in values if v is not None]
    coverage = finite(diagnostic.get("MatchCoverage"))
    terms = [max(values)] if values else []
    if coverage is not None:
        terms.append(max(0.0, 1.0 - coverage))
    return float(max(terms)) if terms else 0.0


def baseline_verdict(score: float) -> str:
    return "disproved" if score > _FAULT_TOL else "certified"


def _baseline_disproved(row: Dict[str, Any], mode: str) -> bool:
    entry = row["baseline_scores"][mode]
    verdict = entry.get("verdict") if isinstance(entry, dict) else None
    if verdict is None:
        verdict = baseline_verdict(entry["score"])
    return verdict == "disproved"


def _rate_value(metric: Dict[str, Any]) -> Optional[float]:
    return metric.get("value") if isinstance(metric, dict) else metric


# ─────────────────────────────────────────────────────────────────────────────
# Baseline pass
# ─────────────────────────────────────────────────────────────────────────────

def score_baselines(
    records: List[Dict[str, Any]],
    modes: Tuple[str, ...] = BASELINE_MODES,
) -> Dict[str, Dict[str, Any]]:
    """Score the canonicalized reference-form baselines (refform/strong)."""
    out: Dict[str, Dict[str, Any]] = {r["record_id"]: {} for r in records}
    wanted = tuple(m for m in modes if m in BASELINE_MODES)
    if wanted:
        evaluated = build_baselines(wanted)
        for record in records:
            ref = ir_from_dict(record["reference_ir"])
            cand = ir_from_dict(record["candidate_ir"])
            out.setdefault(record["record_id"], {}).update({
                mode: {"score": result.score, "verdict": result.verdict,
                       "details": result.details}
                for mode in wanted
                for result in [evaluated[mode].evaluate(ref, cand)]
            })
    # EquivaMap/quasi-Karp reference criterion (paper §9.1-9.2): the published
    # label is the baseline decision, scored here against the contract label.
    if any(r.get("published_label") is not None for r in records):
        for rid, entry in score_published_quasi_karp(records).items():
            out.setdefault(rid, {}).update(entry)
    return out


def score_published_quasi_karp(
    records: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """EquivaMap/quasi-Karp baseline from the dataset's ``published_label``."""
    out: Dict[str, Dict[str, Any]] = {}
    for record in records:
        published = record.get("published_label")
        if published is None:
            out[record["record_id"]] = {"quasi_karp": {
                "score": 0.0, "verdict": "unsupported",
                "details": {"note": "record has no published_label"}}}
        else:
            out[record["record_id"]] = {"quasi_karp": {
                "score": 0.0 if published else 1.0,
                "verdict": "certified" if published else "disproved",
                "details": {"published_label": bool(published),
                            "criterion": "quasi-Karp (EquivaMap)"}}}
    return out


def apply_mapping_policy(records: List[Dict[str, Any]], policy: str) -> None:
    """Make EquiCEval and baselines see the same pair (paper §9.1 D1).

    ``provided`` keeps the published variable mapping; ``discover`` withholds it
    so M1 must find the correspondence itself. Both the evaluator and the
    baselines read ``reference_ir``/``candidate_ir``/``provided_substitutions``,
    so resetting those fields here applies the condition uniformly. The raw IRs
    are retained on every record, so the mapping condition is an input to the
    run, never a property baked irreversibly into the dataset.
    """
    if policy != "discover":
        return
    for record in records:
        raw_ref = record.get("raw_reference_ir")
        raw_cand = record.get("raw_candidate_ir")
        if raw_ref is not None and raw_cand is not None:
            record["reference_ir"] = raw_ref
            record["candidate_ir"] = raw_cand
        record["provided_substitutions"] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Meta analysis
# ─────────────────────────────────────────────────────────────────────────────

def _labeled(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in rows if r["label"] is not None]


def _cluster_ci(rows: List[Dict[str, Any]], indicator) -> Optional[List[float]]:
    if not rows:
        return None
    values = [float(indicator(r)) for r in rows]
    clusters = [r["family"] or "unknown" for r in rows]
    if len(set(clusters)) < 2:
        return None
    low, high = RobustStatsCalculator.clustered_bootstrap_ci(values, clusters)
    return [low, high]


def _auroc(rows: List[Dict[str, Any]], score_key,
           exclude=None) -> Tuple[Optional[float], Optional[float], int]:
    labeled = _labeled(rows)
    eligible = [r for r in labeled if exclude is None or not exclude(r)]
    y_true = [0 if r["label"] else 1 for r in eligible]
    y_score = [score_key(r) for r in eligible]
    if len(set(y_true)) < 2:
        return None, None, len(eligible)
    auroc, auprc = compute_auroc_auprc(y_true, y_score)
    return ((None if math.isnan(auroc) else auroc),
            (None if math.isnan(auprc) else auprc), len(eligible))


def _config_analysis(
    rows: List[Dict[str, Any]],
    baseline_modes: Tuple[str, ...],
) -> Dict[str, Any]:
    labels = [r["label"] for r in rows]
    verdicts = [r["diagnostic"]["verdict"] for r in rows]
    exact = verification_metrics(labels, verdicts)
    numerical = verification_metrics(labels, verdicts, accept_numerical=True)

    eq_rows = [r for r in _labeled(rows) if r["label"] is True]
    mut_rows = [r for r in _labeled(rows) if r["label"] is False]
    auroc, auprc, auroc_n = _auroc(
        rows, lambda r: r["anomaly_score"],
        exclude=lambda r: r["diagnostic"]["verdict"] not in _DECISIVE_VERDICTS)
    localization = [r["localization"] for r in rows if r.get("localization")]
    localization_top1 = (
        compute_localization_accuracy(
            [x["true"] for x in localization], [x["predicted"] for x in localization])
        if localization else None
    )

    solver_calls = [
        (r["diagnostic"].get("budget") or {}).get("solver_calls", 0) for r in rows
    ]
    elapsed = [
        (r["diagnostic"].get("budget") or {}).get("elapsed_seconds", 0.0) for r in rows
    ]

    analysis: Dict[str, Any] = {
        "n_records": len(rows),
        "n_labeled": len(_labeled(rows)),
        "n_unverified_labels": sum(label is None for label in labels),
        "equiceval": {
            "exact": exact,
            "numerical": numerical,
            "auroc": auroc,
            "auprc": auprc,
            "auroc_n": auroc_n,
            "localization_top1": {"value": localization_top1, "n": len(localization)},
            "false_alarm_ci": _cluster_ci(
                eq_rows, lambda r: r["diagnostic"]["verdict"] == "disproved"),
            "error_recall_ci": _cluster_ci(
                mut_rows, lambda r: r["diagnostic"]["verdict"] == "disproved"),
            "false_acceptance_ci": _cluster_ci(
                mut_rows, lambda r: r["diagnostic"]["verdict"] == "certified"),
            "mean_solver_calls": float(np.mean(solver_calls)) if solver_calls else 0.0,
            "total_solver_calls": int(sum(solver_calls)),
            "mean_elapsed_s": float(np.mean(elapsed)) if elapsed else 0.0,
            "witness": witness_metrics(rows),
            "cost_by_size": cost_profiling_by_size([
                {"size": r.get("candidate_size", 0) or 0,
                 "solver_calls": (r["diagnostic"].get("budget") or {}).get("solver_calls", 0)}
                for r in rows
            ]),
            "leave_one_family_out": leave_one_family_out_metrics(
                [r["label"] for r in rows],
                [r["diagnostic"]["verdict"] for r in rows],
                [r["family"] or "unknown" for r in rows],
            ),
        },
        "baselines": {},
        "paired_diff": {},
    }

    def _eq_flag(r):
        return 1.0 if r["diagnostic"]["verdict"] == "disproved" else 0.0

    for mode in baseline_modes:
        def _base_flag(r, m=mode):
            return 1.0 if _baseline_disproved(r, m) else 0.0

        analysis["paired_diff"][mode] = {}
        adj_level = bonferroni_level(2 * len(baseline_modes))
        for name, subset in (("false_alarm_rate", eq_rows), ("error_recall", mut_rows)):
            if not subset:
                analysis["paired_diff"][mode][name] = None
                continue
            values_a = [_eq_flag(r) for r in subset]
            values_b = [_base_flag(r) for r in subset]
            clusters = [r["family"] or "unknown" for r in subset]
            base = paired_difference_ci(values_a, values_b, clusters)
            adjusted = paired_difference_ci(values_a, values_b, clusters, ci_level=adj_level)
            analysis["paired_diff"][mode][name] = {
                **base,
                "adjusted_ci_lower": adjusted["ci_lower"],
                "adjusted_ci_upper": adjusted["ci_upper"],
                "adjusted_ci_level": adj_level,
            }

    for mode in baseline_modes:
        scores = [r["baseline_scores"][mode]["score"] for r in rows]
        b_verdicts = [
            r["baseline_scores"][mode].get("verdict")
            or baseline_verdict(r["baseline_scores"][mode]["score"])
            for r in rows
        ]
        b_labels = [r["label"] for r in rows]
        b_exact = verification_metrics(b_labels, b_verdicts)
        b_auroc, b_auprc, b_auroc_n = _auroc(
            rows, lambda r, m=mode: r["baseline_scores"][m]["score"])
        b_eq = [r for r in _labeled(rows) if r["label"] is True]
        b_mut = [r for r in _labeled(rows) if r["label"] is False]
        analysis["baselines"][mode] = {
            "false_alarm_rate": _rate_value(b_exact["false_alarm_rate"]),
            "error_recall": _rate_value(b_exact["error_recall"]),
            "false_acceptance_rate": _rate_value(b_exact["false_acceptance_rate"]),
            "equivalent_confirmation_rate": _rate_value(b_exact["equivalent_confirmation_rate"]),
            "auroc": b_auroc,
            "auprc": b_auprc,
            "false_alarm_ci": _cluster_ci(
                b_eq, lambda r, m=mode: _baseline_disproved(r, m)),
            "error_recall_ci": _cluster_ci(
                b_mut, lambda r, m=mode: _baseline_disproved(r, m)),
            "mean_score": float(np.mean(scores)) if scores else 0.0,
        }
    return analysis


def analyze(report: Dict[str, Any], dataset: Dict[str, Dict[str, Any]],
            baseline_modes: Tuple[str, ...]) -> Dict[str, Any]:
    configs: Dict[str, Any] = {}
    for row in report["results"]:
        row["dataset_label"] = dataset.get(row["record_id"], {}).get("dataset_label")
        row["mutation_label"] = dataset.get(row["record_id"], {}).get("mutation_label")
        row["transformation_label"] = dataset.get(row["record_id"], {}).get("transformation_label")
        row["candidate_size"] = dataset.get(row["record_id"], {}).get("candidate_size", 0)
        row["anomaly_score"] = anomaly_score(row.get("diagnostic", {}))
        row["baseline_scores"] = dataset.get(row["record_id"], {}).get("baseline_scores", {})

    keys = sorted({(r["seconds"], r["mode"]) for r in report["results"]})
    # Analyse every baseline actually present in the rows, not just the CLI
    # request: ``ra_original`` is scored alongside the requested modes.
    present_modes = sorted({
        mode for row in report["results"]
        for mode in (row.get("baseline_scores") or {})
    })
    analysed_modes = tuple(m for m in ("quasi_karp", *baseline_modes)
                          if m in present_modes)
    for seconds, mode in keys:
        rows = [r for r in report["results"] if r["seconds"] == seconds and r["mode"] == mode]
        configs[f"{mode}@{seconds}s"] = _config_analysis(rows, analysed_modes)
    return configs


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(value: Optional[float], digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _fmt_ci(ci: Optional[List[float]], digits: int = 3) -> str:
    return "n/a" if not ci else f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]"


def build_markdown(dataset_path: Path, report: Dict[str, Any],
                   configs: Dict[str, Any], baseline_modes: Tuple[str, ...]) -> str:
    cfg = report["config"]
    lines = [
        "# Meta-evaluation của EquiCEval (tầng 2)",
        "",
        f"- Dataset: `{dataset_path}`",
        f"- Diagnostic schema: `{cfg['diagnostic_schema']}` | contract: `{cfg['contract']}`",
        f"- Budgets: {cfg['budgets']} | modes: {cfg['modes']}",
        f"- Split: test families = {cfg.get('test_families') or 'none'} | {cfg.get('split_summary')}",
        "- Nhãn độc lập: `benchmark.independent_oracle` (enumeration nguyên, khớp hoán vị đổi tên, kiểm chứa LP).",
        "- Nhãn `None` = không xác minh được độc lập (đổi tên > 8 biến / không bị chặn) — giữ nguyên, không ép nhãn.",
        "",
        "## EquiCEval theo mode (ablation)",
        "",
        "| Cấu hình | n labeled | FPR | FPR 95% CI | Recall | Recall 95% CI | AUROC | AUPRC | Unresolved | Unsupported | Witness valid | Witness cover | Loc top-1 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, analysis in configs.items():
        eq = analysis["equiceval"]
        exact = eq["exact"]
        wit = eq.get("witness", {})
        loc = eq.get("localization_top1", {})
        lines.append(
            f"| {key} | {analysis['n_labeled']} | "
            f"{_fmt(_rate_value(exact['false_alarm_rate']))} | {_fmt_ci(eq['false_alarm_ci'])} | "
            f"{_fmt(_rate_value(exact['error_recall']))} | {_fmt_ci(eq['error_recall_ci'])} | "
            f"{_fmt(eq['auroc'])} | {_fmt(eq['auprc'])} | "
            f"{_fmt(_rate_value(exact['unresolved_rate']))} | {_fmt(_rate_value(exact['unsupported_rate']))} | "
            f"{_fmt(wit.get('validity_rate', {}).get('value'))} | {_fmt(wit.get('coverage', {}).get('value'))} | "
            f"{_fmt(loc.get('value'))} |"
        )

    lines += [
        "",
        "## Baseline reference-form (paper gốc)",
        "",
        "| Cấu hình | baseline | FPR | Recall | AUROC | AUPRC |",
        "|---|---|---|---|---|---|",
    ]
    for key, analysis in configs.items():
        for mode in sorted(analysis.get("baselines", {})):
            b = analysis["baselines"][mode]
            lines.append(
                f"| {key} | {mode} | {_fmt(b['false_alarm_rate'])} | "
                f"{_fmt(b['error_recall'])} | {_fmt(b['auroc'])} | {_fmt(b['auprc'])} |"
            )

    lines += [
        "",
        "## Chênh lệch ghép cặp (EquiCEval − baseline, clustered bootstrap)",
        "",
        "| Cấu hình | baseline | Δ FPR | Δ FPR 95% CI | Δ FPR adj. CI | Δ Recall | Δ Recall 95% CI | Δ Recall adj. CI |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, analysis in configs.items():
        for mode in sorted(analysis.get("paired_diff", {})):
            pd = (analysis.get("paired_diff") or {}).get(mode) or {}
            fpr = pd.get("false_alarm_rate")
            rec = pd.get("error_recall")

            def _ci(entry, lo, hi):
                if not entry or entry.get(lo) is None:
                    return None
                return [entry[lo], entry[hi]]

            lines.append(
                f"| {key} | {mode} | "
                f"{_fmt(fpr['observed']) if fpr else 'n/a'} | "
                f"{_fmt_ci(_ci(fpr, 'ci_lower', 'ci_upper'))} | "
                f"{_fmt_ci(_ci(fpr, 'adjusted_ci_lower', 'adjusted_ci_upper'))} | "
                f"{_fmt(rec['observed']) if rec else 'n/a'} | "
                f"{_fmt_ci(_ci(rec, 'ci_lower', 'ci_upper'))} | "
                f"{_fmt_ci(_ci(rec, 'adjusted_ci_lower', 'adjusted_ci_upper'))} |"
            )

    lines += [
        "",
        "## Chi phí",
        "",
        "| Cấu hình | solver calls / record | total solver calls | elapsed / record (s) |",
        "|---|---|---|---|",
    ]
    for key, analysis in configs.items():
        eq = analysis["equiceval"]
        lines.append(
            f"| {key} | {_fmt(eq['mean_solver_calls'], 2)} | {eq['total_solver_calls']} | "
            f"{_fmt(eq['mean_elapsed_s'])} |"
        )
    lines += [
        "",
        "## Chi phí theo kích thước bài (solver calls / record)",
        "",
        "| Cấu hình | 10 | 50 | 100 | 500 |",
        "|---|---|---|---|---|",
    ]
    for key, analysis in configs.items():
        cbs = (analysis["equiceval"].get("cost_by_size") or {})
        cells = []
        for bucket in ("10", "50", "100", "500"):
            entry = cbs.get(bucket) or {}
            cells.append(_fmt(entry.get("mean_calls"), 2) if entry.get("n") else "n/a")
        lines.append(f"| {key} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Bỏ từng họ bài toán (leave-one-family-out)",
        "",
        "| Cấu hình | họ bỏ | n | FPR | Recall |",
        "|---|---|---|---|---|",
    ]
    for key, analysis in configs.items():
        loo = (analysis["equiceval"].get("leave_one_family_out") or {})
        for family, entry in loo.items():
            lines.append(
                f"| {key} | {family} | {entry['n']} | "
                f"{_fmt(entry['false_alarm_rate'])} | {_fmt(entry['error_recall'])} |"
            )

    lines += [
        "",
        "## Diễn giải",
        "",
        "- FPR = tỉ lệ cặp tương đương (nhãn độc lập) bị EquiCEval kết luận `disproved`.",
        "- Recall = tỉ lệ cặp sai bị `disproved`; `unresolved`/`unsupported` vẫn nằm trong mẫu số.",
        "- AUROC/AUPRC dùng điểm bất thường liên tục mô tả (`Delta_right`, `Delta_left`, `Delta_f`,",
        "  `1 - MatchCoverage`), không thay thế verdict.",
        "- CI là clustered bootstrap theo họ bài toán; `n/a` khi chỉ có <2 họ trong mẫu con.",
        "",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, default=Path("data/equiceval_full_benchmark.json"))
    parser.add_argument("--output", type=Path, required=True,
                        help="A new JSON file; existing files are never overwritten")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path")
    parser.add_argument("--budgets", nargs="+", type=float, default=[1.0, 5.0])
    parser.add_argument("--modes", nargs="+",
                        choices=["direct_only", "certificates", "early_stop"],
                        default=["direct_only", "certificates", "early_stop"])
    parser.add_argument("--contract", choices=SUPPORTED_CONTRACTS,
                        default=PRIMARY_EQUIVAFORMULATION_CONTRACT)
    parser.add_argument("--baselines", nargs="+",
                        choices=[*BASELINE_MODES, "none"],
                        default=list(BASELINE_MODES),
                        help="Baselines to score; 'none' runs EquiCEval only (mode B)")
    parser.add_argument("--equiceval-only", action="store_true",
                        help="Mode B: score EquiCEval alone on the labelled dataset "
                             "(equivalent to --baselines none)")
    parser.add_argument("--use-record-labels", action="store_true",
                        help="Trust per-record is_semantically_equivalent as the verified "
                             "label instead of re-deriving it with independent_label. "
                             "Required for pre-relabelled datasets (e.g. EquivaFormulation) "
                             "whose labels are pinned in the dataset file.")
    parser.add_argument("--mapping", choices=["provided", "discover"], default="provided",
                        help="Paper §9.1 (D1): 'provided' gives the published variable "
                             "mapping (default); 'discover' withholds it so M1 must find "
                             "the correspondence. The same condition is applied to the "
                             "baselines, so the comparison is a fair pipeline comparison.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stratified subset size (0 = toàn bộ dataset)")
    parser.add_argument("--safety-box", type=float, default=None,
                        help="Hộp B hữu hạn (§M0) cho miền không bị chặn: EquiCEval "
                             "chỉ truy vấn trong [-B, B]. Mặc định None = whole-instance.")
    parser.add_argument("--no-context-matching", action="store_true")
    parser.add_argument("--group-matching", action="store_true")
    parser.add_argument("--max-context-pairs", type=int, default=32)
    parser.add_argument("--max-group-trials", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-families", nargs="*", default=[],
                        help="Problem families held out for the final test split")
    args = parser.parse_args()

    if args.output.exists():
        parser.error("Output already exists; choose a new path to preserve earlier measurements")
    if not args.dataset.exists():
        parser.error(f"Dataset not found: {args.dataset}")
    if args.limit < 0:
        parser.error("--limit must be nonnegative")

    raw_payload = json.loads(args.dataset.read_text())
    if isinstance(raw_payload, dict):
        dataset_contract = raw_payload.get("contract")
        if dataset_contract is not None and dataset_contract != args.contract:
            parser.error(
                "dataset.contract không khớp --contract: "
                f"{dataset_contract!r} != {args.contract!r} (nhãn theo contract khác, "
                "không được trộn bảng — paper §9.1 D3)")
        if dataset_contract is not None and raw_payload.get("label_source") \
                and not args.use_record_labels:
            parser.error(
                "dataset chứa nhãn đã đóng băng theo contract; thêm --use-record-labels "
                "thay vì suy lại nhãn bằng independent_label")

    records = stratified_limit(load_dataset(args.dataset), args.limit, args.seed)
    apply_mapping_policy(records, args.mapping)
    split = family_split(records, args.test_families)
    baseline_modes = () if args.equiceval_only else tuple(m for m in args.baselines if m != "none")
    print(f"[meta] {len(records)} records from {args.dataset} "
          f"(budgets={args.budgets}, modes={args.modes}, mapping={args.mapping})")

    started = time.time()
    report = run(records, args.budgets, args.contract, args.modes,
                 context_matching=not args.no_context_matching,
                 group_matching=args.group_matching,
                 max_context_pairs=args.max_context_pairs,
                 max_group_trials=args.max_group_trials,
                 labeler=independent_label,
                 use_record_labels=args.use_record_labels,
                 safety_box_bound=args.safety_box)
    print(f"[meta] EquiCEval pass done in {time.time() - started:.1f}s; "
          f"scoring {len(baseline_modes)} baseline(s)")

    baseline_scores = (score_baselines(records, baseline_modes)
                       if baseline_modes else {})
    dataset: Dict[str, Dict[str, Any]] = {}
    for record in records:
        dataset[record["record_id"]] = {
            "dataset_label": record.get("is_semantically_equivalent"),
            "mutation_label": record.get("mutation_label"),
            "transformation_label": record.get("transformation_label"),
            "candidate_size": _ir_size(record.get("candidate_ir", {})),
            "split": split.get(record["record_id"]),
            "contamination_stratum": record.get("contamination_stratum"),
            "baseline_scores": baseline_scores.get(record["record_id"], {}),
        }
    for row in report["results"]:
        row.pop("input", None)

    configs = analyze(report, dataset, baseline_modes)
    report["dataset"] = dataset
    report["meta_analysis"] = configs
    report["config"]["mapping_policy"] = args.mapping
    report["config"]["safety_box_bound"] = args.safety_box
    report["config"]["test_families"] = list(args.test_families)
    report["config"]["split_summary"] = split_summary(records, split)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(build_markdown(args.dataset, report, configs, baseline_modes))

    print(f"[meta] saved -> {args.output}")
    for key, analysis in configs.items():
        eq = analysis["equiceval"]
        print(f"  {key:24s} n={analysis['n_labeled']:4d} "
              f"FPR={_fmt(_rate_value(eq['exact']['false_alarm_rate']))} "
              f"recall={_fmt(_rate_value(eq['exact']['error_recall']))} "
              f"AUROC={_fmt(eq['auroc'])} unresolved={_fmt(_rate_value(eq['exact']['unresolved_rate']))}")


if __name__ == "__main__":
    main()
