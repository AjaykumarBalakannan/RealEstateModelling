"""
=============================================================
 Sage Ventures – Multifamily Analytics
 PHASE 1: Data Generation Pipeline
 Run:    python generate_data.py
 Needs:  pip install faker
=============================================================
"""

import sqlite3, random, csv, os
from datetime import date, timedelta
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DB_PATH  = "data/sage_ventures.db"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ── REAL SAGE VENTURES PROPERTIES + MD COMPS ─────────────────────────────────
PROPERTIES = [
    {"id":"P001","name":"Duvall Westside",         "city":"Laurel",         "zip":"20707","type":"Luxury Apartment",   "units":287,"year_built":2023},
    {"id":"P002","name":"Mills Crossing",           "city":"Owings Mills",   "zip":"21117","type":"Townhome/Apartment", "units":312,"year_built":2018},
    {"id":"P003","name":"Townes at Heritage Hills", "city":"Glen Burnie",    "zip":"21061","type":"Townhome",           "units":198,"year_built":2016},
    {"id":"P004","name":"Fieldside Grande Ph1",     "city":"Pikesville",     "zip":"21208","type":"Luxury Apartment",   "units":287,"year_built":2023},
    {"id":"P005","name":"Avenue Grand",             "city":"Baltimore",      "zip":"21201","type":"Mid-Rise Apartment", "units":224,"year_built":2020},
    {"id":"P006","name":"Cedar Ridge Commons",      "city":"Ellicott City",  "zip":"21043","type":"Garden Apartment",   "units":310,"year_built":2015},
    {"id":"P007","name":"Overlook at Bulle Rock",   "city":"Havre de Grace", "zip":"21078","type":"Condominium",        "units":180,"year_built":2019},
    {"id":"P008","name":"Riverfront Flats",         "city":"Frederick",      "zip":"21701","type":"Mid-Rise Apartment", "units":260,"year_built":2021},
]

# HUD Fair Market Rents – Baltimore-Columbia-Towson MSA (2024 benchmarks)
UNIT_TYPES = {
    "Studio":  {"sqft":(450,600),   "market_rent":(1350,1650)},
    "1BR/1BA": {"sqft":(650,850),   "market_rent":(1550,1950)},
    "2BR/1BA": {"sqft":(850,1050),  "market_rent":(1800,2250)},
    "2BR/2BA": {"sqft":(950,1150),  "market_rent":(2000,2500)},
    "3BR/2BA": {"sqft":(1150,1450), "market_rent":(2400,3100)},
}

UNIT_MIX = {
    "Luxury Apartment":   {"Studio":0.10,"1BR/1BA":0.30,"2BR/1BA":0.10,"2BR/2BA":0.40,"3BR/2BA":0.10},
    "Townhome/Apartment": {"Studio":0.05,"1BR/1BA":0.20,"2BR/1BA":0.15,"2BR/2BA":0.35,"3BR/2BA":0.25},
    "Townhome":           {"Studio":0.00,"1BR/1BA":0.10,"2BR/1BA":0.10,"2BR/2BA":0.30,"3BR/2BA":0.50},
    "Mid-Rise Apartment": {"Studio":0.15,"1BR/1BA":0.35,"2BR/1BA":0.10,"2BR/2BA":0.30,"3BR/2BA":0.10},
    "Garden Apartment":   {"Studio":0.10,"1BR/1BA":0.30,"2BR/1BA":0.20,"2BR/2BA":0.30,"3BR/2BA":0.10},
    "Condominium":        {"Studio":0.05,"1BR/1BA":0.20,"2BR/1BA":0.10,"2BR/2BA":0.40,"3BR/2BA":0.25},
}

MAINT_CATS = ["Plumbing","HVAC","Appliance","Electrical","Flooring","General","Pest Control"]

def rdate(start, end):
    return start + timedelta(days=random.randint(0,(end-start).days))

def main():
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    # ── SCHEMA ────────────────────────────────────────────────────────────────
    c.executescript("""
    DROP TABLE IF EXISTS properties;
    DROP TABLE IF EXISTS units;
    DROP TABLE IF EXISTS tenants;
    DROP TABLE IF EXISTS rent_roll;
    DROP TABLE IF EXISTS maintenance;
    DROP TABLE IF EXISTS occupancy_monthly;

    CREATE TABLE properties (
        property_id   TEXT PRIMARY KEY,
        name          TEXT,
        city          TEXT,
        zip           TEXT,
        property_type TEXT,
        total_units   INTEGER,
        year_built    INTEGER
    );
    CREATE TABLE units (
        unit_id       TEXT PRIMARY KEY,
        property_id   TEXT,
        unit_number   TEXT,
        unit_type     TEXT,
        sqft          INTEGER,
        market_rent   REAL,
        floor         INTEGER,
        status        TEXT
    );
    CREATE TABLE tenants (
        tenant_id    TEXT PRIMARY KEY,
        unit_id      TEXT,
        full_name    TEXT,
        email        TEXT,
        phone        TEXT,
        lease_start  TEXT,
        lease_end    TEXT,
        monthly_rent REAL,
        deposit      REAL,
        status       TEXT
    );
    CREATE TABLE rent_roll (
        payment_id   TEXT PRIMARY KEY,
        tenant_id    TEXT,
        unit_id      TEXT,
        property_id  TEXT,
        period_month TEXT,
        amount_due   REAL,
        amount_paid  REAL,
        payment_date TEXT,
        status       TEXT
    );
    CREATE TABLE maintenance (
        ticket_id   TEXT PRIMARY KEY,
        unit_id     TEXT,
        property_id TEXT,
        category    TEXT,
        priority    TEXT,
        open_date   TEXT,
        close_date  TEXT,
        cost        REAL,
        status      TEXT
    );
    CREATE TABLE occupancy_monthly (
        occ_id          TEXT PRIMARY KEY,
        property_id     TEXT,
        period_month    TEXT,
        total_units     INTEGER,
        occupied_units  INTEGER,
        vacant_units    INTEGER,
        occupancy_rate  REAL,
        avg_market_rent REAL,
        avg_actual_rent REAL
    );
    """)

    # ── PROPERTIES ────────────────────────────────────────────────────────────
    for p in PROPERTIES:
        c.execute("INSERT INTO properties VALUES (?,?,?,?,?,?,?)",
                  (p["id"],p["name"],p["city"],p["zip"],p["type"],p["units"],p["year_built"]))

    # ── UNITS ─────────────────────────────────────────────────────────────────
    units_data = []
    unit_seq   = 1
    today      = date.today()
    STATUS_POOL = ["Active"]*7 + ["Notice"] + ["Vacant"]*2

    for p in PROPERTIES:
        mix    = UNIT_MIX[p["type"]]
        floors = max(3, min(6, p["year_built"] - 2010))
        unit_num = 1
        for utype, fraction in mix.items():
            count = max(1, int(p["units"] * fraction))
            specs = UNIT_TYPES[utype]
            for _ in range(count):
                uid   = f"U{unit_seq:05d}"
                sqft  = random.randint(*specs["sqft"])
                mrent = round(random.uniform(*specs["market_rent"]), 0)
                floor = random.randint(1, floors)
                stat  = random.choice(STATUS_POOL)
                c.execute("INSERT INTO units VALUES (?,?,?,?,?,?,?,?)",
                          (uid, p["id"], f"{unit_num:03d}", utype, sqft, mrent, floor, stat))
                units_data.append({"uid":uid,"pid":p["id"],"utype":utype,"mrent":mrent,"status":stat})
                unit_num += 1
                unit_seq += 1

    # ── TENANTS ───────────────────────────────────────────────────────────────
    tenants_data = []
    tid_seq = 1
    active_units = [u for u in units_data if u["status"] in ("Active","Notice")]

    for u in active_units:
        tid    = f"T{tid_seq:05d}"
        name   = fake.name()
        email  = fake.email()
        phone  = fake.phone_number()
        ls     = rdate(date(2021,1,1), date(2024,6,1))
        dur    = random.choice([365,365,365,548,730])
        le     = ls + timedelta(days=dur)
        actual = round(u["mrent"] * random.uniform(0.88, 1.00), 0)
        stat   = "Active" if u["status"]=="Active" else "Notice to Vacate"
        c.execute("INSERT INTO tenants VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (tid,u["uid"],name,email,phone,
                   ls.isoformat(),le.isoformat(),actual,actual,stat))
        tenants_data.append({"tid":tid,"uid":u["uid"],"pid":u["pid"],
                              "rent":actual,"ls":ls,"le":le})
        tid_seq += 1

    # ── RENT ROLL (15 months Jan 2024 – Mar 2025) ─────────────────────────────
    pay_seq = 1
    months  = [date(2024,1,1) + timedelta(days=30*i) for i in range(15)]

    for t in tenants_data:
        for mo in months:
            if mo < t["ls"] or mo > t["le"] + timedelta(days=30):
                continue
            pid_str = f"PAY{pay_seq:06d}"
            due     = t["rent"]
            roll    = random.random()
            if roll < 0.93:
                paid, pdate, stat = due, (mo+timedelta(days=random.randint(1,5))).isoformat(), "Paid"
            elif roll < 0.97:
                paid = round(due * random.uniform(0.5,0.99),0)
                pdate, stat = (mo+timedelta(days=random.randint(6,20))).isoformat(), "Partial"
            else:
                paid, pdate, stat = 0, None, "Delinquent"
            c.execute("INSERT INTO rent_roll VALUES (?,?,?,?,?,?,?,?,?)",
                      (pid_str,t["tid"],t["uid"],t["pid"],
                       mo.strftime("%Y-%m"),due,paid,pdate,stat))
            pay_seq += 1

    # ── MAINTENANCE ───────────────────────────────────────────────────────────
    maint_seq = 1
    for p in PROPERTIES:
        p_units   = [u for u in units_data if u["pid"]==p["id"]]
        n_tickets = int(len(p_units) * random.uniform(0.8,1.5))
        for _ in range(n_tickets):
            mid   = f"M{maint_seq:05d}"
            u     = random.choice(p_units)
            cat   = random.choice(MAINT_CATS)
            pri   = random.choice(["Low","Medium","Medium","High","Emergency"])
            odate = rdate(date(2023,6,1), today)
            done  = random.random() < 0.78
            cdate = (odate+timedelta(days=random.randint(1,45))).isoformat() if done else None
            cost  = round(random.uniform(50,2500),2) if done else 0.0
            stat  = "Closed" if done else "Open"
            c.execute("INSERT INTO maintenance VALUES (?,?,?,?,?,?,?,?,?)",
                      (mid,u["uid"],p["id"],cat,pri,
                       odate.isoformat(),cdate,cost,stat))
            maint_seq += 1

    # ── OCCUPANCY MONTHLY ─────────────────────────────────────────────────────
    occ_seq = 1
    for p in PROPERTIES:
        p_units  = [u for u in units_data if u["pid"]==p["id"]]
        base_occ = random.uniform(0.80, 0.95)
        avg_mkt  = round(sum(u["mrent"] for u in p_units)/len(p_units), 0)
        for mo in months:
            seasonal = -0.03 if mo.month in [1,2,12] else 0.01
            occ_rate = min(0.99, max(0.72, base_occ + seasonal + random.uniform(-0.03,0.03)))
            occ_u    = int(len(p_units) * occ_rate)
            avg_act  = round(avg_mkt * random.uniform(0.91,0.98), 0)
            c.execute("INSERT INTO occupancy_monthly VALUES (?,?,?,?,?,?,?,?,?)",
                      (f"OCC{occ_seq:05d}",p["id"],mo.strftime("%Y-%m"),
                       len(p_units),occ_u,len(p_units)-occ_u,
                       round(occ_rate*100,1),avg_mkt,avg_act))
            occ_seq += 1

    conn.commit()

    # ── EXPORT CSVs ───────────────────────────────────────────────────────────
    for fname, query in {
        "properties.csv":        "SELECT * FROM properties",
        "units.csv":             "SELECT * FROM units",
        "tenants.csv":           "SELECT * FROM tenants",
        "rent_roll.csv":         "SELECT * FROM rent_roll",
        "maintenance.csv":       "SELECT * FROM maintenance",
        "occupancy_monthly.csv": "SELECT * FROM occupancy_monthly",
    }.items():
        rows = c.execute(query).fetchall()
        cols = [d[0] for d in c.description]
        with open(f"{DATA_DIR}/{fname}", "w", newline="") as f:
            csv.writer(f).writerow(cols)
            csv.writer(f).writerows(rows)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print("=" * 55)
    print("  Sage Ventures — Phase 1 Complete ✓")
    print("=" * 55)
    print(f"  Properties    : {len(PROPERTIES)}")
    print(f"  Units         : {c.execute('SELECT COUNT(*) FROM units').fetchone()[0]:,}")
    print(f"  Tenants       : {c.execute('SELECT COUNT(*) FROM tenants').fetchone()[0]:,}")
    print(f"  Rent Records  : {c.execute('SELECT COUNT(*) FROM rent_roll').fetchone()[0]:,}")
    print(f"  Maint Tickets : {c.execute('SELECT COUNT(*) FROM maintenance').fetchone()[0]:,}")
    print(f"  DB            → {DB_PATH}")
    print(f"  CSVs          → {DATA_DIR}/")
    print("=" * 55)
    conn.close()

if __name__ == "__main__":
    main()
