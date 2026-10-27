MODEL (
  name staging.work_orders,
  kind VIEW,
  grain work_order_id,
  audits (
    not_null(columns := (work_order_id, product_id, planned_start, status)),
    unique_values(columns := (work_order_id)),
    accepted_values(column := status, is_in := ('complete', 'in_progress'))
  )
);

SELECT
  work_order_id::TEXT AS work_order_id,
  product_id::TEXT AS product_id,
  planned_start::DATE AS planned_start,
  planned_end::DATE AS planned_end,
  actual_end::DATE AS actual_end,
  blocked_by_part_id::TEXT AS blocked_by_part_id,
  status::TEXT AS status
FROM erp.work_orders
