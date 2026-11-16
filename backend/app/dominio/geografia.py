"""Objetos de valor geográficos (docs/diagramas-de-classe-ana.md, seção 2)."""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_KM = 6371.0


@dataclass(frozen=True, slots=True)
class Coordenada:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"latitude fora do intervalo [-90, 90]: {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"longitude fora do intervalo [-180, 180]: {self.longitude}")

    def distancia_km(self, outra: "Coordenada") -> float:
        """Distância de grande círculo (fórmula de haversine)."""
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(outra.latitude), radians(outra.longitude)
        h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
        return 2 * RAIO_TERRA_KM * asin(sqrt(h))
