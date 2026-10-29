from fastapi.testclient import TestClient

from bookmatch.api.main import app

# cliente de teste para app
client = TestClient(app)


def test_health_check():
    # executa a requisição GET que quero testar
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "message": "BookMatch AI está rodando!"
    }