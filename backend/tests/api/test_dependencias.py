from datetime import UTC, datetime

from app.api import dependencias
from app.infra.fontes.ana import FonteAna
from app.infra.fontes.fake import FonteFake
from app.infra.memoria.repositorios import EstacaoRepositorioMemoria


def test_monta_container_com_fonte_ana_quando_credenciais_estao_configuradas(monkeypatch) -> None:
    agora = datetime(2026, 11, 18, tzinfo=UTC)
    monkeypatch.setattr(dependencias, "credenciais_ana", lambda: ("id-teste", "senha-teste"))
    monkeypatch.setattr(dependencias, "base_url_ana", lambda: "https://ana.example/api")
    monkeypatch.setattr(dependencias, "timeout_ana", lambda: 5.0)

    container = dependencias.montar_container(relogio=lambda: agora)

    assert isinstance(container.sincronizar._fonte, FonteAna)
    assert container.carregar_na_inicializacao is False


def test_repo_sql_guarda_os_dados_entre_reinicios(monkeypatch, tmp_path) -> None:
    """Com REPO=sql, um container novo (API reiniciada) enxerga o que o anterior gravou."""
    agora = datetime(2026, 1, 10, 12, tzinfo=UTC)
    monkeypatch.setenv("REPO", "sql")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'tapoo.db'}")

    primeiro = dependencias.montar_container(FonteFake(agora), relogio=lambda: agora)
    dependencias.carga_inicial(primeiro)
    antes = {a.id: a.fatores for a in primeiro.consulta.alertas_ativos()}
    assert antes
    assert all(antes.values())

    depois_do_reinicio = dependencias.montar_container(FonteFake(agora), relogio=lambda: agora)
    assert {a.id: a.fatores for a in depois_do_reinicio.consulta.alertas_ativos()} == antes
    assert depois_do_reinicio.coletar.executar(90000001) == 0  # nada novo para buscar
    # Mesmas medições, mesma avaliação: o alerta lido do banco não muda nem é regravado.
    monitorar = depois_do_reinicio.coletar._monitorar
    assert all(
        monitorar.executar(a.codigo_estacao) is None for a in primeiro.consulta.alertas_ativos()
    )


def test_repo_memoria_e_o_padrao() -> None:
    repos = dependencias.criar_repositorios()
    assert isinstance(repos.estacoes, EstacaoRepositorioMemoria)


def test_regras_de_exemplo_so_acompanham_a_fonte_simulada(monkeypatch) -> None:
    """Com a ANA, as cotas fictícias das estações 9000000x não podem ser carregadas (#175)."""
    agora = datetime(2026, 11, 18, tzinfo=UTC)
    monkeypatch.setenv("REPO", "memoria")
    monkeypatch.setattr(dependencias, "credenciais_ana", lambda: ("id-teste", "senha-teste"))

    com_ana = dependencias.montar_container(relogio=lambda: agora)
    simulado = dependencias.montar_container(FonteFake(agora), relogio=lambda: agora)

    assert com_ana.consulta._regras.da_estacao(90000001) == []
    assert simulado.consulta._regras.da_estacao(90000001)


def test_fonte_real_nao_traz_regras_iniciais() -> None:
    assert FonteAna("id", "senha").regras_iniciais() == []
    assert FonteFake().regras_iniciais()
