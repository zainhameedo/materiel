MODEL (
  name core.products,
  kind FULL,
  grain product_id,
  audits (unique_values(columns := (product_id)))
);

SELECT
  pr.product_id,
  pr.product_name,
  pr.description,
  pr.standard_build_days,
  pr.planned_monthly_rate,
  COUNT(b.part_id) AS bom_lines,
  SUM(b.qty_per_unit * p.standard_cost_usd) AS bom_cost_usd,
  COUNT(*) FILTER (WHERE p.is_flight_critical) AS critical_parts,
  COUNT(*) FILTER (WHERE p.is_flight_critical AND p.is_sole_source) AS critical_sole_source_parts
FROM staging.products AS pr
LEFT JOIN staging.bill_of_materials AS b
  ON pr.product_id = b.product_id
LEFT JOIN core.parts AS p
  ON b.part_id = p.part_id
GROUP BY ALL
