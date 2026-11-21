"""Leitura simples de configuração por ambiente e arquivo local `.env`."""

from __future__ import annotations

import os
from pathlib import Path

_ARQUIVO_ENV = Path(__file__).resolve().parents[2] / ".env"


def _carregar_env_local() -> None:
    """Carrega `.env` no desenvolvimento sem substituir variáveis já exportadas."""
    if not _ARQUIVO_ENV.is_file():
        return
    for linha in _ARQUIVO_ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        nome, valor = nome.strip(), valor.strip().strip("\"'")
        if nome:
            os.environ.setdefault(nome, valor)


def credenciais_ana() -> tuple[str, str] | None:
    """Retorna credenciais completas; rejeita configuração parcial."""
    _carregar_env_local()
    identificador = os.getenv("ANA_IDENTIFICADOR", "").strip()
    senha = os.getenv("ANA_SENHA", "")
    if bool(identificador) != bool(senha):
        raise RuntimeError("Preencha ANA_IDENTIFICADOR e ANA_SENHA juntos no arquivo .env.")
    return (identificador, senha) if identificador and senha else None


def base_url_ana() -> str:
    _carregar_env_local()
    return (
        os.getenv(
            "ANA_BASE_URL",
            "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas",
        )
        .strip()
        .rstrip("/")
    )


def timeout_ana() -> float:
    _carregar_env_local()
    try:
        valor = float(os.getenv("ANA_TIMEOUT_SEGUNDOS", "20"))
    except ValueError as erro:
        raise RuntimeError("ANA_TIMEOUT_SEGUNDOS precisa ser um número.") from erro
    if valor <= 0:
        raise RuntimeError("ANA_TIMEOUT_SEGUNDOS precisa ser maior que zero.")
    return valor


REPOSITORIOS = ("memoria", "sql")


def tipo_repositorio() -> str:
    """Onde os dados ficam: `REPO=memoria` (padrão, some ao reiniciar) ou `REPO=sql`."""
    _carregar_env_local()
    valor = os.getenv("REPO", "memoria").strip().casefold() or "memoria"
    if valor not in REPOSITORIOS:
        raise RuntimeError(f"REPO precisa ser um de: {', '.join(REPOSITORIOS)}.")
    return valor


def url_banco() -> str:
    """URL do banco usado com `REPO=sql`. Sem `DATABASE_URL`, um SQLite local."""
    _carregar_env_local()
    return os.getenv("DATABASE_URL", "").strip() or "sqlite:///tapoo.db"
