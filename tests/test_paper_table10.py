"""Regression tests for the nine mandatory known-answer cases (Bảng 10, §9.3).

Each test checks both the numeric result and the status, so a future change that
silently re-breaks one of these cases fails loudly. Cases 1-3 and 5-9 go through
the full verified evaluator; case 4 exercises the directed-query maximum.
"""
import pytest

from src.equiceval.canonical_ir import (
    CanonicalConstraint,
    CanonicalIR,
    CanonicalVariable,
)
from src.equiceval.directed_query import DirectedDiscrepancyEvaluator
from src.equiceval.contracts import OBJECTIVE_VALUE
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.utils.solver_wrapper import QueryBudget


def _ir(name, variables, constraints=(), obj=None, sense="minimize"):
    variables = {
        v: CanonicalVariable(v, kind, lb, ub)
        for v, (kind, lb, ub) in variables.items()
    }
    return CanonicalIR(name, variables, list(constraints), sense, dict(obj or {}))


def _row(name, coeffs, constant, sense="<="):
    return CanonicalConstraint(name, dict(coeffs), constant, sense)


def _evaluate(ref, cand, **kwargs):
    evaluator = EquiCEvalEvaluator(solver_time_limit=kwargs.pop("solver_time_limit", 5.0),
                                   **kwargs)
    return evaluator.evaluate(ref, cand)


# Case 1: x <= 1 and 0.1x <= 0.1 must normalize the same and not be punished.
def test_case1_scaled_row_is_not_a_false_alarm():
    ref = _ir("ref", {"x": ("continuous", 0.0, 10.0)},
              [_row("c", {"x": 1.0}, -1.0)], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 10.0)},
               [_row("c", {"x": 0.1}, -0.1)], {"x": 1.0})
    assert ref.constraints[0].normalize().coeffs == cand.constraints[0].normalize().coeffs
    res = _evaluate(ref, cand)
    assert res.verdict == "certified"


# Case 2: x <= 8 plus a redundant x <= 10 is equivalent; extra rows are not penalized.
def test_case2_redundant_row_is_not_a_false_alarm():
    ref = _ir("ref", {"x": ("continuous", 0.0, 10.0)},
              [_row("c", {"x": 1.0}, -8.0)], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 10.0)},
               [_row("c", {"x": 1.0}, -8.0), _row("r", {"x": 1.0}, -10.0)], {"x": 1.0})
    res = _evaluate(ref, cand)
    assert res.verdict == "certified"


# Case 3: same optimum, different domain -> counterexample (x = 9) must be exposed.
def test_case3_same_optimum_different_domain_is_disproved():
    ref = _ir("ref", {"x": ("continuous", 0.0, 8.0)}, [], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 10.0)}, [], {"x": 1.0})
    res = _evaluate(ref, cand)
    assert res.verdict == "disproved"
    assert res.delta_right > 0.0


# Case 4: source domain [-1, 0], target row x = 0 -> maximum violation is 1, not 0.
def test_case4_max_violation_is_one_not_zero():
    domain = _ir("cand", {"x": ("continuous", -1.0, 0.0)})
    target = _ir("ref", {"x": ("continuous", float("-inf"), float("inf"))},
                 [_row("eq", {"x": 1.0}, 0.0, "==")])
    witness = DirectedDiscrepancyEvaluator().evaluate_delta_right(
        target, domain, budget=QueryBudget(5.0))
    assert witness.status == "disproved"
    assert witness.discrepancy_value == pytest.approx(1.0)


# Case 5: x in {0,1} versus x in [0,1] -> out of scope / type mismatch, never certified.
def test_case5_binary_versus_continuous_is_unsupported():
    ref = _ir("ref", {"x": ("binary", 0.0, 1.0)}, [], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 1.0)}, [], {"x": 1.0})
    res = _evaluate(ref, cand)
    assert res.verdict == "unsupported"
    assert "variable-type-mismatch" in res.mapping.get("unsupported_features", [])


# Case 6: exhausted budget / solver failure -> unresolved, never certified.
def test_case6_exhausted_budget_stays_unresolved():
    ref = _ir("ref", {"x": ("continuous", 0.0, 10.0)},
              [_row("c", {"x": 1.0}, -1.0)], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 10.0)},
               [_row("c", {"x": 1.0}, -1.0)], {"x": 1.0})
    res = _evaluate(ref, cand, solver_time_limit=0.0)
    assert res.verdict == "unresolved"


# Case 7: a looser candidate bound must not be silently replaced by the reference bound.
def test_case7_candidate_bound_is_not_copied_from_reference():
    ref = _ir("ref", {"x": ("continuous", 0.0, 10.0)}, [], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 1000.0)}, [], {"x": 1.0})
    res = _evaluate(ref, cand)
    assert res.verdict == "disproved"
    assert res.delta_right > 0.0


# Case 8: disjoint but non-empty domains -> feasibility still runs, M5 on the
# intersection is not applicable.
def test_case8_disjoint_domains_skip_objective_comparison():
    ref = _ir("ref", {"x": ("continuous", 0.0, 10.0)},
              [_row("eq", {"x": 1.0}, -1.0, "==")], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 10.0)},
               [_row("eq", {"x": 1.0}, -2.0, "==")], {"x": 1.0})
    res = _evaluate(ref, cand, contract=OBJECTIVE_VALUE)
    assert res.verdict == "disproved"
    assert res.objective_verdict == "not_applicable"


# Case 9: identical feasible sets, different objective -> feasible-set equality
# alone must not certify the whole model.
def test_case9_equal_domains_different_objective_is_disproved():
    ref = _ir("ref", {"x": ("continuous", 0.0, 10.0)}, [], {"x": 1.0})
    cand = _ir("cand", {"x": ("continuous", 0.0, 10.0)}, [], {"x": 2.0})
    res = _evaluate(ref, cand, contract=OBJECTIVE_VALUE)
    assert res.feasibility_verdict == "certified"
    assert res.verdict == "disproved"
