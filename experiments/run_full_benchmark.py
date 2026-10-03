"""Compatibility entry point for the verified runner.

The former label-dependent objective fabrication and row-index baseline have
been retired. Historical output files are preserved; new runs use the current
diagnostic schema reported by experiments.run_verified_evaluation.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from src.benchmark.verified_evaluation import ir_from_dict as dict_to_canonical_ir
from src.equiceval.contracts import PRIMARY_EQUIVAFORMULATION_CONTRACT
from experiments.run_verified_evaluation import run


def run_full_benchmark_eval(dataset_path="data/equiceval_full_benchmark.json"):
    raw = json.loads(Path(dataset_path).read_text())
    records = raw if isinstance(raw, list) else raw.get("records", (
        raw.get("equivalent_records", []) + raw.get("mutant_records", []) +
        raw.get("natural_records", [])))
    report = run(records, [5.0], PRIMARY_EQUIVAFORMULATION_CONTRACT, ["certificates"])
    path = Path("output") / ("verified_full_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"Saved {len(records)} audited records to {path}. Non-enumerable labels remain unverified.")
    return path


if __name__ == "__main__":
    run_full_benchmark_eval()
