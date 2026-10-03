"""
Benchmark Dataset Generator Script for EquiCEval.
Generates Pilot & Full Benchmark Suites and saves JSON artifacts to data/.
"""

import json
import os
from typing import Dict, Any

from src.benchmark.generator import BenchmarkGenerator
from src.benchmark.schema import BenchmarkSuite


def save_suite_to_json(suite: BenchmarkSuite, output_path: str):
    """
    Saves a BenchmarkSuite to JSON format.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    data = {
        "summary": suite.summary(),
        "equivalent_records": [rec.to_dict() for rec in suite.equivalent_records],
        "mutant_records": [rec.to_dict() for rec in suite.mutant_records],
        "natural_records": [rec.to_dict() for rec in suite.natural_records],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully saved benchmark dataset to: {output_path}")


def run_generator_pipeline():
    print("=" * 80)
    print("  EQUICEVAL BENCHMARK SUITE GENERATOR")
    print("=" * 80)

    generator = BenchmarkGenerator(seed=42)

    # 1. Generate Pilot Suite (100 equivalent, 250 mutants)
    print("\n[Phase 1] Generating Pilot Benchmark Suite (100 equivalent, 250 mutants)...")
    pilot_suite = generator.build_full_suite(eq_count=100, mut_count=250)
    print(f"Pilot Suite Summary: {pilot_suite.summary()}")

    pilot_path = "data/equiceval_pilot_benchmark.json"
    save_suite_to_json(pilot_suite, pilot_path)

    # 2. Generate Full Target Suite (400 equivalent, 800 mutants)
    print("\n[Phase 2] Generating Full Target Benchmark Suite (400 equivalent, 800 mutants)...")
    full_suite = generator.build_full_suite(eq_count=400, mut_count=800)
    print(f"Full Suite Summary: {full_suite.summary()}")

    full_path = "data/equiceval_full_benchmark.json"
    save_suite_to_json(full_suite, full_path)

    # 3. Print Transformation & Mutation Operator Breakdown
    print("\n[Breakdown] Equivalent Transformation Classes:")
    trans_counts: Dict[str, int] = {}
    for rec in full_suite.equivalent_records:
        label = rec.transformation_label or "unknown"
        trans_counts[label] = trans_counts.get(label, 0) + 1
    for label, count in trans_counts.items():
        print(f"  - {label}: {count} records")

    print("\n[Breakdown] Controlled Mutation Operator Types:")
    mut_counts: Dict[str, int] = {}
    for rec in full_suite.mutant_records:
        label = (rec.mutation_label or "unknown").split("_")[0]
        mut_counts[label] = mut_counts.get(label, 0) + 1
    for label, count in mut_counts.items():
        print(f"  - {label}: {count} records")

    print("=" * 80)


if __name__ == "__main__":
    run_generator_pipeline()
