"""Le /vision/deteccoes e imprime uma linha legivel por quadro.

Existe para a aula ter uma janela que se olha sem rqt: mostra que a mensagem
nova carrega classe, confianca e posicao -- coisas que um Int32 nao tinha.
"""
import rclpy
from rclpy.node import Node

from pb_interfaces.msg import Deteccoes


class Monitor(Node):
    def __init__(self):
        super().__init__('monitor_deteccoes')
        self.create_subscription(Deteccoes, '/vision/deteccoes', self.ao_receber, 10)
        self.get_logger().info('monitor no ar - assinando /vision/deteccoes')

    def ao_receber(self, msg):
        if msg.total == 0:
            self.get_logger().info('cena vazia')
            return
        partes = ["%s(%.2f) em (%d,%d) area=%d" % (d.classe, d.confianca, d.x, d.y, d.area)
                  for d in msg.deteccoes]
        # O stamp vem do Header: e ele que permite dizer se isto e de agora.
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.get_logger().info("t=%.2f  total=%d  %s" % (t, msg.total, ' | '.join(partes)))


def main():
    rclpy.init()
    no = Monitor()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
