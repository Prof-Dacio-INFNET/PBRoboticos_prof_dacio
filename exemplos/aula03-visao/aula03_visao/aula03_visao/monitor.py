"""Cliente do serviço /vision/status — o outro lado da pergunta/resposta.

Chama o serviço a cada N segundos e loga a resposta. Serve para (a) mostrar em
aula que serviço tem *cliente*, e (b) provar que o pipeline está vivo sem
precisar de interface gráfica.

    ros2 run aula03_visao monitor --ros-args -p periodo:=2.0
"""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class Monitor(Node):
    def __init__(self):
        super().__init__('monitor')
        self.declare_parameter('periodo', 3.0)
        self.cli = self.create_client(Trigger, '/vision/status')
        while not self.cli.wait_for_service(timeout_sec=2.0):
            self.get_logger().info('Esperando /vision/status aparecer...')
        self.create_timer(float(self.get_parameter('periodo').value), self.perguntar)

    def perguntar(self):
        futuro = self.cli.call_async(Trigger.Request())
        futuro.add_done_callback(self.responder)

    def responder(self, futuro):
        try:
            r = futuro.result()
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f'Falha na chamada: {e}')
            return
        self.get_logger().info(f'status: {r.message}')


def main():
    rclpy.init()
    no = Monitor()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        # Ctrl+C: o rclpy do Humble ja pode ter derrubado o contexto pelo
        # signal handler. Chamar shutdown() de novo levanta
        # "rcl_shutdown already called on the given context" -- barulho de
        # saida que assusta a turma sem que nada tenha quebrado. rclpy.ok()
        # resolve: so fecha o que ainda estiver de pe.
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
