const app = require('./app');

const SALES_SERVICE_PORT = Number(process.env.SALES_SERVICE_PORT || 4001);

app.listen(SALES_SERVICE_PORT, () => {
  console.log(`Sales service running on port ${SALES_SERVICE_PORT}`);
});
