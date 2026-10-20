import sqlite3

from monitoria.config import NOME_BANCO
from monitoria.models import STATUS_ATIVOS, Horario, Reserva

# Trecho de SQL com os status que ocupam vaga: ('PENDENTE', 'ACEITA', 'CONFIRMADA')
ATIVAS_SQL = "(" + ", ".join("'" + s.value + "'" for s in STATUS_ATIVOS) + ")"

SCHEMA = """
CREATE TABLE IF NOT EXISTS aluno (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS monitor (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    disciplina TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS horario (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitor(id),
    inicio     TEXT NOT NULL,
    fim        TEXT NOT NULL,
    capacidade INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reserva (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id      INTEGER NOT NULL REFERENCES aluno(id),
    horario_id    INTEGER NOT NULL REFERENCES horario(id),
    duvida        TEXT NOT NULL,
    status        TEXT NOT NULL,
    criada_em     TEXT NOT NULL,
    confirmada_em TEXT
);

CREATE TABLE IF NOT EXISTS falta (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id    INTEGER NOT NULL UNIQUE REFERENCES reserva(id),
    aluno_id      INTEGER NOT NULL REFERENCES aluno(id),
    registrada_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prova_ausencia (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitor(id),
    data       TEXT NOT NULL,
    UNIQUE (monitor_id, data)
);
"""


def conectar(caminho=NOME_BANCO):
    """Abre o banco (use ":memory:" nos testes) e cria as tabelas se nao existirem."""
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row          # permite acessar colunas pelo nome
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def buscar_horario(conn, horario_id):
    linha = conn.execute("SELECT * FROM horario WHERE id = ?", (horario_id,)).fetchone()
    return Horario.de_linha(linha) if linha else None


def buscar_reserva(conn, reserva_id):
    linha = conn.execute("SELECT * FROM reserva WHERE id = ?", (reserva_id,)).fetchone()
    return Reserva.de_linha(linha) if linha else None


def atualizar_status_reserva(conn, reserva_id, novo_status):
    conn.execute("UPDATE reserva SET status = ? WHERE id = ?", (novo_status.value, reserva_id))
    conn.commit()
