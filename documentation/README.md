# RetailTwin AI

RetailTwin AI is a Smart Retail Demand Forecasting and Inventory Optimization application. It provides end-to-end management of stores, products, inventory, and sales, augmented with Machine Learning and Digital Twin capabilities to predict demand, simulate outcomes, and recommend optimal stocking strategies.

## Features (Phases 1-12 Complete)

* **Management:** Stores, Categories, Products, Inventory, and Sales.
* **Authentication:** Role-based access control (Admin, Manager).
* **Demand Forecasting:** Uses Machine Learning (Random Forest) trained on historical sales to forecast future demand, with a moving-average fallback.
* **Digital Twin Simulation:** Simulates expected sales, revenue, profit, and stockouts under different hypothetical stocking scenarios (Conservative, Balanced, Aggressive).
* **Inventory Optimization:** Recommends reorder quantities based on Economic Order Quantity (EOQ)-inspired logic, Lead Time Demand, and Safety Stock formulas.
* **Reporting:** Detailed reports for Sales, Inventory, Forecasts, Simulations, and Optimization, with CSV export capabilities.

## Setup and Installation

1. Install Python 3.11+.
2. Create and activate a virtual environment.
   \\\ash
   python -m venv venv
   .\venv\Scripts\activate
   \\\
3. Install dependencies:
   \\\ash
   pip install -r requirements.txt
   \\\
4. Configure the database in \.env\.
5. Initialize the database:
   \\\ash
   python database/init_db.py
   \\\
6. Run the application:
   \\\ash
   python app.py
   \\\

## Using the Application
Log in using test credentials (e.g., admin@retailtwin.ai / Admin@1234). 
Navigate through the sidebar to manage products, record sales, run ML forecasts, and simulate inventory scenarios using the Digital Twin feature.
