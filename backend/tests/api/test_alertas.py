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


def test_alertas_expoem_fatores_da_explicacao(client: TestClient) -> None:
    alertas = client.get("/alertas").json()
    alerta = next(a for a in alertas if a["codigo_estacao"] == 90000001)
    fatores_esperados = [
        {
            "descricao": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
            "severidade": "ALERTA",
            "severidade_rotulo": "Alerta",
        }
    ]

    assert alerta["fatores"] == fatores_esperados
    assert alerta["fatores"][0]["descricao"] in alerta["mensagem"]
    estacao = client.get("/estacoes/90000001").json()
    assert estacao["alerta"]["fatores"] == fatores_esperados
