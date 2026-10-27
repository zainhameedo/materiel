"""Land source extracts as Apache Iceberg tables in a local warehouse.

Production would point the same catalog at S3 and Glue; locally a SQLite
catalog and a directory stand in for them. Each load is an overwrite that
creates a new snapshot, so earlier extracts stay queryable (time travel).
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog

from materiel.generate import World

ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = ROOT / "warehouse"
NAMESPACE = "erp"


def catalog() -> SqlCatalog:
    WAREHOUSE.mkdir(exist_ok=True)
    return SqlCatalog(
        "local",
        uri=f"sqlite:///{(WAREHOUSE / 'catalog.db').as_posix()}",
        warehouse=WAREHOUSE.as_posix(),  # a plain path; file:// URIs break on Windows
    )


def land(world: World) -> dict[str, str]:
    """Write every source table; return name -> current metadata file path."""
    cat = catalog()
    cat.create_namespace_if_not_exists(NAMESPACE)
    locations = {}
    for name, df in world.tables().items():
        arrow = pa.Table.from_pandas(df, preserve_index=False)
        ident = f"{NAMESPACE}.{name}"
        if cat.table_exists(ident):
            table = cat.load_table(ident)
            with table.update_schema() as upd:
                upd.union_by_name(arrow.schema)
            table.overwrite(arrow)
        else:
            table = cat.create_table(ident, schema=arrow.schema)
            table.append(arrow)
        locations[name] = table.metadata_location
    return locations


def metadata_locations() -> dict[str, str]:
    cat = catalog()
    return {ident[1]: cat.load_table(ident).metadata_location for ident in cat.list_tables(NAMESPACE)}


def register(db_path: Path = WAREHOUSE / "materiel.duckdb") -> list[str]:
    """Point one DuckDB view per source table at its current Iceberg snapshot.

    Transformation models read `erp.<table>`; re-registering after a load
    moves them to the new snapshot without touching model code.
    """
    import duckdb

    con = duckdb.connect(db_path.as_posix())
    con.sql("INSTALL iceberg; LOAD iceberg;")
    con.sql(f"CREATE SCHEMA IF NOT EXISTS {NAMESPACE}")
    names = []
    for name, location in sorted(metadata_locations().items()):
        con.sql(f"CREATE OR REPLACE VIEW {NAMESPACE}.{name} AS SELECT * FROM iceberg_scan('{location}')")
        names.append(name)
    con.close()
    return names


if __name__ == "__main__":
    from materiel.generate import build_world

    land(build_world())
    print("registered:", ", ".join(register()))
