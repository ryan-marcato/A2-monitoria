"""Agendamento: horarios do monitor, reservas dos alunos e resposta do monitor."""
from datetime import datetime, timedelta

from monitoria.config import CAPACIDADE_PADRAO, DURACAO_BLOCO_MIN, PRAZO_CONFIRMACAO_HORAS
from monitoria.database import ATIVAS_SQL, atualizar_status_reserva, buscar_horario, buscar_reserva
from monitoria.erros import RegraDeNegocioError
from monitoria.models import STATUS_ATIVOS, Horario, Reserva, StatusReserva


def criar_horario(conn, monitor_id, inicio, capacidade=CAPACIDADE_PADRAO, agora=None):
    """Monitor cadastra um horario livre de 30 minutos."""
    agora = agora or datetime.now()
    fim = inicio + timedelta(minutes=DURACAO_BLOCO_MIN)  # RN01

    if inicio <= agora:
        raise RegraDeNegocioError("O horário precisa estar no futuro.")
    if capacidade < 1:
        raise RegraDeNegocioError("A capacidade deve ser de pelo menos 1 aluno.")

    # RN08: nao ha horarios em datas de prova do monitor
    prova = conn.execute(
        "SELECT 1 FROM prova_ausencia WHERE monitor_id = ? AND data = ?",
        (monitor_id, inicio.date().isoformat()),
    ).fetchone()
    if prova:
        raise RegraDeNegocioError("Você estará ausente nessa data (prova registrada).")

    # Um monitor nao pode ter dois horarios sobrepostos
    conflito = conn.execute(
        "SELECT 1 FROM horario WHERE monitor_id = ? AND inicio < ? AND fim > ?",
        (monitor_id, fim.isoformat(), inicio.isoformat()),
    ).fetchone()
    if conflito:
        raise RegraDeNegocioError("Você já tem um horário que conflita com esse.")

    cursor = conn.execute(
        "INSERT INTO horario (monitor_id, inicio, fim, capacidade) VALUES (?, ?, ?, ?)",
        (monitor_id, inicio.isoformat(), fim.isoformat(), capacidade),
    )
    conn.commit()
    return Horario(cursor.lastrowid, monitor_id, inicio, fim, capacidade)


def vagas_livres(conn, horario_id):
    """Capacidade do horario menos as reservas ativas."""
    horario = buscar_horario(conn, horario_id)
    ocupadas = conn.execute(
        f"SELECT COUNT(*) FROM reserva WHERE horario_id = ? AND status IN {ATIVAS_SQL}",
        (horario_id,),
    ).fetchone()[0]
    return horario.capacidade - ocupadas


def listar_horarios_disponiveis(conn, agora=None):
    """Horarios que ainda aceitam reserva (prazo aberto e com vagas)."""
    agora = agora or datetime.now()
    linhas = conn.execute(
        """SELECT h.*, m.nome AS monitor_nome, m.disciplina
           FROM horario h JOIN monitor m ON m.id = h.monitor_id
           ORDER BY h.inicio"""
    ).fetchall()

    disponiveis = []
    for linha in linhas:
        horario = Horario.de_linha(linha)
        vagas = vagas_livres(conn, horario.id)
        if agora <= horario.limite_confirmacao() and vagas > 0:
            disponiveis.append({
                "horario": horario,
                "monitor": linha["monitor_nome"],
                "disciplina": linha["disciplina"],
                "vagas": vagas,
            })
    return disponiveis


def reservar(conn, aluno_id, horario_id, duvida, agora=None):
    """Aluno reserva um horario descrevendo a duvida. A reserva nasce PENDENTE."""
    agora = agora or datetime.now()
    duvida = duvida.strip()

    if not duvida:  # RN02
        raise RegraDeNegocioError("Descreva sua dúvida para reservar.")

    horario = buscar_horario(conn, horario_id)
    if horario is None:
        raise RegraDeNegocioError("Horário não encontrado.")

    if agora > horario.limite_confirmacao():
        raise RegraDeNegocioError(
            f"Reservas só são aceitas até {PRAZO_CONFIRMACAO_HORAS}h antes do início."
        )

    repetida = conn.execute(  # RN04
        f"SELECT 1 FROM reserva WHERE aluno_id = ? AND horario_id = ? AND status IN {ATIVAS_SQL}",
        (aluno_id, horario_id),
    ).fetchone()
    if repetida:
        raise RegraDeNegocioError("Você já tem uma reserva ativa nesse horário.")

    if vagas_livres(conn, horario_id) <= 0:  # RN03
        raise RegraDeNegocioError("Esse horário está lotado.")

    cursor = conn.execute(
        "INSERT INTO reserva (aluno_id, horario_id, duvida, status, criada_em) VALUES (?, ?, ?, ?, ?)",
        (aluno_id, horario_id, duvida, StatusReserva.PENDENTE.value, agora.isoformat()),
    )
    conn.commit()
    return Reserva(cursor.lastrowid, aluno_id, horario_id, duvida, StatusReserva.PENDENTE, agora, None)


def cancelar_reserva(conn, aluno_id, reserva_id, agora=None):
    """Aluno cancela a reserva (sem falta) e libera a vaga."""
    agora = agora or datetime.now()
    reserva = buscar_reserva(conn, reserva_id)
    if reserva is None or reserva.aluno_id != aluno_id:
        raise RegraDeNegocioError("Reserva não encontrada.")
    if reserva.status not in STATUS_ATIVOS:
        raise RegraDeNegocioError("Essa reserva não pode mais ser cancelada.")

    horario = buscar_horario(conn, reserva.horario_id)
    if agora >= horario.inicio:
        raise RegraDeNegocioError("Não é possível cancelar depois do início do atendimento.")

    atualizar_status_reserva(conn, reserva_id, StatusReserva.CANCELADA)
    reserva.status = StatusReserva.CANCELADA
    return reserva


def listar_reservas_do_aluno(conn, aluno_id):
    linhas = conn.execute(
        """SELECT r.id AS reserva_id, r.duvida, r.status, h.inicio, m.nome AS monitor
           FROM reserva r
           JOIN horario h ON h.id = r.horario_id
           JOIN monitor m ON m.id = h.monitor_id
           WHERE r.aluno_id = ?
           ORDER BY h.inicio, r.id""",
        (aluno_id,),
    ).fetchall()
    return [
        {
            "reserva_id": l["reserva_id"],
            "monitor": l["monitor"],
            "inicio": datetime.fromisoformat(l["inicio"]),
            "duvida": l["duvida"],
            "status": StatusReserva(l["status"]),
        }
        for l in linhas
    ]


def listar_pendentes_do_monitor(conn, monitor_id):
    """Duvidas aguardando resposta, ordenadas por horario facilita agrupar duvidas parecidas."""
    linhas = conn.execute(
        """SELECT r.id AS reserva_id, r.duvida, h.inicio, a.nome AS aluno
           FROM reserva r
           JOIN horario h ON h.id = r.horario_id
           JOIN aluno a ON a.id = r.aluno_id
           WHERE h.monitor_id = ? AND r.status = 'PENDENTE'
           ORDER BY h.inicio, r.id""",
        (monitor_id,),
    ).fetchall()
    return [
        {
            "reserva_id": l["reserva_id"],
            "aluno": l["aluno"],
            "duvida": l["duvida"],
            "inicio": datetime.fromisoformat(l["inicio"]),
        }
        for l in linhas
    ]


def responder_reserva(conn, monitor_id, reserva_id, aceitar, agora=None):
    """Monitor aceita (aceitar=True) ou recusa (aceitar=False) uma reserva pendente."""
    agora = agora or datetime.now()
    reserva = buscar_reserva(conn, reserva_id)
    horario = buscar_horario(conn, reserva.horario_id) if reserva else None
    if reserva is None or horario.monitor_id != monitor_id:
        raise RegraDeNegocioError("Reserva não encontrada.")
    if reserva.status != StatusReserva.PENDENTE:
        raise RegraDeNegocioError("Essa reserva não está mais pendente.")
    if aceitar and agora > horario.limite_confirmacao():
        raise RegraDeNegocioError("O prazo de confirmação já passou; não dá mais para aceitar.")

    novo_status = StatusReserva.ACEITA if aceitar else StatusReserva.RECUSADA
    atualizar_status_reserva(conn, reserva_id, novo_status)
    reserva.status = novo_status
    return reserva

