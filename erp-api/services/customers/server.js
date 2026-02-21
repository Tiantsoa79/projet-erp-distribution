const app = require('./app');

const CUSTOMERS_SERVICE_PORT = Number(process.env.CUSTOMERS_SERVICE_PORT || 4003);

app.listen(CUSTOMERS_SERVICE_PORT, () => {
  console.log(`Customers service running on port ${CUSTOMERS_SERVICE_PORT}`);
});
