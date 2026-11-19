from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencias import Consulta, Sincronizar
from app.api.schemas import SituacaoMunicipioOut
from app.aplicacao.filtros import FiltroEstacoes

router = APIRouter(prefix="/municipios", tags=["municípios"])


# A UF faz parte do caminho porque há municípios homônimos em estados diferentes.
@router.get("/{uf}/{nome}/situacao")
def situacao_do_municipio(
    consulta: Consulta,
    sincronizar: Sincronizar,
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    nome: Annotated[str, Path(min_length=1)],
) -> SituacaoMunicipioOut:
    """Pior situação entre as estações do município; o nome é comparado sem acentos."""
    # A carga inicial pode ter sido adiada (fonte ANA): traz as estações da UF antes.
    sincronizar.executar(FiltroEstacoes(uf=uf))
    return SituacaoMunicipioOut.de(consulta.situacao_municipio(uf, nome))
