const { Router } = require('express');
const pool = require('../db');

const router = Router();

// =========================================================================
// Strategic dashboard
// =========================================================================

router.get('/strategic', async (req, res) => {
  try {
    const [kpis, monthly, segments, geo, products] = await Promise.all([
      pool.query(`
        WITH date_range AS (
          SELECT MAX(dd.full_date) AS max_date
          FROM dwh.dim_date dd
          WHERE EXISTS (SELECT 1 FROM dwh.fact_sales_order_line f WHERE f.order_date_key = dd.date_key)
        ),
        current_month AS (
          SELECT SUM(f.sales_amount) AS ca, COUNT(DISTINCT f.order_id) AS orders,
                 COUNT(DISTINCT f.customer_key) AS customers, AVG(f.sales_amount) AS avg_order
          FROM dwh.fact_sales_order_line f
          JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
          CROSS JOIN date_range dr
          WHERE dd.full_date >= date_trunc('month', dr.max_date)
        ),
        previous_month AS (
          SELECT SUM(f.sales_amount) AS ca, COUNT(DISTINCT f.order_id) AS orders,
                 COUNT(DISTINCT f.customer_key) AS customers, AVG(f.sales_amount) AS avg_order
          FROM dwh.fact_sales_order_line f
          JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
          CROSS JOIN date_range dr
          WHERE dd.full_date >= date_trunc('month', dr.max_date) - INTERVAL '1 month'
            AND dd.full_date < date_trunc('month', dr.max_date)
        )
        SELECT cm.ca AS ca_cur, cm.orders AS ord_cur, cm.customers AS cli_cur, cm.avg_order AS avg_cur,
               pm.ca AS ca_prev, pm.orders AS ord_prev, pm.customers AS cli_prev, pm.avg_order AS avg_prev
        FROM current_month cm, previous_month pm
      `),
      pool.query(`
        SELECT dd.year_number, dd.month_number, dd.month_name,
               SUM(f.sales_amount) AS ca, COUNT(DISTINCT f.order_id) AS orders,
               SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
        GROUP BY dd.year_number, dd.month_number, dd.month_name
        ORDER BY dd.year_number, dd.month_number
      `),
      pool.query(`
        SELECT dc.segment, COUNT(DISTINCT dc.customer_key) AS nb_clients,
               SUM(f.sales_amount) AS ca, SUM(f.profit_amount) AS profit,
               COUNT(DISTINCT f.order_id) AS orders
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_customer dc ON f.customer_key = dc.customer_key AND dc.is_current = TRUE
        WHERE dc.segment IS NOT NULL
        GROUP BY dc.segment ORDER BY ca DESC
      `),
      pool.query(`
        SELECT dg.region, SUM(f.sales_amount) AS ca,
               COUNT(DISTINCT f.order_id) AS orders, SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_geography dg ON f.geography_key = dg.geography_key
        WHERE dg.region IS NOT NULL
        GROUP BY dg.region ORDER BY ca DESC LIMIT 10
      `),
      pool.query(`
        SELECT dp.product_name, dp.category,
               SUM(f.sales_amount) AS ca, SUM(f.quantity) AS qty, SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_product dp ON f.product_key = dp.product_key AND dp.is_current = TRUE
        GROUP BY dp.product_name, dp.category ORDER BY ca DESC LIMIT 10
      `),
    ]);

    res.json({
      kpis: kpis.rows[0] || {},
      monthly: monthly.rows,
      segments: segments.rows,
      geo: geo.rows,
      products: products.rows,
    });
  } catch (err) {
    console.error('[dashboard/strategic]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// =========================================================================
// Tactical dashboard
// =========================================================================

router.get('/tactical', async (req, res) => {
  try {
    const [daily, categories, status, shipModes] = await Promise.all([
      pool.query(`
        SELECT dd.full_date, SUM(f.sales_amount) AS ca, COUNT(DISTINCT f.order_id) AS orders,
               COUNT(DISTINCT f.customer_key) AS clients, SUM(f.profit_amount) AS profit
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
        GROUP BY dd.full_date ORDER BY dd.full_date
      `),
      pool.query(`
        SELECT dp.category, COUNT(DISTINCT f.order_id) AS orders,
               SUM(f.sales_amount) AS ca, SUM(f.quantity) AS qty,
               SUM(f.profit_amount) AS profit,
               CASE WHEN SUM(f.sales_amount) > 0
                    THEN ROUND(SUM(f.profit_amount) / SUM(f.sales_amount) * 100, 1)
                    ELSE 0 END AS margin_pct
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_product dp ON f.product_key = dp.product_key AND dp.is_current = TRUE
        WHERE dp.category IS NOT NULL
        GROUP BY dp.category ORDER BY ca DESC
      `),
      pool.query(`
        SELECT dos.status_code AS status, COUNT(DISTINCT ft.order_id) AS orders
        FROM dwh.fact_order_status_transition ft
        JOIN dwh.dim_order_status dos ON ft.status_key = dos.status_key
        GROUP BY dos.status_code ORDER BY orders DESC
      `),
      pool.query(`
        SELECT sm.ship_mode_code AS mode, COUNT(DISTINCT f.order_id) AS orders,
               SUM(f.sales_amount) AS ca, AVG(f.sales_amount) AS avg_order
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_ship_mode sm ON f.ship_mode_key = sm.ship_mode_key
        GROUP BY sm.ship_mode_code ORDER BY ca DESC
      `),
    ]);

    res.json({
      daily: daily.rows,
      categories: categories.rows,
      status: status.rows,
      shipModes: shipModes.rows,
    });
  } catch (err) {
    console.error('[dashboard/tactical]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// =========================================================================
// Operational dashboard
// =========================================================================

router.get('/operational', async (req, res) => {
  try {
    const [orders, stock, transitions, geo] = await Promise.all([
      pool.query(`
        SELECT f.order_id, dc.customer_name, dg.city, dg.region,
               dos.status_code AS status, sm.ship_mode_code AS ship_mode,
               dd.full_date AS order_date, SUM(f.sales_amount) AS total
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_customer dc ON f.customer_key = dc.customer_key AND dc.is_current = TRUE
        JOIN dwh.dim_geography dg ON f.geography_key = dg.geography_key
        JOIN dwh.dim_order_status dos ON f.status_key = dos.status_key
        JOIN dwh.dim_ship_mode sm ON f.ship_mode_key = sm.ship_mode_key
        JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
        GROUP BY f.order_id, dc.customer_name, dg.city, dg.region,
                 dos.status_code, sm.ship_mode_code, dd.full_date
        ORDER BY dd.full_date DESC LIMIT 50
      `),
      pool.query(`
        SELECT dp.product_name, dp.category, ds.supplier_name,
               fi.quantity_on_hand, fi.stock_value
        FROM dwh.fact_inventory_snapshot fi
        JOIN dwh.dim_product dp ON fi.product_key = dp.product_key AND dp.is_current = TRUE
        JOIN dwh.dim_supplier ds ON fi.supplier_key = ds.supplier_key AND ds.is_current = TRUE
        JOIN dwh.dim_date dd ON fi.snapshot_date_key = dd.date_key
        WHERE dd.full_date = (SELECT MAX(d2.full_date) FROM dwh.dim_date d2
                              WHERE EXISTS (SELECT 1 FROM dwh.fact_inventory_snapshot f2 WHERE f2.snapshot_date_key = d2.date_key))
        ORDER BY fi.quantity_on_hand ASC LIMIT 20
      `),
      pool.query(`
        SELECT dos.status_code AS status, COUNT(*) AS transitions
        FROM dwh.fact_order_status_transition ft
        JOIN dwh.dim_order_status dos ON ft.status_key = dos.status_key
        GROUP BY dos.status_code ORDER BY transitions DESC
      `),
      pool.query(`
        SELECT dg.region, COUNT(DISTINCT f.order_id) AS orders, SUM(f.sales_amount) AS ca
        FROM dwh.fact_sales_order_line f
        JOIN dwh.dim_geography dg ON f.geography_key = dg.geography_key
        JOIN dwh.dim_date dd ON f.order_date_key = dd.date_key
        WHERE dd.full_date >= (SELECT MAX(full_date) - 30 FROM dwh.dim_date
                               WHERE EXISTS (SELECT 1 FROM dwh.fact_sales_order_line f2 WHERE f2.order_date_key = date_key))
        GROUP BY dg.region ORDER BY orders DESC LIMIT 10
      `),
    ]);

    res.json({
      orders: orders.rows,
      stock: stock.rows,
      transitions: transitions.rows,
      geo: geo.rows,
    });
  } catch (err) {
    console.error('[dashboard/operational]', err.message);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
