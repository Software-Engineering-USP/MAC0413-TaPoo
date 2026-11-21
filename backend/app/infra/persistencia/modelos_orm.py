"""Modelos ORM: o formato das tabelas (docs/diagramas-de-classe-ana.md, seção 1).

O domínio não conhece o SQLAlchemy. Os repositórios de `repositorios_sql.py` convertem
entre estes modelos e as entidades.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    Uuid,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.dominio.enums import (
    Grandeza,
    NivelConsistencia,
    OrigemDado,
    Severidade,
    StatusAlerta,
    TipoEstacao,
)


class DataHoraUtc(TypeDecorator[datetime]):
    """Grava sempre em UTC e devolve `datetime` com fuso, como o domínio exige.

    O SQLite não guarda fuso: lá o valor vai em UTC sem fuso e o fuso é recolocado na
    leitura. No Postgres a coluna é `timestamptz`.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, valor: datetime | None, dialect: Dialect) -> datetime | None:
        if valor is None:
            return None
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError(f"data/hora sem fuso horário não pode ser gravada: {valor!r}")
        valor = valor.astimezone(UTC)
        return valor.replace(tzinfo=None) if dialect.name == "sqlite" else valor

    def process_result_value(self, valor: datetime | None, dialect: Dialect) -> datetime | None:
        if valor is None:
            return None
        return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _enum(classe: type) -> Enum:
    return Enum(classe, native_enum=False, length=20, validate_strings=True)


class Base(DeclarativeBase):
    pass


class EstacaoModelo(Base):
    __tablename__ = "estacoes"

    codigo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[TipoEstacao] = mapped_column(_enum(TipoEstacao))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    uf: Mapped[str] = mapped_column(String(2), index=True)
    municipio: Mapped[str] = mapped_column(String(200))
    rio: Mapped[str | None] = mapped_column(String(200))
    operando: Mapped[bool] = mapped_column(Boolean)
    telemetrica: Mapped[bool] = mapped_column(Boolean)
    atualizado_em: Mapped[datetime] = mapped_column(DataHoraUtc())


class MedicaoModelo(Base):
    """Uma linha por medição. A chave primária é a chave natural de `Medicao.chave()`."""

    __tablename__ = "medicoes"

    codigo_estacao: Mapped[int] = mapped_column(
        ForeignKey("estacoes.codigo", ondelete="CASCADE"), primary_key=True
    )
    grandeza: Mapped[Grandeza] = mapped_column(_enum(Grandeza), primary_key=True)
    data_hora_utc: Mapped[datetime] = mapped_column(DataHoraUtc(), primary_key=True)
    origem: Mapped[OrigemDado] = mapped_column(_enum(OrigemDado), primary_key=True)
    valor: Mapped[float] = mapped_column(Float)
    consistencia: Mapped[NivelConsistencia] = mapped_column(_enum(NivelConsistencia))
    status_fonte: Mapped[str | None] = mapped_column(String(50))
    atualizado_na_fonte_em: Mapped[datetime | None] = mapped_column(DataHoraUtc())


class AlertaModelo(Base):
    """Alertas ativos e encerrados. A medição que disparou o alerta é guardada pela chave."""

    __tablename__ = "alertas"
    __table_args__ = (Index("ix_alertas_estacao_status", "codigo_estacao", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    codigo_estacao: Mapped[int] = mapped_column(ForeignKey("estacoes.codigo", ondelete="CASCADE"))
    severidade: Mapped[Severidade] = mapped_column(_enum(Severidade))
    mensagem: Mapped[str] = mapped_column(Text)
    emitido_em: Mapped[datetime] = mapped_column(DataHoraUtc())
    status: Mapped[StatusAlerta] = mapped_column(_enum(StatusAlerta))
    encerrado_em: Mapped[datetime | None] = mapped_column(DataHoraUtc())
    gatilho_grandeza: Mapped[Grandeza | None] = mapped_column(_enum(Grandeza))
    gatilho_data_hora_utc: Mapped[datetime | None] = mapped_column(DataHoraUtc())
    gatilho_origem: Mapped[OrigemDado | None] = mapped_column(_enum(OrigemDado))
