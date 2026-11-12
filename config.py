import os
from datetime import timedelta
from dotenv import load_dotenv
import pymysql

# Enable PyMySQL as universal pure-python MySQLdb dialect
try:
    pymysql.install_as_MySQLdb()
except Exception:
    pass

load_dotenv()

def _get_database_uri():
    # 1. Check if individual MySQL connection parameters are provided (e.g. Aiven, Railway, AWS RDS, TiDB)
    host = os.environ.get('MYSQLHOST') or os.environ.get('DB_HOST')
    if host:
        user = os.environ.get('MYSQLUSER') or os.environ.get('DB_USER', 'root')
        password = os.environ.get('MYSQLPASSWORD') or os.environ.get('DB_PASSWORD', '')
        port = os.environ.get('MYSQLPORT') or os.environ.get('DB_PORT', '3306')
        database = os.environ.get('MYSQLDATABASE') or os.environ.get('DB_NAME', 'oms_db')
        ssl_mode = os.environ.get('MYSQL_SSL_MODE') or os.environ.get('DB_SSL_MODE')
        ssl_ca = os.environ.get('MYSQL_SSL_CA') or os.environ.get('DB_SSL_CA')

        uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        if ssl_mode:
            uri += f"&ssl_mode={ssl_mode}"
        elif ssl_ca:
            uri += f"&ssl_ca={ssl_ca}"
        return uri

    # 2. Check unified database connection strings
    uri = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    if not uri:
        # Local development fallback
        uri = 'mysql+pymysql://root:@localhost:3306/oms_db?charset=utf8mb4'

    # Auto-convert standard mysql:// to mysql+pymysql:// to ensure pure-python compatibility
    if uri.startswith('mysql://'):
        uri = uri.replace('mysql://', 'mysql+pymysql://', 1)
    elif uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)

    return uri


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'oms-super-secret-key-enterprise-2026')
    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Serverless-Optimized Connection Pool (Vercel / Cloud hosted MySQL)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
        'pool_timeout': 20,
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 5)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 2))
    }

    # Session configurations
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1')

    # File upload configurations (use /tmp/uploads on Vercel serverless)
    IS_VERCEL = bool(os.environ.get('VERCEL'))
    if IS_VERCEL:
        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    else:
        UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app', 'static', 'uploads')

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx', 'xlsx', 'csv', 'txt'}

    # Pagination
    ITEMS_PER_PAGE = 10


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
