MODEL (
  name analysis.build_performance_monthly,
  kind FULL,
  grain (product_id, month)
);

SELECT
  product_id,
  start_month AS month,
  COUNT(*) AS builds_started,
  COUNT(*) FILTER (WHERE status = 'complete') AS builds_completed,
  AVG(is_on_time::INT) FILTER (WHERE status = 'complete') AS on_time_rate,
  AVG(build_days) FILTER (WHERE status = 'complete') AS avg_build_days,
  COUNT(*) FILTER (WHERE was_blocked_by_shortage) AS builds_blocked
FROM core.work_orders
GROUP BY ALL
