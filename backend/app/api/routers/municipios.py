from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencias import Consulta
from app.api.schemas import SituacaoMunicipioOut

router = APIRouter(prefix="/municipios", tags=["municípios"])


# A UF faz parte do caminho porque há municípios homônimos em estados diferentes.
@router.get("/{uf}/{nome}/situacao")
def situacao_do_municipio(
    consulta: Consulta,
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    nome: Annotated[str, Path(min_length=1)],
) -> SituacaoMunicipioOut:
    """Pior situação entre as estações do município; o nome é comparado sem acentos."""
    return SituacaoMunicipioOut.de(consulta.situacao_municipio(uf, nome))
