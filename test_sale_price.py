"""
Full end-to-end test suite for the selling-price change.

Tests:
  T1. Selecting Verification Milk: selling_price auto-populated from product
  T2. Backend ignores client-supplied selling_price (uses product's price)
  T3. Product price change does NOT alter old sales record
  T4. Sale submitted without selling_price succeeds
  T5. Revenue = qty × selling_price × (1 - discount/100)
  T6. MySQL record has correct columns
  T7. Inventory reduced after sale
  T8. Old sales records unaffected
"""
import json
import sqlalchemy as sa
from decimal import Decimal
from datetime import date
from app import create_app
from models import db
from models.product import Product
from models.store import Store
from models.inventory import Inventory
from models.sales import Sales

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

PASS = []
FAIL = []


def check(name, condition, detail=''):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}  {detail}")


with app.app_context():
    with app.test_client() as client:
        # ── Login ──────────────────────────────────────────────────────────────
        client.post('/auth/api/auth/login',
            json={'email': 'admin@retailtwin.ai', 'password': 'Admin@1234'})

        # ── Locate data ────────────────────────────────────────────────────────
        product = Product.query.filter_by(product_name='Verification Milk').first()
        store   = Store.query.filter_by(store_name='RetailTwin Main Store').first()
        inv     = Inventory.query.filter_by(
            product_id=product.product_id, store_id=store.store_id).first()

        sell_price = float(product.selling_price)
        cost_price = float(product.cost_price)
        stock_before = inv.current_stock

        print(f"\nProduct: {product.product_name}  sell={sell_price}  cost={cost_price}")
        print(f"Store: {store.store_name}  stock={stock_before}\n")

        # ── T1: Product API returns selling_price field ─────────────────────────
        print("T1 — /api/products returns selling_price")
        res = client.get('/api/products')
        products = json.loads(res.data)['data']
        vm = next((p for p in products if p['product_name'] == 'Verification Milk'), None)
        check("T1-a: product found in API", vm is not None)
        check("T1-b: selling_price field present", vm and 'selling_price' in vm,
              f"keys={list(vm.keys()) if vm else []}")
        check("T1-c: selling_price is correct",
              vm and float(vm['selling_price']) == sell_price,
              f"got={vm.get('selling_price') if vm else None}")
        check("T1-d: cost_price field present", vm and 'cost_price' in vm)

        # ── T2: POST without selling_price still creates sale ──────────────────
        print("\nT2 — POST /api/sales without selling_price (backend fetches from product)")
        res = client.post('/api/sales', json={
            'store_id': store.store_id,
            'product_id': product.product_id,
            'sale_date': date.today().isoformat(),
            'quantity_sold': 2,
            'discount': 10
        })
        body = json.loads(res.data)
        check("T2-a: HTTP 201", res.status_code == 201, f"got {res.status_code}")
        check("T2-b: success=True", body.get('success'), body.get('message'))
        sale_data = body.get('data', {})
        check("T2-c: selling_price = product price",
              float(sale_data.get('selling_price', 0)) == sell_price,
              f"expected={sell_price} got={sale_data.get('selling_price')}")
        check("T2-d: cost_price = product cost",
              float(sale_data.get('cost_price', 0)) == cost_price,
              f"expected={cost_price} got={sale_data.get('cost_price')}")

        # Revenue = 2 × 42 × 0.90 = 75.60
        expected_revenue = round(2 * sell_price * 0.90, 2)
        check("T2-e: revenue correct",
              abs(float(sale_data.get('revenue', 0)) - expected_revenue) < 0.01,
              f"expected={expected_revenue} got={sale_data.get('revenue')}")
        created_sale_id = sale_data.get('sale_id')

        # ── T3: Backend ignores client-supplied selling_price ──────────────────
        print("\nT3 — Backend ignores tampered selling_price from client")
        res_tamper = client.post('/api/sales', json={
            'store_id': store.store_id,
            'product_id': product.product_id,
            'sale_date': date.today().isoformat(),
            'quantity_sold': 1,
            'selling_price': 999.99,   # tampered value — must be ignored
            'discount': 0
        })
        body_t = json.loads(res_tamper.data)
        check("T3-a: sale succeeds despite tampered price", body_t.get('success'),
              body_t.get('message'))
        sale_t = body_t.get('data', {})
        check("T3-b: recorded selling_price is still product price (not 999.99)",
              float(sale_t.get('selling_price', 0)) == sell_price,
              f"got={sale_t.get('selling_price')}")
        tamper_sale_id = sale_t.get('sale_id')

        # ── T4: Inventory reduced correctly ────────────────────────────────────
        print("\nT4 — Inventory reduced by quantity sold (2 + 1 = 3)")
        db.session.refresh(inv)
        stock_after = inv.current_stock
        check("T4: inventory reduced by 3",
              stock_before - stock_after == 3,
              f"before={stock_before} after={stock_after}")

        # ── T5: MySQL row has correct columns ──────────────────────────────────
        print("\nT5 — MySQL record columns")
        with db.engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT sale_id, product_id, store_id, quantity_sold, selling_price, "
                "cost_price, discount, revenue FROM sales WHERE sale_id=:sid"),
                {"sid": created_sale_id}
            ).fetchone()
        check("T5-a: row found", row is not None)
        if row:
            check("T5-b: product_id correct",  row[1] == product.product_id)
            check("T5-c: store_id correct",     row[2] == store.store_id)
            check("T5-d: quantity_sold = 2",    row[3] == 2)
            check("T5-e: selling_price = 42.00", float(row[4]) == sell_price, f"got={row[4]}")
            check("T5-f: cost_price = 30.00",    float(row[5]) == cost_price, f"got={row[5]}")
            check("T5-g: discount = 10.00",      float(row[6]) == 10.0, f"got={row[6]}")
            check("T5-h: revenue = 75.60",       abs(float(row[7]) - expected_revenue) < 0.01,
                  f"got={row[7]}")

        # ── T6: Historical price preserved after product price change ──────────
        print("\nT6 — Historical price preserved after product price change")
        original_price = product.selling_price
        product.selling_price = Decimal('99.00')
        db.session.commit()

        # Read the old sale from DB
        with db.engine.connect() as conn:
            old_price = conn.execute(sa.text(
                "SELECT selling_price FROM sales WHERE sale_id=:sid"),
                {"sid": created_sale_id}
            ).scalar()
        check("T6: old sale still has original price",
              float(old_price) == sell_price,
              f"got={old_price} expected={sell_price}")

        # Restore product price
        product.selling_price = original_price
        db.session.commit()

        # ── Cleanup ────────────────────────────────────────────────────────────
        print("\nCleanup — removing test sales and restoring inventory")
        for sid in [created_sale_id, tamper_sale_id]:
            if sid:
                sale_obj = db.session.get(Sales, sid)
                if sale_obj:
                    inv.current_stock += sale_obj.quantity_sold
                    db.session.delete(sale_obj)
        db.session.commit()
        print(f"  Inventory restored to: {inv.current_stock}")

print(f"\n{'='*50}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print(f"FAILED: {FAIL}")
else:
    print("All tests passed!")
