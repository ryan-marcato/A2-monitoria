"""Confirmacao de presenca, expiracao de reservas e registro de faltas."""
from datetime import datetime

from monitoria.config import PRAZO_CONFIRMACAO_HORAS
from monitoria.database import atualizar_status_reserva, buscar_horario, buscar_reserva
from monitoria.erros import RegraDeNegocioError
from monitoria.models import Horario, StatusReserva


def confirmar_presenca(conn, aluno_id, reserva_id, agora=None):
    """Aluno confirma presenca em uma reserva aceita pelo monitor."""
    agora = agora or datetime.now()
    reserva = buscar_reserva(conn, reserva_id)
    if reserva is None or reserva.aluno_id != aluno_id:
        raise RegraDeNegocioError("Reserva não encontrada.")
    if reserva.status == StatusReserva.PENDENTE:
        raise RegraDeNegocioError("O monitor ainda não aceitou essa reserva.")
    if reserva.status != StatusReserva.ACEITA:
        raise RegraDeNegocioError("Essa reserva não pode ser confirmada.")

    horario = buscar_horario(conn, reserva.horario_id)
    if agora > horario.limite_confirmacao():  # RN05
        raise RegraDeNegocioError(
            f"O prazo para confirmar acabou (até {PRAZO_CONFIRMACAO_HORAS}h antes do início)."
        )

    conn.execute(
        "UPDATE reserva SET status = ?, confirmada_em = ? WHERE id = ?",
        (StatusReserva.CONFIRMADA.value, agora.isoformat(), reserva_id),
    )
    conn.commit()
    reserva.status = StatusReserva.CONFIRMADA
    reserva.confirmada_em = agora
    return reserva


def expirar_reservas(conn, agora=None):
    """Reservas PENDENTES ou ACEITAS cujo prazo venceu viram EXPIRADA, sem falta (RN06).

    Retorna quantas reservas expiraram.
    """
    agora = agora or datetime.now()
    linhas = conn.execute(
        """SELECT r.id AS reserva_id, h.*
           FROM reserva r JOIN horario h ON h.id = r.horario_id
           WHERE r.status IN ('PENDENTE', 'ACEITA')"""
    ).fetchall()

    total = 0
    for linha in linhas:
        horario = Horario.de_linha(linha)
        if agora > horario.limite_confirmacao():
            atualizar_status_reserva(conn, linha["reserva_id"], StatusReserva.EXPIRADA)
            total += 1
    return total


def listar_confirmados_para_presenca(conn, monitor_id, agora=None):
    """Reservas confirmadas de atendimentos que ja começaram, esperando registro de presenca."""
    agora = agora or datetime.now()
    linhas = conn.execute(
        """SELECT r.id AS reserva_id, r.duvida, h.inicio, a.nome AS aluno
           FROM reserva r
           JOIN horario h ON h.id = r.horario_id
           JOIN aluno a ON a.id = r.aluno_id
           WHERE h.monitor_id = ? AND r.status = 'CONFIRMADA'
           ORDER BY h.inicio, r.id""",
        (monitor_id,),
    ).fetchall()
    lista = []
    for l in linhas:
        inicio = datetime.fromisoformat(l["inicio"])
        if inicio <= agora:
            lista.append({
                "reserva_id": l["reserva_id"],
                "aluno": l["aluno"],
                "duvida": l["duvida"],
                "inicio": inicio,
            })
    return lista


def registrar_presenca(conn, monitor_id, reserva_id, compareceu, agora=None):
    """Monitor registra se o aluno compareceu. So quem confirmou participa (RN07)."""
    agora = agora or datetime.now()
    reserva = buscar_reserva(conn, reserva_id)
    horario = buscar_horario(conn, reserva.horario_id) if reserva else None
    if reserva is None or horario.monitor_id != monitor_id:
        raise RegraDeNegocioError("Reserva não encontrada.")
    if reserva.status != StatusReserva.CONFIRMADA:
        raise RegraDeNegocioError("Só quem confirmou presença pode participar do atendimento.")
    if agora < horario.inicio:
        raise RegraDeNegocioError("O atendimento ainda não começou.")

    if compareceu:
        novo_status = StatusReserva.REALIZADA
    else:
        novo_status = StatusReserva.FALTOU
        conn.execute(
            "INSERT INTO falta (reserva_id, aluno_id, registrada_em) VALUES (?, ?, ?)",
            (reserva_id, reserva.aluno_id, agora.isoformat()),
        )

    atualizar_status_reserva(conn, reserva_id, novo_status)
    reserva.status = novo_status
    return reserva


def listar_faltas_do_aluno(conn, aluno_id):
    linhas = conn.execute(
        """SELECT h.inicio, m.nome AS monitor, r.duvida
           FROM falta f
           JOIN reserva r ON r.id = f.reserva_id
           JOIN horario h ON h.id = r.horario_id
           JOIN monitor m ON m.id = h.monitor_id
           WHERE f.aluno_id = ?
           ORDER BY h.inicio""",
        (aluno_id,),
    ).fetchall()
    return [
        {
            "inicio": datetime.fromisoformat(l["inicio"]),
            "monitor": l["monitor"],
            "duvida": l["duvida"],
        }
        for l in linhas
    ]

