const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.DWH_PGHOST || 'localhost',
  port: parseInt(process.env.DWH_PGPORT || '5432', 10),
  database: process.env.DWH_PGDATABASE || 'erp_distribution_dwh',
  user: process.env.DWH_PGUSER || 'postgres',
  password: process.env.DWH_PGPASSWORD || '',
  max: 10,
  idleTimeoutMillis: 30000,
});

pool.on('error', (err) => {
  console.error('[db] Erreur connexion PostgreSQL:', err.message);
});

module.exports = pool;
