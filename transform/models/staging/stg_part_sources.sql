MODEL (
  name staging.part_sources,
  kind VIEW,
  grain (part_id, supplier_id),
  audits (
    not_null(columns := (part_id, supplier_id)),
    unique_combination_of_columns(columns := (part_id, supplier_id)),
    accepted_range(column := allocation_share, min_v := 0, max_v := 1)
  )
);

SELECT
  part_id::TEXT AS part_id,
  supplier_id::TEXT AS supplier_id,
  allocation_share::DOUBLE AS allocation_share
FROM erp.part_sources
