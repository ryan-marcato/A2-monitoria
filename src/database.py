"""Conexão com SQLite e criação do schema."""
import sqlite3

from . import config

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
    inicio     TEXT NOT NULL,            -- ISO 8601
    fim        TEXT NOT NULL,
    capacidade INTEGER NOT NULL DEFAULT 5 CHECK (capacidade > 0),
    status     TEXT NOT NULL DEFAULT 'DISPONIVEL'
               CHECK (status IN ('DISPONIVEL','BLOQUEADO','REALIZADO')),
    UNIQUE (monitor_id, inicio)
);

CREATE TABLE IF NOT EXISTS reserva (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id      INTEGER NOT NULL REFERENCES aluno(id),
    horario_id    INTEGER NOT NULL REFERENCES horario(id),
    duvida        TEXT NOT NULL CHECK (length(trim(duvida)) > 0),
    status        TEXT NOT NULL DEFAULT 'PENDENTE'
                  CHECK (status IN ('PENDENTE','ACEITA','CONFIRMADA',
                                    'REALIZADA','FALTA','RECUSADA','CANCELADA')),
    criada_em     TEXT NOT NULL,
    confirmada_em TEXT
);

CREATE TABLE IF NOT EXISTS falta (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id     INTEGER NOT NULL UNIQUE REFERENCES reserva(id),
    aluno_id       INTEGER NOT NULL REFERENCES aluno(id),
    registrada_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prova_ausencia (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitor(id),
    data       TEXT NOT NULL,            -- YYYY-MM-DD
    UNIQUE (monitor_id, data)
);
"""


def conectar(caminho: str = config.DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def criar_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
