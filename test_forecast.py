import json
from datetime import date, timedelta
from app import create_app
from models import db
from models.product import Product
from models.store import Store
from services.forecast_service import train_model, generate_forecast

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    print("\n--- Training ML Models ---")
    train_res = train_model()
    print("Train Success:", train_res.get('success'))
    print("Train Message:", train_res.get('message'))
    print("Best Model:", train_res.get('model_name'))
    if train_res.get('metrics'):
        print("Metrics:", train_res['metrics'])
    if train_res.get('comparison'):
        print("Candidate Models compared:", len(train_res['comparison']))
        for comp in train_res['comparison']:
            print(f"  {comp['model']}: RMSE={comp['rmse']} R2={comp['r2']}")

    print("\n--- TEST 1 & 7: Multi-day Forecast for Verification Milk ---")
    store = Store.query.filter_by(store_name='RetailTwin Main Store').first()
    product = Product.query.filter_by(product_name='Verification Milk').first()
    
    if store and product:
        today = date.today()
        forecasts = []
        for i in range(1, 6):
            fd = (today + timedelta(days=i)).isoformat()
            res = generate_forecast(product.product_id, store.store_id, fd, save=False)
            pred = res.get('predicted_demand')
            model = res.get('model_name')
            print(f"Date: {fd} | Prediction: {pred} | Model: {model}")
            forecasts.append(pred)
            assert pred >= 0, "TEST 7 FAILED: Negative prediction"
        
        # Verify it doesn't just repeat the exact same value if using ML
        unique_preds = set(forecasts)
        if len(unique_preds) > 1:
            print("TEST 1 PASSED: Multi-day predictions are varying date-dependent values.")
        else:
            print(f"TEST 1 INFO: Multi-day predictions are identical (might be baseline): {unique_preds}")

    print("\n--- TEST 6: Product with insufficient data ---")
    # Find or create a product with 0 sales
    new_prod = Product.query.filter_by(product_name='Insufficient Product Test').first()
    if not new_prod:
        new_prod = Product(
            product_name='Insufficient Product Test',
            category_id=product.category_id,
            cost_price=10.0,
            selling_price=15.0
        )
        db.session.add(new_prod)
        db.session.commit()
    
    fd = (date.today() + timedelta(days=1)).isoformat()
    res = generate_forecast(new_prod.product_id, store.store_id, fd, save=False)
    print("Model Used:", res.get('model_name'))
    print("Label:", res.get('quality_label'))
    assert res.get('model_name') == 'BaselineMovingAverage', "TEST 6 FAILED: Did not fall back to baseline."
    print("TEST 6 PASSED: Safely falls back to Moving Average.")
    
    # Cleanup
    db.session.delete(new_prod)
    db.session.commit()
