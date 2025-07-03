from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_check_success(monkeypatch):
    class DummyConn:
        def close(self):
            pass

    def dummy_connect():
        return DummyConn()

    monkeypatch.setattr("backend.app.database.connect_to_db", dummy_connect)
    response = client.get("/db-check")
    assert response.status_code == 200
    assert response.json() == {"status": "connected"}
