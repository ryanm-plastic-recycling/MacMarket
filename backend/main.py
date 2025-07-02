from fastapi import FastAPI
import mysql.connector
import os

app = FastAPI()


def get_connection():
    """Create a new database connection using environment variables."""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "user"),
        password=os.getenv("MYSQL_PASSWORD", "password"),
        database=os.getenv("MYSQL_DATABASE", "market"),
    )


@app.get("/market-data")
def read_market_data():
    """Return placeholder market data from MySQL."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Placeholder query; replace with real market data query
    cursor.execute("SELECT 'AAPL' AS symbol, 150.0 AS price")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"data": result}
