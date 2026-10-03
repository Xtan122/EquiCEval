"""Independent, hand-constructed checks of manuscript M2/M3 behavior."""
import json
import math
from dataclasses import replace

import pytest

from src.equiceval.canonical_ir import CanonicalIR, CanonicalVariable as V, CanonicalConstraint as C
from src.equiceval.directed_query import DirectedDiscrepancyEvaluator
from src.equiceval.contracts import OBJECTIVE_VALUE
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.equiceval.evidence import check_implication_certificate, point_is_feasible
from src.equiceval.matching import EquivalenceMatcher, MatchingLabel, normalized_key
from src.utils.solver_wrapper import QueryBudget
from src.equiceval.precheck import ModelPreChecker, FeasStatus, ParseStatus, BoundStatus, MapStatus
from src.utils.solver_wrapper import SolverResult, UnifiedSolver
from unittest.mock import patch


def model(rows, names=("x", "y")):
    return CanonicalIR("component_case", {n: V(n, "continuous", -math.inf, math.inf) for n in names},
                       rows, "minimize", {})


def explain(ref, cand, **kwargs):
    return EquivalenceMatcher().evaluate_components(ref, cand, budget=QueryBudget(5),
                                                    safety_box_bound=2, **kwargs)


def xy_pair(common=None):
    common = common or []
    return (model(common + [C("xy", {"x": 1, "y": 1}, -1, "<=")]),
            model(common + [C("x_only", {"x": 1}, -1, "<=")]))


def test_common_y_zero_certifies_only_context_equivalence():
    ref, cand = xy_pair([C("y_zero", {"y": 1}, 0, "==")])
    report = explain(ref, cand)
    match = next(m for m in report["matches"] if m.gt_name == "xy")
    assert match.label == MatchingLabel.CONTEXT_EQUIVALENT
    assert match.status == "certified"
    assert match.evidence["is_model_level_witness"] is False
    assert [c["name"] for c in match.evidence["common_rows"]] == ["y_zero"]
    # Reconstruct each source and independently replay every exported certificate.
    for direction, source_rows in (("reference_to_candidate", ref.constraints),
                                   ("candidate_to_reference", cand.constraints)):
        source = model(source_rows)
        source = replace(source, variables={n: replace(v, lower_bound=-2, upper_bound=2)
                                            for n, v in source.variables.items()})
        witness = match.evidence[direction]
        assert point_is_feasible(source, witness["variable_assignment"])
        for obligation in witness["obligations"]:
            if obligation["certificate"]:
                row = C(obligation["target_name"], **obligation["target_row"])
                assert check_implication_certificate(source, row, obligation["certificate"])


def test_removing_common_y_zero_exposes_a_pair_witness():
    ref, cand = xy_pair()
    report = explain(ref, cand)
    assert not report["matches"]
    trial = report["trials"][0]
    assert trial.label == MatchingLabel.DISPROVED_WITH_WITNESS
    assert trial.evidence["common_rows"] == []
    for direction, source in (("reference_to_candidate", ref), ("candidate_to_reference", cand)):
        result = trial.evidence[direction]
        if result["status"] == "disproved":
            assert point_is_feasible(source, result["variable_assignment"], box=2)


def test_one_models_private_condition_never_becomes_common_context():
    ref, cand = xy_pair()
    cand.constraints.append(C("private_y_zero", {"y": 1}, 0, "=="))
    report = explain(ref, cand)
    trial = next(t for t in report["trials"] if t.gt_name == "xy" and t.candidate_name == "x_only")
    assert trial.status == "disproved"
    assert not trial.evidence["common_rows"]


def test_duplicate_tested_rows_cannot_leak_into_context():
    ref = model([C("a", {"x": 1}, -1, "<="), C("a_copy", {"x": 1}, -1, "<=")], ("x",))
    cand = model([C("b", {"x": 1}, -2, "<="), C("a", {"x": 1}, -1, "<=")], ("x",))
    report = explain(ref, cand)
    assert all(t.status == "disproved" for t in report["trials"])
    assert all(not t.evidence["common_rows"] for t in report["trials"])


def test_two_empty_context_domains_do_not_certify_a_pair():
    ref, cand = xy_pair([C("zero", {"y": 1}, 0, "=="), C("one", {"y": 1}, -1, "==")])
    report = explain(ref, cand)
    trial = next(t for t in report["trials"] if t.gt_name == "xy" and t.candidate_name == "x_only")
    assert trial.label == MatchingLabel.UNRESOLVED
    assert all(trial.evidence[d]["status"] == "source_infeasible"
               for d in ("reference_to_candidate", "candidate_to_reference"))
    assert not any(m.gt_name == "xy" for m in report["matches"])


@pytest.mark.parametrize("reverse", [False, True])
def test_equality_and_two_inequalities_form_a_verified_group(reverse):
    ref = model([C("zero", {"x": 1}, 0, "==")], ("x",))
    cand = model([C("up", {"x": 1}, 0, "<="), C("down", {"x": -1}, 0, "<=")], ("x",))
    if reverse:
        ref, cand = cand, ref
    report = explain(ref, cand, group_matching=True)
    assert len(report["matches"]) == 1
    group = report["matches"][0]
    assert group.label == MatchingLabel.GROUP_EQUIVALENT
    assert group.status == "certified"
    assert len(group.gt_indices) == (2 if reverse else 1)
    assert report["certified_reference_rows"] == len(ref.constraints)
    assert not report["unmatched_reference_indices"]


def test_group_matching_is_not_claimed_when_disabled():
    ref = model([C("zero", {"x": 1}, 0, "==")], ("x",))
    cand = model([C("up", {"x": 1}, 0, "<="), C("down", {"x": -1}, 0, "<=")], ("x",))
    report = explain(ref, cand, group_matching=False)
    assert not report["matches"]
    assert report["controls"]["tested_group_trials"] == 0


def test_zero_budget_leaves_non_algebraic_pairs_unexplored():
    ref, cand = xy_pair([C("common", {"y": 1}, 0, "==")])
    budget = QueryBudget(0)
    report = EquivalenceMatcher().evaluate_components(ref, cand, budget=budget)
    assert len(report["matches"]) == 1  # Only the known algebraic common row.
    assert not report["trials"]
    assert budget.to_dict()["solver_calls"] == 0


def test_pair_search_cap_and_shared_call_cap_are_respected():
    ref, cand = xy_pair()
    budget = QueryBudget(5, max_calls=1)
    report = EquivalenceMatcher().evaluate_components(ref, cand, budget=budget,
                                                     safety_box_bound=2, max_context_pairs=1)
    assert report["controls"]["tested_context_pairs"] == 1
    assert budget.to_dict()["solver_calls"] == 1
    assert not report["matches"]
    assert report["trials"][0].status == "unresolved"


def test_algebraic_assignment_prefers_exact_when_duplicate_rows_exist():
    ref = model([C("a", {"x": 1}, -1, "<="), C("b", {"x": 2}, -2, "<=")], ("x",))
    cand = model(list(reversed(ref.constraints)), ("x",))
    matches = EquivalenceMatcher().match_constraints(ref, cand)
    assert [(m.gt_index, m.candidate_index) for m in matches] == [(0, 1), (1, 0)]
    assert all(m.label == MatchingLabel.EXACT for m in matches)
    assert normalized_key(C("const", {}, 1, "==")) == normalized_key(C("const", {}, -1, "=="))


def test_sampling_denominators_are_explicit_and_nan_serializes_as_null():
    # M3 now uses solver-targeted strata (feasible/boundary/thin-margin/
    # perturbed), not a uniform box; the sample counts are still explicit.
    ref = model([C("c", {"x": 1}, -2, "<=")], ("x",))
    result = EquiCEvalEvaluator(context_matching=False).evaluate(ref, ref, run_precheck=False)
    diagnostic = result.to_diagnostic_vector()
    assert diagnostic["sampling"]["total_samples"] > 0
    assert set(diagnostic["sampling"]["sample_counts"]) == {
        "feasible", "boundary", "thin_margin", "perturbed"}
    assert diagnostic["D_sat"] == diagnostic["D_margin"] == 0
    assert diagnostic["MatchCoverage"] == 1
    assert sum(diagnostic["budget"]["calls_by_phase"].values()) == diagnostic["budget"]["solver_calls"]
    # No matched rows → no denominator → None, never 0.
    no_rows = model([], ("x",))
    empty = EquiCEvalEvaluator(context_matching=False).evaluate(
        no_rows, no_rows, run_precheck=False).to_diagnostic_vector()
    assert empty["D_sat"] is None and empty["D_margin"] is None
    assert empty["sampling"]["total_samples"] == 0
    assert empty["sampling"]["status"] == "not_applicable"
    json.dumps(empty, allow_nan=False)


def test_context_equivalence_can_have_nonzero_descriptive_scores_outside_context():
    ref, cand = xy_pair([C("common", {"y": 1}, 0, "==")])
    result = EquiCEvalEvaluator(safety_box_bound=2).evaluate(ref, cand, run_precheck=False)
    assert result.verdict == "within_scope"
    assert any(m.label == MatchingLabel.CONTEXT_EQUIVALENT for m in result.matched_details)
    assert result.d_sat > 0 and result.d_margin > 0
    assert result.sampling["total_samples"] > 0


def test_missing_sampling_box_is_not_reported_as_zero_samples_score():
    ref = model([], ("x",))
    diagnostic = EquiCEvalEvaluator(context_matching=False).evaluate(ref, ref, run_precheck=False).to_diagnostic_vector()
    assert diagnostic["D_sat"] is None
    assert diagnostic["sampling"]["status"] == "not_applicable"
    assert diagnostic["sampling"]["total_samples"] == 0


def test_partial_mapping_coverage_does_not_unlock_global_verification():
    ref = model([], ("x", "y"))
    cand = model([], ("x", "unknown"))
    result = EquiCEvalEvaluator().evaluate(ref, cand)
    assert result.to_diagnostic_vector()["MapCoverage"] == 0.5
    assert result.verdict == "unresolved" and not result.mapping["is_verified"]
    assert result.budget["solver_calls"] == 0


def test_objective_coefficient_fidelity_is_separate_from_value_agreement():
    ref = model([C("zero", {"x": 1}, 0, "==")], ("x",))
    cand = replace(ref, objective_coeffs={"x": 2})
    result = EquiCEvalEvaluator(context_matching=False, contract=OBJECTIVE_VALUE).evaluate(
        ref, cand, run_precheck=False)
    assert result.objective_coefficients["status"] == "different"
    assert result.objective_verdict == "certified"  # Both objectives are zero on x=0.
    vector = result.to_diagnostic_vector()
    # Module 5 is now wired: the cross-regret block reports a real status, not
    # a "not_implemented" placeholder.
    assert vector["ObjectiveStatus"] == result.objective5_status
    assert vector["cross_regret"]["status"] == result.objective5_status
    assert vector["cross_regret"]["status"] != "not_implemented"


def test_equality_obligations_have_replayable_signed_sides():
    ref = CanonicalIR("zero", {"x": V("x", "continuous", -1, 1)},
                      [C("zero", {"x": 1}, 0, "==")], "minimize", {})
    cand = replace(ref, constraints=[])
    result = DirectedDiscrepancyEvaluator().evaluate_delta_right(ref, cand)
    sides = [o for o in result.obligations if o["target_name"] == "zero"]
    assert {o["signed_side"] for o in sides} == {"+", "-"}
    assert {o["target_row"]["coeffs"]["x"] for o in sides} == {1, -1}


def test_unbounded_reference_domain_is_not_a_parse_error():
    ref = model([C("nonnegative", {"x": -1}, 0, "<=")], ("x",))
    ref_status, cand_status = ModelPreChecker().run(ref, ref)
    assert ref_status.s_bound == cand_status.s_bound == BoundStatus.DOMAIN_UNBOUNDED
    assert cand_status.s_parse == ParseStatus.PARSED
    assert cand_status.parse_error_msg is None
    assert cand_status.can_run_directed_queries


def test_precheck_validates_points_instead_of_trusting_optimal_status():
    ref = model([C("zero", {"x": 1}, 0, "==")], ("x",))
    fake = SolverResult("Optimal", 0, {"x": 1}, 0, 0, "numerical_optimum")
    with patch.object(UnifiedSolver, "solve_pulp_model", return_value=fake):
        assert ModelPreChecker().check_feasibility(ref)[0] == FeasStatus.UNKNOWN
    incumbent = SolverResult("Timeout", 0, {"x": 0}, 0)
    with patch.object(UnifiedSolver, "solve_pulp_model", return_value=incumbent):
        assert ModelPreChecker().check_feasibility(ref)[0] == FeasStatus.FEASIBLE


def test_partial_mapping_is_unresolved_not_unsupported_by_arbitrary_threshold():
    ref, cand = model([], ("x", "y")), model([], ("x", "unknown"))
    assert ModelPreChecker().check_mapping(ref, cand)[0] == MapStatus.UNRESOLVED


@pytest.mark.parametrize("kind", ["continuous", "binary"])
def test_adding_synthetic_bounds_is_idempotent_without_deleting_user_rows(kind):
    ref = CanonicalIR("bounds", {"x": V("x", kind, 0, 1)},
                      [C("explicit_upper", {"x": 1}, -1, "<="),
                       C("separate_requirement", {"x": 1}, -1, "<=")], "minimize", {})
    once = ref.merge_bounds_into_constraints()
    twice = once.merge_bounds_into_constraints()
    assert len(once.constraints) == len(twice.constraints) == 3
    assert [c.name for c in once.constraints][:2] == ["explicit_upper", "separate_requirement"]
