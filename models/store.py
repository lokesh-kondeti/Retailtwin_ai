"""Store model — physical retail locations."""

from datetime import datetime
from models import db


class Store(db.Model):
    __tablename__ = 'STORE'

    store_id     = db.Column(db.Integer, primary_key=True, autoincrement=True)
    store_name   = db.Column(db.String(100), nullable=False, unique=True)
    location     = db.Column(db.String(150))
    manager_name = db.Column(db.String(100))
    contact      = db.Column(db.String(15))
    created_at   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships — passive_deletes=True tells SQLAlchemy to let MySQL enforce
    # ON DELETE RESTRICT without emitting spurious SET product_id=NULL updates.
    inventory_items = db.relationship('Inventory', backref='store', lazy='dynamic',
                                      passive_deletes=True, foreign_keys='Inventory.store_id')
    sales           = db.relationship('Sales', backref='store', lazy='dynamic',
                                      passive_deletes=True, foreign_keys='Sales.store_id')
    simulations     = db.relationship('DigitalTwinSimulation', backref='store', lazy='dynamic',
                                      passive_deletes=True, foreign_keys='DigitalTwinSimulation.store_id')
    customer_flows  = db.relationship('CustomerFlow', backref='store', lazy='dynamic',
                                      passive_deletes=True, foreign_keys='CustomerFlow.store_id')
    forecasts       = db.relationship('DemandForecast', backref='store', lazy='dynamic',
                                      passive_deletes=True, foreign_keys='DemandForecast.store_id')

    def to_dict(self):
        return {
            'store_id':     self.store_id,
            'store_name':   self.store_name,
            'location':     self.location,
            'manager_name': self.manager_name,
            'contact':      self.contact,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Store {self.store_name}>'
