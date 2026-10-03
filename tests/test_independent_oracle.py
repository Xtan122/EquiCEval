"""Independent labels for renaming and continuous/LP pairs.

The exhaustive integer oracle requires identity names and integer variables, so
it returns ``None`` for renamed and continuous candidates. These tests pin the
two independent fallbacks: an exact variable-bijection match for renaming, and
an LP containment check for continuous/mixed pairs. Equivalent labels are sound
(both polyhedra contained); not-equivalent labels must carry an exact witness.
"""
from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalVariable as V,
    CanonicalConstraint as C,
)
from src.benchmark.independent_oracle import independent_label

CONTRACT = "feasible_set_and_objective_value"


def ir(name, variables, constraints, sense="minimize", obj=None, const=0.0):
    return CanonicalIR(name, variables, constraints, sense, obj or {}, const)


# ── renaming ────────────────────────────────────────────────────────────────

def test_renamed_binary_equivalent():
    ref = ir("k", {"x": V("x", "binary", 0, 1), "y": V("y", "binary", 0, 1)},
             [C("cap", {"x": 1.0, "y": 1.0}, -1.0, "<=")], "maximize", {"x": 1.0, "y": 2.0})
    cand = ir("k_renamed", {"var_A": V("var_A", "binary", 0, 1), "var_B": V("var_B", "binary", 0, 1)},
              [C("cap", {"var_A": 1.0, "var_B": 1.0}, -1.0, "<=")], "maximize", {"var_A": 1.0, "var_B": 2.0})
    label, ev = independent_label(ref, cand, CONTRACT)
    assert label is True
    assert ev["method"] == "independent_renaming_bijection"


def test_renamed_continuous_equivalent():
    ref = ir("d", {"x": V("x", "continuous", 0.0, 10.0)},
             [C("cap", {"x": 2.0}, -10.0, "<=")], "minimize", {"x": 1.0})
    cand = ir("d_renamed", {"var_A": V("var_A", "continuous", 0.0, 10.0)},
              [C("cap", {"var_A": 2.0}, -10.0, "<=")], "minimize", {"var_A": 1.0})
    label, ev = independent_label(ref, cand, CONTRACT)
    assert label is True
    assert ev["method"] == "independent_renaming_bijection"


# ── continuous / LP containment ─────────────────────────────────────────────

def diet_pair():
    ref = ir("diet", {"a": V("a", "continuous", 0.0, 10.0), "b": V("b", "continuous", 0.0, 10.0)},
             [C("min_vit", {"a": -10.0, "b": -5.0}, 50.0, "<="),
              C("max_fiber", {"a": 5.0, "b": 10.0}, -60.0, "<=")],
             "minimize", {"a": 2.0, "b": 1.5})
    return ref


def test_scaled_continuous_equivalent():
    ref = diet_pair()
    scaled = ir("diet_scaled",
                dict(ref.variables),
                [C("min_vit_scaled", {"a": -31.5, "b": -15.75}, 157.5, "<="),
                 C("max_fiber", {"a": 5.0, "b": 10.0}, -60.0, "<=")],
                "minimize", dict(ref.objective_coeffs))
    label, ev = independent_label(ref, scaled, CONTRACT)
    assert label is True
    assert ev["method"] == "independent_scaled_row_match"


def test_over_constraining_continuous_mutant_is_disproved():
    ref = diet_pair()
    mutant = ir("diet_over",
                dict(ref.variables),
                list(ref.constraints) + [C("extra", {"a": 1.0}, -5.0, "<=")],
                "minimize", dict(ref.objective_coeffs))
    label, ev = independent_label(ref, mutant, CONTRACT)
    assert label is False
    assert ev["counterexample"]["point"]


def test_missing_bound_is_disproved():
    ref = ir("m", {"x": V("x", "continuous", 0.0, 10.0)}, [], "minimize", {"x": 1.0})
    cand = ir("m", {"x": V("x", "continuous", 0.0, 12.0)}, [], "minimize", {"x": 1.0})
    label, ev = independent_label(ref, cand, CONTRACT)
    assert label is False


def test_objective_difference_depends_on_contract():
    ref = ir("o", {"x": V("x", "continuous", 0.0, 10.0)}, [], "minimize", {"x": 1.0})
    cand = ir("o", {"x": V("x", "continuous", 0.0, 10.0)}, [], "minimize", {"x": 2.0})
    assert independent_label(ref, cand, "feasible_set")[0] is True
    assert independent_label(ref, cand, CONTRACT)[0] is False


def test_unbounded_direction_is_unknown():
    ref = ir("u", {"x": V("x", "continuous", float("-inf"), float("inf"))}, [], "minimize", {"x": 1.0})
    cand = ir("u", {"x": V("x", "continuous", float("-inf"), 5.0)}, [], "minimize", {"x": 1.0})
    label, _ = independent_label(ref, cand, CONTRACT)
    assert label is None
