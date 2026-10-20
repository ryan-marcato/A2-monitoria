"""Interface de linha de comando (menu interativo).

Esta camada so le entradas e mostra mensagens. As regras ficam em services/.
Para rodar (a partir da pasta src):  python -m monitoria.cli
"""
from datetime import datetime

from monitoria import database
from monitoria.config import CAPACIDADE_PADRAO
from monitoria.erros import RegraDeNegocioError
from monitoria.services import agendamento, cadastro, confirmacao, provas, relatorio

FORMATO_DATA_HORA = "%d/%m/%Y %H:%M"
FORMATO_DATA = "%d/%m/%Y"


#----------Funcoes de entrada e saida----------

def ler_texto(mensagem):
    return input(mensagem).strip()


def ler_numero(mensagem, padrao=None):
    """Le um numero inteiro. Se o usuario so apertar Enter e houver padrao, usa o padrao."""
    while True:
        texto = input(mensagem).strip()
        if texto == "" and padrao is not None:
            return padrao
        try:
            return int(texto)
        except ValueError:
            print("Digite um número válido.")


def ler_data_hora(mensagem):
    while True:
        try:
            return datetime.strptime(input(mensagem).strip(), FORMATO_DATA_HORA)
        except ValueError:
            print("Formato inválido. Use DD/MM/AAAA HH:MM (ex.: 25/10/2026 14:00).")


def ler_data(mensagem):
    while True:
        try:
            return datetime.strptime(input(mensagem).strip(), FORMATO_DATA).date()
        except ValueError:
            print("Formato inválido. Use DD/MM/AAAA (ex.: 25/10/2026).")


def formatar(data_hora):
    return data_hora.strftime(FORMATO_DATA_HORA)


def mostrar_menu(titulo, opcoes):
    print(f"\n=== {titulo} ===")
    for numero, texto in enumerate(opcoes, start=1):
        print(f"{numero} - {texto}")
    print("0 - Voltar")
    return ler_numero("Escolha: ")


#----------Acoes do aluno----------

def mostrar_horarios(conn):
    horarios = agendamento.listar_horarios_disponiveis(conn)
    if not horarios:
        print("Nenhum horário disponível no momento.")
    for item in horarios:
        h = item["horario"]
        print(f"[{h.id}] {formatar(h.inicio)} | {item['monitor']} ({item['disciplina']}) "
              f"| vagas: {item['vagas']}")
    return horarios


def reservar_horario(conn, aluno):
    if not mostrar_horarios(conn):
        return
    horario_id = ler_numero("ID do horário: ")
    duvida = ler_texto("Descreva sua dúvida: ")
    agendamento.reservar(conn, aluno.id, horario_id, duvida)
    print("Reserva feita! Aguarde o monitor aceitar e depois confirme sua presença.")


def mostrar_reservas(conn, aluno):
    reservas = agendamento.listar_reservas_do_aluno(conn, aluno.id)
    if not reservas:
        print("Você ainda não tem reservas.")
    for r in reservas:
        print(f"[{r['reserva_id']}] {formatar(r['inicio'])} | {r['monitor']} "
              f"| {r['status'].value} | {r['duvida']}")
    return reservas


def confirmar_presenca(conn, aluno):
    if not mostrar_reservas(conn, aluno):
        return
    reserva_id = ler_numero("ID da reserva a confirmar: ")
    confirmacao.confirmar_presenca(conn, aluno.id, reserva_id)
    print("Presença confirmada!")


def cancelar_reserva(conn, aluno):
    if not mostrar_reservas(conn, aluno):
        return
    reserva_id = ler_numero("ID da reserva a cancelar: ")
    agendamento.cancelar_reserva(conn, aluno.id, reserva_id)
    print("Reserva cancelada.")


def mostrar_faltas(conn, aluno):
    faltas = confirmacao.listar_faltas_do_aluno(conn, aluno.id)
    if not faltas:
        print("Você não tem faltas registradas.")
    for f in faltas:
        print(f"{formatar(f['inicio'])} | {f['monitor']} | {f['duvida']}")
    print(f"Total de faltas: {len(faltas)}")


def menu_aluno(conn, aluno):
    opcoes = [
        "Ver horários disponíveis",
        "Reservar horário",
        "Minhas reservas",
        "Confirmar presença",
        "Cancelar reserva",
        "Minhas faltas",
    ]
    while True:
        confirmacao.expirar_reservas(conn)  # RN06: libera vagas de quem não confirmou
        escolha = mostrar_menu(f"Aluno: {aluno.nome}", opcoes)
        try:
            if escolha == 1:
                mostrar_horarios(conn)
            elif escolha == 2:
                reservar_horario(conn, aluno)
            elif escolha == 3:
                mostrar_reservas(conn, aluno)
            elif escolha == 4:
                confirmar_presenca(conn, aluno)
            elif escolha == 5:
                cancelar_reserva(conn, aluno)
            elif escolha == 6:
                mostrar_faltas(conn, aluno)
            elif escolha == 0:
                break
            else:
                print("Opção inválida.")
        except RegraDeNegocioError as erro:
            print(f"Erro: {erro}")


#----------Acoes do monitor----------

def cadastrar_horario(conn, monitor):
    inicio = ler_data_hora("Início do horário (DD/MM/AAAA HH:MM): ")
    capacidade = ler_numero(f"Máximo de alunos [{CAPACIDADE_PADRAO}]: ", CAPACIDADE_PADRAO)
    horario = agendamento.criar_horario(conn, monitor.id, inicio, capacidade)
    print(f"Horário criado: {formatar(horario.inicio)} até {horario.fim.strftime('%H:%M')}.")


def responder_duvidas(conn, monitor):
    pendentes = agendamento.listar_pendentes_do_monitor(conn, monitor.id)
    if not pendentes:
        print("Nenhuma dúvida pendente.")
        return
    for p in pendentes:
        print(f"[{p['reserva_id']}] {formatar(p['inicio'])} | {p['aluno']} | {p['duvida']}")
    reserva_id = ler_numero("ID da reserva a responder: ")
    resposta = ler_texto("Aceitar (A) ou recusar (R)? ").upper()
    if resposta not in ("A", "R"):
        print("Resposta inválida.")
        return
    agendamento.responder_reserva(conn, monitor.id, reserva_id, resposta == "A")
    print("Reserva aceita." if resposta == "A" else "Reserva recusada.")


def registrar_presenca(conn, monitor):
    confirmados = confirmacao.listar_confirmados_para_presenca(conn, monitor.id)
    if not confirmados:
        print("Nenhum aluno confirmado aguardando registro de presença.")
        return
    for c in confirmados:
        print(f"[{c['reserva_id']}] {formatar(c['inicio'])} | {c['aluno']} | {c['duvida']}")
    reserva_id = ler_numero("ID da reserva: ")
    resposta = ler_texto("O aluno compareceu? (S/N): ").upper()
    if resposta not in ("S", "N"):
        print("Resposta inválida.")
        return
    confirmacao.registrar_presenca(conn, monitor.id, reserva_id, resposta == "S")
    print("Presença registrada." if resposta == "S" else "Falta registrada.")


def registrar_prova(conn, monitor):
    registradas = provas.listar_provas(conn, monitor.id)
    for p in registradas:
        print(f"Prova já registrada: {p.data.strftime(FORMATO_DATA)}")
    data = ler_data("Data da prova em que você estará ausente (DD/MM/AAAA): ")
    provas.registrar_prova(conn, monitor.id, data)
    print("Data de prova registrada.")


def mostrar_relatorio_duvidas(conn, monitor):
    linhas = relatorio.relatorio_duvidas(conn, monitor.id)
    if not linhas:
        print("Nenhuma dúvida recebida ainda.")
    for l in linhas:
        print(f"{formatar(l['inicio'])} | {l['aluno']} | {l['duvida']} | {l['status'].value}")


def mostrar_relatorio_horas(conn, monitor):
    dados = relatorio.relatorio_horas(conn, monitor.id)
    print(f"Atendimentos realizados: {dados['atendimentos']}")
    print(f"Horas trabalhadas: {dados['horas']:.1f} h ({dados['minutos']} min)")


def menu_monitor(conn, monitor):
    opcoes = [
        "Cadastrar horário livre",
        "Ver dúvidas pendentes (aceitar/recusar)",
        "Registrar presença/falta",
        "Registrar data de prova",
        "Relatório de dúvidas",
        "Relatório de horas trabalhadas",
    ]
    while True:
        confirmacao.expirar_reservas(conn)
        escolha = mostrar_menu(f"Monitor: {monitor.nome} ({monitor.disciplina})", opcoes)
        try:
            if escolha == 1:
                cadastrar_horario(conn, monitor)
            elif escolha == 2:
                responder_duvidas(conn, monitor)
            elif escolha == 3:
                registrar_presenca(conn, monitor)
            elif escolha == 4:
                registrar_prova(conn, monitor)
            elif escolha == 5:
                mostrar_relatorio_duvidas(conn, monitor)
            elif escolha == 6:
                mostrar_relatorio_horas(conn, monitor)
            elif escolha == 0:
                break
            else:
                print("Opção inválida.")
        except RegraDeNegocioError as erro:
            print(f"Erro: {erro}")


#----------menu principal----------

def main():
    conn = database.conectar()
    opcoes = ["Cadastrar aluno", "Entrar como aluno", "Cadastrar monitor", "Entrar como monitor"]
    while True:
        escolha = mostrar_menu("Sistema de Monitoria", opcoes)
        try:
            if escolha == 1:
                aluno = cadastro.cadastrar_aluno(conn, ler_texto("Nome: "), ler_texto("E-mail: "))
                print(f"Aluno {aluno.nome} cadastrado!")
            elif escolha == 2:
                aluno = cadastro.buscar_aluno_por_email(conn, ler_texto("E-mail: "))
                menu_aluno(conn, aluno)
            elif escolha == 3:
                monitor = cadastro.cadastrar_monitor(
                    conn, ler_texto("Nome: "), ler_texto("E-mail: "), ler_texto("Disciplina: ")
                )
                print(f"Monitor {monitor.nome} cadastrado!")
            elif escolha == 4:
                monitor = cadastro.buscar_monitor_por_email(conn, ler_texto("E-mail: "))
                menu_monitor(conn, monitor)
            elif escolha == 0:
                print("Até logo!")
                break
            else:
                print("Opção inválida.")
        except RegraDeNegocioError as erro:
            print(f"Erro: {erro}")
    conn.close()


if __name__ == "__main__":
    main()
