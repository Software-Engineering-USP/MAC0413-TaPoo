from fastapi.testclient import TestClient

from tests.api.conftest import AGORA


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_listar_todas(client: TestClient) -> None:
    resposta = client.get("/estacoes")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 5
    assert set(corpo[0]) >= {"codigo", "nome", "tipo", "latitude", "longitude", "grandezas"}


def test_listar_com_filtros(client: TestClient) -> None:
    codigos = [e["codigo"] for e in client.get("/estacoes?uf=mg").json()]
    assert codigos == [90000003, 90000005]
    filtradas = client.get("/estacoes?uf=MG&apenas_telemetricas=true").json()
    assert [e["codigo"] for e in filtradas] == [90000003]
    fluvio = client.get("/estacoes?tipo=FLUVIOMETRICA").json()
    assert {e["tipo"] for e in fluvio} == {"FLUVIOMETRICA"}


def test_listar_tipo_invalido(client: TestClient) -> None:
    assert client.get("/estacoes?tipo=XYZ").status_code == 422


def test_obter_estacao(client: TestClient) -> None:
    corpo = client.get("/estacoes/90000001").json()
    assert corpo["rio"] == "Rio Tietê"
    assert corpo["grandezas"] == ["CHUVA", "NIVEL", "VAZAO"]


def test_estacao_inexistente(client: TestClient) -> None:
    resposta = client.get("/estacoes/1")
    assert resposta.status_code == 404
    assert "não encontrada" in resposta.json()["detail"]


def test_estacoes_proximas(client: TestClient) -> None:
    # Centro de São Paulo: Tietê a poucos km, Campinas a ~85 km.
    perto = client.get("/estacoes/proximas?lat=-23.55&lon=-46.63").json()
    assert [e["codigo"] for e in perto] == [90000001]
    longe = client.get("/estacoes/proximas?lat=-23.55&lon=-46.63&raio_km=100").json()
    assert [e["codigo"] for e in longe] == [90000001, 90000002]
    assert longe[0]["distancia_km"] < longe[1]["distancia_km"]


def test_estacoes_proximas_valida_parametros(client: TestClient) -> None:
    assert client.get("/estacoes/proximas?lat=-100&lon=0").status_code == 422
    assert client.get("/estacoes/proximas?lat=0").status_code == 422


def test_serie_padrao_ultimas_24h(client: TestClient) -> None:
    corpo = client.get("/estacoes/90000001/medicoes?grandeza=NIVEL").json()
    assert corpo["unidade"] == "cm"
    assert len(corpo["medicoes"]) == 25  # leituras horárias, intervalo fechado
    assert corpo["medicoes"][-1]["data_hora_utc"].startswith(AGORA.strftime("%Y-%m-%dT%H"))
    assert corpo["medicoes"][-1]["valor"] == 440


def test_serie_com_periodo(client: TestClient) -> None:
    resposta = client.get(
        "/estacoes/90000004/medicoes",
        params={
            "grandeza": "CHUVA",
            "inicio": "2026-01-10T09:00:00Z",
            "fim": "2026-01-10T11:00:00-00:00",
        },
    )
    assert [m["valor"] for m in resposta.json()["medicoes"]] == [4, 4, 4]


def test_serie_rejeita_periodo_invalido(client: TestClient) -> None:
    base = "/estacoes/90000001/medicoes?grandeza=NIVEL"
    assert client.get(f"{base}&inicio=2026-01-10T00:00:00").status_code == 422  # sem fuso
    invertido = f"{base}&inicio=2026-01-10T10:00:00Z&fim=2026-01-10T09:00:00Z"
    assert client.get(invertido).status_code == 422
    longo = f"{base}&inicio=2025-01-01T00:00:00Z&fim=2026-01-01T00:00:00Z"
    assert client.get(longo).status_code == 422


def test_serie_de_estacao_inexistente(client: TestClient) -> None:
    assert client.get("/estacoes/1/medicoes?grandeza=NIVEL").status_code == 404
