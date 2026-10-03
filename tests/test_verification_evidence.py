"""Regression and adversarial checks with independently known answers."""
import json
import math
from dataclasses import replace
from unittest.mock import patch
import pytest

from src.equiceval.canonical_ir import (
    CanonicalIR, CanonicalVariable as V, CanonicalConstraint as C,
    build_projection_certificate,
)
from src.equiceval.directed_query import DirectedDiscrepancyEvaluator
from src.equiceval.contracts import OBJECTIVE_VALUE
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.equiceval.evidence import (
    point_is_feasible, check_implication_certificate, find_implication_certificate,
)
from src.equiceval.matching import EquivalenceMatcher
from src.equiceval.metrics import verification_metrics
from src.equiceval.precheck import ModelPreChecker, BoundStatus
from src.utils.solver_wrapper import QueryBudget, SolverResult, UnifiedSolver


def interval(low=0, high=10, constraints=None, kind="continuous", objective=1):
    return CanonicalIR("interval", {"x": V("x", kind, low, high)},
                       constraints or [], "minimize", {"x": objective})


def test_equality_checks_negative_side():
    source = interval(-1, 0)
    target = interval(-1, 0, [C("zero", {"x": 1}, 0, "==")])
    result = DirectedDiscrepancyEvaluator().evaluate_delta_right(target, source)
    assert result.status == "disproved"
    assert result.lower_bound == 1
    assert point_is_feasible(source, result.variable_assignment)
    assert "zero" in result.violated_constraints


@pytest.mark.parametrize("status", ["Error", "Timeout", "Unbounded"])
def test_solver_failure_never_implies_zero(status):
    with patch.object(UnifiedSolver, "solve_pulp_model",
                      return_value=SolverResult(status, None, {}, 0)):
        result = DirectedDiscrepancyEvaluator().evaluate_delta_right(interval(), interval())
        assert result.status == "unresolved"
        assert math.isnan(result.discrepancy_value)
        assert math.isnan(EquivalenceMatcher().check_implication(interval(), C("c", {"x": 1}, -1, "<=")))


def test_timeout_after_feasibility_preserves_unknown_upper_bound():
    good = SolverResult("Optimal", 0, {"x": 0}, 0, 0, "numerical_optimum")
    timeout = SolverResult("Timeout", None, {}, 0)
    with patch.object(UnifiedSolver, "solve_pulp_model", side_effect=[good, timeout, timeout]):
        result = DirectedDiscrepancyEvaluator(use_certificates=False).evaluate_delta_right(
            interval(0, 1), interval(0, 2))
    assert result.status == "unresolved"
    assert result.upper_bound is None
    assert math.isnan(result.discrepancy_value)


def test_timeout_incumbent_can_be_counterexample_without_being_an_optimum():
    good = SolverResult("Optimal", 0, {"x": 0}, 0, 0, "numerical_optimum")
    timeout = SolverResult("Timeout", 2, {"x": 2}, 0)
    with patch.object(UnifiedSolver, "solve_pulp_model", side_effect=[good, timeout, timeout]):
        result = DirectedDiscrepancyEvaluator(use_certificates=False).evaluate_delta_right(
            interval(0, 1), interval(0, 2))
    assert result.status == "disproved"
    assert result.lower_bound == 1
    assert result.upper_bound is None


def test_normalization_small_scale_and_objective_units():
    a, b = C("a", {"x": 1}, -1, "<="), C("b", {"x": 1e-12}, -1e-12, "<=")
    assert a.normalize().coeffs == b.normalize().coeffs
    assert a.evaluate_residual({"x": 2}) == b.evaluate_residual({"x": 2}) == 1
    assert interval(objective=3).canonicalize().objective_coeffs == {"x": 3}


def test_projection_does_not_hide_missing_bound():
    reference, candidate = interval(0, 8), interval(0, 10)
    cert = build_projection_certificate(reference, candidate)
    assert cert.is_verified
    projected = cert.project_ir(candidate, reference)
    assert point_is_feasible(projected, {"x": 9})
    result = EquiCEvalEvaluator(contract="feasible_set").evaluate(reference, candidate)
    assert result.verdict == "disproved"
    assert result.witness_right.lower_bound == pytest.approx(0.25)


def test_zero_lower_bound_is_checked():
    result = EquiCEvalEvaluator(contract="feasible_set").evaluate(interval(0, 1), interval(-1, 1))
    assert result.verdict == "disproved"
    assert result.witness_right.variable_assignment["x"] < 0


def test_affine_map_preserves_own_bounds_and_objective():
    ref = interval(0, 8)
    candidate = CanonicalIR("scaled", {"z": V("z", "continuous", 0, 20)},
                            [], "minimize", {"z": 0.5})
    result = EquiCEvalEvaluator().evaluate(ref, candidate, provided_substitutions={
        "z": {"coeffs": {"x": 2}, "constant": 0}})
    assert result.verdict == "disproved"  # z<=20 means x<=10, not x<=8.
    assert result.objective_verdict == "certified"


def test_fuzzy_names_and_type_mismatch_are_not_certificates():
    ref = interval()
    cand = CanonicalIR("other", {"x_": V("x_", "continuous", 0, 10)}, [], "minimize", {"x_": 1})
    assert not build_projection_certificate(ref, cand).is_verified
    assert EquiCEvalEvaluator().evaluate(interval(0, 1, kind="binary"), interval(0, 1)).verdict == "unsupported"
    assert DirectedDiscrepancyEvaluator().evaluate_delta_right(
        interval(0, 1, kind="binary"), interval(0, 1)).status == "unsupported"


def test_nonbijective_and_nonlattice_maps_rejected():
    assert not build_projection_certificate(interval(), interval(), {"x": {"coeffs": {"x": 0}}}).is_verified
    assert not build_projection_certificate(interval(kind="integer"), interval(kind="integer"),
                                           {"x": {"coeffs": {"x": 2}}}).is_verified


def test_multirow_certificate_rechecked_and_tampering_rejected():
    source = CanonicalIR("two", {"x": V("x", "continuous", 0, 1),
                                 "y": V("y", "continuous", 0, 2)}, [], "minimize", {})
    target = C("total", {"x": 1, "y": 1}, -3, "<=")
    cert = find_implication_certificate(source, target, QueryBudget(5))
    assert cert is not None
    assert len(cert["support_rows"]) == 2
    assert check_implication_certificate(source, target, cert)
    assert not check_implication_certificate(source, replace(target, constant=-2), cert)
    damaged = dict(cert, weights={cert["support_rows"][0]: "-1"})
    assert not check_implication_certificate(source, target, damaged)


def test_redundant_row_does_not_make_model_faulty():
    ref = interval(0, 8)
    candidate = interval(0, 8, [C("redundant", {"x": 1}, -10, "<=")])
    result = EquiCEvalEvaluator().evaluate(ref, candidate)
    assert result.verdict == "certified"


def test_one_point_reused_across_rows_and_report_is_consistent():
    candidate = interval(0, 10)
    reference = interval(0, 10, [C("a", {"x": 1}, -2, "<="), C("b", {"x": 1}, -3, "<=")])
    result = DirectedDiscrepancyEvaluator(use_certificates=False).evaluate_delta_right(reference, candidate)
    assert {"a", "b"} <= set(result.violated_constraints)
    assert all(reference.constraints[i].evaluate_residual(result.variable_assignment) > 0 for i in (0, 1))
    assert sum(o["status"] == "disproved" for o in result.obligations) >= 2


def test_boundedness_checks_every_direction_not_sum():
    ir = CanonicalIR("line", {"x": V("x", "continuous", -math.inf, math.inf),
                              "y": V("y", "continuous", -math.inf, math.inf)},
                     [C("line", {"x": 1, "y": 1}, 0, "==")], "minimize", {})
    assert ModelPreChecker().check_boundedness(ir)[0] == BoundStatus.DOMAIN_UNBOUNDED


def test_precheck_pass_does_not_certify_model():
    _, status = ModelPreChecker().run(interval(), interval())
    assert status.s_solve.value == "precheck-passed"
    assert not status.is_fully_certified()


def test_shared_budget_includes_precheck_and_objective():
    result = EquiCEvalEvaluator(max_solver_calls=1).evaluate(interval(), interval())
    assert result.budget["solver_calls"] == 1
    assert result.verdict == "unresolved"
    assert result.budget["calls"][0]["phase"] == "precheck"
    zero = EquiCEvalEvaluator(solver_time_limit=0).evaluate(interval(), interval())
    assert zero.verdict == "unresolved"
    assert zero.budget["solver_calls"] == 0


def test_objective_scaling_and_minmax_not_erased():
    result = EquiCEvalEvaluator(contract=OBJECTIVE_VALUE).evaluate(
        interval(objective=1), interval(objective=2))
    assert result.feasibility_verdict == "certified"
    assert result.objective_verdict == "disproved"
    assert result.delta_f == pytest.approx(10)
    flipped = replace(interval(), objective_sense="maximize")
    assert EquiCEvalEvaluator(contract=OBJECTIVE_VALUE).evaluate(
        interval(), flipped).verdict == "disproved"
    assert EquiCEvalEvaluator(contract="feasible_set").evaluate(interval(), flipped).verdict == "certified"


def test_small_objective_difference_uses_declared_reference_scale():
    result = EquiCEvalEvaluator(solver_tolerance=1e-5, contract=OBJECTIVE_VALUE).evaluate(
        interval(0, 1, objective=1), interval(0, 1, objective=1.0000001))
    assert result.objective_verdict == "within_tolerance"
    assert result.delta_f == pytest.approx(1e-7)


def test_disjoint_domains_and_infeasible_candidate():
    result = EquiCEvalEvaluator(contract=OBJECTIVE_VALUE).evaluate(
        interval(0, 1), interval(2, 3))
    assert result.verdict == "disproved"
    assert result.objective_verdict == "not_applicable"
    assert result.objective_evidence.status == "source_infeasible"
    bad = interval(0, 1, [C("impossible", {"x": 1}, -2, ">=")])
    assert EquiCEvalEvaluator(contract=OBJECTIVE_VALUE).evaluate(
        interval(0, 1), bad).verdict == "disproved"


def test_box_only_conclusion_is_not_whole_instance_acceptance():
    result = EquiCEvalEvaluator(contract="feasible_set", safety_box_bound=1).evaluate(
        interval(0, 8), interval(0, 10))
    assert result.verdict == "within_scope"
    assert result.witness_right.scope == "box"


def test_strict_json_and_unknowns_not_magic_numbers():
    result = EquiCEvalEvaluator(solver_time_limit=0).evaluate(interval(), interval())
    data = result.to_diagnostic_vector()
    json.dumps(data, allow_nan=False)
    assert data["Delta_right"] is None
    # Inspect unknown fields, not a substring of arbitrary elapsed-time decimals.
    # A legitimate time such as 0.000714207999 can contain the digits "999".
    assert all(data[key] is None for key in ("Delta_right", "Delta_left", "Delta_f", "OptimalityGap"))


def test_distinguish_abstention_from_false_acceptance():
    labels = [False, False, True, True, None]
    a = verification_metrics(labels, ["disproved", "unresolved", "certified", "disproved", "unsupported"])
    b = verification_metrics(labels, ["disproved", "certified", "certified", "disproved", "unsupported"])
    assert a["error_recall"] == b["error_recall"]
    assert a["false_acceptance_rate"]["value"] == 0
    assert b["false_acceptance_rate"]["value"] == 0.5
    assert a["unverified_labels"] == 1
    assert verification_metrics([], [])["error_recall"]["value"] is None


def test_solver_rejects_unknown_variables_and_senses():
    args = dict(var_specs={"x": ("continuous", 0, 1)}, objective_sense="maximize")
    assert UnifiedSolver.solve_pulp_model(**args, objective_coeffs={"unknown": 1}, constraints_list=[]).status == "Error"
    assert UnifiedSolver.solve_pulp_model(**args, objective_coeffs={}, constraints_list=[({"x": 1}, "!=", 0)]).status == "Error"


def test_binary_extra_bounds_are_preserved():
    result = UnifiedSolver.solve_pulp_model({"x": ("binary", 1, 1)}, {"x": 1}, "minimize", [])
    assert result.objective_value == 1
    assert not point_is_feasible(interval(0, 1, kind="binary"), {"x": 0.5})


def test_affine_roundoff_cannot_create_a_certificate():
    ref = interval(0, 1, objective=0)
    candidate = interval(0, 1, objective=0.3333333333333333)
    result = EquiCEvalEvaluator().evaluate(ref, candidate, provided_substitutions={
        "x": {"coeffs": {"x": 0.3333333333333333}}})
    assert result.verdict == "unsupported"
    assert any("higher-precision" in note for note in result.notes)


def test_redundant_row_changes_score_but_not_reference_set():
    ref = CanonicalIR("ref", {"x": V("x", "continuous", 0, 10),
                              "y": V("y", "continuous", 9, 20)}, [], "minimize", {})
    candidate = CanonicalIR("point", {"x": V("x", "continuous", 11, 11),
                                     "y": V("y", "continuous", 8, 8)}, [], "minimize", {})
    augmented = replace(ref, constraints=[C("redundant", {"x": 1, "y": -1}, -1, "<=")])
    checker = DirectedDiscrepancyEvaluator()
    a = checker.evaluate_delta_right(ref, candidate)
    b = checker.evaluate_delta_right(augmented, candidate)
    assert a.lower_bound == pytest.approx(1/9)
    assert b.lower_bound == 1
    assert a.status == b.status == "disproved"


def test_independent_oracle_and_contract_separation():
    from src.benchmark.verified_evaluation import enumerate_oracle, demo_records, ir_from_dict
    ref = interval(0, 3, kind="integer")
    cand = interval(0, 3, kind="integer", objective=2)
    assert enumerate_oracle(ref, cand, "feasible_set")[0] is True
    assert enumerate_oracle(ref, cand, "feasible_set_and_objective_value")[0] is False
    assert enumerate_oracle(interval(), interval(), "feasible_set")[0] is None
    for record in demo_records():
        ref, cand = ir_from_dict(record["reference_ir"]), ir_from_dict(record["candidate_ir"])
        label, evidence = enumerate_oracle(ref, cand, "feasible_set_and_objective_value")
        result = EquiCEvalEvaluator(contract=OBJECTIVE_VALUE).evaluate(ref, cand)
        assert evidence["method"] == "independent_integer_enumeration"
        assert (result.verdict == "certified") == label
        assert result.verdict in ("certified", "disproved")


def test_small_integer_random_cases_agree_with_independent_oracle():
    import random
    from src.benchmark.verified_evaluation import enumerate_oracle
    rng = random.Random(42)
    for _ in range(25):
        ref = CanonicalIR("random", {"x": V("x", "integer", 0, 2),
                                     "y": V("y", "integer", 0, 2)},
                         [C("c", {"x": rng.randint(-2, 2), "y": rng.randint(-2, 2)},
                            -rng.randint(0, 4), "<=")], "minimize", {})
        cand = replace(ref, constraints=[replace(ref.constraints[0], constant=-rng.randint(0, 4))])
        label, _ = enumerate_oracle(ref, cand, "feasible_set")
        result = EquiCEvalEvaluator(contract="feasible_set").evaluate(ref, cand)
        assert not (label and result.verdict == "disproved")
        assert not (label is False and result.verdict in ("certified", "within_tolerance"))
        assert result.verdict in ("certified", "within_tolerance", "disproved")


def test_invalid_bounds_cannot_disappear_during_projection():
    result = EquiCEvalEvaluator().evaluate(interval(), interval(float("nan"), 10))
    assert result.verdict == "unresolved"
    assert result.budget["solver_calls"] == 0


def test_objective_coefficients_below_old_drop_threshold_are_preserved():
    ref, cand = interval(0, 1, objective=0), interval(0, 1, objective=1e-13)
    cert = build_projection_certificate(ref, cand)
    assert cert.project_ir(cand, ref).objective_coeffs["x"] == 1e-13
    result = EquiCEvalEvaluator(solver_tolerance=0, contract=OBJECTIVE_VALUE).evaluate(ref, cand)
    assert result.verdict != "certified"
