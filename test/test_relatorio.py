from datetime import timedelta

from conftest import INICIO, reservar_e_confirmar

from monitoria.services import agendamento, cadastro, confirmacao, relatorio

DEPOIS_DO_INICIO = INICIO + timedelta(minutes=5)


def test_relatorio_de_duvidas(conn, monitor, aluno, horario):
    agendamento.reservar(conn, aluno.id, horario.id, "Como derivar?", agora=INICIO - timedelta(days=1))
    linhas = relatorio.relatorio_duvidas(conn, monitor.id)
    assert len(linhas) == 1
    assert linhas[0]["duvida"] == "Como derivar?"
    assert linhas[0]["aluno"] == "João"


def test_relatorio_vazio(conn, monitor):
    assert relatorio.relatorio_duvidas(conn, monitor.id) == []
    assert relatorio.relatorio_horas(conn, monitor.id)["minutos"] == 0


def test_horas_contam_so_atendimentos_realizados(conn, monitor, aluno, horario):  # RN09
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    assert relatorio.relatorio_horas(conn, monitor.id)["atendimentos"] == 0
    confirmacao.registrar_presenca(conn, monitor.id, reserva.id, True, agora=DEPOIS_DO_INICIO)
    dados = relatorio.relatorio_horas(conn, monitor.id)
    assert dados["atendimentos"] == 1
    assert dados["minutos"] == 30


def test_atendimento_em_grupo_conta_uma_vez(conn, monitor, aluno, horario):
    outro = cadastro.cadastrar_aluno(conn, "Beto", "beto@uni.br")
    r1 = reservar_e_confirmar(conn, monitor, aluno, horario)
    r2 = reservar_e_confirmar(conn, monitor, outro, horario)
    confirmacao.registrar_presenca(conn, monitor.id, r1.id, True, agora=DEPOIS_DO_INICIO)
    confirmacao.registrar_presenca(conn, monitor.id, r2.id, True, agora=DEPOIS_DO_INICIO)
    assert relatorio.relatorio_horas(conn, monitor.id)["minutos"] == 30


def test_falta_nao_conta_como_hora_trabalhada(conn, monitor, aluno, horario):
    reserva = reservar_e_confirmar(conn, monitor, aluno, horario)
    confirmacao.registrar_presenca(conn, monitor.id, reserva.id, False, agora=DEPOIS_DO_INICIO)
    assert relatorio.relatorio_horas(conn, monitor.id)["atendimentos"] == 0
