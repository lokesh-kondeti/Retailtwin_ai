import pytest
import json
import uuid
from datetime import datetime, date, timedelta
from app import create_app
from models import db
from models.user import User
from models.product import Product
from models.category import Category
from models.store import Store
from models.inventory import Inventory
from models.sales import Sales
from models.demand_forecast import DemandForecast
from models.digital_twin import DigitalTwinSimulation

@pytest.fixture(scope='module')
def test_client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client

def login(client, email, password):
    return client.post('/auth/api/auth/login', json={'email': email, 'password': password})

def logout(client):
    return client.post('/auth/api/auth/logout')

class TestComprehensive:

    def test_01_authentication(self, test_client):
        res = login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        assert res.status_code == 200
        
        logout(test_client)
        res = login(test_client, 'manager1@retailtwin.ai', 'Manager@1234')
        assert res.status_code == 200
        
        logout(test_client)
        res = test_client.get('/api/dashboard', follow_redirects=True)
        assert res.status_code in [401, 403, 200]

    def test_02_category_crud(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        cat_name = f"Test Category {uuid.uuid4().hex[:8]}"
        res = test_client.post('/api/categories', json={'category_name': cat_name, 'description': 'Temp'})
        assert res.status_code == 201
        cat_id = json.loads(res.data)['data']['category_id']
        
        res = test_client.put(f'/api/categories/{cat_id}', json={'category_name': f"{cat_name} Edited", 'description': 'Temp'})
        assert res.status_code == 200
        
        res = test_client.delete(f'/api/categories/{cat_id}')
        assert res.status_code == 200

    def test_03_store_crud(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        store_name = f"Test Store {uuid.uuid4().hex[:8]}"
        res = test_client.post('/api/stores', json={'store_name': store_name, 'location': 'Temp'})
        assert res.status_code == 201
        store_id = json.loads(res.data)['data']['store_id']
        
        res = test_client.put(f'/api/stores/{store_id}', json={'store_name': f"{store_name} Edited", 'location': 'Temp'})
        assert res.status_code == 200
        
        res = test_client.delete(f'/api/stores/{store_id}')
        assert res.status_code == 200

    def test_04_product_and_inventory(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        cat_name = f"Temp Cat {uuid.uuid4().hex[:8]}"
        res = test_client.post('/api/categories', json={'category_name': cat_name, 'description': 'desc'})
        cat_id = json.loads(res.data)['data']['category_id']
        
        res = test_client.post('/api/products', json={
            'product_name': f'Test Product {uuid.uuid4().hex[:8]}',
            'category_id': cat_id,
            'cost_price': 100,
            'selling_price': 90,
            'lead_time': 2,
            'expiry_days': 10
        })
        assert res.status_code == 400
        
        prod_name = f'Test Product {uuid.uuid4().hex[:8]}'
        res = test_client.post('/api/products', json={
            'product_name': prod_name,
            'category_id': cat_id,
            'cost_price': 100,
            'selling_price': 150,
            'lead_time': 2,
            'expiry_days': 10
        })
        assert res.status_code == 201
        prod_id = json.loads(res.data)['data']['product_id']
        
        res = test_client.put(f'/api/products/{prod_id}', json={
            'product_name': prod_name,
            'category_id': cat_id,
            'cost_price': 110,
            'selling_price': 160,
            'lead_time': 2,
            'expiry_days': 10
        })
        assert res.status_code == 200
        
        store_name = f"Inv Store {uuid.uuid4().hex[:8]}"
        res = test_client.post('/api/stores', json={'store_name': store_name, 'location': 'Loc'})
        store_id = json.loads(res.data)['data']['store_id']
        
        inv = Inventory(product_id=prod_id, store_id=store_id, current_stock=5, minimum_stock=10, maximum_stock=100, reorder_level=15)
        db.session.add(inv)
        db.session.commit()
        assert inv.stock_status in ['LOW_STOCK', 'LOW']
        
        inv.current_stock = 0
        assert inv.stock_status == 'OUT_OF_STOCK'
        
        inv.current_stock = 150
        assert inv.stock_status == 'OVERSTOCK'
        
        inv.current_stock = 50
        assert inv.stock_status == 'NORMAL'

        db.session.delete(inv)
        db.session.commit()
        test_client.delete(f'/api/products/{prod_id}')
        test_client.delete(f'/api/stores/{store_id}')
        test_client.delete(f'/api/categories/{cat_id}')

    def test_05_sales(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        cat_name = f"Sales Cat {uuid.uuid4().hex[:8]}"
        res = test_client.post('/api/categories', json={'category_name': cat_name, 'description': 'desc'})
        cat_id = json.loads(res.data)['data']['category_id']
        
        store_name = f"Sales Store {uuid.uuid4().hex[:8]}"
        res = test_client.post('/api/stores', json={'store_name': store_name, 'location': 'Loc'})
        store_id = json.loads(res.data)['data']['store_id']
        
        res = test_client.post('/api/products', json={
            'product_name': f'Sales Prod {uuid.uuid4().hex[:8]}', 'category_id': cat_id,
            'cost_price': 100, 'selling_price': 150
        })
        prod_id = json.loads(res.data)['data']['product_id']
        
        inv = Inventory(product_id=prod_id, store_id=store_id, current_stock=100, minimum_stock=10, maximum_stock=200, reorder_level=20)
        db.session.add(inv)
        db.session.commit()

        res = test_client.post('/api/sales', json={
            'product_id': prod_id,
            'store_id': store_id,
            'sale_date': date.today().isoformat(),
            'quantity_sold': 10,
            'selling_price': 150,
            'discount': 10
        })
        assert res.status_code == 201
        
        db.session.refresh(inv)
        assert inv.current_stock == 90
        
        sale = Sales.query.filter_by(product_id=prod_id).first()
        assert float(sale.cost_price) == 100.0
        assert float(sale.selling_price) == 150.0
        assert float(sale.revenue) == 1350.0

        res = test_client.post('/api/sales', json={
            'product_id': prod_id,
            'store_id': store_id,
            'sale_date': date.today().isoformat(),
            'quantity_sold': 100,
            'selling_price': 150,
            'discount': 0
        })
        assert res.status_code in [400, 409] 
        db.session.refresh(inv)
        assert inv.current_stock == 90 
        
        db.session.delete(sale)
        db.session.delete(inv)
        db.session.commit()
        test_client.delete(f'/api/products/{prod_id}')
        test_client.delete(f'/api/stores/{store_id}')
        test_client.delete(f'/api/categories/{cat_id}')

    def test_06_dashboard(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        res = test_client.get('/api/dashboard')
        assert res.status_code == 200
        
    def test_07_forecasting(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        res = test_client.post('/api/forecasts/train')
        assert res.status_code in [200, 400] 

        prod = Product.query.first()
        store = Store.query.first()
        
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        res = test_client.post('/api/forecast', json={
            'product_id': prod.product_id,
            'store_id': store.store_id,
            'forecast_date': tomorrow,
            'save': True
        })
        assert res.status_code == 200

    def test_08_digital_twin(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        prod = Product.query.first()
        store = Store.query.first()
        
        sim_ids = []
        for name, stock in [('Conservative', 10), ('Balanced', 50), ('Aggressive', 100)]:
            res = test_client.post('/api/simulation', json={
                'product_id': prod.product_id,
                'store_id': store.store_id,
                'scenario_name': name,
                'simulated_stock': stock,
                'selling_price': float(prod.selling_price),
                'cost_price': float(prod.cost_price),
                'simulation_days': 7
            })
            assert res.status_code == 201
            sim_ids.append(json.loads(res.data)['data']['simulation_id'])
            
        res = test_client.post('/api/simulations/compare', json={'simulation_ids': sim_ids})
        assert res.status_code == 200

    def test_09_optimization(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        prod = Product.query.first()
        store = Store.query.first()
        
        res = test_client.post('/api/optimization', json={
            'product_id': prod.product_id,
            'store_id': store.store_id
        })
        assert res.status_code == 200

    def test_10_reports(self, test_client):
        login(test_client, 'admin@retailtwin.ai', 'Admin@1234')
        urls = [
            '/api/reports/sales',
            '/api/reports/inventory',
            '/api/reports/forecasts',
            '/api/reports/simulations',
            '/api/reports/optimization'
        ]
        
        for url in urls:
            res = test_client.get(url)
            assert res.status_code == 200
            
        for url in urls:
            res = test_client.get(url + '?export=csv')
            assert res.status_code == 200
