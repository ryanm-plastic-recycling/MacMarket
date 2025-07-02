import os
import mysql.connector
from mysql.connector import MySQLConnection


def connect_to_db() -> MySQLConnection:
    """Connect to MySQL using environment variables.

    Returns a connection object.
    """
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "user"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "db"),
    )
    return conn
