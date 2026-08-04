"""Ponte imagem OpenCV <-> sensor_msgs/Image.

ONDE EDITAR: aqui, em `src/`. Este é o código-fonte do pacote. As cópias que
aparecem em `build/` e `install/` são geradas pelo `colcon build` — mexer nelas
é trabalho perdido, some no próximo build.

Usa cv_bridge quando ele **realmente funciona** (o caminho canônico do
ecossistema ROS 2). Quando não funciona, cai automaticamente numa conversão
manual equivalente para o encoding 'bgr8' — assim a aula não trava por causa de
um pacote quebrado no ambiente de alguém.

Por que "realmente funciona" e não "está instalado"
---------------------------------------------------
Existe um modo de falha comum e traiçoeiro em que o `import cv_bridge`
**passa** e a conversão quebra depois. É o conflito de ABI do NumPy 2:

    A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6
    AttributeError: _ARRAY_API not found
    ...
    KeyError: 16                      # 16 = CV_8UC3, que é exatamente 'bgr8'

O `ros-humble-cv-bridge` do apt traz uma extensão em C++ compilada contra
NumPy 1.x. Sob NumPy 2 ela falha ao carregar, mas o `import` **não** levanta
ImportError: a mensagem é impressa, o módulo Python é importado assim mesmo e a
tabela interna de tipos do cv_bridge fica vazia. O erro só aparece na primeira
conversão, como `KeyError: 16`. Por isso o teste abaixo é um round-trip de
verdade, e o `except` é largo de propósito.

Cura definitiva no seu ambiente (dentro do venv do projeto, nunca com sudo):

    source ~/projeto-pb/.venv/bin/activate
    uv pip install "numpy<2"                    # alinha com o cv_bridge do apt
    sudo apt install ros-humble-cv-bridge python3-opencv

Enquanto isso não acontece, este módulo mantém o exemplo rodando.
"""
import numpy as np
from sensor_msgs.msg import Image


# --------------------------------------------------------------------------
# Plano B: conversão manual. Vale só para 'bgr8', que é o encoding do exemplo.
# 'bgr8' = 3 bytes por pixel na ordem azul-verde-vermelho, `step` = largura*3,
# e o corpo da mensagem é o array contíguo em bytes. Não há mais nada.
# --------------------------------------------------------------------------
def _para_msg_manual(frame, stamp=None, frame_id='camera'):
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
            f"a conversao manual so entende 'bgr8', chegou '{msg.encoding}'. "
            'Conserte o cv_bridge para trabalhar com outros encodings.')
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


# --------------------------------------------------------------------------
# Escolha do caminho, feita uma vez, no import do modulo.
# --------------------------------------------------------------------------
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
    MOTIVO_PLANO_B = f'{type(erro).__name__}: {erro}'
    para_msg = _para_msg_manual
    para_cv = _para_cv_manual


def descrever_ponte():
    """Uma linha para o log do no, dizendo qual caminho esta em uso e por que."""
    if USANDO_CV_BRIDGE:
        return 'cv_bridge=sim (round-trip conferido no import)'
    return f'cv_bridge=nao, conversao manual bgr8 | motivo: {MOTIVO_PLANO_B}'
