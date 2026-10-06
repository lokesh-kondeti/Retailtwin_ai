"""
Diagnostic + migration script for Store duplicates.

Duplicate pairs:
  Store[4] is a duplicate of Store[1]  — has 8 forecasts, 0 everything else
  Store[5] is a duplicate of Store[2]  — has 1 forecast,  0 everything else
  Store[6] is a duplicate of Store[3]  — has 0 records,   safe to delete

Plan:
  1. Migrate DEMAND_FORECAST records from store[4] → store[1]
  2. Migrate DEMAND_FORECAST records from store[5] → store[2]
  3. Delete store[6] (no dependents at all)
  4. Delete store[4] (after migration, no dependents)
  5. Delete store[5] (after migration, no dependents)
"""
import sqlalchemy as sa
from app import app, db

CANONICAL = {
    4: 1,  # store[4] → store[1]
    5: 2,  # store[5] → store[2]
}
SAFE_DELETE_EMPTY = [6]  # store[6] has zero dependents

with app.app_context():
    with db.engine.connect() as conn:
        # ── Step 1: Verify no Sales/Inventory/Simulations/CustomerFlow in duplicates ──
        print("Pre-migration safety check:")
        for dup_id in [4, 5, 6]:
            for tbl in ['inventory', 'sales', 'digital_twin_simulation', 'customer_flow']:
                cnt = conn.execute(
                    sa.text(f"SELECT COUNT(*) FROM {tbl} WHERE store_id=:sid"),
                    {"sid": dup_id}
                ).scalar()
                if cnt > 0:
                    raise RuntimeError(
                        f"ABORT: store[{dup_id}] has {cnt} rows in {tbl}. Manual review needed."
                    )
        print("  OK — duplicates have no Sales/Inventory/Simulation/CustomerFlow records.")

        # ── Step 2: Migrate demand_forecast rows from duplicates to canonical stores ──
        for dup_id, canon_id in CANONICAL.items():
            cnt = conn.execute(
                sa.text("SELECT COUNT(*) FROM demand_forecast WHERE store_id=:sid"),
                {"sid": dup_id}
            ).scalar()
            if cnt > 0:
                print(f"  Migrating {cnt} demand_forecast rows: store[{dup_id}] -> store[{canon_id}]")
                conn.execute(
                    sa.text("UPDATE demand_forecast SET store_id=:canon WHERE store_id=:dup"),
                    {"canon": canon_id, "dup": dup_id}
                )
            else:
                print(f"  store[{dup_id}]: no demand_forecast rows to migrate.")

        # ── Step 3: Delete the duplicate store rows (now with 0 dependents) ──
        for dup_id in list(CANONICAL.keys()) + SAFE_DELETE_EMPTY:
            for tbl in ['inventory', 'sales', 'digital_twin_simulation', 'customer_flow', 'demand_forecast']:
                cnt = conn.execute(
                    sa.text(f"SELECT COUNT(*) FROM {tbl} WHERE store_id=:sid"),
                    {"sid": dup_id}
                ).scalar()
                if cnt > 0:
                    raise RuntimeError(
                        f"ABORT: store[{dup_id}] still has {cnt} rows in {tbl} after migration."
                    )
            conn.execute(sa.text("DELETE FROM store WHERE store_id=:sid"), {"sid": dup_id})
            print(f"  Deleted duplicate store[{dup_id}].")

        conn.commit()

        # ── Step 4: Verify final state ──
        print("\nFinal store table:")
        rows = conn.execute(sa.text("SELECT store_id, store_name FROM store ORDER BY store_id")).fetchall()
        for r in rows:
            print(f"  [{r[0]}] {r[1]}")

        print("\nDuplicate check after migration:")
        rows = conn.execute(sa.text(
            "SELECT store_name, COUNT(*) AS cnt FROM store GROUP BY store_name HAVING COUNT(*) > 1"
        )).fetchall()
        print(f"  Duplicate store names remaining: {len(rows)}")

print("\nMigration complete.")
