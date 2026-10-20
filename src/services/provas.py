"""Datas de prova em que o monitor estara ausente."""
from monitoria.config import MAX_PROVAS_AUSENCIA
from monitoria.erros import RegraDeNegocioError
from monitoria.models import ProvaAusencia


def registrar_prova(conn, monitor_id, data):
    """Registra uma data de prova (RN08: no maximo 2 por monitor)."""
    total = conn.execute(
        "SELECT COUNT(*) FROM prova_ausencia WHERE monitor_id = ?", (monitor_id,)
    ).fetchone()[0]
    if total >= MAX_PROVAS_AUSENCIA:
        raise RegraDeNegocioError(f"Você já registrou {MAX_PROVAS_AUSENCIA} datas de prova.")

    repetida = conn.execute(
        "SELECT 1 FROM prova_ausencia WHERE monitor_id = ? AND data = ?",
        (monitor_id, data.isoformat()),
    ).fetchone()
    if repetida:
        raise RegraDeNegocioError("Essa data já foi registrada.")

    #Se ja existem horarios nesse dia, o monitor receberia reservas na data de ausencia
    horarios = conn.execute(
        "SELECT COUNT(*) FROM horario WHERE monitor_id = ? AND substr(inicio, 1, 10) = ?",
        (monitor_id, data.isoformat()),
    ).fetchone()[0]
    if horarios > 0:
        raise RegraDeNegocioError("Você já tem horários cadastrados nessa data.")

    cursor = conn.execute(
        "INSERT INTO prova_ausencia (monitor_id, data) VALUES (?, ?)",
        (monitor_id, data.isoformat()),
    )
    conn.commit()
    return ProvaAusencia(cursor.lastrowid, monitor_id, data)


def listar_provas(conn, monitor_id):
    linhas = conn.execute(
        "SELECT * FROM prova_ausencia WHERE monitor_id = ? ORDER BY data", (monitor_id,)
    ).fetchall()
    return [ProvaAusencia.de_linha(l) for l in linhas]

