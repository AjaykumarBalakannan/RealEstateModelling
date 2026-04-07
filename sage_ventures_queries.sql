-- ============================================================
-- Sage Ventures | Multifamily Analytics — SQL Query Library
-- Tool: SQLite (connect via DB Browser or Power BI)
-- ============================================================


-- ┌─────────────────────────────────────────────────────────┐
-- │  SECTION 1: PORTFOLIO KPI SUMMARY (YSR)                │
-- └─────────────────────────────────────────────────────────┘

-- 1A. Portfolio-wide snapshot
SELECT
    COUNT(DISTINCT p.property_id)                              AS total_properties,
    COUNT(DISTINCT u.unit_id)                                  AS total_units,
    COUNT(DISTINCT t.tenant_id)                                AS occupied_units,
    ROUND(COUNT(DISTINCT t.tenant_id)*100.0/
          COUNT(DISTINCT u.unit_id), 1)                        AS portfolio_occupancy_pct,
    ROUND(AVG(u.market_rent), 0)                               AS avg_market_rent,
    ROUND(AVG(t.monthly_rent), 0)                              AS avg_actual_rent,
    ROUND((AVG(u.market_rent)-AVG(t.monthly_rent))
          /AVG(u.market_rent)*100, 1)                          AS loss_to_lease_pct,
    ROUND(SUM(t.monthly_rent), 0)                              AS total_monthly_revenue,
    ROUND(SUM(t.monthly_rent)*12, 0)                           AS projected_annual_revenue
FROM properties p
JOIN units u       ON p.property_id = u.property_id
LEFT JOIN tenants t ON u.unit_id    = t.unit_id
                   AND t.status     = 'Active';


-- 1B. Property-level KPI breakdown
SELECT
    p.name                                                     AS property,
    p.city,
    p.property_type,
    p.total_units,
    COUNT(t.tenant_id)                                         AS occupied,
    p.total_units - COUNT(t.tenant_id)                         AS vacant,
    ROUND(COUNT(t.tenant_id)*100.0/p.total_units, 1)           AS occupancy_pct,
    ROUND(AVG(u.market_rent), 0)                               AS avg_market_rent,
    ROUND(AVG(t.monthly_rent), 0)                              AS avg_actual_rent,
    ROUND(AVG(u.market_rent)-AVG(t.monthly_rent), 0)           AS avg_loss_to_lease,
    ROUND(SUM(t.monthly_rent), 0)                              AS monthly_revenue,
    ROUND(SUM(t.monthly_rent)*12, 0)                           AS annual_revenue
FROM properties p
JOIN units u       ON p.property_id = u.property_id
LEFT JOIN tenants t ON u.unit_id    = t.unit_id
                   AND t.status     = 'Active'
GROUP BY p.property_id
ORDER BY monthly_revenue DESC;


-- ┌─────────────────────────────────────────────────────────┐
-- │  SECTION 2: RENT ROLL REPORTING                        │
-- └─────────────────────────────────────────────────────────┘

-- 2A. Current month rent roll (full detail)
SELECT
    p.name                                                     AS property,
    u.unit_number,
    u.unit_type,
    t.full_name                                                AS tenant,
    t.lease_start,
    t.lease_end,
    u.market_rent,
    t.monthly_rent,
    ROUND(u.market_rent - t.monthly_rent, 0)                   AS loss_to_lease,
    r.amount_due,
    r.amount_paid,
    ROUND(r.amount_due - r.amount_paid, 0)                     AS balance_owed,
    r.status                                                   AS payment_status,
    r.payment_date
FROM rent_roll r
JOIN tenants t     ON r.tenant_id    = t.tenant_id
JOIN units u       ON r.unit_id      = u.unit_id
JOIN properties p  ON r.property_id  = p.property_id
WHERE r.period_month = (SELECT MAX(period_month) FROM rent_roll)
ORDER BY p.name, u.unit_number;


-- 2B. Monthly revenue collection summary
SELECT
    r.period_month,
    COUNT(DISTINCT r.payment_id)                               AS total_charges,
    ROUND(SUM(r.amount_due), 0)                                AS gross_potential_rent,
    ROUND(SUM(r.amount_paid), 0)                               AS collected_rent,
    ROUND(SUM(r.amount_due) - SUM(r.amount_paid), 0)           AS uncollected,
    ROUND(SUM(r.amount_paid)*100.0/SUM(r.amount_due), 1)       AS collection_rate_pct,
    SUM(CASE WHEN r.status='Delinquent' THEN 1 ELSE 0 END)     AS delinquent_count,
    SUM(CASE WHEN r.status='Partial'    THEN 1 ELSE 0 END)     AS partial_count
FROM rent_roll r
GROUP BY r.period_month
ORDER BY r.period_month;


-- ┌─────────────────────────────────────────────────────────┐
-- │  SECTION 3: LEASE SCRIPTS                              │
-- └─────────────────────────────────────────────────────────┘

-- 3A. Lease expiration pipeline (30/60/90 day buckets)
SELECT
    p.name                                                     AS property,
    SUM(CASE WHEN julianday(t.lease_end)-julianday('now') < 0
             THEN 1 ELSE 0 END)                                AS already_expired,
    SUM(CASE WHEN julianday(t.lease_end)-julianday('now')
             BETWEEN 0 AND 30  THEN 1 ELSE 0 END)             AS expiring_30d,
    SUM(CASE WHEN julianday(t.lease_end)-julianday('now')
             BETWEEN 31 AND 60 THEN 1 ELSE 0 END)             AS expiring_60d,
    SUM(CASE WHEN julianday(t.lease_end)-julianday('now')
             BETWEEN 61 AND 90 THEN 1 ELSE 0 END)             AS expiring_90d,
    ROUND(SUM(CASE WHEN julianday(t.lease_end)-julianday('now') <= 90
                   THEN t.monthly_rent ELSE 0 END), 0)         AS at_risk_revenue
FROM tenants t
JOIN units u      ON t.unit_id      = u.unit_id
JOIN properties p ON u.property_id  = p.property_id
WHERE t.status = 'Active'
GROUP BY p.property_id
ORDER BY (expiring_30d + expiring_60d + expiring_90d) DESC;


-- 3B. Lease detail — upcoming renewals
SELECT
    p.name                                                     AS property,
    u.unit_number,
    u.unit_type,
    t.full_name                                                AS tenant,
    t.lease_start,
    t.lease_end,
    CAST(julianday(t.lease_end)-julianday('now') AS INT)       AS days_to_expiry,
    t.monthly_rent,
    t.status
FROM tenants t
JOIN units u      ON t.unit_id     = u.unit_id
JOIN properties p ON u.property_id = p.property_id
WHERE julianday(t.lease_end) - julianday('now') BETWEEN 0 AND 90
  AND t.status = 'Active'
ORDER BY days_to_expiry;


-- ┌─────────────────────────────────────────────────────────┐
-- │  SECTION 4: AD HOC QUERIES                             │
-- └─────────────────────────────────────────────────────────┘

-- 4A. Delinquency report — current month
SELECT
    p.name                                                     AS property,
    t.full_name                                                AS tenant,
    u.unit_number,
    r.period_month,
    r.amount_due,
    r.amount_paid,
    ROUND(r.amount_due - r.amount_paid, 0)                     AS balance_owed,
    r.status
FROM rent_roll r
JOIN tenants t    ON r.tenant_id   = t.tenant_id
JOIN units u      ON r.unit_id     = u.unit_id
JOIN properties p ON r.property_id = p.property_id
WHERE r.status IN ('Delinquent','Partial')
  AND r.period_month = (SELECT MAX(period_month) FROM rent_roll)
ORDER BY balance_owed DESC;


-- 4B. Loss-to-lease by property and unit type
SELECT
    p.name                                                     AS property,
    u.unit_type,
    COUNT(u.unit_id)                                           AS unit_count,
    ROUND(AVG(u.market_rent), 0)                               AS avg_market_rent,
    ROUND(AVG(t.monthly_rent), 0)                              AS avg_actual_rent,
    ROUND(AVG(u.market_rent - t.monthly_rent), 0)              AS avg_loss_to_lease,
    ROUND(SUM(u.market_rent - t.monthly_rent)*12, 0)           AS annual_gap
FROM units u
JOIN properties p ON u.property_id  = p.property_id
JOIN tenants t    ON u.unit_id      = t.unit_id
                 AND t.status       = 'Active'
GROUP BY p.property_id, u.unit_type
ORDER BY annual_gap DESC;


-- 4C. Maintenance cost by property (YTD)
SELECT
    p.name                                                     AS property,
    m.category,
    COUNT(m.ticket_id)                                         AS total_tickets,
    SUM(CASE WHEN m.status='Open' THEN 1 ELSE 0 END)           AS open_tickets,
    ROUND(AVG(CASE WHEN m.close_date IS NOT NULL
              THEN julianday(m.close_date)-julianday(m.open_date)
              END), 1)                                         AS avg_resolution_days,
    ROUND(SUM(m.cost), 0)                                      AS total_cost
FROM maintenance m
JOIN properties p ON m.property_id = p.property_id
GROUP BY p.property_id, m.category
ORDER BY total_cost DESC;


-- 4D. YSR — Quarterly revenue rollup
SELECT
    CASE
      WHEN CAST(substr(r.period_month,6,2) AS INT) BETWEEN 1 AND 3  THEN 'Q1'
      WHEN CAST(substr(r.period_month,6,2) AS INT) BETWEEN 4 AND 6  THEN 'Q2'
      WHEN CAST(substr(r.period_month,6,2) AS INT) BETWEEN 7 AND 9  THEN 'Q3'
      ELSE 'Q4'
    END || ' ' || substr(r.period_month,1,4)                  AS quarter,
    ROUND(SUM(r.amount_due), 0)                                AS gross_potential_rent,
    ROUND(SUM(r.amount_paid), 0)                               AS collected_rent,
    ROUND(SUM(r.amount_due)-SUM(r.amount_paid), 0)             AS uncollected,
    ROUND(SUM(r.amount_paid)*100.0/SUM(r.amount_due), 1)       AS collection_rate_pct
FROM rent_roll r
GROUP BY quarter
ORDER BY quarter;


-- 4E. Occupancy trend — monthly (last 6 months)
SELECT
    o.period_month,
    p.name                                                     AS property,
    o.total_units,
    o.occupied_units,
    o.occupancy_rate,
    o.avg_market_rent,
    o.avg_actual_rent
FROM occupancy_monthly o
JOIN properties p ON o.property_id = p.property_id
WHERE o.period_month >= date('now', '-6 months')
ORDER BY o.period_month DESC, o.occupancy_rate DESC;
