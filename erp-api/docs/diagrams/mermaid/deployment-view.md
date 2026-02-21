# Deployment View

```mermaid
flowchart LR
  subgraph LocalHost[Local machine / VM]
    GW[Gateway Node.js :4000]
    SA[Sales Node.js :4001]
    CA[Catalog Node.js :4002]
    CU[Customers Node.js :4003]
    SU[Suppliers Node.js :4004]
    PG[(PostgreSQL :5432)]
  end

  Client[Client HTTP] --> GW
  GW --> SA
  GW --> CA
  GW --> CU
  GW --> SU

  GW --> PG
  SA --> PG
  CA --> PG
  CU --> PG
  SU --> PG
```

Variables environnementales principales:
- `GATEWAY_PORT`, `SALES_SERVICE_PORT`, `CATALOG_SERVICE_PORT`, `CUSTOMERS_SERVICE_PORT`, `SUPPLIERS_SERVICE_PORT`
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
- `GATEWAY_JWT_SECRET`
