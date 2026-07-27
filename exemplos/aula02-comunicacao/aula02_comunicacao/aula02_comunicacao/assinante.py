"""Subscriber: escuta /camera/status e conta quantas mensagens recebeu."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Assinante(Node):
    def __init__(self):
        super().__init__('assinante')
        self.total = 0
        self.create_subscription(String, '/camera/status', self.ao_receber, 10)

    def ao_receber(self, msg: String):
        self.total += 1
        self.get_logger().info(f'[{self.total}] recebi: "{msg.data}"')


def main():
    rclpy.init(); no = Assinante()
    try: rclpy.spin(no)
    except KeyboardInterrupt: pass
    finally: no.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
