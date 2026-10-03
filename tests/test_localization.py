"""Top-1 fault localization (paper §8.2).

For a labelled feasible-set fault with an independent counterexample, the truly
faulty components are the rows the counterexample violates. Localization checks
whether the first constraint EquiCEval reports is among them.
"""
from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalVariable as V,
    CanonicalConstraint as C,
)
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.benchmark.independent_oracle import independent_label
from src.benchmark.witness_metrics import localization_check
from src.benchmark.analysis import compute_localization_accuracy


def missing_cap_pair():
    ref = CanonicalIR("ref", {"x": V("x", "integer", 0.0, 8.0)},
                      [C("cap", {"x": 1.0}, -8.0, "<=")], "minimize", {"x": 1.0})
    cand = CanonicalIR("cand", {"x": V("x", "integer", 0.0, 10.0)},
                       [], "minimize", {"x": 1.0})
    return ref, cand


def test_localization_flags_true_fault_component():
    ref, cand = missing_cap_pair()
    label, evidence = independent_label(ref, cand, "feasible_set_and_objective_value")
    assert label is False
    diagnostic = EquiCEvalEvaluator(solver_time_limit=1.0).evaluate(ref, cand).to_diagnostic_vector()
    result = localization_check(ref, cand, evidence, diagnostic)
    assert result is not None
    assert "cap" in result["true"]
    assert result["predicted"][0] in result["true"]


def test_localization_absent_for_equivalent_pair():
    ref, _ = missing_cap_pair()
    _, evidence = independent_label(ref, ref, "feasible_set_and_objective_value")
    diagnostic = EquiCEvalEvaluator(solver_time_limit=1.0).evaluate(ref, ref).to_diagnostic_vector()
    assert localization_check(ref, ref, evidence, diagnostic) is None


def test_aggregate_localization_accuracy():
    true_list = [["cap", "x"]] * 3 + [["y"]]
    predicted = [["cap"], ["x"], ["cap"], ["z"]]
    assert compute_localization_accuracy(true_list, predicted) == 0.75
