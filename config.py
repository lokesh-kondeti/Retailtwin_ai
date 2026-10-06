"""
RetailTwin AI — Application Configuration
Reads all sensitive settings from environment variables (.env).
No credentials are hardcoded here.
"""

import os
from dotenv import load_dotenv

# Load .env from project root (one level up from this file)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


class Config:
    """Base configuration shared by all environments."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key-change-me')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set True to see SQL queries in console

    # Build MySQL connection URL from individual env vars
    _MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    _MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    _MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    import urllib.parse
    _MYSQL_PASS = urllib.parse.quote_plus(os.environ.get('MYSQL_PASSWORD', ''))
    _MYSQL_DB   = os.environ.get('MYSQL_DATABASE', 'RetailTwin_AI')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{_MYSQL_USER}:{_MYSQL_PASS}"
        f"@{_MYSQL_HOST}:{_MYSQL_PORT}/{_MYSQL_DB}"
        f"?charset=utf8mb4"
    )

    # ML model artifacts directory
    MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trained_models')

    # Minimum sales records needed before attempting RandomForest
    ML_MIN_RECORDS = 30

    # Application port
    APP_PORT = int(os.environ.get('APP_PORT', 5000))


class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing-specific configuration — uses in-memory SQLite to avoid touching MySQL."""
    TESTING = True
    DEBUG = True
    # Override DB to SQLite for fast isolated testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'


# Map environment name → config class
config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}


def get_config():
    """Return the correct config class based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    return config_map.get(env, DevelopmentConfig)
