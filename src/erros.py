"""Exceções do domínio."""


class RegraDeNegocioError(Exception):
    """Levantada quando uma operação viola uma regra de negócio."""
