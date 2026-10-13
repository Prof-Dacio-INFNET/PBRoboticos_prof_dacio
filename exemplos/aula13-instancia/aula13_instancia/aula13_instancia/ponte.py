"""Ponte imagem OpenCV <-> sensor_msgs/Image.

MESMA abordagem do `aula03_visao/ponte.py`, de proposito: usa cv_bridge quando
ele REALMENTE funciona (round-trip conferido no import, nao so `import` que
passou) e cai numa conversao manual de 'bgr8' quando nao funciona -- assim a
aula nao trava por causa de um pacote quebrado no ambiente de alguem.

O diagnostico completo dos dois modos de falha classicos (a ABI do NumPy 2 e a
renumeracao de constantes do OpenCV 5, que aparecem os dois como `KeyError: 16`
na primeira conversao) esta no ponte.py da Aula 3, e vale a leitura. Aqui fica
so a mecanica.

ONDE EDITAR: aqui, em `src/`. O que aparece em `build/` e `install/` e copia do
`colcon build` e some no proximo build.
"""
import numpy as np
from sensor_msgs.msg import Image


def _para_msg_manual(frame, stamp=None, frame_id='camera'):
    """'bgr8' = 3 bytes por pixel, step = largura*3, corpo contiguo. So isso."""
    altura, largura = frame.shape[:2]
    msg = Image()
    if stamp is not None:
        msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.height, msg.width = altura, largura
    msg.encoding = 'bgr8'
    msg.is_bigendian = 0
    msg.step = largura * 3
    msg.data = np.ascontiguousarray(frame).tobytes()
    return msg


def _para_cv_manual(msg):
    if msg.encoding not in ('bgr8', '8UC3'):
        raise ValueError(
            "a conversao manual so entende 'bgr8', chegou '%s'. "
            'Conserte o cv_bridge para trabalhar com outros encodings.' % msg.encoding)
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    return buf.reshape(msg.height, msg.width, 3)


def _testar_cv_bridge(bridge):
    """Round-trip minusculo. Levanta excecao se a ponte estiver quebrada."""
    original = np.zeros((2, 2, 3), dtype=np.uint8)
    original[0, 0] = (10, 20, 30)
    original[1, 1] = (200, 100, 50)
    volta = bridge.imgmsg_to_cv2(
        bridge.cv2_to_imgmsg(original, encoding='bgr8'), desired_encoding='bgr8')
    if volta.shape != original.shape or not np.array_equal(volta, original):
        raise RuntimeError('round-trip do cv_bridge devolveu imagem diferente da original')


MOTIVO_PLANO_B = ''

try:
    from cv_bridge import CvBridge

    _bridge = CvBridge()
    _testar_cv_bridge(_bridge)          # <- e isto que pega o KeyError: 16
    USANDO_CV_BRIDGE = True

    def para_msg(frame, stamp=None, frame_id='camera'):
        msg = _bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        if stamp is not None:
            msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        return msg

    def para_cv(msg):
        return _bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

except Exception as erro:   # ImportError, KeyError, AttributeError, RuntimeError...
    USANDO_CV_BRIDGE = False
    MOTIVO_PLANO_B = '%s: %s' % (type(erro).__name__, erro)
    para_msg = _para_msg_manual
    para_cv = _para_cv_manual


def descrever_ponte():
    """Uma linha para o log do no, dizendo qual caminho esta em uso e por que."""
    if USANDO_CV_BRIDGE:
        return 'cv_bridge=sim (round-trip conferido no import)'
    return 'cv_bridge=nao, conversao manual bgr8 | motivo: %s' % MOTIVO_PLANO_B
