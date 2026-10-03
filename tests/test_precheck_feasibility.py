"""Module 0 feasibility must accept solver points that sit on a scaled row.

Regression: a semantics-preserving ``scaled`` transformation multiplies a row's
coefficients and constant by the same positive float. The exact-decimal spelling
of the products then differs from the constant by a few ulp (e.g. 9e-14), so the
solver's optimal vertex was rejected by the strict checker and the whole pair was
reported as ``s_solve=TIMEOUT`` (unresolved). The checker must tolerate that
representation noise without ever accepting a semantic violation.
"""
from src.equiceval.canonical_ir import (
    CanonicalIR,
    CanonicalVariable as V,
    CanonicalConstraint as C,
)
from src.equiceval.evidence import point_is_feasible
from src.equiceval.precheck import ModelPreChecker, FeasStatus, SolveStatus


def scaled_aircraft_assignment():
    """AircraftAssignment candidate scaled by 4.742813257457667 (see benchmark)."""
    names = ["x_1_1", "x_1_2", "x_2_1", "x_2_2", "x_3_1", "x_3_2"]
    variables = {n: V(n, "binary", 0, 1) for n in names}
    constraints = [
        C("avail_A1", {"x_1_1": 1.0, "x_1_2": 1.0}, -2.0, "<="),
        C("avail_A2", {"x_2_1": 1.0, "x_2_2": 1.0}, -3.0, "<="),
        C("avail_A3_scaled",
          {"x_3_1": 4.742813257457667, "x_3_2": 4.742813257457667},
          -4.742813257457667, "<="),
        C("demand_R1_scaled",
          {"x_1_1": -124.91861506571105, "x_2_1": -149.90233807885326,
           "x_3_1": -174.88606109199546},
          249.8372301314221, "<="),
        C("demand_R2_scaled",
          {"x_1_2": -283.97380276678916, "x_2_2": -324.54148887633045,
           "x_3_2": -365.1091749858718},
          608.5152916431197, "<="),
    ]
    return CanonicalIR("scaled_aircraft_assignment", variables, constraints,
                       "minimize", {n: 1.0 for n in names})


BOUNDARY_POINT = {"x_1_1": 1.0, "x_1_2": 1.0, "x_2_1": 1.0,
                  "x_2_2": 1.0, "x_3_1": 0.0, "x_3_2": 0.0}


def test_scaled_boundary_point_is_feasible_within_tolerance():
    ir = scaled_aircraft_assignment()
    assert point_is_feasible(ir, BOUNDARY_POINT) is True


def test_scaled_boundary_point_is_rejected_in_strict_mode():
    ir = scaled_aircraft_assignment()
    assert point_is_feasible(ir, BOUNDARY_POINT, tolerance=0) is False


def test_check_feasibility_accepts_scaled_boundary():
    ir = scaled_aircraft_assignment()
    checker = ModelPreChecker(solver_time_limit=1.0)
    status, _, _ = checker.check_feasibility(ir)
    assert status == FeasStatus.FEASIBLE


def test_scaled_boundary_is_not_reported_as_timeout():
    ir = scaled_aircraft_assignment()
    checker = ModelPreChecker(solver_time_limit=1.0)
    _, cand = checker.run(None, ir, check_reference=False)
    assert cand.s_solve != SolveStatus.TIMEOUT


def test_gross_violation_is_still_rejected():
    ir = scaled_aircraft_assignment()
    all_ones = {n: 1.0 for n in ir.variables}
    assert point_is_feasible(ir, all_ones) is False


def test_non_integer_point_is_still_rejected():
    ir = scaled_aircraft_assignment()
    fractional = dict(BOUNDARY_POINT, x_1_1=0.5)
    assert point_is_feasible(ir, fractional) is False
