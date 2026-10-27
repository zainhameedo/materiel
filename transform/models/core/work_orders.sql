MODEL (
  name core.work_orders,
  kind FULL,
  grain work_order_id,
  audits (unique_values(columns := (work_order_id)))
);

SELECT
  wo.work_order_id,
  wo.product_id,
  wo.status,
  wo.planned_start,
  wo.planned_end,
  wo.actual_end,
  wo.blocked_by_part_id,
  wo.blocked_by_part_id IS NOT NULL AS was_blocked_by_shortage,
  DATEDIFF('day', wo.planned_start, wo.actual_end) AS build_days,
  DATEDIFF('day', wo.planned_end, COALESCE(wo.actual_end, @as_of::DATE)) AS days_past_plan,
  wo.actual_end <= wo.planned_end + 5 AS is_on_time,
  DATE_TRUNC('month', wo.planned_start)::DATE AS start_month
FROM staging.work_orders AS wo
