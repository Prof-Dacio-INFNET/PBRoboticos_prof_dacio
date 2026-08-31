"""Cliente da action VarrerCena -- pede, acompanha e sabe cancelar.

Use para ver os tres momentos que so a action tem:
  1. o objetivo ser ACEITO ou REJEITADO
  2. o feedback chegando DURANTE a execucao
  3. o cancelamento funcionando de verdade (Ctrl+C aqui cancela la)

    ros2 run aula07_acoes cliente_varredura
    ros2 run aula07_acoes cliente_varredura --ros-args -p duracao_s:=20.0
"""
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from pb_interfaces.action import VarrerCena


class ClienteVarredura(Node):
    def __init__(self):
        super().__init__('cliente_varredura')
        self.declare_parameter('duracao_s', 10.0)
        self.declare_parameter('classe_alvo', 'objeto_alvo')
        self.declare_parameter('minimo_para_parar', 0)

        self.cliente = ActionClient(self, VarrerCena, 'varrer_cena')
        self.goal_handle = None

    def enviar(self):
        self.get_logger().info('esperando o servidor da action...')
        if not self.cliente.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                "servidor 'varrer_cena' nao apareceu em 10s. Ele esta rodando? "
                "'ros2 action list' mostra a action?")
            return False

        objetivo = VarrerCena.Goal()
        objetivo.duracao_s = float(self.get_parameter('duracao_s').value)
        objetivo.classe_alvo = self.get_parameter('classe_alvo').value
        objetivo.minimo_para_parar = int(self.get_parameter('minimo_para_parar').value)

        self.get_logger().info("enviando objetivo: %.1fs procurando '%s'"
                               % (objetivo.duracao_s, objetivo.classe_alvo))
        fut = self.cliente.send_goal_async(objetivo, feedback_callback=self.ao_feedback)
        fut.add_done_callback(self.ao_responder)
        return True

    def ao_feedback(self, msg):
        f = msg.feedback
        self.get_logger().info('  ... %.1fs  progresso=%.0f%%  vistos=%d'
                               % (f.decorrido_s, f.progresso * 100, f.vistos_ate_agora))

    def ao_responder(self, fut):
        gh = fut.result()
        if not gh.accepted:
            # REJEITADO e diferente de FALHOU: o servidor olhou o pedido e disse nao.
            self.get_logger().error('objetivo REJEITADO pelo servidor')
            rclpy.shutdown()
            return
        self.goal_handle = gh
        self.get_logger().info('objetivo aceito - acompanhando (Ctrl+C cancela)')
        gh.get_result_async().add_done_callback(self.ao_terminar)

    def ao_terminar(self, fut):
        r = fut.result().result
        self.get_logger().info(
            'RESULTADO: total_visto=%d  confianca_media=%.2f  quadros=%d  |  %s'
            % (r.total_visto, r.confianca_media, r.quadros_analisados, r.resumo))
        rclpy.shutdown()

    def cancelar(self):
        if self.goal_handle is not None:
            self.get_logger().info('pedindo cancelamento...')
            self.goal_handle.cancel_goal_async()


def main():
    rclpy.init()
    no = ClienteVarredura()
    if not no.enviar():
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        return
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        # Ctrl+C aqui NAO mata a tarefa la: manda cancelar e espera a confirmacao.
        # E essa diferenca que o gate G2.3 procura.
        no.cancelar()
        rclpy.spin_once(no, timeout_sec=2.0)
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
