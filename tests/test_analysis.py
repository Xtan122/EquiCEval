"""
Unit tests for Robust Statistical Analysis Engine (src/benchmark/analysis.py).
"""

import pytest
import numpy as np
from scipy import stats
from src.benchmark.analysis import (
    RobustStatsCalculator,
    leave_one_family_out,
    leave_one_outlier_out,
    mixed_effects_model,
    multiple_comparison_correction,
    compute_auroc_auprc,
    compute_localization_accuracy,
    ranking_stability_ci,
    cost_profiling_by_size,
)
from src.benchmark.visualization import plot_scatter_delta_vs_gap


def test_compute_fpr_and_recall():
    # 5 equivalent records, 5 mutant records
    is_equivalent = [True, True, True, True, True, False, False, False, False, False]
    is_mutant = [not x for x in is_equivalent]

    # Baseline predicted faulty on 2 equivalent (FPs) and 3 mutants (TPs)
    preds_baseline_faulty = [True, True, False, False, False, True, True, True, False, False]

    fpr_base = RobustStatsCalculator.compute_fpr(preds_baseline_faulty, is_equivalent)
    rec_base = RobustStatsCalculator.compute_recall(preds_baseline_faulty, is_mutant)

    assert pytest.approx(fpr_base, 1e-4) == 2 / 5  # 0.40
    assert pytest.approx(rec_base, 1e-4) == 3 / 5  # 0.60


def test_clustered_bootstrap_ci():
    values = [0.1, 0.12, 0.09, 0.8, 0.85, 0.79]
    labels = ["Knapsack", "Knapsack", "Knapsack", "Diet", "Diet", "Diet"]

    ci_lower, ci_upper = RobustStatsCalculator.clustered_bootstrap_ci(
        data_values=values,
        cluster_labels=labels,
        num_bootstraps=500,
        ci_level=0.95,
        seed=42
    )

    assert ci_lower <= ci_upper
    assert 0.0 <= ci_lower <= 1.0
    assert 0.0 <= ci_upper <= 1.0


def test_rank_correlations():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]

    rho, tau = RobustStatsCalculator.compute_rank_correlations(x, y)

    assert pytest.approx(rho, 1e-4) == 1.0
    assert pytest.approx(tau, 1e-4) == 1.0


def _spearman_corr(rows):
    gaps = [r["gap"] for r in rows]
    metrics = [r["metric"] for r in rows]
    rho, _ = stats.spearmanr(gaps, metrics)
    return rho


def _synthetic_rows():
    rows = [
        {"family": f, "problem": f"{f}{j}", "metric": m, "gap": g}
        for f, gs, ms in (
            ("A", [0.1, 0.2, 0.3, 0.4], [0.9, 0.8, 0.7, 0.6]),
            ("B", [0.5, 0.6, 0.7, 0.8], [0.5, 0.4, 0.3, 0.2]),
            ("C", [0.55, 0.65, 0.75, 0.85], [0.6, 0.5, 0.4, 0.3]),
        )
        for j, (g, m) in enumerate(zip(gs, ms))
    ]
    return rows


def test_leave_one_family_out():
    rows = _synthetic_rows()
    result = leave_one_family_out(_spearman_corr, rows)
    assert set(result.keys()) == {"A", "B", "C"}
    full = _spearman_corr(rows)
    assert any(abs(v - full) > 1e-9 for v in result.values())


def test_leave_one_outlier_out():
    rows = _synthetic_rows()
    result = leave_one_outlier_out(_spearman_corr, rows)
    assert len(result) == len(rows)
    assert set(result.keys()) == set(range(len(rows)))


def test_mixed_effects_model():
    pytest.importorskip("statsmodels")
    pd = pytest.importorskip("pandas")
    rng = np.random.RandomState(42)
    offsets = {"A": 0.6, "B": 0.0, "C": -0.6}
    records = []
    for fam, offset in offsets.items():
        for _ in range(12):
            records.append({"metric": offset + rng.normal(0, 0.15), "family": fam})
    df = pd.DataFrame(records)
    result = mixed_effects_model(df, metric_col="metric", family_col="family")
    assert "family_var" in result
    assert "intercept" in result
    assert result["n_groups"] == 3
    assert result["n_obs"] == 36
    assert result["family_var"] >= 0.0


def test_multiple_comparison():
    pvalues = [0.001, 0.03, 0.05, 0.2, 0.8]
    for method in ("bonferroni", "holm", "bh"):
        corrected = multiple_comparison_correction(pvalues, method=method)
        assert len(corrected) == len(pvalues)
        assert all(0.0 <= p <= 1.0 for p in corrected)
        assert corrected[0] >= pvalues[0]
    with pytest.raises(ValueError):
        multiple_comparison_correction(pvalues, method="unknown")


def test_auroc_auprc():
    pytest.importorskip("sklearn")
    y_true = [0, 1, 1, 0, 1, 0, 1, 0]
    scores = [0.1, 0.8, 0.6, 0.2, 0.9, 0.05, 0.7, 0.3]
    auroc, auprc = compute_auroc_auprc(y_true, scores)
    assert 0.0 <= auroc <= 1.0
    assert 0.0 <= auprc <= 1.0
    a2, b2 = compute_auroc_auprc([1, 1, 1, 1], [0.1, 0.2, 0.3, 0.4])
    assert np.isnan(a2) and np.isnan(b2)


def test_localization_accuracy():
    assert compute_localization_accuracy(["c2"], ["c2"]) == 1.0
    assert compute_localization_accuracy(["c2"], ["c1"]) == 0.0
    per_record = compute_localization_accuracy(
        [["c2"], ["c1"], ["c3"]], [["c2"], ["c2"], ["c3"]]
    )
    assert pytest.approx(per_record, 1e-6) == 2 / 3


def test_ranking_stability_ci():
    scores_by_model = {
        "A": [0.9, 0.8, 0.85],
        "B": [0.7, 0.6, 0.75],
        "C": [0.5, 0.55, 0.45],
    }
    result = ranking_stability_ci(scores_by_model, n_boot=50, seed=42)
    assert set(result.keys()) == {"A", "B", "C"}
    for model, ci in result.items():
        assert set(ci.keys()) == {"mean_rank", "ci_low", "ci_high"}
        assert isinstance(ci["mean_rank"], float)
        assert ci["ci_low"] <= ci["ci_high"]
    assert result["A"]["mean_rank"] == 1.0


def test_cost_profiling():
    entries = [(5, 2), (8, 3), (20, 10), (30, 12), (70, 20), (90, 25), (150, 40), (400, 60)]
    result = cost_profiling_by_size(entries)
    assert set(result.keys()) == {"10", "50", "100", "500"}
    assert result["10"]["n"] == 2
    assert result["10"]["mean_calls"] == 2.5
    assert result["10"]["median_calls"] == 2.5
    assert result["50"]["n"] == 2
    assert result["100"]["n"] == 2
    assert result["500"]["n"] == 2
    dict_entries = [{"size": 5, "calls": 2}, {"size": 30, "calls": 10}]
    result2 = cost_profiling_by_size(dict_entries)
    assert result2["10"]["n"] == 1
    assert result2["50"]["n"] == 1


def test_scatter_plot_generation(tmp_path):
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [0.9, 0.7, 0.5, 0.4, 0.2]
    out_path = plot_scatter_delta_vs_gap(x, y, out_path=tmp_path / "scatter.png")
    assert out_path.exists()
    assert out_path.stat().st_size > 0
