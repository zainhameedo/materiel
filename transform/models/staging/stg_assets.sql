MODEL (
  name staging.assets,
  kind VIEW,
  grain serial_number,
  audits (not_null(columns := (serial_number, product_id, delivered_on)), unique_values(columns := (serial_number)))
);

SELECT
  serial_number::TEXT AS serial_number,
  product_id::TEXT AS product_id,
  work_order_id::TEXT AS work_order_id,
  delivered_on::DATE AS delivered_on,
  customer::TEXT AS customer
FROM erp.assets
