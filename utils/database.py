from contextlib import contextmanager
from mysql.connector import pooling
from flask import current_app

class DatabasePool:
    def __init__(self, app=None):
        self.pool = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
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

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with proper cleanup"""
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

db_pool = None

def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = DatabasePool()
    return db_pool

def get_connection(self):
    return self.pool.get_connection()

# Create a convenience function that uses the pool instance
@contextmanager
def db_cursor():
    """Convenience function for getting a database cursor"""
    if not current_app or not hasattr(current_app, 'db_pool'):
        raise RuntimeError("Application not configured with database pool")
    
    try:
        connection = current_app.db_pool.get_connection()
        cursor = connection.cursor(dictionary=True)
    finally:
        cursor.close()
        connection.close()