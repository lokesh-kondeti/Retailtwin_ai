"""PricingStrategy model — optional pricing recommendation module."""

from datetime import datetime, date
from models import db


class PricingStrategy(db.Model):
    __tablename__ = 'PRICING_STRATEGY'

    pricing_id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id          = db.Column(db.Integer, db.ForeignKey('PRODUCT.product_id',
                                    onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    original_price      = db.Column(db.Numeric(10, 2), nullable=False)
    suggested_price     = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=0.00)
    effective_date      = db.Column(db.Date, nullable=False, default=date.today)
    created_at          = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'pricing_id':          self.pricing_id,
            'product_id':          self.product_id,
            'product_name':        self.product.product_name if self.product else None,
            'original_price':      float(self.original_price),
            'suggested_price':     float(self.suggested_price),
            'discount_percentage': float(self.discount_percentage),
            'effective_date':      self.effective_date.isoformat() if self.effective_date else None,
            'created_at':          self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<PricingStrategy product={self.product_id} suggested={self.suggested_price}>'
