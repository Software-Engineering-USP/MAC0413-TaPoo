import json

from app.dominio.geografia import Coordenada
from app.infra.normais.inmet import NormaisInmet


def test_arquivo_versionado_tem_as_normais_1991_2020() -> None:
    normais = NormaisInmet().todas()
    assert len(normais) == 221
    assert all(len(n.chuva_mensal_mm) == 12 for n in normais)
    sao_paulo = next(n for n in normais if n.codigo == 83781)
    assert sao_paulo.uf == "SP"
    assert sao_paulo.chuva_do_mes(1) == 292.1


def test_le_arquivo_informado_uma_vez(tmp_path) -> None:
    arquivo = tmp_path / "normais.json"
    item = {
        "codigo": 1,
        "nome": "X",
        "uf": "SP",
        "latitude": -23.0,
        "longitude": -46.0,
        "chuva_mensal_mm": [10.0] * 11 + [None],
    }
    arquivo.write_text(json.dumps({"estacoes": [item]}), encoding="utf-8")
    normais = NormaisInmet(arquivo)

    primeira = normais.todas()
    arquivo.unlink()
    assert normais.todas() == primeira
    assert primeira[0].coordenada == Coordenada(-23.0, -46.0)
    assert primeira[0].chuva_do_mes(12) is None
