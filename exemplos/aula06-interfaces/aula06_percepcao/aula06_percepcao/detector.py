"""Percepcao que fala a propria lingua.

O TP1 publicava `std_msgs/Int32` em /vision/contagem e respondia
`std_srvs/srv/Trigger` em /vision/status. Funciona -- e para de funcionar no
dia em que voce precisa saber *o que* foi visto, com *que* confianca e *onde*.

Este no publica `pb_interfaces/msg/Deteccoes` e serve
`pb_interfaces/srv/StatusVisao`. Mesmo pipeline, mesma segmentacao por cor:
o que mudou foi o vocabulario.

Fontes:
  * sintetico (padrao) -- gera a cena internamente, roda sem nada mais no ar
  * topico             -- assina /camera/image_raw (o publicador da Aula 3)

    ros2 launch aula06_percepcao percepcao.launch.py
    ros2 launch aula06_percepcao percepcao.launch.py fonte:=topico
"""
import cv2
import numpy as np
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import Header

from pb_interfaces.msg import Deteccao, Deteccoes
from pb_interfaces.srv import StatusVisao

from .cena import frame as frame_sintetico, msg_para_frame

QOS_SENSOR = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST, depth=1)


class Detector(Node):
    def __init__(self):
        super().__init__('detector')
        self.declare_parameter('fonte', 'sintetico')     # sintetico | topico
        self.declare_parameter('classe', 'objeto_alvo')  # o rotulo do SEU dominio
        self.declare_parameter('h_min', 0)
        self.declare_parameter('h_max', 10)
        self.declare_parameter('s_min', 120)
        self.declare_parameter('v_min', 70)
        self.declare_parameter('area_min', 300)
        self.declare_parameter('fps', 15.0)

        self.fonte = self.get_parameter('fonte').value
        self.classe = self.get_parameter('classe').value
        self.k = 0
        self.ultimo = Deteccoes()          # guarda o ultimo resultado para o servico

        self.pub = self.create_publisher(Deteccoes, '/vision/deteccoes', 10)
        self.srv = self.create_service(StatusVisao, '/vision/status', self.responder_status)

        if self.fonte == 'topico':
            self.create_subscription(Image, '/camera/image_raw', self.ao_receber, QOS_SENSOR)
            self.get_logger().info('assinando /camera/image_raw')
        else:
            fps = float(self.get_parameter('fps').value)
            # Relogio monotonico: o de parede pode saltar no WSL2 e congelar o timer.
            try:
                self.create_timer(1.0 / max(fps, 1.0), self.tick,
                                  clock=Clock(clock_type=ClockType.STEADY_TIME))
            except TypeError:
                self.create_timer(1.0 / max(fps, 1.0), self.tick)

        self.get_logger().info(
            "detector no ar - classe='%s' - publica pb_interfaces/Deteccoes em "
            "/vision/deteccoes - servico /vision/status (pb_interfaces/StatusVisao)"
            % self.classe)

    # ------------------------------------------------------------ entradas
    def tick(self):
        self.processar(frame_sintetico(self.k))
        self.k += 1

    def ao_receber(self, msg):
        try:
            self.processar(msg_para_frame(msg))
        except ValueError as e:
            self.get_logger().warn(str(e), throttle_duration_sec=5.0)

    # ------------------------------------------------------------ nucleo
    def detectar(self, img):
        """BGR -> lista de Deteccao. Nada de ROS aqui dentro, de proposito."""
        p = self.get_parameter
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mascara = cv2.inRange(
            hsv,
            np.array([p('h_min').value, p('s_min').value, p('v_min').value], np.uint8),
            np.array([p('h_max').value, 255, 255], np.uint8))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        area_min = int(p('area_min').value)
        achados = []
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contornos:
            area = cv2.contourArea(c)
            if area < area_min:
                continue
            m = cv2.moments(c)
            if m['m00'] == 0:
                continue
            d = Deteccao()
            d.classe = self.classe
            # Confianca honesta: segmentacao por cor NAO produz probabilidade.
            # Usamos o quao "cheio" e o contorno como proxy, e dizemos que e proxy.
            # Trocar isto por um detector treinado e o assunto da Etapa 4.
            d.confianca = float(min(1.0, area / (cv2.contourArea(cv2.convexHull(c)) + 1e-6)))
            d.x = int(m['m10'] / m['m00'])
            d.y = int(m['m01'] / m['m00'])
            d.area = int(area)
            achados.append(d)
        return achados

    def processar(self, img):
        achados = self.detectar(img)
        msg = Deteccoes()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()   # carimbo do MUNDO: relogio de parede
        msg.header.frame_id = 'camera'
        msg.deteccoes = achados
        msg.total = len(achados)
        self.ultimo = msg
        self.pub.publish(msg)

    # ------------------------------------------------------------ servico
    def responder_status(self, req, resp):
        d = self.ultimo.deteccoes
        resp.ativo = True
        resp.classe_alvo = self.classe
        resp.total_detectado = len(d)
        resp.confianca_media = float(sum(x.confianca for x in d) / len(d)) if d else 0.0
        resp.mensagem = ("vendo %d '%s' na cena" % (len(d), self.classe)) if d \
            else ("nenhum '%s' na cena" % self.classe)
        return resp


def main():
    rclpy.init()
    no = Detector()
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
