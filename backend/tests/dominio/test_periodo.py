from datetime import UTC, datetime, timedelta, timezone
from itertools import pairwise

import pytest

from app.dominio.periodo import Periodo

INICIO = datetime(2026, 1, 1, tzinfo=UTC)


def test_rejeita_datetime_sem_fuso() -> None:
    with pytest.raises(ValueError):
        Periodo(datetime(2026, 1, 1), datetime(2026, 1, 2))


def test_normaliza_para_utc() -> None:
    brasilia = timezone(timedelta(hours=-3))
    p = Periodo(datetime(2026, 1, 1, 0, tzinfo=brasilia), datetime(2026, 1, 2, tzinfo=brasilia))
    assert p.inicio == datetime(2026, 1, 1, 3, tzinfo=UTC)
    assert p.inicio.tzinfo is UTC


def test_rejeita_inicio_depois_do_fim() -> None:
    with pytest.raises(ValueError):
        Periodo(INICIO, INICIO)


def test_dividir_respeita_limite_e_cobre_todo_o_periodo() -> None:
    p = Periodo(INICIO, INICIO + timedelta(days=75))
    fatias = p.dividir(30)
    assert [f.duracao() for f in fatias] == [timedelta(days=30)] * 2 + [timedelta(days=15)]
    assert fatias[0].inicio == p.inicio
    assert fatias[-1].fim == p.fim
    assert all(a.fim == b.inicio for a, b in pairwise(fatias))


def test_dividir_periodo_menor_que_limite() -> None:
    p = Periodo(INICIO, INICIO + timedelta(days=3))
    assert p.dividir(30) == [p]


def test_contem() -> None:
    p = Periodo.ultimos(timedelta(hours=24), ate=INICIO)
    assert p.contem(INICIO - timedelta(hours=1))
    assert not p.contem(INICIO + timedelta(seconds=1))
