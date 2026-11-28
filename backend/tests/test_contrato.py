"""O contrato (docs/contrato-api.md) e os mocks do front acompanham a API.

Se este teste falhar, uma rota ou um schema mudou: rode
`uv run python -m scripts.gerar_contrato` em `backend/` e commite os arquivos.
"""

from scripts import gerar_contrato as gerador


def test_contrato_e_mocks_estao_em_dia() -> None:
    pendentes = gerador.desatualizados(gerador.gerar_arquivos())
    nomes = [str(p.relative_to(gerador.RAIZ)) for p in pendentes]
    assert not nomes, "rode `uv run python -m scripts.gerar_contrato`: " + ", ".join(nomes)


def test_geracao_e_deterministica() -> None:
    primeira = gerador.gerar_arquivos()
    segunda = gerador.gerar_arquivos()
    assert primeira == segunda


def test_ids_de_alerta_sao_estaveis_e_compartilhados() -> None:
    respostas = gerador._ids_estaveis(
        {
            "a.json": [{"id": "6f1c2d1e-0000-4000-8000-000000000abc", "x": 1}],
            "b.json": {
                "alerta": {"id": "6f1c2d1e-0000-4000-8000-000000000abc"},
                "outro": {"id": "0b9d6c55-1111-4111-8111-000000000def"},
                "codigo": {"id": 7},
            },
        }
    )
    primeiro = "00000000-0000-0000-0000-000000000001"
    assert respostas["a.json"][0]["id"] == primeiro
    assert respostas["b.json"]["alerta"]["id"] == primeiro
    assert respostas["b.json"]["outro"]["id"] == "00000000-0000-0000-0000-000000000002"
    assert respostas["b.json"]["codigo"]["id"] == 7  # só UUIDs são trocados


def test_exemplo_vai_para_a_rota_mais_especifica() -> None:
    caminhos = {"/estacoes/{codigo}": {}, "/estacoes/proximas": {}, "/estacoes": {}}
    assert gerador._rota_do_exemplo("/estacoes/proximas?lat=1", caminhos) == "/estacoes/proximas"
    assert gerador._rota_do_exemplo("/estacoes/123", caminhos) == "/estacoes/{codigo}"
    assert gerador._rota_do_exemplo("/alertas", caminhos) is None


def test_check_aponta_arquivo_desatualizado(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(gerador, "PASTA_MOCKS", tmp_path / "mocks")
    monkeypatch.setattr(gerador, "ARQUIVO_DOC", tmp_path / "contrato-api.md")
    monkeypatch.setattr(gerador, "RAIZ", tmp_path)
    assert gerador.main(["--check"]) == 1
    assert gerador.main([]) == 0
    assert gerador.main(["--check"]) == 0
    (tmp_path / "mocks" / "sobra.json").write_text("{}", encoding="utf-8")
    assert gerador.main(["--check"]) == 1
    assert gerador.main([]) == 0
    assert not (tmp_path / "mocks" / "sobra.json").exists()
