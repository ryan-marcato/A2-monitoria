# Sistema de Monitoria

Sistema de terminal (CLI) para organizar a monitoria: o monitor cadastra horários de 30 minutos, os alunos reservam descrevendo a dúvida, o monitor aceita ou recusa, o aluno confirma presença e o sistema registra faltas e gera relatórios.

**Equipe:** Lucas Youssif Abdallah Catore · Ryan Henrique Escandelari Marcato

## Como rodar

Requisitos: Python 3.10+.

```bash
cd src
python -m monitoria.cli
```

O banco `monitoria.db` (SQLite) é criado automaticamente na pasta em que o comando é executado.

## Como testar

```bash
pip install -r requirements.txt
pytest
```

## Fluxo de uma reserva

1. O aluno reserva um horário com a dúvida → `PENDENTE`.
2. O monitor aceita (`ACEITA`) ou recusa (`RECUSADA`).
3. O aluno confirma presença até 2 horas antes → `CONFIRMADA`. Se não confirmar no prazo → `EXPIRADA` (sem falta).
4. Depois do atendimento, o monitor registra quem compareceu (`REALIZADA`) ou faltou (`FALTOU`, gera falta).
5. O aluno pode cancelar (`CANCELADA`) antes do início, sem falta.

Só participa do atendimento quem confirmou presença. Só recebe falta quem confirmou e não apareceu.

## Estrutura

```
src/monitoria/
├── config.py       constantes (duração do bloco, capacidade, prazo)
├── models.py       dataclasses e enums
├── database.py     conexão SQLite e tabelas
├── erros.py        RegraDeNegocioError
├── cli.py          menus (entrada e saída)
└── services/       regras de negócio
    ├── cadastro.py
    ├── agendamento.py
    ├── confirmacao.py
    ├── provas.py
    └── relatorio.py
tests/              testes por módulo + fluxo completo
docs/               histórias de usuário e projeto inicial
```

A CLI só chama os serviços; os serviços nunca usam `print` ou `input`. Assim, uma interface web poderia reutilizar as mesmas regras.

## Regras de negócio

| ID | Regra | Onde |
|----|-------|------|
| RN01 | Todo horário dura 30 minutos. | agendamento |
| RN02 | A dúvida é obrigatória para reservar. | agendamento |
| RN03 | O horário aceita reservas até a capacidade (padrão 5). | agendamento |
| RN04 | O aluno não tem duas reservas ativas no mesmo horário. | agendamento |
| RN05 | A confirmação é feita até 2 horas antes do início. | confirmacao |
| RN06 | Reserva não confirmada no prazo expira, sem falta, e libera a vaga. | confirmacao |
| RN07 | Só quem confirmou e não compareceu recebe falta (uma por reserva). | confirmacao |
| RN08 | O monitor registra no máximo 2 datas de prova; não há horários nelas. | provas / agendamento |
| RN09 | Horas trabalhadas = 30 min por horário com pelo menos um aluno presente. | relatorio |
| RN10 | O monitor aceita ou recusa cada reserva pendente. | agendamento |
