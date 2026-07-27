"""Serviço: /contagem (std_srvs/Trigger) responde quantas mensagens já passaram.
Prenuncia o /vision/status do TP1 (pergunta/resposta síncrona)."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger


class ServicoContagem(Node):
    def __init__(self):
        super().__init__('servico_contagem')
        self.total = 0
        self.create_subscription(String, '/camera/status', self._conta, 10)
        self.create_service(Trigger, '/contagem', self._responder)
        self.get_logger().info('Serviço /contagem pronto (chame com ros2 service call)')

    def _conta(self, _msg):
        self.total += 1

    def _responder(self, request, response):
        response.success = True
        response.message = f'{self.total} mensagens em /camera/status até agora'
        return response


def main():
    rclpy.init(); no = ServicoContagem()
    try: rclpy.spin(no)
    except KeyboardInterrupt: pass
    finally: no.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
