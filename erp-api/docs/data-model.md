# Modèle de données (MCD / MLD / ERD)

## 1. MCD (conceptuel)

```mermaid
flowchart LR
  Client[Client]
  Commande[Commande]
  Ligne[LigneCommande]
  Produit[Produit]
  Fournisseur[Fournisseur]
  Historique[HistoriqueStatutCommande]
  Utilisateur[Utilisateur]
  Role[Role]
  Permission[Permission]
  Audit[JournalAudit]
  Periode[PeriodeComptable]

  Client -->|0..N passe| Commande
  Commande -->|1..N contient| Ligne
  Ligne -->|1 reference| Produit
  Fournisseur -->|0..N fournit| Produit
  Commande -->|0..N a| Historique
  Utilisateur -->|N..N| Role
  Role -->|N..N| Permission

  Utilisateur -.acteur de.-> Audit
  Commande -.controlee par.-> Periode
```

## 2. MLD (relationnel simplifié)

```mermaid
classDiagram
  class customers {
    +customer_id PK
  }
  class suppliers {
    +supplier_id PK
  }
  class products {
    +product_id PK
    +supplier_id FK
  }
  class orders {
    +order_id PK
    +customer_id FK
  }
  class order_lines {
    +row_id PK
    +order_id FK
    +product_id FK
  }
  class order_status_history {
    +id PK
    +order_id FK
  }
  class users {
    +user_id PK
  }
  class roles {
    +role_id PK
  }
  class permissions {
    +permission_id PK
  }
  class user_roles {
    +user_id FK
    +role_id FK
    +PK composite
  }
  class role_permissions {
    +role_id FK
    +permission_id FK
    +PK composite
  }
  class audit_logs {
    +audit_id PK
  }
  class accounting_periods {
    +period_id PK
  }

  customers "1" --> "0..*" orders : customer_id
  orders "1" --> "1..*" order_lines : order_id
  suppliers "1" --> "0..*" products : supplier_id
  products "1" --> "0..*" order_lines : product_id
  orders "1" --> "0..*" order_status_history : order_id
  users "1" --> "0..*" user_roles : user_id
  roles "1" --> "0..*" user_roles : role_id
  roles "1" --> "0..*" role_permissions : role_id
  permissions "1" --> "0..*" role_permissions : permission_id
```

## 3. ERD (Mermaid)

```mermaid
erDiagram
  CUSTOMERS ||--o{ ORDERS : places
  ORDERS ||--|{ ORDER_LINES : contains
  PRODUCTS ||--o{ ORDER_LINES : referenced_by
  SUPPLIERS ||--o{ PRODUCTS : provides
  ORDERS ||--o{ ORDER_STATUS_HISTORY : has

  USERS ||--o{ USER_ROLES : has
  ROLES ||--o{ USER_ROLES : assigned
  ROLES ||--o{ ROLE_PERMISSIONS : grants
  PERMISSIONS ||--o{ ROLE_PERMISSIONS : mapped

  CUSTOMERS {
    string customer_id PK
    string customer_name
    string segment
    string city
    string region
  }

  SUPPLIERS {
    string supplier_id PK
    string supplier_name
    string country
  }

  PRODUCTS {
    string product_id PK
    string product_name
    string supplier_id FK
    int stock_quantity
  }

  ORDERS {
    string order_id PK
    string customer_id FK
    date order_date
    string current_status
  }

  ORDER_LINES {
    int row_id PK
    string order_id FK
    string product_id FK
    int quantity
    decimal sales
  }

  ORDER_STATUS_HISTORY {
    int id PK
    string order_id FK
    string status
    datetime status_date
  }

  USERS {
    int user_id PK
    string username
    bool is_active
  }

  ROLES {
    int role_id PK
    string role_code
  }

  PERMISSIONS {
    int permission_id PK
    string permission_code
  }
```

## 4. Contraintes clés

- `orders_ship_date_after_order_date_check`
- `suppliers_rating_range_check` (rating entre 0 et 5)
- `suppliers_lead_time_non_negative_check` (lead_time_days >= 0)
- `products_non_negative_values_check` (unit_cost, unit_price, stock/reorder >= 0)
- `order_lines_business_values_check` (quantity > 0, discount 0..1, montants >= 0)
- `status` des périodes comptables limité à `open|closed`
- suppression cascade `orders -> order_lines` et `orders -> order_status_history`
- clés uniques sur `username`, `role_code`, `permission_code`

## 5. Note API / FK

La base conserve les FK en ID.
L'API peut accepter des noms (supplier/customer/product), puis résout vers ID avant persistance.
