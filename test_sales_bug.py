import sys
import os
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath('app.py')))

from app import create_app
from models import db
from models.sales import Sales
from models.inventory import Inventory
from models.product import Product
from models.store import Store

app = create_app()

def run_tests():
    with app.app_context():
        store = Store.query.filter_by(store_name='RetailTwin Main Store').first()
        product = Product.query.filter_by(product_name='Verification Milk').first()
        
        if not store or not product:
            print("Store or Product not found.")
            return

        inventory = Inventory.query.filter_by(store_id=store.store_id, product_id=product.product_id).first()
        initial_stock = inventory.current_stock
        print(f"Initial Stock: {initial_stock}")

        print("\n--- TEST 1: RECORD ONE NEW SALE ---")
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                
            payload = {
                'store_id': store.store_id,
                'product_id': product.product_id,
                'sale_date': date.today().isoformat(),
                'quantity_sold': 1,
                'discount': 0
            }
            res = client.post('/api/sales', json=payload)
            data = res.get_json()
            assert data['success'] is True, f"Sale failed: {data}"
            print("A. Sale succeeds: True")
            
            # Verify inventory
            inv_after = Inventory.query.filter_by(store_id=store.store_id, product_id=product.product_id).first()
            assert inv_after.current_stock == initial_stock - 1, "B. Inventory did not decrease by exactly 1"
            print(f"B. Inventory decreased by exactly 1: True (Now {inv_after.current_stock})")
            
            # Verify Sales record
            new_sale = Sales.query.order_by(Sales.sale_id.desc()).first()
            assert new_sale.quantity_sold == 1, "F. Quantity incorrect"
            assert new_sale.product_id == product.product_id, "D. Product incorrect"
            assert new_sale.store_id == store.store_id, "E. Store incorrect"
            print("C-F. New record created with correct product, store, qty.")
            print(f"G-I. Price: {new_sale.selling_price}, Cost: {new_sale.cost_price}, Discount: {new_sale.discount}")
            print(f"J. Revenue: {new_sale.revenue}")
            print(f"K. Sale Date: {new_sale.sale_date}")
            
            # Verify Sales History API
            res_list = client.get('/api/sales?limit=10')
            list_data = res_list.get_json()['data']
            top_sale_id = list_data[0]['sale_id']
            # If the date is today, and there's a future date, the new sale might be #2.
            # We fixed the order by sale_date DESC, created_at DESC.
            # Wait, if there's a future date (2026-08-22), the new sale (2026-08-21) will be below it!
            found_in_history = any(s['sale_id'] == new_sale.sale_id for s in list_data)
            print(f"L. Transaction appears in Sales History API top 10: {found_in_history}")
            
        print("\n--- TEST 2: RECORD TWO MORE SALES ---")
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                
            payload1 = {'store_id': store.store_id, 'product_id': product.product_id, 'sale_date': date.today().isoformat(), 'quantity_sold': 1, 'discount': 0}
            payload2 = {'store_id': store.store_id, 'product_id': product.product_id, 'sale_date': date.today().isoformat(), 'quantity_sold': 2, 'discount': 0}
            
            client.post('/api/sales', json=payload1)
            client.post('/api/sales', json=payload2)
            
            inv_final = Inventory.query.filter_by(store_id=store.store_id, product_id=product.product_id).first()
            print(f"Inventory after 2 more sales: {inv_final.current_stock} (Expected: {initial_stock - 4})")
            
            res_list = client.get('/api/sales?limit=20')
            list_data = res_list.get_json()['data']
            
            # Get latest 3 sales from DB
            latest_sales = Sales.query.order_by(Sales.sale_id.desc()).limit(3).all()
            for s in latest_sales:
                found = any(ld['sale_id'] == s.sale_id for ld in list_data)
                print(f"Sale ID {s.sale_id} found in History: {found}")
                
        print("\n--- TEST 6: FAILURE / ROLLBACK ---")
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                
            inv_before_fail = Inventory.query.filter_by(store_id=store.store_id, product_id=product.product_id).first().current_stock
            sales_count_before = Sales.query.count()
            
            payload_fail = {
                'store_id': store.store_id,
                'product_id': product.product_id,
                'sale_date': date.today().isoformat(),
                'quantity_sold': 999999, # more than available
                'discount': 0
            }
            res_fail = client.post('/api/sales', json=payload_fail)
            data_fail = res_fail.get_json()
            print(f"Failed sale response: {data_fail}")
            
            inv_after_fail = Inventory.query.filter_by(store_id=store.store_id, product_id=product.product_id).first().current_stock
            sales_count_after = Sales.query.count()
            
            assert inv_before_fail == inv_after_fail, "Inventory changed on failed sale!"
            assert sales_count_before == sales_count_after, "Sales count changed on failed sale!"
            print("Rollback successful. Inventory and Sales unchanged.")

if __name__ == '__main__':
    run_tests()
