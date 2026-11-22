"""Enumerações do domínio (ver docs/diagramas-de-classe-ana.md, seções 2–4)."""

from enum import StrEnum


class TipoEstacao(StrEnum):
    FLUVIOMETRICA = "FLUVIOMETRICA"
    PLUVIOMETRICA = "PLUVIOMETRICA"


class Grandeza(StrEnum):
    CHUVA = "CHUVA"
    NIVEL = "NIVEL"
    VAZAO = "VAZAO"

    @property
    def unidade(self) -> str:
        return _UNIDADES[self]

    @property
    def rotulo(self) -> str:
        """Nome para exibição ao usuário (ex.: "Nível")."""
        return _ROTULOS_GRANDEZA[self]


_UNIDADES = {Grandeza.CHUVA: "mm", Grandeza.NIVEL: "cm", Grandeza.VAZAO: "m3/s"}
_ROTULOS_GRANDEZA = {Grandeza.CHUVA: "Chuva", Grandeza.NIVEL: "Nível", Grandeza.VAZAO: "Vazão"}


class OrigemDado(StrEnum):
    TELEMETRICA = "TELEMETRICA"
    CONVENCIONAL = "CONVENCIONAL"
    SATELITE = "SATELITE"


class NivelConsistencia(StrEnum):
    BRUTO = "BRUTO"
    CONSISTIDO = "CONSISTIDO"


class Severidade(StrEnum):
    """Classificação normalizada do TaPoo; ordenável de NORMAL a EMERGENCIA."""

    NORMAL = "NORMAL"
    ATENCAO = "ATENCAO"
    ALERTA = "ALERTA"
    EMERGENCIA = "EMERGENCIA"

    @property
    def nivel(self) -> int:
        return list(Severidade).index(self)

    @property
    def rotulo(self) -> str:
        """Nome para exibição ao usuário (ex.: "Atenção")."""
        return _ROTULOS_SEVERIDADE[self]

    # str já define comparações lexicográficas; sobrescrevemos as quatro
    # para que a ordem siga a gravidade, não o texto.
    def __lt__(self, outra: object) -> bool:
        if not isinstance(outra, Severidade):
            return NotImplemented
        return self.nivel < outra.nivel

    def __le__(self, outra: object) -> bool:
        if not isinstance(outra, Severidade):
            return NotImplemented
        return self.nivel <= outra.nivel

    def __gt__(self, outra: object) -> bool:
        if not isinstance(outra, Severidade):
            return NotImplemented
        return self.nivel > outra.nivel

    def __ge__(self, outra: object) -> bool:
        if not isinstance(outra, Severidade):
            return NotImplemented
        return self.nivel >= outra.nivel


_ROTULOS_SEVERIDADE = {
    Severidade.NORMAL: "Normal",
    Severidade.ATENCAO: "Atenção",
    Severidade.ALERTA: "Alerta",
    Severidade.EMERGENCIA: "Emergência",
}


class StatusAlerta(StrEnum):
    ATIVO = "ATIVO"
    ENCERRADO = "ENCERRADO"
