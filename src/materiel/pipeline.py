"""The end-to-end pipeline as a Flyte workflow.

    uv run pyflyte run src/materiel/pipeline.py pipeline

runs it locally; the same file registers to a Flyte cluster unchanged. Steps:
extract and land as Iceberg -> transform with SQLMesh (tests, then models and
audits) -> export for the web app.
"""

from __future__ import annotations

from pathlib import Path

from flytekit import task, workflow

ROOT = Path(__file__).resolve().parents[2]


@task(cache=False)
def land(seed: int) -> list[str]:
    from materiel.generate import build_world
    from materiel.lake import land as land_tables
    from materiel.lake import register

    land_tables(build_world(seed))
    return register()


@task
def transform(tables: list[str]) -> int:
    from sqlmesh import Context

    ctx = Context(paths=[ROOT / "transform"])
    tests = ctx.test()
    if not tests.wasSuccessful():
        raise RuntimeError("SQLMesh unit tests failed")
    # First run (a fresh clone, or CI): build everything. Later runs: new data,
    # same code, so apply any model changes and rebuild everything downstream
    # of the refreshed sources. Audits run as each model builds.
    if ctx.state_reader.get_environment("prod") is None:
        ctx.plan(auto_apply=True, no_prompts=True)
    else:
        ctx.plan(auto_apply=True, no_prompts=True, restate_models=["core.*", "analysis.*"])
    n = len(ctx.models)
    ctx.close()  # release the DuckDB file for the export step
    return n


@task
def export(models_built: int, out: str) -> str:
    from materiel.export import main

    return str(main(Path(out)))


@workflow
def pipeline(seed: int = 7, out: str = str(ROOT / "export" / "materiel.json")) -> str:
    tables = land(seed=seed)
    n = transform(tables=tables)
    return export(models_built=n, out=out)


if __name__ == "__main__":
    print(pipeline())
