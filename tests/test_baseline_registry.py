"""Baseline registry: only the original-paper reference-form methods for now.

External baselines (EquivaMap / ReLoop / Falsification) are deferred; the
registry exists so they can be added behind one interface without touching the
tier-2 runner.
"""
import pytest

from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalVariable as V,
    CanonicalConstraint as C,
)
from src.benchmark.baselines import BASELINES, build_baselines


def pair_with_missing_constraint():
    ref = CanonicalIR("ref", {"x": V("x", "integer", 0.0, 8.0)},
                      [C("cap", {"x": 1.0}, -8.0, "<=")], "minimize", {"x": 1.0})
    cand = CanonicalIR("cand", {"x": V("x", "integer", 0.0, 10.0)},
                       [], "minimize", {"x": 1.0})
    return ref, cand


def test_registry_exposes_reference_form_methods():
    assert set(build_baselines(["refform", "strong"])) == {"refform", "strong"}


def test_unknown_baseline_raises():
    with pytest.raises(KeyError):
        build_baselines(["equiva_map"])


def test_identical_pair_is_certified():
    ref = CanonicalIR("ref", {"x": V("x", "integer", 0.0, 8.0)},
                      [C("cap", {"x": 1.0}, -8.0, "<=")], "minimize", {"x": 1.0})
    result = BASELINES["refform"].evaluate(ref, ref)
    assert result.verdict == "certified"
    assert result.score == 0.0


def test_missing_constraint_pair_is_disproved():
    ref, cand = pair_with_missing_constraint()
    result = BASELINES["refform"].evaluate(ref, cand)
    assert result.verdict == "disproved"
    assert result.score > 0.0
    assert result.details["n_ref"] == 1
