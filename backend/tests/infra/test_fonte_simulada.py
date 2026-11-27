import json
from datetime import UTC, datetime, timedelta

import pytest

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.alerta import RegraCotaReferencia
from app.dominio.enums import Grandeza, OrigemDados
from app.dominio.periodo import Periodo
from app.infra.fontes.simulada import FonteSimulada, regras_de_exemplo

AGORA = datetime(2026, 1, 10, 12, 34, tzinfo=UTC)


def test_cenario_json_define_estacoes_e_perfis() -> None:
    fonte = FonteSimulada(AGORA)

    assert fonte.origem_dados is OrigemDados.SIMULADO
    estacoes_sp = fonte.listar_estacoes(FiltroEstacoes(uf="SP"))
    assert {estacao.codigo for estacao in estacoes_sp} == {90000001, 90000002}
    estacao_tiete = fonte.buscar_estacao(90000001)
    assert estacao_tiete.rio == "Rio Tietê"
    assert estacao_tiete.municipio.uf == "SP"

    periodo = Periodo.ultimos(timedelta(hours=1), ate=AGORA)
    medicoes = fonte.buscar_medicoes(90000001, periodo)
    nivel = next(m for m in medicoes if m.grandeza() is Grandeza.NIVEL)
    vazao = next(m for m in medicoes if m.grandeza() is Grandeza.VAZAO)
    assert nivel.valor == 440
    assert vazao.valor == 18.5


def test_regras_de_exemplo_sao_lidas_do_cenario_json() -> None:
    regras = regras_de_exemplo()

    assert len(regras) == 5
    assert regras[0].codigo_estacao == 90000001
    assert isinstance(regras[0], RegraCotaReferencia)
    assert regras[0].cota_alerta_cm == 400


def test_fonte_simulada_usa_estacoes_do_arquivo_configurado(tmp_path) -> None:
    arquivo = tmp_path / "cenario.json"
    arquivo.write_text(
        json.dumps(
            {
                "estacoes": [
                    {
                        "codigo": 123,
                        "nome": "Estação de teste",
                        "tipo": "PLUVIOMETRICA",
                        "latitude": -23.5,
                        "longitude": -46.6,
                        "uf": "SP",
                        "municipio": "São Paulo",
                        "perfis": {"chuva": {"tipo": "constante", "valor": 2}},
                    }
                ],
                "regras": [],
            }
        ),
        encoding="utf-8",
    )

    fonte = FonteSimulada(AGORA, arquivo=arquivo)

    assert [estacao.codigo for estacao in fonte.listar_estacoes(FiltroEstacoes())] == [123]
    periodo = Periodo.ultimos(timedelta(hours=1), ate=AGORA)
    assert [m.valor for m in fonte.buscar_medicoes(123, periodo)] == [2]


def test_fonte_simulada_rejeita_lista_de_estacoes_com_tipo_invalido(tmp_path) -> None:
    arquivo = tmp_path / "cenario.json"
    arquivo.write_text('{"estacoes": {}}', encoding="utf-8")

    with pytest.raises(TypeError, match="lista de estações"):
        FonteSimulada(AGORA, arquivo=arquivo)


@pytest.mark.parametrize(
    ("estacoes", "mensagem"),
    [
        ([{"codigo": 7}], "nome.*ausente"),
        (
            [
                {
                    "codigo": 7,
                    "nome": "Teste",
                    "tipo": "PLUVIOMETRICA",
                    "latitude": 0,
                    "longitude": 0,
                    "uf": "SP",
                    "municipio": "Teste",
                    "perfis": {"chuva": {"tipo": "nao_existe"}},
                }
            ],
            "tipo desconhecido",
        ),
        (
            [
                {
                    "codigo": 7,
                    "nome": "Teste",
                    "tipo": "PLUVIOMETRICA",
                    "latitude": 0,
                    "longitude": 0,
                    "uf": "SP",
                    "municipio": "Teste",
                    "perfis": {"chuva": {"tipo": "constante"}},
                }
            ],
            "campo obrigatório 'valor' ausente",
        ),
        (
            [
                {
                    "codigo": 7,
                    "nome": "Teste",
                    "tipo": "PLUVIOMETRICA",
                    "latitude": 0,
                    "longitude": 0,
                    "uf": "SP",
                    "municipio": "Teste",
                    "telemetrica": "false",
                }
            ],
            "esperado valor booleano",
        ),
    ],
)
def test_fonte_simulada_valida_cenario_antes_de_usar(
    tmp_path, estacoes: list[dict], mensagem: str
) -> None:
    arquivo = tmp_path / "cenario.json"
    arquivo.write_text(json.dumps({"estacoes": estacoes}), encoding="utf-8")

    tipo_erro = TypeError if mensagem == "esperado valor booleano" else ValueError
    with pytest.raises(tipo_erro, match=mensagem):
        FonteSimulada(AGORA, arquivo=arquivo)


def test_fonte_simulada_rejeita_codigos_duplicados(tmp_path) -> None:
    arquivo = tmp_path / "cenario.json"
    estacao = {
        "codigo": 7,
        "nome": "Teste",
        "tipo": "PLUVIOMETRICA",
        "latitude": 0,
        "longitude": 0,
        "uf": "SP",
        "municipio": "Teste",
    }
    arquivo.write_text(json.dumps({"estacoes": [estacao, estacao]}), encoding="utf-8")

    with pytest.raises(ValueError, match="código duplicado"):
        FonteSimulada(AGORA, arquivo=arquivo)


def test_fonte_simulada_rejeita_perfil_de_vazao_circular(tmp_path) -> None:
    arquivo = tmp_path / "cenario.json"
    estacao = {
        "codigo": 7,
        "nome": "Teste",
        "tipo": "FLUVIOMETRICA",
        "latitude": 0,
        "longitude": 0,
        "uf": "SP",
        "municipio": "Teste",
        "perfis": {
            "vazao": {
                "tipo": "vazao_por_nivel",
                "perfil_nivel": "vazao",
                "coeficiente": 1,
                "expoente": 1,
            }
        },
    }
    arquivo.write_text(json.dumps({"estacoes": [estacao]}), encoding="utf-8")

    with pytest.raises(ValueError, match="perfil_nivel inválido"):
        FonteSimulada(AGORA, arquivo=arquivo)


def test_regras_de_exemplo_rejeita_regras_em_objeto(tmp_path) -> None:
    arquivo = tmp_path / "regras.json"
    arquivo.write_text('{"regras": {}}', encoding="utf-8")

    with pytest.raises(TypeError, match="regras em uma lista"):
        regras_de_exemplo(arquivo)
