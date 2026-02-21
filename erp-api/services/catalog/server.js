const app = require('./app');

const CATALOG_SERVICE_PORT = Number(process.env.CATALOG_SERVICE_PORT || 4002);

app.listen(CATALOG_SERVICE_PORT, () => {
  console.log(`Catalog service running on port ${CATALOG_SERVICE_PORT}`);
});
