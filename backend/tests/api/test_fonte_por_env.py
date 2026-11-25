import pytest

from app.api.dependencias import criar_fonte
from app.infra.fontes.ana import FonteAna
from app.infra.fontes.simulada import FonteSimulada


def test_fonte_ana_exige_credencial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FONTE", "ana")
    monkeypatch.delenv("ANA_IDENTIFICADOR", raising=False)
    monkeypatch.delenv("ANA_SENHA", raising=False)
    with pytest.raises(RuntimeError, match="ANA_IDENTIFICADOR"):
        criar_fonte()


def test_fonte_ana_retorna_fonte_ana(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FONTE", "ana")
    monkeypatch.setenv("ANA_IDENTIFICADOR", "id")
    monkeypatch.setenv("ANA_SENHA", "senha")
    assert isinstance(criar_fonte(), FonteAna)


def test_fonte_simulada_retorna_fonte_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FONTE", "simulada")
    assert isinstance(criar_fonte(), FonteSimulada)


def test_fonte_desconhecida_falha_com_erro_explicito(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FONTE", "anaa")
    with pytest.raises(RuntimeError, match="FONTE precisa ser um de"):
        criar_fonte()


def test_sem_fonte_env_e_com_credencial_ana(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FONTE", raising=False)
    monkeypatch.setenv("ANA_IDENTIFICADOR", "id")
    monkeypatch.setenv("ANA_SENHA", "senha")
    assert isinstance(criar_fonte(), FonteAna)


def test_sem_fonte_env_e_sem_credencial_ana(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FONTE", raising=False)
    monkeypatch.delenv("ANA_IDENTIFICADOR", raising=False)
    monkeypatch.delenv("ANA_SENHA", raising=False)
    assert isinstance(criar_fonte(), FonteSimulada)
