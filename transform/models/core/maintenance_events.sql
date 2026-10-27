MODEL (
  name core.maintenance_events,
  kind FULL,
  grain maintenance_event_id,
  audits (unique_values(columns := (maintenance_event_id)), accepted_range(column := downtime_days, min_v := 0))
);

SELECT
  m.maintenance_event_id,
  m.serial_number,
  a.product_id,
  m.failed_part_id,
  m.failure_mode,
  m.opened_on,
  m.closed_on,
  m.closed_on IS NULL AS is_open,
  DATEDIFF('day', m.opened_on, COALESCE(m.closed_on, @as_of::DATE)) AS downtime_days
FROM staging.maintenance_events AS m
JOIN staging.assets AS a
  ON m.serial_number = a.serial_number
