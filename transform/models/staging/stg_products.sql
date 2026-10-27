MODEL (
  name staging.products,
  kind VIEW,
  grain product_id,
  audits (not_null(columns := (product_id, product_name)), unique_values(columns := (product_id)))
);

SELECT
  product_id::TEXT AS product_id,
  product_name::TEXT AS product_name,
  description::TEXT AS description,
  build_cycle_days::INT AS standard_build_days,
  monthly_rate::INT AS planned_monthly_rate
FROM erp.programs
