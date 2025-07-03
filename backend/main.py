from fastapi import FastAPI
from backend.app.database import connect_to_db

app = FastAPI()



@app.get("/market-data")
def read_market_data():
    """Return placeholder market data from MySQL."""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    # Placeholder query; replace with real market data query
    cursor.execute("SELECT 'AAPL' AS symbol, 150.0 AS price")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"data": result}
