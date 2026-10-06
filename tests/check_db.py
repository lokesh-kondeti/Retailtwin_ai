import pymysql
import os
from dotenv import load_dotenv

load_dotenv()
conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'RetailTwin_AI'),
    charset='utf8mb4',
    autocommit=True
)
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT product_id FROM PRODUCT WHERE product_name LIKE '%Test Milk%' ORDER BY product_id DESC LIMIT 1")
pid = cursor.fetchone()['product_id']

print("--- SALES ---")
cursor.execute("SELECT sale_id, quantity_sold, created_at FROM SALES WHERE product_id=%s ORDER BY created_at ASC", (pid,))
for row in cursor.fetchall():
    print(f"Sale {row['sale_id']}: qty={row['quantity_sold']}, time={row['created_at']}")

print("--- INVENTORY UPDATES (We only have last_updated) ---")
cursor.execute("SELECT inventory_id, current_stock, last_updated FROM INVENTORY WHERE product_id=%s", (pid,))
inv = cursor.fetchone()
print(f"Inventory {inv['inventory_id']}: stock={inv['current_stock']}, time={inv['last_updated']}")

conn.close()
