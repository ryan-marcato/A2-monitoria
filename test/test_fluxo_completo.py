"""Fluxo ponta a ponta: cadastro -> horário -> reserva -> aceite -> confirmação -> presença -> relatório."""
from datetime import date, timedelta

import pytest
from conftest import AGORA, INICIO

from monitoria import database
from monitoria.erros import RegraDeNegocioError
from monitoria.models import StatusReserva
from monitoria.services import agendamento, cadastro, confirmacao, provas, relatorio


def test_fluxo_completo():
    conn = database.conectar(":memory:")

    # Cadastros
    monitor = cadastro.cadastrar_monitor(conn, "Maria", "maria@uni.br", "Cálculo")
    ana = cadastro.cadastrar_aluno(conn, "Ana", "ana@uni.br")
    beto = cadastro.cadastrar_aluno(conn, "Beto", "beto@uni.br")
    caio = cadastro.cadastrar_aluno(conn, "Caio", "caio@uni.br")

    # Monitor registra prova e cria horario
    provas.registrar_prova(conn, monitor.id, date(2026, 11, 10))
    horario = agendamento.criar_horario(conn, monitor.id, INICIO, agora=AGORA)

    # Tres alunos reservam o mesmo horário (atendimento em grupo)
    reservas = {}
    for aluno in (ana, beto, caio):
        reservas[aluno.nome] = agendamento.reservar(
            conn, aluno.id, horario.id, f"Dúvida de {aluno.nome}", agora=AGORA)

    # Monitor aceita todos
    for reserva in reservas.values():
        agendamento.responder_reserva(conn, monitor.id, reserva.id, True, agora=AGORA)

    # Ana e Beto confirmam; Caio não confirma
    confirmacao.confirmar_presenca(conn, ana.id, reservas["Ana"].id, agora=AGORA)
    confirmacao.confirmar_presenca(conn, beto.id, reservas["Beto"].id, agora=AGORA)

    # Passa o prazo: a reserva do Caio expira, sem falta
    confirmacao.expirar_reservas(conn, agora=INICIO - timedelta(hours=1))
    assert database.buscar_reserva(conn, reservas["Caio"].id).status == StatusReserva.EXPIRADA

    # Atendimento: Ana comparece, Beto confirmou e faltou, Caio aparece mas nao confirmou
    depois = INICIO + timedelta(minutes=10)
    confirmacao.registrar_presenca(conn, monitor.id, reservas["Ana"].id, True, agora=depois)
    confirmacao.registrar_presenca(conn, monitor.id, reservas["Beto"].id, False, agora=depois)
    with pytest.raises(RegraDeNegocioError):
        confirmacao.registrar_presenca(conn, monitor.id, reservas["Caio"].id, True, agora=depois)

    # Faltas: só o Beto
    assert len(confirmacao.listar_faltas_do_aluno(conn, beto.id)) == 1
    assert confirmacao.listar_faltas_do_aluno(conn, caio.id) == []
    assert confirmacao.listar_faltas_do_aluno(conn, ana.id) == []

    # Relatórios
    assert len(relatorio.relatorio_duvidas(conn, monitor.id)) == 3
    horas = relatorio.relatorio_horas(conn, monitor.id)
    assert horas["atendimentos"] == 1
    assert horas["minutos"] == 30

    conn.close()
