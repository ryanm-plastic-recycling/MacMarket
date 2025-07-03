import mysql.connector
from backend.app.database import connect_to_db


def test_connect_to_db(monkeypatch):
    class DummyConnection:
        pass

    def dummy_connect(**kwargs):
        return DummyConnection()

    monkeypatch.setattr(mysql.connector, "connect", dummy_connect)
    conn = connect_to_db()
    assert isinstance(conn, DummyConnection)
