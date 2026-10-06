"""Sales model — individual sales transactions."""

from datetime import datetime, date
from decimal import Decimal
from models import db


class Sales(db.Model):
    __tablename__ = 'SALES'

    sale_id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id    = db.Column(db.Integer, db.ForeignKey('PRODUCT.product_id',
                              onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    store_id      = db.Column(db.Integer, db.ForeignKey('STORE.store_id',
                              onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    sale_date     = db.Column(db.Date, nullable=False, default=date.today)
    quantity_sold = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price    = db.Column(db.Numeric(10, 2), nullable=False)
    discount      = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    revenue       = db.Column(db.Numeric(12, 2), nullable=False)
    created_at    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @staticmethod
    def calculate_revenue(quantity: int, price: Decimal, discount_pct: Decimal) -> Decimal:
        """
        Calculate revenue server-side.
        revenue = quantity × price × (1 - discount% / 100)
        Never trust the client-provided revenue value.
        """
        discount_pct = Decimal(str(discount_pct)) if not isinstance(discount_pct, Decimal) else discount_pct
        price = Decimal(str(price)) if not isinstance(price, Decimal) else price
        return round(quantity * price * (1 - discount_pct / 100), 2)

    def to_dict(self):
        return {
            'sale_id':       self.sale_id,
            'product_id':    self.product_id,
            'product_name':  self.product.product_name if self.product else None,
            'store_id':      self.store_id,
            'store_name':    self.store.store_name if self.store else None,
            'sale_date':     self.sale_date.isoformat() if self.sale_date else None,
            'quantity_sold': self.quantity_sold,
            'selling_price': float(self.selling_price),
            'cost_price':    float(self.cost_price),
            'discount':      float(self.discount),
            'revenue':       float(self.revenue),
            'created_at':    self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Sale product={self.product_id} store={self.store_id} qty={self.quantity_sold}>'
