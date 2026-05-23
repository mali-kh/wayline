#!/usr/bin/env python3
"""
Plot Experiment 2: Scalability — P2P vs Centralized.

Generates:
  2A (ODAG): Makespan vs fan-out width (P2P data-agent vs NFS)
  2B (CDAG): Throughput + latency vs fan-out width (ZMQ P2P vs MQTT broker)

Usage: python3 eval/scalability/plot-scalability.py
"""

import os
import csv
import sys
import numpy as np
from collections import defaultdict

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

COLORS = {"p2p": "#3b82f6", "nfs": "#ef4444", "zmq": "#3b82f6", "mqtt": "#ef4444"}
MARKERS = {"p2p": "o", "nfs": "s", "zmq": "o", "mqtt": "s"}
LABELS = {
    "p2p": "DSF (P2P data-agent)",
    "nfs": "NFS shared storage",
    "zmq": "DSF (ZMQ P2P)",
    "mqtt": "MQTT Broker",
}


def plot_odag():
    """Plot ODAG makespan vs fan-out width."""
    csv_path = os.path.join(RESULTS_DIR, "odag-scalability.csv")
    if not os.path.exists(csv_path):
        print(f"  Skipping ODAG plot: {csv_path} not found")
        return

    data = defaultdict(lambda: defaultdict(list))
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                makespan = float(row["makespan"])
            except (ValueError, TypeError):
                continue
            if makespan > 0:
                data[row["transport"]][int(row["workers"])].append(makespan)

    if not data:
        print("  Skipping ODAG plot: no data")
        return

    fig, ax = plt.subplots(figsize=(6, 4.5))

    for transport in ["p2p", "nfs"]:
        if transport not in data:
            continue
        workers = sorted(data[transport].keys())
        means = [np.mean(data[transport][w]) for w in workers]
        stds = [np.std(data[transport][w]) for w in workers]

        ax.errorbar(workers, means, yerr=stds,
                     marker=MARKERS[transport], color=COLORS[transport],
                     linewidth=2, markersize=8, capsize=5,
                     label=LABELS[transport])

    ax.set_xlabel("Number of Workers (fan-out width)")
    ax.set_ylabel("Makespan (seconds)")
    ax.set_title("ODAG Scalability: P2P vs NFS")
    ax.legend()
    ax.set_xticks(sorted(set(w for t in data for w in data[t])))

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "odag-scalability.png")
    plt.savefig(out, dpi=200)
    print(f"  Saved: {out}")
    plt.close()


def plot_cdag():
    """Plot CDAG throughput and latency vs fan-out width."""
    csv_path = os.path.join(RESULTS_DIR, "cdag-scalability.csv")
    if not os.path.exists(csv_path):
        # Try old name.
        csv_path = os.path.join(RESULTS_DIR, "scalability.csv")
        if not os.path.exists(csv_path):
            print(f"  Skipping CDAG plots: no CSV found")
            return

    data = defaultdict(lambda: defaultdict(lambda: {"throughput": [], "avg_latency": [], "p50": [], "p95": []}))
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            tp = float(row["throughput"])
            if tp > 0:
                t, w = row["transport"], int(row["workers"])
                data[t][w]["throughput"].append(tp)
                data[t][w]["avg_latency"].append(float(row["avg_latency"]))
                data[t][w]["p50"].append(float(row["p50_latency"]))
                data[t][w]["p95"].append(float(row["p95_latency"]))

    if not data:
        print("  Skipping CDAG plots: no data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    for transport in ["zmq", "mqtt"]:
        if transport not in data:
            continue
        workers = sorted(data[transport].keys())

        # Throughput.
        tp_means = [np.mean(data[transport][w]["throughput"]) for w in workers]
        tp_stds = [np.std(data[transport][w]["throughput"]) for w in workers]
        axes[0].errorbar(workers, tp_means, yerr=tp_stds,
                          marker=MARKERS[transport], color=COLORS[transport],
                          linewidth=2, markersize=8, capsize=5,
                          label=LABELS[transport])

        # Latency p50.
        lat_means = [np.mean(data[transport][w]["p50"]) * 1000 for w in workers]
        lat_stds = [np.std(data[transport][w]["p50"]) * 1000 for w in workers]
        axes[1].errorbar(workers, lat_means, yerr=lat_stds,
                          marker=MARKERS[transport], color=COLORS[transport],
                          linewidth=2, markersize=8, capsize=5,
                          label=LABELS[transport])

    xticks = sorted(set(w for t in data for w in data[t]))
    axes[0].set_xlabel("Workers")
    axes[0].set_ylabel("Throughput (msg/s)")
    axes[0].set_title("(a) CDAG Throughput")
    axes[0].legend()
    axes[0].set_xticks(xticks)

    axes[1].set_xlabel("Workers")
    axes[1].set_ylabel("Latency p50 (ms)")
    axes[1].set_title("(b) CDAG Latency")
    axes[1].legend()
    axes[1].set_xticks(xticks)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "cdag-scalability.png")
    plt.savefig(out, dpi=200)
    print(f"  Saved: {out}")
    plt.close()


def plot_combined():
    """3-panel combined figure for the paper."""
    odag_path = os.path.join(RESULTS_DIR, "odag-scalability.csv")
    cdag_path = os.path.join(RESULTS_DIR, "cdag-scalability.csv")
    if not os.path.exists(cdag_path):
        cdag_path = os.path.join(RESULTS_DIR, "scalability.csv")

    has_odag = os.path.exists(odag_path)
    has_cdag = os.path.exists(cdag_path)

    if not has_odag and not has_cdag:
        print("  Skipping combined plot: no data")
        return

    n_panels = (1 if has_odag else 0) + (2 if has_cdag else 0)
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 4.5))
    if n_panels == 1:
        axes = [axes]

    idx = 0

    # ODAG panel.
    if has_odag:
        odag_data = defaultdict(lambda: defaultdict(list))
        with open(odag_path) as f:
            for row in csv.DictReader(f):
                try:
                    ms = float(row["makespan"])
                except (ValueError, TypeError):
                    continue
                if ms > 0:
                    odag_data[row["transport"]][int(row["workers"])].append(ms)

        ax = axes[idx]
        for transport in ["p2p", "nfs"]:
            if transport not in odag_data:
                continue
            workers = sorted(odag_data[transport].keys())
            means = [np.mean(odag_data[transport][w]) for w in workers]
            stds = [np.std(odag_data[transport][w]) for w in workers]
            ax.errorbar(workers, means, yerr=stds,
                         marker=MARKERS[transport], color=COLORS[transport],
                         linewidth=2, markersize=8, capsize=5,
                         label=LABELS[transport])
        ax.set_xlabel("Workers")
        ax.set_ylabel("Makespan (s)")
        ax.set_title("(a) ODAG: Makespan")
        ax.legend(fontsize=9)
        ax.set_xticks(sorted(set(w for t in odag_data for w in odag_data[t])))
        idx += 1

    # CDAG panels.
    if has_cdag:
        cdag_data = defaultdict(lambda: defaultdict(lambda: {"throughput": [], "p50": []}))
        with open(cdag_path) as f:
            for row in csv.DictReader(f):
                if float(row["throughput"]) > 0:
                    t, w = row["transport"], int(row["workers"])
                    cdag_data[t][w]["throughput"].append(float(row["throughput"]))
                    cdag_data[t][w]["p50"].append(float(row["p50_latency"]))

        for transport in ["zmq", "mqtt"]:
            if transport not in cdag_data:
                continue
            workers = sorted(cdag_data[transport].keys())

            tp_means = [np.mean(cdag_data[transport][w]["throughput"]) for w in workers]
            tp_stds = [np.std(cdag_data[transport][w]["throughput"]) for w in workers]
            axes[idx].errorbar(workers, tp_means, yerr=tp_stds,
                                marker=MARKERS[transport], color=COLORS[transport],
                                linewidth=2, markersize=8, capsize=5,
                                label=LABELS[transport])

            lat_means = [np.mean(cdag_data[transport][w]["p50"]) * 1000 for w in workers]
            lat_stds = [np.std(cdag_data[transport][w]["p50"]) * 1000 for w in workers]
            axes[idx + 1].errorbar(workers, lat_means, yerr=lat_stds,
                                    marker=MARKERS[transport], color=COLORS[transport],
                                    linewidth=2, markersize=8, capsize=5,
                                    label=LABELS[transport])

        xticks = sorted(set(w for t in cdag_data for w in cdag_data[t]))
        axes[idx].set_xlabel("Workers")
        axes[idx].set_ylabel("Throughput (msg/s)")
        axes[idx].set_title("(b) CDAG: Throughput")
        axes[idx].legend(fontsize=9)
        axes[idx].set_xticks(xticks)

        axes[idx + 1].set_xlabel("Workers")
        axes[idx + 1].set_ylabel("Latency p50 (ms)")
        axes[idx + 1].set_title("(c) CDAG: Latency")
        axes[idx + 1].legend(fontsize=9)
        axes[idx + 1].set_xticks(xticks)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "scalability-combined.png")
    plt.savefig(out, dpi=200)
    print(f"  Saved: {out}")
    plt.close()


if __name__ == "__main__":
    print("=== Experiment 2: Scalability Plots ===")
    print("ODAG (P2P vs NFS):")
    plot_odag()
    print("CDAG (ZMQ vs MQTT):")
    plot_cdag()
    print("Combined:")
    plot_combined()
    print("Done.")
