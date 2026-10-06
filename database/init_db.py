"""
RetailTwin AI — Database Initialization Script
Run this script ONCE to create the database, tables, and seed data.

Usage:
    python database/init_db.py

Requires:
    - MySQL running on 127.0.0.1:3306
    - .env file with MYSQL_PASSWORD set
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

DB_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('MYSQL_PORT', 3306))
DB_USER = os.environ.get('MYSQL_USER', 'root')
DB_PASS = os.environ.get('MYSQL_PASSWORD', '')
DB_NAME = os.environ.get('MYSQL_DATABASE', 'RetailTwin_AI')

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
SEED_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed.sql')


def connect_no_db():
    """Connect to MySQL without selecting a database."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        charset='utf8mb4',
        autocommit=True
    )


def connect_db():
    """Connect to MySQL and select RetailTwin_AI."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4',
        autocommit=True
    )


def run_sql_file(conn, filepath):
    """Execute a SQL file, splitting on semicolons."""
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    # Split statements and execute non-empty ones
    statements = [s.strip() for s in raw.split(';') if s.strip()]
    with conn.cursor() as cursor:
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except pymysql.err.OperationalError as e:
                # Ignore "table already exists" and similar non-critical errors
                print(f"  [WARN] {e}")
            except Exception as e:
                print(f"  [ERROR] Failed on statement:\n  {stmt[:120]}...\n  Reason: {e}")
                raise


def generate_real_password_hashes(conn):
    """
    Replace the placeholder password hashes in seed.sql with real Werkzeug hashes.
    This runs after seed.sql is executed so the database has correct hashes.
    """
    credentials = [
        ('admin@retailtwin.ai',    'Admin@1234'),
        ('manager1@retailtwin.ai', 'Manager@1234'),
        ('manager2@retailtwin.ai', 'Manager@1234'),
    ]
    with conn.cursor() as cursor:
        for email, plain_password in credentials:
            real_hash = generate_password_hash(plain_password)
            cursor.execute(
                "UPDATE USER SET password_hash = %s WHERE email = %s",
                (real_hash, email)
            )
            print(f"  Updated password hash for {email}")


def main():
    print("=" * 60)
    print("RetailTwin AI — Database Initialization")
    print("=" * 60)
    print(f"  Host     : {DB_HOST}:{DB_PORT}")
    print(f"  User     : {DB_USER}")
    print(f"  Database : {DB_NAME}")
    print()

    if DB_PASS == 'YOUR_MYSQL_PASSWORD_HERE' or not DB_PASS:
        print("[ERROR] MYSQL_PASSWORD is not set in your .env file.")
        print("  Open retail_twin_ai/.env and set your MySQL root password.")
        sys.exit(1)

    # Step 1: Connect without database to create it
    print("[1/4] Connecting to MySQL...")
    try:
        conn_root = connect_no_db()
        print("  MySQL connection successful.")
    except pymysql.err.OperationalError as e:
        print(f"[ERROR] Cannot connect to MySQL: {e}")
        print("  Make sure MySQL is running and your credentials are correct in .env")
        sys.exit(1)

    # Step 2: Run schema.sql (creates DB + tables)
    print(f"\n[2/4] Running schema.sql...")
    run_sql_file(conn_root, SCHEMA_FILE)
    conn_root.close()
    print("  Schema applied successfully.")

    # Step 3: Run seed.sql (sample data)
    print(f"\n[3/4] Running seed.sql...")
    conn_db = connect_db()
    run_sql_file(conn_db, SEED_FILE)
    print("  Seed data loaded successfully.")

    # Step 4: Fix password hashes (Werkzeug real hashes)
    print(f"\n[4/4] Generating correct password hashes...")
    generate_real_password_hashes(conn_db)
    conn_db.close()

    print("\n" + "=" * 60)
    print("Database initialization COMPLETE.")
    print()
    print("Test Credentials:")
    print("  Admin   : admin@retailtwin.ai    / Admin@1234")
    print("  Manager : manager1@retailtwin.ai / Manager@1234")
    print("=" * 60)


if __name__ == '__main__':
    main()
