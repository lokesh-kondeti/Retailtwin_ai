"""User model — stores admin and store manager accounts."""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(db.Model):
    __tablename__ = 'USER'

    user_id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone         = db.Column(db.String(15))
    role          = db.Column(db.Enum('ADMIN', 'STORE_MANAGER'), nullable=False, default='STORE_MANAGER')
    created_at    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, plain_password: str):
        """Hash and store the password. Never stores plain text."""
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        """Return True if the plain password matches the stored hash."""
        return check_password_hash(self.password_hash, plain_password)

    def to_dict(self):
        """Serialize to dict — password hash is excluded."""
        return {
            'user_id':    self.user_id,
            'name':       self.name,
            'email':      self.email,
            'phone':      self.phone,
            'role':       self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
