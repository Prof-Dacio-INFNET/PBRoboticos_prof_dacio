"""O mundo como no ROS 2: publica /scan, /odom e a TF odom -> base_footprint.

Este no faz o papel que o Gazebo faria no TP3, e faz de proposito a versao
minima: sem fisica, sem render, sem janela. O que ele entrega sao as MESMAS
interfaces -- e e' das interfaces que o seu sistema depende, nao do simulador.

    ros2 run aula11_mundo mundo
    ros2 topic echo /deriva
    ros2 param set /mundo deriva_pct 0.0     # desliga a deriva e compare

A deriva e' o ponto da aula. A odometria e' integrada com um erro sistematico
de rotacao, como a de um robo real cujo raio de roda voce mediu com regua. O
/scan, esse, sai da pose VERDADEIRA. Entao, com o tempo, o que o robo acha que
ve deixa de bater com o que ele ve -- e e' exatamente esse buraco que o SLAM
preenche publicando map -> odom.
"""
import math

import numpy as np
import rclpy
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32
from tf2_ros import TransformBroadcaster

from .mapa import Mundo
from .nucleo import aplicar_deriva, passo_diferencial


def quat_de_yaw(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class NoMundo(Node):
    def __init__(self):
        super().__init__('mundo')

        self.declare_parameter('taxa_hz', 20.0)
        self.declare_parameter('taxa_scan_hz', 5.0)
        self.declare_parameter('feixes', 360)
        self.declare_parameter('alcance_max', 6.0)
        self.declare_parameter('deriva_pct', 3.0)
        self.declare_parameter('raio_robo', 0.20)
        self.declare_parameter('pose_inicial', [2.0, 4.0, 0.0])
        self.declare_parameter('quadro_base', 'base_footprint')
        self.declare_parameter('laser_x', 0.10)
        self.declare_parameter('quadro_laser', 'laser_frame')

        p = self.get_parameter
        self.taxa = p('taxa_hz').value
        self.alcance = p('alcance_max').value
        self.raio = p('raio_robo').value
        self.base = p('quadro_base').value
        self.laser = p('quadro_laser').value
        self.laser_x = float(p('laser_x').value)

        x0, y0, t0 = p('pose_inicial').value
        self.verdadeira = [float(x0), float(y0), float(t0)]   # onde o robo esta
        self.odom = [float(x0), float(y0), float(t0)]         # onde ele ACHA que esta

        self.mundo = Mundo()
        self.angulos = np.linspace(-math.pi, math.pi, int(p('feixes').value),
                                   endpoint=False)
        self.v = self.w = 0.0

        # O mundo VERDADEIRO, publicado so' para voce poder ver. O robo nao tem
        # acesso a isto -- se tivesse, nao precisaria de SLAM. Ele existe no
        # RViz2 para que a deriva seja visivel: as paredes ficam paradas no
        # quadro `map` enquanto o laser, desenhado pela odometria, escorrega
        # para fora delas.
        qos_fixo = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_verdade = self.create_publisher(OccupancyGrid, 'mundo_real', qos_fixo)

        self.pub_scan = self.create_publisher(LaserScan, 'scan', 10)
        self.pub_odom = self.create_publisher(Odometry, 'odom', 10)
        self.pub_deriva = self.create_publisher(Float32, 'deriva', 10)
        self.tf = TransformBroadcaster(self)
        self.create_subscription(Twist, 'cmd_vel', self.ouvir_cmd, 10)

        self.create_timer(1.0 / self.taxa, self.passo)
        self.create_timer(1.0 / p('taxa_scan_hz').value, self.varrer)

        self.get_logger().info(
            f'mundo {self.mundo.nx}x{self.mundo.ny} celulas | '
            f'deriva {p("deriva_pct").value}% | pose {self.verdadeira}')

        self.publicar_verdade()

    # ------------------------------------------------------------- entradas
    def ouvir_cmd(self, msg: Twist):
        self.v, self.w = msg.linear.x, msg.angular.z

    # ------------------------------------------------------------- simulacao
    def livre(self, x, y) -> bool:
        """O robo cabe aqui? Testa oito pontos na borda, nao so' o centro."""
        for a in np.linspace(0, 2 * math.pi, 8, endpoint=False):
            if self.mundo.ocupado(x + self.raio * math.cos(a),
                                  y + self.raio * math.sin(a)):
                return False
        return True

    def passo(self):
        dt = 1.0 / self.taxa

        x, y, th = self.verdadeira
        nx, ny, nth = passo_diferencial(self.verdadeira, self.v, self.w, dt)
        self.verdadeira = [nx, ny, nth] if self.livre(nx, ny) \
            else [x, y, nth]                   # bateu: gira, mas nao avanca

        # A odometria nao sabe que bateu -- ela so' integra o que foi comandado,
        # com o erro de escala. E' por isso que ela diverge por colisao tambem.
        self.odom = list(aplicar_deriva(
            self.odom, self.v, self.w, dt,
            self.get_parameter('deriva_pct').value))

        self.publicar_odom()
        d = Float32()
        d.data = float(math.hypot(self.verdadeira[0] - self.odom[0],
                                  self.verdadeira[1] - self.odom[1]))
        self.pub_deriva.publish(d)

    # ------------------------------------------------------------- saidas
    def publicar_odom(self):
        agora = self.get_clock().now().to_msg()
        x, y, th = self.odom
        qx, qy, qz, qw = quat_de_yaw(th)

        t = TransformStamped()
        t.header.stamp = agora
        t.header.frame_id = 'odom'
        t.child_frame_id = self.base
        t.transform.translation.x, t.transform.translation.y = x, y
        (t.transform.rotation.x, t.transform.rotation.y,
         t.transform.rotation.z, t.transform.rotation.w) = qx, qy, qz, qw
        self.tf.sendTransform(t)

        o = Odometry()
        o.header.stamp = agora
        o.header.frame_id = 'odom'
        o.child_frame_id = self.base
        o.pose.pose.position.x, o.pose.pose.position.y = x, y
        (o.pose.pose.orientation.x, o.pose.pose.orientation.y,
         o.pose.pose.orientation.z, o.pose.pose.orientation.w) = qx, qy, qz, qw
        o.twist.twist.linear.x, o.twist.twist.angular.z = self.v, self.w
        self.pub_odom.publish(o)

    def publicar_verdade(self):
        """A grade de ocupacao como OccupancyGrid, uma vez, em transient local."""
        g = OccupancyGrid()
        g.header.stamp = self.get_clock().now().to_msg()
        g.header.frame_id = 'map'
        g.info.resolution = float(self.mundo.res)
        g.info.width = int(self.mundo.nx)
        g.info.height = int(self.mundo.ny)
        g.info.origin.position.x = 0.0
        g.info.origin.position.y = 0.0
        g.info.origin.orientation.w = 1.0
        # OccupancyGrid e' row-major a partir da origem (canto inferior
        # esquerdo) -- a mesma ordem da nossa grade, entao nao ha flip aqui.
        g.data = [100 if v else 0 for v in self.mundo.grade.ravel()]
        self.pub_verdade.publish(g)

    def pose_do_laser(self):
        """Onde o laser esta, no mundo: o centro do robo mais o deslocamento.

        Parece detalhe e nao e. A TF diz ao ROS 2 que o laser fica `laser_x` a
        frente do base_footprint; se a medida sair do centro, existe um vies
        sistematico desse tamanho entre onde o feixe foi medido e onde todo o
        resto do sistema acha que ele foi. Nada acusa: o scan chega bonito, o
        SLAM fecha um mapa deslocado, e o AMCL converge com erro constante.
        """
        x, y, th = self.verdadeira
        return (x + self.laser_x * math.cos(th),
                y + self.laser_x * math.sin(th),
                th)

    def varrer(self):
        leituras = self.mundo.medir(*self.pose_do_laser(), self.angulos,
                                    alcance_max=self.alcance)
        s = LaserScan()
        s.header.stamp = self.get_clock().now().to_msg()
        s.header.frame_id = self.laser
        s.angle_min = float(self.angulos[0])
        s.angle_max = float(self.angulos[-1])
        s.angle_increment = float(self.angulos[1] - self.angulos[0])
        s.range_min, s.range_max = 0.05, float(self.alcance)
        s.ranges = [float(r) for r in leituras]
        self.pub_scan.publish(s)


def main():
    rclpy.init()
    no = NoMundo()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
