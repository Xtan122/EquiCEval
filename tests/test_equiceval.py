"""
Unit tests for EquiCEval core framework:
- Canonical IR normalization
- Equivalence-aware matching & mutual implication
- Directed discrepancy queries (Delta_right and Delta_left)
- Full EquiCEval diagnostic vector pipeline
"""

import pytest
from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalConstraint,
    CanonicalVariable,
    build_projection_certificate,
)
from src.equiceval.matching import EquivalenceMatcher, MatchingLabel
from src.equiceval.directed_query import DirectedDiscrepancyEvaluator
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.equiceval.precheck import MapStatus, ModelPreChecker


def build_sample_knapsack_gt_ir() -> CanonicalIR:
    """Ground truth Knapsack IR: 10 x_1 + 20 x_2 + 30 x_3 <= 50"""
    return CanonicalIR(
        problem_name="Knapsack",
        variables={
            "x_1": CanonicalVariable("x_1", "binary", 0.0, 1.0),
            "x_2": CanonicalVariable("x_2", "binary", 0.0, 1.0),
            "x_3": CanonicalVariable("x_3", "binary", 0.0, 1.0),
        },
        constraints=[
            CanonicalConstraint("cap", {"x_1": 10.0, "x_2": 20.0, "x_3": 30.0}, -50.0, "<=")
        ],
        objective_sense="maximize",
        objective_coeffs={"x_1": 60.0, "x_2": 100.0, "x_3": 120.0},
    )


def build_scaled_knapsack_cand_ir() -> CanonicalIR:
    """
    Equivalent Candidate Knapsack IR multiplied by positive scalar 2.0:
    20 x_1 + 40 x_2 + 60 x_3 <= 100
    This is SEMANTICALLY EQUIVALENT. Paper baseline penalized LLaMA for this,
    EquiCEval should recognize it as EQUIVALENT.
    """
    return CanonicalIR(
        problem_name="Knapsack_Scaled",
        variables={
            "x_1": CanonicalVariable("x_1", "binary", 0.0, 1.0),
            "x_2": CanonicalVariable("x_2", "binary", 0.0, 1.0),
            "x_3": CanonicalVariable("x_3", "binary", 0.0, 1.0),
        },
        constraints=[
            CanonicalConstraint("cap_scaled", {"x_1": 20.0, "x_2": 40.0, "x_3": 60.0}, -100.0, "<=")
        ],
        objective_sense="maximize",
        objective_coeffs={"x_1": 60.0, "x_2": 100.0, "x_3": 120.0},
    )


def build_omitted_knapsack_cand_ir() -> CanonicalIR:
    """
    Candidate Knapsack IR with OMITTED capacity constraint (Empty constraint list).
    """
    return CanonicalIR(
        problem_name="Knapsack_Omitted",
        variables={
            "x_1": CanonicalVariable("x_1", "binary", 0.0, 1.0),
            "x_2": CanonicalVariable("x_2", "binary", 0.0, 1.0),
            "x_3": CanonicalVariable("x_3", "binary", 0.0, 1.0),
        },
        constraints=[],
        objective_sense="maximize",
        objective_coeffs={"x_1": 60.0, "x_2": 100.0, "x_3": 120.0},
    )


def test_canonical_ir_normalization():
    gt = build_sample_knapsack_gt_ir()
    cand = build_scaled_knapsack_cand_ir()

    gt_norm = gt.canonicalize()
    cand_norm = cand.canonicalize()

    # The normalized coefficients should match exactly after dividing by L1 norm (60.0)
    c1 = gt_norm.constraints[0]
    c2 = cand_norm.constraints[0]

    assert pytest.approx(c1.coeffs["x_1"], 1e-5) == c2.coeffs["x_1"]
    assert pytest.approx(c1.coeffs["x_2"], 1e-5) == c2.coeffs["x_2"]
    assert pytest.approx(c1.coeffs["x_3"], 1e-5) == c2.coeffs["x_3"]
    assert pytest.approx(c1.constant, 1e-5) == c2.constant


def test_equivalence_matching_scaled_formulation():
    gt = build_sample_knapsack_gt_ir()
    cand = build_scaled_knapsack_cand_ir()

    matcher = EquivalenceMatcher()
    matches = matcher.match_constraints(gt, cand)

    assert len(matches) == 1
    assert matches[0].label in (
        MatchingLabel.NORMALIZED_EQUIVALENT,
        MatchingLabel.EXACT,
        MatchingLabel.CONTEXT_EQUIVALENT,
    )


def test_directed_discrepancy_omission():
    gt = build_sample_knapsack_gt_ir()
    cand_omitted = build_omitted_knapsack_cand_ir()

    evaluator = DirectedDiscrepancyEvaluator()
    delta_right, delta_left = evaluator.evaluate_directed_discrepancies(gt, cand_omitted)

    # Candidate omitted constraint => F(cand) contains x = (1, 1, 1) which violates GT
    # 10(1) + 20(1) + 30(1) = 60 > 50 => Violation = 10 > 0
    assert delta_right.discrepancy_value > 0.0
    assert delta_right.direction == "under_constraining"
    assert "cap" in delta_right.violated_constraints


def test_full_equiceval_pipeline():
    gt = build_sample_knapsack_gt_ir()
    cand_scaled = build_scaled_knapsack_cand_ir()

    evaluator = EquiCEvalEvaluator()
    res = evaluator.evaluate(
        gt_ir=gt,
        cand_ir=cand_scaled,
        gt_optimal_val=220.0,
        cand_optimal_val=220.0,
    )

    vector = res.to_diagnostic_vector()
    assert vector["VarMatch"] == 1.0
    assert vector["ConMatch"] == 1.0
    assert vector["OptimalityGap"] == 0.0
    assert res.con_match_score == 1.0


def test_projection_certificate_detects_requirement_id_renaming():
    ref = CanonicalIR(
        problem_name="Reference",
        variables={
            "x": CanonicalVariable(
                "x",
                "continuous",
                0.0,
                10.0,
                requirement_id="req.decision.x",
            )
        },
        constraints=[CanonicalConstraint("ub", {"x": 1.0}, -5.0, "<=")],
        objective_sense="maximize",
        objective_coeffs={"x": 1.0},
    )
    cand = CanonicalIR(
        problem_name="Candidate",
        variables={
            "renamed_x": CanonicalVariable(
                "renamed_x",
                "continuous",
                0.0,
                10.0,
                requirement_id="req.decision.x",
            )
        },
        constraints=[CanonicalConstraint("ub", {"renamed_x": 1.0}, -5.0, "<=")],
        objective_sense="maximize",
        objective_coeffs={"renamed_x": 1.0},
    )

    cert = build_projection_certificate(ref, cand)

    assert cert.is_verified
    assert cert.variable_map == {"renamed_x": "x"}
    assert cert.is_renaming


def test_precheck_marks_nonlinear_scope_unsupported():
    ref = build_sample_knapsack_gt_ir()
    cand = CanonicalIR(
        problem_name="NonlinearCandidate",
        variables={
            "x_1": CanonicalVariable("x_1", "binary", 0.0, 1.0),
            "x_2": CanonicalVariable("x_2", "binary", 0.0, 1.0),
            "x_3": CanonicalVariable("x_3", "binary", 0.0, 1.0),
        },
        constraints=[],
        objective_sense="maximize",
        objective_coeffs={"x_1": 1.0},
        metadata={"nonlinear": True},
    )

    _, cand_status = ModelPreChecker(solver_time_limit=1.0).run(ref, cand)

    assert cand_status.s_map == MapStatus.UNSUPPORTED
    assert not cand_status.can_run_delta_right
    assert not cand_status.can_run_delta_left


# ─── Module 1: new fields ────────────────────────────────────────────────────

def test_canonical_variable_has_is_auxiliary_and_index_sets():
    """CanonicalVariable must carry is_auxiliary and index_sets (paper §4.2)."""
    prim = CanonicalVariable("x", "continuous", 0.0, 10.0)
    assert prim.is_auxiliary is False
    assert prim.index_sets == []

    aux = CanonicalVariable("s", "continuous", 0.0, 1e6, is_auxiliary=True, index_sets=["i", "j"])
    assert aux.is_auxiliary is True
    assert aux.index_sets == ["i", "j"]


def test_merge_bounds_into_constraints_produces_explicit_bound_constraints():
    """
    A reference with upper_bound=5 and a candidate with an explicit x<=5
    constraint should normalise to the same fingerprint after canonicalize().
    """
    # Reference: bound stored in variable, no explicit constraint
    ref = CanonicalIR(
        problem_name="BoundRef",
        variables={"x": CanonicalVariable("x", "continuous", 0.0, 5.0)},
        constraints=[],
        objective_sense="maximize",
        objective_coeffs={"x": 1.0},
    )
    # Candidate: same bound expressed as explicit inequality
    cand = CanonicalIR(
        problem_name="BoundCand",
        variables={"x": CanonicalVariable("x", "continuous", 0.0, float("inf"))},
        constraints=[
            CanonicalConstraint("ub_x", {"x": 1.0}, -5.0, "<=")
        ],
        objective_sense="maximize",
        objective_coeffs={"x": 1.0},
    )

    ref_norm = ref.canonicalize()   # merge_bounds=True by default
    cand_norm = cand.canonicalize()

    # Both should have exactly one constraint after canonicalization
    ref_c_names  = {c.name for c in ref_norm.constraints}
    cand_c_names = {c.name for c in cand_norm.constraints}
    assert "_ub_x" in ref_c_names or any("ub" in n for n in ref_c_names)
    assert len(ref_norm.constraints) >= 1

    # The upper-bound constraints should have the same normalized coefficients
    ref_ub  = next(c for c in ref_norm.constraints if c.coeffs.get("x", 0) > 0)
    cand_ub = next(c for c in cand_norm.constraints if c.coeffs.get("x", 0) > 0)
    assert pytest.approx(ref_ub.coeffs["x"], abs=1e-6) == cand_ub.coeffs["x"]
    assert pytest.approx(ref_ub.constant,      abs=1e-6) == cand_ub.constant


def test_normalize_flips_geq_to_leq():
    """A '>=' constraint must be normalized to '<=' by flip_to_leq()."""
    from src.equiceval.canonical_ir import CanonicalConstraint
    # x >= 3  →  -x + 3 <= 0  after flip, then normalized: coeffs={x:-1}, const=3
    c = CanonicalConstraint("lb", {"x": 1.0}, -3.0, ">=")
    normed = c.normalize()
    assert normed.sense == "<="
    # Original: x >= 3  → -x <= -3  → after L1 norm (coeff=1): {x:-1}, const=-3... wait
    # flip: {x: -1.0}, constant: 3.0, sense '<='
    # normalize by L1=1: {x:-1}, const=3, sense='<='
    # q=max(||a||_1, |b|)=3, as specified in the revised manuscript.
    assert pytest.approx(normed.coeffs["x"], abs=1e-9) == -1.0 / 3.0
    assert pytest.approx(normed.constant,     abs=1e-9) == 1.0


def test_precheck_timeout_sets_solve_status_timeout():
    """
    When a solver times out (FeasStatus.UNKNOWN), Module 0 must set
    s_solve = SolveStatus.TIMEOUT and should_report_as_inconclusive = True.
    We simulate this by patching check_feasibility directly.
    """
    import unittest.mock as mock
    from src.equiceval.precheck import ModelPreChecker, FeasStatus, SolveStatus

    ref = build_sample_knapsack_gt_ir()
    cand = build_omitted_knapsack_cand_ir()

    checker = ModelPreChecker(solver_time_limit=30.0)

    with mock.patch.object(
        checker, "check_feasibility",
        side_effect=[
            # ref feasibility call → OK
            (FeasStatus.FEASIBLE, [], 0.01),
            # cand feasibility call → TIMEOUT (simulated)
            (FeasStatus.UNKNOWN, [], 30.0),
        ],
    ):
        _, cand_status = checker.run(ref, cand)

    assert cand_status.s_solve == SolveStatus.TIMEOUT
    assert cand_status.should_report_as_inconclusive is True
    assert not cand_status.can_run_delta_right
