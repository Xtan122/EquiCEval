"""Tests for the tier-2 meta-evaluation pieces: reference-form baseline and
the meta-analysis helpers in experiments/evaluate_equiceval.py."""
import pytest

from src.benchmark.reference_form_baseline import ReferenceFormBaseline
from src.benchmark.verified_evaluation import demo_records
from src.equiceval.canonical_ir import (
    CanonicalConstraint,
    CanonicalIR,
    CanonicalVariable,
)
from experiments.run_verified_evaluation import run
from experiments.evaluate_equiceval import (
    analyze,
    anomaly_score,
    baseline_verdict,
    score_baselines,
    stratified_limit,
)


def _ir(problem, variables, constraint_var, sense="<=", constant=-1.0):
    return CanonicalIR(
        problem,
        {v: CanonicalVariable(v, "binary", 0.0, 1.0) for v in variables},
        [CanonicalConstraint("c", {constraint_var: 1.0}, constant, sense)],
        "minimize",
        {variables[0]: 1.0},
    )


def test_refform_baseline_rejects_renamed_variables():
    ref = _ir("Ref", ["x_1"], "x_1")
    cand = _ir("Cand", ["x1"], "x1")
    assert ReferenceFormBaseline("refform").evaluate(ref, cand)["score"] > 0
    assert ReferenceFormBaseline("strong").evaluate(ref, cand)["score"] == pytest.approx(0.0)


def test_baseline_strong_scores_equivalent_pair_zero():
    ref = _ir("Ref", ["x1"], "x1")
    cand = _ir("Cand", ["x1"], "x1")
    for mode in ("refform", "strong"):
        assert ReferenceFormBaseline(mode).evaluate(ref, cand)["score"] == pytest.approx(0.0)


def test_baseline_flags_rescaled_matched_rows_via_cons_rmse():
    """The original paper's Cons-RMSE must participate in the fault decision.

    ``x <= 1`` and ``0.1x <= 0.1`` define the same feasible set, but the raw
    constraint functions differ, so the scale-sensitive Cons-RMSE term has to
    fire even when the normalized (``strong``) rows match.
    """
    ref = CanonicalIR(
        "Ref", {"x": CanonicalVariable("x", "continuous", 0.0, 1.0)},
        [CanonicalConstraint("c", {"x": 1.0}, -1.0, "<=")], "minimize", {"x": 1.0})
    cand = CanonicalIR(
        "Cand", {"x": CanonicalVariable("x", "continuous", 0.0, 1.0)},
        [CanonicalConstraint("c", {"x": 0.1}, -0.1, "<=")], "minimize", {"x": 0.1})
    details = ReferenceFormBaseline("strong").evaluate(ref, cand)
    assert details["cons_rmse_exceeds"] is True
    assert details["score"] > 0.0


def test_anomaly_score_prefers_fault_signal():
    certified = {"Delta_right": 0.0, "Delta_left": 0.0, "Delta_f": 0.0, "MatchCoverage": 1.0}
    mutant = {"Delta_right": 0.5, "Delta_left": 0.0, "Delta_f": 0.0, "MatchCoverage": 0.5}
    assert anomaly_score(certified) == pytest.approx(0.0)
    assert anomaly_score(mutant) == pytest.approx(0.5)
    assert anomaly_score({"MatchCoverage": 0.25}) == pytest.approx(0.75)
    assert anomaly_score({}) == pytest.approx(0.0)


def test_baseline_verdict_threshold():
    assert baseline_verdict(0.0) == "certified"
    assert baseline_verdict(1e-6) == "disproved"


def test_stratified_limit_keeps_ratio():
    records = (
        [{"record_id": f"eq{i}", "is_semantically_equivalent": True} for i in range(10)]
        + [{"record_id": f"mut{i}", "is_semantically_equivalent": False} for i in range(10)]
    )
    subset = stratified_limit(records, 6)
    assert len(subset) == 6
    assert sum(r["is_semantically_equivalent"] for r in subset) == 3


def test_meta_analysis_end_to_end_on_demo():
    records = demo_records()
    report = run(records, [1.0], "feasible_set", ["certificates"])
    scores = score_baselines(records)
    dataset = {
        r["record_id"]: {"baseline_scores": scores[r["record_id"]], "candidate_size": 0}
        for r in records
    }
    configs = analyze(report, dataset, ("refform", "strong"))
    assert "certificates@1.0s" in configs
    analysis = configs["certificates@1.0s"]
    assert analysis["equiceval"]["exact"]["verdict_counts"]
    assert set(analysis["baselines"]) == {"refform", "strong"}


def _ra_record(problems, record_id="ra_1"):
    """Small record with a ``base_problem_name`` in the GroundTruth registry."""
    ref = _ir("Ref", ["x_1"], "x_1")
    cand = _ir("Cand", ["x_1"], "x_1")
    return {
        "record_id": record_id,
        "base_problem_name": problems,
        "is_semantically_equivalent": True,
        "reference_ir": _ir_to_dict(ref),
        "candidate_ir": _ir_to_dict(cand),
    }


def _ir_to_dict(ir):
    from src.benchmark.verified_evaluation import ir_to_dict
    return ir_to_dict(ir)


def test_score_baselines_refform_impl_only_reference_form():
    records = [_ra_record("Knapsack")]
    out = score_baselines(records, ("refform", "strong"))
    assert set(out["ra_1"]) == {"refform", "strong"}
