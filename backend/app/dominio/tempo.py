"""Utilitários de data/hora: o domínio trabalha sempre em UTC com fuso explícito."""

from datetime import UTC, datetime


def exigir_utc(valor: datetime, campo: str = "data/hora") -> datetime:
    """Rejeita datetimes sem fuso e normaliza os demais para UTC."""
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError(f"{campo} precisa ter fuso horário (recebido: {valor!r})")
    return valor.astimezone(UTC)


def agora_utc() -> datetime:
    return datetime.now(UTC)
