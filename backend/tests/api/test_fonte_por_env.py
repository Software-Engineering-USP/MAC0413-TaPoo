import json

import pytest

from app.api.dependencias import criar_fonte, criar_repositorios
from app.aplicacao.filtros import FiltroEstacoes
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


def test_fonte_simulada_carrega_caminho_configurado(monkeypatch, tmp_path) -> None:
    arquivo = tmp_path / "cenario.json"
    arquivo.write_text(
        json.dumps(
            {
                "estacoes": [
                    {
                        "codigo": 123,
                        "nome": "Estação configurada",
                        "tipo": "PLUVIOMETRICA",
                        "latitude": -23.5,
                        "longitude": -46.6,
                        "uf": "SP",
                        "municipio": "São Paulo",
                        "perfis": {},
                    }
                ],
                "regras": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FONTE", "simulada")
    monkeypatch.setenv("CENARIO_SIMULADO", str(arquivo))

    fonte = criar_fonte()

    assert isinstance(fonte, FonteSimulada)
    assert [estacao.codigo for estacao in fonte.listar_estacoes(FiltroEstacoes())] == [123]


def test_fonte_ana_nao_usa_regras_ficticias_sem_arquivo_configurado(monkeypatch) -> None:
    monkeypatch.setenv("FONTE", "ana")
    monkeypatch.setenv("ANA_IDENTIFICADOR", "id")
    monkeypatch.setenv("ANA_SENHA", "senha")
    monkeypatch.delenv("REGRAS_ARQUIVO", raising=False)

    assert criar_repositorios("memoria").regras.da_estacao(90000001) == []


def test_fonte_ana_carrega_regras_do_arquivo_configurado(monkeypatch, tmp_path) -> None:
    arquivo = tmp_path / "regras.json"
    arquivo.write_text(
        json.dumps(
            {
                "regras": [
                    {
                        "tipo": "cota_referencia",
                        "codigo_estacao": 123,
                        "cota_atencao_cm": 100,
                        "cota_alerta_cm": 200,
                        "cota_inundacao_cm": 300,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FONTE", "ana")
    monkeypatch.setenv("ANA_IDENTIFICADOR", "id")
    monkeypatch.setenv("ANA_SENHA", "senha")
    monkeypatch.setenv("REGRAS_ARQUIVO", str(arquivo))

    regras = criar_repositorios("memoria").regras.da_estacao(123)

    assert len(regras) == 1
    assert regras[0].codigo_estacao == 123
