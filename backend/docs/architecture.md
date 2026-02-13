# Architecture technique - ERP Distribution Backend

## 1. Vue d'ensemble

Le backend est construit en architecture SOA/microservices autour d'une API REST exposée via une gateway.

- Gateway (`:4000`): authentification JWT, contrôle RBAC, routage vers les services métier.
- Sales (`:4001`): commandes, lignes, workflow de statuts, règles de période comptable.
- Catalog (`:4002`): produits, stock, rattachement fournisseurs.
- Customers (`:4003`): clients.
- Suppliers (`:4004`): fournisseurs.
- PostgreSQL: persistance transactionnelle + audit + RBAC + périodes comptables.

## 2. Principes de conception

- Séparation claire par domaine métier.
- Contrats REST homogènes via gateway (`/api/v1/*`).
- Contrôle d'accès basé sur permissions (RBAC) au niveau gateway.
- Auditabilité des opérations sensibles (create/update/delete/transition/administration).
- Validation métier explicite et erreurs contrôlées (`422`, `409`, etc.).

## 3. Flux d'appel standard

1. Le client appelle la gateway avec token JWT.
2. La gateway valide l'authentification.
3. La gateway détermine la permission requise selon route + méthode.
4. Si autorisé, la requête est relayée au microservice cible.
5. Le microservice applique validations métier, transaction DB et audit.
6. La réponse est renvoyée telle quelle via la gateway.

## 4. Composants clés

### 4.1 Gateway

Responsabilités:
- login/logout/me
- endpoints admin RBAC (users/roles/assign/revoke)
- endpoint audit read
- forward proxy vers services métiers

### 4.2 Services métiers

Chaque service métier suit le pattern:
- `server.js`: bootstrap (port + `app.listen`)
- `app.js`: routes, validations, transactions, audit

## 5. Décisions d'architecture importantes

- Les clés étrangères restent des IDs en base.
- L'API accepte des noms pour ergonomie (`supplier_name`, `customer_name`, `product_name`) puis résout vers IDs avant persistance.
- Certains IDs sont auto-générés si absents (suppliers/customers/products/orders).
- Les transitions d'état de commande sont strictement contrôlées.
- Les périodes comptables fermées bloquent les mutations de commandes.

## 6. Diagrammes associés

Sources Mermaid:
- `docs/diagrams/mermaid/system-context.md`
- `docs/diagrams/mermaid/container-view.md`
- `docs/diagrams/mermaid/sequence-create-order.md`
- `docs/diagrams/mermaid/deployment-view.md`

Exports PNG:
- `docs/diagrams/png/system-context-c4-level-1.png`
- `docs/diagrams/png/container-view.png`
- `docs/diagrams/png/sequence-create-order.png`
- `docs/diagrams/png/deployment-view.png`
- `docs/diagrams/png/mcd.png`
- `docs/diagrams/png/mld-relationnel-simplifie.png`
- `docs/diagrams/png/erd.png`

Et pour la base:
- `docs/data-model.md` (MCD/MLD/ERD)
