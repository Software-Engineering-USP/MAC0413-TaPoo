import pytest
from fastapi.testclient import TestClient

from app.api.dependencias import montar_container
from app.infra.fontes.ana import ErroFonteAna, FonteAna
from app.infra.fontes.fake import FonteFake
from app.main import create_app
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
    assert corpo["severidade"] == "ALERTA"
    assert corpo["severidade_rotulo"] == "Alerta"
    assert corpo["alerta"]["codigo_estacao"] == 90000001
    assert corpo["alerta"]["status"] == "ATIVO"


def test_listar_traz_situacao_de_cada_estacao(client: TestClient) -> None:
    situacoes = {e["codigo"]: e["severidade"] for e in client.get("/estacoes").json()}
    assert situacoes == {
        90000001: "ALERTA",
        90000002: "NORMAL",
        90000003: "NORMAL",
        90000004: "EMERGENCIA",
        90000005: "NORMAL",
    }
    sem_alerta = client.get("/estacoes?uf=MG").json()
    assert all(e["alerta"] is None for e in sem_alerta)


def test_acesso_direto_sincroniza_estacao_ainda_nao_carregada() -> None:
    fonte = FonteFake(AGORA)
    fonte.carregar_na_inicializacao = False
    app = create_app(lambda: montar_container(fonte, relogio=lambda: AGORA))

    with TestClient(app) as cliente:
        resposta = cliente.get("/estacoes/90000001")

    assert resposta.status_code == 200
    assert resposta.json()["codigo"] == 90000001


def test_medicoes_diretas_sincronizam_estacao_ainda_nao_carregada() -> None:
    fonte = FonteFake(AGORA)
    fonte.carregar_na_inicializacao = False
    app = create_app(lambda: montar_container(fonte, relogio=lambda: AGORA))

    with TestClient(app) as cliente:
        resposta = cliente.get("/estacoes/90000001/medicoes?grandeza=NIVEL")

    assert resposta.status_code == 200
    assert resposta.json()["medicoes"]


def test_indisponibilidade_da_ana_retorna_502(monkeypatch) -> None:
    fonte = FonteAna("id", "senha")

    def indisponivel(codigo):
        raise ErroFonteAna("ANA indisponível")

    monkeypatch.setattr(fonte, "buscar_estacao", indisponivel)
    app = create_app(lambda: montar_container(fonte, relogio=lambda: AGORA))

    with TestClient(app) as cliente:
        resposta = cliente.get("/estacoes/15400000")

    assert resposta.status_code == 502
    assert resposta.json()["detail"] == "ANA indisponível"


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
    assert [e["severidade"] for e in longe] == ["ALERTA", "NORMAL"]


def test_estacoes_proximas_valida_parametros(client: TestClient) -> None:
    assert client.get("/estacoes/proximas?lat=-100&lon=0").status_code == 422
    assert client.get("/estacoes/proximas?lat=0").status_code == 422


def test_serie_padrao_ultimas_24h(client: TestClient) -> None:
    corpo = client.get("/estacoes/90000001/medicoes?grandeza=NIVEL").json()
    assert (corpo["grandeza_rotulo"], corpo["unidade"]) == ("Nível", "cm")
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


def test_busca_por_nome_municipio_ou_rio(client: TestClient) -> None:
    def codigos(q: str) -> list[int]:
        resposta = client.get("/estacoes", params={"q": q})
        assert resposta.status_code == 200
        return [e["codigo"] for e in resposta.json()]

    assert codigos("tiete") == [90000001]
    assert codigos("SÃO paulo") == [90000001]
    assert codigos("petropolis") == [90000004]
    assert codigos("rio") == [90000001, 90000003]
    assert codigos("inexistente") == []


def test_busca_combina_com_uf_e_traz_situacao(client: TestClient) -> None:
    corpo = client.get("/estacoes", params={"q": "exemplo", "uf": "MG"}).json()
    assert [e["codigo"] for e in corpo] == [90000003, 90000005]
    assert all("severidade" in e for e in corpo)


@pytest.mark.parametrize("q", ["a", "x" * 101])
def test_busca_valida_tamanho_do_termo(client: TestClient, q: str) -> None:
    assert client.get("/estacoes", params={"q": q}).status_code == 422


class FonteSemCarga(FonteFake):
    carregar_na_inicializacao = False

    def __init__(self) -> None:
        super().__init__(AGORA)
        self.listagens: list[str | None] = []

    def listar_estacoes(self, filtro):
        self.listagens.append(filtro.uf)
        return super().listar_estacoes(filtro)


def test_busca_sem_uf_nao_sincroniza_o_inventario() -> None:
    fonte = FonteSemCarga()
    app = create_app(lambda: montar_container(fonte, relogio=lambda: AGORA))
    with TestClient(app) as client:
        assert client.get("/estacoes", params={"q": "tiete"}).json() == []
        assert fonte.listagens == []

        client.get("/estacoes", params={"uf": "SP"})  # o usuário abre o estado
        assert [e["codigo"] for e in client.get("/estacoes?q=tiete").json()] == [90000001]
        assert fonte.listagens == ["SP"]


def test_busca_com_uf_sincroniza_so_o_estado() -> None:
    fonte = FonteSemCarga()
    app = create_app(lambda: montar_container(fonte, relogio=lambda: AGORA))
    with TestClient(app) as client:
        corpo = client.get("/estacoes", params={"q": "velhas", "uf": "mg"}).json()
        assert [e["codigo"] for e in corpo] == [90000003]
        assert fonte.listagens == ["mg"]
