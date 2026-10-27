MODEL (
  name staging.purchase_order_lines,
  kind VIEW,
  grain po_line_id,
  audits (
    not_null(columns := (po_line_id, part_id, supplier_id, order_date, promised_date)),
    unique_values(columns := (po_line_id)),
    valid_receipt
  )
);

SELECT
  po_line_id::TEXT AS po_line_id,
  po_number::TEXT AS po_number,
  part_id::TEXT AS part_id,
  supplier_id::TEXT AS supplier_id,
  order_date::DATE AS order_date,
  promised_date::DATE AS promised_date,
  received_date::DATE AS received_date,
  qty_ordered::INT AS qty_ordered,
  qty_received::INT AS qty_received,
  qty_rejected::INT AS qty_rejected,
  unit_price_usd::DECIMAL(12, 2) AS unit_price_usd
FROM erp.purchase_order_lines
