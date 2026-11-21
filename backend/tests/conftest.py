import pytest


@pytest.fixture(autouse=True)
def _repositorio_em_memoria(monkeypatch) -> None:
    """Os testes não usam o banco do `.env` local; quem precisa de SQL pede explicitamente."""
    monkeypatch.setenv("REPO", "memoria")
