const path = require('path');
const fs = require('fs');

// Charger .env racine en priorite, sinon local
const rootEnv = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(rootEnv)) {
  require('dotenv').config({ path: rootEnv });
} else {
  require('dotenv').config();
}

const express = require('express');
const cors = require('cors');

const dashboardRoutes = require('./routes/dashboard');
const pipelineRoutes = require('./routes/pipeline');
const miningRoutes = require('./routes/mining');
const aiRoutes = require('./routes/ai');

const app = express();
const PORT = parseInt(process.env.INTERFACE_PORT || process.env.PORT || '3030', 10);

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// API routes
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/pipeline', pipelineRoutes);
app.use('/api/mining', miningRoutes);
app.use('/api/ai', aiRoutes);

// SPA fallback
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`\n  ============================================`);
  console.log(`  ERP Distribution - Interface Decisionnelle`);
  console.log(`  http://localhost:${PORT}`);
  console.log(`  ============================================`);
  console.log(`  #/             Pipeline ETL`);
  console.log(`  #/strategic    Dashboard Strategique`);
  console.log(`  #/tactical     Dashboard Tactique`);
  console.log(`  #/operational  Dashboard Operationnel`);
  console.log(`  #/mining       Data Mining`);
  console.log(`  #/ai           AI Reporting`);
  console.log(`  ============================================\n`);
});
