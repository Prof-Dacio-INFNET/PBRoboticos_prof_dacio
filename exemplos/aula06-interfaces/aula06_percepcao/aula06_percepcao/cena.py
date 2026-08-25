"""Cena sintetica -- a mesma da Aula 3, isolada aqui para o exemplo rodar sozinho.

Manter o gerador separado do no tem um motivo: e assim que voce testa a
percepcao sem camera, sem ROS e sem aula. Um modulo puro, sem rclpy dentro,
pode ser importado por um teste.
"""
import math

import cv2
import numpy as np


def frame(k, largura=640, altura=480):
    """Devolve o quadro numero k: 2 objetos vermelhos e 1 distrator azul."""
    h, w = altura, largura
    img = np.full((h, w, 3), 40, dtype=np.uint8)
    cv2.rectangle(img, (0, int(h * 0.78)), (w, h), (70, 70, 70), -1)
    t = k / 15.0
    cv2.circle(img, (int(w * 0.5 + w * 0.30 * math.cos(t)),
                     int(h * 0.45 + h * 0.20 * math.sin(t))), 34, (32, 32, 220), -1)
    cv2.circle(img, (int(w * 0.5 + w * 0.22 * math.cos(-1.7 * t + 2.0)),
                     int(h * 0.55 + h * 0.16 * math.sin(-1.7 * t + 2.0))), 22, (28, 40, 200), -1)
    cv2.circle(img, (int(w * 0.5 + w * 0.34 * math.cos(0.8 * t + 1.0)),
                     int(h * 0.5 + h * 0.28 * math.sin(0.8 * t + 1.0))), 26, (210, 120, 30), -1)
    return img


def msg_para_frame(msg):
    """sensor_msgs/Image (bgr8) -> numpy, sem cv_bridge.

    Sao tres linhas. O cv_bridge faz muito mais do que isso -- e por isso ele
    tem mais superficie para quebrar (ver o KeyError: 16 da Aula 3). Quando a
    unica coisa de que voce precisa e bgr8, esta funcao nao tem como falhar
    por causa de versao de NumPy ou de OpenCV.
    """
    if msg.encoding != 'bgr8':
        raise ValueError("esperava encoding bgr8, veio '%s'" % msg.encoding)
    return np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
