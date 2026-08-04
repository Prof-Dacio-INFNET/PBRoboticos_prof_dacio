"""Assina /camera/image_raw, segmenta por cor (HSV) e conta objetos.

É o miolo do TP1: um nó que ao mesmo tempo **assina** um tópico, **publica**
resultados e **atende um serviço**.

  entrada   /camera/image_raw       (sensor_msgs/Image)
  saidas    /vision/segmented       (sensor_msgs/Image — máscara colorida sobre o frame)
            /vision/contagem        (std_msgs/Int32 — nº de objetos no último frame)
  serviço   /vision/status          (std_srvs/Trigger — responde o último estado)

Faixa HSV vem de parâmetros (config/segmentacao.yaml) — plantando o hábito de
parametrizar que o TP2 vai cobrar:

    ros2 run aula03_visao segmentador_hsv --ros-args --params-file config/segmentacao.yaml
    ros2 param set /segmentador_hsv area_min 300.0
"""
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

from .ponte import para_msg, para_cv

QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class SegmentadorHSV(Node):
    def __init__(self):
        super().__init__('segmentador_hsv')
        # Vermelho dá volta no círculo de matiz -> duas faixas (0-10 e 170-180).
        self.declare_parameter('h_min', 0)
        self.declare_parameter('h_max', 10)
        self.declare_parameter('h_min2', 170)
        self.declare_parameter('h_max2', 180)
        self.declare_parameter('s_min', 120)
        self.declare_parameter('v_min', 70)
        self.declare_parameter('area_min', 400.0)
        self.declare_parameter('desenhar_contornos', True)

        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.on_frame, QOS_SENSOR)
        self.pub_img = self.create_publisher(Image, '/vision/segmented', QOS_SENSOR)
        self.pub_cont = self.create_publisher(Int32, '/vision/contagem', 10)
        self.srv = self.create_service(Trigger, '/vision/status', self.on_status)

        self.ultima_contagem = 0
        self.frames = 0
        self.get_logger().info(
            'Segmentador no ar: /camera/image_raw -> /vision/segmented + /vision/contagem '
            '· serviço /vision/status')

    # --------------------------------------------------------------- visão
    def mascara(self, hsv):
        p = {n: self.get_parameter(n).value for n in
             ('h_min', 'h_max', 'h_min2', 'h_max2', 's_min', 'v_min')}
        m1 = cv2.inRange(hsv, np.array([p['h_min'], p['s_min'], p['v_min']]),
                         np.array([p['h_max'], 255, 255]))
        m2 = cv2.inRange(hsv, np.array([p['h_min2'], p['s_min'], p['v_min']]),
                         np.array([p['h_max2'], 255, 255]))
        m = cv2.bitwise_or(m1, m2)
        # morfologia: fecha buracos e remove sal-e-pimenta
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, nucleo)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, nucleo)
        return m

    def on_frame(self, msg):
        frame = para_cv(msg)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mascara = self.mascara(hsv)

        area_min = float(self.get_parameter('area_min').value)
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        objetos = [c for c in contornos if cv2.contourArea(c) >= area_min]

        saida = frame.copy()
        # máscara em verde translúcido (o mesmo recurso volta no TP3, com YOLO)
        verde = np.zeros_like(frame)
        verde[:, :, 1] = mascara
        saida = cv2.addWeighted(saida, 1.0, verde, 0.5, 0)
        if self.get_parameter('desenhar_contornos').value:
            for c in objetos:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(saida, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(saida, f'objetos: {len(objetos)}', (12, saida.shape[0] - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

        self.ultima_contagem = len(objetos)
        self.frames += 1
        self.pub_img.publish(para_msg(saida, stamp=msg.header.stamp, frame_id='camera'))
        self.pub_cont.publish(Int32(data=self.ultima_contagem))

    # ------------------------------------------------------------- serviço
    def on_status(self, req, resp):
        resp.success = self.frames > 0
        resp.message = (f'{self.ultima_contagem} objeto(s) no ultimo frame '
                        f'({self.frames} frames processados)')
        self.get_logger().info(f'/vision/status -> {resp.message}')
        return resp


def main():
    rclpy.init()
    no = SegmentadorHSV()
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
