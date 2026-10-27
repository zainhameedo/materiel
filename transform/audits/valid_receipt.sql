AUDIT (name valid_receipt);
-- A receipt can't precede its order, and can't reject more than it received.
SELECT *
FROM @this_model
WHERE received_date < order_date
   OR qty_rejected > qty_received
   OR qty_received > qty_ordered
