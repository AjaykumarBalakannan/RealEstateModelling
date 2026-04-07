"""
excel_report.py

auto-generates a formatted 7-sheet excel workbook from the database.
this is the kind of report you'd schedule to run on the 1st of every month
and land in the CFO's inbox automatically.

run after generate_data.py, feature_engineering.py, adhoc_analysis.py.

run:  python excel_report.py
deps: pip install pandas openpyxl
"""

import sqlite3
import pandas as pd
import os
from datetime import date
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, Reference

DB  = "data/sage_ventures.db"
OUT = "outputs"
os.makedirs(OUT, exist_ok=True)

TODAY    = date.today()
RPT_DATE = TODAY.strftime("%B %d, %Y")
OUTFILE  = f"{OUT}/SageVentures_Analytics_Report_{TODAY.strftime('%Y%m%d')}.xlsx"

# brand colors
C_DARK_GREEN  = "1A3A2A"
C_MID_GREEN   = "1A6B3A"
C_LIGHT_GREEN = "E8F5E9"
C_GOLD        = "C8A951"
C_WHITE       = "FFFFFF"
C_LIGHT_GRAY  = "F5F5F5"
C_DARK_GRAY   = "444444"
C_RED_LIGHT   = "FFEBEE"
C_RED_DARK    = "C62828"
C_AMBER_LIGHT = "FFF8E1"
C_AMBER_DARK  = "E65100"


# ── style helpers ─────────────────────────────────────────────────────────────

def fill(hex_c):
    return PatternFill("solid", fgColor=hex_c)

def font(bold=False, color=C_DARK_GRAY, size=11, italic=False):
    return Font(bold=bold, color=color, size=size,
                italic=italic, name="Calibri")

def align(h="left", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def set_widths(ws, widths):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def write_header_row(ws, row, cols, bg=C_DARK_GREEN, fg=C_WHITE):
    for i, val in enumerate(cols, 1):
        c = ws.cell(row=row, column=i, value=val)
        c.fill      = fill(bg)
        c.font      = font(bold=True, color=fg, size=10)
        c.border    = thin_border()
        c.alignment = align("center")


def write_data_row(ws, row, vals, bg=C_WHITE, money_cols=None):
    money_cols = money_cols or []
    for i, val in enumerate(vals, 1):
        c = ws.cell(row=row, column=i, value=val)
        c.fill      = fill(bg)
        c.font      = font(color=C_DARK_GRAY)
        c.border    = thin_border()
        c.alignment = align("left" if isinstance(val,str) else "right")
        if i in money_cols:
            c.number_format = "$#,##0"


def title_block(ws, title, subtitle):
    # sage ventures branding at top of each sheet
    ws.merge_cells("A1:H1")
    h = ws["A1"]
    h.value     = "SAGE VENTURES"
    h.font      = Font(bold=True, size=14, color=C_WHITE, name="Calibri")
    h.fill      = fill(C_DARK_GREEN)
    h.alignment = align("left","center")
    ws.row_dimensions[1].height = 26

    ws.merge_cells("A2:H2")
    t = ws["A2"]
    t.value     = title
    t.font      = Font(bold=True, size=12, color=C_DARK_GREEN, name="Calibri")
    t.fill      = fill(C_LIGHT_GREEN)
    t.alignment = align("left","center")

    ws.merge_cells("A3:H3")
    s = ws["A3"]
    s.value     = f"Report Date: {RPT_DATE}  |  {subtitle}"
    s.font      = Font(size=9, color=C_DARK_GRAY, italic=True, name="Calibri")
    s.fill      = fill(C_LIGHT_GRAY)
    s.alignment = align("left","center")
    ws.row_dimensions[3].height = 16


# ── sheet 1: executive summary ────────────────────────────────────────────────

def sheet_executive(wb, conn):
    ws = wb.create_sheet("Executive Summary")
    ws.sheet_view.showGridLines = False
    title_block(ws, "Portfolio Executive Summary", "All Properties")

    kpi = pd.read_sql("""
    SELECT
        COUNT(DISTINCT p.property_id)                              total_props,
        COUNT(DISTINCT u.unit_id)                                  total_units,
        COUNT(DISTINCT t.tenant_id)                                occupied,
        ROUND(COUNT(DISTINCT t.tenant_id)*100.0/COUNT(DISTINCT u.unit_id),1) occ_pct,
        ROUND(AVG(u.market_rent),0)                                avg_mkt,
        ROUND(AVG(t.monthly_rent),0)                               avg_actual,
        ROUND(SUM(t.monthly_rent),0)                               monthly_rev
    FROM properties p
    JOIN units u ON p.property_id=u.property_id
    LEFT JOIN tenants t ON u.unit_id=t.unit_id AND t.status='Active'
    """, conn).iloc[0]

    # quick KPI summary rows before the property table
    ws.row_dimensions[5].height = 8
    kpis = [
        ("Portfolio Occupancy", f"{kpi['occ_pct']}%"),
        ("Total Units",         f"{int(kpi['total_units']):,}"),
        ("Occupied Units",      f"{int(kpi['occupied']):,}"),
        ("Avg Market Rent",     f"${kpi['avg_mkt']:,.0f}"),
        ("Avg Actual Rent",     f"${kpi['avg_actual']:,.0f}"),
        ("Monthly Revenue",     f"${kpi['monthly_rev']:,.0f}"),
    ]
    for i, (lbl, val) in enumerate(kpis):
        col = 1 + (i % 4) * 2
        row = 6 + (i // 4) * 3
        ws.merge_cells(start_row=row,   start_column=col, end_row=row,   end_column=col+1)
        ws.merge_cells(start_row=row+1, start_column=col, end_row=row+1, end_column=col+1)
        lc = ws.cell(row=row,   column=col, value=lbl)
        vc = ws.cell(row=row+1, column=col, value=val)
        lc.font = Font(size=9, color=C_DARK_GRAY, name="Calibri")
        vc.font = Font(bold=True, size=16, color=C_DARK_GREEN, name="Calibri")
        for cell in [lc, vc]:
            cell.fill      = fill(C_LIGHT_GREEN)
            cell.alignment = align("center")

    # property table starts at row 13
    start = 13
    ws.cell(row=start, column=1, value="Property Performance").font = \
        Font(bold=True, size=11, color=C_DARK_GREEN, name="Calibri")

    cols = ["Property","City","Units","Occupied","Occ %",
            "Avg Mkt Rent","Avg Actual Rent","Monthly Rev"]
    write_header_row(ws, start+1, cols)

    props = pd.read_sql("""
    SELECT p.name, p.city, p.total_units,
        COUNT(t.tenant_id) occ,
        ROUND(COUNT(t.tenant_id)*100.0/p.total_units,1) occ_pct,
        ROUND(AVG(u.market_rent),0) avg_mkt,
        ROUND(AVG(t.monthly_rent),0) avg_actual,
        ROUND(SUM(t.monthly_rent),0) monthly_rev
    FROM properties p
    JOIN units u ON p.property_id=u.property_id
    LEFT JOIN tenants t ON u.unit_id=t.unit_id AND t.status='Active'
    GROUP BY p.property_id ORDER BY monthly_rev DESC
    """, conn)

    for i, (_, r) in enumerate(props.iterrows()):
        bg = C_LIGHT_GRAY if i%2==0 else C_WHITE
        write_data_row(ws, start+2+i,
                       [r["name"],r["city"],r["total_units"],r["occ"],
                        r["occ_pct"]/100, r["avg_mkt"],r["avg_actual"],r["monthly_rev"]],
                       bg=bg, money_cols=[6,7,8])
        occ_cell = ws.cell(row=start+2+i, column=5)
        occ_cell.number_format = "0.0%"
        # color code occupancy
        if r["occ_pct"] < 80:
            occ_cell.fill = fill(C_RED_LIGHT)
            occ_cell.font = font(color=C_RED_DARK, bold=True)
        elif r["occ_pct"] >= 90:
            occ_cell.fill = fill(C_LIGHT_GREEN)
            occ_cell.font = font(color=C_MID_GREEN, bold=True)

    set_widths(ws, {"A":26,"B":14,"C":8,"D":10,"E":8,
                    "F":15,"G":15,"H":14})


# ── sheet 2: rent roll ────────────────────────────────────────────────────────

def sheet_rent_roll(wb, conn):
    ws = wb.create_sheet("Rent Roll")
    ws.sheet_view.showGridLines = False
    title_block(ws, "Rent Roll — Current Month",
                "All active tenants and payment status")

    last = pd.read_sql("SELECT MAX(period_month) mo FROM rent_roll", conn).iloc[0]["mo"]

    df = pd.read_sql(f"""
    SELECT
        p.name property, p.city, u.unit_number, u.unit_type,
        t.full_name tenant, t.lease_start, t.lease_end,
        t.monthly_rent, u.market_rent,
        ROUND(u.market_rent-t.monthly_rent,0) loss_to_lease,
        r.amount_due, r.amount_paid,
        ROUND(r.amount_due-r.amount_paid,0) balance,
        r.status
    FROM rent_roll r
    JOIN tenants    t ON r.tenant_id   = t.tenant_id
    JOIN units      u ON r.unit_id     = u.unit_id
    JOIN properties p ON r.property_id = p.property_id
    WHERE r.period_month = '{last}'
    ORDER BY p.name, u.unit_number
    """, conn)

    status_colors = {
        "Paid":       (C_LIGHT_GREEN,  C_MID_GREEN),
        "Partial":    (C_AMBER_LIGHT,  C_AMBER_DARK),
        "Delinquent": (C_RED_LIGHT,    C_RED_DARK),
    }

    cols = ["Property","City","Unit","Type","Tenant",
            "Lease Start","Lease End","Monthly Rent","Market Rent",
            "Loss-to-Lease","Amount Due","Amount Paid","Balance","Status"]
    write_header_row(ws, 5, cols)

    for i, (_, r) in enumerate(df.iterrows()):
        bg = C_LIGHT_GRAY if i%2==0 else C_WHITE
        write_data_row(ws, 6+i,
                       [r["property"],r["city"],r["unit_number"],r["unit_type"],
                        r["tenant"],r["lease_start"],r["lease_end"],
                        r["monthly_rent"],r["market_rent"],r["loss_to_lease"],
                        r["amount_due"],r["amount_paid"],r["balance"],r["status"]],
                       bg=bg, money_cols=[8,9,10,11,12,13])
        sc = ws.cell(row=6+i, column=14)
        if r["status"] in status_colors:
            bg_c, fg_c = status_colors[r["status"]]
            sc.fill = fill(bg_c)
            sc.font = font(color=fg_c, bold=True)

    ws.freeze_panes = "A6"
    set_widths(ws, {"A":22,"B":14,"C":7,"D":11,"E":22,
                    "F":12,"G":12,"H":13,"I":13,"J":13,
                    "K":12,"L":12,"M":10,"N":12})


# ── sheet 3: lease expiration ──────────────────────────────────────────────────

def sheet_lease_expiration(wb, conn):
    ws = wb.create_sheet("Lease Expiration")
    ws.sheet_view.showGridLines = False
    title_block(ws, "Lease Expiration Pipeline", "Next 90 days — renewal risk")

    df = pd.read_sql("""
    SELECT
        p.name property, p.city, t.full_name tenant,
        u.unit_number, u.unit_type, t.monthly_rent, t.lease_end,
        CAST(julianday(t.lease_end)-julianday('now') AS INT) days_to_expiry,
        CASE
          WHEN julianday(t.lease_end)-julianday('now') < 0    THEN 'Expired'
          WHEN julianday(t.lease_end)-julianday('now') <= 30  THEN '0-30 Days'
          WHEN julianday(t.lease_end)-julianday('now') <= 60  THEN '31-60 Days'
          ELSE '61-90 Days'
        END bucket,
        t.status
    FROM tenants t
    JOIN units      u ON t.unit_id     = u.unit_id
    JOIN properties p ON u.property_id = p.property_id
    WHERE julianday(t.lease_end)-julianday('now') <= 90
      AND t.status = 'Active'
    ORDER BY days_to_expiry
    """, conn)

    bucket_colors = {
        "Expired":    (C_RED_LIGHT,   C_RED_DARK),
        "0-30 Days":  (C_RED_LIGHT,   C_RED_DARK),
        "31-60 Days": (C_AMBER_LIGHT, C_AMBER_DARK),
        "61-90 Days": (C_LIGHT_GREEN, C_MID_GREEN),
    }

    cols = ["Property","City","Tenant","Unit","Type",
            "Monthly Rent","Lease End","Days to Expiry","Bucket","Status"]
    write_header_row(ws, 5, cols)

    for i, (_, r) in enumerate(df.iterrows()):
        bg = C_LIGHT_GRAY if i%2==0 else C_WHITE
        write_data_row(ws, 6+i,
                       [r["property"],r["city"],r["tenant"],r["unit_number"],
                        r["unit_type"],r["monthly_rent"],r["lease_end"],
                        r["days_to_expiry"],r["bucket"],r["status"]],
                       bg=bg, money_cols=[6])
        bc = ws.cell(row=6+i, column=9)
        if r["bucket"] in bucket_colors:
            bg_c, fg_c = bucket_colors[r["bucket"]]
            bc.fill = fill(bg_c)
            bc.font = font(color=fg_c, bold=True)

    ws.freeze_panes = "A6"
    set_widths(ws, {"A":22,"B":14,"C":22,"D":7,"E":11,
                    "F":13,"G":12,"H":14,"I":12,"J":12})


# ── sheet 4: delinquency ──────────────────────────────────────────────────────

def sheet_delinquency(wb, conn):
    ws = wb.create_sheet("Delinquency Report")
    ws.sheet_view.showGridLines = False
    title_block(ws, "Delinquency Report — Current Month",
                "Unpaid and partial balance accounts")

    last = pd.read_sql("SELECT MAX(period_month) mo FROM rent_roll", conn).iloc[0]["mo"]

    df = pd.read_sql(f"""
    SELECT
        p.name property, p.city, t.full_name tenant,
        u.unit_number, u.unit_type, r.period_month,
        r.amount_due, r.amount_paid,
        ROUND(r.amount_due-r.amount_paid,0) balance_owed,
        r.status, t.lease_end
    FROM rent_roll r
    JOIN tenants    t ON r.tenant_id   = t.tenant_id
    JOIN units      u ON r.unit_id     = u.unit_id
    JOIN properties p ON r.property_id = p.property_id
    WHERE r.status IN ('Delinquent','Partial')
      AND r.period_month = '{last}'
    ORDER BY balance_owed DESC
    """, conn)

    # summary at top
    total = df["balance_owed"].sum()
    ws.cell(row=5,column=1,value="Delinquent Accounts:").font = font(bold=True)
    ws.cell(row=5,column=2,value=len(df[df["status"]=="Delinquent"])).font = font(color=C_RED_DARK,bold=True)
    ws.cell(row=5,column=3,value="Total Exposure:").font = font(bold=True)
    ws.cell(row=5,column=4,value=total).font = font(color=C_RED_DARK,bold=True)
    ws.cell(row=5,column=4).number_format = "$#,##0"

    cols = ["Property","City","Tenant","Unit","Type",
            "Period","Amount Due","Amount Paid","Balance Owed","Status","Lease End"]
    write_header_row(ws, 7, cols, bg=C_RED_DARK)

    for i, (_, r) in enumerate(df.iterrows()):
        bg = C_RED_LIGHT if r["status"]=="Delinquent" else C_AMBER_LIGHT
        write_data_row(ws, 8+i,
                       [r["property"],r["city"],r["tenant"],r["unit_number"],
                        r["unit_type"],r["period_month"],r["amount_due"],
                        r["amount_paid"],r["balance_owed"],r["status"],r["lease_end"]],
                       bg=bg, money_cols=[7,8,9])

    set_widths(ws, {"A":22,"B":14,"C":22,"D":7,"E":11,
                    "F":10,"G":12,"H":12,"I":12,"J":12,"K":12})


# ── sheet 5: YSR revenue trend ────────────────────────────────────────────────

def sheet_ysr(wb, conn):
    ws = wb.create_sheet("YSR Revenue Trend")
    ws.sheet_view.showGridLines = False
    title_block(ws, "YSR — Yield Summary Report",
                "Monthly GPR vs Collected Rent | 15-month view")

    df = pd.read_sql("""
    SELECT
        period_month,
        ROUND(SUM(amount_due),0)  gpr,
        ROUND(SUM(amount_paid),0) collected,
        ROUND(SUM(amount_due)-SUM(amount_paid),0) uncollected,
        ROUND(SUM(amount_paid)*100.0/SUM(amount_due),1) coll_rate
    FROM rent_roll
    GROUP BY period_month
    ORDER BY period_month
    """, conn)

    cols = ["Period","Gross Potential Rent","Collected Rent","Uncollected","Collection Rate %"]
    write_header_row(ws, 5, cols)

    for i, (_, r) in enumerate(df.iterrows()):
        bg = C_LIGHT_GRAY if i%2==0 else C_WHITE
        write_data_row(ws, 6+i,
                       [r["period_month"],r["gpr"],r["collected"],
                        r["uncollected"],r["coll_rate"]/100],
                       bg=bg, money_cols=[2,3,4])
        ws.cell(row=6+i,column=5).number_format = "0.0%"

    # bar chart
    chart = BarChart()
    chart.type  = "col"
    chart.title = "GPR vs Collected Rent"
    chart.y_axis.title = "Revenue ($)"
    chart.width  = 22
    chart.height = 12
    chart.style  = 10

    data = Reference(ws, min_col=2, max_col=3, min_row=5, max_row=5+len(df))
    cats = Reference(ws, min_col=1, min_row=6, max_row=5+len(df))
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.series[0].graphicalProperties.solidFill = C_DARK_GREEN
    chart.series[1].graphicalProperties.solidFill = C_GOLD
    ws.add_chart(chart, "G5")

    set_widths(ws, {"A":12,"B":22,"C":18,"D":14,"E":16})


# ── sheet 6: maintenance ──────────────────────────────────────────────────────

def sheet_maintenance(wb, conn):
    ws = wb.create_sheet("Maintenance Analysis")
    ws.sheet_view.showGridLines = False
    title_block(ws, "Maintenance Cost & SLA Analysis",
                "Open tickets, resolution times, cost by property and category")

    df = pd.read_sql("""
    SELECT
        p.name property, m.category, m.priority,
        COUNT(m.ticket_id) total_tickets,
        SUM(CASE WHEN m.status='Open' THEN 1 ELSE 0 END) open_tickets,
        ROUND(AVG(CASE WHEN m.close_date IS NOT NULL
              THEN julianday(m.close_date)-julianday(m.open_date) END),1) avg_res_days,
        ROUND(SUM(m.cost),0) total_cost,
        ROUND(AVG(m.cost),0) avg_cost
    FROM maintenance m
    JOIN properties p ON m.property_id = p.property_id
    GROUP BY p.property_id, m.category, m.priority
    ORDER BY total_cost DESC
    """, conn)

    priority_colors = {
        "Emergency": (C_RED_LIGHT,   C_RED_DARK),
        "High":      (C_AMBER_LIGHT, C_AMBER_DARK),
    }

    cols = ["Property","Category","Priority","Total Tickets",
            "Open","Avg Res. Days","Total Cost","Avg Cost"]
    write_header_row(ws, 5, cols)

    for i, (_, r) in enumerate(df.iterrows()):
        bg = C_LIGHT_GRAY if i%2==0 else C_WHITE
        write_data_row(ws, 6+i,
                       [r["property"],r["category"],r["priority"],
                        r["total_tickets"],r["open_tickets"],
                        r["avg_res_days"],r["total_cost"],r["avg_cost"]],
                       bg=bg, money_cols=[7,8])
        pc = ws.cell(row=6+i, column=3)
        if r["priority"] in priority_colors:
            bg_c, fg_c = priority_colors[r["priority"]]
            pc.fill = fill(bg_c)
            pc.font = font(color=fg_c, bold=True)

    set_widths(ws, {"A":22,"B":14,"C":11,"D":13,"E":8,
                    "F":14,"G":12,"H":10})


# ── sheet 7: feature engineering insights ─────────────────────────────────────

def sheet_feature_insights(wb):
    ws = wb.create_sheet("Feature Engineering")
    ws.sheet_view.showGridLines = False
    title_block(ws, "Feature-Engineered Metrics",
                "Derived analytics — risk scores, grades, loss-to-lease")

    try:
        df = pd.read_csv("data/feat_property_kpis.csv")
        want = ["name","city","occupancy_rate","vacancy_rate",
                "avg_market_rent","avg_actual_rent","loss_to_lease_pct",
                "collection_rate_pct","revenue_per_unit",
                "performance_score","performance_grade"]
        df = df[[c for c in want if c in df.columns]]

        cols = ["Property","City","Occupancy %","Vacancy %",
                "Avg Mkt Rent","Avg Actual Rent","Loss-to-Lease %",
                "Collection %","Rev/Unit","Perf Score","Grade"]
        write_header_row(ws, 5, cols)

        grade_colors = {
            "A+": (C_LIGHT_GREEN, C_MID_GREEN),
            "A":  (C_LIGHT_GREEN, C_MID_GREEN),
            "B":  (C_AMBER_LIGHT, C_AMBER_DARK),
            "C":  (C_RED_LIGHT,   C_RED_DARK),
        }
        for i, (_, r) in enumerate(df.iterrows()):
            bg   = C_LIGHT_GRAY if i%2==0 else C_WHITE
            vals = [r.get(c,"") for c in df.columns]
            write_data_row(ws, 6+i, vals, bg=bg, money_cols=[5,6,9])
            gc = ws.cell(row=6+i, column=len(df.columns))
            g  = str(r.get("performance_grade",""))
            if g in grade_colors:
                bg_c, fg_c = grade_colors[g]
                gc.fill = fill(bg_c)
                gc.font = font(color=fg_c, bold=True)

        set_widths(ws, {"A":22,"B":14,"C":11,"D":10,"E":14,
                        "F":14,"G":13,"H":12,"I":10,"J":11,"K":7})
    except FileNotFoundError:
        ws.cell(row=5, column=1,
                value="run feature_engineering.py first to populate this sheet.")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    wb   = Workbook()
    wb.remove(wb.active)  # remove blank default sheet

    print("phase 4 — excel report")
    print("-" * 30)

    print("  executive summary...")
    sheet_executive(wb, conn)

    print("  rent roll...")
    sheet_rent_roll(wb, conn)

    print("  lease expiration...")
    sheet_lease_expiration(wb, conn)

    print("  delinquency report...")
    sheet_delinquency(wb, conn)

    print("  YSR revenue trend...")
    sheet_ysr(wb, conn)

    print("  maintenance analysis...")
    sheet_maintenance(wb, conn)

    print("  feature engineering insights...")
    sheet_feature_insights(wb)

    conn.close()
    wb.save(OUTFILE)

    print(f"\nreport → {OUTFILE}")
    print("7 sheets | conditional formatting | charts")
    print("done.")


if __name__ == "__main__":
    main()
