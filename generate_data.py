"""
generate_data.py

builds the sqlite database and exports raw csvs.
phase 1 of the pipeline — run this first.

property names from sage ventures' website, rent ranges from
HUD fair market rents for baltimore-columbia-towson MSA 2024.

run:  python generate_data.py
deps: pip install faker
"""

import sqlite3
import random
import csv
import os
from datetime import date, timedelta
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DB   = "data/sage_ventures.db"
DATA = "data"
os.makedirs(DATA, exist_ok=True)


# real sage ventures properties + similar maryland comps
PROPERTIES = [
    {"id":"P001","name":"Duvall Westside",         "city":"Laurel",         "zip":"20707","type":"Luxury Apartment",   "units":287,"built":2023},
    {"id":"P002","name":"Mills Crossing",           "city":"Owings Mills",   "zip":"21117","type":"Townhome/Apartment", "units":312,"built":2018},
    {"id":"P003","name":"Townes at Heritage Hills", "city":"Glen Burnie",    "zip":"21061","type":"Townhome",           "units":198,"built":2016},
    {"id":"P004","name":"Fieldside Grande Ph1",     "city":"Pikesville",     "zip":"21208","type":"Luxury Apartment",   "units":287,"built":2023},
    {"id":"P005","name":"Avenue Grand",             "city":"Baltimore",      "zip":"21201","type":"Mid-Rise Apartment", "units":224,"built":2020},
    {"id":"P006","name":"Cedar Ridge Commons",      "city":"Ellicott City",  "zip":"21043","type":"Garden Apartment",   "units":310,"built":2015},
    {"id":"P007","name":"Overlook at Bulle Rock",   "city":"Havre de Grace", "zip":"21078","type":"Condominium",        "units":180,"built":2019},
    {"id":"P008","name":"Riverfront Flats",         "city":"Frederick",      "zip":"21701","type":"Mid-Rise Apartment", "units":260,"built":2021},
]

# HUD FMR ranges — baltimore MSA 2024
UNIT_TYPES = {
    "Studio":  {"sqft":(450,600),   "rent":(1350,1650)},
    "1BR/1BA": {"sqft":(650,850),   "rent":(1550,1950)},
    "2BR/1BA": {"sqft":(850,1050),  "rent":(1800,2250)},
    "2BR/2BA": {"sqft":(950,1150),  "rent":(2000,2500)},
    "3BR/2BA": {"sqft":(1150,1450), "rent":(2400,3100)},
}

# unit mix by property type
UNIT_MIX = {
    "Luxury Apartment":   {"Studio":0.10,"1BR/1BA":0.30,"2BR/1BA":0.10,"2BR/2BA":0.40,"3BR/2BA":0.10},
    "Townhome/Apartment": {"Studio":0.05,"1BR/1BA":0.20,"2BR/1BA":0.15,"2BR/2BA":0.35,"3BR/2BA":0.25},
    "Townhome":           {"Studio":0.00,"1BR/1BA":0.10,"2BR/1BA":0.10,"2BR/2BA":0.30,"3BR/2BA":0.50},
    "Mid-Rise Apartment": {"Studio":0.15,"1BR/1BA":0.35,"2BR/1BA":0.10,"2BR/2BA":0.30,"3BR/2BA":0.10},
    "Garden Apartment":   {"Studio":0.10,"1BR/1BA":0.30,"2BR/1BA":0.20,"2BR/2BA":0.30,"3BR/2BA":0.10},
    "Condominium":        {"Studio":0.05,"1BR/1BA":0.20,"2BR/1BA":0.10,"2BR/2BA":0.40,"3BR/2BA":0.25},
}

MAINT_CATS  = ["Plumbing","HVAC","Appliance","Electrical","Flooring","General","Pest Control"]
STATUS_POOL = ["Active"]*7 + ["Notice"] + ["Vacant"]*2  # weighted toward occupied


def rdate(start, end):
    return start + timedelta(days=random.randint(0, (end-start).days))


def create_schema(c):
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


def insert_properties(c):
    for p in PROPERTIES:
        c.execute(
            "INSERT INTO properties VALUES (?,?,?,?,?,?,?)",
            (p["id"],p["name"],p["city"],p["zip"],p["type"],p["units"],p["built"])
        )


def insert_units(c):
    units = []
    seq   = 1

    for p in PROPERTIES:
        mix    = UNIT_MIX[p["type"]]
        floors = max(3, min(6, p["built"] - 2010))
        unum   = 1

        for utype, pct in mix.items():
            count = max(1, int(p["units"] * pct))
            specs = UNIT_TYPES[utype]

            for _ in range(count):
                uid  = f"U{seq:05d}"
                sqft = random.randint(*specs["sqft"])
                rent = round(random.uniform(*specs["rent"]), 0)
                stat = random.choice(STATUS_POOL)

                c.execute(
                    "INSERT INTO units VALUES (?,?,?,?,?,?,?,?)",
                    (uid, p["id"], f"{unum:03d}", utype, sqft, rent,
                     random.randint(1, floors), stat)
                )
                units.append({"uid":uid,"pid":p["id"],"utype":utype,"rent":rent,"status":stat})
                unum += 1
                seq  += 1

    return units


def insert_tenants(c, units):
    tenants = []
    seq     = 1
    occupied = [u for u in units if u["status"] in ("Active","Notice")]

    for u in occupied:
        tid  = f"T{seq:05d}"
        ls   = rdate(date(2021,1,1), date(2024,6,1))
        dur  = random.choice([365,365,365,548,730])  # 1yr is most common
        le   = ls + timedelta(days=dur)

        # actual rent is slightly below market — normal in competitive markets
        actual = round(u["rent"] * random.uniform(0.88, 1.00), 0)
        stat   = "Active" if u["status"]=="Active" else "Notice to Vacate"

        c.execute(
            "INSERT INTO tenants VALUES (?,?,?,?,?,?,?,?,?,?)",
            (tid, u["uid"], fake.name(), fake.email(), fake.phone_number(),
             ls.isoformat(), le.isoformat(), actual, actual, stat)
        )
        tenants.append({"tid":tid,"uid":u["uid"],"pid":u["pid"],"rent":actual,"ls":ls,"le":le})
        seq += 1

    return tenants


def insert_rent_roll(c, tenants):
    # jan 2024 through mar 2025 — 15 months of payment history
    months = [date(2024,1,1) + timedelta(days=30*i) for i in range(15)]
    seq    = 1

    for t in tenants:
        for mo in months:
            if mo < t["ls"] or mo > t["le"] + timedelta(days=30):
                continue

            due = t["rent"]
            r   = random.random()

            # 93% on time, 4% partial, 3% delinquent
            if r < 0.93:
                paid, pdate, stat = due, (mo + timedelta(days=random.randint(1,5))).isoformat(), "Paid"
            elif r < 0.97:
                paid  = round(due * random.uniform(0.5, 0.99), 0)
                pdate = (mo + timedelta(days=random.randint(6,20))).isoformat()
                stat  = "Partial"
            else:
                paid, pdate, stat = 0, None, "Delinquent"

            c.execute(
                "INSERT INTO rent_roll VALUES (?,?,?,?,?,?,?,?,?)",
                (f"PAY{seq:06d}", t["tid"], t["uid"], t["pid"],
                 mo.strftime("%Y-%m"), due, paid, pdate, stat)
            )
            seq += 1


def insert_maintenance(c, units):
    today = date.today()
    seq   = 1

    for p in PROPERTIES:
        p_units = [u for u in units if u["pid"] == p["id"]]
        n       = int(len(p_units) * random.uniform(0.8, 1.5))

        for _ in range(n):
            mid      = f"M{seq:05d}"
            u        = random.choice(p_units)
            priority = random.choice(["Low","Medium","Medium","High","Emergency"])
            odate    = rdate(date(2023,6,1), today)
            closed   = random.random() < 0.78
            cdate    = (odate + timedelta(days=random.randint(1,45))).isoformat() if closed else None
            cost     = round(random.uniform(50,2500), 2) if closed else 0.0

            c.execute(
                "INSERT INTO maintenance VALUES (?,?,?,?,?,?,?,?,?)",
                (mid, u["uid"], p["id"], random.choice(MAINT_CATS), priority,
                 odate.isoformat(), cdate, cost, "Closed" if closed else "Open")
            )
            seq += 1


def insert_occupancy(c, units):
    months = [date(2024,1,1) + timedelta(days=30*i) for i in range(15)]
    seq    = 1

    for p in PROPERTIES:
        p_units  = [u for u in units if u["pid"] == p["id"]]
        base     = random.uniform(0.80, 0.95)
        avg_mkt  = round(sum(u["rent"] for u in p_units) / len(p_units), 0)

        for mo in months:
            # small seasonal dip in winter
            seasonal = -0.03 if mo.month in [1,2,12] else 0.01
            rate     = min(0.99, max(0.72, base + seasonal + random.uniform(-0.03,0.03)))
            occ_u    = int(len(p_units) * rate)

            c.execute(
                "INSERT INTO occupancy_monthly VALUES (?,?,?,?,?,?,?,?,?)",
                (f"OCC{seq:05d}", p["id"], mo.strftime("%Y-%m"),
                 len(p_units), occ_u, len(p_units)-occ_u,
                 round(rate*100,1), avg_mkt,
                 round(avg_mkt * random.uniform(0.91,0.98), 0))
            )
            seq += 1


def export_csvs(conn):
    c = conn.cursor()
    for tbl in ["properties","units","tenants","rent_roll","maintenance","occupancy_monthly"]:
        rows = c.execute(f"SELECT * FROM {tbl}").fetchall()
        cols = [d[0] for d in c.description]
        with open(f"{DATA}/{tbl}.csv","w",newline="") as f:
            csv.writer(f).writerow(cols)
            csv.writer(f).writerows(rows)


def main():
    conn = sqlite3.connect(DB)
    c    = conn.cursor()

    print("phase 1 — data generation")
    print("-" * 30)

    create_schema(c)
    print("schema created")

    insert_properties(c)
    print(f"properties : {len(PROPERTIES)}")

    units = insert_units(c)
    print(f"units      : {len(units):,}")

    tenants = insert_tenants(c, units)
    print(f"tenants    : {len(tenants):,}")

    insert_rent_roll(c, tenants)
    n_pay = c.execute("SELECT COUNT(*) FROM rent_roll").fetchone()[0]
    print(f"payments   : {n_pay:,}")

    insert_maintenance(c, units)
    n_maint = c.execute("SELECT COUNT(*) FROM maintenance").fetchone()[0]
    print(f"tickets    : {n_maint:,}")

    insert_occupancy(c, units)

    conn.commit()
    export_csvs(conn)
    conn.close()

    print(f"\ndb  → {DB}")
    print(f"csv → {DATA}/")
    print("done.")


if __name__ == "__main__":
    main()
