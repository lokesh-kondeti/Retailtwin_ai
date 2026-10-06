"""
Regression tests for:
  - Duplicate stores
  - Store deletion
  - Safety of historical data
  - All major modules still working
"""
import pytest
import json
import uuid
from datetime import date
from app import create_app
from models import db
from models.store import Store
from models.product import Product
from models.category import Category
from models.inventory import Inventory
from models.sales import Sales
from models.demand_forecast import DemandForecast


@pytest.fixture(scope='module')
def test_client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client


def login(client, email='admin@retailtwin.ai', password='Admin@1234'):
    return client.post('/auth/api/auth/login', json={'email': email, 'password': password})


# ──────────────────────────────────────────
# TEST 1: Each store appears exactly once
# ──────────────────────────────────────────
def test_01_no_duplicate_stores_in_api(test_client):
    login(test_client)
    res = test_client.get('/api/stores')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success']
    names = [s['store_name'] for s in data['data']]
    assert len(names) == len(set(names)), f"Duplicate store names found in API: {names}"
    print(f"  Stores returned: {names}")


# ──────────────────────────────────────────
# TEST 2: Delete store with NO dependents
# ──────────────────────────────────────────
def test_02_delete_store_no_dependents(test_client):
    login(test_client)
    name = f"TempStore {uuid.uuid4().hex[:8]}"
    res = test_client.post('/api/stores', json={'store_name': name, 'location': 'Test'})
    assert res.status_code == 201
    store_id = json.loads(res.data)['data']['store_id']

    res = test_client.delete(f'/api/stores/{store_id}')
    assert res.status_code == 200
    assert json.loads(res.data)['success'] is True


# ──────────────────────────────────────────
# TEST 3: Delete store WITH inventory → should fail
# ──────────────────────────────────────────
def test_03_delete_store_with_inventory_blocked(test_client):
    login(test_client)

    # Create category and product
    res = test_client.post('/api/categories', json={'category_name': f'Cat {uuid.uuid4().hex[:6]}', 'description': ''})
    cat_id = json.loads(res.data)['data']['category_id']
    res = test_client.post('/api/products', json={
        'product_name': f'Prod {uuid.uuid4().hex[:6]}', 'category_id': cat_id,
        'cost_price': 10, 'selling_price': 15
    })
    prod_id = json.loads(res.data)['data']['product_id']

    name = f"InvStore {uuid.uuid4().hex[:8]}"
    res = test_client.post('/api/stores', json={'store_name': name, 'location': 'Test'})
    store_id = json.loads(res.data)['data']['store_id']

    inv = Inventory(product_id=prod_id, store_id=store_id, current_stock=5,
                    minimum_stock=1, maximum_stock=100, reorder_level=5)
    db.session.add(inv)
    db.session.commit()

    # Attempt delete — must fail
    res = test_client.delete(f'/api/stores/{store_id}')
    assert res.status_code == 409
    msg = json.loads(res.data)['message']
    assert 'inventory' in msg.lower()

    # Cleanup
    db.session.delete(inv)
    db.session.commit()
    test_client.delete(f'/api/stores/{store_id}')
    test_client.delete(f'/api/products/{prod_id}')
    test_client.delete(f'/api/categories/{cat_id}')


# ──────────────────────────────────────────
# TEST 4: Historical SALES must NOT be deleted
# ──────────────────────────────────────────
def test_04_sales_protected_on_store_delete(test_client):
    login(test_client)

    res = test_client.post('/api/categories', json={'category_name': f'SaleCat {uuid.uuid4().hex[:6]}', 'description': ''})
    cat_id = json.loads(res.data)['data']['category_id']
    res = test_client.post('/api/products', json={
        'product_name': f'SaleProd {uuid.uuid4().hex[:6]}', 'category_id': cat_id,
        'cost_price': 10, 'selling_price': 15
    })
    prod_id = json.loads(res.data)['data']['product_id']

    name = f"SaleStore {uuid.uuid4().hex[:8]}"
    res = test_client.post('/api/stores', json={'store_name': name, 'location': 'Test'})
    store_id = json.loads(res.data)['data']['store_id']

    # Manually add a sales record
    sale = Sales(product_id=prod_id, store_id=store_id, sale_date=date.today(),
                 quantity_sold=5, selling_price=15, cost_price=10, revenue=75)
    db.session.add(sale)
    db.session.commit()
    sale_id = sale.sale_id

    # Delete attempt — must fail with 409
    res = test_client.delete(f'/api/stores/{store_id}')
    assert res.status_code == 409
    assert 'sales' in json.loads(res.data)['message'].lower()

    # Verify the sale still exists
    still_exists = db.session.get(Sales, sale_id)
    assert still_exists is not None, "Sale was accidentally deleted!"

    # Cleanup
    db.session.delete(sale)
    db.session.commit()
    test_client.delete(f'/api/stores/{store_id}')
    test_client.delete(f'/api/products/{prod_id}')
    test_client.delete(f'/api/categories/{cat_id}')


# ──────────────────────────────────────────
# TEST 5: Existing canonical stores remain correct
# ──────────────────────────────────────────
def test_05_canonical_stores_intact(test_client):
    login(test_client)
    res = test_client.get('/api/stores')
    data = json.loads(res.data)
    names = {s['store_name'] for s in data['data']}
    assert 'RetailTwin Main Store' in names
    assert 'RetailTwin North Branch' in names
    assert 'RetailTwin West Outlet' in names


# ──────────────────────────────────────────
# TEST 6: Products still work
# ──────────────────────────────────────────
def test_06_products_still_work(test_client):
    login(test_client)
    res = test_client.get('/api/products')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success']
    assert len(data['data']) > 0


# ──────────────────────────────────────────
# TEST 7: Inventory still works
# ──────────────────────────────────────────
def test_07_inventory_still_works(test_client):
    login(test_client)
    res = test_client.get('/api/inventory')
    assert res.status_code == 200
    assert json.loads(res.data)['success']


# ──────────────────────────────────────────
# TEST 8: Sales still work
# ──────────────────────────────────────────
def test_08_sales_still_work(test_client):
    login(test_client)
    res = test_client.get('/api/sales')
    assert res.status_code == 200
    assert json.loads(res.data)['success']


# ──────────────────────────────────────────
# TEST 9: Demand Forecasting still works
# ──────────────────────────────────────────
def test_09_forecasting_still_works(test_client):
    login(test_client)
    res = test_client.post('/api/forecasts/train')
    assert res.status_code in [200, 400]


# ──────────────────────────────────────────
# TEST 10: Digital Twin still works
# ──────────────────────────────────────────
def test_10_digital_twin_still_works(test_client):
    login(test_client)
    prod = Product.query.first()
    store = Store.query.first()
    res = test_client.post('/api/simulation', json={
        'product_id': prod.product_id,
        'store_id': store.store_id,
        'scenario_name': 'RegTest',
        'simulated_stock': 50,
        'selling_price': float(prod.selling_price),
        'cost_price': float(prod.cost_price),
        'simulation_days': 7
    })
    assert res.status_code == 201


# ──────────────────────────────────────────
# TEST 11: Optimization still works
# ──────────────────────────────────────────
def test_11_optimization_still_works(test_client):
    login(test_client)
    prod = Product.query.first()
    store = Store.query.first()
    res = test_client.post('/api/optimization', json={
        'product_id': prod.product_id,
        'store_id': store.store_id
    })
    assert res.status_code == 200


# ──────────────────────────────────────────
# TEST 12: Reports and CSV exports still work
# ──────────────────────────────────────────
def test_12_reports_still_work(test_client):
    login(test_client)
    urls = ['/api/reports/sales', '/api/reports/inventory',
            '/api/reports/forecasts', '/api/reports/simulations',
            '/api/reports/optimization']
    for url in urls:
        res = test_client.get(url)
        assert res.status_code == 200, f"Failed: {url}"
    for url in urls:
        res = test_client.get(url + '?export=csv')
        assert res.status_code == 200, f"CSV Failed: {url}"


# ──────────────────────────────────────────
# TEST 13: Prevent duplicate store creation
# ──────────────────────────────────────────
def test_13_prevent_duplicate_store_name(test_client):
    login(test_client)
    name = f"UniqueStore {uuid.uuid4().hex[:8]}"
    res = test_client.post('/api/stores', json={'store_name': name, 'location': 'Test'})
    assert res.status_code == 201
    store_id = json.loads(res.data)['data']['store_id']

    # Try to create again with same name
    res2 = test_client.post('/api/stores', json={'store_name': name, 'location': 'Other'})
    assert res2.status_code == 409
    assert 'already exists' in json.loads(res2.data)['message']

    # Cleanup
    test_client.delete(f'/api/stores/{store_id}')


# ──────────────────────────────────────────
# TEST 14: Store with only forecasts can be deleted (forecasts removed)
# ──────────────────────────────────────────
def test_14_delete_store_with_forecast_only(test_client):
    login(test_client)
    name = f"ForecastStore {uuid.uuid4().hex[:8]}"
    res = test_client.post('/api/stores', json={'store_name': name, 'location': 'Test'})
    store_id = json.loads(res.data)['data']['store_id']

    prod = Product.query.first()
    fc = DemandForecast(product_id=prod.product_id, store_id=store_id,
                        forecast_date=date.today(), predicted_demand=20.0)
    db.session.add(fc)
    db.session.commit()

    res = test_client.delete(f'/api/stores/{store_id}')
    assert res.status_code == 200
    assert json.loads(res.data)['success'] is True

    # Confirm store is gone
    assert db.session.get(Store, store_id) is None
