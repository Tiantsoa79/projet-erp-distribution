const express = require('express');
const { pool } = require('../../database/connection');
const { buildAuditActor, recordAudit } = require('../../utils/audit');

const app = express();
app.use(express.json());

const SALES_SERVICE_PORT = Number(process.env.SALES_SERVICE_PORT || 4001);
const ORDER_STATUSES = ['Draft', 'Submitted', 'Approved', 'Shipped', 'Closed'];
const STATUS_TRANSITIONS = {
  Draft: ['Submitted'],
  Submitted: ['Approved'],
  Approved: ['Shipped'],
  Shipped: ['Closed'],
  Closed: [],
};

function parsePositiveInt(value, fallback) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function toNumberOrNull(value) {
  if (value === undefined || value === null || value === '') return null;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function isIsoDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

async function isClosedAccountingPeriod(client, dateIso) {
  const result = await client.query(
    `
    SELECT period_code
    FROM accounting_periods
    WHERE status = 'closed'
      AND $1::date BETWEEN start_date AND end_date
    LIMIT 1
    `,
    [dateIso]
  );

  return result.rowCount > 0 ? result.rows[0].period_code : null;
}

async function generateNextOrderId(client) {
  const currentYear = new Date().getUTCFullYear();
  const result = await client.query(
    `
    SELECT COALESCE(MAX((regexp_match(order_id, $1))[1]::int), 0) AS max_id
    FROM orders
    WHERE order_id ~ $2
    `,
    [`^[A-Z]{2}-${currentYear}-(\\d+)$`, `^[A-Z]{2}-${currentYear}-\\d+$`]
  );

  const nextId = Number(result.rows[0].max_id) + 1;
  return `OR-${currentYear}-${String(nextId).padStart(6, '0')}`;
}

async function resolveCustomerId(client, customerId, customerName) {
  if (customerId) return customerId;
  if (!customerName) return null;

  const result = await client.query(
    `
    SELECT customer_id
    FROM customers
    WHERE LOWER(customer_name) = LOWER($1)
    ORDER BY customer_id
    `,
    [customerName]
  );

  if (result.rowCount === 0) {
    const error = new Error(`Customer not registered: ${customerName}`);
    error.status = 404;
    error.code = 'CUSTOMER_NOT_FOUND';
    throw error;
  }

  if (result.rowCount > 1) {
    const error = new Error(`Customer name is ambiguous: ${customerName}`);
    error.status = 409;
    error.code = 'CUSTOMER_AMBIGUOUS';
    throw error;
  }

  return result.rows[0].customer_id;
}

async function resolveProductId(client, productId, productName) {
  if (productId) return productId;
  if (!productName) return null;

  const result = await client.query(
    `
    SELECT product_id
    FROM products
    WHERE LOWER(product_name) = LOWER($1)
    ORDER BY product_id
    `,
    [productName]
  );

  if (result.rowCount === 0) {
    const error = new Error(`Product not registered: ${productName}`);
    error.status = 404;
    error.code = 'PRODUCT_NOT_FOUND';
    throw error;
  }

  if (result.rowCount > 1) {
    const error = new Error(`Product name is ambiguous: ${productName}`);
    error.status = 409;
    error.code = 'PRODUCT_AMBIGUOUS';
    throw error;
  }

  return result.rows[0].product_id;
}

function validateLines(lines) {
  const errors = [];

  lines.forEach((line, index) => {
    const prefix = `lines[${index}]`;

    const quantity = toNumberOrNull(line.quantity);
    const discount = toNumberOrNull(line.discount);
    const sales = toNumberOrNull(line.sales);
    const unitPrice = toNumberOrNull(line.unit_price);
    const cost = toNumberOrNull(line.cost);
    const profit = toNumberOrNull(line.profit);

    if (!Number.isInteger(quantity) || quantity <= 0) {
      errors.push(`${prefix}.quantity doit etre un entier > 0`);
    }

    if (discount !== null && (discount < 0 || discount > 1)) {
      errors.push(`${prefix}.discount doit etre entre 0 et 1`);
    }

    if (unitPrice !== null && unitPrice < 0) {
      errors.push(`${prefix}.unit_price doit etre >= 0`);
    }

    if (cost !== null && cost < 0) {
      errors.push(`${prefix}.cost doit etre >= 0`);
    }

    if (sales !== null && sales < 0) {
      errors.push(`${prefix}.sales doit etre >= 0`);
    }

    if (profit !== null && profit < 0) {
      errors.push(`${prefix}.profit doit etre >= 0`);
    }

    if (sales !== null && unitPrice !== null && Number.isInteger(quantity) && quantity > 0) {
      const expectedSales = quantity * unitPrice * (1 - (discount || 0));
      if (Math.abs(sales - expectedSales) > 0.05) {
        errors.push(`${prefix}: incoherence sales (attendu ~ ${expectedSales.toFixed(2)})`);
      }
    }

    if (profit !== null && sales !== null && cost !== null && Number.isInteger(quantity) && quantity > 0) {
      const expectedProfit = sales - cost * quantity;
      if (Math.abs(profit - expectedProfit) > 0.05) {
        errors.push(`${prefix}: incoherence profit (attendu ~ ${expectedProfit.toFixed(2)})`);
      }
    }
  });

  return errors;
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
        o.current_status,
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
    customer_name,
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

  const validationErrors = [];
  if (!customer_id && !customer_name) {
    validationErrors.push('customer_id ou customer_name est requis');
  }
  if (!isIsoDate(order_date)) validationErrors.push('order_date est requis au format YYYY-MM-DD');
  if (!Array.isArray(lines) || lines.length === 0) {
    validationErrors.push('au moins une ligne est requise');
  }

  if (Array.isArray(lines)) {
    lines.forEach((line, index) => {
      if (!line.product_id && !line.product_name) {
        validationErrors.push(`lines[${index}].product_id ou lines[${index}].product_name est requis`);
      }
    });
  }

  if (ship_date && !isIsoDate(ship_date)) {
    validationErrors.push('ship_date doit etre au format YYYY-MM-DD');
  }

  if (isIsoDate(order_date) && ship_date && isIsoDate(ship_date) && ship_date < order_date) {
    validationErrors.push('ship_date doit etre >= order_date');
  }

  const initialStatus = initial_status || 'Draft';
  if (!ORDER_STATUSES.includes(initialStatus)) {
    validationErrors.push(`initial_status invalide. Valeurs autorisees: ${ORDER_STATUSES.join(', ')}`);
  }

  if (Array.isArray(lines) && lines.length > 0) {
    validationErrors.push(...validateLines(lines));
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
    const finalOrderId = order_id || await generateNextOrderId(client);
    const finalCustomerId = await resolveCustomerId(client, customer_id, customer_name);

    const resolvedLines = [];
    for (const line of lines) {
      const finalProductId = await resolveProductId(client, line.product_id, line.product_name);
      resolvedLines.push({ ...line, product_id: finalProductId });
    }

    const closedPeriodCode = await isClosedAccountingPeriod(client, order_date);
    if (closedPeriodCode) {
      return res.status(409).json({
        code: 'PERIOD_CLOSED',
        message: `Modification interdite: periode ${closedPeriodCode} cloturee`,
      });
    }

    await client.query('BEGIN');
    inTransaction = true;

    await client.query(
      `
      INSERT INTO orders (
        order_id, customer_id, order_date, ship_date, current_status, ship_mode,
        country, city, state, postal_code, region
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
      `,
      [
        finalOrderId,
        finalCustomerId,
        order_date,
        ship_date || null,
        initialStatus,
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

    for (const line of resolvedLines) {
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
          finalOrderId,
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
      [finalOrderId, initialStatus, req.headers['x-gateway-user'] || 'API']
    );

    await recordAudit(client, {
      entityType: 'order',
      entityId: finalOrderId,
      action: 'order.create',
      beforeState: null,
      afterState: {
        order_id: finalOrderId,
        customer_id: finalCustomerId,
        order_date,
        ship_date: ship_date || null,
        current_status: initialStatus,
        line_count: lines.length,
      },
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'sales',
    });

    await client.query('COMMIT');
    inTransaction = false;
    return res.status(201).json({
      message: 'Order created',
      order_id: finalOrderId,
      current_status: initialStatus,
    });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return next(error);
  } finally {
    client.release();
  }
});

app.patch('/orders/:orderId', async (req, res, next) => {
  const { orderId } = req.params;
  const {
    customer_id,
    order_date,
    ship_date,
    ship_mode,
    country,
    city,
    state,
    postal_code,
    region,
  } = req.body;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT
        order_id,
        customer_id,
        order_date,
        ship_date,
        current_status,
        ship_mode,
        country,
        city,
        state,
        postal_code,
        region
      FROM orders
      WHERE order_id = $1
      `,
      [orderId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Order not found' });
    }

    const beforeOrder = beforeResult.rows[0];
    const effectiveOrderDate = order_date || beforeOrder.order_date;
    const effectiveShipDate = ship_date === undefined ? beforeOrder.ship_date : ship_date;

    const validationErrors = [];
    if (order_date !== undefined && order_date !== null && !isIsoDate(order_date)) {
      validationErrors.push('order_date doit etre au format YYYY-MM-DD');
    }
    if (ship_date !== undefined && ship_date !== null && ship_date !== '' && !isIsoDate(ship_date)) {
      validationErrors.push('ship_date doit etre au format YYYY-MM-DD');
    }
    if (effectiveOrderDate && effectiveShipDate && isIsoDate(String(effectiveOrderDate)) && isIsoDate(String(effectiveShipDate))) {
      if (String(effectiveShipDate) < String(effectiveOrderDate)) {
        validationErrors.push('ship_date doit etre >= order_date');
      }
    }

    if (validationErrors.length > 0) {
      return res.status(422).json({
        code: 'BUSINESS_VALIDATION_FAILED',
        message: 'Validation metier echouee',
        errors: validationErrors,
      });
    }

    if (!effectiveOrderDate) {
      return res.status(422).json({
        code: 'MISSING_ORDER_DATE',
        message: 'order_date manquant: impossible de verifier la periode comptable',
      });
    }

    const closedPeriodCode = await isClosedAccountingPeriod(client, effectiveOrderDate);
    if (closedPeriodCode) {
      return res.status(409).json({
        code: 'PERIOD_CLOSED',
        message: `Modification interdite: periode ${closedPeriodCode} cloturee`,
      });
    }

    await client.query('BEGIN');
    inTransaction = true;

    const result = await client.query(
      `
      UPDATE orders
      SET customer_id = COALESCE($2, customer_id),
          order_date = COALESCE($3, order_date),
          ship_date = COALESCE($4, ship_date),
          ship_mode = COALESCE($5, ship_mode),
          country = COALESCE($6, country),
          city = COALESCE($7, city),
          state = COALESCE($8, state),
          postal_code = COALESCE($9, postal_code),
          region = COALESCE($10, region),
          updated_at = NOW()
      WHERE order_id = $1
      RETURNING
        order_id,
        customer_id,
        order_date,
        ship_date,
        current_status,
        ship_mode,
        country,
        city,
        state,
        postal_code,
        region,
        updated_at
      `,
      [
        orderId,
        customer_id,
        order_date,
        ship_date,
        ship_mode,
        country,
        city,
        state,
        postal_code,
        region,
      ]
    );

    await recordAudit(client, {
      entityType: 'order',
      entityId: orderId,
      action: 'order.update',
      beforeState: beforeOrder,
      afterState: result.rows[0],
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'sales',
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

app.delete('/orders/:orderId', async (req, res, next) => {
  const { orderId } = req.params;

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const beforeResult = await client.query(
      `
      SELECT
        order_id,
        customer_id,
        order_date,
        ship_date,
        current_status,
        ship_mode,
        country,
        city,
        state,
        postal_code,
        region
      FROM orders
      WHERE order_id = $1
      `,
      [orderId]
    );

    if (beforeResult.rowCount === 0) {
      return res.status(404).json({ message: 'Order not found' });
    }

    const order = beforeResult.rows[0];
    if (!order.order_date) {
      return res.status(422).json({
        code: 'MISSING_ORDER_DATE',
        message: 'order_date manquant: impossible de verifier la periode comptable',
      });
    }

    const closedPeriodCode = await isClosedAccountingPeriod(client, order.order_date);
    if (closedPeriodCode) {
      return res.status(409).json({
        code: 'PERIOD_CLOSED',
        message: `Suppression interdite: periode ${closedPeriodCode} cloturee`,
      });
    }

    await client.query('BEGIN');
    inTransaction = true;

    await client.query('DELETE FROM orders WHERE order_id = $1', [orderId]);

    await recordAudit(client, {
      entityType: 'order',
      entityId: orderId,
      action: 'order.delete',
      beforeState: order,
      afterState: null,
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'sales',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({ message: 'Order deleted', order_id: orderId });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return next(error);
  } finally {
    client.release();
  }
});

app.post('/orders/:orderId/transition', async (req, res, next) => {
  const { orderId } = req.params;
  const { to_status } = req.body;

  if (!ORDER_STATUSES.includes(to_status)) {
    return res.status(422).json({
      code: 'INVALID_STATUS',
      message: `to_status invalide. Valeurs autorisees: ${ORDER_STATUSES.join(', ')}`,
    });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const actor = buildAuditActor(req.headers);
    const orderResult = await client.query(
      'SELECT order_id, order_date, current_status FROM orders WHERE order_id = $1',
      [orderId]
    );

    if (orderResult.rowCount === 0) {
      return res.status(404).json({ message: 'Order not found' });
    }

    const order = orderResult.rows[0];
    const currentStatus = order.current_status || 'Draft';
    const allowedTransitions = STATUS_TRANSITIONS[currentStatus] || [];

    if (!allowedTransitions.includes(to_status)) {
      return res.status(422).json({
        code: 'INVALID_TRANSITION',
        message: `Transition invalide: ${currentStatus} -> ${to_status}`,
        allowed_transitions: allowedTransitions,
      });
    }

    if (!order.order_date) {
      return res.status(422).json({
        code: 'MISSING_ORDER_DATE',
        message: 'order_date manquant: impossible de verifier la periode comptable',
      });
    }

    const closedPeriodCode = await isClosedAccountingPeriod(client, order.order_date);
    if (closedPeriodCode) {
      return res.status(409).json({
        code: 'PERIOD_CLOSED',
        message: `Transition interdite: periode ${closedPeriodCode} cloturee`,
      });
    }

    await client.query('BEGIN');
    inTransaction = true;

    await client.query(
      `
      UPDATE orders
      SET current_status = $2,
          updated_at = NOW()
      WHERE order_id = $1
      `,
      [orderId, to_status]
    );

    await client.query(
      `
      INSERT INTO order_status_history (order_id, status, status_date, updated_by)
      VALUES ($1, $2, NOW(), $3)
      `,
      [orderId, to_status, req.headers['x-gateway-user'] || 'API']
    );

    await recordAudit(client, {
      entityType: 'order',
      entityId: orderId,
      action: 'order.transition',
      beforeState: { current_status: currentStatus },
      afterState: { current_status: to_status },
      actorUserId: actor.actorUserId,
      actorUsername: actor.actorUsername,
      requestId: actor.requestId,
      sourceService: 'sales',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({
      message: 'Order transitioned',
      order_id: orderId,
      from_status: currentStatus,
      to_status,
    });
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
  const status = error.status || (error.code === '23505' || error.code === '23503' ? 409 : 500);
  res.status(status).json({
    message: 'Sales service error',
    detail: error.message,
  });
});

app.listen(SALES_SERVICE_PORT, () => {
  console.log(`Sales service running on port ${SALES_SERVICE_PORT}`);
});
