"""Servidor da action VarrerCena -- tarefa longa, com feedback e cancelavel.

O que este no faz: recebe "observe a cena por N segundos procurando X",
publica progresso enquanto observa, e devolve um resumo no fim. Pode terminar
antes se ja tiver visto o suficiente, e pode ser CANCELADO a qualquer momento.

A parte que a maioria erra esta em duas linhas deste arquivo, e nao no .action:

  1. ReentrantCallbackGroup no ActionServer
  2. MultiThreadedExecutor no main()

Sem as duas, o execute_callback ocupa a unica thread do executor e o pedido de
cancelamento NUNCA chega a ser processado -- o cliente pede cancel, o servidor
nao ouve, e a tarefa vai ate o fim. O sintoma e cruel porque nao ha erro: tudo
"funciona", so nao cancela. E o cancelamento e exatamente o que o gate G2.3
testa.
"""
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from pb_interfaces.action import VarrerCena
from pb_interfaces.msg import Deteccoes

PERIODO_S = 0.2          # com que frequencia o laco acorda e publica feedback


class ServidorVarredura(Node):
    def __init__(self):
        super().__init__('servidor_varredura')
        self.ultimo = Deteccoes()
        self.quadros = 0
        self.recebido_em = None       # quando chegou a ultima percepcao (monotonico)
        self.ocupado = False          # um objetivo por vez -- ver aceitar_objetivo()

        self.declare_parameter('timeout_percepcao_s', 3.0)
        self.declare_parameter('carencia_s', 3.0)

        # Assina a percepcao da Aula 6. Se ela nao estiver no ar, a varredura
        # roda mesmo assim e relata zero -- degradar, nao quebrar.
        self.create_subscription(Deteccoes, '/vision/deteccoes', self._ao_receber, 10)

        # ReentrantCallbackGroup: permite que callbacks deste no rodem em
        # paralelo. E o que deixa o cancelamento ser ouvido enquanto o
        # execute_callback ainda esta trabalhando.
        self._server = ActionServer(
            self, VarrerCena, 'varrer_cena',
            execute_callback=self.executar,
            goal_callback=self.aceitar_objetivo,
            cancel_callback=self.aceitar_cancelamento,
            callback_group=ReentrantCallbackGroup())

        self.get_logger().info(
            "servidor da action 'varrer_cena' no ar - teste com: "
            "ros2 action send_goal /varrer_cena pb_interfaces/action/VarrerCena "
            "\"{duracao_s: 10.0, classe_alvo: 'objeto_alvo', minimo_para_parar: 0}\" --feedback")

    def _ao_receber(self, msg):
        self.ultimo = msg
        self.quadros += 1
        self.recebido_em = time.monotonic()

    # -------------------------------------------------------- politicas
    def aceitar_objetivo(self, goal_request):
        """Chamado ANTES de executar. E aqui que se recusa pedido absurdo."""
        # Um objetivo por vez. Por padrao o rclpy aceita quantos vierem e executa
        # todos em paralelo -- o que quase sempre esta errado num robo fisico: ele
        # tem um braco so. Rejeitar enquanto ocupado e a politica honesta, e o
        # cliente descobre na hora em vez de descobrir por comportamento estranho.
        if self.ocupado:
            self.get_logger().warn('objetivo REJEITADO: ja existe uma varredura em curso')
            return GoalResponse.REJECT
        # Honestidade sobre o limite disto: 'ocupado' so vira True quando a
        # execucao COMECA, entao dois pedidos que chegam no mesmo milissegundo
        # podem passar os dois. Para uma aula, a janela e irrelevante; para um
        # robo de verdade, a serializacao correta vive no handle_accepted_callback,
        # com fila. Saber onde a sua solucao simples quebra faz parte de escolher
        # a solucao simples.

        d = goal_request.duracao_s
        if not (0.0 < d <= 120.0):
            self.get_logger().warn('objetivo REJEITADO: duracao_s=%.1f fora de (0, 120]' % d)
            return GoalResponse.REJECT
        self.get_logger().info("objetivo aceito: %.1fs procurando '%s'"
                               % (d, goal_request.classe_alvo))
        return GoalResponse.ACCEPT

    def aceitar_cancelamento(self, goal_handle):
        """Aceitar cancelamento e uma DECISAO, nao um automatismo.

        Um robo com o braco no meio de um movimento pode precisar recusar, ou
        aceitar e recolher antes. Aqui observar e inofensivo, entao aceitamos.
        """
        self.get_logger().info('cancelamento pedido - aceitando')
        return CancelResponse.ACCEPT

    # -------------------------------------------------------- execucao
    def executar(self, goal_handle):
        self.ocupado = True
        try:
            return self._executar(goal_handle)
        finally:
            self.ocupado = False           # solta a vaga em QUALQUER saida

    def _executar(self, goal_handle):
        pedido = goal_handle.request
        alvo = pedido.classe_alvo
        limite = pedido.minimo_para_parar
        timeout = float(self.get_parameter('timeout_percepcao_s').value)
        carencia = float(self.get_parameter('carencia_s').value)

        inicio = time.monotonic()          # monotonico: nao anda para tras
        quadros_no_inicio = self.quadros
        picos, soma_conf, amostras = 0, 0.0, 0

        while True:
            decorrido = time.monotonic() - inicio

            # ---- 1. o cancelamento vem ANTES de qualquer outra coisa ----
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()     # sem esta linha o cliente fica pendurado
                self.get_logger().info('varredura CANCELADA em %.1fs' % decorrido)
                return self._resultado(picos, soma_conf, amostras,
                                       self.quadros - quadros_no_inicio,
                                       'cancelada em %.1fs' % decorrido)

            # ---- 1b. ABORTAR e diferente de CANCELAR ----
            # Cancelar e decisao de quem pediu. Abortar e decisao do servidor:
            # ele desistiu porque a tarefa deixou de ser possivel. Aqui, ficar
            # sem percepcao e exatamente isso -- varrer a cena sem imagem nao e
            # uma varredura ruim, e uma varredura que nao esta acontecendo.
            mudo = (self.recebido_em is None or (time.monotonic() - self.recebido_em) > timeout)
            if decorrido > carencia and mudo:
                goal_handle.abort()
                self.get_logger().error('varredura ABORTADA: sem percepcao ha mais de %.1fs' % timeout)
                return self._resultado(picos, soma_conf, amostras,
                                       self.quadros - quadros_no_inicio,
                                       'abortada: percepcao muda ha mais de %.1fs' % timeout)

            # ---- 2. amostra a percepcao ----
            vistos = sum(1 for d in self.ultimo.deteccoes if d.classe == alvo)
            if vistos:
                picos = max(picos, vistos)
                soma_conf += sum(d.confianca for d in self.ultimo.deteccoes if d.classe == alvo)
                amostras += vistos

            # ---- 3. sucesso antecipado ----
            if limite and picos >= limite:
                goal_handle.succeed()
                return self._resultado(picos, soma_conf, amostras,
                                       self.quadros - quadros_no_inicio,
                                       'parou cedo: viu %d (minimo %d) em %.1fs'
                                       % (picos, limite, decorrido))

            # ---- 4. fim do prazo ----
            if decorrido >= pedido.duracao_s:
                goal_handle.succeed()
                return self._resultado(picos, soma_conf, amostras,
                                       self.quadros - quadros_no_inicio,
                                       'varredura completa de %.1fs' % decorrido)

            # ---- 5. feedback: o que diferencia action de servico ----
            fb = VarrerCena.Feedback()
            fb.decorrido_s = float(decorrido)
            fb.vistos_ate_agora = picos
            fb.progresso = float(min(1.0, decorrido / max(pedido.duracao_s, 1e-6)))
            goal_handle.publish_feedback(fb)

            time.sleep(PERIODO_S)

    def _resultado(self, picos, soma_conf, amostras, quadros, resumo):
        r = VarrerCena.Result()
        r.total_visto = picos
        r.confianca_media = float(soma_conf / amostras) if amostras else 0.0
        r.quadros_analisados = quadros
        r.resumo = resumo
        return r


def main():
    rclpy.init()
    no = ServidorVarredura()
    # MultiThreadedExecutor: sem ele, o execute_callback prende a unica thread
    # e o cancelamento nunca e processado.
    executor = MultiThreadedExecutor()
    try:
        rclpy.spin(no, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
