# Sage Ventures — Power BI Direct Database Connection
# How to connect Power BI Desktop directly to sage_ventures.db
# instead of loading CSVs manually

=====================================================================
 OPTION A — Connect Power BI Desktop to SQLite (Recommended)
=====================================================================

Step 1 — Install SQLite ODBC Driver (Windows only, one time)
------------------------------------------------------------
Download: http://www.ch-werner.de/sqliteodbc/
→ sqliteodbc.exe (32-bit) AND sqliteodbc_w64.exe (64-bit)
→ install both

Step 2 — Set up ODBC Data Source
---------------------------------
Windows Search → "ODBC Data Sources (64-bit)" → open it
→ System DSN tab → Add
→ Select "SQLite3 ODBC Driver"
→ Data Source Name: SageVentures
→ Database Name: C:\path\to\sage_ventures\data\sage_ventures.db
→ OK

Step 3 — Connect Power BI to ODBC
-----------------------------------
Power BI Desktop → Home → Get Data → More
→ search "ODBC" → select ODBC → Connect
→ DSN: SageVentures → OK
→ Navigator shows all 6 tables:
   ☑ properties
   ☑ units
   ☑ tenants
   ☑ rent_roll
   ☑ maintenance
   ☑ occupancy_monthly
→ Select All → Load

Step 4 — Use Native SQL Queries in Power BI
--------------------------------------------
Instead of loading raw tables, paste SQL directly:
→ Get Data → ODBC → Advanced Options
→ paste any query from sage_ventures_queries.sql
→ Power BI runs it live against the database

Example — paste this for the Executive KPI query:
--------------------------------------------------
SELECT
    p.name,
    p.city,
    p.total_units,
    COUNT(t.tenant_id) AS occupied_units,
    ROUND(COUNT(t.tenant_id)*100.0/p.total_units,1) AS occupancy_rate,
    ROUND(AVG(u.market_rent),0) AS avg_market_rent,
    ROUND(AVG(t.monthly_rent),0) AS avg_actual_rent,
    ROUND(SUM(t.monthly_rent),0) AS monthly_revenue
FROM properties p
JOIN units u ON p.property_id = u.property_id
LEFT JOIN tenants t ON u.unit_id = t.unit_id AND t.status='Active'
GROUP BY p.property_id
ORDER BY monthly_revenue DESC

Step 5 — Set Auto Refresh
--------------------------
Power BI Desktop → Home → Transform Data → Data Source Settings
→ set refresh schedule
→ every time you run python run_pipeline.py
   the database updates → Power BI refreshes automatically


=====================================================================
 OPTION B — What We Currently Have (CSV approach)
=====================================================================

Current flow:
python run_pipeline.py
    → generates sage_ventures.db  (SQLite)
    → generates feat_*.csv        (from SQL queries on the DB)
    → Power BI loads feat_*.csv   (manual load)

This works fine but requires manual CSV reload in Power BI
when data changes.

The ODBC connection (Option A) makes it fully automatic —
run_pipeline.py → database updates → Power BI auto-refreshes.


=====================================================================
 TALKING POINT FOR THE RECRUITER
=====================================================================

"The pipeline is fully automated with a single command —
python run_pipeline.py triggers the entire workflow:
data generation, feature engineering, ad hoc analysis,
Excel report generation, and chart automation.

Power BI connects directly to the SQLite database via ODBC,
so when the pipeline runs, the dashboard refreshes automatically —
no manual CSV imports needed.

This mirrors how I'd set it up in a production environment
connecting to Yardi or RealPage's database — same concept,
just a different source system."
