MODEL (
  name staging.bill_of_materials,
  kind VIEW,
  grain (product_id, part_id),
  audits (
    unique_combination_of_columns(columns := (product_id, part_id)),
    accepted_range(column := qty_per_unit, min_v := 1, max_v := 100)
  )
);

SELECT
  product_id::TEXT AS product_id,
  part_id::TEXT AS part_id,
  qty_per_unit::INT AS qty_per_unit
FROM erp.bom
