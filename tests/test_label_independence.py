"""Label independence guard (AGENTS hard invariant #3).

The reference labels used to grade EquiCEval must be produced *independently* of
EquiCEval: the relabel oracle may reuse the IR datatypes and contract-name
constants, but it must never import or execute the M0-M5 evaluation pipeline
(`evaluator`, `matching`, `directed_query`, `behavioral_discrepancy`,
`objective_discrepancy`, `precheck`, `evidence`, `metrics`) nor the runner
`experiments.run_verified_evaluation`, which would make the labels circular.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORACLE_FILES = [
    ROOT / "src" / "benchmark" / "independent_oracle.py",
]
FORBIDDEN_EQUICEVAL_MODULES = (
    "evaluator",
    "matching",
    "directed_query",
    "behavioral_discrepancy",
    "objective_discrepancy",
    "precheck",
    "evidence",
    "metrics",
)
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z0-9_\.]+)", re.MULTILINE)


def _imports(path: Path) -> set[str]:
    return set(IMPORT_RE.findall(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", ORACLE_FILES, ids=lambda p: p.name)
def test_oracle_does_not_import_equiceval_pipeline(path):
    forbidden = {
        f"src.equiceval.{name}" for name in FORBIDDEN_EQUICEVAL_MODULES
    } | {"experiments.run_verified_evaluation"}
    found = {imp for imp in _imports(path) if imp in forbidden
             or any(imp.startswith(f"{f}.") for f in forbidden)}
    assert not found, f"{path.name} imports EquiCEval pipeline: {sorted(found)}"


def test_oracle_source_has_no_engine_entry_points():
    """The oracle source must not reference any M0-M5 entry point by name.

    ``src/equiceval/__init__.py`` eagerly imports the engine, so a strict
    process-level ``sys.modules`` check is not possible without refactoring the
    package. This lexical guard catches an accidental call such as
    ``EquiCEvalEvaluator(...).evaluate(...)`` inside the oracle.
    """
    forbidden_tokens = (
        "EquiCEvalEvaluator",
        "EquivalenceMatcher",
        "DirectedDiscrepancyEvaluator",
        "BehavioralDiscrepancyEvaluator",
        "ObjectiveDiscrepancyEvaluator",
        "ModelPreChecker",
        "run_verified_evaluation",
        "evaluate_equiceval",
    )
    for path in ORACLE_FILES:
        source = path.read_text(encoding="utf-8")
        hits = [token for token in forbidden_tokens if token in source]
        assert not hits, f"{path.name} references engine entry points: {hits}"

