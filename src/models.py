"""Modelos: entidades (dataclasses) e status (enums).

Esta camada nao acessa banco de dados nem interface.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from monitoria.config import PRAZO_CONFIRMACAO_HORAS


class StatusReserva(Enum):
    PENDENTE = "PENDENTE"        # aluno reservou; monitor ainda nao respondeu
    ACEITA = "ACEITA"            # monitor aceitou; aluno precisa confirmar presença
    RECUSADA = "RECUSADA"        # monitor recusou
    CONFIRMADA = "CONFIRMADA"    # aluno confirmou presença
    CANCELADA = "CANCELADA"      # aluno cancelou
    EXPIRADA = "EXPIRADA"        # prazo de confirmacao venceu (sem falta)
    REALIZADA = "REALIZADA"      # aluno confirmou e compareceu
    FALTOU = "FALTOU"            # aluno confirmou e nao compareceu (gera falta)


# Reservas que ocupam vaga em um horário
STATUS_ATIVOS = (StatusReserva.PENDENTE, StatusReserva.ACEITA, StatusReserva.CONFIRMADA)


@dataclass
class Aluno:
    id: int
    nome: str
    email: str

    @classmethod
    def de_linha(cls, linha):
        return cls(linha["id"], linha["nome"], linha["email"])


@dataclass
class Monitor:
    id: int
    nome: str
    email: str
    disciplina: str

    @classmethod
    def de_linha(cls, linha):
        return cls(linha["id"], linha["nome"], linha["email"], linha["disciplina"])


@dataclass
class Horario:
    id: int
    monitor_id: int
    inicio: datetime
    fim: datetime
    capacidade: int

    @classmethod
    def de_linha(cls, linha):
        return cls(
            linha["id"],
            linha["monitor_id"],
            datetime.fromisoformat(linha["inicio"]),
            datetime.fromisoformat(linha["fim"]),
            linha["capacidade"],
        )

    def limite_confirmacao(self):
        """Último instante para reservar, aceitar e confirmar (RN05)."""
        return self.inicio - timedelta(hours=PRAZO_CONFIRMACAO_HORAS)


@dataclass
class Reserva:
    id: int
    aluno_id: int
    horario_id: int
    duvida: str
    status: StatusReserva
    criada_em: datetime
    confirmada_em: Optional[datetime]

    @classmethod
    def de_linha(cls, linha):
        confirmada = linha["confirmada_em"]
        return cls(
            linha["id"],
            linha["aluno_id"],
            linha["horario_id"],
            linha["duvida"],
            StatusReserva(linha["status"]),
            datetime.fromisoformat(linha["criada_em"]),
            datetime.fromisoformat(confirmada) if confirmada else None,
        )


@dataclass
class ProvaAusencia:
    id: int
    monitor_id: int
    data: date

    @classmethod
    def de_linha(cls, linha):
        return cls(linha["id"], linha["monitor_id"], date.fromisoformat(linha["data"]))
