import re

file_path = 'database/seed.sql'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace PRODUCT table insert signature
content = content.replace(
    'INSERT IGNORE INTO PRODUCT (product_name, category_id, price, lead_time, expiry_days, created_at) VALUES',
    'INSERT IGNORE INTO PRODUCT (product_name, category_id, cost_price, selling_price, lead_time, expiry_days, created_at) VALUES'
)

# Replace PRODUCT entries
product_replacements = [
    ("('Full Cream Milk 1L',      1,  52.00,  1,   5,  NOW()),", "('Full Cream Milk 1L',      1,  40.00,  52.00,  1,   5,  NOW()),"),
    ("('Fresh Eggs (Tray of 30)', 1,  180.00, 2,  15,  NOW()),", "('Fresh Eggs (Tray of 30)', 1, 140.00, 180.00, 2,  15,  NOW()),"),
    ("('Butter 500g',             1,  235.00, 3,  90,  NOW()),", "('Butter 500g',             1, 190.00, 235.00, 3,  90,  NOW()),"),
    ("('Basmati Rice 5kg',        2,  320.00, 5, 365,  NOW()),", "('Basmati Rice 5kg',        2, 260.00, 320.00, 5, 365,  NOW()),"),
    ("('Wheat Flour 5kg',         2,  180.00, 4, 180,  NOW()),", "('Wheat Flour 5kg',         2, 140.00, 180.00, 4, 180,  NOW()),"),
    ("('Brown Bread Loaf',        2,   45.00, 1,   5,  NOW()),", "('Brown Bread Loaf',        2,  35.00,  45.00, 1,   5,  NOW()),"),
    ("('Sugar 1kg',               3,   45.00, 3, 730,  NOW()),", "('Sugar 1kg',               3,  35.00,  45.00, 3, 730,  NOW()),"),
    ("('Refined Cooking Oil 1L',  3,  130.00, 4, 365,  NOW()),", "('Refined Cooking Oil 1L',  3, 105.00, 130.00, 4, 365,  NOW()),"),
    ("('Iodized Salt 1kg',        3,   22.00, 5, 730,  NOW()),", "('Iodized Salt 1kg',        3,  15.00,  22.00, 5, 730,  NOW()),"),
    ("('Masala Tea 500g',         4,  195.00, 5, 365,  NOW()),", "('Masala Tea 500g',         4, 150.00, 195.00, 5, 365,  NOW()),"),
    ("('Instant Coffee 200g',     4,  299.00, 5, 365,  NOW()),", "('Instant Coffee 200g',     4, 230.00, 299.00, 5, 365,  NOW()),"),
    ("('Cream Biscuits 200g',     5,   30.00, 3, 120,  NOW()),", "('Cream Biscuits 200g',     5,  22.00,  30.00, 3, 120,  NOW()),"),
    ("('Salted Chips 100g',       5,   20.00, 3,  60,  NOW()),", "('Salted Chips 100g',       5,  15.00,  20.00, 3,  60,  NOW()),"),
    ("('Tomatoes 1kg',            6,   35.00, 1,   5,  NOW()),", "('Tomatoes 1kg',            6,  25.00,  35.00, 1,   5,  NOW()),"),
    ("('Potatoes 1kg',            6,   28.00, 2,  14,  NOW());", "('Potatoes 1kg',            6,  20.00,  28.00, 2,  14,  NOW());")
]

for old, new in product_replacements:
    content = content.replace(old, new)

# Replace SALES table insert signature
content = content.replace(
    'INSERT INTO SALES (product_id, store_id, sale_date, quantity_sold, selling_price, discount, revenue) VALUES',
    'INSERT INTO SALES (product_id, store_id, sale_date, quantity_sold, cost_price, selling_price, discount, revenue) VALUES'
)

# Use regex to inject cost_price for each product
# Product 1 (Milk): 52.00 -> 40.00, 52.00
content = re.sub(r'\(1, (\d+), ([^,]+), (\d+), 52\.00,', r'(1, \1, \2, \3, 40.00, 52.00,', content)
# Product 4 (Rice): 320.00 -> 260.00, 320.00
content = re.sub(r'\(4, (\d+), ([^,]+), (\d+), 320\.00,', r'(4, \1, \2, \3, 260.00, 320.00,', content)
# Product 7 (Sugar): 45.00 -> 35.00, 45.00
content = re.sub(r'\(7, (\d+), ([^,]+), (\d+), 45\.00,', r'(7, \1, \2, \3, 35.00, 45.00,', content)
# Product 10 (Tea): 195.00 -> 150.00, 195.00
content = re.sub(r'\(10, (\d+), ([^,]+), (\d+), 195\.00,', r'(10, \1, \2, \3, 150.00, 195.00,', content)
# Product 12 (Biscuits): 30.00 -> 22.00, 30.00
content = re.sub(r'\(12, (\d+), ([^,]+), (\d+), 30\.00,', r'(12, \1, \2, \3, 22.00, 30.00,', content)
# Product 8 (Cooking Oil): 130.00 -> 105.00, 130.00
content = re.sub(r'\(8, (\d+), ([^,]+), (\d+), 130\.00,', r'(8, \1, \2, \3, 105.00, 130.00,', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("seed.sql updated successfully.")
