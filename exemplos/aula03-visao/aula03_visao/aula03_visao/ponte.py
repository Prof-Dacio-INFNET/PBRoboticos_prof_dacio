"""Ponte imagem OpenCV <-> sensor_msgs/Image.

Usa cv_bridge quando disponível (o padrão do ecossistema ROS 2). Se o pacote
`ros-humble-cv-bridge` não estiver instalado, cai automaticamente em uma
conversão manual equivalente para o encoding 'bgr8' — assim a aula não trava
por causa de um apt faltando. No TP1 você deve instalar o cv_bridge de verdade:

    sudo apt install ros-humble-cv-bridge python3-opencv
"""
import numpy as np
from sensor_msgs.msg import Image

try:  # caminho normal
    from cv_bridge import CvBridge

    _bridge = CvBridge()
    USANDO_CV_BRIDGE = True

    def para_msg(frame, stamp=None, frame_id='camera'):
        msg = _bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        if stamp is not None:
            msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        return msg

    def para_cv(msg):
        return _bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

except ImportError:  # plano B: conversão manual (só bgr8)
    USANDO_CV_BRIDGE = False

    def para_msg(frame, stamp=None, frame_id='camera'):
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

    def para_cv(msg):
        buf = np.frombuffer(msg.data, dtype=np.uint8)
        return buf.reshape(msg.height, msg.width, 3)
