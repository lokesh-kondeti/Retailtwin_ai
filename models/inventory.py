"""Inventory model — per-store stock levels for each product."""

from datetime import datetime
from models import db


class Inventory(db.Model):
    __tablename__ = 'INVENTORY'

    inventory_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id    = db.Column(db.Integer, db.ForeignKey('PRODUCT.product_id',
                              onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    store_id      = db.Column(db.Integer, db.ForeignKey('STORE.store_id',
                              onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)
    maximum_stock = db.Column(db.Integer, nullable=False, default=1000)
    reorder_level = db.Column(db.Integer, nullable=False, default=10)
    last_updated  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                              onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('product_id', 'store_id', name='uq_inventory_product_store'),
    )

    @property
    def stock_status(self) -> str:
        """
        Returns stock status string based on current vs reorder level and maximum.
        """
        if self.current_stock <= 0:
            return 'OUT_OF_STOCK'
        if self.current_stock <= self.reorder_level:
            return 'LOW_STOCK'
        if self.current_stock >= self.maximum_stock * 0.9:
            return 'OVERSTOCK'
        return 'NORMAL'

    def to_dict(self):
        return {
            'inventory_id':  self.inventory_id,
            'product_id':    self.product_id,
            'product_name':  self.product.product_name if self.product else None,
            'store_id':      self.store_id,
            'store_name':    self.store.store_name if self.store else None,
            'current_stock': self.current_stock,
            'minimum_stock': self.minimum_stock,
            'maximum_stock': self.maximum_stock,
            'reorder_level': self.reorder_level,
            'stock_status':  self.stock_status,
            'last_updated':  self.last_updated.isoformat() if self.last_updated else None,
        }

    def __repr__(self):
        return f'<Inventory product={self.product_id} store={self.store_id} stock={self.current_stock}>'
