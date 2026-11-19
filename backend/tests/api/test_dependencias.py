from datetime import UTC, datetime

from app.api import dependencias
from app.infra.fontes.ana import FonteAna


def test_monta_container_com_fonte_ana_quando_credenciais_estao_configuradas(monkeypatch) -> None:
    agora = datetime(2026, 11, 18, tzinfo=UTC)
    monkeypatch.setattr(dependencias, "credenciais_ana", lambda: ("id-teste", "senha-teste"))
    monkeypatch.setattr(dependencias, "base_url_ana", lambda: "https://ana.example/api")
    monkeypatch.setattr(dependencias, "timeout_ana", lambda: 5.0)

    container = dependencias.montar_container(relogio=lambda: agora)

    assert isinstance(container.sincronizar._fonte, FonteAna)
    assert container.carregar_na_inicializacao is False
