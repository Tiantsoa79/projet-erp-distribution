const express = require('express');
const { pool } = require('../../database/connection');

const app = express();
app.use(express.json());

const SALES_SERVICE_PORT = Number(process.env.SALES_SERVICE_PORT || 4001);

function parsePositiveInt(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.status(200).json({
      service: 'sales',
      status: 'ok',
      db: 'connected',
    });
  } catch (error) {
    res.status(500).json({
      service: 'sales',
      status: 'error',
      db: 'disconnected',
      message: error.message,
    });
  }
});

app.get('/orders', async (req, res, next) => {
  const limit = parsePositiveInt(req.query.limit, 20);
  const offset = Math.max(Number(req.query.offset) || 0, 0);

  try {
    const query = `
      SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.ship_date,
        o.ship_mode,
        o.region,
        COUNT(ol.row_id)::int AS line_count,
        COALESCE(SUM(ol.sales), 0)::numeric(14,4) AS total_sales,
        COALESCE(SUM(ol.profit), 0)::numeric(14,4) AS total_profit
      FROM orders o
      LEFT JOIN order_lines ol ON ol.order_id = o.order_id
      GROUP BY o.order_id
      ORDER BY o.order_date DESC NULLS LAST, o.order_id DESC
      LIMIT $1 OFFSET $2
    `;

    const result = await pool.query(query, [limit, offset]);
    res.status(200).json({
      items: result.rows,
      pagination: { limit, offset },
    });
  } catch (error) {
    next(error);
  }
});

app.get('/orders/:orderId', async (req, res, next) => {
  const { orderId } = req.params;

  try {
    const orderResult = await pool.query('SELECT * FROM orders WHERE order_id = $1', [orderId]);
    if (orderResult.rowCount === 0) {
      return res.status(404).json({ message: 'Order not found' });
    }

    const [linesResult, statusResult] = await Promise.all([
      pool.query(
        'SELECT row_id, product_id, quantity, discount, sales, unit_price, cost, profit FROM order_lines WHERE order_id = $1 ORDER BY row_id',
        [orderId]
      ),
      pool.query(
        'SELECT status, status_date, updated_by FROM order_status_history WHERE order_id = $1 ORDER BY status_date',
        [orderId]
      ),
    ]);

    return res.status(200).json({
      order: orderResult.rows[0],
      lines: linesResult.rows,
      status_history: statusResult.rows,
    });
  } catch (error) {
    return next(error);
  }
});

app.post('/orders', async (req, res, next) => {
  const {
    order_id,
    customer_id,
    order_date,
    ship_date,
    ship_mode,
    country,
    city,
    state,
    postal_code,
    region,
    lines,
    initial_status,
  } = req.body;

  if (!order_id || !customer_id || !Array.isArray(lines) || lines.length === 0) {
    return res.status(400).json({
      message: 'order_id, customer_id et au moins une ligne sont requis.',
    });
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    await client.query(
      `
      INSERT INTO orders (
        order_id, customer_id, order_date, ship_date, ship_mode,
        country, city, state, postal_code, region
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
      `,
      [
        order_id,
        customer_id,
        order_date || null,
        ship_date || null,
        ship_mode || null,
        country || null,
        city || null,
        state || null,
        postal_code || null,
        region || null,
      ]
    );

    const rowIdSeedResult = await client.query('SELECT COALESCE(MAX(row_id), 0) AS max_id FROM order_lines');
    let nextRowId = Number(rowIdSeedResult.rows[0].max_id) + 1;

    for (const line of lines) {
      const rowId = Number.isInteger(line.row_id) ? line.row_id : nextRowId++;
      await client.query(
        `
        INSERT INTO order_lines (
          row_id, order_id, product_id, quantity, discount,
          sales, unit_price, cost, profit
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        `,
        [
          rowId,
          order_id,
          line.product_id || null,
          line.quantity || null,
          line.discount || null,
          line.sales || null,
          line.unit_price || null,
          line.cost || null,
          line.profit || null,
        ]
      );
    }

    await client.query(
      `
      INSERT INTO order_status_history (order_id, status, status_date, updated_by)
      VALUES ($1, $2, NOW(), $3)
      `,
      [order_id, initial_status || 'Pending', 'API']
    );

    await client.query('COMMIT');
    return res.status(201).json({ message: 'Order created', order_id });
  } catch (error) {
    await client.query('ROLLBACK');
    return next(error);
  } finally {
    client.release();
  }
});

app.use((error, _req, res, _next) => {
  const status = error.code === '23505' ? 409 : 500;
  res.status(status).json({
    message: 'Sales service error',
    detail: error.message,
  });
});

app.listen(SALES_SERVICE_PORT, () => {
  console.log(`Sales service running on port ${SALES_SERVICE_PORT}`);
});
