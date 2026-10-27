MODEL (
  name core.assets,
  kind FULL,
  grain serial_number,
  audits (unique_values(columns := (serial_number)))
);

/* A fielded unit, with its maintenance history rolled up. */
SELECT
  a.serial_number,
  a.product_id,
  a.work_order_id,
  a.customer,
  a.delivered_on,
  DATEDIFF('day', a.delivered_on, @as_of::DATE) AS days_in_service,
  COUNT(m.maintenance_event_id) AS maintenance_events,
  COUNT(m.maintenance_event_id) FILTER (WHERE m.is_open) > 0 AS is_down,
  SUM(m.downtime_days) AS downtime_days
FROM staging.assets AS a
LEFT JOIN core.maintenance_events AS m
  ON a.serial_number = m.serial_number
GROUP BY ALL
