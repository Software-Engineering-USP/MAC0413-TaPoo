"""Repositórios em memória: implementam as portas de `app.aplicacao.portas`.

Servem para a primeira versão e para testes. Os dados somem quando o processo
reinicia; a troca por repositórios SQL não muda serviços nem rotas.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import (
    AlertaRepositorio,
    EstacaoRepositorio,
    MedicaoRepositorio,
    RegraRepositorio,
)
from app.dominio.alerta import Alerta, RegraAlerta
from app.dominio.enums import Grandeza, OrigemDado
from app.dominio.estacao import Estacao
from app.dominio.medicao import Medicao, SerieTemporal
from app.dominio.periodo import Periodo

ChaveMedicao = tuple[int, Grandeza, datetime, OrigemDado]


class EstacaoRepositorioMemoria(EstacaoRepositorio):
    def __init__(self) -> None:
        self._por_codigo: dict[int, Estacao] = {}

    def salvar_varias(self, estacoes: Iterable[Estacao]) -> int:
        total = 0
        for estacao in estacoes:
            self._por_codigo[estacao.codigo] = estacao
            total += 1
        return total

    def por_codigo(self, codigo: int) -> Estacao | None:
        return self._por_codigo.get(codigo)

    def buscar(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return sorted(
            (e for e in self._por_codigo.values() if filtro.aceita(e)), key=lambda e: e.codigo
        )

    def monitoradas(self) -> list[Estacao]:
        return [e for e in self.buscar(FiltroEstacoes(apenas_telemetricas=True)) if e.operando]


class MedicaoRepositorioMemoria(MedicaoRepositorio):
    def __init__(self) -> None:
        self._por_estacao: dict[int, dict[ChaveMedicao, Medicao]] = defaultdict(dict)

    def salvar_varias(self, medicoes: Iterable[Medicao]) -> int:
        total = 0
        for medicao in medicoes:
            # Upsert pela chave natural: dados corrigidos na fonte substituem os antigos.
            self._por_estacao[medicao.codigo_estacao][medicao.chave()] = medicao
            total += 1
        return total

    def serie(self, codigo: int, grandeza: Grandeza, periodo: Periodo) -> SerieTemporal:
        return SerieTemporal(
            codigo,
            grandeza,
            [
                m
                for m in self._por_estacao.get(codigo, {}).values()
                if m.grandeza() is grandeza and periodo.contem(m.data_hora_utc)
            ],
        )

    def ultima_atualizacao(self, codigo: int) -> datetime | None:
        return max(
            (
                m.atualizado_na_fonte_em or m.data_hora_utc
                for m in self._por_estacao.get(codigo, {}).values()
            ),
            default=None,
        )


class AlertaRepositorioMemoria(AlertaRepositorio):
    def __init__(self) -> None:
        self._por_id: dict[UUID, Alerta] = {}

    def salvar(self, alerta: Alerta) -> None:
        self._por_id[alerta.id] = alerta

    def ativo_da_estacao(self, codigo: int) -> Alerta | None:
        return next((a for a in self.ativos() if a.codigo_estacao == codigo), None)

    def ativos(self) -> list[Alerta]:
        return [a for a in self._por_id.values() if a.ativo]


class RegraRepositorioMemoria(RegraRepositorio):
    def __init__(self, regras: Iterable[RegraAlerta] = ()) -> None:
        self._por_estacao: dict[int, list[RegraAlerta]] = defaultdict(list)
        for regra in regras:
            self.adicionar(regra)

    def adicionar(self, regra: RegraAlerta) -> None:
        self._por_estacao[regra.codigo_estacao].append(regra)

    def da_estacao(self, codigo: int) -> list[RegraAlerta]:
        return list(self._por_estacao.get(codigo, []))
