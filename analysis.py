"""Fastned expansion case: which country should Fastned enter after Austria?

Scores four candidate markets (Poland, Czechia, Sweden, Portugal) on five weighted
criteria and runs a sensitivity check on the weights.

Run:  python analysis.py
Outputs: results.csv, charts/*.png, printed ranking.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).parent
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

NAVY, BLUE, GREY = "#1F3864", "#2E75B6", "#BFBFBF"

# Weights reflect what drives a fast-charging business: enough EVs today,
# fast growth, too few chargers (pricing power), supportive policy, and
# operational fit with Fastned's existing network.
WEIGHTS = {
    "market_size": 0.30,      # BEV fleet on the road
    "growth": 0.25,           # BEV registration growth 2024 -> 2025
    "charging_gap": 0.25,     # BEVs per public DC charge point
    "policy": 0.10,           # national EV support (1-3)
    "network_fit": 0.10,      # proximity to existing Fastned markets (1-3)
}


def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "countries.csv")
    df["bevs_per_dc_point"] = (df["bev_fleet_est_2024"] / df["dc_charge_points_2023"]).round(1)
    return df


def minmax(s: pd.Series) -> pd.Series:
    return (s - s.min()) / (s.max() - s.min()) if s.max() != s.min() else s * 0 + 1


def score(candidates: pd.DataFrame, weights: dict) -> pd.DataFrame:
    c = candidates.copy()
    c["market_size"] = minmax(c["bev_fleet_est_2024"])
    c["growth"] = minmax(c["bev_growth_vs_2024_pct"])
    c["charging_gap"] = minmax(c["bevs_per_dc_point"])
    c["policy"] = minmax(c["policy_score"])
    c["network_fit"] = minmax(c["network_fit_score"])
    c["total_score"] = sum(c[k] * w for k, w in weights.items()).round(3)
    return c.sort_values("total_score", ascending=False)


def sensitivity(candidates: pd.DataFrame) -> pd.DataFrame:
    """Re-weight one criterion up by 50% at a time and record the winner."""
    rows = []
    for k in WEIGHTS:
        w = dict(WEIGHTS)
        w[k] *= 1.5
        total = sum(w.values())
        w = {kk: v / total for kk, v in w.items()}
        ranked = score(candidates, w)
        rows.append({"criterion_upweighted": k, "winner": ranked.iloc[0]["country"],
                     "runner_up": ranked.iloc[1]["country"]})
    return pd.DataFrame(rows)


def charts(df: pd.DataFrame, ranked: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

    # 1. Market size vs growth (bubble = charging gap)
    fig, ax = plt.subplots(figsize=(8, 5))
    plot = df[df["country"].isin(ranked["country"].tolist() + ["Austria"])]
    for _, r in plot.iterrows():
        color = NAVY if r["country"] == ranked.iloc[0]["country"] else (GREY if r["role"].startswith("bench") else BLUE)
        ax.scatter(r["bev_fleet_est_2024"] / 1000, r["bev_growth_vs_2024_pct"], s=r["bevs_per_dc_point"] * 12,
                   color=color, alpha=0.75, edgecolor="white", linewidth=1.5)
        ax.annotate(r["country"], (r["bev_fleet_est_2024"] / 1000, r["bev_growth_vs_2024_pct"]),
                    textcoords="offset points", xytext=(10, 6))
    ax.set_xlabel("BEV fleet on the road, 2024 (thousands, est.)")
    ax.set_ylabel("BEV registration growth 2025 vs 2024 (%)")
    ax.set_title("Market size vs growth (bubble size = BEVs per public DC charger)", loc="left")
    fig.tight_layout()
    fig.savefig(CHARTS / "market_map.png", dpi=150)
    plt.close(fig)

    # 2. Weighted score ranking
    fig, ax = plt.subplots(figsize=(8, 4))
    r2 = ranked.iloc[::-1]
    colors = [NAVY if c == ranked.iloc[0]["country"] else BLUE for c in r2["country"]]
    ax.barh(r2["country"], r2["total_score"], color=colors)
    for y, v in enumerate(r2["total_score"]):
        ax.text(v + 0.01, y, f"{v:.2f}", va="center")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Weighted attractiveness score (0-1)")
    ax.set_title("Market attractiveness ranking", loc="left")
    fig.tight_layout()
    fig.savefig(CHARTS / "ranking.png", dpi=150)
    plt.close(fig)

    # 3. Charging gap
    fig, ax = plt.subplots(figsize=(8, 4))
    gap = df[df["country"].isin(ranked["country"].tolist() + ["Austria", "Germany"])].sort_values("bevs_per_dc_point")
    ax.barh(gap["country"], gap["bevs_per_dc_point"],
            color=[GREY if r in ("benchmark (announced next market)", "existing market") else BLUE for r in gap["role"]])
    for y, v in enumerate(gap["bevs_per_dc_point"]):
        ax.text(v + 1, y, f"{v:.0f}", va="center")
    ax.set_xlabel("Battery-electric cars per public DC charge point")
    ax.set_title("Where are fast chargers scarcest?", loc="left")
    fig.tight_layout()
    fig.savefig(CHARTS / "charging_gap.png", dpi=150)
    plt.close(fig)


def main() -> None:
    df = load()
    candidates = df[df["role"] == "candidate"]
    ranked = score(candidates, WEIGHTS)
    sens = sensitivity(candidates)

    cols = ["country", "bev_fleet_est_2024", "bev_growth_vs_2024_pct", "bevs_per_dc_point",
            "policy_score", "network_fit_score", "total_score"]
    ranked[cols].to_csv(ROOT / "results.csv", index=False)
    charts(df, ranked)

    print("Ranking:\n", ranked[cols].to_string(index=False))
    print("\nSensitivity (each criterion weighted +50%):\n", sens.to_string(index=False))


if __name__ == "__main__":
    main()
