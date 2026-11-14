from fastapi import APIRouter

from app.api.dependencias import Consulta
from app.api.schemas import AlertaOut

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("", response_model=list[AlertaOut])
def alertas_ativos(consulta: Consulta) -> list[AlertaOut]:
    """Alertas ativos, do mais grave para o menos grave."""
    return [AlertaOut.de(a) for a in consulta.alertas_ativos()]
