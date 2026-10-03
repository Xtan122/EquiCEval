"""Witness validity and coverage (paper §8.2).

Witness validity = fraction of exported counterexamples that pass an independent
re-check (point feasible in the source model, violating the target). Witness
coverage = fraction of labelled feasible-set faults that carry at least one
valid witness. Both report "not applicable" when the denominator is zero.
"""
from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalVariable as V,
    CanonicalConstraint as C,
)
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.benchmark.witness_metrics import witness_check, witness_metrics


def missing_bound_pair():
    ref = CanonicalIR("ref", {"x": V("x", "integer", 0.0, 8.0)},
                      [C("cap", {"x": 1.0}, -8.0, "<=")], "minimize", {"x": 1.0})
    cand = CanonicalIR("cand", {"x": V("x", "integer", 0.0, 10.0)},
                       [], "minimize", {"x": 1.0})
    return ref, cand


def test_witness_check_accepts_valid_counterexample():
    ref, cand = missing_bound_pair()
    diagnostic = EquiCEvalEvaluator(solver_time_limit=1.0).evaluate(ref, cand).to_diagnostic_vector()
    assert diagnostic["verdict"] == "disproved"
    present, valid = witness_check(ref, cand, diagnostic)
    assert present is True
    assert valid is True


def test_witness_check_rejects_tampered_point():
    ref, cand = missing_bound_pair()
    diagnostic = EquiCEvalEvaluator(solver_time_limit=1.0).evaluate(ref, cand).to_diagnostic_vector()
    diagnostic["right_evidence"]["variable_assignment"] = {"x": 100.0}
    present, valid = witness_check(ref, cand, diagnostic)
    assert present is True
    assert valid is False


def test_witness_check_absent_when_certified():
    ref, _ = missing_bound_pair()
    diagnostic = EquiCEvalEvaluator(solver_time_limit=1.0).evaluate(ref, ref).to_diagnostic_vector()
    present, valid = witness_check(ref, ref, diagnostic)
    assert present is False
    assert valid is False


def test_witness_metrics_rates_and_not_applicable():
    rows = [
        {"label": False, "fault_kind": "feasible_set", "witness": {"present": True, "valid": True}},
        {"label": False, "fault_kind": "feasible_set", "witness": {"present": True, "valid": False}},
        {"label": True, "fault_kind": None, "witness": {"present": False, "valid": False}},
    ]
    metrics = witness_metrics(rows)
    assert metrics["validity_rate"]["value"] == 0.5
    assert metrics["coverage"]["value"] == 0.5

    empty = witness_metrics([{"label": True, "fault_kind": None,
                              "witness": {"present": False, "valid": False}}])
    assert empty["validity_rate"]["value"] is None
    assert empty["coverage"]["value"] is None
