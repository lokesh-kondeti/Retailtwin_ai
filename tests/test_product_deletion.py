import pytest
import json
import uuid
from datetime import date
from app import create_app
from models import db
from models.product import Product
from models.category import Category
from models.store import Store
from models.demand_forecast import DemandForecast
from models.sales import Sales
from tests.test_comprehensive import login

@pytest.fixture(scope='module')
def test_client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_product_deletion_with_forecast_only(test_client):
    login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
    
    # 1. Create Category
    res = test_client.post('/api/categories', json={'category_name': 'Forecast Cat', 'description': 'desc'})
    cat_id = json.loads(res.data)['data']['category_id']
    
    # 2. Create Store
    res = test_client.post('/api/stores', json={'store_name': 'Forecast Store', 'location': 'Loc'})
    store_id = json.loads(res.data)['data']['store_id']
    
    # 3. Create Product
    res = test_client.post('/api/products', json={
        'product_name': f'Forecast Prod {uuid.uuid4().hex[:8]}', 'category_id': cat_id,
        'cost_price': 100, 'selling_price': 150
    })
    prod_id = json.loads(res.data)['data']['product_id']
    
    # 4. Add DemandForecast manually
    forecast = DemandForecast(product_id=prod_id, store_id=store_id, forecast_date=date.today(), predicted_demand=50.0)
    db.session.add(forecast)
    db.session.commit()
    
    # 5. Delete Product (Should succeed because it ONLY has forecast)
    res = test_client.delete(f'/api/products/{prod_id}')
    assert res.status_code == 200
    assert json.loads(res.data)['success'] is True
    
    # Cleanup
    test_client.delete(f'/api/stores/{store_id}')
    test_client.delete(f'/api/categories/{cat_id}')


def test_product_deletion_with_sales(test_client):
    login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
    
    # 1. Create Category
    res = test_client.post('/api/categories', json={'category_name': 'Sales Cat 2', 'description': 'desc'})
    cat_id = json.loads(res.data)['data']['category_id']
    
    # 2. Create Store
    res = test_client.post('/api/stores', json={'store_name': 'Sales Store 2', 'location': 'Loc'})
    store_id = json.loads(res.data)['data']['store_id']
    
    # 3. Create Product
    res = test_client.post('/api/products', json={
        'product_name': f'Sales Prod {uuid.uuid4().hex[:8]}', 'category_id': cat_id,
        'cost_price': 100, 'selling_price': 150
    })
    prod_id = json.loads(res.data)['data']['product_id']
    
    # 4. Add Sales manually (no forecast)
    sale = Sales(product_id=prod_id, store_id=store_id, sale_date=date.today(), quantity_sold=10, selling_price=150, cost_price=100, revenue=1500)
    db.session.add(sale)
    db.session.commit()
    
    # 5. Delete Product (Should FAIL with 409 because it has Sales)
    res = test_client.delete(f'/api/products/{prod_id}')
    assert res.status_code == 409
    assert 'Historical sales records exist' in json.loads(res.data)['message']
    
    # Cleanup (manual)
    db.session.delete(sale)
    db.session.commit()
    test_client.delete(f'/api/products/{prod_id}')
    test_client.delete(f'/api/stores/{store_id}')
    test_client.delete(f'/api/categories/{cat_id}')
