from datetime import timedelta

import pytest

from app import configuracao


def test_carregar_env_local_ignora_linhas_invalidas_e_preserva_ambiente(
    monkeypatch, tmp_path
) -> None:
    arquivo = tmp_path / ".env"
    arquivo.write_text(
        "\n# comentário\nSEM_IGUAL\n =sem_nome\nCHAVE = 'valor=completo'\nEXPORTADA=arquivo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", arquivo)
    monkeypatch.delenv("CHAVE", raising=False)
    monkeypatch.setenv("EXPORTADA", "ambiente")

    configuracao._carregar_env_local()

    assert configuracao.os.environ["CHAVE"] == "valor=completo"
    assert configuracao.os.environ["EXPORTADA"] == "ambiente"
    assert "SEM_IGUAL" not in configuracao.os.environ


def test_carregar_env_local_sem_arquivo_nao_falha(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")

    configuracao._carregar_env_local()


def test_credenciais_ana_ausentes_parciais_e_completas(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.delenv("ANA_IDENTIFICADOR", raising=False)
    monkeypatch.delenv("ANA_SENHA", raising=False)
    assert configuracao.credenciais_ana() is None

    monkeypatch.setenv("ANA_IDENTIFICADOR", "usuario")
    with pytest.raises(RuntimeError, match="Preencha ANA_IDENTIFICADOR"):
        configuracao.credenciais_ana()

    monkeypatch.setenv("ANA_SENHA", "senha")
    assert configuracao.credenciais_ana() == ("usuario", "senha")


def test_base_url_ana_usa_padrao_e_normaliza_configuracao(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.delenv("ANA_BASE_URL", raising=False)
    assert configuracao.base_url_ana() == (
        "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
    )

    monkeypatch.setenv("ANA_BASE_URL", " https://ana.example/api/// ")
    assert configuracao.base_url_ana() == "https://ana.example/api"


def test_timeout_ana_usa_padrao_e_aceita_numero_positivo(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.delenv("ANA_TIMEOUT_SEGUNDOS", raising=False)
    assert configuracao.timeout_ana() == 20

    monkeypatch.setenv("ANA_TIMEOUT_SEGUNDOS", "3.5")
    assert configuracao.timeout_ana() == 3.5


@pytest.mark.parametrize("valor", ["invalido", "0", "-1"])
def test_timeout_ana_rejeita_valores_invalidos(monkeypatch, tmp_path, valor) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.setenv("ANA_TIMEOUT_SEGUNDOS", valor)

    with pytest.raises(RuntimeError, match="ANA_TIMEOUT_SEGUNDOS"):
        configuracao.timeout_ana()


def test_tipo_repositorio_padrao_e_valores_aceitos(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.delenv("REPO", raising=False)
    assert configuracao.tipo_repositorio() == "memoria"

    monkeypatch.setenv("REPO", " SQL ")
    assert configuracao.tipo_repositorio() == "sql"

    monkeypatch.setenv("REPO", "")
    assert configuracao.tipo_repositorio() == "memoria"


def test_tipo_repositorio_rejeita_valor_desconhecido(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.setenv("REPO", "mongo")

    with pytest.raises(RuntimeError, match="REPO"):
        configuracao.tipo_repositorio()


def test_url_banco_usa_sqlite_local_sem_configuracao(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert configuracao.url_banco() == "sqlite:///tapoo.db"

    monkeypatch.setenv("DATABASE_URL", " postgresql://u:s@db/tapoo ")
    assert configuracao.url_banco() == "postgresql://u:s@db/tapoo"
def test_intervalo_coleta_padrao_valor_e_desligado(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.delenv("COLETA_INTERVALO_MINUTOS", raising=False)
    assert configuracao.intervalo_coleta() == timedelta(minutes=15)

    monkeypatch.setenv("COLETA_INTERVALO_MINUTOS", "0.5")
    assert configuracao.intervalo_coleta() == timedelta(seconds=30)

    monkeypatch.setenv("COLETA_INTERVALO_MINUTOS", "0")
    assert configuracao.intervalo_coleta() is None


@pytest.mark.parametrize("valor", ["invalido", "-1", "nan", "inf", "-inf"])
def test_intervalo_coleta_rejeita_valores_invalidos(monkeypatch, tmp_path, valor) -> None:
    monkeypatch.setattr(configuracao, "_ARQUIVO_ENV", tmp_path / "ausente")
    monkeypatch.setenv("COLETA_INTERVALO_MINUTOS", valor)

    with pytest.raises(RuntimeError, match="COLETA_INTERVALO_MINUTOS"):
        configuracao.intervalo_coleta()
