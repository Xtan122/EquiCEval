# EquiCEval

Equivalence-aware, counterexample-guided evaluation of optimization formulations
(LP/MILP). This repository is the **method** repo: it contains the M0–M5 engine,
the canonical intermediate representation, the independent label oracle, the
canonicalized reference-form baselines, and the labelled benchmark used to
validate the engine itself.

The Refai–Ahmed baseline comparison on LLM outputs and the EquivaMap /
EquivaFormulation validation live in separate experiment repositories
(`equiceval-llm-eval`, `equiceval-meta-eval`).

## Install

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Test

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests -m "not ollama" -q
```

## Usage

```bash
# Score the built-in 12-case fixtures (offline, no network)
PYTHONPATH=. .venv/bin/python -m experiments.run_verified_evaluation \
  --output output/tier1_$(date +%s).json --budgets 0 1 5

# Meta-evaluate the engine on the labelled benchmark (no LLM calls)
PYTHONPATH=. .venv/bin/python -m experiments.evaluate_equiceval \
  --dataset data/equiceval_pilot_benchmark.json --limit 48 \
  --budgets 1 --modes direct_only certificates early_stop \
  --baselines refform strong \
  --output output/meta_$(date +%s).json --report output/reports/meta.md

# Regenerate the labelled benchmark (deterministic, seed=42)
PYTHONPATH=. .venv/bin/python -m experiments.generate_benchmark_dataset
```

- Scripts under `experiments/` import `src.*`; always set `PYTHONPATH=.`.
- `--output` must not exist (`open("x")`); runners never overwrite.

## Layout

- `src/equiceval/` — engine, one file per module: `precheck.py` (M0),
  `canonical_ir.py` (M1), `matching.py` (M2), `behavioral_discrepancy.py` (M3),
  `directed_query.py` (M4), `objective_discrepancy.py` (M5), orchestrated by
  `evaluator.py`; `contracts.py`, `metrics.py`, `evidence.py`,
  `constraint_rmse.py`.
- `src/benchmark/` — `verified_evaluation.py` (IR serde + integer oracle),
  `independent_oracle.py` (renaming/LP labels), `witness_metrics.py`,
  `analysis.py`, `splits.py`, `reference_form_baseline.py` + `baselines/`,
  `reference_ir.py`, `ground_truth.py`, dataset generation
  (`generator.py`, `transformations.py`, `mutator.py`, `schema.py`).
- `src/utils/solver_wrapper.py` — LP → HiGHS, MILP → SCIP, fallback PuLP/CBC.
- `data/equiceval_{pilot,full}_benchmark.json` — committed labelled benchmarks.

## Hard invariants

- Never certify on timeout; never force `unresolved`/`null` labels.
- Labels must be produced independently of the M0–M5 pipeline.
- Budget is shared by the whole pair (M0–M5), not per query.
