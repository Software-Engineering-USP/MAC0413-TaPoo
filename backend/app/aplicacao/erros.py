class ErroAplicacao(Exception):
    """Base dos erros que a camada de API traduz em respostas HTTP."""


class RecursoNaoEncontrado(ErroAplicacao):
    """Base dos erros traduzidos em 404."""


class EstacaoNaoEncontrada(RecursoNaoEncontrado):
    def __init__(self, codigo: int) -> None:
        super().__init__(f"estação {codigo} não encontrada")
        self.codigo = codigo


class MunicipioNaoEncontrado(RecursoNaoEncontrado):
    def __init__(self, uf: str, municipio: str) -> None:
        super().__init__(f"nenhuma estação encontrada em {municipio}/{uf.upper()}")
        self.uf = uf
        self.municipio = municipio
