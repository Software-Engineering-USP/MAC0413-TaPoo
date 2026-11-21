from fastapi.testclient import TestClient


def test_alertas_ativos_ordenados_por_severidade(client: TestClient) -> None:
    corpo = client.get("/alertas").json()
    assert [(a["codigo_estacao"], a["severidade"]) for a in corpo] == [
        (90000004, "EMERGENCIA"),
        (90000001, "ALERTA"),
    ]
    assert all(a["status"] == "ATIVO" and a["encerrado_em"] is None for a in corpo)
    assert "Chuva acumulada" in corpo[0]["mensagem"]


def test_alertas_trazem_rotulo_da_severidade(client: TestClient) -> None:
    rotulos = [a["severidade_rotulo"] for a in client.get("/alertas").json()]
    assert rotulos == ["Emergência", "Alerta"]


def test_historico_de_alertas_da_estacao(client: TestClient) -> None:
    corpo = client.get("/estacoes/90000004/alertas").json()
    assert [(a["severidade"], a["status"]) for a in corpo] == [("EMERGENCIA", "ATIVO")]
    assert client.get("/estacoes/90000003/alertas").json() == []


def test_historico_de_alertas_valida_limite_e_estacao(client: TestClient) -> None:
    assert client.get("/estacoes/90000004/alertas?limite=0").status_code == 422
    assert client.get("/estacoes/90000004/alertas?limite=501").status_code == 422
    assert client.get("/estacoes/99999999/alertas").status_code == 404
