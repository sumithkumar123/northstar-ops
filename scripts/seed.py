"""
Seed demo data into all schemas.
Run AFTER docker compose is up:
    docker compose exec auth_service python /scripts/seed.py
Or standalone with DATABASE_URL set.

Creates:
  - 2 regions (US-East, GB-London)
  - 3 stores
  - 3 users (one per role)
  - 5 products
  - Inventory records for each store/product
"""
import asyncio
import os
import sys
import uuid

# When run inside a container the shared/ dir is on the path
sys.path.insert(0, "/app")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_BASE_DB = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://northstar:northstar_pass@postgres/northstar",
)
AUTH_DB = _BASE_DB
INV_DB = _BASE_DB

# Fixed UUIDs so the seed is idempotent / reproducible
REGION_US = "a1000000-0000-0000-0000-000000000001"
REGION_GB = "a1000000-0000-0000-0000-000000000002"
STORE_1   = "b1000000-0000-0000-0000-000000000001"
STORE_2   = "b1000000-0000-0000-0000-000000000002"
STORE_3   = "b1000000-0000-0000-0000-000000000003"
USER_ADMIN   = "c1000000-0000-0000-0000-000000000001"
USER_MANAGER = "c1000000-0000-0000-0000-000000000002"
USER_ASSOC   = "c1000000-0000-0000-0000-000000000003"

PRODUCTS = [
    ("SKU-001", "Trail Running Shoes",     "Lightweight trail runner", 129.99, 15, "Footwear"),
    ("SKU-002", "Merino Wool Base Layer",  "400g merino top",          89.99,  20, "Apparel"),
    ("SKU-003", "Trekking Poles (Pair)",   "Collapsible aluminium",    74.99,  10, "Equipment"),
    ("SKU-004", "Waterproof Jacket",       "3-layer Gore-Tex",         249.99,  8, "Apparel"),
    ("SKU-005", "Hiking Backpack 45L",     "Ventilated frame pack",    189.99,  5, "Equipment"),
]


async def seed_auth():
    engine = create_async_engine(AUTH_DB, echo=False,
                                  connect_args={"server_settings": {"search_path": "auth"}})
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        # Regions
        for rid, name, cc in [
            (REGION_US, "US-East", "US"),
            (REGION_GB, "GB-London", "GB"),
        ]:
            await db.execute(text("""
                INSERT INTO auth.regions (id, name, country_code)
                VALUES (:id, :name, :cc)
                ON CONFLICT (id) DO NOTHING
            """), {"id": rid, "name": name, "cc": cc})

        # Stores
        for sid, name, rid, city, cc in [
            (STORE_1, "NorthStar NYC Flagship",  REGION_US, "New York",  "US"),
            (STORE_2, "NorthStar Boston Outlet",  REGION_US, "Boston",    "US"),
            (STORE_3, "NorthStar London Central", REGION_GB, "London",    "GB"),
        ]:
            await db.execute(text("""
                INSERT INTO auth.stores (id, name, region_id, city, country_code)
                VALUES (:id, :name, :rid, :city, :cc)
                ON CONFLICT (id) DO NOTHING
            """), {"id": sid, "name": name, "rid": rid, "city": city, "cc": cc})

        # Users
        for uid, username, email, role, store_id, region_id in [
            (USER_ADMIN,   "admin",   "admin@northstar.com",   "regional_admin",  None,    REGION_US),
            (USER_MANAGER, "manager", "manager@northstar.com", "store_manager",   STORE_1, REGION_US),
            (USER_ASSOC,   "assoc",   "assoc@northstar.com",   "sales_associate", STORE_1, REGION_US),
        ]:
            await db.execute(text("""
                INSERT INTO auth.users (id, username, email, hashed_password, role, store_id, region_id)
                VALUES (:id, :username, :email, :hp, :role, :store_id, :region_id)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": uid, "username": username, "email": email,
                "hp": pwd_ctx.hash("password123"),
                "role": role, "store_id": store_id, "region_id": region_id,
            })

        await db.commit()
    await engine.dispose()
    print("Auth seed complete.")


async def seed_inventory():
    engine = create_async_engine(INV_DB, echo=False,
                                  connect_args={"server_settings": {"search_path": "inventory"}})
    Session = async_sessionmaker(engine, expire_on_commit=False)
    product_ids = {}

    async with Session() as db:
        # Category: get or create
        cat_ids = {}
        for _, _, _, _, _, cat_name in PRODUCTS:
            if cat_name not in cat_ids:
                cid = str(uuid.uuid4())
                await db.execute(text("""
                    INSERT INTO inventory.categories (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT (name) DO NOTHING
                """), {"id": cid, "name": cat_name})
                result = await db.execute(
                    text("SELECT id FROM inventory.categories WHERE name = :name"),
                    {"name": cat_name}
                )
                cat_ids[cat_name] = str(result.scalar_one())

        await db.flush()

        # Products
        for sku, name, desc, price, reorder, cat_name in PRODUCTS:
            pid = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO inventory.products (id, sku, name, description, category_id, unit_price, reorder_point)
                VALUES (:id, :sku, :name, :desc, :cat_id, :price, :reorder)
                ON CONFLICT (sku) DO NOTHING
            """), {"id": pid, "sku": sku, "name": name, "desc": desc,
                   "cat_id": cat_ids[cat_name], "price": price, "reorder": reorder})
            result = await db.execute(
                text("SELECT id FROM inventory.products WHERE sku = :sku"), {"sku": sku}
            )
            product_ids[sku] = str(result.scalar_one())

        await db.flush()

        # Inventory: each store gets 50 of each product
        for store_id in [STORE_1, STORE_2, STORE_3]:
            for sku, pid in product_ids.items():
                await db.execute(text("""
                    INSERT INTO inventory.inventory (id, store_id, product_id, quantity)
                    VALUES (:id, :store_id, :product_id, 50)
                    ON CONFLICT DO NOTHING
                """), {"id": str(uuid.uuid4()), "store_id": store_id, "product_id": pid})

        await db.commit()
    await engine.dispose()
    print("Inventory seed complete.")
    return product_ids


async def main():
    await seed_auth()
    product_ids = await seed_inventory()
    print("\nDemo credentials:")
    print("  admin   / password123  (regional_admin)")
    print("  manager / password123  (store_manager,  store:", STORE_1, ")")
    print("  assoc   / password123  (sales_associate, store:", STORE_1, ")")
    print("\nStore IDs:")
    print("  STORE_1 (NYC):", STORE_1)
    print("  STORE_2 (Boston):", STORE_2)
    print("  STORE_3 (London):", STORE_3)
    print("\nSample product IDs:", list(product_ids.items())[:3])


if __name__ == "__main__":
    asyncio.run(main())
