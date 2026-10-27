MODEL (
  name analysis.supplier_quality_panel,
  kind FULL,
  grain (supplier_id, month),
  description 'Supplier x month receiving-inspection panel for evaluating the supplier development program.'
);

SELECT
  pol.supplier_id,
  pol.receipt_month AS month,
  SUM(pol.qty_received) AS units_received,
  SUM(pol.qty_rejected) AS units_rejected,
  e.enrolled_on IS NOT NULL AS enrolled,
  pol.receipt_month >= e.enrolled_on AS post_enrollment,
  DATEDIFF('month', e.enrolled_on, pol.receipt_month) AS months_from_enrollment
FROM core.purchase_order_lines AS pol
LEFT JOIN staging.supplier_program_enrollment AS e
  ON pol.supplier_id = e.supplier_id
WHERE pol.is_received
GROUP BY ALL
HAVING SUM(pol.qty_received) > 0
