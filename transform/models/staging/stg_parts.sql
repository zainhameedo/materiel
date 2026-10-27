MODEL (
  name staging.parts,
  kind VIEW,
  grain part_id,
  audits (not_null(columns := (part_id, category)), unique_values(columns := (part_id)))
);

SELECT
  part_id::TEXT AS part_id,
  part_name::TEXT AS part_name,
  category::TEXT AS category,
  standard_cost_usd::DECIMAL(12, 2) AS standard_cost_usd,
  nominal_lead_time_days::INT AS nominal_lead_time_days,
  is_flight_critical::BOOLEAN AS is_flight_critical
FROM erp.parts
