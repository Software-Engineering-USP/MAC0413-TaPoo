"""Compatibilidade com o nome legado da fonte sintética."""

from app.infra.fontes.simulada import FonteSimulada, regras_de_exemplo

FonteFake = FonteSimulada

__all__ = ["FonteFake", "FonteSimulada", "regras_de_exemplo"]
