"""Erros do sistema."""


class RegraDeNegocioError(Exception):
    """Lancado quando uma regra de negocio é violada.

    A interface (cli.py) captura esse erro e mostra a mensagem ao usuario.
    """
