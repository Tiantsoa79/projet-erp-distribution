const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse');
const { Client } = require('pg');
require('dotenv').config();

const backendDir = path.resolve(__dirname, '..');
const schemaPath = path.join(backendDir, 'database', 'schema.sql');
const dataDir = process.env.CSV_DATA_DIR
  ? path.resolve(backendDir, process.env.CSV_DATA_DIR)
  : path.resolve(backendDir, '..', 'data');

function quoteIdentifier(identifier) {
  return `"${String(identifier).replace(/"/g, '""')}"`;
}

async function ensureDatabaseExists() {
  const targetDatabase = process.env.PGDATABASE;
  if (!targetDatabase) {
    throw new Error('PGDATABASE est requis dans le fichier .env');
  }

  const adminClient = new Client({
    host: process.env.PGHOST,
    port: Number(process.env.PGPORT || 5432),
    database: process.env.PGADMINDB || 'postgres',
    user: process.env.PGUSER,
    password: process.env.PGPASSWORD,
  });

  await adminClient.connect();
  try {
    const existsResult = await adminClient.query(
      'SELECT 1 FROM pg_database WHERE datname = $1',
      [targetDatabase]
    );

    if (existsResult.rowCount === 0) {
      await adminClient.query(`CREATE DATABASE ${quoteIdentifier(targetDatabase)}`);
      console.log(`Base ${targetDatabase} creee automatiquement.`);
    }
  } finally {
    await adminClient.end();
  }
}

async function isInitialImportAlreadyDone(client) {
  const tablesResult = await client.query(`
    SELECT
      to_regclass('public.customers') IS NOT NULL AS customers,
      to_regclass('public.suppliers') IS NOT NULL AS suppliers,
      to_regclass('public.products') IS NOT NULL AS products,
      to_regclass('public.orders') IS NOT NULL AS orders,
      to_regclass('public.order_lines') IS NOT NULL AS order_lines,
      to_regclass('public.order_status_history') IS NOT NULL AS order_status_history
  `);

  const tables = tablesResult.rows[0];
  const allTablesExist =
    tables.customers &&
    tables.suppliers &&
    tables.products &&
    tables.orders &&
    tables.order_lines &&
    tables.order_status_history;

  if (!allTablesExist) {
    return false;
  }

  const countsResult = await client.query(`
    SELECT
      (SELECT COUNT(*) FROM customers) AS customers_count,
      (SELECT COUNT(*) FROM suppliers) AS suppliers_count,
      (SELECT COUNT(*) FROM products) AS products_count,
      (SELECT COUNT(*) FROM orders) AS orders_count,
      (SELECT COUNT(*) FROM order_lines) AS order_lines_count,
      (SELECT COUNT(*) FROM order_status_history) AS order_status_history_count
  `);

  const counts = countsResult.rows[0];
  return (
    Number(counts.customers_count) > 0 &&
    Number(counts.suppliers_count) > 0 &&
    Number(counts.products_count) > 0 &&
    Number(counts.orders_count) > 0 &&
    Number(counts.order_lines_count) > 0 &&
    Number(counts.order_status_history_count) > 0
  );
}

function toNullable(value) {
  if (value === undefined || value === null) return null;
  const trimmed = String(value).trim();
  return trimmed === '' ? null : trimmed;
}

function toNumber(value) {
  const clean = toNullable(value);
  if (clean === null) return null;
  const parsed = Number(clean);
  return Number.isNaN(parsed) ? null : parsed;
}

function toInteger(value) {
  const parsed = toNumber(value);
  return parsed === null ? null : Math.trunc(parsed);
}

function toBoolean(value) {
  const clean = toNullable(value);
  if (clean === null) return null;
  return clean.toLowerCase() === 'true';
}

function toDateISO(value) {
  const clean = toNullable(value);
  if (!clean) return null;
  return clean;
}

function toDateFromSlash(value) {
  const clean = toNullable(value);
  if (!clean) return null;
  const [day, month, year] = clean.split('/');
  if (!day || !month || !year) return null;
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}

function normalizePostalCode(value) {
  const clean = toNullable(value);
  if (!clean) return null;
  const parsed = Number(clean);
  if (Number.isNaN(parsed)) return clean;
  return String(Math.trunc(parsed));
}

async function readCsv(fileName) {
  const filePath = path.join(dataDir, fileName);
  return new Promise((resolve, reject) => {
    const rows = [];
    fs.createReadStream(filePath)
      .pipe(
        parse({
          columns: true,
          trim: true,
          skip_empty_lines: true,
        })
      )
      .on('data', (row) => rows.push(row))
      .on('end', () => resolve(rows))
      .on('error', reject);
  });
}

async function importSuppliers(client) {
  const rows = await readCsv('suppliers.csv');
  for (const row of rows) {
    await client.query(
      `
      INSERT INTO suppliers (
        supplier_id, supplier_name, country, contact_email, contact_phone,
        rating, lead_time_days, payment_terms, active
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
      ON CONFLICT (supplier_id) DO UPDATE SET
        supplier_name = EXCLUDED.supplier_name,
        country = EXCLUDED.country,
        contact_email = EXCLUDED.contact_email,
        contact_phone = EXCLUDED.contact_phone,
        rating = EXCLUDED.rating,
        lead_time_days = EXCLUDED.lead_time_days,
        payment_terms = EXCLUDED.payment_terms,
        active = EXCLUDED.active,
        updated_at = NOW();
      `,
      [
        toNullable(row.Supplier_ID),
        toNullable(row.Supplier_Name),
        toNullable(row.Country),
        toNullable(row.Contact_Email),
        toNullable(row.Contact_Phone),
        toNumber(row.Rating),
        toInteger(row.Lead_Time_Days),
        toNullable(row.Payment_Terms),
        toBoolean(row.Active),
      ]
    );
  }
  return rows.length;
}

async function importCustomers(client) {
  const rows = await readCsv('customers_enriched.csv');
  for (const row of rows) {
    await client.query(
      `
      INSERT INTO customers (
        customer_id, customer_name, segment, city, state, region,
        gender, age, email, registration_date, total_sales, total_profit,
        total_orders, average_order_value, customer_segment_score
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
      ON CONFLICT (customer_id) DO UPDATE SET
        customer_name = EXCLUDED.customer_name,
        segment = EXCLUDED.segment,
        city = EXCLUDED.city,
        state = EXCLUDED.state,
        region = EXCLUDED.region,
        gender = EXCLUDED.gender,
        age = EXCLUDED.age,
        email = EXCLUDED.email,
        registration_date = EXCLUDED.registration_date,
        total_sales = EXCLUDED.total_sales,
        total_profit = EXCLUDED.total_profit,
        total_orders = EXCLUDED.total_orders,
        average_order_value = EXCLUDED.average_order_value,
        customer_segment_score = EXCLUDED.customer_segment_score,
        updated_at = NOW();
      `,
      [
        toNullable(row.Customer_ID),
        toNullable(row.Customer_Name),
        toNullable(row.Segment),
        toNullable(row.City),
        toNullable(row.State),
        toNullable(row.Region),
        toNullable(row.Gender),
        toInteger(row.Age),
        toNullable(row.Email),
        toDateISO(row.Registration_Date),
        toNumber(row.Total_Sales),
        toNumber(row.Total_Profit),
        toInteger(row.Total_Orders),
        toNumber(row.Average_Order_Value),
        toNullable(row.Customer_Segment_Score),
      ]
    );
  }
  return rows.length;
}

async function importProducts(client) {
  const consolidatedRows = await readCsv('products_consolidated.csv');
  for (const row of consolidatedRows) {
    await client.query(
      `
      INSERT INTO products (
        product_id, product_name, category, sub_category, unit_cost,
        stock_quantity, supplier_id, unit_price, total_units_sold, margin_percentage
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
      ON CONFLICT (product_id) DO UPDATE SET
        product_name = EXCLUDED.product_name,
        category = EXCLUDED.category,
        sub_category = EXCLUDED.sub_category,
        unit_cost = EXCLUDED.unit_cost,
        stock_quantity = EXCLUDED.stock_quantity,
        supplier_id = EXCLUDED.supplier_id,
        unit_price = EXCLUDED.unit_price,
        total_units_sold = EXCLUDED.total_units_sold,
        margin_percentage = EXCLUDED.margin_percentage,
        updated_at = NOW();
      `,
      [
        toNullable(row.Product_ID),
        toNullable(row.Product_Name),
        toNullable(row.Category),
        toNullable(row.Sub_Category),
        toNumber(row.Unit_Cost),
        toInteger(row.Stock_Quantity),
        toNullable(row.Supplier_ID),
        toNumber(row.Unit_Price),
        toInteger(row.Total_Units_Sold),
        toNumber(row.Margin_Percentage),
      ]
    );
  }

  const inventoryRows = await readCsv('products_inventory.csv');
  for (const row of inventoryRows) {
    await client.query(
      `
      INSERT INTO products (
        product_id, product_name, category, sub_category, stock_quantity,
        reorder_level, reorder_quantity, unit_cost, warehouse_location,
        last_restock_date, supplier_id
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
      ON CONFLICT (product_id) DO UPDATE SET
        product_name = EXCLUDED.product_name,
        category = EXCLUDED.category,
        sub_category = EXCLUDED.sub_category,
        stock_quantity = EXCLUDED.stock_quantity,
        reorder_level = EXCLUDED.reorder_level,
        reorder_quantity = EXCLUDED.reorder_quantity,
        unit_cost = EXCLUDED.unit_cost,
        warehouse_location = EXCLUDED.warehouse_location,
        last_restock_date = EXCLUDED.last_restock_date,
        supplier_id = EXCLUDED.supplier_id,
        updated_at = NOW();
      `,
      [
        toNullable(row.Product_ID),
        toNullable(row.Product_Name),
        toNullable(row.Category),
        toNullable(row.Sub_Category),
        toInteger(row.Stock_Quantity),
        toInteger(row.Reorder_Level),
        toInteger(row.Reorder_Quantity),
        toNumber(row.Unit_Cost),
        toNullable(row.Warehouse_Location),
        toDateISO(row.Last_Restock_Date),
        toNullable(row.Supplier_ID),
      ]
    );
  }

  return {
    consolidated: consolidatedRows.length,
    inventory: inventoryRows.length,
  };
}

async function importOrdersAndLines(client) {
  const rows = await readCsv('orders_transactions.csv');

  for (const row of rows) {
    await client.query(
      `
      INSERT INTO orders (
        order_id, customer_id, order_date, ship_date, ship_mode,
        country, city, state, postal_code, region
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
      ON CONFLICT (order_id) DO UPDATE SET
        customer_id = EXCLUDED.customer_id,
        order_date = EXCLUDED.order_date,
        ship_date = EXCLUDED.ship_date,
        ship_mode = EXCLUDED.ship_mode,
        country = EXCLUDED.country,
        city = EXCLUDED.city,
        state = EXCLUDED.state,
        postal_code = EXCLUDED.postal_code,
        region = EXCLUDED.region,
        updated_at = NOW();
      `,
      [
        toNullable(row['Order ID']),
        toNullable(row['Customer ID']),
        toDateFromSlash(row['Order Date']),
        toDateFromSlash(row['Ship Date']),
        toNullable(row['Ship Mode']),
        toNullable(row.Country),
        toNullable(row.City),
        toNullable(row.State),
        normalizePostalCode(row['Postal Code']),
        toNullable(row.Region),
      ]
    );

    await client.query(
      `
      INSERT INTO order_lines (
        row_id, order_id, product_id, quantity, discount,
        sales, unit_price, cost, profit
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
      ON CONFLICT (row_id) DO UPDATE SET
        order_id = EXCLUDED.order_id,
        product_id = EXCLUDED.product_id,
        quantity = EXCLUDED.quantity,
        discount = EXCLUDED.discount,
        sales = EXCLUDED.sales,
        unit_price = EXCLUDED.unit_price,
        cost = EXCLUDED.cost,
        profit = EXCLUDED.profit,
        updated_at = NOW();
      `,
      [
        toInteger(row['Row ID']),
        toNullable(row['Order ID']),
        toNullable(row['Product ID']),
        toInteger(row.Quantity),
        toNumber(row.Discount),
        toNumber(row.Sales),
        toNumber(row.Unit_Price),
        toNumber(row.Cost),
        toNumber(row.Profit),
      ]
    );
  }

  return rows.length;
}

async function importOrderStatus(client) {
  const rows = await readCsv('order_status.csv');

  for (const row of rows) {
    await client.query(
      `
      INSERT INTO order_status_history (order_id, status, status_date, updated_by)
      VALUES ($1,$2,$3,$4)
      ON CONFLICT (order_id, status, status_date) DO UPDATE SET
        updated_by = EXCLUDED.updated_by;
      `,
      [
        toNullable(row.Order_ID),
        toNullable(row.Status),
        toNullable(row.Status_Date),
        toNullable(row.Updated_By),
      ]
    );
  }

  return rows.length;
}

async function main() {
  await ensureDatabaseExists();

  const client = new Client({
    host: process.env.PGHOST,
    port: Number(process.env.PGPORT || 5432),
    database: process.env.PGDATABASE,
    user: process.env.PGUSER,
    password: process.env.PGPASSWORD,
  });

  await client.connect();

  try {
    const alreadyImported = await isInitialImportAlreadyDone(client);
    if (alreadyImported) {
      console.log(
        'Import ignore: la base existe deja et les donnees initiales sont deja chargees.'
      );
      return;
    }

    await client.query('BEGIN');

    const schemaSql = fs.readFileSync(schemaPath, 'utf8');
    await client.query(schemaSql);

    const suppliersCount = await importSuppliers(client);
    const customersCount = await importCustomers(client);
    const productsCount = await importProducts(client);
    const orderLinesCount = await importOrdersAndLines(client);
    const statusCount = await importOrderStatus(client);

    await client.query('COMMIT');

    console.log('Import termine avec succes.');
    console.log(`Suppliers: ${suppliersCount}`);
    console.log(`Customers: ${customersCount}`);
    console.log(`Products consolidated: ${productsCount.consolidated}`);
    console.log(`Products inventory: ${productsCount.inventory}`);
    console.log(`Order transactions (lignes): ${orderLinesCount}`);
    console.log(`Order status records: ${statusCount}`);
  } catch (error) {
    await client.query('ROLLBACK');
    console.error("Erreur pendant l'import:", error);
    process.exitCode = 1;
  } finally {
    await client.end();
  }
}

main();
