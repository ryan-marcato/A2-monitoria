from datetime import date

import pytest
from conftest import INICIO

from monitoria.erros import RegraDeNegocioError
from monitoria.services import provas


def test_registrar_prova(conn, monitor):
    prova = provas.registrar_prova(conn, monitor.id, date(2026, 11, 10))
    assert prova.data == date(2026, 11, 10)
    assert len(provas.listar_provas(conn, monitor.id)) == 1


def test_maximo_de_duas_provas(conn, monitor):  # RN08
    provas.registrar_prova(conn, monitor.id, date(2026, 11, 10))
    provas.registrar_prova(conn, monitor.id, date(2026, 11, 12))
    with pytest.raises(RegraDeNegocioError):
        provas.registrar_prova(conn, monitor.id, date(2026, 11, 14))


def test_data_repetida_e_recusada(conn, monitor):
    provas.registrar_prova(conn, monitor.id, date(2026, 11, 10))
    with pytest.raises(RegraDeNegocioError):
        provas.registrar_prova(conn, monitor.id, date(2026, 11, 10))


def test_data_com_horarios_existentes_e_recusada(conn, monitor, horario):
    with pytest.raises(RegraDeNegocioError):
        provas.registrar_prova(conn, monitor.id, INICIO.date())
