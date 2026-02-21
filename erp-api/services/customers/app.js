const express = require('express');
const { pool } = require('../../database/connection');
const { buildAuditActor, recordAudit } = require('../../utils/audit');
const { sendServiceError } = require('../../utils/service-http');

const app = express();
app.use(express.json());

async function generateNextCustomerId(client) {
  const result = await client.query(
    `
    SELECT COALESCE(MAX((regexp_match(customer_id, '^[A-Z]{2}-(\\d+)$'))[1]::int), 0) AS max_id
    FROM customers
    WHERE customer_id ~ '^[A-Z]{2}-\\d+$'
    `
  );

  const nextId = Number(result.rows[0].max_id) + 1;
  return `CU-${String(nextId).padStart(5, '0')}`;
}

function parsePositiveInt(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function normalizeNullableString(value) {
  if (value === undefined || value === null) return null;
  const normalized = String(value).trim();
  return normalized === '' ? null : normalized;
}

function isValidEmail(value) {
  return typeof value === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
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

  const normalizedName = normalizeNullableString(customer_name);
  const normalizedEmail = normalizeNullableString(email);

  const validationErrors = [];
  if (!normalizedName) {
    validationErrors.push('customer_name est requis.');
  }
  if (normalizedEmail && !isValidEmail(normalizedEmail)) {
    validationErrors.push('email invalide.');
  }

  if (validationErrors.length > 0) {
    return res.status(422).json({
      code: 'BUSINESS_VALIDATION_FAILED',
      message: 'Validation metier echouee',
      errors: validationErrors,
    });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const finalCustomerId = customer_id || await generateNextCustomerId(client);

    const duplicateResult = await client.query(
      `
      SELECT customer_id
      FROM customers
      WHERE LOWER(customer_name) = LOWER($1)
        AND COALESCE(LOWER(email), '') = COALESCE(LOWER($2), '')
      LIMIT 1
      `,
      [normalizedName, normalizedEmail]
    );

    if (duplicateResult.rowCount > 0) {
      return res.status(409).json({
        code: 'CUSTOMER_DUPLICATE',
        message: 'Un client avec le meme nom et email existe deja.',
        customer_id: duplicateResult.rows[0].customer_id,
      });
    }

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
      `
      INSERT INTO customers (customer_id, customer_name, segment, city, state, region, email)
      VALUES ($1,$2,$3,$4,$5,$6,$7)
      RETURNING customer_id, customer_name, segment, city, state, region, email, created_at
      `,
      [
        finalCustomerId,
        normalizedName,
        normalizeNullableString(segment),
        normalizeNullableString(city),
        normalizeNullableString(state),
        normalizeNullableString(region),
        normalizedEmail,
      ]
    );

    await recordAudit(client, {
      entityType: 'customer',
      entityId: finalCustomerId,
      action: 'customer.create',
      beforeState: null,
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'customers',
    });

    await client.query('COMMIT');
    inTransaction = false;

    res.status(201).json({ item: result.rows[0] });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    next(error);
  } finally {
    client.release();
  }
});

app.patch('/customers/:customerId', async (req, res, next) => {
  const { customerId } = req.params;
  const { customer_name, segment, city, state, region, email } = req.body;

  const normalizedName = normalizeNullableString(customer_name);
  const normalizedEmail = normalizeNullableString(email);
  if (normalizedEmail && !isValidEmail(normalizedEmail)) {
    return res.status(422).json({
      code: 'BUSINESS_VALIDATION_FAILED',
      message: 'Validation metier echouee',
      errors: ['email invalide.'],
    });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT customer_id, customer_name, segment, city, state, region, email
      FROM customers
      WHERE customer_id = $1
      `,
      [customerId]
    );

    if (beforeResult.rowCount === 0) return res.status(404).json({ message: 'Customer not found' });

    const effectiveName = normalizedName || beforeResult.rows[0].customer_name;
    const effectiveEmail = normalizedEmail === null
      ? beforeResult.rows[0].email
      : normalizedEmail;

    const duplicateResult = await client.query(
      `
      SELECT customer_id
      FROM customers
      WHERE customer_id <> $1
        AND LOWER(customer_name) = LOWER($2)
        AND COALESCE(LOWER(email), '') = COALESCE(LOWER($3), '')
      LIMIT 1
      `,
      [customerId, effectiveName, effectiveEmail]
    );

    if (duplicateResult.rowCount > 0) {
      return res.status(409).json({
        code: 'CUSTOMER_DUPLICATE',
        message: 'Un client avec le meme nom et email existe deja.',
        customer_id: duplicateResult.rows[0].customer_id,
      });
    }

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
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
      [
        customerId,
        normalizedName,
        normalizeNullableString(segment),
        normalizeNullableString(city),
        normalizeNullableString(state),
        normalizeNullableString(region),
        normalizedEmail,
      ]
    );

    await recordAudit(client, {
      entityType: 'customer',
      entityId: customerId,
      action: 'customer.update',
      beforeState: beforeResult.rows[0],
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'customers',
    });

    await client.query('COMMIT');
    inTransaction = false;

    res.status(200).json({ item: result.rows[0] });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    next(error);
  } finally {
    client.release();
  }
});

app.delete('/customers/:customerId', async (req, res, next) => {
  const { customerId } = req.params;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT customer_id, customer_name, segment, city, state, region, email
      FROM customers
      WHERE customer_id = $1
      `,
      [customerId]
    );

    if (beforeResult.rowCount === 0) return res.status(404).json({ message: 'Customer not found' });

    await client.query('BEGIN');
    inTransaction = true;

    await client.query('DELETE FROM customers WHERE customer_id = $1', [customerId]);

    await recordAudit(client, {
      entityType: 'customer',
      entityId: customerId,
      action: 'customer.delete',
      beforeState: beforeResult.rows[0],
      afterState: null,
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'customers',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({ message: 'Customer deleted', customer_id: customerId });
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
  sendServiceError(res, 'Customers', error);
});

module.exports = app;
