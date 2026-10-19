"""Modelos de dados e enums de status."""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class StatusHorario(str, Enum):
    DISPONIVEL = "DISPONIVEL"
    BLOQUEADO = "BLOQUEADO"
    REALIZADO = "REALIZADO"


class StatusReserva(str, Enum):
    PENDENTE = "PENDENTE"
    ACEITA = "ACEITA"
    CONFIRMADA = "CONFIRMADA"
    REALIZADA = "REALIZADA"
    FALTA = "FALTA"
    RECUSADA = "RECUSADA"
    CANCELADA = "CANCELADA"

    @classmethod
    def ocupam_vaga(cls):
        return (cls.PENDENTE, cls.ACEITA, cls.CONFIRMADA)


@dataclass
class Aluno:
    nome: str
    email: str
    id: Optional[int] = None


@dataclass
class Monitor:
    nome: str
    email: str
    disciplina: str
    id: Optional[int] = None


@dataclass
class Horario:
    monitor_id: int
    inicio: datetime
    fim: datetime
    capacidade: int
    status: StatusHorario = StatusHorario.DISPONIVEL
    id: Optional[int] = None


@dataclass
class Reserva:
    aluno_id: int
    horario_id: int
    duvida: str
    status: StatusReserva = StatusReserva.PENDENTE
    criada_em: Optional[datetime] = None
    confirmada_em: Optional[datetime] = None
    id: Optional[int] = None


@dataclass
class Falta:
    reserva_id: int
    aluno_id: int
    registrada_em: datetime
    id: Optional[int] = None


@dataclass
class ProvaAusencia:
    monitor_id: int
    data: date
    id: Optional[int] = None
