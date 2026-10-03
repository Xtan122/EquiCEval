"""Family-level splits prevent leakage: all variants of one family stay together.

Paper §7.1: a renamed variant must not sit in the test split while its original
selects thresholds. The split is deterministic and total.
"""
import pytest

from src.benchmark.splits import family_split, split_summary


def _records():
    recs = []
    for fam, n in (("Knapsack", 2), ("Diet", 3), ("AircraftLanding", 1)):
        for i in range(n):
            recs.append({"record_id": f"{fam}_{i}", "base_problem_name": fam})
    return recs


def test_family_split_keeps_families_together():
    split = family_split(_records(), test_families=["Diet"])
    assert split["Diet_0"] == split["Diet_1"] == split["Diet_2"] == "test"
    assert split["Knapsack_0"] == split["Knapsack_1"] == "selection"
    assert split["AircraftLanding_0"] == "selection"


def test_family_split_is_total_and_unknown_families_default_selection():
    recs = _records()
    split = family_split(recs, test_families=["Unknown"])
    assert set(split) == {r["record_id"] for r in recs}
    assert set(split.values()) == {"selection"}


def test_split_summary_reports_counts_per_family():
    split = family_split(_records(), test_families=["Diet", "AircraftLanding"])
    summary = split_summary(_records(), split)
    assert summary["test"]["Diet"] == 3
    assert summary["selection"]["Knapsack"] == 2
    assert summary["test"]["AircraftLanding"] == 1


def test_empty_test_families_is_all_selection():
    split = family_split(_records(), test_families=[])
    assert set(split.values()) == {"selection"}
