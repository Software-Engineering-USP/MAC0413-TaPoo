"""Fonte determinística para demonstrações, configurada pelo arquivo cenario-demo.json."""

import json
from datetime import datetime, timedelta
from math import sin
from pathlib import Path
from typing import Any

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.dominio.alerta import (
    RegraAlerta,
    RegraChuvaAcumulada,
    RegraChuvaPrevisao,
    RegraCotaReferencia,
)
from app.dominio.enums import OrigemDados, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva, MedicaoNivel, MedicaoVazao
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc, exigir_utc

HISTORICO = timedelta(days=7)
ARQUIVO_CENARIO = Path(__file__).with_name("dados") / "cenario-demo.json"
_CLASSES_MEDICAO = {
    "chuva": MedicaoChuva,
    "nivel": MedicaoNivel,
    "vazao": MedicaoVazao,
}


def _ler_cenario(
    arquivo: Path = ARQUIVO_CENARIO, *, exigir_estacoes: bool = True
) -> dict[str, Any]:
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise RuntimeError(f"Não foi possível carregar o cenário simulado: {arquivo}.") from erro
    if not isinstance(dados, dict):
        raise TypeError("Cenário simulado inválido: esperado um objeto JSON.")
    if exigir_estacoes and not isinstance(dados.get("estacoes"), list):
        raise TypeError("Cenário simulado inválido: informe a lista de estações.")
    if not exigir_estacoes and not isinstance(dados.get("regras"), list):
        raise TypeError("Cenário simulado inválido: informe as regras em uma lista.")
    if "regras" in dados and not isinstance(dados["regras"], list):
        raise TypeError("Cenário simulado inválido: informe as regras em uma lista.")
    return dados


def _obter(item: dict[str, Any], campo: str, contexto: str) -> Any:
    try:
        return item[campo]
    except KeyError as erro:
        raise ValueError(f"{contexto}: campo obrigatório '{campo}' ausente.") from erro


def regras_de_exemplo(arquivo: Path = ARQUIVO_CENARIO) -> list[RegraAlerta]:
    """Lê regras de alerta de um cenário ou de um arquivo independente de regras."""
    regras = []
    for indice, item in enumerate(_ler_cenario(arquivo, exigir_estacoes=False).get("regras", [])):
        contexto = f"Regra {indice + 1}"
        if not isinstance(item, dict):
            raise TypeError(f"{contexto}: cada regra deve ser um objeto.")
        tipo = _obter(item, "tipo", contexto)
        codigo = _converter(int, _obter(item, "codigo_estacao", contexto), contexto)
        janela = timedelta(
            hours=_converter(float, item.get("janela_horas", 24), f"{contexto}, janela_horas")
        )
        if tipo == "cota_referencia":
            valores = [
                _converter(float, _obter(item, campo, contexto), contexto)
                for campo in ("cota_atencao_cm", "cota_alerta_cm", "cota_inundacao_cm")
            ]
            regra = RegraCotaReferencia(
                codigo,
                *valores,
            )
        elif tipo == "chuva_acumulada":
            _validar_limites_chuva(item, contexto)
            regra = RegraChuvaAcumulada(codigo, janela, *_limites_chuva(item))
        elif tipo == "chuva_previsao":
            _validar_limites_chuva(item, contexto)
            regra = RegraChuvaPrevisao(
                codigo,
                Coordenada(
                    _converter(float, _obter(item, "latitude", contexto), contexto),
                    _converter(float, _obter(item, "longitude", contexto), contexto),
                ),
                janela,
                *_limites_chuva(item),
            )
        else:
            raise ValueError(f"{contexto}: tipo desconhecido '{tipo}'.")
        regras.append(regra)
    return regras


Perfil = dict[str, Any]


class FonteSimulada(FonteDadosHidrologicos):
    """Gera séries horárias fictícias a partir dos perfis definidos em JSON."""

    def __init__(
        self,
        agora: datetime | None = None,
        *,
        arquivo: Path = ARQUIVO_CENARIO,
    ) -> None:
        self._agora = exigir_utc(agora or agora_utc()).replace(minute=0, second=0, microsecond=0)
        dados = _ler_cenario(arquivo)
        self._dados: list[tuple[Estacao, dict[str, Perfil]]] = []
        codigos: set[int] = set()
        for indice, item in enumerate(dados["estacoes"]):
            contexto = f"Estação {indice + 1}"
            if not isinstance(item, dict):
                raise TypeError(f"{contexto}: cada estação deve ser um objeto.")
            codigo = _converter(int, _obter(item, "codigo", contexto), contexto)
            if codigo in codigos:
                raise ValueError(f"{contexto}: código duplicado {codigo}.")
            codigos.add(codigo)
            for campo in ("nome", "tipo", "latitude", "longitude", "uf", "municipio"):
                _obter(item, campo, f"Estação {codigo}")
            estacao = Estacao(
                codigo=codigo,
                nome=str(item["nome"]),
                tipo=_converter(TipoEstacao, item["tipo"], f"Estação {codigo}, campo 'tipo'"),
                coordenada=Coordenada(
                    _converter(float, item["latitude"], f"Estação {codigo}, latitude"),
                    _converter(float, item["longitude"], f"Estação {codigo}, longitude"),
                ),
                uf=str(item["uf"]),
                municipio=str(item["municipio"]),
                rio=item.get("rio"),
                operando=_booleano(item.get("operando", True), f"Estação {codigo}, operando"),
                telemetrica=_booleano(
                    item.get("telemetrica", True), f"Estação {codigo}, telemetrica"
                ),
            )
            perfis = item.get("perfis", {})
            if not isinstance(perfis, dict) or not set(perfis).issubset(_CLASSES_MEDICAO):
                raise ValueError(f"Perfis de medição inválidos para a estação {codigo}.")
            self._validar_perfis(codigo, perfis)
            self._dados.append((estacao, perfis))

    @property
    def origem_dados(self) -> OrigemDados:
        return OrigemDados.SIMULADO

    @staticmethod
    def _validar_perfis(codigo: int, perfis: dict[str, Perfil]) -> None:
        campos = {
            "linear": ("minimo", "valor_atual", "queda_por_hora"),
            "senoide": ("amplitude", "periodo_horas"),
            "senoide_positiva": ("amplitude", "periodo_horas"),
            "recente": ("valor_recente", "horas_recentes", "valor_anterior"),
            "constante": ("valor",),
            "vazao_por_nivel": ("perfil_nivel", "coeficiente", "expoente"),
        }
        for grandeza, perfil in perfis.items():
            contexto = f"Estação {codigo}, perfil '{grandeza}'"
            if not isinstance(perfil, dict):
                raise TypeError(f"{contexto}: o perfil deve ser um objeto.")
            tipo = _obter(perfil, "tipo", contexto)
            if not isinstance(tipo, str) or tipo not in campos:
                raise ValueError(f"{contexto}: tipo desconhecido '{tipo}'.")
            for campo in campos[tipo]:
                _obter(perfil, campo, contexto)
            for campo in campos[tipo]:
                if campo != "perfil_nivel":
                    _converter(float, perfil[campo], f"{contexto}, campo '{campo}'")
            if tipo == "senoide":
                perfil.setdefault("base", 0)
                _converter(float, perfil["base"], f"{contexto}, campo 'base'")
            if "casas" in perfil:
                _converter(int, perfil["casas"], f"{contexto}, campo 'casas'")
            if tipo in ("senoide", "senoide_positiva"):
                periodo = float(perfil["periodo_horas"])
                if periodo == 0:
                    raise ValueError(f"{contexto}: periodo_horas deve ser diferente de zero.")
            if tipo == "vazao_por_nivel":
                referencia = str(perfil["perfil_nivel"])
                if referencia == grandeza or referencia not in perfis:
                    raise ValueError(f"{contexto}: perfil_nivel inválido '{referencia}'.")
                perfil_referenciado = perfis[referencia]
                if (
                    not isinstance(perfil_referenciado, dict)
                    or perfil_referenciado.get("tipo") == "vazao_por_nivel"
                ):
                    raise ValueError(f"{contexto}: referência circular em perfil_nivel.")

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return [estacao for estacao, _ in self._dados if filtro.aceita(estacao)]

    def buscar_estacao(self, codigo: int) -> Estacao | None:
        return next((estacao for estacao, _ in self._dados if estacao.codigo == codigo), None)

    def buscar_medicoes(
        self, codigo: int, periodo: Periodo, alteradas_desde: datetime | None = None
    ) -> list[Medicao]:
        perfis = next((perfis for estacao, perfis in self._dados if estacao.codigo == codigo), None)
        if perfis is None:
            return []
        medicoes = []
        for instante in self._horas(periodo):
            if alteradas_desde is not None and instante <= exigir_utc(alteradas_desde):
                continue
            horas_atras = (self._agora - instante) / timedelta(hours=1)
            for grandeza in perfis:
                valor = self._avaliar_perfil(perfis, grandeza, horas_atras)
                medicoes.append(
                    _CLASSES_MEDICAO[grandeza](
                        codigo,
                        instante,
                        valor,
                        atualizado_na_fonte_em=instante,
                    )
                )
        return medicoes

    def _horas(self, periodo: Periodo) -> list[datetime]:
        inicio = max(periodo.inicio, self._agora - HISTORICO)
        fim = min(periodo.fim, self._agora)
        atual = inicio.replace(minute=0, second=0, microsecond=0)
        if atual < inicio:
            atual += timedelta(hours=1)
        horas = []
        while atual <= fim:
            horas.append(atual)
            atual += timedelta(hours=1)
        return horas

    @classmethod
    def _avaliar_perfil(cls, perfis: dict[str, Perfil], nome: str, horas_atras: float) -> float:
        perfil = perfis[nome]
        tipo = perfil["tipo"]
        if tipo == "linear":
            return max(
                float(perfil["minimo"]),
                float(perfil["valor_atual"]) - float(perfil["queda_por_hora"]) * horas_atras,
            )
        if tipo in ("senoide", "senoide_positiva"):
            valor = float(perfil.get("base", 0)) + float(perfil["amplitude"]) * sin(
                horas_atras / float(perfil["periodo_horas"])
            )
            if tipo == "senoide_positiva":
                valor = max(0.0, valor)
            casas = perfil.get("casas")
            return round(valor, int(casas)) if casas is not None else valor
        if tipo == "recente":
            chave = (
                "valor_recente"
                if horas_atras < float(perfil["horas_recentes"])
                else "valor_anterior"
            )
            return float(perfil[chave])
        if tipo == "constante":
            return float(perfil["valor"])
        if tipo == "vazao_por_nivel":
            nivel = cls._avaliar_perfil(perfis, str(perfil["perfil_nivel"]), horas_atras)
            valor = float(perfil["coeficiente"]) * nivel ** float(perfil["expoente"])
            return round(valor, int(perfil.get("casas", 1)))
        raise ValueError(f"Perfil desconhecido no cenário simulado: {tipo}.")


def _converter(conversor, valor: Any, contexto: str):
    try:
        return conversor(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{contexto}: valor inválido '{valor}'.") from erro


def _booleano(valor: Any, contexto: str) -> bool:
    if not isinstance(valor, bool):
        raise TypeError(f"{contexto}: esperado valor booleano.")
    return valor


def _validar_limites_chuva(item: dict[str, Any], contexto: str) -> None:
    for campo in ("limite_moderado_mm", "limite_alto_mm", "limite_extremo_mm"):
        _converter(float, _obter(item, campo, contexto), contexto)


def _limites_chuva(item: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(item["limite_moderado_mm"]),
        float(item["limite_alto_mm"]),
        float(item["limite_extremo_mm"]),
    )
