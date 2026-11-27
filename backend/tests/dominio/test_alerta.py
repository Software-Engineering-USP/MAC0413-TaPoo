from datetime import UTC, datetime, timedelta

import pytest

from app.dominio.alerta import (
    Alerta,
    AvaliacaoDeSituacao,
    AvaliadorAlertas,
    ContextoAvaliacao,
    FatorAvaliacao,
    RegraChuvaAcumulada,
    RegraChuvaPrevisao,
    RegraCotaReferencia,
)
from app.dominio.enums import Grandeza, Severidade, StatusAlerta
from app.dominio.erros import DadoInvalido
from app.dominio.geografia import Coordenada
from app.dominio.medicao import MedicaoChuva, MedicaoNivel, PrevisaoChuva, SerieTemporal

T0 = datetime(2026, 1, 1, tzinfo=UTC)
COD = 100


def serie_nivel(*valores: float) -> SerieTemporal:
    return SerieTemporal(
        COD,
        Grandeza.NIVEL,
        [MedicaoNivel(COD, T0 + timedelta(hours=i), v) for i, v in enumerate(valores)],
    )


def serie_chuva(mm_por_hora: float, horas: int) -> SerieTemporal:
    return SerieTemporal(
        COD,
        Grandeza.CHUVA,
        [MedicaoChuva(COD, T0 + timedelta(hours=i), mm_por_hora) for i in range(horas)],
    )


COTA = RegraCotaReferencia(COD, cota_atencao_cm=300, cota_alerta_cm=400, cota_inundacao_cm=500)
CHUVA = RegraChuvaAcumulada(COD, timedelta(hours=24), 30, 50, 80)


@pytest.mark.parametrize(
    "nivel, esperado",
    [
        (299, Severidade.NORMAL),
        (300, Severidade.ATENCAO),
        (450, Severidade.ALERTA),
        (500, Severidade.EMERGENCIA),
    ],
)
def test_regra_cota_usa_ultima_leitura(nivel: float, esperado: Severidade) -> None:
    assert COTA.avaliar(serie_nivel(600, nivel)) is esperado


@pytest.mark.parametrize(
    "mm_h, esperado",
    [
        (1, Severidade.NORMAL),
        (1.5, Severidade.ATENCAO),
        (3, Severidade.ALERTA),
        (4, Severidade.EMERGENCIA),
    ],
)
def test_regra_chuva_acumulada(mm_h: float, esperado: Severidade) -> None:
    assert CHUVA.avaliar(serie_chuva(mm_h, 24)) is esperado


def test_regra_rejeita_limites_fora_de_ordem() -> None:
    with pytest.raises(DadoInvalido):
        RegraCotaReferencia(COD, 500, 400, 300)


def test_regra_rejeita_serie_de_outra_grandeza() -> None:
    serie = serie_chuva(1, 1)
    with pytest.raises(DadoInvalido):
        COTA.avaliar(serie)


def test_descrever_cota_referencia_com_severidade_normal() -> None:
    descricao = COTA.descrever(Severidade.NORMAL, serie_nivel(250))

    assert descricao == "Rio abaixo da cota de atenção (250 cm, limite 300 cm)"


def test_descricao_de_chuva_informa_limite_da_severidade() -> None:
    descricao = CHUVA.descrever(Severidade.ALERTA, serie_chuva(3, 24))

    assert descricao == "Chuva acumulada de 72.0 mm em 24 h (limite de alerta: 50.0 mm)"


def test_alerta_nao_pode_ser_normal() -> None:
    with pytest.raises(DadoInvalido):
        Alerta(COD, Severidade.NORMAL, "x", T0)


def test_alerta_escalar_e_encerrar() -> None:
    alerta = Alerta(COD, Severidade.ATENCAO, "x", T0)
    with pytest.raises(ValueError):
        alerta.escalar(Severidade.ATENCAO, "y", None, ())
    alerta.escalar(Severidade.ALERTA, "y", None, ())
    assert alerta.severidade is Severidade.ALERTA
    alerta.encerrar(T0 + timedelta(hours=1))
    assert alerta.status is StatusAlerta.ENCERRADO
    with pytest.raises(ValueError):
        alerta.escalar(Severidade.EMERGENCIA, "z", None, ())
    depois = T0 + timedelta(hours=2)
    with pytest.raises(DadoInvalido):
        alerta.encerrar(depois)


def test_escalar_substitui_mensagem_e_fatores() -> None:
    fator_inicial = FatorAvaliacao("nível elevado", Severidade.ATENCAO, COD, None)
    fator_novo = FatorAvaliacao("chuva intensa", Severidade.ALERTA, COD, None)
    alerta = Alerta(COD, Severidade.ATENCAO, "nível elevado", T0, fatores=(fator_inicial,))

    alerta.escalar(Severidade.ALERTA, "chuva intensa", None, (fator_novo,))

    assert alerta.mensagem == "chuva intensa"
    assert alerta.fatores == (fator_novo,)


def test_avaliador_cria_alerta_com_pior_severidade() -> None:
    avaliador = AvaliadorAlertas([COTA, CHUVA])
    series = {Grandeza.NIVEL: serie_nivel(320), Grandeza.CHUVA: serie_chuva(3, 24)}
    alerta = avaliador.avaliar(series, None, T0)
    assert alerta is not None
    assert alerta.severidade is Severidade.ALERTA
    assert "Chuva acumulada" in alerta.mensagem
    assert alerta.medicao_gatilho.grandeza() is Grandeza.CHUVA


def test_avaliacao_agrega_fatores_e_compoe_mensagem() -> None:
    avaliador = AvaliadorAlertas([COTA, CHUVA])
    series = {Grandeza.NIVEL: serie_nivel(450), Grandeza.CHUVA: serie_chuva(3, 24)}

    resultado = avaliador.avaliar_regras(series)

    assert resultado.severidade is Severidade.ALERTA
    assert len(resultado.fatores) == 2
    assert "Rio acima da cota de alerta" in resultado.mensagem
    assert "Chuva acumulada de 72.0 mm em 24 h" in resultado.mensagem
    assert resultado.mensagem.count(";") == 1


def test_avaliacao_vazia_e_normal_sem_fatores() -> None:
    resultado = AvaliacaoDeSituacao()

    assert resultado.severidade is Severidade.NORMAL
    assert resultado.fatores == ()
    assert resultado.mensagem == ""
    assert resultado.fator_mais_grave is None


def test_avaliacao_seleciona_fator_mais_grave() -> None:
    fator_atencao = FatorAvaliacao("nível elevado", Severidade.ATENCAO, COD, None)
    fator_emergencia = FatorAvaliacao("chuva extrema", Severidade.EMERGENCIA, COD, None)

    resultado = AvaliacaoDeSituacao((fator_atencao, fator_emergencia))

    assert resultado.severidade is Severidade.EMERGENCIA
    assert resultado.fator_mais_grave is fator_emergencia
    assert resultado.fatores == (fator_emergencia, fator_atencao)


def test_avaliacao_preserva_ordem_dos_fatores_em_empate() -> None:
    primeiro = FatorAvaliacao("primeiro", Severidade.ALERTA, COD, None)
    segundo = FatorAvaliacao("segundo", Severidade.ALERTA, COD, None)

    resultado = AvaliacaoDeSituacao((primeiro, segundo))

    assert resultado.fator_mais_grave is primeiro
    assert resultado.fatores == (primeiro, segundo)


def test_alerta_inclui_mensagem_de_todos_os_fatores_acionados() -> None:
    avaliador = AvaliadorAlertas([COTA, CHUVA])
    series = {Grandeza.NIVEL: serie_nivel(450), Grandeza.CHUVA: serie_chuva(3, 24)}

    alerta = avaliador.avaliar(series, None, T0)

    assert alerta is not None
    assert alerta.severidade is Severidade.ALERTA
    assert "Rio acima da cota de alerta" in alerta.mensagem
    assert "Chuva acumulada de 72.0 mm em 24 h" in alerta.mensagem
    assert alerta.medicao_gatilho is series[Grandeza.NIVEL].ultimo()
    assert len(alerta.fatores) == 2
    assert {fator.severidade for fator in alerta.fatores} == {Severidade.ALERTA}


def test_avaliador_sem_alerta_quando_normal() -> None:
    assert AvaliadorAlertas([COTA]).avaliar({Grandeza.NIVEL: serie_nivel(100)}, None, T0) is None


def test_avaliador_escala_mas_nao_rebaixa() -> None:
    avaliador = AvaliadorAlertas([COTA])
    ativo = Alerta(COD, Severidade.ALERTA, "x", T0)
    resultado = avaliador.avaliar({Grandeza.NIVEL: serie_nivel(350)}, ativo, T0)
    assert resultado is ativo
    assert ativo.severidade is Severidade.ALERTA
    assert "Rio acima da cota de atenção" in ativo.mensagem
    resultado = avaliador.avaliar({Grandeza.NIVEL: serie_nivel(550)}, ativo, T0)
    assert resultado is ativo
    assert ativo.severidade is Severidade.EMERGENCIA


def test_avaliador_atualiza_fatores_sem_escalar_severidade() -> None:
    avaliador = AvaliadorAlertas([COTA, CHUVA])
    serie_nivel_alerta = serie_nivel(450)
    ativo = avaliador.avaliar({Grandeza.NIVEL: serie_nivel_alerta}, None, T0)
    assert ativo is not None

    series_com_chuva = {
        Grandeza.NIVEL: serie_nivel_alerta,
        Grandeza.CHUVA: serie_chuva(1.5, 24),
    }
    resultado = avaliador.avaliar(series_com_chuva, ativo, T0 + timedelta(hours=1))

    assert resultado is ativo
    assert ativo.severidade is Severidade.ALERTA
    assert len(ativo.fatores) == 2
    assert "Chuva acumulada de 36.0 mm" in ativo.mensagem


def test_avaliador_atualiza_descricao_quando_o_valor_muda() -> None:
    avaliador = AvaliadorAlertas([COTA])
    ativo = avaliador.avaliar({Grandeza.NIVEL: serie_nivel(450)}, None, T0)
    assert ativo is not None
    assert "450 cm" in ativo.mensagem

    resultado = avaliador.avaliar(
        {Grandeza.NIVEL: serie_nivel(460)},
        ativo,
        T0 + timedelta(hours=1),
    )

    assert resultado is ativo
    assert ativo.severidade is Severidade.ALERTA
    assert "460 cm" in ativo.mensagem


def test_avaliador_remove_fator_normalizado_sem_rebaixar_alerta() -> None:
    avaliador = AvaliadorAlertas([COTA, CHUVA])
    series_nivel_e_chuva = {
        Grandeza.NIVEL: serie_nivel(450),
        Grandeza.CHUVA: serie_chuva(3, 24),
    }
    ativo = avaliador.avaliar(series_nivel_e_chuva, None, T0)
    assert ativo is not None
    assert len(ativo.fatores) == 2

    resultado = avaliador.avaliar(
        {Grandeza.NIVEL: serie_nivel(250), Grandeza.CHUVA: serie_chuva(3, 24)},
        ativo,
        T0 + timedelta(hours=1),
    )

    assert resultado is ativo
    assert ativo.severidade is Severidade.ALERTA
    assert len(ativo.fatores) == 1
    assert "Rio acima da cota" not in ativo.mensagem
    assert "Chuva acumulada" in ativo.mensagem


def test_avaliador_encerra_quando_normaliza() -> None:
    ativo = Alerta(COD, Severidade.ALERTA, "x", T0)
    fim = T0 + timedelta(hours=3)
    resultado = AvaliadorAlertas([COTA]).avaliar({Grandeza.NIVEL: serie_nivel(100)}, ativo, fim)
    assert resultado is ativo
    assert ativo.status is StatusAlerta.ENCERRADO
    assert ativo.encerrado_em == fim


def test_avaliador_ignora_regras_inativas() -> None:
    inativa = RegraCotaReferencia(COD, 1, 2, 3, ativa=False)
    assert AvaliadorAlertas([inativa]).avaliar({Grandeza.NIVEL: serie_nivel(10)}, None, T0) is None


def test_regra_chuva_previsao_usa_proximas_24_h_sem_serie_observada() -> None:
    regra = RegraChuvaPrevisao(COD, Coordenada(-23, -46), timedelta(hours=24), 30, 60, 90)
    previsoes = [PrevisaoChuva(T0 - timedelta(hours=1), 1000)] + [
        PrevisaoChuva(T0 + timedelta(hours=i), 50 if i < 24 else 0) for i in range(168)
    ]

    alerta = AvaliadorAlertas([regra]).avaliar({}, None, T0, previsoes)
    contexto = ContextoAvaliacao({}, T0, tuple(previsoes))

    assert alerta is not None
    assert alerta.severidade is Severidade.EMERGENCIA
    assert alerta.medicao_gatilho is None
    assert regra.descrever(alerta.severidade, contexto) == "Chuva prevista de 1200.0 mm em 24 h"
