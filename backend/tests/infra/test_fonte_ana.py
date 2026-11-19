import json
from datetime import UTC, datetime
from io import BytesIO
from typing import Self
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.enums import Grandeza, NivelConsistencia, TipoEstacao
from app.dominio.periodo import Periodo
from app.infra.fontes import ana
from app.infra.fontes.ana import FonteAna


class RespostaFake:
    def __init__(self, dados: dict) -> None:
        self._dados = json.dumps(dados).encode()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self) -> bytes:
        return self._dados


def test_lista_estacoes_por_uf_e_reutiliza_token(monkeypatch) -> None:
    chamadas = []

    def abrir(requisicao, timeout):
        chamadas.append(requisicao)
        if requisicao.full_url.endswith("/OAUth/v1"):
            return RespostaFake({"status": "OK", "items": {"tokenautenticacao": "token-teste"}})
        return RespostaFake(
            {
                "status": "OK",
                "items": [
                    {
                        "codigoestacao": "15400000",
                        "Estacao_Nome": "PORTO VELHO",
                        "Tipo_Estacao": "Fluviometrica",
                        "Latitude": "-8.7483",
                        "Longitude": "-63.9169",
                        "UF_Estacao": "RO",
                        "Municipio_Nome": "PORTO VELHO",
                        "Operando": "1",
                        "Data_Periodo_Telemetrica_Inicio": "2001-06-01",
                    }
                ],
            }
        )

    monkeypatch.setattr(ana, "urlopen", abrir)
    fonte = FonteAna("identificador", "senha")
    estacoes = fonte.listar_estacoes(FiltroEstacoes(uf="RO"))

    assert len(estacoes) == 1
    assert estacoes[0].codigo == 15400000
    assert estacoes[0].tipo is TipoEstacao.FLUVIOMETRICA
    assert estacoes[0].telemetrica
    assert len(chamadas) == 2
    assert chamadas[0].get_header("Identificador") == "identificador"
    assert chamadas[0].get_header("Senha") == "senha"
    assert chamadas[1].get_header("Authorization") == "Bearer token-teste"
    assert parse_qs(urlparse(chamadas[1].full_url).query) == {"Unidade Federativa": ["RO"]}


def test_listagem_nacional_retorna_resultados_parciais_se_uma_uf_falhar(monkeypatch) -> None:
    autenticacoes = 0
    ufs_consultadas = []

    def abrir(requisicao, timeout):
        nonlocal autenticacoes
        if requisicao.full_url.endswith("/OAUth/v1"):
            autenticacoes += 1
            return RespostaFake({"status": "OK", "items": {"tokenautenticacao": "token"}})
        uf = parse_qs(urlparse(requisicao.full_url).query)["Unidade Federativa"][0]
        ufs_consultadas.append(uf)
        if uf == "AC":
            raise HTTPError(requisicao.full_url, 500, "Unavailable", None, BytesIO())
        if uf == "SP":
            return RespostaFake(
                {
                    "status": "OK",
                    "items": {
                        "codigoestacao": "15400000",
                        "Estacao_Nome": "PORTO VELHO",
                        "Tipo_Estacao": "Fluviometrica",
                        "Latitude": "-8.7483",
                        "Longitude": "-63.9169",
                        "UF_Estacao": "SP",
                        "Municipio_Nome": "SÃO PAULO",
                    },
                }
            )
        return RespostaFake({"status": "OK", "items": []})

    monkeypatch.setattr(ana, "urlopen", abrir)
    estacoes = FonteAna("id", "senha").listar_estacoes(FiltroEstacoes())

    assert [estacao.codigo for estacao in estacoes] == [15400000]
    assert autenticacoes == 1
    assert len(ufs_consultadas) == len(ana._UFS)


def test_busca_mapeia_grandezas_e_status_de_qualidade(monkeypatch) -> None:
    chamadas = []

    def abrir(requisicao, timeout):
        chamadas.append(requisicao)
        if requisicao.full_url.endswith("/OAUth/v1"):
            return RespostaFake({"status": "OK", "items": {"tokenautenticacao": "token-teste"}})
        return RespostaFake(
            {
                "status": "OK",
                "items": [
                    {
                        "Data_Hora_Medicao": "2026-11-16 12:00:00.0",
                        "Data_Atualizacao": "2026-11-16 12:10:00.0",
                        "Chuva_Adotada": "1.25",
                        "Cota_Adotada": "781.00",
                        "Cota_Adotada_Status": "1",
                        "Vazao_Adotada": "13225.42",
                        "Vazao_Adotada_Status": "0",
                    }
                ],
            }
        )

    monkeypatch.setattr(ana, "urlopen", abrir)
    fonte = FonteAna("identificador", "senha")
    periodo = Periodo(
        datetime(2026, 11, 16, 14, tzinfo=UTC), datetime(2026, 11, 16, 16, tzinfo=UTC)
    )
    medicoes = fonte.buscar_medicoes(15400000, periodo)

    assert len(medicoes) == 3
    assert {medicao.grandeza() for medicao in medicoes} == set(Grandeza)
    nivel = next(medicao for medicao in medicoes if medicao.grandeza() is Grandeza.NIVEL)
    assert nivel.valor == 781
    assert nivel.consistencia is NivelConsistencia.BRUTO
    assert nivel.status_fonte == "1"
    chuva = next(medicao for medicao in medicoes if medicao.grandeza() is Grandeza.CHUVA)
    assert chuva.consistencia is NivelConsistencia.BRUTO
    assert chuva.status_fonte is None
    vazao = next(medicao for medicao in medicoes if medicao.grandeza() is Grandeza.VAZAO)
    assert vazao.consistencia is NivelConsistencia.CONSISTIDO
    assert nivel.atualizado_na_fonte_em == datetime(2026, 11, 16, 15, 10, tzinfo=UTC)
    parametros = parse_qs(urlparse(chamadas[1].full_url).query)
    assert parametros["Código da Estação"] == ["15400000"]
    assert parametros["Range Intervalo de busca"] == ["HORA_24"]
    assert medicoes[0].data_hora_utc == datetime(2026, 11, 16, 15, tzinfo=UTC)


def test_busca_estacao_por_codigo(monkeypatch) -> None:
    chamadas = []

    def abrir(requisicao, timeout):
        chamadas.append(requisicao)
        if requisicao.full_url.endswith("/OAUth/v1"):
            return RespostaFake({"status": "OK", "items": {"tokenautenticacao": "token"}})
        parametros = parse_qs(urlparse(requisicao.full_url).query)
        item = {
            "codigoestacao": "15400000",
            "Estacao_Nome": "PORTO VELHO",
            "Tipo_Estacao": "Fluviometrica",
            "Latitude": "-8.7483",
            "Longitude": "-63.9169",
            "UF_Estacao": "SP",
            "Municipio_Nome": "SÃO PAULO",
        }
        if "Código da Estação" in parametros:
            items = item
        else:
            items = [item, {**item, "codigoestacao": "15400001", "Estacao_Nome": "OUTRA"}]
        return RespostaFake(
            {
                "status": "OK",
                "items": items,
            }
        )

    monkeypatch.setattr(ana, "urlopen", abrir)
    fonte = FonteAna("id", "senha")
    estacao = fonte.buscar_estacao(15400000)

    assert estacao is not None
    assert estacao.codigo == 15400000
    parametros = parse_qs(urlparse(chamadas[1].full_url).query)
    assert parametros == {"Código da Estação": ["15400000"]}
    estacoes_da_uf = fonte.listar_estacoes(FiltroEstacoes(uf="SP"))
    assert {estacao.codigo for estacao in estacoes_da_uf} == {15400000, 15400001}
    parametros = parse_qs(urlparse(chamadas[2].full_url).query)
    assert parametros == {"Unidade Federativa": ["SP"]}


def test_busca_medicoes_reflete_data_local_da_ana(monkeypatch) -> None:
    chamadas = []

    def abrir(requisicao, timeout):
        chamadas.append(requisicao)
        if requisicao.full_url.endswith("/OAUth/v1"):
            return RespostaFake({"status": "OK", "items": {"tokenautenticacao": "token"}})
        return RespostaFake({"status": "OK", "items": []})

    monkeypatch.setattr(ana, "urlopen", abrir)
    periodo = Periodo(
        datetime(2026, 11, 15, 1, 30, tzinfo=UTC),
        datetime(2026, 11, 16, 1, 30, tzinfo=UTC),
    )
    FonteAna("id", "senha").buscar_medicoes(15400000, periodo)

    parametros = parse_qs(urlparse(chamadas[1].full_url).query)
    assert parametros["Data de Busca (yyyy-MM-dd)"] == ["2026-11-15"]
    assert parametros["Range Intervalo de busca"] == ["DIAS_2"]


def test_ignora_registro_com_medicao_invalida(monkeypatch) -> None:
    def abrir(requisicao, timeout):
        if requisicao.full_url.endswith("/OAUth/v1"):
            return RespostaFake({"status": "OK", "items": {"tokenautenticacao": "token"}})
        return RespostaFake(
            {
                "status": "OK",
                "items": [
                    {
                        "Data_Hora_Medicao": "2026-11-16 12:00:00",
                        "Cota_Adotada": "valor-invalido",
                    },
                    {
                        "Data_Hora_Medicao": "2026-11-16 12:00:00",
                        "Cota_Adotada": "781",
                    },
                ],
            }
        )

    monkeypatch.setattr(ana, "urlopen", abrir)
    periodo = Periodo(
        datetime(2026, 11, 16, 14, tzinfo=UTC), datetime(2026, 11, 16, 16, tzinfo=UTC)
    )
    medicoes = FonteAna("id", "senha").buscar_medicoes(15400000, periodo)

    assert len(medicoes) == 1
    assert medicoes[0].valor == 781


def test_renova_token_uma_vez_apos_resposta_401(monkeypatch) -> None:
    tokens_emitidos = 0
    chamadas_api = 0

    def abrir(requisicao, timeout):
        nonlocal tokens_emitidos, chamadas_api
        if requisicao.full_url.endswith("/OAUth/v1"):
            tokens_emitidos += 1
            return RespostaFake(
                {"status": "OK", "items": {"tokenautenticacao": f"token-{tokens_emitidos}"}}
            )
        chamadas_api += 1
        if chamadas_api == 1:
            raise HTTPError(requisicao.full_url, 401, "Unauthorized", None, BytesIO())
        assert requisicao.get_header("Authorization") == "Bearer token-2"
        return RespostaFake({"status": "OK", "items": []})

    monkeypatch.setattr(ana, "urlopen", abrir)
    periodo = Periodo(
        datetime(2026, 11, 16, 14, tzinfo=UTC), datetime(2026, 11, 16, 16, tzinfo=UTC)
    )
    assert FonteAna("id", "senha").buscar_medicoes(15400000, periodo) == []
    assert tokens_emitidos == 2
    assert chamadas_api == 2
