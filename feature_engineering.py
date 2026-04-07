"""
feature_engineering.py

takes the raw sqlite tables and adds calculated columns
that are actually useful for analysis — risk scores,
lease urgency, loss-to-lease, SLA flags etc.

run after generate_data.py.

run:  python feature_engineering.py
deps: pip install pandas numpy
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import date
import os

DB  = "data/sage_ventures.db"
OUT = "data"
os.makedirs(OUT, exist_ok=True)

TODAY = pd.Timestamp(date.today())


def load(conn):
    props   = pd.read_sql("SELECT * FROM properties",        conn)
    units   = pd.read_sql("SELECT * FROM units",             conn)
    tenants = pd.read_sql("SELECT * FROM tenants",           conn)
    rr      = pd.read_sql("SELECT * FROM rent_roll",         conn)
    maint   = pd.read_sql("SELECT * FROM maintenance",       conn)
    return props, units, tenants, rr, maint


# ── tenant features ────────────────────────────────────────────────────────────

def tenant_features(tenants, units, rr):
    print("  tenants...")
    df = tenants.copy()
    df["lease_start"] = pd.to_datetime(df["lease_start"])
    df["lease_end"]   = pd.to_datetime(df["lease_end"])

    df["lease_duration_days"] = (df["lease_end"] - df["lease_start"]).dt.days
    df["days_to_expiry"]      = (df["lease_end"] - TODAY).dt.days
    df["lease_expired"]       = (df["lease_end"] < TODAY).astype(int)

    def expiry_bucket(d):
        if d < 0:    return "Expired"
        if d <= 30:  return "0-30 Days"
        if d <= 60:  return "31-60 Days"
        if d <= 90:  return "61-90 Days"
        return "90+ Days"

    df["expiry_bucket"] = df["days_to_expiry"].apply(expiry_bucket)

    df["lease_term_type"] = df["lease_duration_days"].apply(
        lambda d: "Short-Term (<6mo)" if d < 180
             else "Standard (6-12mo)" if d <= 365
             else "Long-Term (>12mo)"
    )

    # merge market rent from units so we can calc loss-to-lease per tenant
    df = df.merge(
        units[["unit_id","market_rent","unit_type","sqft"]],
        on="unit_id", how="left"
    )
    df["loss_to_lease"]     = df["market_rent"] - df["monthly_rent"]
    df["loss_to_lease_pct"] = (df["loss_to_lease"] / df["market_rent"] * 100).round(2)
    df["concession_flag"]   = (df["loss_to_lease_pct"] > 5).astype(int)

    # payment behaviour from rent roll
    pay = rr.groupby("tenant_id").agg(
        total_charges    = ("payment_id", "count"),
        paid_on_time     = ("status",     lambda x: (x=="Paid").sum()),
        partial_count    = ("status",     lambda x: (x=="Partial").sum()),
        delinquent_count = ("status",     lambda x: (x=="Delinquent").sum()),
        total_due        = ("amount_due",  "sum"),
        total_paid       = ("amount_paid", "sum"),
    ).reset_index()

    pay["collection_rate"]     = (pay["total_paid"] / pay["total_due"] * 100).round(2)
    pay["payment_reliability"] = (pay["paid_on_time"] / pay["total_charges"] * 100).round(2)

    # delinquency risk score 0-100
    # weights: delinquent months hurt most, partials less so
    pay["delinquency_risk_score"] = (
        (pay["delinquent_count"] * 30) +
        (pay["partial_count"]    * 10) +
        ((100 - pay["payment_reliability"]) * 0.6)
    ).clip(0, 100).round(1)

    pay["risk_tier"] = pd.cut(
        pay["delinquency_risk_score"],
        bins=[-1, 10, 30, 60, 100],
        labels=["Low Risk","Medium Risk","High Risk","Critical"]
    )

    df = df.merge(pay, on="tenant_id", how="left")
    df.to_csv(f"{OUT}/feat_tenants.csv", index=False)
    print(f"    {len(df):,} rows, {len(df.columns)} columns")
    return df


# ── unit features ──────────────────────────────────────────────────────────────

def unit_features(units, props, tenants):
    print("  units...")
    df = units.copy()
    df = df.merge(
        props[["property_id","name","city","property_type","year_built"]],
        on="property_id", how="left"
    )

    df["is_vacant"]             = (df["status"] == "Vacant").astype(int)
    df["annual_market_revenue"] = df["market_rent"] * 12
    df["rent_per_sqft"]         = (df["market_rent"] / df["sqft"]).round(2)
    df["property_age"]          = date.today().year - df["year_built"]
    df["needs_attention"]       = (df["property_age"] > 8).astype(int)

    df["rent_tier"] = pd.cut(
        df["market_rent"],
        bins=[0,1500,2000,2500,9999],
        labels=["Economy","Mid-Range","Premium","Luxury"]
    )

    # merge actual rent from active tenants
    active = tenants[tenants["status"]=="Active"][["unit_id","monthly_rent"]]
    df = df.merge(active, on="unit_id", how="left")
    df["actual_rent"]      = df["monthly_rent"].fillna(0)
    df["loss_to_lease"]    = df["market_rent"] - df["actual_rent"]
    df["occupancy_status"] = df["actual_rent"].apply(
        lambda x: "Occupied" if x > 0 else "Vacant"
    )
    df.drop(columns=["monthly_rent"], inplace=True)

    df.to_csv(f"{OUT}/feat_units.csv", index=False)
    print(f"    {len(df):,} rows, {len(df.columns)} columns")
    return df


# ── maintenance features ───────────────────────────────────────────────────────

def maintenance_features(maint, props):
    print("  maintenance...")
    df = maint.copy()
    df["open_date"]  = pd.to_datetime(df["open_date"])
    df["close_date"] = pd.to_datetime(df["close_date"])
    df = df.merge(props[["property_id","name","city"]], on="property_id", how="left")

    df["resolution_days"] = (df["close_date"] - df["open_date"]).dt.days
    df["is_open"]         = (df["status"] == "Open").astype(int)
    df["days_open"]       = df["open_date"].apply(
        lambda d: (TODAY - d).days if pd.notna(d) else 0
    )

    # SLA thresholds by priority
    # emergency should be done in 1 day, low priority gets 14 days
    sla = {"Emergency":1,"High":3,"Medium":7,"Low":14}
    df["sla_days"]   = df["priority"].map(sla)
    df["sla_breach"] = (
        (df["is_open"] == 1) & (df["days_open"] > df["sla_days"])
    ).astype(int)

    df["cost_tier"] = pd.cut(
        df["cost"],
        bins=[-1,0,250,1000,9999],
        labels=["No Cost","Low","Medium","High"]
    )

    df.to_csv(f"{OUT}/feat_maintenance.csv", index=False)
    print(f"    {len(df):,} rows, {len(df.columns)} columns")
    return df


# ── property kpi rollup ────────────────────────────────────────────────────────

def property_kpis(props, units, tenants, rr, maint):
    print("  property KPIs...")
    df = props.copy()

    # occupancy
    occ = units.merge(
        tenants[tenants["status"]=="Active"][["unit_id","monthly_rent"]],
        on="unit_id", how="left"
    )
    occ_agg = occ.groupby("property_id").agg(
        total_units     = ("unit_id",      "count"),
        occupied_units  = ("monthly_rent", lambda x: x.notna().sum()),
        avg_market_rent = ("market_rent",  "mean"),
        avg_actual_rent = ("monthly_rent", "mean"),
        total_sqft      = ("sqft",         "sum"),
    ).reset_index()

    occ_agg["occupancy_rate"]    = (occ_agg["occupied_units"] / occ_agg["total_units"] * 100).round(1)
    occ_agg["vacancy_rate"]      = (100 - occ_agg["occupancy_rate"]).round(1)
    occ_agg["loss_to_lease_pct"] = (
        (occ_agg["avg_market_rent"] - occ_agg["avg_actual_rent"]) /
         occ_agg["avg_market_rent"] * 100
    ).round(2)

    # revenue — last full month
    last_mo = rr["period_month"].max()
    rev = rr[rr["period_month"]==last_mo].groupby("property_id").agg(
        gross_potential_rent = ("amount_due",  "sum"),
        collected_rent       = ("amount_paid", "sum"),
    ).reset_index()
    rev["collection_rate_pct"] = (rev["collected_rent"] / rev["gross_potential_rent"] * 100).round(1)
    rev["uncollected"]         = (rev["gross_potential_rent"] - rev["collected_rent"]).round(0)

    # maintenance summary
    m_agg = maint.groupby("property_id").agg(
        total_tickets    = ("ticket_id","count"),
        open_tickets     = ("status",   lambda x: (x=="Open").sum()),
        total_maint_cost = ("cost",     "sum"),
        avg_resolution   = ("close_date",lambda x: x.notna().sum()),
    ).reset_index()

    df = df.merge(occ_agg, on="property_id", how="left")
    df = df.merge(rev,     on="property_id", how="left")
    df = df.merge(m_agg,   on="property_id", how="left")

    df["revenue_per_unit"] = (df["collected_rent"] / df["occupied_units"]).round(0)
    df["annual_revenue"]   = (df["collected_rent"] * 12).round(0)

    # composite performance score
    df["performance_score"] = (
        (df["occupancy_rate"]      * 0.40) +
        (df["collection_rate_pct"] * 0.35) +
        ((100 - df["vacancy_rate"]) * 0.25)
    ).round(1)

    df["performance_grade"] = pd.cut(
        df["performance_score"],
        bins=[0,60,70,80,90,100],
        labels=["D","C","B","A","A+"]
    )

    df.to_csv(f"{OUT}/feat_property_kpis.csv", index=False)
    print(f"    {len(df):,} rows, {len(df.columns)} columns")
    return df


# ── rent roll features ─────────────────────────────────────────────────────────

def rent_roll_features(rr, tenants, units, props):
    print("  rent roll...")
    df = rr.copy()
    df["payment_date"] = pd.to_datetime(df["payment_date"])
    df["period_dt"]    = pd.to_datetime(df["period_month"] + "-01")

    df["days_to_pay"]   = (df["payment_date"] - df["period_dt"]).dt.days
    df["is_paid"]       = (df["status"] == "Paid").astype(int)
    df["is_delinquent"] = (df["status"] == "Delinquent").astype(int)
    df["is_partial"]    = (df["status"] == "Partial").astype(int)
    df["balance_owed"]  = (df["amount_due"] - df["amount_paid"]).round(2)
    df["late_flag"]     = (df["days_to_pay"] > 5).astype(int)

    df["quarter"] = (
        "Q" + df["period_dt"].dt.quarter.astype(str) +
        " " + df["period_dt"].dt.year.astype(str)
    )

    df = df.merge(props[["property_id","name","city"]], on="property_id", how="left")
    df = df.merge(units[["unit_id","unit_type"]], on="unit_id", how="left")

    df.to_csv(f"{OUT}/feat_rent_roll.csv", index=False)
    print(f"    {len(df):,} rows, {len(df.columns)} columns")
    return df


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    props, units, tenants, rr, maint = load(conn)
    conn.close()

    print("phase 2 — feature engineering")
    print("-" * 30)

    tenant_features(tenants, units, rr)
    unit_features(units, props, tenants)
    maintenance_features(maint, props)
    property_kpis(props, units, tenants, rr, maint)
    rent_roll_features(rr, tenants, units, props)

    print(f"\nall feat_*.csv files → {OUT}/")
    print("done.")


if __name__ == "__main__":
    main()
