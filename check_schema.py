import sqlalchemy as sa
from app import app, db
with app.app_context():
    with db.engine.connect() as conn:
        print("DEMAND_FORECAST:")
        print(conn.execute(sa.text("SHOW CREATE TABLE DEMAND_FORECAST")).fetchone()[1])
        print("\nSALES:")
        print(conn.execute(sa.text("SHOW CREATE TABLE SALES")).fetchone()[1])
