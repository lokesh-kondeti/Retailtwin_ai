"""
Digital Twin Simulation Service.

A software-based virtual representation of selected retail inventory and demand behavior
used to evaluate hypothetical inventory strategies.

NOT a physically accurate store replica — purely a software simulation
for academic inventory strategy evaluation.
"""

from datetime import datetime
from decimal import Decimal

from models import db
from models.digital_twin import DigitalTwinSimulation
from models.inventory import Inventory
from models.product import Product
from models.store import Store
from models.demand_forecast import DemandForecast


def run_simulation(data: dict) -> dict:
    """
    Run a single Digital Twin simulation scenario.

    Simulation Logic:
    -----------------
    1. Retrieve predicted demand (from latest forecast or provide via data).
    2. Set virtual starting inventory = simulated_stock.
    3. Simulate sales: units_sold = min(simulated_stock, predicted_demand).
    4. stockout = max(0, predicted_demand - simulated_stock).
    5. overstock = max(0, simulated_stock - predicted_demand).
    6. revenue = units_sold × selling_price × (1 - discount/100).
    7. profit = revenue - (units_sold × cost_price).
    8. loss from stockout = stockout × selling_price × 0.3 (opportunity cost).
    9. Save result.
    """
    try:
        product_id      = int(data['product_id'])
        store_id        = int(data['store_id'])
        scenario_name   = str(data['scenario_name']).strip()
        simulated_stock = int(data['simulated_stock'])
        selling_price   = float(data['selling_price'])
        cost_price      = float(data['cost_price'])
        discount_pct    = float(data.get('discount', 0))
        simulation_days = int(data.get('simulation_days', 7))

        product = Product.query.get(product_id)
        store   = Store.query.get(store_id)
        if not product or not store:
            return {'success': False, 'message': 'Product or store not found.'}

        # Get latest forecast demand for this product/store
        forecast = DemandForecast.query.filter_by(
            product_id=product_id, store_id=store_id
        ).order_by(DemandForecast.created_at.desc()).first()

        if forecast:
            daily_demand = float(forecast.predicted_demand)
        else:
            # No forecast: use average daily sales from history
            from models.sales import Sales
            from sqlalchemy import func
            avg = db.session.query(
                func.avg(Sales.quantity_sold)
            ).filter_by(product_id=product_id, store_id=store_id).scalar()
            daily_demand = float(avg or 0)

        if daily_demand <= 0:
            return {
                'success': False,
                'message': ('No demand data available. Generate a forecast first '
                            'or record some sales history.')
            }

        # Get real inventory starting stock
        real_inventory = Inventory.query.filter_by(
            product_id=product_id, store_id=store_id
        ).first()
        starting_stock = real_inventory.current_stock if real_inventory else simulated_stock

        # Simulate over simulation_days
        total_demand   = daily_demand * simulation_days
        units_sold     = min(simulated_stock, total_demand)
        stockout_units = max(0, total_demand - simulated_stock)
        overstock_units = max(0, simulated_stock - total_demand)

        effective_price = selling_price * (1 - discount_pct / 100)
        revenue  = round(units_sold * effective_price, 2)
        profit   = round(revenue - (units_sold * cost_price), 2)

        # Opportunity loss from stockout (estimated at 30% of selling price per missed unit)
        loss = round(stockout_units * selling_price * 0.3, 2)

        # Recommendation text
        if stockout_units > 0 and overstock_units == 0:
            rec = (f"Stock of {simulated_stock} units is INSUFFICIENT. "
                   f"Expected demand is {round(total_demand, 0):.0f} units over {simulation_days} days. "
                   f"Consider increasing stock by at least {round(stockout_units, 0):.0f} units "
                   f"to avoid lost sales.")
        elif overstock_units > 0 and stockout_units == 0:
            rec = (f"Stock of {simulated_stock} units exceeds demand. "
                   f"{round(overstock_units, 0):.0f} units will remain unsold. "
                   f"Consider reducing stock to approximately {round(total_demand, 0):.0f} units "
                   f"to minimize holding costs.")
        else:
            rec = (f"Stock of {simulated_stock} units closely matches expected demand of "
                   f"{round(total_demand, 0):.0f} units over {simulation_days} days. "
                   f"This appears to be an efficient stocking level.")

        sim = DigitalTwinSimulation(
            store_id=store_id,
            product_id=product_id,
            scenario_name=scenario_name,
            simulation_date=datetime.utcnow(),
            starting_stock=starting_stock,
            simulated_stock=simulated_stock,
            expected_sales=Decimal(str(round(units_sold, 2))),
            expected_revenue=Decimal(str(revenue)),
            expected_profit=Decimal(str(profit)),
            expected_loss=Decimal(str(loss)),
            expected_stockout=int(round(stockout_units)),
            expected_overstock=int(round(overstock_units)),
            recommendation=rec
        )
        db.session.add(sim)
        db.session.commit()

        return {
            'success':    True,
            'message':    'Simulation completed.',
            'data':       sim.to_dict(),
            'assumptions': {
                'daily_demand':     round(daily_demand, 2),
                'simulation_days':  simulation_days,
                'total_demand':     round(total_demand, 2),
                'forecast_source':  'DemandForecast' if forecast else 'HistoricalAverage',
            }
        }

    except (KeyError, ValueError, TypeError) as e:
        return {'success': False, 'message': f'Invalid input: {str(e)}'}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Simulation error: {str(e)}'}


def compare_scenarios(simulation_ids: list) -> dict:
    """
    Compare multiple simulation scenarios and recommend the best one.

    Scoring formula:
        score = profit - (overstock × price × 0.1) - (stockout × price × 0.3)

    Rationale:
    - Stockout penalty (0.3) is higher than overstock cost (0.1) because
      lost sales also damage customer satisfaction.
    - The scenario with the highest score is recommended.
    """
    sims = DigitalTwinSimulation.query.filter(
        DigitalTwinSimulation.simulation_id.in_(simulation_ids)
    ).all()

    if not sims:
        return {'success': False, 'message': 'No simulations found for given IDs.'}

    scored = []
    for sim in sims:
        product = sim.product
        cost_price    = float(product.cost_price) if product else 0.0
        selling_price = float(product.selling_price) if product else 0.0

        profit    = float(sim.expected_profit)
        overstock = sim.expected_overstock
        stockout  = sim.expected_stockout

        score = profit - (overstock * cost_price * 0.1) - (stockout * selling_price * 0.3)
        scored.append({'sim': sim, 'score': score})

    scored.sort(key=lambda x: x['score'], reverse=True)
    best = scored[0]['sim']

    comparison = []
    for item in scored:
        s   = item['sim']
        rec = 'RECOMMENDED' if s.simulation_id == best.simulation_id else ''
        comparison.append({
            **s.to_dict(),
            'score':       round(item['score'], 2),
            'recommended': rec
        })

    return {
        'success': True,
        'comparison': comparison,
        'best_scenario': {
            'simulation_id': best.simulation_id,
            'scenario_name': best.scenario_name,
            'simulated_stock': best.simulated_stock,
        },
        'scoring_explanation': (
            'Score = Profit − (Overstock × Cost Price × 0.1) − (Stockout × Selling Price × 0.3). '
            'Stockout is penalized more heavily because lost sales also reduce customer trust.'
        )
    }
