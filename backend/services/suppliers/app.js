const express = require('express');
const { pool } = require('../../database/connection');
const { buildAuditActor, recordAudit } = require('../../utils/audit');
const { sendServiceError } = require('../../utils/service-http');

const app = express();
app.use(express.json());

async function generateNextSupplierId(client) {
  const result = await client.query(
    `
    SELECT COALESCE(MAX((regexp_match(supplier_id, '^SUP-(\\d+)$'))[1]::int), 0) AS max_id
    FROM suppliers
    WHERE supplier_id ~ '^SUP-\\d+$'
    `
  );

  const nextId = Number(result.rows[0].max_id) + 1;
  return `SUP-${String(nextId).padStart(3, '0')}`;
}

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

app.post('/suppliers', async (req, res, next) => {
  const {
    supplier_id,
    supplier_name,
    country,
    contact_email,
    contact_phone,
    rating,
    lead_time_days,
    payment_terms,
    active,
  } = req.body;

  if (!supplier_name) {
    return res.status(400).json({ message: 'supplier_name est requis.' });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const finalSupplierId = supplier_id || await generateNextSupplierId(client);

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
      `
      INSERT INTO suppliers (
        supplier_id, supplier_name, country, contact_email,
        contact_phone, rating, lead_time_days, payment_terms, active
      )
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
      RETURNING supplier_id, supplier_name, country, contact_email, contact_phone,
                rating, lead_time_days, payment_terms, active, created_at
      `,
      [
        finalSupplierId,
        supplier_name,
        country || null,
        contact_email || null,
        contact_phone || null,
        rating ?? null,
        lead_time_days ?? null,
        payment_terms || null,
        active ?? true,
      ]
    );

    await recordAudit(client, {
      entityType: 'supplier',
      entityId: finalSupplierId,
      action: 'supplier.create',
      beforeState: null,
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'suppliers',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(201).json({ item: result.rows[0] });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return next(error);
  } finally {
    client.release();
  }
});

app.patch('/suppliers/:supplierId', async (req, res, next) => {
  const { supplierId } = req.params;
  const { supplier_name, country, contact_email, contact_phone, rating, lead_time_days, payment_terms, active } = req.body;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT supplier_id, supplier_name, country, contact_email, contact_phone,
             rating, lead_time_days, payment_terms, active
      FROM suppliers
      WHERE supplier_id = $1
      `,
      [supplierId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Supplier not found' });
    }

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
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

    await recordAudit(client, {
      entityType: 'supplier',
      entityId: supplierId,
      action: 'supplier.update',
      beforeState: beforeResult.rows[0],
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'suppliers',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return next(error);
  } finally {
    client.release();
  }
});

app.delete('/suppliers/:supplierId', async (req, res, next) => {
  const { supplierId } = req.params;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT supplier_id, supplier_name, country, contact_email, contact_phone,
             rating, lead_time_days, payment_terms, active
      FROM suppliers
      WHERE supplier_id = $1
      `,
      [supplierId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Supplier not found' });
    }

    await client.query('BEGIN');
    inTransaction = true;

    await client.query('DELETE FROM suppliers WHERE supplier_id = $1', [supplierId]);

    await recordAudit(client, {
      entityType: 'supplier',
      entityId: supplierId,
      action: 'supplier.delete',
      beforeState: beforeResult.rows[0],
      afterState: null,
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'suppliers',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({ message: 'Supplier deleted', supplier_id: supplierId });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return next(error);
  } finally {
    client.release();
  }
});

app.use((error, _req, res, _next) => {
  sendServiceError(res, 'Supplier', error);
});

module.exports = app;
