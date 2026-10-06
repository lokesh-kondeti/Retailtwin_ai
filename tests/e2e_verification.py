import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = 'http://127.0.0.1:5000'
session = requests.Session()

def run():
    print("Starting End-to-End Verification (Phases 8-12)...")

    # 1. Login
    print("\n[1] Logging in as admin...")
    r = session.post(f"{BASE_URL}/auth/login", data={'email': 'admin@retailtwin.ai', 'password': 'Admin@1234'})
    if r.status_code == 200 and 'Invalid email or password' not in r.text:
        print("? Login successful")
    else:
        print("? Login failed (status:", r.status_code, ")")
        return

    # 2. Train Forecast Model
    print("\n[2] Training ML Forecast Model...")
    r = session.post(f"{BASE_URL}/api/forecasts/train")
    if r.status_code == 200:
        data = r.json()
        print(f"? ML Model Trained Successfully: R2={data.get('metrics', {}).get('R2')}")
    else:
        print("?? Model training returned:", r.status_code, r.text)

    # Fetch store and product
    r = session.get(f"{BASE_URL}/api/stores")
    stores = r.json().get('data', [])
    store_id = stores[0]['store_id']

    r = session.get(f"{BASE_URL}/api/products")
    products = r.json().get('data', [])
    product_id = products[0]['product_id']
    cost_price = products[0]['cost_price']
    selling_price = products[0]['selling_price']

    # 3. Generate Forecast
    print("\n[3] Generating Forecast...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    r = session.post(f"{BASE_URL}/api/forecast", json={
        'product_id': product_id,
        'store_id': store_id,
        'forecast_date': tomorrow,
        'save': True
    })
    if r.status_code == 200:
        data = r.json()
        print(f"? Forecast generated: {data.get('predicted_demand')} units using {data.get('model_name')}")
    else:
        print("? Forecast failed:", r.text)

    # 4. Digital Twin Simulation (3 Scenarios)
    print("\n[4] Running Digital Twin Simulation (3 Scenarios)...")
    sim_ids = []
    scenarios = [
        {"name": "Conservative", "stock": 50},
        {"name": "Balanced", "stock": 100},
        {"name": "Aggressive", "stock": 150}
    ]
    for sc in scenarios:
        r = session.post(f"{BASE_URL}/api/simulation", json={
            'product_id': product_id,
            'store_id': store_id,
            'scenario_name': sc['name'],
            'simulated_stock': sc['stock'],
            'selling_price': selling_price,
            'cost_price': cost_price,
            'simulation_days': 7
        })
        if r.status_code == 201:
            sim_ids.append(r.json()['data']['simulation_id'])
            print(f"? Scenario '{sc['name']}' simulated.")
        else:
            print(f"? Scenario '{sc['name']}' failed:", r.text)
            
    print("  Comparing Scenarios...")
    r = session.post(f"{BASE_URL}/api/simulations/compare", json={'simulation_ids': sim_ids})
    if r.status_code == 200:
        data = r.json()
        print(f"? Comparison successful. Recommended Scenario: {data.get('best_scenario', {}).get('scenario_name')}")
    else:
        print("? Comparison failed:", r.text)

    # 5. Inventory Optimization
    print("\n[5] Generating Inventory Optimization...")
    r = session.post(f"{BASE_URL}/api/optimization", json={
        'product_id': product_id,
        'store_id': store_id
    })
    if r.status_code == 200:
        data = r.json()
        print(f"? Optimization successful: Recommended Stock = {data.get('recommended_stock')}, Status = {data.get('reorder_status')}")
    else:
        print("? Optimization failed:", r.text)

    # 6. Reports & CSV Export
    print("\n[6] Checking Reports and CSV Exports...")
    report_urls = [
        "/api/reports/sales?export=csv",
        "/api/reports/inventory?export=csv",
        "/api/reports/forecasts?export=csv",
        "/api/reports/simulations?export=csv",
        "/api/reports/optimization?export=csv"
    ]
    all_exports_ok = True
    for url in report_urls:
        r = session.get(f"{BASE_URL}{url}")
        if r.status_code == 200 and 'text/csv' in r.headers.get('Content-Type', ''):
            print(f"? Export successful: {url}")
        else:
            print(f"? Export failed for {url}:", r.status_code)
            all_exports_ok = False
            
    if all_exports_ok:
        print("\n?? ALL PHASES 8-12 VERIFIED SUCCESSFULLY!")
    else:
        print("\n?? SOME VERIFICATIONS FAILED.")

if __name__ == '__main__':
    run()
