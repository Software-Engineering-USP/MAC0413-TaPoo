"""Composição da aplicação: liga as portas às implementações concretas.

É o único lugar que conhece `app.infra`. Trocar memória por SQL (`REPO`), ou `FonteFake`
por `FonteAna`, muda só este arquivo.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.consulta import ConsultarDados
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.portas import (
    AlertaRepositorio,
    EstacaoRepositorio,
    FonteDadosHidrologicos,
    FonteDePrevisao,
    MedicaoRepositorio,
    RegraRepositorio,
)
from app.aplicacao.sincronizacao import SincronizarEstacoes
from app.configuracao import (
    base_url_ana,
    credenciais_ana,
    timeout_ana,
    tipo_repositorio,
    url_banco,
)
from app.dominio.tempo import agora_utc
from app.infra.agendador import AgendadorColeta
from app.infra.fontes.ana import FonteAna
from app.infra.fontes.fake import FonteFake, regras_de_exemplo
from app.infra.fontes.openmeteo import FonteOpenMeteo
from app.infra.memoria.repositorios import (
    AlertaRepositorioMemoria,
    EstacaoRepositorioMemoria,
    MedicaoRepositorioMemoria,
    RegraRepositorioMemoria,
)
from app.infra.persistencia.repositorios_sql import (
    AlertaRepositorioSql,
    BancoDeDados,
    EstacaoRepositorioSql,
    MedicaoRepositorioSql,
)


@dataclass(frozen=True, slots=True)
class Container:
    consulta: ConsultarDados
    sincronizar: SincronizarEstacoes
    coletar: ColetarMedicoes
    relogio: Callable[[], datetime]
    carregar_na_inicializacao: bool = True


@dataclass(frozen=True, slots=True)
class Repositorios:
    estacoes: EstacaoRepositorio
    medicoes: MedicaoRepositorio
    alertas: AlertaRepositorio
    regras: RegraRepositorio


def criar_fonte(relogio: Callable[[], datetime] = agora_utc) -> FonteDadosHidrologicos:
    """Escolhe a `FonteDadosHidrologicos` pela variável de ambiente `FONTE`.

    `FONTE=ana` exige credenciais. `FONTE=fake`/`simulada` usa dados fictícios.
    Sem `FONTE`, mantém o comportamento anterior: ANA com credenciais, simulada sem.
    """
    credencial = credenciais_ana()
    var = (os.getenv("FONTE") or "").strip().casefold()
    if var not in ("", "ana", "fake", "simulada"):
        raise RuntimeError("FONTE precisa ser um de: ana, fake, simulada.")
    if var == "ana":
        if credencial is None:
            raise RuntimeError("FONTE=ana exige ANA_IDENTIFICADOR e ANA_SENHA.")
        return FonteAna(*credencial, base_url=base_url_ana(), timeout=timeout_ana())
    if var in ("fake", "simulada"):
        return FonteFake(relogio())
    if credencial is not None:
        return FonteAna(*credencial, base_url=base_url_ana(), timeout=timeout_ana())
    return FonteFake(relogio())


def criar_repositorios(tipo: str | None = None, url: str | None = None) -> Repositorios:
    """Escolhe repositórios por `REPO=memoria|sql` e `DATABASE_URL` no caso SQL."""
    if (tipo or tipo_repositorio()) == "sql":
        return repositorios_sql(BancoDeDados(url or url_banco()))
    return Repositorios(
        EstacaoRepositorioMemoria(),
        MedicaoRepositorioMemoria(),
        AlertaRepositorioMemoria(),
        RegraRepositorioMemoria(regras_de_exemplo()),
    )


def repositorios_sql(banco: BancoDeDados) -> Repositorios:
    """Repositórios SQL sobre `banco`, criando as tabelas que ainda não existem."""
    banco.criar_tabelas()
    return Repositorios(
        EstacaoRepositorioSql(banco),
        MedicaoRepositorioSql(banco),
        AlertaRepositorioSql(banco),
        RegraRepositorioMemoria(regras_de_exemplo()),
    )


def montar_container(
    fonte: FonteDadosHidrologicos | None = None,
    relogio: Callable[[], datetime] = agora_utc,
    fonte_previsao: FonteDePrevisao | None = None,
    repositorios: Repositorios | None = None,
) -> Container:
    if fonte is None:
        fonte = criar_fonte(relogio)
        if fonte_previsao is None:
            fonte_previsao = FonteOpenMeteo()
    repositorios = repositorios or criar_repositorios()
    monitorar = MonitorarEstacoes(
        repositorios.medicoes,
        repositorios.regras,
        repositorios.alertas,
        fonte_previsao=fonte_previsao,
        relogio=relogio,
    )
    return Container(
        consulta=ConsultarDados(repositorios.estacoes, repositorios.medicoes, repositorios.alertas),
        sincronizar=SincronizarEstacoes(fonte, repositorios.estacoes),
        coletar=ColetarMedicoes(
            fonte,
            repositorios.estacoes,
            repositorios.medicoes,
            monitorar,
            relogio=relogio,
        ),
        relogio=relogio,
        carregar_na_inicializacao=fonte.carregar_na_inicializacao,
    )


def carga_inicial(container: Container) -> None:
    """Sincroniza estações; fontes pequenas também carregam séries de exemplo."""
    if container.carregar_na_inicializacao:
        container.sincronizar.executar()
        executar_ciclo(container)


def executar_ciclo(container: Container) -> int:
    """Coleta as estações monitoradas e reavalia os alertas, sem sincronizar inventário."""
    return container.coletar.executar_todas()


def criar_agendador(container: Container, intervalo: timedelta) -> AgendadorColeta:
    return AgendadorColeta(lambda: executar_ciclo(container), intervalo)


def _container(request: Request) -> Container:
    return request.app.state.container


def get_consulta(request: Request) -> ConsultarDados:
    return _container(request).consulta


def get_relogio(request: Request) -> Callable[[], datetime]:
    return _container(request).relogio


def get_coletar(request: Request) -> ColetarMedicoes:
    return _container(request).coletar


def get_sincronizar(request: Request) -> SincronizarEstacoes:
    return _container(request).sincronizar


Consulta = Annotated[ConsultarDados, Depends(get_consulta)]
Relogio = Annotated[Callable[[], datetime], Depends(get_relogio)]
Coletar = Annotated[ColetarMedicoes, Depends(get_coletar)]
Sincronizar = Annotated[SincronizarEstacoes, Depends(get_sincronizar)]
