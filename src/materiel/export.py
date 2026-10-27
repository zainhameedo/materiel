"""Export the modeled data as one compact JSON file for the static web app."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from materiel.causal import estimate, load_panel
from materiel.lake import WAREHOUSE


def _rows(con, sql: str) -> list[dict]:
    df = con.sql(sql).df()
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime"):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return json.loads(df.to_json(orient="records", date_format="iso", double_precision=4))


def build_payload() -> dict:
    con = duckdb.connect((WAREHOUSE / "materiel.duckdb").as_posix(), read_only=True)
    q = lambda sql: _rows(con, sql)  # noqa: E731

    payload = {
        "as_of": "2026-09-30",
        "products": q("""
            SELECT p.product_id AS id, p.product_name AS name, p.description, p.bom_lines,
                   p.critical_parts, p.critical_sole_source_parts,
                   (SELECT COUNT(*) FROM core.assets a WHERE a.product_id = p.product_id) AS fleet,
                   (SELECT COUNT(*) FROM core.assets a WHERE a.product_id = p.product_id AND a.is_down) AS down_now
            FROM core.products p ORDER BY p.product_id DESC"""),
        "readiness": q("""SELECT product_id AS p, strftime(month, '%Y-%m') AS m, availability AS a, asset_days AS n
                          FROM analysis.fleet_readiness_monthly ORDER BY month"""),
        "builds": q("""SELECT product_id AS p, strftime(month, '%Y-%m') AS m, builds_started AS s,
                              builds_completed AS c, on_time_rate AS ot, builds_blocked AS b
                       FROM analysis.build_performance_monthly ORDER BY month"""),
        "suppliers": q("""
            SELECT supplier_id AS id, supplier_name AS name, state, parts_supplied AS parts,
                   sole_source_parts AS sole, on_time_rate_12m AS otd, defect_ppm_12m AS ppm,
                   spend_usd_12m AS spend, development_program_enrolled_on IS NOT NULL AS enrolled
            FROM core.suppliers ORDER BY supplier_id"""),
        "parts": q("""
            SELECT part_id AS id, category AS cat, is_flight_critical AS crit, is_sole_source AS sole,
                   n_suppliers AS ns, actual_lead_time_days AS lt, risk_score AS risk,
                   builds_blocked AS blocked, build_days_lost AS days_lost,
                   likelihood AS lk, impact AS im, spend_usd_12m AS spend
            FROM analysis.part_risk ORDER BY risk_score DESC"""),
        "sources": q("SELECT part_id AS part, supplier_id AS sup, allocation_share AS share FROM staging.part_sources"),
        "bom": q("SELECT product_id AS prod, part_id AS part, qty_per_unit AS qty FROM staging.bill_of_materials"),
        "exposure": q("""
            SELECT supplier_id AS sup, part_id AS part, product_id AS prod, builds_at_risk AS builds,
                   fielded_units_using_part AS fleet, field_failures_12m AS failures
            FROM analysis.supplier_exposure"""),
    }
    con.close()
    payload["program"] = estimate(load_panel())
    return payload


def main(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_payload(), separators=(",", ":")))
    return out


if __name__ == "__main__":
    path = main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("export/materiel.json"))
    print(path, f"{path.stat().st_size / 1024:.0f} KB")
