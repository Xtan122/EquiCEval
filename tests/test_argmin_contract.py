"""The ``feasible_set_and_argmin`` contract compares optimal decision sets.

Two linear objectives have the same argmin over a common (bounded) feasible set
when their signed coefficient vectors are positive multiples; additive constants
do not change the argmin. Objective unit conversion is expressed through the
projection's affine substitutions.
"""
from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalVariable as V,
    CanonicalConstraint as C,
)
from src.equiceval.evaluator import EquiCEvalEvaluator
from src.benchmark.independent_oracle import independent_label

ARG = "feasible_set_and_argmin"
VAL = "feasible_set_and_objective_value"


def box(sense="minimize", obj=None, const=0.0, unit=""):
    var = V("x", "continuous", 0.0, 10.0, unit=unit)
    return CanonicalIR("p", {"x": var}, [], sense, obj or {"x": 1.0}, const)


def test_positive_scaling_is_same_argmin():
    ref = box(obj={"x": 1.0})
    cand = box(obj={"x": 2.0})
    assert EquiCEvalEvaluator(contract=ARG).evaluate(ref, cand).verdict == "certified"


def test_opposite_direction_is_disproved():
    ref = box(sense="minimize", obj={"x": 1.0})
    cand = box(sense="maximize", obj={"x": 1.0})
    assert EquiCEvalEvaluator(contract=ARG).evaluate(ref, cand).verdict == "disproved"


def test_additive_constant_keeps_argmin():
    ref = box(obj={"x": 1.0}, const=0.0)
    cand = box(obj={"x": 1.0}, const=5.0)
    assert EquiCEvalEvaluator(contract=ARG).evaluate(ref, cand).verdict == "certified"
    # the objective-value contract distinguishes them
    assert EquiCEvalEvaluator(contract=VAL).evaluate(ref, cand).verdict == "disproved"


def test_different_slope_is_disproved():
    ref = CanonicalIR("p", {"x": V("x", "continuous", 0.0, 10.0),
                            "y": V("y", "continuous", 0.0, 10.0)},
                      [], "minimize", {"x": 1.0, "y": 0.0})
    cand = CanonicalIR("p", {"x": V("x", "continuous", 0.0, 10.0),
                             "y": V("y", "continuous", 0.0, 10.0)},
                       [], "minimize", {"x": 1.0, "y": 1.0})
    assert EquiCEvalEvaluator(contract=ARG).evaluate(ref, cand).verdict == "disproved"


def test_independent_label_argmin_positive_multiple():
    ref = CanonicalIR("p", {"x": V("x", "integer", 0.0, 8.0)}, [], "minimize", {"x": 1.0})
    cand = CanonicalIR("p", {"x": V("x", "integer", 0.0, 8.0)}, [], "minimize", {"x": 2.0})
    assert independent_label(ref, cand, ARG)[0] is True


def test_independent_label_argmin_opposite_direction():
    ref = CanonicalIR("p", {"x": V("x", "integer", 0.0, 8.0)}, [], "minimize", {"x": 1.0})
    cand = CanonicalIR("p", {"x": V("x", "integer", 0.0, 8.0)}, [], "maximize", {"x": 1.0})
    assert independent_label(ref, cand, ARG)[0] is False


def test_independent_label_argmin_continuous_via_bijection():
    ref = CanonicalIR("p", {"x": V("x", "continuous", 0.0, 8.0)}, [], "minimize", {"x": 1.0})
    cand = CanonicalIR("p", {"x": V("x", "continuous", 0.0, 8.0)}, [], "minimize", {"x": 3.0})
    assert independent_label(ref, cand, ARG)[0] is True


def test_objective_unit_conversion_via_projection():
    ref = CanonicalIR("u", {"x": V("x", "continuous", 0.0, 5.0, unit="tonne")},
                      [C("cap", {"x": 1.0}, -5.0, "<=")], "minimize", {"x": 1.0})
    cand = CanonicalIR("u", {"x": V("x", "continuous", 0.0, 5000.0, unit="kg")},
                       [C("cap", {"x": 1.0}, -5000.0, "<=")], "minimize", {"x": 0.001})
    assert EquiCEvalEvaluator(contract=VAL).evaluate(ref, cand).verdict == "certified"
