MODEL (
  name core.suppliers,
  kind FULL,
  grain supplier_id,
  audits (unique_values(columns := (supplier_id)), accepted_range(column := on_time_rate_12m, min_v := 0, max_v := 1))
);

WITH last_12m AS (
  SELECT
    supplier_id,
    COUNT(*) FILTER (WHERE is_received) AS lines_received,
    AVG(is_on_time::INT) FILTER (WHERE is_received) AS on_time_rate,
    1e6 * SUM(qty_rejected) / NULLIF(SUM(qty_received), 0) AS defect_ppm,
    SUM(extended_value_usd) AS spend_usd
  FROM core.purchase_order_lines
  WHERE order_date > @as_of::DATE - INTERVAL 12 MONTH
  GROUP BY supplier_id
), sourcing AS (
  SELECT
    ps.supplier_id,
    COUNT(*) AS parts_supplied,
    COUNT(*) FILTER (WHERE n.n_sources = 1) AS sole_source_parts
  FROM staging.part_sources AS ps
  JOIN (SELECT part_id, COUNT(*) AS n_sources FROM staging.part_sources GROUP BY part_id) AS n
    ON ps.part_id = n.part_id
  GROUP BY ps.supplier_id
)
SELECT
  s.supplier_id,
  s.supplier_name,
  s.state,
  s.is_small_business,
  COALESCE(src.parts_supplied, 0) AS parts_supplied,
  COALESCE(src.sole_source_parts, 0) AS sole_source_parts,
  l.lines_received AS lines_received_12m,
  l.on_time_rate AS on_time_rate_12m,
  l.defect_ppm AS defect_ppm_12m,
  l.spend_usd AS spend_usd_12m,
  e.enrolled_on AS development_program_enrolled_on
FROM staging.suppliers AS s
LEFT JOIN sourcing AS src
  ON s.supplier_id = src.supplier_id
LEFT JOIN last_12m AS l
  ON s.supplier_id = l.supplier_id
LEFT JOIN staging.supplier_program_enrollment AS e
  ON s.supplier_id = e.supplier_id
