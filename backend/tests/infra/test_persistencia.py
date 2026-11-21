from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from app.infra.persistencia.modelos_orm import DataHoraUtc
from app.infra.persistencia.repositorios_sql import BancoDeDados, normalizar_url


@pytest.mark.parametrize(
    ("url", "esperada"),
    [
        ("postgres://u:s@h/db", "postgresql+psycopg://u:s@h/db"),
        ("postgresql://u:s@h/db", "postgresql+psycopg://u:s@h/db"),
        ("postgresql+psycopg://u:s@h/db", "postgresql+psycopg://u:s@h/db"),
        ("sqlite:///tapoo.db", "sqlite:///tapoo.db"),
    ],
)
def test_normalizar_url_usa_o_driver_psycopg(url: str, esperada: str) -> None:
    assert normalizar_url(url) == esperada


def test_data_hora_sem_fuso_nao_e_gravada() -> None:
    with pytest.raises(ValueError, match="sem fuso"):
        DataHoraUtc().process_bind_param(datetime(2026, 1, 1), sqlite.dialect())


def test_data_hora_no_sqlite_vai_sem_fuso_e_no_postgres_com_fuso() -> None:
    instante = datetime(2026, 1, 1, 12, tzinfo=UTC)
    tipo = DataHoraUtc()
    assert tipo.process_bind_param(instante, sqlite.dialect()) == datetime(2026, 1, 1, 12)
    assert tipo.process_bind_param(instante, postgresql.dialect()).tzinfo is UTC
    assert tipo.process_result_value(datetime(2026, 1, 1, 12), sqlite.dialect()) == instante
    assert tipo.process_bind_param(None, sqlite.dialect()) is None
    assert tipo.process_result_value(None, sqlite.dialect()) is None


def test_sqlite_ativa_chaves_estrangeiras() -> None:
    banco = BancoDeDados("sqlite://")
    with banco.engine.connect() as conexao:
        assert conexao.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    banco.engine.dispose()
