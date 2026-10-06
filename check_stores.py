import sqlalchemy as sa
from app import app, db
from models.store import Store

with app.app_context():
    with db.engine.connect() as conn:
        print("=" * 60)
        print("ALL STORES (store_id, store_name):")
        print("=" * 60)
        rows = conn.execute(sa.text("SELECT store_id, store_name, location, manager_name FROM store ORDER BY store_id")).fetchall()
        for r in rows:
            print(f"  [{r[0]}] {r[1]} | loc={r[2]} | mgr={r[3]}")

        print("\n" + "=" * 60)
        print("DUPLICATE STORE NAMES (COUNT > 1):")
        print("=" * 60)
        rows = conn.execute(sa.text("SELECT store_name, COUNT(*) AS cnt FROM store GROUP BY store_name HAVING COUNT(*) > 1")).fetchall()
        if rows:
            for r in rows:
                print(f"  '{r[0]}' appears {r[1]} times")
        else:
            print("  None found — no actual DB duplicates.")

        print("\n" + "=" * 60)
        print("DEPENDENT RECORDS PER STORE:")
        print("=" * 60)
        stores = conn.execute(sa.text("SELECT store_id, store_name FROM store ORDER BY store_id")).fetchall()
        for s in stores:
            sid = s[0]
            inv  = conn.execute(sa.text("SELECT COUNT(*) FROM inventory WHERE store_id=:sid"), {"sid": sid}).scalar()
            sal  = conn.execute(sa.text("SELECT COUNT(*) FROM sales WHERE store_id=:sid"), {"sid": sid}).scalar()
            df   = conn.execute(sa.text("SELECT COUNT(*) FROM demand_forecast WHERE store_id=:sid"), {"sid": sid}).scalar()
            dts  = conn.execute(sa.text("SELECT COUNT(*) FROM digital_twin_simulation WHERE store_id=:sid"), {"sid": sid}).scalar()
            cf   = conn.execute(sa.text("SELECT COUNT(*) FROM customer_flow WHERE store_id=:sid"), {"sid": sid}).scalar()
            print(f"  Store[{sid}] '{s[1]}': inv={inv}, sales={sal}, forecasts={df}, simulations={dts}, customer_flow={cf}")

        print("\n" + "=" * 60)
        print("LIVE API TEST (Store.query.all()):")
        print("=" * 60)
        stores_orm = Store.query.order_by(Store.store_id).all()
        for s in stores_orm:
            print(f"  [{s.store_id}] {s.store_name}")
        print(f"  Total returned by ORM: {len(stores_orm)}")

        print("\n" + "=" * 60)
        print("STORE TABLE SCHEMA:")
        print("=" * 60)
        schema = conn.execute(sa.text("SHOW CREATE TABLE store")).fetchone()[1]
        print(schema)
