MODEL (
  name analysis.supplier_exposure,
  kind FULL,
  grain (supplier_id, part_id, product_id),
  description 'If this supplier stopped shipping tomorrow: which parts, which products, how many builds and fielded units are exposed.'
);

WITH share AS (
  SELECT
    ps.supplier_id,
    ps.part_id,
    ps.allocation_share,
    p.is_sole_source,
    p.is_flight_critical,
    p.category,
    p.nominal_lead_time_days
  FROM staging.part_sources AS ps
  JOIN core.parts AS p
    ON ps.part_id = p.part_id
), fleet AS (
  SELECT product_id, COUNT(*) AS fielded_units
  FROM core.assets
  GROUP BY product_id
), spares AS (
  /* Spares demand: how often each part fails in the field, per product. */
  SELECT product_id, failed_part_id AS part_id, COUNT(*) AS field_failures_12m
  FROM core.maintenance_events
  WHERE opened_on > @as_of::DATE - INTERVAL 12 MONTH
  GROUP BY ALL
)
SELECT
  s.supplier_id,
  s.part_id,
  b.product_id,
  s.category,
  s.is_flight_critical,
  s.is_sole_source,
  s.allocation_share,
  b.qty_per_unit,
  /* Builds that cannot start within one replacement lead time if this supply stops.
     Sole-source parts stop the line outright; split parts lose this supplier's share. */
  pr.planned_monthly_rate * s.nominal_lead_time_days / 30.0
    * CASE WHEN s.is_sole_source THEN 1.0 ELSE s.allocation_share END AS builds_at_risk,
  COALESCE(f.fielded_units, 0) AS fielded_units_using_part,
  COALESCE(sp.field_failures_12m, 0) AS field_failures_12m
FROM share AS s
JOIN staging.bill_of_materials AS b
  ON s.part_id = b.part_id
JOIN core.products AS pr
  ON b.product_id = pr.product_id
LEFT JOIN fleet AS f
  ON b.product_id = f.product_id
LEFT JOIN spares AS sp
  ON b.product_id = sp.product_id AND s.part_id = sp.part_id
