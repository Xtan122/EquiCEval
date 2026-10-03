"""
Phase 1 — Solver Backend Upgrade tests.

Covers: HiGHS for LP, SCIP for MILP, new SolverResult fields
(node_count, mip_gap, best_bound), incumbent extraction on timeout,
auto backend selection, and warm-start caching.
"""

import pytest

from src.utils.solver_wrapper import SolverResult, UnifiedSolver


def _simple_lp():
    """max x + y s.t. x + y <= 1, x, y >= 0  →  optimal objective 1.0"""
    var_specs = {"x": ("continuous", 0.0, float("inf")), "y": ("continuous", 0.0, float("inf"))}
    obj_coeffs = {"x": 1.0, "y": 1.0}
    constraints = [({"x": 1.0, "y": 1.0}, "<=", 1.0)]
    return var_specs, obj_coeffs, constraints


def _simple_milp():
    """Knapsack: max 60x1 + 100x2 + 120x3 s.t. 10x1 + 20x2 + 30x3 <= 50, binary  →  220.0"""
    var_specs = {
        "x_1": ("binary", 0.0, 1.0),
        "x_2": ("binary", 0.0, 1.0),
        "x_3": ("binary", 0.0, 1.0),
    }
    obj_coeffs = {"x_1": 60.0, "x_2": 100.0, "x_3": 120.0}
    constraints = [({"x_1": 10.0, "x_2": 20.0, "x_3": 30.0}, "<=", 50.0)]
    return var_specs, obj_coeffs, constraints


def test_solve_lp_highs():
    """Simple LP → Optimal, HiGHS backend, all new fields populated."""
    var_specs, obj_coeffs, constraints = _simple_lp()
    res = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res.status == "Optimal"
    assert res.solver == "HiGHS"
    assert res.objective_value == pytest.approx(1.0, abs=1e-6)
    assert res.node_count == 0
    assert res.mip_gap is None or res.mip_gap <= 1e-6
    assert res.best_bound is not None and res.best_bound == pytest.approx(1.0, abs=1e-6)


def test_solve_milp_scip():
    """Small MILP → Optimal, SCIP backend, node_count/mip_gap/best_bound populated."""
    var_specs, obj_coeffs, constraints = _simple_milp()
    res = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res.status == "Optimal"
    assert res.solver == "SCIP"
    assert res.objective_value == pytest.approx(220.0, abs=1e-4)
    assert res.variable_values["x_2"] == pytest.approx(1.0, abs=1e-4)
    assert res.variable_values["x_3"] == pytest.approx(1.0, abs=1e-4)
    assert res.node_count >= 0
    assert res.mip_gap is not None and res.mip_gap <= 1e-4
    assert res.best_bound is not None and res.best_bound == pytest.approx(220.0, abs=1e-3)


def test_solve_timeout_incumbent():
    """Tight time limit → Timeout with incumbent + feasibility certificate."""
    import random
    random.seed(7)
    n = 60
    var_specs = {f"x{i}": ("binary", 0.0, 1.0) for i in range(n)}
    obj_coeffs = {f"x{i}": float(random.randint(1, 20)) for i in range(n)}
    constraints = []
    for _ in range(10):
        idxs = random.sample(range(n), 4)
        coeffs = {f"x{i}": 1.0 for i in idxs}
        constraints.append((coeffs, "<=", float(random.randint(1, 3))))

    incumbent = {f"x{i}": 0.0 for i in range(n)}

    res = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
        time_limit=0.0001,
        warm_start=incumbent,
    )
    assert res.status == "Timeout"
    assert res.solver == "SCIP"
    assert res.objective_value is not None
    assert res.incumbent_feasible is True
    assert res.node_count >= 0
    assert res.mip_gap is not None


def test_solve_infeasible():
    """Contradictory constraints → Infeasible."""
    var_specs = {"x": ("continuous", 0.0, float("inf")), "y": ("continuous", 0.0, float("inf"))}
    obj_coeffs = {"x": 1.0, "y": 1.0}
    constraints = [
        ({"x": 1.0, "y": 1.0}, "<=", 1.0),
        ({"x": 1.0, "y": 1.0}, ">=", 2.0),
    ]
    res = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res.status == "Infeasible"
    assert res.objective_value is None


def test_solve_unbounded():
    """No upper bound, max objective → Unbounded."""
    var_specs = {"x": ("continuous", 0.0, float("inf")), "y": ("continuous", 0.0, float("inf"))}
    obj_coeffs = {"x": 1.0, "y": 1.0}
    constraints = [({"x": 1.0, "y": 1.0}, ">=", 1.0)]
    res = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res.status == "Unbounded"
    assert res.objective_value is None


def test_solver_auto_selection(monkeypatch):
    """LP → HiGHS, MILP → SCIP, fallback → CBC."""
    lp_vars, lp_obj, lp_cons = _simple_lp()
    milp_vars, milp_obj, milp_cons = _simple_milp()

    res = UnifiedSolver.solve(lp_vars, lp_obj, "maximize", lp_cons)
    assert res.solver == "HiGHS"

    res = UnifiedSolver.solve(milp_vars, milp_obj, "maximize", milp_cons)
    assert res.solver == "SCIP"

    UnifiedSolver._AVAILABLE = {"highs": False, "scip": False}
    try:
        res = UnifiedSolver.solve(lp_vars, lp_obj, "maximize", lp_cons)
        assert res.solver == "CBC"
        assert res.status == "Optimal"
    finally:
        UnifiedSolver._AVAILABLE = None


def test_solve_pulp_model_backward_compat():
    """Old entry point still works and returns the new fields."""
    var_specs, obj_coeffs, constraints = _simple_lp()
    res = UnifiedSolver.solve_pulp_model(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res.status == "Optimal"
    assert isinstance(res, SolverResult)
    assert hasattr(res, "node_count")
    assert hasattr(res, "mip_gap")
    assert hasattr(res, "best_bound")


def test_warm_start():
    """Second sequential solve of the same model uses the warm-start cache."""
    UnifiedSolver._warm_start_cache.clear()
    var_specs, obj_coeffs, constraints = _simple_lp()

    res1 = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res1.status == "Optimal"
    assert res1.warm_start_used is False

    res2 = UnifiedSolver.solve(
        var_specs=var_specs,
        objective_coeffs=obj_coeffs,
        objective_sense="maximize",
        constraints_list=constraints,
    )
    assert res2.status == "Optimal"
    assert res2.warm_start_used is True
    assert res2.objective_value == pytest.approx(1.0, abs=1e-6)
