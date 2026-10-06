import urllib.request
import urllib.parse
import json
import http.cookiejar

def main():
    print("Starting Workflow Test...")
    
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    base_url = "http://127.0.0.1:5000"
    
    # 1. Test Login (Phase 3)
    login_data = urllib.parse.urlencode({'email': 'admin@retailtwin.ai', 'password': 'Admin@1234'}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/auth/login", data=login_data)
    try:
        response = opener.open(req)
        print("Login Success!")
    except Exception as e:
        print("Login Failed:", e)
        return
        
    # Helper for API GET
    def api_get(endpoint):
        try:
            req = urllib.request.Request(f"{base_url}{endpoint}")
            res = opener.open(req)
            return json.loads(res.read().decode('utf-8'))
        except Exception as e:
            return {"success": False, "error": str(e)}

    # 2. Test Store, Category, Product CRUD (Phase 4)
    stores = api_get("/api/stores")
    print(f"Stores: {len(stores.get('data', []))} found (Success: {stores.get('success')})")
    
    cats = api_get("/api/categories")
    print(f"Categories: {len(cats.get('data', []))} found (Success: {cats.get('success')})")
    
    prods = api_get("/api/products")
    print(f"Products: {len(prods.get('data', []))} found (Success: {prods.get('success')})")

    # 3. Test Inventory (Phase 5)
    inv = api_get("/api/inventory")
    print(f"Inventory Records: {len(inv.get('data', []))} found (Success: {inv.get('success')})")

    # 4. Test Sales (Phase 6)
    sales = api_get("/api/sales")
    print(f"Sales Records: {len(sales.get('data', []))} found (Success: {sales.get('success')})")

    # 5. Test Dashboard (Phase 7)
    dashboard = api_get("/api/dashboard")
    print(f"Dashboard Data Success: {dashboard.get('success')}")
    if dashboard.get("success"):
        data = dashboard["data"]
        print(f"  Total Products: {data.get('total_products')}")
        print(f"  Total Stores: {data.get('total_stores')}")
        print(f"  Today's Sales Count: {data.get('todays_sales')}")
        print(f"  Today's Revenue: {data.get('todays_revenue')}")
        
    print("Workflow Test Completed.")

if __name__ == '__main__':
    main()
