import sqlite3

import pytest

from monitoria import database


def test_cria_todas_as_tabelas(conn):
    linhas = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    tabelas = {linha["name"] for linha in linhas}
    assert {"aluno", "monitor", "horario", "reserva", "falta", "prova_ausencia"} <= tabelas


def test_email_do_aluno_e_unico(conn):
    conn.execute("INSERT INTO aluno (nome, email) VALUES ('A', 'a@uni.br')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO aluno (nome, email) VALUES ('B', 'a@uni.br')")


def test_reserva_inexistente_retorna_none(conn):
    assert database.buscar_reserva(conn, 999) is None


def test_horario_inexistente_retorna_none(conn):
    assert database.buscar_horario(conn, 999) is None
