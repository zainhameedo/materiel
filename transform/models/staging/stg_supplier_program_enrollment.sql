MODEL (
  name staging.supplier_program_enrollment,
  kind VIEW,
  grain supplier_id,
  audits (unique_values(columns := (supplier_id)))
);

SELECT
  supplier_id::TEXT AS supplier_id,
  enrolled_on::DATE AS enrolled_on
FROM erp.supplier_program_enrollment
