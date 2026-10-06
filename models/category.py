"""Category model — product classification."""

from datetime import date
from models import db


class Category(db.Model):
    __tablename__ = 'CATEGORY'

    category_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(100), nullable=False, unique=True)
    description   = db.Column(db.Text)
    created_date  = db.Column(db.Date, nullable=False, default=date.today)

    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic',
                               foreign_keys='Product.category_id')

    def to_dict(self):
        return {
            'category_id':   self.category_id,
            'category_name': self.category_name,
            'description':   self.description,
            'created_date':  self.created_date.isoformat() if self.created_date else None,
            'product_count': self.products.count(),
        }

    def __repr__(self):
        return f'<Category {self.category_name}>'
