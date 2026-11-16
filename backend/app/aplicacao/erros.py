class ErroAplicacao(Exception):
    """Base dos erros que a camada de API traduz em respostas HTTP."""


class EstacaoNaoEncontrada(ErroAplicacao):
    def __init__(self, codigo: int) -> None:
        super().__init__(f"estação {codigo} não encontrada")
        self.codigo = codigo
