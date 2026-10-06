"""Add UNIQUE constraint on store.store_name — run AFTER duplicate rows are removed."""
import sqlalchemy as sa
from app import app, db

with app.app_context():
    with db.engine.connect() as conn:
        # Check if constraint already exists
        existing = conn.execute(sa.text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema=DATABASE() AND table_name='store' AND index_name='uq_store_name'"
        )).scalar()

        if existing:
            print("UNIQUE constraint uq_store_name already exists — skipping.")
        else:
            conn.execute(sa.text(
                "ALTER TABLE store ADD CONSTRAINT uq_store_name UNIQUE (store_name)"
            ))
            conn.commit()
            print("UNIQUE constraint uq_store_name added successfully.")

        # Verify
        res = conn.execute(sa.text("SHOW CREATE TABLE store")).fetchone()[1]
        print("\nStore schema:")
        print(res)
