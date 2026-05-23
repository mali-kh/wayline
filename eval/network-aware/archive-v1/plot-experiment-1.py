#!/usr/bin/env python3
"""
Plot Experiment 1 results: Network-Aware vs Dependency-Only Scheduling.

Reads CSV files from eval/results/ and generates publication-quality figures.

Usage: python3 eval/plot-experiment-1.py
"""

import os
import csv
import sys
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib not installed. Install with: pip install matplotlib")
    sys.exit(1)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

plt.rcParams.update({
    "font.size": 12,
    "font.family": "serif",
    "axes.grid": True,
    "grid.alpha": 0.3,
})


def plot_odag():
    """Plot ODAG makespan comparison (bar chart + convergence)."""
    csv_path = os.path.join(RESULTS_DIR, "odag-makespan.csv")
    if not os.path.exists(csv_path):
        print(f"  Skipping ODAG plots: {csv_path} not found")
        return

    data = {"random": [], "heft": []}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            sched = row["scheduler"]
            makespan = float(row["makespan"])
            if makespan > 0 and sched in data:
                data[sched].append(makespan)

    if not data["random"] or not data["heft"]:
        print("  Skipping ODAG plots: insufficient data")
        return

    # --- Bar chart: mean ± stddev ---
    fig, ax = plt.subplots(figsize=(5, 4))
    schedulers = ["random", "heft"]
    means = [np.mean(data[s]) for s in schedulers]
    stds = [np.std(data[s]) for s in schedulers]
    colors = ["#ef4444", "#3b82f6"]
    labels = ["Random\n(dependency-only)", "HEFT\n(network-aware)"]

    bars = ax.bar(labels, means, yerr=stds, capsize=8, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Makespan (seconds)")
    ax.set_title("ODAG: IoBT Mission Snapshot")

    # Add value labels on bars.
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + std + 1,
                f"{mean:.1f}s", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # Improvement annotation.
    if means[0] > 0:
        improvement = (means[0] - means[1]) / means[0] * 100
        ax.text(0.5, 0.95, f"{improvement:.0f}% improvement",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=11, color="#16a34a", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#dcfce7", edgecolor="#16a34a", alpha=0.8))

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "odag-makespan-bar.png")
    plt.savefig(out, dpi=200)
    print(f"  Saved: {out}")
    plt.close()

    # --- Convergence plot (HEFT over runs) ---
    if len(data["heft"]) >= 3:
        fig, ax = plt.subplots(figsize=(6, 4))
        runs = list(range(1, len(data["heft"]) + 1))
        ax.plot(runs, data["heft"], "o-", color="#3b82f6", label="HEFT", linewidth=2, markersize=6)
        if data["random"]:
            random_mean = np.mean(data["random"])
            ax.axhline(y=random_mean, color="#ef4444", linestyle="--", linewidth=1.5, label=f"Random mean ({random_mean:.1f}s)")
        ax.set_xlabel("Run number")
        ax.set_ylabel("Makespan (seconds)")
        ax.set_title("HEFT Profiler Convergence")
        ax.legend()
        plt.tight_layout()
        out = os.path.join(FIGURES_DIR, "odag-convergence.png")
        plt.savefig(out, dpi=200)
        print(f"  Saved: {out}")
        plt.close()


def plot_cdag():
    """Plot CDAG latency/throughput comparison."""
    csv_path = os.path.join(RESULTS_DIR, "cdag-latency.csv")
    if not os.path.exists(csv_path):
        print(f"  Skipping CDAG plots: {csv_path} not found")
        return

    data = {"random": {"lat": [], "tp": []}, "locality": {"lat": [], "tp": []}}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            sched = row["scheduler"]
            if sched not in data:
                continue
            avg_lat = float(row["avg_latency"])
            tp = float(row["throughput"])
            if avg_lat > 0:
                data[sched]["lat"].append(avg_lat)
            if tp > 0:
                data[sched]["tp"].append(tp)

    has_data = data["random"]["lat"] and data["locality"]["lat"]
    if not has_data:
        print("  Skipping CDAG plots: insufficient data")
        return

    # --- Latency bar chart ---
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    schedulers = ["random", "locality"]
    colors = ["#ef4444", "#3b82f6"]
    labels = ["Random", "Locality"]

    # Latency
    ax = axes[0]
    means = [np.mean(data[s]["lat"]) * 1000 for s in schedulers]  # ms
    stds = [np.std(data[s]["lat"]) * 1000 for s in schedulers]
    bars = ax.bar(labels, means, yerr=stds, capsize=8, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Avg End-to-End Latency (ms)")
    ax.set_title("CDAG: Camera Pipeline Latency")
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + std + 0.5,
                f"{mean:.0f}ms", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # Throughput
    ax = axes[1]
    means = [np.mean(data[s]["tp"]) for s in schedulers]
    stds = [np.std(data[s]["tp"]) for s in schedulers]
    bars = ax.bar(labels, means, yerr=stds, capsize=8, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Throughput (msg/s)")
    ax.set_title("CDAG: Camera Pipeline Throughput")
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + std + 0.1,
                f"{mean:.1f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "cdag-latency-throughput.png")
    plt.savefig(out, dpi=200)
    print(f"  Saved: {out}")
    plt.close()


if __name__ == "__main__":
    print("=== Experiment 1 Plots ===")
    print("ODAG plots:")
    plot_odag()
    print("CDAG plots:")
    plot_cdag()
    print("Done.")
