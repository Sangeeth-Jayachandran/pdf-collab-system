from contextlib import contextmanager
from mysql.connector import pooling
from flask import current_app

class DatabasePool:
    def __init__(self, app=None):
        self.pool = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with app context"""
        self.pool = pooling.MySQLConnectionPool(
            pool_name="pdf_pool",
            pool_size=5,
            host=app.config['DB_HOST'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME'],
            buffered=True,
            autocommit=True
        )
    
    def get_connection(self):
        """Get connection from pool with validation"""
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        return self.pool.get_connection()

db_pool = None

def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = DatabasePool()
    return db_pool



@contextmanager
def db_cursor():
    """Improved cursor handling with null checks"""
    conn = None
    try:
        conn = current_app.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        current_app.logger.error(f"DB operation failed: {str(e)}", exc_info=True)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()