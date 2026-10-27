MODEL (
  name staging.maintenance_events,
  kind VIEW,
  grain maintenance_event_id,
  audits (not_null(columns := (maintenance_event_id, serial_number, opened_on)), unique_values(columns := (maintenance_event_id)))
);

SELECT
  maintenance_event_id::TEXT AS maintenance_event_id,
  serial_number::TEXT AS serial_number,
  opened_on::DATE AS opened_on,
  closed_on::DATE AS closed_on,
  failed_part_id::TEXT AS failed_part_id,
  failure_mode::TEXT AS failure_mode
FROM erp.maintenance_events
