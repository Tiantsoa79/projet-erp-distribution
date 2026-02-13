# Catalogue des erreurs métier et techniques

## 1. Auth / RBAC (Gateway)

- `401 UNAUTHORIZED`: token absent
- `401 INVALID_TOKEN`: token invalide/expiré
- `403 FORBIDDEN`: permission manquante
- `401 INVALID_CREDENTIALS`: login invalide
- `403 USER_DISABLED`: utilisateur inactif

## 2. Admin RBAC

- `400 BAD_REQUEST`: paramètres invalides
- `404 USER_NOT_FOUND`
- `404 ROLE_NOT_FOUND`
- `409 ROLE_ALREADY_ASSIGNED`
- `404 ROLE_NOT_ASSIGNED`

## 3. Sales

- `422 BUSINESS_VALIDATION_FAILED`
- `422 INVALID_STATUS`
- `422 INVALID_TRANSITION`
- `422 MISSING_ORDER_DATE`
- `409 PERIOD_CLOSED`
- `404 Order not found`

## 4. Catalog

- `404 Product not found`
- `404 SUPPLIER_NOT_FOUND` (nom fournisseur introuvable)
- `409 SUPPLIER_AMBIGUOUS` (nom fournisseur non unique)
- `409` contraintes DB (`23505`, `23503`)

## 5. Customers

- `404 Customer not found`
- `400 customer_name est requis` (create)
- `409` contraintes DB (`23505`, `23503`)

## 6. Suppliers

- `404 Supplier not found`
- `400 supplier_name est requis` (create)
- `409` contraintes DB (`23505`, `23503`)

## 7. Règles de mapping status HTTP

- `error.status` explicite prioritaire
- sinon `409` pour erreurs DB connues (`23505`, `23503`)
- sinon `500`
