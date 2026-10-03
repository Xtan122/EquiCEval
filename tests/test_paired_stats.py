"""Clustered-bootstrap CI for paired differences between two raters.

Comparing two tools on the same pairs requires a CI for
``mean(A) - mean(B)``, resampling clusters (problem families), not separate CIs
for each tool (paper §8.4). Single-cluster data cannot be resampled and must
report no interval while still reporting the observed difference.
"""
from src.benchmark.analysis import paired_difference_ci


def test_perfect_separation():
    a = [1.0, 1.0, 1.0, 1.0]
    b = [0.0, 0.0, 0.0, 0.0]
    clusters = ["f1", "f1", "f2", "f2"]
    result = paired_difference_ci(a, b, clusters, num_bootstraps=200, seed=42)
    assert result["observed"] == 1.0
    assert result["ci_lower"] == 1.0
    assert result["ci_upper"] == 1.0


def test_identical_raters_give_zero():
    a = [1.0, 0.0, 1.0, 0.0]
    result = paired_difference_ci(a, list(a), ["f1", "f1", "f2", "f2"],
                                  num_bootstraps=200, seed=42)
    assert result["observed"] == 0.0
    assert result["ci_lower"] == 0.0
    assert result["ci_upper"] == 0.0


def test_single_cluster_has_no_interval():
    result = paired_difference_ci([1.0, 0.0], [0.0, 0.0], ["f1", "f1"],
                                  num_bootstraps=200, seed=42)
    assert result["observed"] == 0.5
    assert result["ci_lower"] is None
    assert result["ci_upper"] is None


def test_mixed_differences_bracket_observed():
    a = [1.0, 0.0, 1.0, 0.0]
    b = [0.0, 1.0, 0.0, 0.0]
    result = paired_difference_ci(a, b, ["f1", "f2", "f3", "f4"],
                                  num_bootstraps=500, seed=42)
    assert result["observed"] == 0.25
    assert result["ci_lower"] <= result["observed"] <= result["ci_upper"]
