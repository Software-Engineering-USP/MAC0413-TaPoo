import asyncio
import logging
import threading
from datetime import timedelta

import pytest

from app.infra.agendador import AgendadorColeta

RAPIDO = timedelta(milliseconds=5)


async def _esperar(condicao, limite: float = 2.0) -> None:
    async with asyncio.timeout(limite):
        while not condicao():
            await asyncio.sleep(0.005)


def test_executa_a_acao_repetidamente_ate_parar() -> None:
    chamadas: list[int] = []

    async def cenario() -> None:
        agendador = AgendadorColeta(lambda: chamadas.append(1), RAPIDO)
        agendador.iniciar()
        assert agendador.rodando
        await _esperar(lambda: len(chamadas) >= 3)
        await agendador.parar()
        assert not agendador.rodando
        total = len(chamadas)
        await asyncio.sleep(0.05)
        assert len(chamadas) == total

    asyncio.run(cenario())


def test_falha_em_um_ciclo_nao_interrompe_os_proximos(caplog) -> None:
    chamadas: list[int] = []

    def acao() -> None:
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("fonte fora do ar")

    async def cenario() -> None:
        agendador = AgendadorColeta(acao, RAPIDO)
        agendador.iniciar()
        await _esperar(lambda: len(chamadas) >= 2)
        await agendador.parar()

    with caplog.at_level(logging.ERROR, logger="app.infra.agendador"):
        asyncio.run(cenario())

    assert "Falha no ciclo de coleta" in caplog.text
    assert "fonte fora do ar" in caplog.text


def test_acao_roda_fora_da_thread_do_event_loop() -> None:
    threads: list[int] = []

    async def cenario() -> None:
        agendador = AgendadorColeta(lambda: threads.append(threading.get_ident()), RAPIDO)
        agendador.iniciar()
        await _esperar(lambda: bool(threads))
        await agendador.parar()

    asyncio.run(cenario())
    assert threads[0] != threading.get_ident()


def test_primeiro_ciclo_espera_o_intervalo_por_padrao() -> None:
    chamadas: list[int] = []

    async def cenario() -> None:
        agendador = AgendadorColeta(lambda: chamadas.append(1), timedelta(hours=1))
        agendador.iniciar()
        agendador.iniciar()  # chamar de novo não cria outra tarefa
        await asyncio.sleep(0.05)
        await agendador.parar()
        await agendador.parar()  # parar duas vezes é inofensivo

    asyncio.run(cenario())
    assert chamadas == []


@pytest.mark.parametrize("intervalo", [timedelta(0), timedelta(seconds=-1)])
def test_rejeita_intervalo_nao_positivo(intervalo) -> None:
    with pytest.raises(ValueError, match="intervalo"):
        AgendadorColeta(lambda: None, intervalo)
