import json
from datetime import UTC, datetime, timedelta

import pytest

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.alerta import RegraCotaReferencia
from app.dominio.enums import Grandeza
from app.dominio.periodo import Periodo
from app.infra.fontes.simulada import FonteSimulada, regras_de_exemplo

AGORA = datetime(2026, 1, 10, 12, 34, tzinfo=UTC)


def test_cenario_json_define_estacoes_e_perfis() -> None:
    fonte = FonteSimulada(AGORA)

    estacoes_sp = fonte.listar_estacoes(FiltroEstacoes(uf="SP"))
    assert {estacao.codigo for estacao in estacoes_sp} == {90000001, 90000002}
    assert fonte.buscar_estacao(90000001).rio == "Rio Tietê"

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
