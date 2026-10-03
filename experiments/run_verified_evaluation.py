"""Run from repository root: python -m experiments.run_verified_evaluation --help."""
import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
import importlib.metadata

from src.benchmark.verified_evaluation import ir_from_dict, enumerate_oracle, demo_records
from src.benchmark.witness_metrics import (
    localization_check,
    witness_check,
    witness_check_record,
)
from src.equiceval.evaluator import EquiCEvalEvaluator, DIAGNOSTIC_SCHEMA_VERSION
from src.equiceval.contracts import PRIMARY_EQUIVAFORMULATION_CONTRACT, SUPPORTED_CONTRACTS
from src.equiceval.metrics import verification_metrics
from src.utils.solver_wrapper import CBC_SETTINGS


def _finite_for_json(value):
    """Strict-JSON sanitizer: non-finite floats (unbounded IR bounds) -> null.

    The report stores the raw input IRs, whose ``upper_bound``/``lower_bound``
    are legitimately ``inf``; ``json.dump(..., allow_nan=False)`` would reject it.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _finite_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite_for_json(v) for v in value]
    return value


def _record_certificate(record, contract):
    """Return a sound record-level certificate applicable to the contract.

    Dataset adapters may attach a ``certificate`` to a record when they can
    prove non-equivalence without the general evaluator (e.g. a feasibility
    problem with a constant objective under the argmin contract).  It is only
    honoured for contracts that include the certificate's stated semantics.
    """
    certificate = record.get("certificate")
    if not isinstance(certificate, dict):
        return None
    cert_contract = certificate.get("contract")
    if isinstance(cert_contract, (list, tuple, set, frozenset)):
        if contract not in cert_contract:
            return None
    elif cert_contract not in (None, contract):
        return None
    if isinstance(cert_contract, str) and "argmin" in cert_contract \
            and "argmin" not in contract:
        return None
    return certificate


def _certificate_diagnostic(certificate):
    """Minimal diagnostic vector for a record-level certificate."""
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "verdict": certificate.get("verdict", "disproved"),
        "feasibility_verdict": "not_requested",
        "objective_verdict": "disproved",
        "VarMatch": None, "ConMatch": None, "MapCoverage": None,
        "MatchCoverage": None, "NumericalMatchCoverage": None,
        "D_sat": None, "D_margin": None, "Delta_right": None, "Delta_left": None,
        "Delta_f": None, "OptimalityGap": None, "Gap_abs": None, "Gap_sym": None,
        "certificate": certificate,
        "notes": [certificate.get("reason", "")],
        "Status": {"certificate_backed": True},
    }


def run(records, budgets, contract, modes, *, on_result=None, context_matching=True,
        group_matching=False, max_context_pairs=32, max_group_trials=16, labeler=None,
        use_record_labels=False, safety_box_bound=None):
    root = Path(__file__).resolve().parents[1]
    sources = list((root / "src/equiceval").glob("*.py")) + [
        root / "src/utils/solver_wrapper.py", root / "src/benchmark/verified_evaluation.py",
        Path(__file__)]
    source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sources}
    component_options = dict(context_matching=context_matching, group_matching=group_matching,
                             max_context_pairs=max_context_pairs, max_group_trials=max_group_trials)
    config = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "contract": contract,
        "budgets": budgets, "modes": modes, "python": platform.python_version(),
        "platform": platform.platform(), "pulp": importlib.metadata.version("pulp"),
        "solver_settings": dict(CBC_SETTINGS), "solver_tolerance": 1e-5,
        "sampling_seed": 42, "num_samples": 100,
        "diagnostic_schema": DIAGNOSTIC_SCHEMA_VERSION,
        "scipy": importlib.metadata.version("scipy"),
        "component_settings": dict(component_options,
                                   schedule="after M4/M5; shared remaining pair budget"),
        "source_sha256": source_hashes,
        "input_sha256": hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
        "interpretation": "Small independently enumerated cases; not evidence of broad generalization.",
    }
    results, summaries = [], []
    # Oracle enumeration is independent of (seconds, mode); compute it once.
    label_fn = labeler or enumerate_oracle
    precomputed = []
    for record in records:
        ref = ir_from_dict(record["reference_ir"])
        cand = ir_from_dict(record["candidate_ir"])
        if use_record_labels:
            label = record.get("is_semantically_equivalent")
            evidence = {"method": "dataset_label", "source": record.get("provenance")}
        else:
            label, evidence = label_fn(ref, cand, contract)
        fault_kind = None
        if label is False:
            fault_kind = (evidence.get("counterexample") or {}).get("kind")
        provided = record.get("provided_substitutions") or None
        precomputed.append((record, ref, cand, label, evidence, fault_kind, provided))

    for seconds in budgets:
        for mode in modes:
            labels, verdicts = [], []
            for record, ref, cand, label, evidence, fault_kind, provided in precomputed:
                record_certificate = _record_certificate(record, contract)
                if record_certificate is not None:
                    result_verdict = record_certificate["verdict"]
                    diagnostic = _certificate_diagnostic(record_certificate)
                    result = None
                else:
                    evaluator = EquiCEvalEvaluator(
                        solver_time_limit=seconds, contract=contract,
                        safety_box_bound=safety_box_bound,
                        use_certificates=mode != "direct_only", stop_on_witness=mode == "early_stop",
                        **component_options)
                    result = evaluator.evaluate(ref, cand, provided_substitutions=provided)
                    diagnostic = result.to_diagnostic_vector()
                    result_verdict = result.verdict
                if record.get("raw_reference_ir") and record.get("raw_candidate_ir"):
                    present, valid = witness_check_record(record, diagnostic)
                    witness_scope = "raw_source_models"
                else:
                    present, valid = witness_check(ref, cand, diagnostic)
                    witness_scope = "evaluation_inputs"
                labels.append(label)
                verdicts.append(result_verdict)
                results.append({
                    "record_id": record.get("record_id"), "family": record.get("family", record.get("base_problem_name")),
                    "mode": mode, "seconds": seconds, "label": label, "label_evidence": evidence,
                    "fault_kind": fault_kind,
                    "witness": {"present": present, "valid": valid,
                                "verified_on": witness_scope},
                    "localization": localization_check(ref, cand, evidence, diagnostic),
                    "input": record, "diagnostic": diagnostic,
                })
                if on_result is not None:
                    on_result(results[-1])
            summaries.append({
                "mode": mode, "seconds": seconds,
                "exact_acceptance": verification_metrics(labels, verdicts),
                "numerical_acceptance": verification_metrics(labels, verdicts, accept_numerical=True),
            })
    return {"config": config, "results": results, "summaries": summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, help="Omit for 12 diagnostic fixtures")
    parser.add_argument("--output", type=Path, required=True, help="A new JSON file; existing files are never overwritten")
    parser.add_argument("--budgets", nargs="+", type=float, default=[0, 1, 5])
    parser.add_argument("--modes", nargs="+", choices=["direct_only", "certificates", "early_stop"],
                        default=["direct_only", "certificates", "early_stop"])
    parser.add_argument("--contract", choices=SUPPORTED_CONTRACTS,
                        default=PRIMARY_EQUIVAFORMULATION_CONTRACT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-context-matching", action="store_true",
                        help="Skip contextual pairs; retain algebraic matches")
    parser.add_argument("--group-matching", action="store_true",
                        help="Opt in to bounded one-versus-two residual group matching")
    parser.add_argument("--max-context-pairs", type=int, default=32)
    parser.add_argument("--max-group-trials", type=int, default=16)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path to preserve earlier measurements")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.dataset:
        raw = json.loads(args.dataset.read_text())
        records = raw if isinstance(raw, list) else raw.get("records", (
            raw.get("equivalent_records", []) + raw.get("mutant_records", []) + raw.get("natural_records", [])))
    else:
        records = demo_records()
    if args.limit:
        records = records[:args.limit]
    if args.max_context_pairs < 0 or args.max_group_trials < 0:
        parser.error("Component search limits must be nonnegative")
    report = run(records, args.budgets, args.contract, args.modes,
                 context_matching=not args.no_context_matching, group_matching=args.group_matching,
                 max_context_pairs=args.max_context_pairs, max_group_trials=args.max_group_trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(_finite_for_json(report), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"output": str(args.output), "runs": len(report["results"])}, ensure_ascii=False))
    for summary in report["summaries"]:
        print(summary["seconds"], summary["mode"],
              summary["exact_acceptance"]["verdict_counts"])


if __name__ == "__main__":
    main()
