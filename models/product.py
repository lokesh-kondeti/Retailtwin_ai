"""Product model — retail items tracked in inventory and sales."""

from datetime import datetime
from models import db


class Product(db.Model):
    __tablename__ = 'PRODUCT'

    product_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(100), nullable=False)
    category_id  = db.Column(db.Integer, db.ForeignKey('CATEGORY.category_id',
                              onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    cost_price   = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    lead_time    = db.Column(db.Integer, nullable=False, default=1)   # days
    expiry_days  = db.Column(db.Integer, nullable=False, default=365) # shelf life
    created_at   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    inventory_items  = db.relationship('Inventory', backref='product', lazy='dynamic',
                                       passive_deletes=True, foreign_keys='Inventory.product_id')
    sales            = db.relationship('Sales', backref='product', lazy='dynamic',
                                       passive_deletes=True, foreign_keys='Sales.product_id')
    forecasts        = db.relationship('DemandForecast', backref='product', lazy='dynamic',
                                       passive_deletes=True, foreign_keys='DemandForecast.product_id')
    simulations      = db.relationship('DigitalTwinSimulation', backref='product', lazy='dynamic',
                                       passive_deletes=True, foreign_keys='DigitalTwinSimulation.product_id')
    pricing_strategies = db.relationship('PricingStrategy', backref='product', lazy='dynamic',
                                         passive_deletes=True, foreign_keys='PricingStrategy.product_id')

    def to_dict(self):
        return {
            'product_id':    self.product_id,
            'product_name':  self.product_name,
            'category_id':   self.category_id,
            'category_name': self.category.category_name if self.category else None,
            'cost_price':    float(self.cost_price),
            'selling_price': float(self.selling_price),
            'lead_time':     self.lead_time,
            'expiry_days':   self.expiry_days,
            'created_at':    self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Product {self.product_name}>'
