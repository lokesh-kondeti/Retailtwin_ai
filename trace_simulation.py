"""
Full Digital Twin end-to-end trace:
1. Verify Verification Milk + RetailTwin Main Store data
2. Fire /api/simulation for all 3 scenarios
3. Fire /api/simulations/compare
4. Print the exact JSON returned
5. Verify inventory was NOT modified
"""
import json
import sqlalchemy as sa
from app import app, db
from models.product import Product
from models.store import Store
from models.inventory import Inventory
from models.demand_forecast import DemandForecast

with app.app_context():
    print("=" * 60)
    print("STEP 1 — Verify DB data")
    print("=" * 60)

    product = Product.query.filter_by(product_name='Verification Milk').first()
    if not product:
        print("ERROR: 'Verification Milk' not found!")
        exit(1)
    print(f"Product: [{product.product_id}] {product.product_name}")
    print(f"  cost_price={product.cost_price}  selling_price={product.selling_price}")

    store = Store.query.filter_by(store_name='RetailTwin Main Store').first()
    if not store:
        print("ERROR: 'RetailTwin Main Store' not found!")
        exit(1)
    print(f"Store: [{store.store_id}] {store.store_name}")

    inv = Inventory.query.filter_by(product_id=product.product_id, store_id=store.store_id).first()
    if inv:
        print(f"Inventory: current_stock={inv.current_stock}")
        initial_stock = inv.current_stock
    else:
        print("WARNING: No inventory record.")
        initial_stock = None

    fc = DemandForecast.query.filter_by(
        product_id=product.product_id, store_id=store.store_id
    ).order_by(DemandForecast.created_at.desc()).first()
    if fc:
        print(f"Latest Forecast: {fc.predicted_demand} units/day  model={fc.model_name}")
    else:
        print("WARNING: No demand forecast record.")

    print("\n" + "=" * 60)
    print("STEP 2 — Run simulations via Flask test client")
    print("=" * 60)

    from app import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    with flask_app.test_client() as client:
        # Login
        login_res = client.post('/auth/api/auth/login',
            json={'email': 'admin@retailtwin.ai', 'password': 'Admin@1234'})
        print(f"Login: {login_res.status_code} {json.loads(login_res.data).get('message','')}")

        # Run each scenario
        scenarios = [
            ('Conservative', 100),
            ('Balanced', 150),
            ('Aggressive', 200),
        ]
        sim_ids = []
        for name, stock in scenarios:
            payload = {
                'product_id': product.product_id,
                'store_id': store.store_id,
                'scenario_name': name,
                'simulated_stock': stock,
                'selling_price': float(product.selling_price),
                'cost_price': float(product.cost_price),
                'discount': 0,
                'simulation_days': 7
            }
            res = client.post('/api/simulation', json=payload)
            body = json.loads(res.data)
            print(f"\nScenario '{name}' stock={stock}:")
            print(f"  HTTP {res.status_code}")
            print(f"  success={body.get('success')}  message={body.get('message','')}")
            if body.get('success'):
                sim_data = body.get('data', {})
                print(f"  simulation_id={sim_data.get('simulation_id')}")
                print(f"  expected_sales={sim_data.get('expected_sales')}")
                print(f"  expected_revenue={sim_data.get('expected_revenue')}")
                print(f"  expected_profit={sim_data.get('expected_profit')}")
                print(f"  expected_stockout={sim_data.get('expected_stockout')}")
                print(f"  expected_overstock={sim_data.get('expected_overstock')}")
                sim_ids.append(sim_data['simulation_id'])
            else:
                print(f"  FULL RESPONSE: {json.dumps(body, indent=2)}")

        print(f"\nsim_ids collected: {sim_ids}")

        if len(sim_ids) >= 2:
            print("\n" + "=" * 60)
            print("STEP 3 — Compare scenarios")
            print("=" * 60)
            cmp_res = client.post('/api/simulations/compare', json={'simulation_ids': sim_ids})
            cmp_body = json.loads(cmp_res.data)
            print(f"HTTP {cmp_res.status_code}")
            print(f"success={cmp_body.get('success')}")
            if cmp_body.get('success'):
                print(f"best_scenario={cmp_body.get('best_scenario')}")
                print(f"comparison rows: {len(cmp_body.get('comparison', []))}")
                for row in cmp_body.get('comparison', []):
                    print(f"  {row.get('scenario_name')} | stock={row.get('simulated_stock')} | "
                          f"sales={row.get('expected_sales')} | revenue={row.get('expected_revenue')} | "
                          f"profit={row.get('expected_profit')} | score={row.get('score')} | "
                          f"rec={row.get('recommended')}")
                print(f"\nFull compare JSON keys: {list(cmp_body.keys())}")
            else:
                print(f"FULL ERROR: {json.dumps(cmp_body, indent=2)}")

    print("\n" + "=" * 60)
    print("STEP 4 — Verify inventory NOT modified")
    print("=" * 60)
    if inv:
        db.session.refresh(inv)
        print(f"Inventory after simulation: {inv.current_stock} (was {initial_stock})")
        if inv.current_stock == initial_stock:
            print("OK — inventory unchanged.")
        else:
            print("ERROR — inventory was MODIFIED by simulation!")
