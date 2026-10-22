from datetime import timedelta

import pytest
from conftest import AGORA, INICIO, reservar_e_aceitar, reservar_e_confirmar

from monitoria.erros import RegraDeNegocioError
from monitoria.models import StatusReserva
from monitoria.services import agendamento, confirmacao
from monitoria.database import buscar_reserva

DEPOIS_DO_INICIO = INICIO + timedelta(minutes=5)


# ----------Confirmacao----------

def test_aluno_confirma_reserva_aceita(conn, monitor, aluno, horario):
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario)
    resultado = confirmacao.confirmar_presenca(conn, aluno.id, reserva.id, agora=AGORA)
    assert resultado.status == StatusReserva.CONFIRMADA
    assert resultado.confirmada_em == AGORA


def test_nao_confirma_reserva_pendente(conn, aluno, horario):
    reserva = agendamento.reservar(conn, aluno.id, horario.id, "Dúvida", agora=AGORA)
    with pytest.raises(RegraDeNegocioError):
        confirmacao.confirmar_presenca(conn, aluno.id, reserva.id, agora=AGORA)


def test_nao_confirma_depois_do_prazo(conn, monitor, aluno, horario):  # RN05
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario)
    with pytest.raises(RegraDeNegocioError):
        confirmacao.confirmar_presenca(conn, aluno.id, reserva.id,
                                       agora=INICIO - timedelta(hours=1))


def test_confirma_exatamente_no_limite(conn, monitor, aluno, horario):
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario)
    limite = INICIO - timedelta(hours=2)
    resultado = confirmacao.confirmar_presenca(conn, aluno.id, reserva.id, agora=limite)
    assert resultado.status == StatusReserva.CONFIRMADA


# ----------Expiracao----------

def test_reserva_nao_confirmada_expira_sem_falta(conn, monitor, aluno, horario):  # RN06
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario)
    total = confirmacao.expirar_reservas(conn, agora=INICIO - timedelta(hours=1))
    assert total == 1
    assert buscar_reserva(conn, reserva.id).status == StatusReserva.EXPIRADA
    assert confirmacao.listar_faltas_do_aluno(conn, aluno.id) == []


def test_expiracao_libera_a_vaga(conn, monitor, aluno, horario):
    reservar_e_aceitar(conn, monitor, aluno, horario)
    confirmacao.expirar_reservas(conn, agora=INICIO - timedelta(hours=1))
    assert agendamento.vagas_livres(conn, horario.id) == 5


def test_reserva_confirmada_nao_expira(conn, monitor, aluno, horario):
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    confirmacao.expirar_reservas(conn, agora=INICIO - timedelta(hours=1))
    assert buscar_reserva(conn, reserva.id).status == StatusReserva.CONFIRMADA


# ----------Presença e faltas----------

def test_registrar_comparecimento(conn, monitor, aluno, horario):
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    resultado = confirmacao.registrar_presenca(conn, monitor.id, reserva.id, True,
                                               agora=DEPOIS_DO_INICIO)
    assert resultado.status == StatusReserva.REALIZADA


def test_confirmou_e_faltou_gera_uma_falta(conn, monitor, aluno, horario):  # RN07
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    resultado = confirmacao.registrar_presenca(conn, monitor.id, reserva.id, False,
                                               agora=DEPOIS_DO_INICIO)
    assert resultado.status == StatusReserva.FALTOU
    assert len(confirmacao.listar_faltas_do_aluno(conn, aluno.id)) == 1


def test_falta_nao_pode_ser_registrada_duas_vezes(conn, monitor, aluno, horario):
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    confirmacao.registrar_presenca(conn, monitor.id, reserva.id, False, agora=DEPOIS_DO_INICIO)
    with pytest.raises(RegraDeNegocioError):
        confirmacao.registrar_presenca(conn, monitor.id, reserva.id, False,
                                       agora=DEPOIS_DO_INICIO)
    assert len(confirmacao.listar_faltas_do_aluno(conn, aluno.id)) == 1


def test_quem_nao_confirmou_nao_participa(conn, monitor, aluno, horario):
    reserva = reservar_e_aceitar(conn, monitor, aluno, horario)  # aceita, mas não confirmada
    with pytest.raises(RegraDeNegocioError):
        confirmacao.registrar_presenca(conn, monitor.id, reserva.id, True,
                                       agora=DEPOIS_DO_INICIO)


def test_nao_registra_presenca_antes_do_inicio(conn, monitor, aluno, horario):
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    with pytest.raises(RegraDeNegocioError):
        confirmacao.registrar_presenca(conn, monitor.id, reserva.id, True, agora=AGORA)


def test_lista_confirmados_so_depois_do_inicio(conn, monitor, aluno, horario):
    reservar_e_confirmar(conn, monitor, aluno, horario)
    assert confirmacao.listar_confirmados_para_presenca(conn, monitor.id, agora=AGORA) == []
    lista = confirmacao.listar_confirmados_para_presenca(conn, monitor.id, agora=DEPOIS_DO_INICIO)
    assert len(lista) == 1
