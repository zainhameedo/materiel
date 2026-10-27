MODEL (
  name analysis.part_risk,
  kind FULL,
  grain part_id,
  description 'Parts ranked by how likely and how badly they stop production.',
  audits (unique_values(columns := (part_id)), accepted_range(column := risk_score, min_v := 0, max_v := 100))
);

WITH blocks AS (
  SELECT blocked_by_part_id AS part_id, COUNT(*) AS builds_blocked, SUM(days_past_plan) AS build_days_lost
  FROM core.work_orders
  WHERE was_blocked_by_shortage
  GROUP BY 1
), exposure AS (
  /* Builds that needed the part: every work order for a product whose BOM includes it. */
  SELECT b.part_id, COUNT(*) AS builds_using_part
  FROM staging.bill_of_materials AS b
  JOIN core.work_orders AS w
    ON b.product_id = w.product_id
  GROUP BY 1
), scored AS (
  SELECT
    p.*,
    COALESCE(bl.builds_blocked, 0) AS builds_blocked,
    COALESCE(bl.build_days_lost, 0) AS build_days_lost,
    /* Likelihood: half forward-looking (late suppliers, few alternatives),
       half observed (share of builds this part has already stopped). */
    0.5 * (1 - COALESCE(p.supplier_on_time_rate, 0.8)) / p.n_suppliers
      + 0.5 * COALESCE(bl.builds_blocked, 0) / ex.builds_using_part AS likelihood,
    /* Impact: criticality, breadth of use, replacement lead time (capped at 6 months). */
    (CASE WHEN p.is_flight_critical THEN 1.0 ELSE 0.4 END)
      * p.used_in_products
      * LEAST(COALESCE(p.actual_lead_time_days, p.nominal_lead_time_days), 180) / 180.0 AS impact
  FROM core.parts AS p
  JOIN exposure AS ex
    ON p.part_id = ex.part_id
  LEFT JOIN blocks AS bl
    ON p.part_id = bl.part_id
)
SELECT
  part_id,
  part_name,
  category,
  is_flight_critical,
  is_sole_source,
  n_suppliers,
  used_in_products,
  supplier_on_time_rate,
  actual_lead_time_days,
  spend_usd_12m,
  builds_blocked,
  build_days_lost,
  likelihood,
  impact,
  /* Scaled so the riskiest part scores 100. */
  ROUND(100 * likelihood * impact / MAX(likelihood * impact) OVER (), 1) AS risk_score
FROM scored
