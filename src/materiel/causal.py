"""Did the supplier development program reduce defects?

The program enrolled the suppliers with the worst quality, so the obvious
comparisons mislead:

* enrolled vs. not, after launch: enrolled suppliers still look far worse,
  because they started far worse (selection).
* enrolled, before vs. after: picks up anything else that changed over time.

Difference-in-differences nets out both: supplier fixed effects absorb each
supplier's baseline, month fixed effects absorb shocks common to everyone.
Defects are counts out of units inspected, so the model is a Poisson GLM with
log(units received) as exposure; coefficients read as proportional changes in
the defect rate. Standard errors are clustered by supplier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from materiel.lake import WAREHOUSE


@dataclass
class Estimate:
    label: str
    effect: float  # proportional change in defect rate, e.g. -0.3 = 30% fewer
    ci_low: float | None
    ci_high: float | None
    note: str


def load_panel() -> pd.DataFrame:
    con = duckdb.connect((WAREHOUSE / "materiel.duckdb").as_posix(), read_only=True)
    df = con.sql("SELECT * FROM analysis.supplier_quality_panel").df()
    con.close()
    df["month"] = pd.to_datetime(df.month)
    # Nullable columns from the warehouse: not enrolled means no enrollment date.
    df["enrolled"] = df.enrolled.astype(bool)
    df["post_enrollment"] = df.post_enrollment.astype("boolean").fillna(False).astype(bool)
    df["months_from_enrollment"] = df.months_from_enrollment.astype("Float64").astype(float)
    df["treated_post"] = (df.enrolled & df.post_enrollment).astype(int)
    return df


def _rate(df: pd.DataFrame) -> float:
    return df.units_rejected.sum() / df.units_received.sum()


def _poisson(formula: str, df: pd.DataFrame):
    model = smf.glm(formula, data=df, family=sm.families.Poisson(), offset=np.log(df.units_received))
    return model.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.supplier_id)[0]})


def _pct(b: float) -> float:
    return float(np.expm1(b))


def estimate(df: pd.DataFrame) -> dict:
    post = df.month >= "2025-07-01"
    enrolled = df.enrolled

    naive_cross = _rate(df[post & enrolled]) / _rate(df[post & ~enrolled]) - 1
    naive_prepost = _rate(df[post & enrolled]) / _rate(df[~post & enrolled]) - 1

    did = _poisson("units_rejected ~ treated_post + C(supplier_id) + C(month)", df)
    b, (lo, hi) = did.params["treated_post"], did.conf_int().loc["treated_post"]

    # Placebo: pretend the program launched in Jan 2025, using only pre-launch data.
    pre = df[~post].copy()
    pre["fake_post"] = (pre.enrolled & (pre.month >= "2025-01-01")).astype(int)
    plc = _poisson("units_rejected ~ fake_post + C(supplier_id) + C(month)", pre)
    pb, (plo, phi) = plc.params["fake_post"], plc.conf_int().loc["fake_post"]

    estimates = [
        Estimate("Enrolled vs. not enrolled, after launch", naive_cross, None, None,
                 "Says the program made things worse. Enrolled suppliers were chosen for bad quality."),
        Estimate("Enrolled suppliers, before vs. after", naive_prepost, None, None,
                 "Right direction, but credits the program with anything else that changed."),
        Estimate("Difference-in-differences", _pct(b), _pct(lo), _pct(hi),
                 "Supplier and month fixed effects; 95% CI clustered by supplier."),
        Estimate("Placebo: fake launch in Jan 2025", _pct(pb), _pct(plo), _pct(phi),
                 "Should be near zero. It is, so pre-trends look parallel."),
    ]
    return {"estimates": [asdict(e) for e in estimates], "event_study": event_study(df),
            "trend": raw_trend(df)}


def event_study(df: pd.DataFrame, window: tuple[int, int] = (-12, 14)) -> list[dict]:
    """Effect by month relative to enrollment; month -1 is the reference."""
    d = df.copy()
    rel = d.months_from_enrollment.where(d.enrolled)
    lo, hi = window
    terms = []
    for k in range(lo, hi + 1):
        if k == -1:
            continue
        name = f"m{k + 100}"  # keep names formula-safe
        d[name] = (rel == k).astype(int)
        terms.append((k, name))
    fit = _poisson("units_rejected ~ " + " + ".join(n for _, n in terms) + " + C(supplier_id) + C(month)",
                   d[(rel.isna()) | rel.between(lo, hi)])
    ci = fit.conf_int()
    out = [{"k": -1, "effect": 0.0, "low": 0.0, "high": 0.0}]
    for k, n in terms:
        out.append({"k": k, "effect": _pct(fit.params[n]), "low": _pct(ci.loc[n, 0]), "high": _pct(ci.loc[n, 1])})
    return sorted(out, key=lambda r: r["k"])


def raw_trend(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(["month", "enrolled"])[["units_rejected", "units_received"]].sum().reset_index()
    g["ppm"] = 1e6 * g.units_rejected / g.units_received
    wide = g.pivot(index="month", columns="enrolled", values="ppm").reset_index()
    return [{"month": m.strftime("%Y-%m"), "enrolled": round(float(t), 0), "others": round(float(c), 0)}
            for m, c, t in wide[["month", False, True]].itertuples(index=False)]


if __name__ == "__main__":
    res = estimate(load_panel())
    for e in res["estimates"]:
        ci = "" if e["ci_low"] is None else f"  [{e['ci_low']:+.1%}, {e['ci_high']:+.1%}]"
        print(f"{e['label']:45s} {e['effect']:+.1%}{ci}")
