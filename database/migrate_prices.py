import pymysql
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'RetailTwin_AI'),
    charset='utf8mb4',
    autocommit=True
)

cursor = conn.cursor()

# 1. Alter PRODUCT table
try:
    cursor.execute("ALTER TABLE PRODUCT CHANGE price selling_price DECIMAL(10,2) NOT NULL;")
    print("Renamed price to selling_price in PRODUCT")
except Exception as e:
    print(f"PRODUCT rename error: {e}")

try:
    cursor.execute("ALTER TABLE PRODUCT ADD COLUMN cost_price DECIMAL(10,2) NOT NULL AFTER category_id;")
    print("Added cost_price to PRODUCT")
except Exception as e:
    print(f"PRODUCT add column error: {e}")

# 2. Explicit realistic cost prices for seed data
product_costs = {
    'Full Cream Milk 1L': 40.00,
    'Fresh Eggs (Tray of 30)': 140.00,
    'Butter 500g': 190.00,
    'Basmati Rice 5kg': 260.00,
    'Wheat Flour 5kg': 140.00,
    'Brown Bread Loaf': 35.00,
    'Sugar 1kg': 35.00,
    'Refined Cooking Oil 1L': 105.00,
    'Iodized Salt 1kg': 15.00,
    'Masala Tea 500g': 150.00,
    'Instant Coffee 200g': 230.00,
    'Cream Biscuits 200g': 22.00,
    'Salted Chips 100g': 15.00,
    'Tomatoes 1kg': 25.00,
    'Potatoes 1kg': 20.00
}

for name, cost in product_costs.items():
    cursor.execute("UPDATE PRODUCT SET cost_price = %s WHERE product_name = %s", (cost, name))

# Set any remaining unknown products (if any were manually added) to 75% as fallback
cursor.execute("UPDATE PRODUCT SET cost_price = selling_price * 0.75 WHERE cost_price = 0.00;")

# 3. Alter SALES table
try:
    cursor.execute("ALTER TABLE SALES ADD COLUMN cost_price DECIMAL(10,2) NOT NULL AFTER quantity_sold;")
    print("Added cost_price to SALES")
except Exception as e:
    print(f"SALES add column error: {e}")

# Sync existing SALES with historical cost price
cursor.execute("""
    UPDATE SALES s
    JOIN PRODUCT p ON s.product_id = p.product_id
    SET s.cost_price = p.cost_price
    WHERE s.cost_price = 0.00;
""")

conn.close()
print("Migration completed safely.")
