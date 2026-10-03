"""Plot measured per-record costs and verdict rates from schema-2.0/2.1 logs."""
import argparse
import json
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.equiceval.metrics import verification_metrics


def plot(report, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    groups = defaultdict(list)
    for row in report["results"]:
        if row["diagnostic"]["schema_version"] not in ("2.0", "2.1"):
            raise ValueError("Only schema 2.0/2.1 diagnostics are supported")
        groups[(row["mode"], row["seconds"])].append(row)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    modes = sorted({mode for mode, _ in groups})
    for mode in modes:
        points = []
        for (m, seconds), group in sorted(groups.items()):
            if m != mode:
                continue
            metrics = verification_metrics([r["label"] for r in group],
                                            [r["diagnostic"]["verdict"] for r in group])
            latency = sum(r["diagnostic"]["budget"]["elapsed_seconds"] for r in group)/len(group)
            points.append((latency, metrics["error_recall"]["value"],
                           metrics["unresolved_rate"]["value"], seconds))
        for axis, index in zip(axes, (1, 2)):
            available = [p for p in points if p[index] is not None]
            axis.plot([p[0] for p in available], [100*p[index] for p in available],
                      "o-", label=mode)
    for axis, title in zip(axes, ("Error detection recall (%)", "Unresolved (%)")):
        axis.set(xlabel="Measured mean elapsed time per pair (s)", ylabel=title, ylim=(-3, 108))
        axis.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    budgets = ", ".join(f"{s:g}s" for s in sorted({s for _, s in groups}))
    fig.suptitle("Diagnostic fixtures: not a generalization benchmark\n"
                 f"Each series shows measured runs at budgets {budgets}", fontsize=10)
    fig.savefig(output_dir / "measured_verification.png", dpi=180)
    fig.savefig(output_dir / "measured_verification.pdf")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    plot(json.loads(args.input.read_text()), args.output_dir)


if __name__ == "__main__":
    main()
