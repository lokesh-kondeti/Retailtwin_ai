with open('documentation/API_REFERENCE.md', 'w', encoding='utf-8') as f:
    f.write('''# API Reference

The backend exposes several JSON endpoints used by the frontend for dynamic updates. All API endpoints require authentication via session cookies.

## Forecasting
- \POST /api/forecasts/train\: Triggers ML model training using historical sales.
- \POST /api/forecast\: Generates a demand forecast for a specific product, store, and date.
- \GET /api/forecasts\: Retrieves historical forecasts.

## Digital Twin Simulation
- \POST /api/simulation\: Runs a single inventory simulation scenario.
- \POST /api/simulations/compare\: Compares multiple simulation IDs and returns a recommendation.
- \GET /api/simulations\: Retrieves historical simulations.

## Inventory Optimization
- \POST /api/optimization\: Computes safety stock, lead time demand, and recommended reorder quantity for a given product and store.

## Reports Export
Append \?export=csv\ to any of these endpoints to download the report as a CSV file.
- \GET /api/reports/sales\
- \GET /api/reports/inventory\
- \GET /api/reports/forecasts\
- \GET /api/reports/simulations\
- \GET /api/reports/optimization\
''')
