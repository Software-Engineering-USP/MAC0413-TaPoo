from datetime import UTC, datetime, timedelta

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.alerta import Alerta
from app.dominio.enums import Grandeza, Severidade, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import MedicaoChuva, MedicaoNivel
from app.dominio.periodo import Periodo
from app.infra.memoria.repositorios import (
    AlertaRepositorioMemoria,
    EstacaoRepositorioMemoria,
    MedicaoRepositorioMemoria,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_medicao_upsert_pela_chave_natural() -> None:
    repo = MedicaoRepositorioMemoria()
    repo.salvar_varias([MedicaoNivel(1, T0, 100), MedicaoChuva(1, T0, 5)])
    repo.salvar_varias([MedicaoNivel(1, T0, 120)])  # correção vinda da fonte

    serie = repo.serie(1, Grandeza.NIVEL, Periodo.ultimos(timedelta(hours=1), ate=T0))
    assert [m.valor for m in serie.medicoes] == [120]
    assert len(repo.serie(1, Grandeza.CHUVA, Periodo.ultimos(timedelta(hours=1), ate=T0))) == 1


def test_ultima_atualizacao_prefere_data_da_fonte() -> None:
    repo = MedicaoRepositorioMemoria()
    assert repo.ultima_atualizacao(1) is None
    corrigida_em = T0 + timedelta(days=1)
    repo.salvar_varias(
        [
            MedicaoNivel(1, T0, 100, atualizado_na_fonte_em=corrigida_em),
            MedicaoNivel(1, T0 + timedelta(hours=1), 101),
        ]
    )
    assert repo.ultima_atualizacao(1) == corrigida_em


def test_estacoes_filtro_e_monitoradas() -> None:
    repo = EstacaoRepositorioMemoria()

    def estacao(codigo: int, uf: str, **kw) -> Estacao:
        return Estacao(codigo, "x", TipoEstacao.PLUVIOMETRICA, Coordenada(0, 0), uf, "y", **kw)

    repo.salvar_varias(
        [estacao(3, "SP"), estacao(1, "MG", telemetrica=False), estacao(2, "SP", operando=False)]
    )
    assert [e.codigo for e in repo.buscar(FiltroEstacoes())] == [1, 2, 3]
    assert [e.codigo for e in repo.buscar(FiltroEstacoes(uf="sp"))] == [2, 3]
    assert [e.codigo for e in repo.monitoradas()] == [3]


def test_alerta_ativo_da_estacao() -> None:
    repo = AlertaRepositorioMemoria()
    alerta = Alerta(1, Severidade.ALERTA, "x", T0)
    repo.salvar(alerta)
    assert repo.ativo_da_estacao(1) is alerta
    alerta.encerrar(T0)
    repo.salvar(alerta)
    assert repo.ativo_da_estacao(1) is None
    assert repo.ativos() == []
