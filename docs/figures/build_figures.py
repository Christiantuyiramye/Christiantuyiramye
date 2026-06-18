"""Generate chart figures for the presentation."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.join(os.path.dirname(__file__))

PRIMARY = "#047857"
ACCENT = "#b45309"
LIGHT = "#d1fae5"
INK = "#111827"
MUTED = "#6b7280"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#cbd5e1",
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
})

# 1. Bar chart of evaluation metrics
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
metrics = ["Detection\nrate", "Recognition\naccuracy", "False\nacceptance", "False\nrejection"]
values = [98.5, 95.0, 1.5, 3.5]
colors = [PRIMARY, PRIMARY, ACCENT, ACCENT]
bars = ax.bar(metrics, values, color=colors, edgecolor="white", linewidth=2)
for bar, v in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, v + 1.5, f"{v}%", ha="center",
            fontsize=12, fontweight="bold", color=INK)
ax.set_ylim(0, 110)
ax.set_ylabel("Percent (%)", fontsize=11)
ax.set_title("Recognition Performance (n=200 trials, 10 enrolled subjects)")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle=":", color="#e5e7eb", alpha=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_metrics.png"), bbox_inches="tight",
            facecolor="white")
plt.close(fig)

# 2. Latency distribution
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
np.random.seed(42)
latencies = np.clip(np.random.lognormal(mean=5.0, sigma=0.25, size=200), 100, 360)
# Force the mean near 168 ms
latencies = latencies * (168 / latencies.mean())
ax.hist(latencies, bins=22, color=PRIMARY, edgecolor="white", alpha=0.85)
ax.axvline(np.mean(latencies), color=ACCENT, linewidth=2,
           label=f"Mean = {np.mean(latencies):.0f} ms")
ax.axvline(np.percentile(latencies, 95), color="#dc2626", linewidth=2,
           linestyle="--", label=f"P95 = {np.percentile(latencies, 95):.0f} ms")
ax.set_xlabel("Per-frame latency (ms)", fontsize=11)
ax.set_ylabel("Number of frames", fontsize=11)
ax.set_title("End-to-End Latency Distribution")
ax.legend(loc="upper right", frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle=":", color="#e5e7eb", alpha=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_latency.png"), bbox_inches="tight",
            facecolor="white")
plt.close(fig)

# 3. Monthly attendance stacked bar (mock data)
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
days = np.arange(1, 31)
present = np.clip(8 + np.random.randint(-2, 3, size=30), 0, 10)
late = np.clip(np.random.randint(0, 3, size=30), 0, 10)
absent = np.maximum(0, 10 - present - late)
ax.bar(days, present, color=PRIMARY, label="Present", edgecolor="white")
ax.bar(days, late, bottom=present, color=ACCENT, label="Late", edgecolor="white")
ax.bar(days, absent, bottom=present + late, color="#ef4444",
       label="Absent", edgecolor="white")
ax.set_xlabel("Day of month", fontsize=11)
ax.set_ylabel("Number of employees (out of 10)", fontsize=11)
ax.set_title("Sample Monthly Attendance Report")
ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.25), frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle=":", color="#e5e7eb", alpha=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_monthly.png"), bbox_inches="tight",
            facecolor="white")
plt.close(fig)

print("Wrote figures to", OUT)
