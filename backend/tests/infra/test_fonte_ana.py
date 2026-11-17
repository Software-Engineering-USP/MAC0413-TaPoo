import json
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.enums import Grandeza, NivelConsistencia, TipoEstacao
from app.dominio.periodo import Periodo
from app.infra.fontes import ana
from app.infra.fontes.ana import FonteAna


class RespostaFake:
    def __init__(self, dados: dict) -> None:
        self._dados = json.dumps(dados).encode()

    def __enter__(self) -> "RespostaFake":
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
            return RespostaFake(
                {"status": "OK", "items": {"tokenautenticacao": "token-teste"}}
            )
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


def test_busca_mapeia_grandezas_e_status_de_qualidade(monkeypatch) -> None:
    chamadas = []

    def abrir(requisicao, timeout):
        chamadas.append(requisicao)
        if requisicao.full_url.endswith("/OAUth/v1"):
            return RespostaFake(
                {"status": "OK", "items": {"tokenautenticacao": "token-teste"}}
            )
        return RespostaFake(
            {
                "status": "OK",
                "items": [
                    {
                        "Data_Hora_Medicao": "2026-11-16 12:00:00.0",
                        "Data_Atualizacao": "2026-11-16 12:10:00.0",
                        "Chuva_Adotada": "1.25",
                        "Chuva_Adotada_Status": "0",
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
    assert nivel.atualizado_na_fonte_em == datetime(2026, 11, 16, 15, 10, tzinfo=UTC)
    parametros = parse_qs(urlparse(chamadas[1].full_url).query)
    assert parametros["Código da Estação"] == ["15400000"]
    assert parametros["Range Intervalo de busca"] == ["HORA_24"]
    assert medicoes[0].data_hora_utc == datetime(2026, 11, 16, 15, tzinfo=UTC)
