MODEL (
  name staging.suppliers,
  kind VIEW,
  grain supplier_id,
  audits (not_null(columns := (supplier_id, supplier_name)), unique_values(columns := (supplier_id)))
);

SELECT
  supplier_id::TEXT AS supplier_id,
  supplier_name::TEXT AS supplier_name,
  state::TEXT AS state,
  is_small_business::BOOLEAN AS is_small_business
FROM erp.suppliers
