"""SQLMesh project config.

Runs in DuckDB over the Iceberg warehouse in ../warehouse. In production the
same models would run on Athena against Iceberg on S3; only this file changes.
"""

from pathlib import Path

from sqlmesh.core.config import (
    Config,
    DuckDBConnectionConfig,
    GatewayConfig,
    LinterConfig,
    ModelDefaultsConfig,
)

ROOT = Path(__file__).resolve().parents[1]

config = Config(
    gateways={
        "local": GatewayConfig(
            connection=DuckDBConnectionConfig(
                database=(ROOT / "warehouse" / "materiel.duckdb").as_posix(),
                extensions=["iceberg"],
            ),
        ),
    },
    default_gateway="local",
    model_defaults=ModelDefaultsConfig(dialect="duckdb", start="2024-01-01"),
    # The data ends 2026-09-30; pin "today" so every run is reproducible.
    variables={"as_of": "2026-09-30"},
    linter=LinterConfig(enabled=True, rules=["ambiguousorinvalidcolumn", "invalidselectstarexpansion"]),
)
