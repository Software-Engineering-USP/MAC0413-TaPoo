from fastapi.testclient import TestClient


def test_situacao_de_municipio_em_alerta(client: TestClient) -> None:
    resposta = client.get("/municipios/sp/sao paulo/situacao")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["uf"], corpo["municipio"], corpo["severidade"]) == ("SP", "São Paulo", "ALERTA")
    [estacao] = corpo["estacoes"]
    assert estacao["codigo"] == 90000001
    assert estacao["alerta"]["severidade"] == "ALERTA"


def test_situacao_de_municipio_normal(client: TestClient) -> None:
    corpo = client.get("/municipios/MG/Belo Horizonte/situacao").json()
    assert corpo["severidade"] == "NORMAL"
    assert corpo["estacoes"][0]["alerta"] is None


def test_municipio_inexistente_ou_de_outra_uf(client: TestClient) -> None:
    for url in ("/municipios/SP/Atlantida/situacao", "/municipios/RJ/Campinas/situacao"):
        resposta = client.get(url)
        assert resposta.status_code == 404
        assert "nenhuma estação" in resposta.json()["detail"]


def test_municipio_com_uf_invalida(client: TestClient) -> None:
    assert client.get("/municipios/SAO/Campinas/situacao").status_code == 422
