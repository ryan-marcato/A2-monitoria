"""Relatorios do monitor: duvidas apresentadas e horas trabalhadas."""
from datetime import datetime

from monitoria.config import DURACAO_BLOCO_MIN
from monitoria.models import StatusReserva


def relatorio_duvidas(conn, monitor_id):
    """Todas as dúvidas recebidas pelo monitor, por horário."""
    linhas = conn.execute(
        """SELECT h.inicio, a.nome AS aluno, r.duvida, r.status
           FROM reserva r
           JOIN horario h ON h.id = r.horario_id
           JOIN aluno a ON a.id = r.aluno_id
           WHERE h.monitor_id = ?
           ORDER BY h.inicio, r.id""",
        (monitor_id,),
    ).fetchall()
    return [
        {
            "inicio": datetime.fromisoformat(l["inicio"]),
            "aluno": l["aluno"],
            "duvida": l["duvida"],
            "status": StatusReserva(l["status"]),
        }
        for l in linhas
    ]


def relatorio_horas(conn, monitor_id):
    """Horas trabalhadas (RN09).

    Cada horario com pelo menos um aluno presente conta como 1 atendimento de 30 min,
    mesmo que tenha sido em grupo.
    """
    atendimentos = conn.execute(
        """SELECT COUNT(DISTINCT h.id)
           FROM horario h JOIN reserva r ON r.horario_id = h.id
           WHERE h.monitor_id = ? AND r.status = 'REALIZADA'""",
        (monitor_id,),
    ).fetchone()[0]
    minutos = atendimentos * DURACAO_BLOCO_MIN
    return {"atendimentos": atendimentos, "minutos": minutos, "horas": minutos / 60}

