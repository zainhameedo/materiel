MODEL (
  name core.parts,
  kind FULL,
  grain part_id,
  audits (unique_values(columns := (part_id)))
);

WITH sources AS (
  SELECT
    ps.part_id,
    COUNT(*) AS n_suppliers,
    /* Allocation-weighted reliability of the suppliers who make this part. */
    SUM(ps.allocation_share * s.on_time_rate_12m) / SUM(ps.allocation_share) AS supplier_on_time_rate
  FROM staging.part_sources AS ps
  JOIN core.suppliers AS s
    ON ps.supplier_id = s.supplier_id
  GROUP BY ps.part_id
), usage AS (
  SELECT
    part_id,
    COUNT(*) AS used_in_products,
    LIST(product_id ORDER BY product_id) AS product_ids
  FROM staging.bill_of_materials
  GROUP BY part_id
), receipts AS (
  SELECT
    part_id,
    MEDIAN(DATEDIFF('day', order_date, received_date)) AS actual_lead_time_days,
    SUM(extended_value_usd) FILTER (WHERE order_date > @as_of::DATE - INTERVAL 12 MONTH) AS spend_usd_12m
  FROM core.purchase_order_lines
  WHERE is_received
  GROUP BY part_id
)
SELECT
  p.part_id,
  p.part_name,
  p.category,
  p.standard_cost_usd,
  p.is_flight_critical,
  p.nominal_lead_time_days,
  r.actual_lead_time_days,
  src.n_suppliers,
  src.n_suppliers = 1 AS is_sole_source,
  src.supplier_on_time_rate,
  COALESCE(u.used_in_products, 0) AS used_in_products,
  u.product_ids,
  r.spend_usd_12m
FROM staging.parts AS p
LEFT JOIN sources AS src
  ON p.part_id = src.part_id
LEFT JOIN usage AS u
  ON p.part_id = u.part_id
LEFT JOIN receipts AS r
  ON p.part_id = r.part_id
