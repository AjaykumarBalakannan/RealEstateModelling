"""
visualize.py

generates 10 charts from the feature-engineered data.
all saved to outputs/charts/ as png files.

run after feature_engineering.py and adhoc_analysis.py.

run:  python visualize.py
deps: pip install pandas matplotlib seaborn numpy
"""

import os
import warnings
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np

warnings.filterwarnings("ignore")

DATA   = "data"
ADHOC  = "outputs/adhoc"
CHARTS = "outputs/charts"
os.makedirs(CHARTS, exist_ok=True)

# brand palette
DG  = "#1A3A2A"   # dark green
MG  = "#1A6B3A"   # mid green
LG  = "#C8E6C9"   # light green
GLD = "#C8A951"   # gold
RED = "#C62828"
AMB = "#E65100"
GRY = "#888888"

PROP_COLORS = ["#1A3A2A","#1A6B3A","#2E7D52","#43A066",
               "#C8A951","#D4813A","#C62828","#6A4C93"]


# global style — applied once at module level
plt.rcParams.update({
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "axes.edgecolor":    "#DDDDDD",
    "axes.grid":         True,
    "grid.color":        "#EEEEEE",
    "grid.linewidth":    0.6,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "font.family":       "DejaVu Sans",
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.titlepad":     14,
    "axes.labelsize":    11,
    "axes.labelcolor":   "#444444",
    "xtick.color":       "#666666",
    "ytick.color":       "#666666",
    "legend.frameon":    False,
})


def save(fig, name):
    path = f"{CHARTS}/{name}"
    fig.savefig(path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  saved → {name}")


def watermark(ax):
    ax.text(0.99, 0.01, "Sage Ventures Analytics",
            transform=ax.transAxes, fontsize=8,
            color="#CCCCCC", ha="right", va="bottom", style="italic")


def title_block(fig, title, subtitle):
    # title + subtitle above the plot area
    fig.text(0.07, 0.97, title,    fontsize=15, fontweight="bold",
             color=DG, va="top")
    fig.text(0.07, 0.93, subtitle, fontsize=10, color=GRY, va="top")


# ── chart 1: occupancy by property ────────────────────────────────────────────

def chart_occupancy():
    df = pd.read_csv(f"{DATA}/feat_property_kpis.csv") \
           .sort_values("occupancy_rate", ascending=True)

    fig, ax = plt.subplots(figsize=(10,5))
    title_block(fig, "Portfolio Occupancy Rate by Property",
                "Color-coded vs 93% target | Red < 70%, Amber 70-80%, Green >= 80%")

    colors = [RED if v < 70 else AMB if v < 80 else MG
              for v in df["occupancy_rate"]]

    bars = ax.barh(df["name"], df["occupancy_rate"],
                   color=colors, height=0.55, zorder=3)

    ax.axvline(93, color=DG, linewidth=1.5, linestyle="--",
               zorder=4, label="Target 93%")

    for bar, val in zip(bars, df["occupancy_rate"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va="center", fontsize=10,
                fontweight="bold", color=DG)

    ax.set_xlim(0, 105)
    ax.set_xlabel("Occupancy Rate (%)")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

    patches = [
        mpatches.Patch(color=MG,  label=">= 80% on target"),
        mpatches.Patch(color=AMB, label="70-80% watch"),
        mpatches.Patch(color=RED, label="< 70% at risk"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=9)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "01_occupancy_by_property.png")


# ── chart 2: YSR quarterly revenue trend ──────────────────────────────────────

def chart_ysr():
    df = pd.read_csv(f"{ADHOC}/adhoc5_ysr_portfolio.csv") \
           .sort_values("quarter")

    fig, ax1 = plt.subplots(figsize=(11,5))
    title_block(fig, "YSR — Quarterly Revenue Trend",
                "Gross Potential Rent vs Collected Rent with collection rate")

    x, w = np.arange(len(df)), 0.35
    ax1.bar(x - w/2, df["gross_potential_rent"]/1e6, w,
            label="Gross Potential Rent", color=DG, alpha=0.85, zorder=3)
    ax1.bar(x + w/2, df["collected_rent"]/1e6, w,
            label="Collected Rent", color=GLD, alpha=0.85, zorder=3)

    ax1.set_ylabel("Revenue ($M)")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:.1f}M"))
    ax1.set_xticks(x)
    ax1.set_xticklabels(df["quarter"], fontsize=10)

    # collection rate on right axis
    ax2 = ax1.twinx()
    ax2.plot(x, df["collection_rate_pct"], color=RED,
             marker="o", linewidth=2, markersize=6, zorder=5)
    ax2.set_ylabel("Collection Rate (%)", color=RED)
    ax2.set_ylim(90, 100)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax2.tick_params(axis="y", colors=RED)

    lines = [
        plt.Rectangle((0,0),1,1, color=DG),
        plt.Rectangle((0,0),1,1, color=GLD),
        plt.Line2D([0],[0], color=RED, marker="o", linewidth=2),
    ]
    ax1.legend(lines, ["Gross Potential Rent","Collected Rent","Collection Rate %"],
               loc="upper right", fontsize=9)
    watermark(ax1)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "02_ysr_quarterly_trend.png")


# ── chart 3: loss-to-lease stacked bar ────────────────────────────────────────

def chart_loss_to_lease():
    df    = pd.read_csv(f"{ADHOC}/adhoc3_loss_to_lease.csv")
    pivot = df.groupby(["property","unit_type"])["annual_revenue_gap"] \
               .sum().unstack(fill_value=0)
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False).drop(columns="_total")

    unit_colors = {
        "Studio":  "#1A3A2A","1BR/1BA":"#1A6B3A",
        "2BR/1BA": "#C8A951","2BR/2BA":"#D4813A","3BR/2BA":"#C62828"
    }

    fig, ax = plt.subplots(figsize=(12,5))
    title_block(fig, "Annual Loss-to-Lease by Property & Unit Type",
                "Revenue gap between market rent and actual rent ($/year)")

    bottom = np.zeros(len(pivot))
    for utype in pivot.columns:
        vals = pivot[utype].values / 1000
        ax.bar(pivot.index, vals, bottom=bottom/1000 if bottom.sum()>0 else bottom,
               label=utype, color=unit_colors.get(utype, GRY),
               alpha=0.88, width=0.6, zorder=3)
        bottom = bottom + pivot[utype].values

    totals = pivot.sum(axis=1).values / 1000
    for i, total in enumerate(totals):
        ax.text(i, total+2, f"${total:.0f}K",
                ha="center", fontsize=9, fontweight="bold", color=DG)

    ax.set_ylabel("Annual Revenue Gap ($K)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:.0f}K"))
    ax.set_xticklabels([p.replace(" ","\n") for p in pivot.index], fontsize=9)
    ax.legend(title="Unit Type", fontsize=9, loc="upper right")
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "03_loss_to_lease_stacked.png")


# ── chart 4: tenant risk tier donut ───────────────────────────────────────────

def chart_risk_tiers():
    df     = pd.read_csv(f"{DATA}/feat_tenants.csv")
    counts = df["risk_tier"].value_counts()
    order  = ["Low Risk","Medium Risk","High Risk","Critical"]
    counts = counts.reindex([o for o in order if o in counts.index])

    colors = [MG, GLD, AMB, RED]

    fig, ax = plt.subplots(figsize=(8,6))
    title_block(fig, "Tenant Delinquency Risk Tier Distribution",
                "Based on payment history, partial payments and on-time rate")

    wedges, _, autotexts = ax.pie(
        counts.values, colors=colors[:len(counts)],
        autopct="%1.1f%%", pctdistance=0.75, startangle=140,
        wedgeprops={"width":0.55,"edgecolor":"white","linewidth":2},
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
        at.set_color("white")

    # total in center
    ax.text(0, 0, f"{counts.sum():,}\nTenants",
            ha="center", va="center", fontsize=14,
            fontweight="bold", color=DG)

    legend_labels = [f"{t}  ({c:,})" for t,c in zip(counts.index, counts.values)]
    ax.legend(wedges, legend_labels, loc="lower center",
              bbox_to_anchor=(0.5,-0.08), ncol=2, fontsize=10)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "04_risk_tier_donut.png")


# ── chart 5: maintenance cost by category ─────────────────────────────────────

def chart_maintenance_cost():
    df  = pd.read_csv(f"{ADHOC}/adhoc4_maintenance_cost.csv")
    cat = df.groupby("category")["total_cost"].sum().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10,5))
    title_block(fig, "Total Maintenance Cost by Category",
                "YTD closed ticket spend across all 8 properties")

    colors = [PROP_COLORS[i % len(PROP_COLORS)] for i in range(len(cat))]
    bars   = ax.barh(cat.index, cat.values/1000, color=colors,
                     height=0.55, zorder=3)

    for bar, val in zip(bars, cat.values/1000):
        ax.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
                f"${val:,.0f}K", va="center", fontsize=10,
                fontweight="bold", color=DG)

    ax.set_xlabel("Total Cost ($K)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:.0f}K"))
    ax.set_xlim(0, cat.max()/1000 * 1.20)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "05_maintenance_cost_by_category.png")


# ── chart 6: SLA breaches by property ─────────────────────────────────────────

def chart_sla_breaches():
    df    = pd.read_csv(f"{ADHOC}/adhoc4_sla_breaches.csv")
    pivot = df.pivot_table(index="name", columns="priority",
                           values="sla_breach_count", fill_value=0)

    pri_colors = {"Emergency":RED,"High":AMB,"Medium":GLD,"Low":MG}

    fig, ax = plt.subplots(figsize=(12,5))
    title_block(fig, "Maintenance SLA Breaches by Property & Priority",
                "Open tickets that exceeded SLA resolution threshold")

    n    = len(pivot.columns)
    x    = np.arange(len(pivot))
    w    = 0.7 / n

    for i, pri in enumerate(pivot.columns):
        offset = (i - n/2 + 0.5) * w
        vals   = pivot[pri].values
        bars   = ax.bar(x+offset, vals, w*0.9, label=pri,
                        color=pri_colors.get(pri, GRY), alpha=0.88, zorder=3)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                        str(int(v)), ha="center", fontsize=8,
                        fontweight="bold", color=DG)

    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ","\n") for n in pivot.index], fontsize=9)
    ax.set_ylabel("SLA Breach Count")
    ax.legend(title="Priority", fontsize=9)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "06_sla_breaches_by_property.png")


# ── chart 7: market vs actual rent ────────────────────────────────────────────

def chart_rent_comparison():
    df = pd.read_csv(f"{DATA}/feat_property_kpis.csv") \
           .sort_values("avg_market_rent", ascending=False)

    fig, ax = plt.subplots(figsize=(12,5))
    title_block(fig, "Avg Market Rent vs Avg Actual Rent by Property",
                "Gap shows loss-to-lease — revenue left on the table")

    x, w = np.arange(len(df)), 0.35
    ax.bar(x-w/2, df["avg_market_rent"], w,
           label="Market Rent", color=DG, alpha=0.88, zorder=3)
    ax.bar(x+w/2, df["avg_actual_rent"], w,
           label="Actual Rent", color=GLD, alpha=0.88, zorder=3)

    # annotate the gap
    for i, (mkt, act) in enumerate(zip(df["avg_market_rent"], df["avg_actual_rent"])):
        ax.annotate(f"-${mkt-act:.0f}", xy=(i, act),
                    xytext=(i, act-80), ha="center",
                    fontsize=8, color=RED, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ","\n") for n in df["name"]], fontsize=9)
    ax.set_ylabel("Monthly Rent ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:,.0f}"))
    ax.legend(fontsize=10)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "07_market_vs_actual_rent.png")


# ── chart 8: unit mix by property ─────────────────────────────────────────────

def chart_unit_mix():
    df    = pd.read_csv(f"{DATA}/feat_units.csv")
    pivot = df.groupby(["name","unit_type"]).size().unstack(fill_value=0)
    pivot = pivot.div(pivot.sum(axis=1), axis=0) * 100

    utypes = ["Studio","1BR/1BA","2BR/1BA","2BR/2BA","3BR/2BA"]
    utypes = [u for u in utypes if u in pivot.columns]
    colors = ["#1A3A2A","#1A6B3A","#C8A951","#D4813A","#C62828"]

    fig, ax = plt.subplots(figsize=(13,5))
    title_block(fig, "Unit Mix Distribution by Property",
                "Percentage of each unit type per property")

    bottom = np.zeros(len(pivot))
    for utype, color in zip(utypes, colors):
        vals = pivot[utype].values
        ax.bar(pivot.index, vals, bottom=bottom,
               label=utype, color=color, alpha=0.88, width=0.6, zorder=3)
        for i, (v,b) in enumerate(zip(vals, bottom)):
            if v > 5:  # only label if big enough to read
                ax.text(i, b+v/2, f"{v:.0f}%",
                        ha="center", va="center",
                        fontsize=8, color="white", fontweight="bold")
        bottom += vals

    ax.set_ylabel("Share of Units (%)")
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_xticklabels([n.replace(" ","\n") for n in pivot.index], fontsize=9)
    ax.legend(title="Unit Type", fontsize=9, loc="upper right", ncol=5)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "08_unit_mix_by_property.png")


# ── chart 9: performance heatmap ──────────────────────────────────────────────

def chart_performance_heatmap():
    df = pd.read_csv(f"{DATA}/feat_property_kpis.csv")
    df = df.set_index("name")

    kpis = {
        "Occupancy %":     "occupancy_rate",
        "Collection %":    "collection_rate_pct",
        "Vac. (inverted)": "vacancy_rate",
        "Loss-to-Lease %": "loss_to_lease_pct",
        "Perf. Score":     "performance_score",
    }

    heat = df[[v for v in kpis.values()]].copy()
    heat.columns = list(kpis.keys())

    # invert vacancy and LTL so green = good everywhere
    heat["Vac. (inverted)"] = 100 - heat["Vac. (inverted)"]
    heat["Loss-to-Lease %"] = 10  - heat["Loss-to-Lease %"]

    heat_norm = (heat - heat.min()) / (heat.max() - heat.min()) * 100

    fig, ax = plt.subplots(figsize=(11,5))
    title_block(fig, "Property Performance Heatmap",
                "Green = stronger performance | All KPIs normalised 0-100")

    cmap = sns.diverging_palette(10, 130, s=80, l=55, as_cmap=True)
    sns.heatmap(heat_norm, ax=ax, cmap=cmap,
                annot=heat.round(1), fmt=".1f",
                linewidths=0.5, linecolor="#EEEEEE",
                cbar_kws={"label":"Score (normalised)"},
                annot_kws={"size":10})

    ax.tick_params(axis="x", labelsize=10, rotation=15)
    ax.tick_params(axis="y", labelsize=9,  rotation=0)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "09_performance_heatmap.png")


# ── chart 10: delinquency exposure by property ────────────────────────────────

def chart_delinquency():
    df = pd.read_csv(f"{ADHOC}/adhoc1_delinquency.csv")

    summary = df.groupby(["property","payment_status"]).agg(
        accounts   = ("tenant","count"),
        total_owed = ("balance_owed","sum"),
    ).reset_index()

    pivot = summary.pivot_table(
        index="property", columns="payment_status",
        values="total_owed", fill_value=0
    )

    fig, ax = plt.subplots(figsize=(11,5))
    title_block(fig, "Delinquency Exposure by Property — Current Month",
                f"Total exposure: ${df['balance_owed'].sum():,.0f}")

    x    = np.arange(len(pivot))
    w    = 0.35
    cols = pivot.columns.tolist()
    clrs = {"Delinquent":RED,"Partial":AMB}

    for i, col in enumerate(cols):
        offset = (i - len(cols)/2 + 0.5) * w
        vals   = pivot[col].values
        bars   = ax.bar(x+offset, vals, w*0.9, label=col,
                        color=clrs.get(col,GRY), alpha=0.88, zorder=3)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x()+bar.get_width()/2,
                        bar.get_height()+30, f"${v:,.0f}",
                        ha="center", fontsize=8,
                        fontweight="bold", color=DG)

    ax.set_xticks(x)
    ax.set_xticklabels([p.replace(" ","\n") for p in pivot.index], fontsize=9)
    ax.set_ylabel("Balance Owed ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:,.0f}"))
    ax.legend(fontsize=10)
    watermark(ax)
    plt.tight_layout(rect=[0,0,1,0.91])
    save(fig, "10_delinquency_by_property.png")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print("phase 5 — visualizations")
    print("-" * 30)

    chart_occupancy()
    chart_ysr()
    chart_loss_to_lease()
    chart_risk_tiers()
    chart_maintenance_cost()
    chart_sla_breaches()
    chart_rent_comparison()
    chart_unit_mix()
    chart_performance_heatmap()
    chart_delinquency()

    print(f"\n10 charts → {CHARTS}/")
    print("done.")


if __name__ == "__main__":
    main()
