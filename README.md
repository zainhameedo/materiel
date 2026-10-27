# materiel

A working model of a defense hardware manufacturer, from purchase order to fielded unit, and four questions it answers:

1. If a supplier stopped shipping tomorrow, what couldn't we build?
2. Which parts are most likely to stop production?
3. How ready is the fielded fleet, and why?
4. Did the supplier development program reduce defects?

The write-up, with interactive figures, is at **[zainhameedo.com/materiel](https://zainhameedo.com/materiel/)**.

The company and its data are synthetic. The generator ([`generate.py`](src/materiel/generate.py)) simulates realistic mechanics: late parts stall builds, bad lots fail inspection, fielded units fail and wait on spares. It also plants one causal effect, a 35% cut in defect rates for suppliers enrolled in a development program, so the analysis can be checked against a known answer.

## Pipeline

```
source extracts ──► Iceberg ──► SQLMesh ───────────────────────────► export ──► web page
 (10 tables)       snapshots    staging ─► entities ─► analysis         JSON
                                 views     product       exposure
                                           part          part risk
                                           supplier      readiness
                                           order line    quality panel ──► Poisson DiD
                                           build                           (statsmodels)
                                           fielded unit
                                           repair
└───────────────────────────── one Flyte workflow ─────────────────────────────┘
```

| Layer | What it does |
|---|---|
| [`lake.py`](src/materiel/lake.py) | Lands each source table as an Apache Iceberg table (local SQLite catalog standing in for Glue/S3) and points a DuckDB view at its current snapshot. |
| [`transform/models/staging`](transform/models/staging) | Typed, renamed views over the sources, with key and validity audits. |
| [`transform/models/core`](transform/models/core) | One definition of each thing the business talks about, with relationships and derived facts: is this order late, is this unit down, how many sources does this part have. |
| [`transform/models/analysis`](transform/models/analysis) | Supplier exposure, part risk, build performance, fleet readiness, and the supplier quality panel. |
| [`causal.py`](src/materiel/causal.py) | Naive comparisons vs. difference-in-differences (Poisson, supplier and month fixed effects, clustered SEs), an event study and a placebo. |
| [`pipeline.py`](src/materiel/pipeline.py) | The Flyte workflow: land, test, plan and audit, export. |

22 models, 33 audits run on every build, SQLMesh unit tests for the logic that is easiest to get wrong (lateness of open orders, repair intervals clipped to months), and pytest checks that the estimator recovers the planted effect and finds none in the placebo.

## Run it

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pyflyte run src/materiel/pipeline.py pipeline   # land, transform, export (~30s)
uv run pytest -q                                        # estimator tests
cd transform && uv run sqlmesh test                     # model unit tests
```

Explore the models with `cd transform && uv run sqlmesh ui`, or query the warehouse directly:

```bash
cd transform && uv run sqlmesh fetchdf "select * from analysis.part_risk order by risk_score desc limit 10"
```

## Production shape

Locally everything runs on DuckDB over a directory. With real systems behind it, the catalog becomes Glue, the warehouse S3, and SQLMesh runs on Athena; only `lake.py`'s catalog and `transform/config.py`'s gateway change. Sources would land incrementally, and the larger fact models (order lines, work orders) would become incremental by time.

## What's simplified

- Exposure uses lead time, not inventory. With on-hand and safety stock it becomes days of cover.
- The risk weights are judgment; with history they should be fit against which parts actually blocked builds the next quarter.
- The program launched on one date. A staggered rollout needs an estimator built for it (e.g. Callaway and Sant'Anna), because two-way fixed effects can be badly biased there.
