const express = require('express');
const { pool } = require('../../database/connection');

const app = express();
app.use(express.json());

const CATALOG_SERVICE_PORT = Number(process.env.CATALOG_SERVICE_PORT || 4002);

function parsePositiveInt(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.status(200).json({
      service: 'catalog',
      status: 'ok',
      db: 'connected',
    });
  } catch (error) {
    res.status(500).json({
      service: 'catalog',
      status: 'error',
      db: 'disconnected',
      message: error.message,
    });
  }
});

app.get('/products', async (req, res, next) => {
  const limit = parsePositiveInt(req.query.limit, 20);
  const offset = Math.max(Number(req.query.offset) || 0, 0);
  const category = req.query.category || null;

  try {
    const query = `
      SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.sub_category,
        p.unit_cost,
        p.unit_price,
        p.stock_quantity,
        p.reorder_level,
        p.reorder_quantity,
        p.warehouse_location,
        p.supplier_id,
        s.supplier_name
      FROM products p
      LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id
      WHERE ($1::text IS NULL OR p.category = $1)
      ORDER BY p.product_id
      LIMIT $2 OFFSET $3
    `;

    const result = await pool.query(query, [category, limit, offset]);
    res.status(200).json({
      items: result.rows,
      pagination: { limit, offset },
      filters: { category },
    });
  } catch (error) {
    next(error);
  }
});

app.get('/products/:productId', async (req, res, next) => {
  const { productId } = req.params;

  try {
    const result = await pool.query(
      `
      SELECT
        p.*,
        s.supplier_name,
        s.country AS supplier_country,
        s.rating AS supplier_rating
      FROM products p
      LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id
      WHERE p.product_id = $1
      `,
      [productId]
    );

    if (result.rowCount === 0) {
      return res.status(404).json({ message: 'Product not found' });
    }

    return res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    return next(error);
  }
});

app.patch('/products/:productId/stock', async (req, res, next) => {
  const { productId } = req.params;
  const { stock_quantity } = req.body;

  if (!Number.isInteger(stock_quantity) || stock_quantity < 0) {
    return res.status(400).json({
      message: 'stock_quantity doit etre un entier >= 0.',
    });
  }

  try {
    const result = await pool.query(
      `
      UPDATE products
      SET stock_quantity = $2,
          updated_at = NOW()
      WHERE product_id = $1
      RETURNING product_id, product_name, stock_quantity, updated_at
      `,
      [productId, stock_quantity]
    );

    if (result.rowCount === 0) {
      return res.status(404).json({ message: 'Product not found' });
    }

    return res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    return next(error);
  }
});

app.use((error, _req, res, _next) => {
  res.status(500).json({
    message: 'Catalog service error',
    detail: error.message,
  });
});

app.listen(CATALOG_SERVICE_PORT, () => {
  console.log(`Catalog service running on port ${CATALOG_SERVICE_PORT}`);
});
