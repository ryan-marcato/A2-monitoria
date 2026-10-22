"""Configuracao compartilhada dos testes (banco em memoria, dados de exemplo)."""
from datetime import datetime

import pytest

from monitoria import database
from monitoria.services import agendamento, cadastro, confirmacao

AGORA = datetime(2026, 10, 20, 8, 0)      # "hoje" nos testes
INICIO = datetime(2026, 10, 22, 14, 0)    # horario de teste (2 dias depois)


@pytest.fixture
def conn():
    conexao = database.conectar(":memory:")
    yield conexao
    conexao.close()


@pytest.fixture
def monitor(conn):
    return cadastro.cadastrar_monitor(conn, "Maria", "maria@uni.br", "Cálculo")


@pytest.fixture
def aluno(conn):
    return cadastro.cadastrar_aluno(conn, "João", "joao@uni.br")


@pytest.fixture
def horario(conn, monitor):
    return agendamento.criar_horario(conn, monitor.id, INICIO, agora=AGORA)


def reservar_e_aceitar(conn, monitor, aluno, horario, duvida="Dúvida sobre limites"):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, duvida, agora=AGORA)
    agendamento.responder_reserva(conn, monitor.id, reserva.id, True, agora=AGORA)
    return reserva


def reservar_e_confirmar(conn, monitor, aluno, horario, duvida="Dúvida sobre limites"):
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario, duvida)
    confirmacao.confirmar_presenca(conn, aluno.id, reserva.id, agora=AGORA)
    return reserva
