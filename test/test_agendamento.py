from datetime import timedelta

import pytest
from conftest import AGORA, INICIO, reservar_e_aceitar

from monitoria.erros import RegraDeNegocioError
from monitoria.models import StatusReserva
from monitoria.services import agendamento, cadastro, provas


# ----------Horarios----------

def test_horario_tem_30_minutos(horario):  # RN01
    assert horario.fim - horario.inicio == timedelta(minutes=30)


def test_horario_no_passado_e_recusado(conn, monitor):
    with pytest.raises(RegraDeNegocioError):
        agendamento.criar_horario(conn, monitor.id, AGORA - timedelta(hours=1), agora=AGORA)


def test_horario_conflitante_e_recusado(conn, monitor, horario):
    with pytest.raises(RegraDeNegocioError):
        agendamento.criar_horario(conn, monitor.id, INICIO + timedelta(minutes=15), agora=AGORA)


def test_horario_em_dia_de_prova_e_recusado(conn, monitor):  # RN08
    provas.registrar_prova(conn, monitor.id, INICIO.date())
    with pytest.raises(RegraDeNegocioError):
        agendamento.criar_horario(conn, monitor.id, INICIO, agora=AGORA)


def test_listar_horarios_mostra_vagas(conn, aluno, horario):
    agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    lista = agendamento.listar_horarios_disponiveis(conn, agora=AGORA)
    assert len(lista) == 1
    assert lista[0]["vagas"] == 4


def test_horario_fora_do_prazo_nao_e_listado(conn, horario):
    lista = agendamento.listar_horarios_disponiveis(conn, agora=INICIO - timedelta(hours=1))
    assert lista == []


# ----------Reservas----------

def test_reservar_cria_reserva_pendente(conn, aluno, horario):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    assert reserva.status == StatusReserva.PENDENTE


def test_reservar_exige_duvida(conn, aluno, horario):  # RN02
    with pytest.raises(RegraDeNegocioError):
        agendamento.reservar(conn, aluno.id, horario.id, "   ", agora=AGORA)


def test_reservar_depois_do_prazo_e_recusado(conn, aluno, horario):
    with pytest.raises(RegraDeNegocioError):
        agendamento.reservar(conn, aluno.id, horario.id, "Dúvida",
                             agora=INICIO - timedelta(hours=1))


def test_horario_lotado_recusa_reserva(conn, monitor, aluno):  # RN03
    pequeno = agendamento.criar_horario(conn, monitor.id, INICIO, capacidade=1, agora=AGORA)
    outro = cadastro.cadastrar_aluno(conn, "Beto", "beto@uni.br")
    agendamento.reservar(conn, aluno.id, pequeno.id, "Dúvida 1", agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        agendamento.reservar(conn, outro.id, pequeno.id, "Dúvida 2", agora=AGORA)


def test_reserva_duplicada_e_recusada(conn, aluno, horario):  # RN04
    agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        agendamento.reservar(conn, aluno.id, horario.id, "Outra", agora=AGORA)


# ----------Resposta do monitor----------

def test_monitor_aceita_reserva(conn, monitor, aluno, horario):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    resultado = agendamento.responder_reserva(conn, monitor.id, reserva.id, True, agora=AGORA)
    assert resultado.status == StatusReserva.ACEITA


def test_recusa_libera_a_vaga(conn, monitor, aluno, horario):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    assert agendamento.vagas_livres(conn, horario.id) == 4
    agendamento.responder_reserva(conn, monitor.id, reserva.id, False, agora=AGORA)
    assert agendamento.vagas_livres(conn, horario.id) == 5


def test_reserva_so_pode_ser_respondida_uma_vez(conn, monitor, aluno, horario):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    agendamento.responder_reserva(conn, monitor.id, reserva.id, True, agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        agendamento.responder_reserva(conn, monitor.id, reserva.id, False, agora=AGORA)


def test_outro_monitor_nao_responde_reserva(conn, aluno, horario):
    outro = cadastro.cadastrar_monitor(conn, "Pedro", "pedro@uni.br", "Física")
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        agendamento.responder_reserva(conn, outro.id, reserva.id, True, agora=AGORA)


def test_lista_pendentes_do_monitor(conn, monitor, aluno, horario):
    agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    pendentes = agendamento.listar_pendentes_do_monitor(conn, monitor.id)
    assert len(pendentes) == 1
    assert pendentes[0]["aluno"] == "João"


# ----------Cancelamento----------

def test_cancelar_reserva_libera_vaga(conn, monitor, aluno, horario):
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario)
    agendamento.cancelar_reserva(conn, aluno.id, reserva.id, agora=AGORA)
    assert agendamento.vagas_livres(conn, horario.id) == 5


def test_nao_cancela_reserva_de_outro_aluno(conn, aluno, horario):
    outro = cadastro.cadastrar_aluno(conn, "Beto", "beto@uni.br")
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        agendamento.cancelar_reserva(conn, outro.id, reserva.id, agora=AGORA)


def test_nao_cancela_depois_do_inicio(conn, aluno, horario):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        agendamento.cancelar_reserva(conn, aluno.id, reserva.id, agora=INICIO)
