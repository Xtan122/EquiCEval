"""Regression tests for structural index-name mapping and verified reference
elimination ported into src/equiceval/canonical_ir.py.

These are additive detection methods: shared names, declared aliases and
requirement IDs keep precedence, and fuzzy names without index digits stay
rejected (see test_verification_evidence.test_fuzzy_names_and_type_mismatch_are_not_certificates).
"""
import pytest

from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalConstraint,
    CanonicalVariable,
    build_projection_certificate,
)
from src.benchmark.reference_ir import (
    make_aircraft_assignment_reference,
    make_aircraft_landing_reference,
)


def _unlinked_aircraft_landing_reference():
    """ALP reference without the explicit ``z_ij + z_ji = 1`` rows.

    The complement-elimination feature applies when the reference encodes both
    order binaries without a linking row; the fixed reference (paper Eq 24) uses
    the link instead, so this fixture preserves the elimination test coverage.
    """
    ref = make_aircraft_landing_reference()
    ref.constraints = [c for c in ref.constraints if not c.name.startswith("order_link")]
    return ref


def _var(name, vtype="binary", lb=0.0, ub=1.0, unit="", index_sets=None):
    var = CanonicalVariable(name, vtype, lb, ub)
    var.unit = unit
    var.index_sets = list(index_sets or [])
    return var


def test_index_signature_maps_semantic_names():
    ref = make_aircraft_assignment_reference()
    pairs = [(1, 1), (1, 2), (2, 1), (2, 2), (3, 1), (3, 2)]
    variables = {f"x_A{a}_R{r}": _var(f"x_A{a}_R{r}") for a, r in pairs}
    cand = CanonicalIR(
        "AircraftAssignment_LLM",
        variables,
        [],
        "minimize",
        {f"x_A{a}_R{r}": 100.0 for a, r in pairs},
    )
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert cert.variable_map["x_A1_R1"] == "x11"
    assert cert.variable_map["x_A3_R2"] == "x32"
    assert "index-signature" in cert.detection_method
    # Name/pattern matches are assumptions, never silent proof (§5.4).
    assert any("assumption" in w for w in cert.warnings)


def _aircraft_landing_candidate(break_eliminated_row=False):
    variables = {}
    for i in (1, 2, 3):
        variables[f"x_A{i}"] = _var(f"x_A{i}", "continuous", 1.0, 10.0 + 2 * i)
        variables[f"e_A{i}"] = _var(f"e_A{i}", "continuous", 0.0, 1000.0)
        variables[f"l_A{i}"] = _var(f"l_A{i}", "continuous", 0.0, 1000.0)
    variables["z_A1_A2"] = _var("z_A1_A2")
    variables["z_A1_A3"] = _var("z_A1_A3")
    variables["z_A2_A3"] = _var("z_A2_A3")
    cons = [
        CanonicalConstraint("c12", {"x_A2": -1.0, "x_A1": 1.0, "z_A1_A2": 1000.0}, -998.0, "<="),
        CanonicalConstraint("c13", {"x_A1": -1.0, "x_A2": 1.0, "z_A1_A2": -1000.0}, 2.0, "<="),
        CanonicalConstraint("c14", {"x_A3": -1.0, "x_A1": 1.0, "z_A1_A3": 1000.0}, -997.0, "<="),
        CanonicalConstraint("c15", {"x_A1": -1.0, "x_A3": 1.0, "z_A1_A3": -1000.0}, 3.0, "<="),
        CanonicalConstraint("c16", {"x_A3": -1.0, "x_A2": 1.0, "z_A2_A3": 1000.0}, -996.0, "<="),
        CanonicalConstraint("c17", {"x_A2": -1.0, "x_A3": 1.0, "z_A2_A3": -1000.0}, 4.0, "<="),
    ]
    if break_eliminated_row:
        cons[0] = CanonicalConstraint("c12", {"x_A2": -1.0, "x_A1": 1.0}, -998.0, "<=")
    return CanonicalIR(
        "AircraftLanding_LLM",
        variables,
        cons,
        "minimize",
        {"e_A1": 5.0, "l_A1": 10.0, "e_A2": 10.0, "l_A2": 20.0, "e_A3": 15.0, "l_A3": 30.0},
    )


def test_complement_elimination_verified_by_constraints():
    ref = _unlinked_aircraft_landing_reference()
    cand = _aircraft_landing_candidate()
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert "ref-elimination" in cert.detection_method
    assert cert.variable_map["x_A1"] == "x1"
    assert cert.variable_map["z_A1_A2"] == "z12"
    assert set(cert.ref_eliminations) == {"z21", "z31", "z32"}
    expr = cert.ref_eliminations["z21"]
    assert expr.coeffs == {"z_A1_A2": -1.0}
    assert expr.constant == pytest.approx(1.0)


def test_elimination_rejected_without_row_evidence():
    ref = _unlinked_aircraft_landing_reference()
    cand = _aircraft_landing_candidate(break_eliminated_row=True)
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is False
    assert cert.ref_eliminations == {}


def test_linked_reference_accepts_single_ordering_binary_via_tautology():
    """A single-z candidate that reproduces the linking row is now verified.

    The reference's ``z_ij + z_ji = 1`` row becomes a tautology after substituting
    ``z_ji = 1 - z_ij``; it imposes no obligation on the candidate, so the lift is
    accepted instead of rejecting the whole certificate (previous behaviour).
    """
    ref = make_aircraft_landing_reference()
    cand = _aircraft_landing_candidate()
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is True
    assert set(cert.ref_eliminations) == {"z21", "z31", "z32"}
    assert "ref-elimination" in cert.detection_method


def test_linked_reference_rejects_candidate_with_broken_separation_row():
    """False-positive guard: a broken separation row must still be rejected."""
    ref = make_aircraft_landing_reference()
    cand = _aircraft_landing_candidate(break_eliminated_row=True)
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is False


def test_projected_ir_pins_eliminated_variable():
    ref = _unlinked_aircraft_landing_reference()
    cand = _aircraft_landing_candidate()
    cert = build_projection_certificate(ref, cand)
    projected = cert.project_ir(cand, ref)
    names = {c.name for c in projected.constraints}
    assert {"_elim_z21", "_elim_z31", "_elim_z32"} <= names


# ── Existential projection for candidate-only auxiliary variables ───────────

def _slack_candidate():
    """Reference ``x + y <= 10`` vs candidate with slack ``s >= 0``.

    Directly names the reference coordinates so the only structural difference is
    the extra auxiliary ``s`` defined by ``x + y + s = 10`` (never in the
    objective). It must be projected out existentially, not treated as unmapped.
    """
    ref = CanonicalIR(
        "slack_ref",
        {"x": _var("x", "continuous", 0.0, 20.0),
         "y": _var("y", "continuous", 0.0, 20.0)},
        [CanonicalConstraint("cap", {"x": 1.0, "y": 1.0}, -10.0, "<=")],
        "minimize",
        {"x": 1.0, "y": 1.0},
    )
    cand = CanonicalIR(
        "slack_cand",
        {"x": _var("x", "continuous", 0.0, 20.0),
         "y": _var("y", "continuous", 0.0, 20.0),
         "s": _var("s", "continuous", 0.0, 20.0)},
        [CanonicalConstraint("cap_slack", {"x": 1.0, "y": 1.0, "s": 1.0}, -10.0, "<="),
         CanonicalConstraint("s_nonneg", {"s": -1.0}, 0.0, "<=")],
        "minimize",
        {"x": 1.0, "y": 1.0},
    )
    return ref, cand


def test_candidate_only_slack_variable_is_projected():
    ref, cand = _slack_candidate()
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is True
    assert cert.existential_variables.get("s") is not None
    assert "existential-projection" in cert.detection_method


def test_auxiliary_in_objective_is_not_projected():
    """A candidate-only variable that enters the objective must NOT be projected."""
    ref, cand = _slack_candidate()
    cand.objective_coeffs = {"x": 1.0, "y": 1.0, "s": 5.0}
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is False


# ── Module 1 §5.4: declared unit conversion ─────────────────────────────────

def _single_var_ir(problem, name, unit="", vtype="continuous", index_sets=None):
    return CanonicalIR(
        problem,
        {name: _var(name, vtype, 0.0, 10.0, unit=unit, index_sets=index_sets)},
        [CanonicalConstraint("c", {name: 1.0}, -5.0, "<=")],
        "minimize",
        {name: 1.0},
    )


def test_declared_unit_conversion_scales_projection():
    ref = _single_var_ir("Ref", "x", unit="tonne")
    cand = _single_var_ir("Cand", "x", unit="kg")
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert "unit-conversion" in cert.detection_method
    # 1 tonne = 1000 kg  =>  value_kg = 1000 * value_tonne
    assert cert.affine_substitutions["x"].coeffs == {"x": 1000.0}
    assert cert.is_identity is False
    row = next(c for c in cert.project_ir(cand, ref).constraints if c.name == "c")
    assert row.coeffs["x"] == pytest.approx(1000.0)
    assert row.constant == pytest.approx(-5.0)


def test_unit_conversion_rejected_for_binary_domain():
    ref = _single_var_ir("Ref", "x", unit="tonne", vtype="binary")
    cand = _single_var_ir("Cand", "x", unit="kg", vtype="binary")
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is False
    assert "unit-domain-change" in cert.unsupported_features


def test_incompatible_declared_units_rejected():
    ref = _single_var_ir("Ref", "x", unit="kg")
    cand = _single_var_ir("Cand", "x", unit="min")
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is False
    assert "unit-mismatch" in cert.unsupported_features


# ── Module 1 §5.4: index-set cardinality on name-proposed matches ────────────

def test_index_cardinality_mismatch_rejects_name_match():
    ref = _single_var_ir("Ref", "x11", index_sets=["A1", "R1"])
    cand = _single_var_ir("Cand", "x_A1_R1", index_sets=["A1", "A2"])
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified is False
    assert "index-cardinality-mismatch" in cert.unsupported_features


def test_matching_index_sets_keep_name_match():
    ref = _single_var_ir("Ref", "x11", index_sets=["A1", "R1"])
    cand = _single_var_ir("Cand", "x_A1_R1", index_sets=["A1", "R1"])
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert "index-signature" in cert.detection_method


# ── Module 1 §5.4: normalized-name, semantic-role and fingerprint sources ────

def test_normalized_name_maps_underscore_variant():
    ref = _single_var_ir("Ref", "x11")
    cand = _single_var_ir("Cand", "x_1_1")
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert cert.variable_map["x_1_1"] == "x11"
    assert "normalized-name" in cert.detection_method
    assert any("assumption" in w for w in cert.warnings)


def test_trailing_separator_name_is_not_mapped():
    # 'x_' -> 'x' is exactly the fuzzy match the evidence tests forbid; neither
    # the normalized-name guard nor the fingerprint fallback may re-admit it.
    ref = _single_var_ir("Ref", "x")
    cand = _single_var_ir("Cand", "x_")
    assert build_projection_certificate(ref, cand).is_verified is False


def test_semantic_role_maps_arbitrary_name():
    ref = _single_var_ir("Ref", "a")
    ref.variables["a"].semantic_role = "select_item1"
    cand = _single_var_ir("Cand", "w")
    cand.variables["w"].semantic_role = "select_item1"
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert cert.variable_map["w"] == "a"
    assert "semantic-role" in cert.detection_method


def test_structural_fingerprint_recovers_arbitrary_rename():
    ref = _single_var_ir("Ref", "InvestmentCondos")
    cand = _single_var_ir("Cand", "w")
    cert = build_projection_certificate(ref, cand)
    assert cert.is_verified
    assert cert.variable_map["w"] == "InvestmentCondos"
    assert "structural-fingerprint" in cert.detection_method
    assert any("assumption" in w for w in cert.warnings)


def test_fingerprint_requires_uniqueness_on_both_sides():
    ref = CanonicalIR(
        "Ref",
        {"a": _var("a", "continuous", 0.0, 10.0), "b": _var("b", "continuous", 0.0, 10.0)},
        [], "minimize", {"a": 1.0, "b": 1.0})
    cand = CanonicalIR(
        "Cand",
        {"w": _var("w", "continuous", 0.0, 10.0), "v": _var("v", "continuous", 0.0, 10.0)},
        [], "minimize", {"w": 1.0, "v": 1.0})
    assert build_projection_certificate(ref, cand).is_verified is False
