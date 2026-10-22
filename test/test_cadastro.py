import pytest

from monitoria.erros import RegraDeNegocioError
from monitoria.services import cadastro


def test_cadastrar_aluno(conn):
    aluno = cadastro.cadastrar_aluno(conn, "Ana", "ANA@uni.br")
    assert aluno.id == 1
    assert aluno.email == "ana@uni.br"  # e-mail eh guardado em minúsculas


def test_email_duplicado_de_aluno_e_recusado(conn, aluno):
    with pytest.raises(RegraDeNegocioError):
        cadastro.cadastrar_aluno(conn, "Outro", aluno.email)


def test_campos_vazios_sao_recusados(conn):
    with pytest.raises(RegraDeNegocioError):
        cadastro.cadastrar_aluno(conn, "", "x@uni.br")
    with pytest.raises(RegraDeNegocioError):
        cadastro.cadastrar_monitor(conn, "Maria", "m@uni.br", "")


def test_cadastrar_monitor(conn):
    monitor = cadastro.cadastrar_monitor(conn, "Maria", "m@uni.br", "Cálculo")
    assert monitor.disciplina == "Cálculo"


def test_buscar_por_email(conn, aluno, monitor):
    assert cadastro.buscar_aluno_por_email(conn, aluno.email).id == aluno.id
    assert cadastro.buscar_monitor_por_email(conn, monitor.email).id == monitor.id


def test_buscar_email_inexistente(conn):
    with pytest.raises(RegraDeNegocioError):
        cadastro.buscar_aluno_por_email(conn, "ninguem@uni.br")
