"""DemandForecast model — ML-generated demand predictions."""

from datetime import datetime, date
from models import db


class DemandForecast(db.Model):
    __tablename__ = 'DEMAND_FORECAST'

    forecast_id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id       = db.Column(db.Integer, db.ForeignKey('PRODUCT.product_id',
                                 onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    store_id         = db.Column(db.Integer, db.ForeignKey('STORE.store_id',
                                 onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    forecast_date    = db.Column(db.Date, nullable=False)
    predicted_demand = db.Column(db.Numeric(10, 2), nullable=False)
    # confidence_score = max(0, R² × 100) from model cross-validation
    confidence_score = db.Column(db.Numeric(5, 2), nullable=False, default=0.00)
    model_name       = db.Column(db.String(100), nullable=False, default='RandomForestRegressor')
    created_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'forecast_id':      self.forecast_id,
            'product_id':       self.product_id,
            'product_name':     self.product.product_name if self.product else None,
            'store_id':         self.store_id,
            'store_name':       self.store.store_name if self.store else None,
            'forecast_date':    self.forecast_date.isoformat() if self.forecast_date else None,
            'predicted_demand': float(self.predicted_demand),
            'confidence_score': float(self.confidence_score),
            'model_name':       self.model_name,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (f'<Forecast product={self.product_id} store={self.store_id} '
                f'date={self.forecast_date} demand={self.predicted_demand}>')
