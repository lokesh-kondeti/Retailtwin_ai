import urllib.request
import urllib.parse
import json
import sys

base_url = "http://127.0.0.1:5000"

# Setup session with cookie processor
cookie_jar = urllib.request.HTTPCookieProcessor()
opener = urllib.request.build_opener(cookie_jar)
urllib.request.install_opener(opener)

def request(method, path, data=None):
    url = f"{base_url}{path}"
    headers = {}
    if data is not None:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")
        return None

print("1. Login...")
login_data = urllib.parse.urlencode({'email': 'admin@retailtwin.ai', 'password': 'Admin@1234'}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/login", data=login_data)
urllib.request.urlopen(req)

print("2. Create Test Milk...")
create_res = request('POST', '/api/products', {
    "product_name": "Test Milk",
    "category_id": 1,
    "cost_price": 30.00,
    "selling_price": 42.00,
    "lead_time": 2,
    "expiry_days": 7
})
if not create_res or not create_res['success']:
    print("Failed to create product")
    sys.exit(1)
product_id = create_res['data']['product_id']
print(f"   Created Product ID: {product_id}")

print("3. Edit Test Milk...")
edit_res = request('PUT', f'/api/products/{product_id}', {
    "product_name": "Test Milk Updated",
    "category_id": 1,
    "cost_price": 30.00,
    "selling_price": 42.00,
    "lead_time": 2,
    "expiry_days": 7
})
p_data = edit_res['data']
assert p_data['cost_price'] == 30.0, "Cost price mismatch"
assert p_data['selling_price'] == 42.0, "Selling price mismatch"
print("   Edit successful, prices retained.")

print("4. Add Inventory (to allow sale)...")
inv_res = request('POST', '/api/inventory', {
    "product_id": product_id,
    "store_id": 1,
    "current_stock": 100,
    "minimum_stock": 10,
    "maximum_stock": 200,
    "reorder_level": 20
})
assert inv_res['success'], "Failed to add inventory"

print("5. Record Sale (10 units)...")
sale_res = request('POST', '/api/sales', {
    "product_id": product_id,
    "store_id": 1,
    "quantity_sold": 10,
    "selling_price": 42.00,
    "sale_date": "2026-08-18"
})
s_data = sale_res['data']
assert s_data['revenue'] == 420.0, f"Expected 420, got {s_data['revenue']}"
assert s_data['cost_price'] == 30.0, f"Expected cost 30, got {s_data.get('cost_price')}"
profit = s_data['revenue'] - (s_data['quantity_sold'] * s_data['cost_price'])
assert profit == 120.0, f"Expected profit 120, got {profit}"
print(f"   Sale successful! Revenue: {s_data['revenue']}, Profit: {profit}")

print("6. Verify Inventory Decreased...")
inv_list = request('GET', '/api/inventory?store_id=1')
inv_record = next(i for i in inv_list['data'] if i['product_id'] == product_id)
assert inv_record['current_stock'] == 90, f"Expected 90, got {inv_record['current_stock']}"
print("   Inventory correctly decreased to 90.")

print("7. Verify Dashboard...")
dash_res = request('GET', '/api/dashboard')
assert dash_res['success'], "Dashboard failed"
print("   Dashboard OK!")

print("8. Verify Digital Twin...")
sim_res = request('POST', '/api/simulation', {
    "product_id": product_id,
    "store_id": 1,
    "scenario_name": "Test Scenario",
    "simulated_stock": 50,
    "cost_price": 30.00,
    "selling_price": 42.00,
    "simulation_days": 7
})
sim_data = sim_res['data']
# Expected units sold might vary if historical avg is very low, but it will use prices.
print(f"   Simulated Profit: {sim_data['expected_profit']}")

print("All tests passed successfully!")
