# NorthStar Outfitters — Operations Platform Prototype

Microservices-based retail operations platform built with Python/FastAPI + PostgreSQL.

## Quick Start

```bash
# 1. Generate RSA keypair (one-time)
docker compose run --rm keygen

# 2. Start all services
docker compose up --build

# 3. Seed demo data (wait ~15s for services to be ready)
docker compose exec auth_service python /scripts/seed.py
```

Services will be available at:

| Service    | Port  | Docs                          |
|------------|-------|-------------------------------|
| Gateway    | 8000  | http://localhost:8000/docs    |
| Auth       | 8001  | http://localhost:8001/docs    |
| Inventory  | 8002  | http://localhost:8002/docs    |
| Sales      | 8003  | http://localhost:8003/docs    |

---

## Demo Walkthrough

### 1. Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "manager", "password": "password123"}'
```
Save the `access_token` from the response.

```bash
TOKEN="<paste access_token here>"
```

### 2. View store inventory
```bash
STORE_ID="b1000000-0000-0000-0000-000000000001"

curl http://localhost:8000/inventory/stores/$STORE_ID \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Create a sale
```bash
# Get a product ID first — from the inventory response above, copy a product_id
curl -X POST http://localhost:8000/sales/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "b1000000-0000-0000-0000-000000000001",
    "payment_method": "card",
    "country_code": "US",
    "state_code": "NY",
    "items": [{
      "product_id": "<product_id from inventory>",
      "sku": "SKU-001",
      "product_name": "Trail Running Shoes",
      "quantity": 2,
      "unit_price": 129.99
    }]
  }'
```

### 4. Daily sales report (manager/admin only)
```bash
curl "http://localhost:8000/sales/reports/daily?store_id=$STORE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. RBAC test — sales associate cannot adjust stock
```bash
# Login as sales associate
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "assoc", "password": "password123"}'

ASSOC_TOKEN="<assoc access_token>"

# This will return 403 Forbidden
curl -X PATCH "http://localhost:8000/inventory/stores/$STORE_ID/products/<product_id>" \
  -H "Authorization: Bearer $ASSOC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"delta": 10, "transaction_type": "restock"}'
```

---

## Architecture

```
Client (PWA/Browser)
       │ HTTPS
       ▼
  Gateway :8000          ← JWT validation, routing
  ├── Auth :8001          ← Login, JWT issuance (RS256)
  ├── Inventory :8002     ← Stock CRUD, pessimistic locking
  └── Sales :8003         ← Order state machine, tax, receipts
       │
  PostgreSQL :5432
  ├── schema: auth
  ├── schema: inventory
  └── schema: sales
```

## User Roles

| Role             | Login       | Password     | Permissions                              |
|------------------|-------------|--------------|------------------------------------------|
| regional_admin   | admin       | password123  | Full access to all stores                |
| store_manager    | manager     | password123  | Inventory updates, reports, void orders  |
| sales_associate  | assoc       | password123  | Create sales, view own store inventory   |

## Key Design Decisions

- **RS256 JWT**: asymmetric — services only need the public key; private key stays in auth_service only
- **SELECT FOR UPDATE**: inventory adjustments use pessimistic locking to prevent overselling under concurrent POS load
- **offline_id on SalesOrder**: UNIQUE constraint makes PWA offline sync retries idempotent — no double-posting
- **Tax calculation**: pluggable per country_code (US state tax / GB VAT)
- **Separate PostgreSQL schemas** (not separate databases): preserves service boundary while keeping Docker Compose simple for the prototype
