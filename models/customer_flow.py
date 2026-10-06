"""CustomerFlow model — optional secondary module for store traffic analytics."""

from models import db


class CustomerFlow(db.Model):
    __tablename__ = 'CUSTOMER_FLOW'

    flow_id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    store_id       = db.Column(db.Integer, db.ForeignKey('STORE.store_id',
                               onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    date           = db.Column(db.Date, nullable=False)
    customer_count = db.Column(db.Integer, nullable=False, default=0)
    peak_hour      = db.Column(db.String(20))
    avg_dwell_time = db.Column(db.Numeric(6, 2), nullable=False, default=0.00)

    __table_args__ = (
        db.UniqueConstraint('store_id', 'date', name='uq_flow_store_date'),
    )

    def to_dict(self):
        return {
            'flow_id':        self.flow_id,
            'store_id':       self.store_id,
            'store_name':     self.store.store_name if self.store else None,
            'date':           self.date.isoformat() if self.date else None,
            'customer_count': self.customer_count,
            'peak_hour':      self.peak_hour,
            'avg_dwell_time': float(self.avg_dwell_time),
        }

    def __repr__(self):
        return f'<CustomerFlow store={self.store_id} date={self.date} count={self.customer_count}>'
