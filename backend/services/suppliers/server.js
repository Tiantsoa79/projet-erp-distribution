const express = require('express');
const { pool } = require('../../database/connection');

const app = express();
app.use(express.json());

const SUPPLIERS_SERVICE_PORT = Number(
  process.env.SUPPLIERS_SERVICE_PORT || process.env.SUPPLIER_SERVICE_PORT || 4004
);

app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.status(200).json({ service: 'supplier', status: 'ok', db: 'connected' });
  } catch (error) {
    res.status(500).json({ service: 'supplier', status: 'error', db: 'disconnected', message: error.message });
  }
});

app.get('/suppliers', async (_req, res, next) => {
  try {
    const result = await pool.query(
      `
      SELECT supplier_id, supplier_name, country, contact_email, contact_phone,
             rating, lead_time_days, payment_terms, active
      FROM suppliers
      ORDER BY supplier_name
      `
    );

    res.status(200).json({ items: result.rows });
  } catch (error) {
    next(error);
  }
});

app.get('/suppliers/:supplierId', async (req, res, next) => {
  const { supplierId } = req.params;

  try {
    const supplierResult = await pool.query('SELECT * FROM suppliers WHERE supplier_id = $1', [supplierId]);
    if (supplierResult.rowCount === 0) {
      return res.status(404).json({ message: 'Supplier not found' });
    }

    const productsResult = await pool.query(
      `
      SELECT product_id, product_name, category, sub_category, stock_quantity, unit_cost, unit_price
      FROM products
      WHERE supplier_id = $1
      ORDER BY product_name
      `,
      [supplierId]
    );

    return res.status(200).json({ supplier: supplierResult.rows[0], products: productsResult.rows });
  } catch (error) {
    return next(error);
  }
});

app.patch('/suppliers/:supplierId', async (req, res, next) => {
  const { supplierId } = req.params;
  const { supplier_name, country, contact_email, contact_phone, rating, lead_time_days, payment_terms, active } = req.body;

  try {
    const result = await pool.query(
      `
      UPDATE suppliers
      SET supplier_name = COALESCE($2, supplier_name),
          country = COALESCE($3, country),
          contact_email = COALESCE($4, contact_email),
          contact_phone = COALESCE($5, contact_phone),
          rating = COALESCE($6, rating),
          lead_time_days = COALESCE($7, lead_time_days),
          payment_terms = COALESCE($8, payment_terms),
          active = COALESCE($9, active),
          updated_at = NOW()
      WHERE supplier_id = $1
      RETURNING supplier_id, supplier_name, country, contact_email, contact_phone, rating, lead_time_days, payment_terms, active, updated_at
      `,
      [supplierId, supplier_name, country, contact_email, contact_phone, rating, lead_time_days, payment_terms, active]
    );

    if (result.rowCount === 0) {
      return res.status(404).json({ message: 'Supplier not found' });
    }

    return res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    return next(error);
  }
});

app.use((error, _req, res, _next) => {
  res.status(500).json({ message: 'Supplier service error', detail: error.message });
});

app.listen(SUPPLIERS_SERVICE_PORT, () => {
  console.log(`Suppliers service running on port ${SUPPLIERS_SERVICE_PORT}`);
});
