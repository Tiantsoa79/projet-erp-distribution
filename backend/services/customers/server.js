const express = require('express');
const { pool } = require('../../database/connection');

const app = express();
app.use(express.json());

const CUSTOMERS_SERVICE_PORT = Number(process.env.CUSTOMERS_SERVICE_PORT || 4003);

function parsePositiveInt(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.status(200).json({ service: 'customers', status: 'ok', db: 'connected' });
  } catch (error) {
    res.status(500).json({ service: 'customers', status: 'error', db: 'disconnected', message: error.message });
  }
});

app.get('/customers', async (req, res, next) => {
  const limit = parsePositiveInt(req.query.limit, 20);
  const offset = Math.max(Number(req.query.offset) || 0, 0);
  const segment = req.query.segment || null;

  try {
    const result = await pool.query(
      `
      SELECT customer_id, customer_name, segment, city, state, region, email,
             total_sales, total_profit, total_orders, average_order_value
      FROM customers
      WHERE ($1::text IS NULL OR segment = $1)
      ORDER BY customer_id
      LIMIT $2 OFFSET $3
      `,
      [segment, limit, offset]
    );

    res.status(200).json({ items: result.rows, pagination: { limit, offset }, filters: { segment } });
  } catch (error) {
    next(error);
  }
});

app.get('/customers/:customerId', async (req, res, next) => {
  const { customerId } = req.params;
  try {
    const result = await pool.query('SELECT * FROM customers WHERE customer_id = $1', [customerId]);
    if (result.rowCount === 0) return res.status(404).json({ message: 'Customer not found' });
    res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

app.post('/customers', async (req, res, next) => {
  const { customer_id, customer_name, segment, city, state, region, email } = req.body;

  if (!customer_id || !customer_name) {
    return res.status(400).json({ message: 'customer_id et customer_name sont requis.' });
  }

  try {
    const result = await pool.query(
      `
      INSERT INTO customers (customer_id, customer_name, segment, city, state, region, email)
      VALUES ($1,$2,$3,$4,$5,$6,$7)
      RETURNING customer_id, customer_name, segment, city, state, region, email, created_at
      `,
      [customer_id, customer_name, segment || null, city || null, state || null, region || null, email || null]
    );

    res.status(201).json({ item: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

app.patch('/customers/:customerId', async (req, res, next) => {
  const { customerId } = req.params;
  const { customer_name, segment, city, state, region, email } = req.body;

  try {
    const result = await pool.query(
      `
      UPDATE customers
      SET customer_name = COALESCE($2, customer_name),
          segment = COALESCE($3, segment),
          city = COALESCE($4, city),
          state = COALESCE($5, state),
          region = COALESCE($6, region),
          email = COALESCE($7, email),
          updated_at = NOW()
      WHERE customer_id = $1
      RETURNING customer_id, customer_name, segment, city, state, region, email, updated_at
      `,
      [customerId, customer_name, segment, city, state, region, email]
    );

    if (result.rowCount === 0) return res.status(404).json({ message: 'Customer not found' });
    res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

app.use((error, _req, res, _next) => {
  const status = error.code === '23505' ? 409 : 500;
  res.status(status).json({ message: 'Customers service error', detail: error.message });
});

app.listen(CUSTOMERS_SERVICE_PORT, () => {
  console.log(`Customers service running on port ${CUSTOMERS_SERVICE_PORT}`);
});
