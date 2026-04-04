# Railway Deployment Guide

## Step 1 — Create Railway project

1. Go to https://railway.app → sign up (free, no credit card)
2. New Project → Empty Project
3. Name it `northstar`

---

## Step 2 — Add PostgreSQL

Inside the project:
- Click **+ New** → **Database** → **PostgreSQL**
- Wait for it to provision
- Click the PostgreSQL service → **Variables** tab → copy `DATABASE_URL`

---
postgresql://postgres:ZkuCwdBMvUVvMUUfcyRpcdRajVfOSlUi@postgres.railway.internal:5432/railway
## Step 3 — Push code to GitHub

```bash
cd c:/Users/sumith/Documents/Supply_Chain/northstar
git init   # if not already a repo
git add .
git commit -m "Railway deployment ready"
# Create a new GitHub repo named northstar-ops, then:
git remote add origin https://github.com/YOUR_USERNAME/northstar-ops.git
git push -u origin main
```

---

## Step 4 — Deploy services (repeat for each)

For each service: **+ New** → **GitHub Repo** → select `northstar-ops` → configure:

### Auth Service
- **Root Directory:** `*leave empty*` (Must be `/` so Docker can see the `shared/` folder)
- **Dockerfile Path:** `auth_service/Dockerfile`
- **Environment Variables:**
```
DATABASE_URL=<paste from PostgreSQL>
DB_SCHEMA=auth
JWT_PRIVATE_KEY_B64=<from .env.railway file>
JWT_PUBLIC_KEY_B64=<from .env.railway file>
ACCESS_TOKEN_TTL=900
REFRESH_TOKEN_TTL=86400
```
- After deploy, note the URL e.g. `https://northstar-auth.up.railway.app`
- 
northstar-ops-production.up.railway.app

### Inventory Service
- **Root Directory:** `*leave empty*`
- **Dockerfile Path:** `inventory_service/Dockerfile`
- **Environment Variables:**
```
DATABASE_URL=<paste from PostgreSQL>
DB_SCHEMA=inventory
JWT_PUBLIC_KEY_B64=<from .env.railway file>
```
- Note URL e.g. `https://northstar-inventory.up.railway.app`

### Sales Service
- **Root Directory:** `*leave empty*`
- **Dockerfile Path:** `sales_service/Dockerfile`
- **Environment Variables:**
```
DATABASE_URL=<paste from PostgreSQL>
DB_SCHEMA=sales
JWT_PUBLIC_KEY_B64=<from .env.railway file>
INVENTORY_SERVICE_URL=https://northstar-inventory.up.railway.app
```

### AI Service
- **Root Directory:** `*leave empty*`
- **Dockerfile Path:** `ai_service/Dockerfile`
- **Environment Variables:**
```
DATABASE_URL=<paste from PostgreSQL>
```

### Gateway
- **Root Directory:** `*leave empty*`
- **Dockerfile Path:** `gateway/Dockerfile`
- **Environment Variables:**
```
JWT_PUBLIC_KEY_B64=<from .env.railway file>
AUTH_SERVICE_URL=https://northstar-auth.up.railway.app
INVENTORY_SERVICE_URL=https://northstar-inventory.up.railway.app
SALES_SERVICE_URL=https://northstar-sales.up.railway.app
AI_SERVICE_URL=https://northstar-ai.up.railway.app
```
- Note URL e.g. `https://northstar-gateway.up.railway.app`

### Frontend
- **Root Directory:** `/frontend` (This one MUST have the root directory set, no Dockerfile Path needed)
- **Environment Variables:**
```
GATEWAY_URL=https://northstar-gateway.up.railway.app
```
- This is the **public URL** judges will use

---

## Step 5 — Seed demo data

In Railway dashboard → Auth Service → **Shell** (or Deployments → latest → Run Command):
```bash
python /scripts/seed.py
```

Or via curl after deployment:
```bash
# The seed runs automatically if you add this to auth_service startup
```

---

## Step 6 — Get your public URL

Frontend service → **Settings** → **Domains** → **Generate Domain**

Share this URL in your submission. Format will be:
```
https://northstar-frontend-production.up.railway.app
```

---

## Key values from .env.railway

Open `c:/Users/sumith/Documents/Supply_Chain/northstar/.env.railway`  
Copy `JWT_PRIVATE_KEY_B64` and `JWT_PUBLIC_KEY_B64` values into Railway env vars.

> **Keep .env.railway secret** — do not commit to GitHub (it's in .gitignore)
