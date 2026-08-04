"""Publica imagens em /camera/image_raw — a boca do pipeline de visão do TP1.

Três fontes, escolhidas pelo parâmetro `fonte`:
  * sintetico (padrão) — gera um cenário com objetos coloridos em movimento.
    NÃO precisa de webcam: todo mundo consegue rodar hoje, inclusive no WSL2.
  * webcam            — cv2.VideoCapture(dispositivo). No WSL2 exige usbipd
                        (ver tutoriais/camera-wsl2-usbipd.md).
  * video             — arquivo de vídeo em loop (parâmetro `arquivo`).

Exemplos:
    ros2 run aula03_visao publicador_camera
    ros2 run aula03_visao publicador_camera --ros-args -p fonte:=webcam -p dispositivo:=0
    ros2 run aula03_visao publicador_camera --ros-args -p fonte:=video -p arquivo:=/home/eu/clip.mp4
"""
import math

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image

from .ponte import para_msg, descrever_ponte

# QoS típico de sensor: entrega rápida, sem retransmitir frame velho.
QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class PublicadorCamera(Node):
    def __init__(self):
        super().__init__('publicador_camera')
        self.declare_parameter('fonte', 'sintetico')      # sintetico | webcam | video
        self.declare_parameter('dispositivo', 0)          # índice da webcam
        self.declare_parameter('arquivo', '')             # caminho do vídeo
        self.declare_parameter('fps', 15.0)
        self.declare_parameter('largura', 640)
        self.declare_parameter('altura', 480)

        self.fonte = self.get_parameter('fonte').value
        self.largura = int(self.get_parameter('largura').value)
        self.altura = int(self.get_parameter('altura').value)
        fps = float(self.get_parameter('fps').value)

        self.pub = self.create_publisher(Image, '/camera/image_raw', QOS_SENSOR)
        self.cap = None
        self.k = 0

        if self.fonte in ('webcam', 'video'):
            alvo = (int(self.get_parameter('dispositivo').value)
                    if self.fonte == 'webcam'
                    else self.get_parameter('arquivo').value)
            self.cap = cv2.VideoCapture(alvo)
            if not self.cap.isOpened():
                self.get_logger().error(
                    f"Nao consegui abrir a fonte '{alvo}'. Caindo para 'sintetico'. "
                    "Webcam no WSL2? veja tutoriais/camera-wsl2-usbipd.md")
                self.cap = None
                self.fonte = 'sintetico'

        self.create_timer(1.0 / max(fps, 1.0), self.tick)
        self.get_logger().info(
            f'Publicando /camera/image_raw · fonte={self.fonte} · {self.largura}x{self.altura} '
            f'@{fps:.0f}fps · {descrever_ponte()}')

    # ---------------------------------------------------------------- fontes
    def frame_sintetico(self):
        """Cena com fundo neutro + 3 objetos coloridos (2 vermelhos, 1 azul)."""
        h, w = self.altura, self.largura
        frame = np.full((h, w, 3), 40, dtype=np.uint8)
        cv2.rectangle(frame, (0, int(h * 0.78)), (w, h), (70, 70, 70), -1)  # "chao"
        t = self.k / 15.0
        # dois objetos VERMELHOS (BGR) em orbitas diferentes
        cv2.circle(frame, (int(w * 0.5 + w * 0.30 * math.cos(t)),
                           int(h * 0.45 + h * 0.20 * math.sin(t))), 34, (32, 32, 220), -1)
        cv2.circle(frame, (int(w * 0.5 + w * 0.22 * math.cos(-1.7 * t + 2.0)),
                           int(h * 0.55 + h * 0.16 * math.sin(-1.7 * t + 2.0))), 22, (28, 40, 200), -1)
        # um distrator AZUL: prova que a segmentacao por cor esta funcionando
        cv2.circle(frame, (int(w * 0.5 + w * 0.34 * math.cos(0.8 * t + 1.0)),
                           int(h * 0.5 + h * 0.28 * math.sin(0.8 * t + 1.0))), 26, (210, 120, 30), -1)
        cv2.putText(frame, f'sintetico  frame {self.k}', (12, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1, cv2.LINE_AA)
        return frame

    def frame_capturado(self):
        ok, frame = self.cap.read()
        if not ok:  # fim do arquivo -> recomeca
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        if not ok:
            return None
        return cv2.resize(frame, (self.largura, self.altura))

    # ------------------------------------------------------------------ loop
    def tick(self):
        frame = self.frame_sintetico() if self.cap is None else self.frame_capturado()
        if frame is None:
            self.get_logger().warn('Sem frame nesta iteracao.')
            return
        self.pub.publish(para_msg(frame, stamp=self.get_clock().now().to_msg()))
        self.k += 1


def main():
    rclpy.init()
    no = PublicadorCamera()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        if no.cap is not None:
            no.cap.release()
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
