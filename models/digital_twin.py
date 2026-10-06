"""DigitalTwinSimulation model — virtual inventory scenario results."""

from datetime import datetime
from models import db


class DigitalTwinSimulation(db.Model):
    __tablename__ = 'DIGITAL_TWIN_SIMULATION'

    simulation_id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    store_id           = db.Column(db.Integer, db.ForeignKey('STORE.store_id',
                                   onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    product_id         = db.Column(db.Integer, db.ForeignKey('PRODUCT.product_id',
                                   onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    scenario_name      = db.Column(db.String(100), nullable=False)
    simulation_date    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    starting_stock     = db.Column(db.Integer, nullable=False)
    simulated_stock    = db.Column(db.Integer, nullable=False)
    expected_sales     = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    expected_revenue   = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    expected_profit    = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    expected_loss      = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    expected_stockout  = db.Column(db.Integer, nullable=False, default=0)
    expected_overstock = db.Column(db.Integer, nullable=False, default=0)
    recommendation     = db.Column(db.Text)

    def to_dict(self):
        return {
            'simulation_id':    self.simulation_id,
            'store_id':         self.store_id,
            'store_name':       self.store.store_name if self.store else None,
            'product_id':       self.product_id,
            'product_name':     self.product.product_name if self.product else None,
            'scenario_name':    self.scenario_name,
            'simulation_date':  self.simulation_date.isoformat() if self.simulation_date else None,
            'starting_stock':   self.starting_stock,
            'simulated_stock':  self.simulated_stock,
            'expected_sales':   float(self.expected_sales),
            'expected_revenue': float(self.expected_revenue),
            'expected_profit':  float(self.expected_profit),
            'expected_loss':    float(self.expected_loss),
            'expected_stockout':  self.expected_stockout,
            'expected_overstock': self.expected_overstock,
            'recommendation':   self.recommendation,
        }

    def __repr__(self):
        return f'<Simulation {self.scenario_name} product={self.product_id} store={self.store_id}>'
