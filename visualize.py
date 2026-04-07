"""
=============================================================
 Sage Ventures – Multifamily Analytics
 PHASE 5: Automated Visualization Engine
 Run:    python visualize.py
 Needs:  pip install pandas matplotlib seaborn
 Run AFTER all previous phases
=============================================================
 Auto-generates 10 publication-ready charts from real data.
 All charts saved to: outputs/charts/
=============================================================
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

# ── PATHS ─────────────────────────────────────────────────────────────────────
DATA_DIR   = "data"
ADHOC_DIR  = "outputs/adhoc"
CHART_DIR  = "outputs/charts"
os.makedirs(CHART_DIR, exist_ok=True)

# ── BRAND PALETTE ─────────────────────────────────────────────────────────────
DARK_GREEN   = "#1A3A2A"
MID_GREEN    = "#1A6B3A"
LIGHT_GREEN  = "#C8E6C9"
ACCENT_GOLD  = "#C8A951"
ACCENT_RED   = "#C62828"
ACCENT_AMBER = "#E65100"
GRAY         = "#888888"
LIGHT_GRAY   = "#F5F5F5"
WHITE        = "#FFFFFF"

PROP_COLORS = [
    "#1A3A2A","#1A6B3A","#2E7D52","#43A066",
    "#C8A951","#D4813A","#C62828","#6A4C93"
]

# ── GLOBAL STYLE ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  WHITE,
    "axes.facecolor":    WHITE,
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
    path = f"{CHART_DIR}/{name}"
    fig.savefig(path, dpi=150, bbox_inches="tight",
                facecolor=WHITE, edgecolor="none")
    plt.close(fig)
    print(f"  ✓  Saved → {path}")

def watermark(ax, text="Sage Ventures Analytics"):
    ax.text(0.99, 0.01, text, transform=ax.transAxes,
            fontsize=8, color="#CCCCCC",
            ha="right", va="bottom", style="italic")

def title_bar(fig, title, subtitle):
    fig.text(0.07, 0.97, title,    fontsize=15, fontweight="bold",
             color=DARK_GREEN, va="top")
    fig.text(0.07, 0.93, subtitle, fontsize=10, color=GRAY, va="top")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Portfolio Occupancy Rate by Property (Horizontal Bar)
# ══════════════════════════════════════════════════════════════════════════════
def chart_occupancy():
    print("\n  [1/10] Portfolio Occupancy by Property...")
    df = pd.read_csv("data/feat_property_kpis.csv") \
           .sort_values("occupancy_rate", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    title_bar(fig, "Portfolio Occupancy Rate by Property",
              "Percentage of units currently occupied | Target: 93%")

    colors = [ACCENT_RED if v < 70 else ACCENT_AMBER if v < 80
              else MID_GREEN for v in df["occupancy_rate"]]

    bars = ax.barh(df["name"], df["occupancy_rate"],
                   color=colors, height=0.55, zorder=3)

    # Target line
    ax.axvline(93, color=DARK_GREEN, linewidth=1.5,
               linestyle="--", label="Target 93%", zorder=4)

    # Value labels
    for bar, val in zip(bars, df["occupancy_rate"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va="center", fontsize=10,
                fontweight="bold", color=DARK_GREEN)

    ax.set_xlim(0, 105)
    ax.set_xlabel("Occupancy Rate (%)")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(loc="lower right", fontsize=9)

    patches = [
        mpatches.Patch(color=MID_GREEN,    label="≥ 80% (On Target)"),
        mpatches.Patch(color=ACCENT_AMBER, label="70–80% (Watch)"),
        mpatches.Patch(color=ACCENT_RED,   label="< 70% (At Risk)"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=9)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "01_occupancy_by_property.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — YSR: Quarterly Revenue Trend (Grouped Bar + Line)
# ══════════════════════════════════════════════════════════════════════════════
def chart_ysr_trend():
    print("  [2/10] YSR Quarterly Revenue Trend...")
    df = pd.read_csv("outputs/adhoc/adhoc5_ysr_portfolio.csv") \
           .sort_values("quarter")

    fig, ax1 = plt.subplots(figsize=(11, 5))
    title_bar(fig, "YSR — Quarterly Revenue Trend",
              "Gross Potential Rent vs Collected Rent with Collection Rate")

    x     = np.arange(len(df))
    width = 0.35

    b1 = ax1.bar(x - width/2, df["gross_potential_rent"]/1e6,
                 width, label="Gross Potential Rent",
                 color=DARK_GREEN, alpha=0.85, zorder=3)
    b2 = ax1.bar(x + width/2, df["collected_rent"]/1e6,
                 width, label="Collected Rent",
                 color=ACCENT_GOLD, alpha=0.85, zorder=3)

    ax1.set_ylabel("Revenue ($M)")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"${v:.1f}M"))
    ax1.set_xticks(x)
    ax1.set_xticklabels(df["quarter"], fontsize=10)

    # Collection rate on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(x, df["collection_rate_pct"], color=ACCENT_RED,
             marker="o", linewidth=2, markersize=6,
             label="Collection Rate %", zorder=5)
    ax2.set_ylabel("Collection Rate (%)", color=ACCENT_RED)
    ax2.set_ylim(90, 100)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax2.tick_params(axis="y", colors=ACCENT_RED)
    ax2.spines["right"].set_edgecolor(ACCENT_RED)

    # Combined legend
    lines  = [b1, b2,
              plt.Line2D([0],[0], color=ACCENT_RED, marker="o", linewidth=2)]
    labels = ["Gross Potential Rent","Collected Rent","Collection Rate %"]
    ax1.legend(lines, labels, loc="upper right", fontsize=9)

    watermark(ax1)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "02_ysr_quarterly_trend.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 3 — Loss-to-Lease by Property (Stacked Bar)
# ══════════════════════════════════════════════════════════════════════════════
def chart_loss_to_lease():
    print("  [3/10] Loss-to-Lease by Property...")
    df = pd.read_csv("outputs/adhoc/adhoc3_loss_to_lease.csv")

    pivot = df.groupby(["property","unit_type"])["annual_revenue_gap"] \
               .sum().unstack(fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=False).drop(columns="total")

    unit_colors = {
        "Studio":  "#1A3A2A","1BR/1BA":"#1A6B3A",
        "2BR/1BA": "#C8A951","2BR/2BA":"#D4813A","3BR/2BA":"#C62828"
    }

    fig, ax = plt.subplots(figsize=(12, 5))
    title_bar(fig, "Annual Loss-to-Lease by Property & Unit Type",
              "Revenue gap between market rent and actual rent collected ($/year)")

    bottom = np.zeros(len(pivot))
    for utype in pivot.columns:
        vals = pivot[utype].values / 1000
        bars = ax.bar(pivot.index, vals, bottom=bottom/1000 if bottom.sum()>0 else bottom,
                      label=utype, color=unit_colors.get(utype, GRAY),
                      alpha=0.88, width=0.6, zorder=3)
        bottom = bottom + pivot[utype].values

    # Total labels on top
    totals = pivot.sum(axis=1).values / 1000
    for i, (prop, total) in enumerate(zip(pivot.index, totals)):
        ax.text(i, total + 2, f"${total:.0f}K",
                ha="center", fontsize=9, fontweight="bold", color=DARK_GREEN)

    ax.set_ylabel("Annual Revenue Gap ($K)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:.0f}K"))
    ax.set_xticklabels([p.replace(" ","\n") for p in pivot.index],
                       fontsize=9)
    ax.legend(title="Unit Type", fontsize=9, title_fontsize=9,
              loc="upper right")
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "03_loss_to_lease_stacked.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 4 — Tenant Risk Tier Distribution (Donut)
# ══════════════════════════════════════════════════════════════════════════════
def chart_risk_tiers():
    print("  [4/10] Tenant Risk Tier Distribution...")
    df     = pd.read_csv("data/feat_tenants.csv")
    counts = df["risk_tier"].value_counts()
    order  = ["Low Risk","Medium Risk","High Risk","Critical"]
    counts = counts.reindex([o for o in order if o in counts.index])

    colors = [MID_GREEN, ACCENT_GOLD, ACCENT_AMBER, ACCENT_RED]

    fig, ax = plt.subplots(figsize=(8, 6))
    title_bar(fig, "Tenant Delinquency Risk Tier Distribution",
              "Based on payment history, partial payments & on-time rate")

    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=None,
        colors=colors[:len(counts)],
        autopct="%1.1f%%",
        pctdistance=0.75,
        startangle=140,
        wedgeprops={"width":0.55, "edgecolor":WHITE, "linewidth":2},
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
        at.set_color(WHITE)

    # Centre text
    ax.text(0, 0, f"{counts.sum():,}\nTenants",
            ha="center", va="center", fontsize=14,
            fontweight="bold", color=DARK_GREEN)

    legend_labels = [f"{t}  ({c:,})" for t, c in zip(counts.index, counts.values)]
    ax.legend(wedges, legend_labels, loc="lower center",
              bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=10)

    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "04_risk_tier_donut.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 5 — Maintenance Cost by Category (Horizontal Bar)
# ══════════════════════════════════════════════════════════════════════════════
def chart_maintenance_cost():
    print("  [5/10] Maintenance Cost by Category...")
    df    = pd.read_csv("outputs/adhoc/adhoc4_maintenance_cost.csv")
    cat   = df.groupby("category")["total_cost"].sum() \
               .sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    title_bar(fig, "Total Maintenance Cost by Category",
              "YTD closed ticket spend across all 8 properties")

    colors = [PROP_COLORS[i % len(PROP_COLORS)] for i in range(len(cat))]
    bars   = ax.barh(cat.index, cat.values/1000, color=colors,
                     height=0.55, zorder=3)

    for bar, val in zip(bars, cat.values/1000):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f"${val:,.0f}K", va="center", fontsize=10,
                fontweight="bold", color=DARK_GREEN)

    ax.set_xlabel("Total Cost ($K)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:.0f}K"))
    ax.set_xlim(0, cat.max()/1000 * 1.20)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "05_maintenance_cost_by_category.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 6 — SLA Breaches by Property & Priority (Grouped Bar)
# ══════════════════════════════════════════════════════════════════════════════
def chart_sla_breaches():
    print("  [6/10] SLA Breaches by Property & Priority...")
    df    = pd.read_csv("outputs/adhoc/adhoc4_sla_breaches.csv")
    pivot = df.pivot_table(index="name", columns="priority",
                           values="sla_breach_count", fill_value=0)

    pri_colors = {"Emergency": ACCENT_RED, "High": ACCENT_AMBER,
                  "Medium": ACCENT_GOLD,  "Low": MID_GREEN}

    fig, ax = plt.subplots(figsize=(12, 5))
    title_bar(fig, "Maintenance SLA Breaches by Property & Priority",
              "Open tickets that exceeded SLA resolution threshold")

    n_props = len(pivot)
    n_pris  = len(pivot.columns)
    x       = np.arange(n_props)
    width   = 0.7 / n_pris

    for i, pri in enumerate(pivot.columns):
        offset = (i - n_pris/2 + 0.5) * width
        vals   = pivot[pri].values
        bars   = ax.bar(x + offset, vals, width*0.9,
                        label=pri,
                        color=pri_colors.get(pri, GRAY),
                        alpha=0.88, zorder=3)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.3, str(int(v)),
                        ha="center", fontsize=8,
                        fontweight="bold", color=DARK_GREEN)

    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ","\n") for n in pivot.index], fontsize=9)
    ax.set_ylabel("SLA Breach Count")
    ax.legend(title="Priority", fontsize=9, title_fontsize=9)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "06_sla_breaches_by_property.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 7 — Market vs Actual Rent by Property (Side-by-Side Bar)
# ══════════════════════════════════════════════════════════════════════════════
def chart_rent_comparison():
    print("  [7/10] Market vs Actual Rent by Property...")
    df = pd.read_csv("data/feat_property_kpis.csv") \
           .sort_values("avg_market_rent", ascending=False)

    fig, ax = plt.subplots(figsize=(12, 5))
    title_bar(fig, "Avg Market Rent vs Avg Actual Rent by Property",
              "Gap reveals loss-to-lease — revenue left on the table")

    x     = np.arange(len(df))
    width = 0.35

    ax.bar(x - width/2, df["avg_market_rent"], width,
           label="Market Rent", color=DARK_GREEN, alpha=0.88, zorder=3)
    ax.bar(x + width/2, df["avg_actual_rent"], width,
           label="Actual Rent", color=ACCENT_GOLD, alpha=0.88, zorder=3)

    # Gap annotation
    for i, (mkt, act) in enumerate(zip(df["avg_market_rent"], df["avg_actual_rent"])):
        gap = mkt - act
        ax.annotate(f"-${gap:.0f}", xy=(i, act), xytext=(i, act - 80),
                    ha="center", fontsize=8, color=ACCENT_RED,
                    fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ","\n") for n in df["name"]], fontsize=9)
    ax.set_ylabel("Monthly Rent ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:,.0f}"))
    ax.legend(fontsize=10)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "07_market_vs_actual_rent.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 8 — Unit Mix Distribution (Stacked 100% Bar per Property)
# ══════════════════════════════════════════════════════════════════════════════
def chart_unit_mix():
    print("  [8/10] Unit Mix Distribution by Property...")
    df    = pd.read_csv("data/feat_units.csv")
    pivot = df.groupby(["name","unit_type"]).size().unstack(fill_value=0)
    pivot = pivot.div(pivot.sum(axis=1), axis=0) * 100

    utypes = ["Studio","1BR/1BA","2BR/1BA","2BR/2BA","3BR/2BA"]
    utypes = [u for u in utypes if u in pivot.columns]
    colors = ["#1A3A2A","#1A6B3A","#C8A951","#D4813A","#C62828"]

    fig, ax = plt.subplots(figsize=(13, 5))
    title_bar(fig, "Unit Mix Distribution by Property",
              "Percentage of each unit type in the portfolio")

    bottom = np.zeros(len(pivot))
    for utype, color in zip(utypes, colors):
        if utype not in pivot.columns:
            continue
        vals = pivot[utype].values
        ax.bar(pivot.index, vals, bottom=bottom,
               label=utype, color=color, alpha=0.88,
               width=0.6, zorder=3)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v > 5:
                ax.text(i, b + v/2, f"{v:.0f}%",
                        ha="center", va="center",
                        fontsize=8, color=WHITE, fontweight="bold")
        bottom += vals

    ax.set_ylabel("Share of Units (%)")
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_xticklabels([n.replace(" ","\n") for n in pivot.index], fontsize=9)
    ax.legend(title="Unit Type", fontsize=9, title_fontsize=9,
              loc="upper right", ncol=5)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "08_unit_mix_by_property.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 9 — Performance Score Heatmap (Property × KPI)
# ══════════════════════════════════════════════════════════════════════════════
def chart_performance_heatmap():
    print("  [9/10] Property Performance Heatmap...")
    df = pd.read_csv("data/feat_property_kpis.csv")
    df = df.set_index("name")

    kpis = {
        "Occupancy Rate":      "occupancy_rate",
        "Collection Rate":     "collection_rate_pct",
        "Vacancy Rate (inv.)": "vacancy_rate",
        "Loss-to-Lease %":     "loss_to_lease_pct",
        "Performance Score":   "performance_score",
    }

    heat = df[[v for v in kpis.values()]].copy()
    heat.columns = list(kpis.keys())

    # Invert vacancy & loss-to-lease so green = good
    heat["Vacancy Rate (inv.)"] = 100 - heat["Vacancy Rate (inv.)"]
    heat["Loss-to-Lease %"]     = 10  - heat["Loss-to-Lease %"]

    heat_norm = (heat - heat.min()) / (heat.max() - heat.min()) * 100

    fig, ax = plt.subplots(figsize=(11, 5))
    title_bar(fig, "Property Performance Heatmap",
              "Green = better performance | All KPIs normalised 0–100")

    cmap = sns.diverging_palette(10, 130, s=80, l=55, as_cmap=True)
    sns.heatmap(heat_norm, ax=ax, cmap=cmap,
                annot=heat.round(1), fmt=".1f",
                linewidths=0.5, linecolor="#EEEEEE",
                cbar_kws={"label":"Score (normalised)"},
                annot_kws={"size":10})

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", labelsize=10, rotation=15)
    ax.tick_params(axis="y", labelsize=9,  rotation=0)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "09_performance_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 10 — Delinquency Exposure by Property (Bar + Table combo)
# ══════════════════════════════════════════════════════════════════════════════
def chart_delinquency():
    print("  [10/10] Delinquency Exposure by Property...")
    df = pd.read_csv("outputs/adhoc/adhoc1_delinquency.csv")

    prop_summary = df.groupby(["property","payment_status"]).agg(
        accounts    = ("tenant","count"),
        total_owed  = ("balance_owed","sum"),
    ).reset_index()

    pivot = prop_summary.pivot_table(
        index="property", columns="payment_status",
        values="total_owed", fill_value=0
    )

    fig, ax = plt.subplots(figsize=(11, 5))
    title_bar(fig, "Delinquency Exposure by Property — Current Month",
              f"Total portfolio exposure: ${df['balance_owed'].sum():,.0f}")

    x     = np.arange(len(pivot))
    width = 0.35
    cols  = pivot.columns.tolist()
    clrs  = {"Delinquent": ACCENT_RED, "Partial": ACCENT_AMBER}

    for i, col in enumerate(cols):
        offset = (i - len(cols)/2 + 0.5) * width
        vals   = pivot[col].values
        bars   = ax.bar(x + offset, vals, width*0.9,
                        label=col,
                        color=clrs.get(col, GRAY),
                        alpha=0.88, zorder=3)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 30,
                        f"${v:,.0f}", ha="center",
                        fontsize=8, fontweight="bold",
                        color=DARK_GREEN)

    ax.set_xticks(x)
    ax.set_xticklabels([p.replace(" ","\n") for p in pivot.index], fontsize=9)
    ax.set_ylabel("Balance Owed ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v:,.0f}"))
    ax.legend(fontsize=10)
    watermark(ax)
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "10_delinquency_by_property.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("\n" + "="*55)
    print("  Sage Ventures — Phase 5: Visualization Engine")
    print("="*55)

    chart_occupancy()
    chart_ysr_trend()
    chart_loss_to_lease()
    chart_risk_tiers()
    chart_maintenance_cost()
    chart_sla_breaches()
    chart_rent_comparison()
    chart_unit_mix()
    chart_performance_heatmap()
    chart_delinquency()

    print("\n" + "="*55)
    print("  Phase 5 Complete ✓")
    print(f"  10 charts saved → {CHART_DIR}/")
    print("="*55)
    print("""
  Charts generated:
  01  Occupancy Rate by Property (horizontal bar)
  02  YSR Quarterly Revenue Trend (grouped bar + line)
  03  Loss-to-Lease by Property & Unit Type (stacked bar)
  04  Tenant Risk Tier Distribution (donut)
  05  Maintenance Cost by Category (horizontal bar)
  06  SLA Breaches by Property & Priority (grouped bar)
  07  Market vs Actual Rent by Property (side-by-side bar)
  08  Unit Mix Distribution by Property (100% stacked bar)
  09  Property Performance Heatmap (normalised KPI grid)
  10  Delinquency Exposure by Property (grouped bar)
    """)

if __name__ == "__main__":
    main()
