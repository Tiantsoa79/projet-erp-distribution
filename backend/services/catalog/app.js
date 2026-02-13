const express = require('express');
const { pool } = require('../../database/connection');
const { buildAuditActor, recordAudit } = require('../../utils/audit');
const { sendServiceError } = require('../../utils/service-http');

const app = express();
app.use(express.json());

async function generateNextProductId(client) {
  const result = await client.query(
    `
    SELECT COALESCE(MAX((regexp_match(product_id, '^[A-Z]{3}-[A-Z]{2}-(\\d+)$'))[1]::int), 0) AS max_id
    FROM products
    WHERE product_id ~ '^[A-Z]{3}-[A-Z]{2}-\\d+$'
    `
  );

  const nextId = Number(result.rows[0].max_id) + 1;
  return `PRD-AU-${String(nextId).padStart(8, '0')}`;
}

async function resolveSupplierId(client, supplierId, supplierName) {
  if (supplierId) return supplierId;
  if (!supplierName) return null;

  const supplierResult = await client.query(
    `
    SELECT supplier_id
    FROM suppliers
    WHERE LOWER(supplier_name) = LOWER($1)
    ORDER BY supplier_id
    `,
    [supplierName]
  );

  if (supplierResult.rowCount === 0) {
    const error = new Error(`Supplier not registered: ${supplierName}`);
    error.status = 404;
    error.code = 'SUPPLIER_NOT_FOUND';
    throw error;
  }

  if (supplierResult.rowCount > 1) {
    const error = new Error(`Supplier name is ambiguous: ${supplierName}`);
    error.status = 409;
    error.code = 'SUPPLIER_AMBIGUOUS';
    throw error;
  }

  return supplierResult.rows[0].supplier_id;
}

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

app.post('/products', async (req, res, next) => {
  const {
    product_id,
    product_name,
    category,
    sub_category,
    unit_cost,
    unit_price,
    stock_quantity,
    reorder_level,
    reorder_quantity,
    warehouse_location,
    supplier_id,
    supplier_name,
  } = req.body;

  if (!product_name) {
    return res.status(400).json({ message: 'product_name est requis.' });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const finalProductId = product_id || await generateNextProductId(client);
    const finalSupplierId = await resolveSupplierId(client, supplier_id, supplier_name);

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
      `
      INSERT INTO products (
        product_id, product_name, category, sub_category, unit_cost, unit_price,
        stock_quantity, reorder_level, reorder_quantity, warehouse_location, supplier_id
      )
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
      RETURNING product_id, product_name, category, sub_category, unit_cost, unit_price,
                stock_quantity, reorder_level, reorder_quantity, warehouse_location, supplier_id, created_at
      `,
      [
        finalProductId,
        product_name,
        category || null,
        sub_category || null,
        unit_cost ?? null,
        unit_price ?? null,
        stock_quantity ?? null,
        reorder_level ?? null,
        reorder_quantity ?? null,
        warehouse_location || null,
        finalSupplierId,
      ]
    );

    await recordAudit(client, {
      entityType: 'product',
      entityId: finalProductId,
      action: 'product.create',
      beforeState: null,
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'catalog',
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

app.patch('/products/:productId', async (req, res, next) => {
  const { productId } = req.params;
  const {
    product_name,
    category,
    sub_category,
    unit_cost,
    unit_price,
    stock_quantity,
    reorder_level,
    reorder_quantity,
    warehouse_location,
    supplier_id,
    supplier_name,
  } = req.body;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const finalSupplierId = await resolveSupplierId(client, supplier_id, supplier_name);
    const beforeResult = await client.query(
      `
      SELECT product_id, product_name, category, sub_category, unit_cost, unit_price,
             stock_quantity, reorder_level, reorder_quantity, warehouse_location, supplier_id
      FROM products
      WHERE product_id = $1
      `,
      [productId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Product not found' });
    }

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
      `
      UPDATE products
      SET product_name = COALESCE($2, product_name),
          category = COALESCE($3, category),
          sub_category = COALESCE($4, sub_category),
          unit_cost = COALESCE($5, unit_cost),
          unit_price = COALESCE($6, unit_price),
          stock_quantity = COALESCE($7, stock_quantity),
          reorder_level = COALESCE($8, reorder_level),
          reorder_quantity = COALESCE($9, reorder_quantity),
          warehouse_location = COALESCE($10, warehouse_location),
          supplier_id = COALESCE($11, supplier_id),
          updated_at = NOW()
      WHERE product_id = $1
      RETURNING product_id, product_name, category, sub_category, unit_cost, unit_price,
                stock_quantity, reorder_level, reorder_quantity, warehouse_location, supplier_id, updated_at
      `,
      [
        productId,
        product_name,
        category,
        sub_category,
        unit_cost,
        unit_price,
        stock_quantity,
        reorder_level,
        reorder_quantity,
        warehouse_location,
        finalSupplierId,
      ]
    );

    await recordAudit(client, {
      entityType: 'product',
      entityId: productId,
      action: 'product.update',
      beforeState: beforeResult.rows[0],
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'catalog',
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

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT product_id, product_name, stock_quantity
      FROM products
      WHERE product_id = $1
      `,
      [productId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Product not found' });
    }

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
      `
      UPDATE products
      SET stock_quantity = $2,
          updated_at = NOW()
      WHERE product_id = $1
      RETURNING product_id, product_name, stock_quantity, updated_at
      `,
      [productId, stock_quantity]
    );

    await recordAudit(client, {
      entityType: 'product',
      entityId: productId,
      action: 'product.stock.update',
      beforeState: beforeResult.rows[0],
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'catalog',
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

app.delete('/products/:productId', async (req, res, next) => {
  const { productId } = req.params;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT product_id, product_name, category, sub_category, unit_cost, unit_price,
             stock_quantity, reorder_level, reorder_quantity, warehouse_location, supplier_id
      FROM products
      WHERE product_id = $1
      `,
      [productId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Product not found' });
    }

    await client.query('BEGIN');
    inTransaction = true;

    await client.query('DELETE FROM products WHERE product_id = $1', [productId]);

    await recordAudit(client, {
      entityType: 'product',
      entityId: productId,
      action: 'product.delete',
      beforeState: beforeResult.rows[0],
      afterState: null,
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'catalog',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({ message: 'Product deleted', product_id: productId });
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
  sendServiceError(res, 'Catalog', error);
});

module.exports = app;
