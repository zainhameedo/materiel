"""Synthetic operating data for a fictional defense hardware manufacturer.

Three products, a shared bill of materials, ~60 suppliers, 33 months of
purchasing, production and field sustainment. The data is fake, but the
mechanics are not: late parts stall builds, bad lots fail inspection, and
fielded units break and wait on spares.

One causal effect is planted on purpose. In July 2025 a supplier development
program enrolls the suppliers with the worst quality record. It cuts their
defect rate by ~35%. Because enrollment is selected on bad quality, a naive
treated-vs-untreated comparison gets the sign wrong; difference-in-differences
recovers it. See models/analysis and src/materiel/causal.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2026-09-30")
PROGRAM_START = pd.Timestamp("2025-07-01")
TRUE_EFFECT = -0.35  # proportional change in defect rate for enrolled suppliers

PRODUCTS = [
    # product_id, name, description, build cycle days, monthly build rate
    ("P-KES", "Kestrel", "Low-cost interceptor", 21, 38),
    ("P-PET", "Petrel", "Autonomous surface vessel", 55, 6),
    ("P-HAL", "Halyard", "Persistent sensor mast", 30, 14),
]

CATEGORIES = {
    # category: (unit cost range USD, lead time range days)
    "Airframe": ((400, 9_000), (20, 60)),
    "Propulsion": ((1_500, 40_000), (45, 120)),
    "Avionics": ((800, 25_000), (30, 90)),
    "Energetics": ((2_000, 30_000), (60, 150)),
    "Power": ((300, 12_000), (25, 75)),
    "RF & Sensors": ((1_000, 60_000), (40, 130)),
    "Hull & Structure": ((2_000, 80_000), (35, 100)),
    "Harness & Fasteners": ((5, 600), (10, 35)),
}

SUPPLIER_STEMS = [
    "Arbor", "Bellwether", "Cobalt", "Dunmore", "Elmstead", "Fairhaven", "Granite",
    "Halden", "Ironwood", "Juniper", "Keystone", "Lakeshore", "Meridian", "Northgate",
    "Oakridge", "Pinecrest", "Quarry", "Redline", "Summit", "Tidewater", "Underhill",
    "Vantage", "Westbrook", "Yardley", "Zenith", "Ashford", "Brightwater", "Coldbrook",
    "Driftwood", "Eastlake",
]
SUPPLIER_SUFFIXES = ["Precision", "Systems", "Composites", "Electronics", "Machining",
                     "Dynamics", "Components", "Industries", "Technologies", "Works"]
STATES = ["CA", "TX", "OH", "AZ", "WA", "MI", "PA", "AL", "FL", "CO", "MN", "VA", "NH", "UT"]
CUSTOMERS = ["Army - 1st Air Defense Bn", "Army - 4th Air Defense Bn", "Navy - Coastal Riverine Grp 1",
             "Navy - Unmanned Surface Sqn 2", "USMC - 3rd LAAD Bn", "Allied - Partner Nation A",
             "Allied - Partner Nation B"]


@dataclass
class World:
    programs: pd.DataFrame
    parts: pd.DataFrame
    suppliers: pd.DataFrame
    part_sources: pd.DataFrame
    bom: pd.DataFrame
    purchase_order_lines: pd.DataFrame
    work_orders: pd.DataFrame
    assets: pd.DataFrame
    maintenance_events: pd.DataFrame
    supplier_program_enrollment: pd.DataFrame

    def tables(self) -> dict[str, pd.DataFrame]:
        return {k: v for k, v in self.__dict__.items()}


def _months() -> pd.DatetimeIndex:
    return pd.date_range(START, END, freq="MS")


def build_world(seed: int = 7) -> World:
    rng = np.random.default_rng(seed)

    programs = pd.DataFrame(PRODUCTS, columns=["product_id", "product_name", "description",
                                               "build_cycle_days", "monthly_rate"])

    # Parts -------------------------------------------------------------------
    rows = []
    n = 0
    for cat, ((c_lo, c_hi), (l_lo, l_hi)) in CATEGORIES.items():
        for _ in range(int(rng.integers(10, 16))):
            n += 1
            cost = float(np.exp(rng.uniform(np.log(c_lo), np.log(c_hi))))
            rows.append({
                "part_id": f"PN-{n:04d}",
                "part_name": f"{cat} item {n:03d}",
                "category": cat,
                "standard_cost_usd": round(cost, 2),
                "nominal_lead_time_days": int(rng.integers(l_lo, l_hi)),
                "is_flight_critical": bool(rng.random() < (0.55 if cat in
                                          ("Propulsion", "Avionics", "Energetics", "RF & Sensors") else 0.15)),
            })
    parts = pd.DataFrame(rows)

    # Suppliers ----------------------------------------------------------------
    names = rng.choice([f"{s} {x}" for s in SUPPLIER_STEMS for x in SUPPLIER_SUFFIXES], 60, replace=False)
    suppliers = pd.DataFrame({
        "supplier_id": [f"SUP-{i:03d}" for i in range(1, 61)],
        "supplier_name": names,
        "state": rng.choice(STATES, 60),
        "is_small_business": rng.random(60) < 0.45,
        # latent traits, dropped before export
        "_otd": np.clip(rng.beta(8, 2, 60), 0.45, 0.99),
        "_defect": np.exp(rng.normal(np.log(0.018), 0.65, 60)),
    })

    # Sourcing: each part has 1-3 approved suppliers; ~30% are single source.
    src = []
    for p in parts.itertuples():
        k = 1 if rng.random() < 0.3 else int(rng.integers(2, 4))
        chosen = rng.choice(suppliers.supplier_id, k, replace=False)
        shares = rng.dirichlet(np.ones(k) * 2)
        for s, sh in zip(chosen, shares):
            src.append({"part_id": p.part_id, "supplier_id": s, "allocation_share": round(float(sh), 3)})
    part_sources = pd.DataFrame(src)

    # Bill of materials: each product uses 30-45 parts, some shared.
    bom_rows = []
    for prod in programs.itertuples():
        used = rng.choice(parts.part_id, int(rng.integers(30, 46)), replace=False)
        for pid in used:
            bom_rows.append({"product_id": prod.product_id, "part_id": pid,
                             "qty_per_unit": int(rng.choice([1, 1, 1, 2, 2, 4, 8, 24]))})
    bom = pd.DataFrame(bom_rows)

    # Supplier development program: worst-quality third of suppliers, July 2025.
    cutoff = suppliers._defect.quantile(2 / 3)
    enrolled = suppliers[suppliers._defect >= cutoff].supplier_id
    enrollment = pd.DataFrame({"supplier_id": enrolled, "enrolled_on": PROGRAM_START.date()})
    enrolled_set = set(enrolled)

    # Purchase order lines -----------------------------------------------------
    sup_traits = suppliers.set_index("supplier_id")
    part_info = parts.set_index("part_id")
    demand = bom.merge(programs[["product_id", "monthly_rate"]], on="product_id")
    demand["monthly_qty"] = demand.qty_per_unit * demand.monthly_rate
    monthly_part_qty = demand.groupby("part_id").monthly_qty.sum()

    po_rows = []
    line = 0
    for month in _months():
        season = 1 + 0.15 * np.sin((month.month - 3) / 12 * 2 * np.pi)
        ramp = 0.75 + 0.5 * (month - START).days / (END - START).days  # production ramps up
        for part_id, mqty in monthly_part_qty.items():
            srcs = part_sources[part_sources.part_id == part_id]
            for s in srcs.itertuples():
                qty = rng.poisson(max(mqty * s.allocation_share * season * ramp, 0.5))
                if qty == 0:
                    continue
                line += 1
                t = sup_traits.loc[s.supplier_id]
                order_date = month + pd.Timedelta(days=int(rng.integers(0, 28)))
                lead = int(part_info.loc[part_id, "nominal_lead_time_days"])
                promised = order_date + pd.Timedelta(days=lead)
                late = rng.random() > t._otd
                slip = int(rng.gamma(2.0, 9.0)) if late else -int(rng.integers(0, 5))
                received = promised + pd.Timedelta(days=slip)
                rate = t._defect
                if s.supplier_id in enrolled_set and received >= PROGRAM_START:
                    # program effect phases in over ~3 months
                    phase = min(1.0, (received - PROGRAM_START).days / 90)
                    rate *= 1 + TRUE_EFFECT * phase
                rate *= 1.25 if part_info.loc[part_id, "is_flight_critical"] else 1.0
                # Ramp strain: as volume climbs, everyone's quality slips a little.
                rate *= 1 + 0.45 * max(0.0, (received - START).days / (END - START).days)
                rejected = int(rng.binomial(qty, min(rate, 0.6)))
                price = part_info.loc[part_id, "standard_cost_usd"] * rng.normal(1.0, 0.04)
                po_rows.append({
                    "po_line_id": f"POL-{line:06d}",
                    "po_number": f"PO-{order_date:%y%m}-{s.supplier_id[-3:]}",
                    "part_id": part_id,
                    "supplier_id": s.supplier_id,
                    "order_date": order_date.date(),
                    "promised_date": promised.date(),
                    "received_date": received.date() if received <= END else None,
                    "qty_ordered": int(qty),
                    "qty_received": int(qty) if received <= END else 0,
                    "qty_rejected": rejected if received <= END else 0,
                    "unit_price_usd": round(float(price), 2),
                })
    pol = pd.DataFrame(po_rows)

    # Work orders --------------------------------------------------------------
    # A build is blocked when one of its flight-critical parts had a late
    # receipt in the 30 days before planned start.
    late_receipts = pol.dropna(subset=["received_date"]).copy()
    late_receipts["received_date"] = pd.to_datetime(late_receipts.received_date)
    late_receipts["days_late"] = (late_receipts.received_date - pd.to_datetime(late_receipts.promised_date)).dt.days
    late_receipts = late_receipts[late_receipts.days_late > 14]

    wo_rows = []
    w = 0
    for month in _months():
        ramp = 0.75 + 0.5 * (month - START).days / (END - START).days
        for prod in programs.itertuples():
            crit = set(bom[(bom.product_id == prod.product_id)].part_id) & set(parts[parts.is_flight_critical].part_id)
            for _ in range(rng.poisson(prod.monthly_rate * ramp)):
                w += 1
                start = month + pd.Timedelta(days=int(rng.integers(0, 28)))
                window = late_receipts[(late_receipts.received_date > start - pd.Timedelta(days=30))
                                       & (late_receipts.received_date <= start + pd.Timedelta(days=10))
                                       & (late_receipts.part_id.isin(crit))]
                blocked_by, delay = None, 0
                if len(window) and rng.random() < 0.22:  # safety stock absorbs most slips
                    worst = window.sort_values("days_late").iloc[-1]
                    blocked_by = worst.part_id
                    delay = int(worst.days_late * rng.uniform(0.4, 0.9))
                cycle = int(prod.build_cycle_days * rng.normal(0.97, 0.06))
                end = start + pd.Timedelta(days=cycle + delay)
                wo_rows.append({
                    "work_order_id": f"WO-{w:06d}",
                    "product_id": prod.product_id,
                    "planned_start": start.date(),
                    "planned_end": (start + pd.Timedelta(days=prod.build_cycle_days)).date(),
                    "actual_end": end.date() if end <= END else None,
                    "blocked_by_part_id": blocked_by,
                    "status": "complete" if end <= END else "in_progress",
                })
    work_orders = pd.DataFrame(wo_rows)

    # Fielded assets and sustainment ------------------------------------------
    done = work_orders[work_orders.status == "complete"].copy()
    done = done.sample(frac=0.85, random_state=seed)  # remainder is test/attrition
    assets = pd.DataFrame({
        "serial_number": [f"{p[2:]}-{i:05d}" for i, p in enumerate(done.product_id, 1)],
        "product_id": done.product_id.values,
        "work_order_id": done.work_order_id.values,
        "delivered_on": (pd.to_datetime(done.actual_end) + pd.to_timedelta(rng.integers(3, 20, len(done)), "D")).dt.date.values,
        "customer": rng.choice(CUSTOMERS, len(done)),
    })
    assets = assets[pd.to_datetime(assets.delivered_on) <= END].reset_index(drop=True)

    # Maintenance: failures arrive at a product-specific rate; each consumes a
    # spare. Downtime depends on whether the spare's suppliers are reliable.
    fail_rate = {"P-KES": 0.02, "P-PET": 0.11, "P-HAL": 0.06}  # per asset-month
    sup_otd = sup_traits._otd
    part_reliab = part_sources.assign(otd=part_sources.supplier_id.map(sup_otd)) \
        .groupby("part_id").apply(lambda g: np.average(g.otd, weights=g.allocation_share), include_groups=False)
    m_rows = []
    e = 0
    for a in assets.itertuples():
        months_in_field = (END - pd.Timestamp(a.delivered_on)).days / 30.4
        k = rng.poisson(fail_rate[a.product_id] * months_in_field)
        cand = bom[bom.product_id == a.product_id].part_id.values
        for _ in range(k):
            e += 1
            opened = pd.Timestamp(a.delivered_on) + pd.Timedelta(days=int(rng.uniform(0, months_in_field * 30.4)))
            part = rng.choice(cand)
            wait = rng.gamma(2.0, 6.0 + 45 * (1 - part_reliab[part]))
            closed = opened + pd.Timedelta(days=int(1 + wait))
            m_rows.append({
                "maintenance_event_id": f"ME-{e:06d}",
                "serial_number": a.serial_number,
                "opened_on": opened.date(),
                "closed_on": closed.date() if closed <= END else None,
                "failed_part_id": part,
                "failure_mode": rng.choice(["Wear", "Damage", "Electrical fault", "Software", "Corrosion"],
                                           p=[0.35, 0.2, 0.25, 0.1, 0.1]),
            })
    maintenance = pd.DataFrame(m_rows)

    suppliers = suppliers.drop(columns=["_otd", "_defect"])
    return World(programs, parts, suppliers, part_sources, bom, pol, work_orders,
                 assets, maintenance, enrollment)


def write_parquet(world: World, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in world.tables().items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)


if __name__ == "__main__":
    w = build_world()
    for k, v in w.tables().items():
        print(f"{k:32s} {len(v):>7,d}")
