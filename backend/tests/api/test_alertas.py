from fastapi.testclient import TestClient


def test_alertas_ativos_ordenados_por_severidade(client: TestClient) -> None:
    corpo = client.get("/alertas").json()
    assert [(a["codigo_estacao"], a["severidade"]) for a in corpo] == [
        (90000004, "EMERGENCIA"),
        (90000001, "ALERTA"),
    ]
    assert all(a["status"] == "ATIVO" and a["encerrado_em"] is None for a in corpo)
    assert "Chuva acumulada" in corpo[0]["mensagem"]
