MODEL (
  name core.purchase_order_lines,
  kind FULL,
  grain po_line_id,
  references (part_id, supplier_id),
  audits (unique_values(columns := (po_line_id)))
);

SELECT
  pol.po_line_id,
  pol.po_number,
  pol.part_id,
  pol.supplier_id,
  pol.order_date,
  pol.promised_date,
  pol.received_date,
  pol.qty_ordered,
  pol.qty_received,
  pol.qty_rejected,
  pol.unit_price_usd,
  pol.qty_ordered * pol.unit_price_usd AS extended_value_usd,
  pol.received_date IS NOT NULL AS is_received,
  /* Open lines past their promise date count as late as of today. */
  DATEDIFF('day', pol.promised_date, COALESCE(pol.received_date, @as_of::DATE)) AS days_late,
  pol.received_date IS NOT NULL AND pol.received_date <= pol.promised_date AS is_on_time,
  DATE_TRUNC('month', COALESCE(pol.received_date, pol.promised_date))::DATE AS receipt_month
FROM staging.purchase_order_lines AS pol
