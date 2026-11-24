from datetime import UTC, datetime

import pytest

from app.dominio.alerta import Alerta
from app.dominio.enums import Severidade, TipoEstacao
from app.dominio.erros import DadoInvalido
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.municipio import Municipio
from app.dominio.situacao import SituacaoEstacao, SituacaoMunicipio

AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)


X = Municipio("X", "SP")


def estacao(codigo: int, municipio: Municipio = X) -> Estacao:
    return Estacao(
        codigo, f"Estação {codigo}", TipoEstacao.PLUVIOMETRICA, Coordenada(-23, -46), municipio
    )


def alerta(codigo: int, severidade: Severidade) -> Alerta:
    return Alerta(codigo, severidade, "mensagem", emitido_em=AGORA)


def test_estacao_sem_alerta_esta_normal() -> None:
    assert SituacaoEstacao(estacao(1)).severidade is Severidade.NORMAL


def test_estacao_com_alerta_usa_severidade_do_alerta() -> None:
    situacao = SituacaoEstacao(estacao(1), alerta(1, Severidade.ALERTA))
    assert situacao.severidade is Severidade.ALERTA


def test_alerta_de_outra_estacao_e_rejeitado() -> None:
    estacao_1 = estacao(1)
    alerta_da_2 = alerta(2, Severidade.ALERTA)
    with pytest.raises(DadoInvalido, match="outra estação"):
        SituacaoEstacao(estacao_1, alerta_da_2)


def test_alerta_encerrado_e_rejeitado() -> None:
    estacao_1 = estacao(1)
    encerrado = alerta(1, Severidade.ALERTA)
    encerrado.encerrar(AGORA)
    with pytest.raises(DadoInvalido, match="ativos"):
        SituacaoEstacao(estacao_1, encerrado)


def test_municipio_assume_a_pior_situacao_e_ordena_por_gravidade() -> None:
    situacao = SituacaoMunicipio(
        X,
        (
            SituacaoEstacao(estacao(1)),
            SituacaoEstacao(estacao(3), alerta(3, Severidade.ATENCAO)),
            SituacaoEstacao(estacao(2), alerta(2, Severidade.EMERGENCIA)),
        ),
    )
    assert situacao.severidade is Severidade.EMERGENCIA
    assert [s.estacao.codigo for s in situacao.estacoes] == [2, 3, 1]
    assert [a.codigo_estacao for a in situacao.alertas] == [2, 3]


def test_municipio_sem_estacoes_e_rejeitado() -> None:
    with pytest.raises(DadoInvalido):
        SituacaoMunicipio(X, ())


def test_municipio_rejeita_estacao_de_outro_municipio() -> None:
    outra = SituacaoEstacao(estacao(2, Municipio("X", "MG")))
    with pytest.raises(DadoInvalido, match="fora de X/SP"):
        SituacaoMunicipio(X, (SituacaoEstacao(estacao(1)), outra))


def test_municipio_aceita_grafias_diferentes_do_mesmo_municipio() -> None:
    sp = Municipio("São Paulo", "SP")
    situacao = SituacaoMunicipio(
        sp,
        (
            SituacaoEstacao(estacao(1, sp)),
            SituacaoEstacao(estacao(2, Municipio("SAO PAULO", "sp"))),
        ),
    )
    assert len(situacao.estacoes) == 2
