const app = require('./app');

const SUPPLIERS_SERVICE_PORT = Number(
  process.env.SUPPLIERS_SERVICE_PORT || process.env.SUPPLIER_SERVICE_PORT || 4004
);

app.listen(SUPPLIERS_SERVICE_PORT, () => {
  console.log(`Suppliers service running on port ${SUPPLIERS_SERVICE_PORT}`);
});
