"""Repositórios SQL: implementam as portas de `app.aplicacao.portas` (diagrama, seção 6).

Funcionam com SQLite (desenvolvimento e testes) e Postgres (deploy). Cada operação abre e
fecha a sua transação, então os repositórios podem ser usados pelas rotas e pelo
agendador ao mesmo tempo.
"""

from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime
from itertools import batched
from typing import Any

from sqlalchemy import Engine, create_engine, event, func, select, type_coerce
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import AlertaRepositorio, EstacaoRepositorio, MedicaoRepositorio
from app.dominio.alerta import Alerta
from app.dominio.enums import Grandeza, StatusAlerta
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, SerieTemporal, classe_de_medicao
from app.dominio.periodo import Periodo
from app.infra.persistencia.modelos_orm import (
    AlertaModelo,
    Base,
    DataHoraUtc,
    EstacaoModelo,
    MedicaoModelo,
)

# Linhas por comando INSERT: fica abaixo do limite de parâmetros do SQLite e do Postgres.
TAMANHO_LOTE = 500


def normalizar_url(url: str) -> str:
    """Usa o driver psycopg 3 para Postgres; hospedagens costumam dar `postgres://...`."""
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url.removeprefix(prefixo)
    return url


def criar_engine(url: str) -> Engine:
    url = normalizar_url(url)
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)
    # O agendador grava em outra thread; SQLite em memória precisa de uma só conexão.
    opcoes: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
    if url in ("sqlite://", "sqlite:///:memory:"):
        opcoes["poolclass"] = StaticPool
    engine = create_engine(url, **opcoes)

    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(conexao, _registro) -> None:
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


class BancoDeDados:
    """Engine e fábrica de sessões compartilhadas pelos repositórios SQL."""

    def __init__(self, url: str) -> None:
        self.engine = criar_engine(url)
        self.sessoes = sessionmaker(self.engine, expire_on_commit=False)

    def criar_tabelas(self) -> None:
        Base.metadata.create_all(self.engine)

    def apagar_tabelas(self) -> None:
        Base.metadata.drop_all(self.engine)


def _upsert(
    sessao: Session, modelo: type[Base], linhas: Sequence[dict], chave: tuple[str, ...]
) -> None:
    """INSERT ... ON CONFLICT DO UPDATE, em lotes. Funciona no SQLite e no Postgres."""
    dialeto = postgresql if sessao.get_bind().dialect.name == "postgresql" else sqlite
    tabela = modelo.__table__
    for lote in batched(linhas, TAMANHO_LOTE):
        comando = dialeto.insert(tabela).values(list(lote))
        atualizar = {
            c.name: comando.excluded[c.name] for c in tabela.columns if c.name not in chave
        }
        sessao.execute(comando.on_conflict_do_update(index_elements=list(chave), set_=atualizar))


def _sem_repetir(linhas: Iterable[dict], chave: tuple[str, ...]) -> list[dict]:
    """Mantém a última linha de cada chave: o Postgres recusa a mesma chave duas vezes num
    único INSERT, e no repositório em memória a última gravação também é a que vale."""
    por_chave = {tuple(linha[c] for c in chave): linha for linha in linhas}
    return list(por_chave.values())


class EstacaoRepositorioSql(EstacaoRepositorio):
    _CHAVE = ("codigo",)

    def __init__(self, banco: BancoDeDados) -> None:
        self._sessoes = banco.sessoes

    def salvar_varias(self, estacoes: Iterable[Estacao]) -> int:
        linhas = [self._para_linha(e) for e in estacoes]
        if linhas:
            with self._sessoes.begin() as sessao:
                _upsert(sessao, EstacaoModelo, _sem_repetir(linhas, self._CHAVE), self._CHAVE)
        return len(linhas)

    def por_codigo(self, codigo: int) -> Estacao | None:
        with self._sessoes() as sessao:
            modelo = sessao.get(EstacaoModelo, codigo)
            return self._para_estacao(modelo) if modelo is not None else None

    def buscar(self, filtro: FiltroEstacoes) -> list[Estacao]:
        consulta = select(EstacaoModelo).order_by(EstacaoModelo.codigo)
        if filtro.uf is not None:
            consulta = consulta.where(EstacaoModelo.uf == filtro.uf.upper())
        if filtro.tipo is not None:
            consulta = consulta.where(EstacaoModelo.tipo == filtro.tipo)
        if filtro.apenas_telemetricas:
            consulta = consulta.where(EstacaoModelo.telemetrica.is_(True))
        # Os critérios que comparam nomes sem acento ficam com o próprio filtro.
        return [e for e in self._listar(consulta) if filtro.aceita(e)]

    def monitoradas(self) -> list[Estacao]:
        consulta = (
            select(EstacaoModelo)
            .where(EstacaoModelo.telemetrica.is_(True), EstacaoModelo.operando.is_(True))
            .order_by(EstacaoModelo.codigo)
        )
        return list(self._listar(consulta))

    def _listar(self, consulta) -> Iterator[Estacao]:
        with self._sessoes() as sessao:
            modelos = sessao.scalars(consulta).all()
        return (self._para_estacao(m) for m in modelos)

    @staticmethod
    def _para_linha(estacao: Estacao) -> dict:
        return {
            "codigo": estacao.codigo,
            "nome": estacao.nome,
            "tipo": estacao.tipo,
            "latitude": estacao.coordenada.latitude,
            "longitude": estacao.coordenada.longitude,
            "uf": estacao.uf,
            "municipio": estacao.municipio,
            "rio": estacao.rio,
            "operando": estacao.operando,
            "telemetrica": estacao.telemetrica,
            "atualizado_em": estacao.atualizado_em,
        }

    @staticmethod
    def _para_estacao(modelo: EstacaoModelo) -> Estacao:
        return Estacao(
            modelo.codigo,
            modelo.nome,
            modelo.tipo,
            Coordenada(modelo.latitude, modelo.longitude),
            modelo.uf,
            modelo.municipio,
            rio=modelo.rio,
            operando=modelo.operando,
            telemetrica=modelo.telemetrica,
            atualizado_em=modelo.atualizado_em,
        )


class MedicaoRepositorioSql(MedicaoRepositorio):
    """Upsert pela chave natural `(codigo_estacao, grandeza, data_hora_utc, origem)`."""

    _CHAVE = ("codigo_estacao", "grandeza", "data_hora_utc", "origem")

    def __init__(self, banco: BancoDeDados) -> None:
        self._sessoes = banco.sessoes

    def salvar_varias(self, medicoes: Iterable[Medicao]) -> int:
        linhas = [self._para_linha(m) for m in medicoes]
        if linhas:
            with self._sessoes.begin() as sessao:
                _upsert(sessao, MedicaoModelo, _sem_repetir(linhas, self._CHAVE), self._CHAVE)
        return len(linhas)

    def serie(self, codigo: int, grandeza: Grandeza, periodo: Periodo) -> SerieTemporal:
        consulta = select(MedicaoModelo).where(
            MedicaoModelo.codigo_estacao == codigo,
            MedicaoModelo.grandeza == grandeza,
            MedicaoModelo.data_hora_utc >= periodo.inicio,
            MedicaoModelo.data_hora_utc <= periodo.fim,
        )
        with self._sessoes() as sessao:
            modelos = sessao.scalars(consulta).all()
        return SerieTemporal(codigo, grandeza, [self.para_medicao(m) for m in modelos])

    def ultima_atualizacao(self, codigo: int) -> datetime | None:
        atualizado = func.coalesce(
            MedicaoModelo.atualizado_na_fonte_em, MedicaoModelo.data_hora_utc
        )
        # `type_coerce` faz o resultado passar pelo mesmo conversor de UTC das colunas.
        consulta = select(type_coerce(func.max(atualizado), DataHoraUtc())).where(
            MedicaoModelo.codigo_estacao == codigo
        )
        with self._sessoes() as sessao:
            return sessao.scalar(consulta)

    @staticmethod
    def _para_linha(medicao: Medicao) -> dict:
        return {
            "codigo_estacao": medicao.codigo_estacao,
            "grandeza": medicao.grandeza(),
            "data_hora_utc": medicao.data_hora_utc,
            "origem": medicao.origem,
            "valor": medicao.valor,
            "consistencia": medicao.consistencia,
            "status_fonte": medicao.status_fonte,
            "atualizado_na_fonte_em": medicao.atualizado_na_fonte_em,
        }

    @staticmethod
    def para_medicao(modelo: MedicaoModelo) -> Medicao:
        return classe_de_medicao(modelo.grandeza)(
            modelo.codigo_estacao,
            modelo.data_hora_utc,
            modelo.valor,
            origem=modelo.origem,
            consistencia=modelo.consistencia,
            status_fonte=modelo.status_fonte,
            atualizado_na_fonte_em=modelo.atualizado_na_fonte_em,
        )


class AlertaRepositorioSql(AlertaRepositorio):
    """Guarda alertas ativos e encerrados. A medição que disparou o alerta é guardada pela
    chave natural e lida de novo da tabela de medições."""

    def __init__(self, banco: BancoDeDados) -> None:
        self._sessoes = banco.sessoes

    def salvar(self, alerta: Alerta) -> None:
        with self._sessoes.begin() as sessao:
            sessao.merge(self._para_modelo(alerta))

    def ativo_da_estacao(self, codigo: int) -> Alerta | None:
        return next(iter(self._listar(codigo_estacao=codigo, status=StatusAlerta.ATIVO)), None)

    def ativos(self) -> list[Alerta]:
        return self._listar(status=StatusAlerta.ATIVO)

    def historico_da_estacao(self, codigo: int, limite: int | None = None) -> list[Alerta]:
        """Alertas ativos e encerrados da estação, do mais recente para o mais antigo."""
        return self._listar(codigo_estacao=codigo, limite=limite)

    def _listar(self, *, limite: int | None = None, **criterios) -> list[Alerta]:
        consulta = (
            select(AlertaModelo)
            .filter_by(**criterios)
            .order_by(AlertaModelo.emitido_em.desc())
            .limit(limite)
        )
        with self._sessoes() as sessao:
            return [self._para_alerta(sessao, m) for m in sessao.scalars(consulta).all()]

    @staticmethod
    def _para_modelo(alerta: Alerta) -> AlertaModelo:
        gatilho = alerta.medicao_gatilho
        return AlertaModelo(
            id=alerta.id,
            codigo_estacao=alerta.codigo_estacao,
            severidade=alerta.severidade,
            mensagem=alerta.mensagem,
            emitido_em=alerta.emitido_em,
            status=alerta.status,
            encerrado_em=alerta.encerrado_em,
            gatilho_grandeza=gatilho.grandeza() if gatilho else None,
            gatilho_data_hora_utc=gatilho.data_hora_utc if gatilho else None,
            gatilho_origem=gatilho.origem if gatilho else None,
        )

    @staticmethod
    def _para_alerta(sessao: Session, modelo: AlertaModelo) -> Alerta:
        gatilho = None
        if modelo.gatilho_grandeza is not None:
            medicao = sessao.get(
                MedicaoModelo,
                (
                    modelo.codigo_estacao,
                    modelo.gatilho_grandeza,
                    modelo.gatilho_data_hora_utc,
                    modelo.gatilho_origem,
                ),
            )
            gatilho = MedicaoRepositorioSql.para_medicao(medicao) if medicao else None
        return Alerta(
            modelo.codigo_estacao,
            modelo.severidade,
            modelo.mensagem,
            modelo.emitido_em,
            medicao_gatilho=gatilho,
            status=modelo.status,
            encerrado_em=modelo.encerrado_em,
            id=modelo.id,
        )
