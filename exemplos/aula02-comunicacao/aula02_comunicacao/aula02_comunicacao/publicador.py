"""Publisher: publica um 'status' em /camera/status a cada 1s (padrão-esqueleto do TP1)."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Publicador(Node):
    def __init__(self):
        super().__init__('publicador')
        self.pub = self.create_publisher(String, '/camera/status', 10)
        self.n = 0
        self.create_timer(1.0, self.tick)
        self.get_logger().info('Publicando em /camera/status')

    def tick(self):
        msg = String()
        msg.data = f'frame {self.n}: 0 objeto(s) detectado(s)'  # troque pela sua lógica no TP1
        self.pub.publish(msg)
        self.n += 1


def main():
    rclpy.init(); no = Publicador()
    try: rclpy.spin(no)
    except KeyboardInterrupt: pass
    finally: no.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
