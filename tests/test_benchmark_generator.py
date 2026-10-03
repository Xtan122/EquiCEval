"""
Unit tests for EquiCEval Benchmark Generator:
- Semantics-preserving transformations
- Controlled mutation operators & solver verification
- BenchmarkSuite generation & GoldRecord schema compliance
"""

import pytest
from src.benchmark.ground_truth import PROBLEMS_REGISTRY
from src.benchmark.transformations import SemanticsPreservingTransformer
from src.benchmark.mutator import ControlledMutator
from src.benchmark.generator import BenchmarkGenerator
from src.benchmark.schema import ContaminationStratum, GoldRecord
from src.benchmark.reference_ir import get_reference_ir
from src.utils.solver_wrapper import UnifiedSolver


def _solve_obj(ir):
    """Solves an IR and returns its optimal objective value (or None)."""
    var_specs = {
        vname: (v.var_type, v.lower_bound, v.upper_bound)
        for vname, v in ir.variables.items()
    }
    cons = [(c.coeffs, c.sense, -c.constant) for c in ir.constraints]
    res = UnifiedSolver.solve_pulp_model(
        var_specs=var_specs,
        objective_coeffs=ir.objective_coeffs,
        objective_sense=ir.objective_sense,
        constraints_list=cons,
    )
    return res.objective_value if res.status == "Optimal" else None



def test_positive_scaling_transformation():
    generator = BenchmarkGenerator(seed=42)
    ref_ir = generator.problem_to_canonical_ir(PROBLEMS_REGISTRY["Knapsack"])
    transformer = SemanticsPreservingTransformer(seed=42)

    scaled_ir = transformer.apply_positive_scaling(ref_ir, scale_range=(2.0, 3.0))

    assert len(scaled_ir.constraints) == len(ref_ir.constraints)
    assert scaled_ir.constraints[0].sense == ref_ir.constraints[0].sense


def test_convert_bounds_to_constraints():
    generator = BenchmarkGenerator(seed=42)
    ref_ir = generator.problem_to_canonical_ir(PROBLEMS_REGISTRY["Diet"])
    transformer = SemanticsPreservingTransformer(seed=42)

    bounded_ir = transformer.convert_bounds_to_constraints(ref_ir)

    # Upper bound constraints should be added for x_apple <= 10 and x_banana <= 10
    assert len(bounded_ir.constraints) > len(ref_ir.constraints)


def test_mutator_omit_constraint():
    generator = BenchmarkGenerator(seed=42)
    ref_ir = generator.problem_to_canonical_ir(PROBLEMS_REGISTRY["Knapsack"])
    mutator = ControlledMutator(seed=42)

    mutant_ir, label = mutator.mutate_omit_constraint(ref_ir)

    assert len(mutant_ir.constraints) == len(ref_ir.constraints) - 1
    assert "omitted" in label

    # Solver should verify semantics changed
    is_valid = mutator.verify_mutant_semantics_changed(ref_ir, mutant_ir)
    assert is_valid is True


def test_benchmark_generator_build_pilot_suite():
    generator = BenchmarkGenerator(seed=42)
    suite = generator.build_full_suite(eq_count=20, mut_count=30)

    summary = suite.summary()
    assert summary["equivalent_count"] == 20
    assert summary["mutant_count"] == 30
    assert summary["total_count"] == 50

    # Verify every record is solver-certified
    for rec in suite.equivalent_records:
        assert rec.is_semantically_equivalent is True
        assert rec.solver_certified is True
        assert rec.contamination_stratum == ContaminationStratum.PUBLIC_BASE

    for rec in suite.mutant_records:
        assert rec.is_semantically_equivalent is False
        assert rec.solver_certified is True
        assert rec.mutation_label is not None


# ─── Phase 8: extra transformations ───────────────────────────────────────────

def test_aggregate_decompose():
    """Decomposing an equality constraint stays equivalent (same optimal value)."""
    ref = get_reference_ir("AircraftLanding")
    assert any(c.sense == "==" for c in ref.constraints)
    transformer = SemanticsPreservingTransformer(seed=42)
    new_ir = transformer.apply_aggregate_decompose(ref)
    assert len(new_ir.constraints) > len(ref.constraints)
    assert _solve_obj(new_ir) == pytest.approx(_solve_obj(ref), abs=1e-3)


def test_auxiliary_variable():
    """Adding a slack/auxiliary variable with a projection stays equivalent."""
    ref = get_reference_ir("Diet")
    transformer = SemanticsPreservingTransformer(seed=42)
    new_ir = transformer.apply_auxiliary_variable(ref)
    assert len(new_ir.variables) == len(ref.variables) + 1
    assert len(new_ir.constraints) == len(ref.constraints) + 1
    assert _solve_obj(new_ir) == pytest.approx(_solve_obj(ref), abs=1e-3)


def test_move_constant():
    """Moving a constant between LHS/RHS stays equivalent."""
    ref = get_reference_ir("Diet")
    transformer = SemanticsPreservingTransformer(seed=42)
    new_ir = transformer.apply_move_constant(ref)
    assert new_ir is not ref
    assert _solve_obj(new_ir) == pytest.approx(_solve_obj(ref), abs=1e-3)


def test_coverage_matrix():
    """Coverage matrix covers all 7 transformation types across all 4 problems."""
    transformer = SemanticsPreservingTransformer(seed=42)
    matrix = transformer.generate_coverage_matrix()
    trans_types = {
        "positive-scaling", "bound-to-constraint", "implied-redundant",
        "variable-renaming", "aggregate-decompose", "auxiliary-variable",
        "move-constant",
    }
    assert set(matrix.keys()) == {"Knapsack", "AircraftAssignment", "Diet", "AircraftLanding"}
    for problem, types in matrix.items():
        assert trans_types.issubset(set(types)), f"{problem} missing transformation types"


# ─── Phase 8: extra mutations ────────────────────────────────────────────────

def test_constant_error():
    """RHS constant perturbed → solver confirms semantics changed."""
    ref = get_reference_ir("Knapsack")
    mutator = ControlledMutator(seed=42)
    mutant, label = mutator.mutate_constant_error(ref)
    assert "constant" in label.lower()
    assert mutator.verify_mutant_semantics_changed(ref, mutant) is True


def test_wrong_domain():
    """continuous→integer domain change → solver confirms different feasible set."""
    ref = get_reference_ir("Diet")
    mutator = ControlledMutator(seed=42)
    mutant, label = mutator.mutate_wrong_domain(ref)
    assert "domain" in label.lower()
    assert mutator.verify_mutant_semantics_changed(ref, mutant) is True


def test_missing_index_range():
    """Index range truncated (variables dropped) → solver confirms different."""
    ref = get_reference_ir("AircraftAssignment")
    mutator = ControlledMutator(seed=42)
    mutant, label = mutator.mutate_missing_index_range(ref)
    assert "index" in label.lower()
    assert len(mutant.variables) < len(ref.variables)
    assert mutator.verify_mutant_semantics_changed(ref, mutant) is True


def test_broken_big_m():
    """Big-M link broken → solver confirms different feasible set."""
    ref = get_reference_ir("AircraftLanding")
    mutator = ControlledMutator(seed=42)
    mutant, label = mutator.mutate_broken_big_m(ref)
    assert "big" in label.lower()
    assert mutator.verify_mutant_semantics_changed(ref, mutant) is True


def test_mutation_survival_report():
    """Survival report counts survivors/exclusions and reports the rate."""
    from src.benchmark.mutator import generate_survival_report

    results = [
        ("m1", True, None),
        ("m2", False, "infeasible"),
        ("m3", False, "equivalent"),
        ("m4", True, None),
    ]
    report = generate_survival_report(results)
    assert report.n_generated == 4
    assert report.n_survived == 2
    assert report.n_excluded == 2
    assert report.survival_rate == pytest.approx(0.5)
    assert report.exclusion_reasons == {"infeasible": 1, "equivalent": 1}


# ─── Phase 8: Gold Record fields ─────────────────────────────────────────────

def test_gold_record_full_fields():
    """GoldRecord carries all paper-required audit fields."""
    ref = get_reference_ir("Knapsack")
    rec = GoldRecord(
        record_id="r1", base_problem_name="Knapsack",
        reference_ir=ref, candidate_ir=ref, record_type="equivalent",
        is_semantically_equivalent=True,
        projection_status="verified",
        matching_evidence="exact",
        solver_witness={"x2": 1.0, "x3": 1.0},
        family_label="Knapsack",
    )
    d = rec.to_dict()
    assert d["projection_status"] == "verified"
    assert d["matching_evidence"] == "exact"
    assert d["solver_witness"] == {"x2": 1.0, "x3": 1.0}
    assert d["family_label"] == "Knapsack"
    assert d["exclusion_reason"] == ""


def test_gold_record_exclusion_reason():
    """Excluded record carries a reason code."""
    ref = get_reference_ir("Knapsack")
    rec = GoldRecord(
        record_id="r2", base_problem_name="Knapsack",
        reference_ir=ref, candidate_ir=ref, record_type="mutant",
        is_semantically_equivalent=False,
        exclusion_reason="solver_certification_failed",
    )
    assert rec.exclusion_reason == "solver_certification_failed"
    assert rec.to_dict()["exclusion_reason"] == "solver_certification_failed"
