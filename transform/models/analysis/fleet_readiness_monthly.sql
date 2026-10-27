MODEL (
  name analysis.fleet_readiness_monthly,
  kind FULL,
  grain (product_id, month),
  description 'Share of fielded asset-days that units were mission capable.'
);

/* Each unit and each open repair is an interval; clip it to the month and count days. */
WITH months AS (
  SELECT
    month::DATE AS month_start,
    LEAST(month + INTERVAL 1 MONTH, @as_of::DATE + INTERVAL 1 DAY)::DATE AS month_end
  FROM (SELECT UNNEST(GENERATE_SERIES(DATE '2024-01-01', @as_of::DATE, INTERVAL 1 MONTH)) AS month)
), fleet_days AS (
  SELECT
    a.product_id,
    m.month_start,
    SUM(DATEDIFF('day', GREATEST(m.month_start, a.delivered_on), m.month_end)) AS asset_days
  FROM core.assets AS a
  JOIN months AS m
    ON a.delivered_on < m.month_end
  GROUP BY ALL
), down_days AS (
  SELECT
    e.product_id,
    m.month_start,
    SUM(
      DATEDIFF(
        'day',
        GREATEST(m.month_start, e.opened_on),
        LEAST(m.month_end, COALESCE(e.closed_on, m.month_end))
      )
    ) AS asset_days_down
  FROM core.maintenance_events AS e
  JOIN months AS m
    ON e.opened_on < m.month_end AND COALESCE(e.closed_on, m.month_end) > m.month_start
  GROUP BY ALL
)
SELECT
  f.product_id,
  f.month_start AS month,
  f.asset_days,
  COALESCE(d.asset_days_down, 0) AS asset_days_down,
  1 - COALESCE(d.asset_days_down, 0) / f.asset_days AS availability
FROM fleet_days AS f
LEFT JOIN down_days AS d
  ON f.product_id = d.product_id AND f.month_start = d.month_start
WHERE f.asset_days > 0
