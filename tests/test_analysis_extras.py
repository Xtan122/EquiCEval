"""Analysis extras: cost-by-size buckets, leave-one-family-out, Bonferroni level."""
from src.benchmark.analysis import (
    cost_profiling_by_size,
    leave_one_family_out_metrics,
    bonferroni_level,
)


def test_bonferroni_level_widens_with_more_tests():
    assert bonferroni_level(1) == 0.95
    assert bonferroni_level(5) > bonferroni_level(1)
    assert bonferroni_level(5) == 0.99
    assert bonferroni_level(0) == 0.95


def test_leave_one_family_out_metrics_recompute_without_family():
    labels = [True, False, False, True]
    verdicts = ["certified", "disproved", "unresolved", "certified"]
    families = ["Knapsack", "Knapsack", "Diet", "Diet"]
    out = leave_one_family_out_metrics(labels, verdicts, families)
    assert set(out) == {"Knapsack", "Diet"}
    # without Diet, one negative (disproved) remains -> recall 1.0
    assert out["Diet"]["error_recall"] == 1.0
    # without Knapsack, one negative (unresolved) remains -> recall 0.0
    assert out["Knapsack"]["error_recall"] == 0.0


def test_cost_profiling_by_size_buckets():
    buckets = cost_profiling_by_size([
        {"size": 5, "solver_calls": 10},
        {"size": 60, "solver_calls": 20},
        {"size": 600, "solver_calls": 30},
    ])
    assert buckets
    means = [v["mean_calls"] for v in buckets.values() if v["n"]]
    assert means == sorted(means)
    assert sum(v["n"] for v in buckets.values()) == 3
