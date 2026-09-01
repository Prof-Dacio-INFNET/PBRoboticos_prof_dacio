"""DEMO 1 -- as setas que um dia serao motores.

Acha o maior objeto VERMELHO da cena e desenha, sobre a propria imagem da
webcam, a seta do movimento que a camera precisaria fazer para centralizar e
depois se aproximar do alvo.

A seta e um substituto honesto de um comando de motor. O no publica
pb_interfaces/msg/ComandoMovimento em /demo/comando; hoje quem "assina" esse
comando e um desenho, amanha e um driver de tracao. Nenhuma linha da percepcao
muda -- e essa separacao e a razao de o ROS 2 existir.

    ros2 run demo_visual guia_visual
    ros2 run demo_visual guia_visual --ros-args -p janela:=false -p dispositivo:=1
"""
import cv2
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header

from pb_interfaces.msg import ComandoMovimento, Deteccao, Deteccoes

from .piloto import processar


class GuiaVisual(Node):
    def __init__(self):
        super().__init__('guia_visual')
        self.declare_parameter('dispositivo', 0)
        self.declare_parameter('largura', 640)
        self.declare_parameter('altura', 480)
        self.declare_parameter('fps', 20.0)
        self.declare_parameter('janela', True)      # cv2.imshow; false = so por topico
        self.declare_parameter('espelhar', True)    # webcam frontal: espelho e mais intuitivo
        self.declare_parameter('area_min', 800)
        self.declare_parameter('tolerancia', 0.15)  # zona morta
        self.declare_parameter('area_alvo', 0.06)   # fracao da tela = "distancia certa"

        self.janela = bool(self.get_parameter('janela').value)
        self.pub_cmd = self.create_publisher(ComandoMovimento, '/demo/comando', 10)
        self.pub_det = self.create_publisher(Deteccoes, '/vision/deteccoes', 10)
        self.pub_img = self.create_publisher(Image, '/demo/imagem_anotada', 10)

        self.cap = cv2.VideoCapture(int(self.get_parameter('dispositivo').value), cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.get_logger().error(
                "nao consegui abrir a camera. No WSL2: refaca o 'usbipd attach', e confira "
                "'ls -l /dev/video*' e 'groups | grep video'")
            raise SystemExit(1)
        # MJPG ANTES do tamanho: invertido, o driver renegocia e volta para YUYV
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.get_parameter('largura').value))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.get_parameter('altura').value))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        fps = float(self.get_parameter('fps').value)
        try:                                     # relogio monotonico: o de parede salta no WSL2
            self.create_timer(1.0 / fps, self.tick,
                              clock=Clock(clock_type=ClockType.STEADY_TIME))
        except TypeError:
            self.create_timer(1.0 / fps, self.tick)

        self.get_logger().info('guia visual no ar - /demo/comando e /demo/imagem_anotada · janela=%s'
                               % self.janela)

    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn('sem quadro da camera', throttle_duration_sec=5.0)
            return
        if bool(self.get_parameter('espelhar').value):
            frame = cv2.flip(frame, 1)

        p = self.get_parameter
        frame, acao, motivo, ex, ey, ea, area, centro = processar(
            frame,
            area_min=float(p('area_min').value),
            tol=float(p('tolerancia').value),
            area_alvo=float(p('area_alvo').value))

        det = Deteccoes()
        det.header = Header()
        det.header.stamp = self.get_clock().now().to_msg()
        det.header.frame_id = 'camera'
        if centro is not None:
            d = Deteccao()
            d.classe, d.confianca = 'alvo_vermelho', 1.0
            d.x, d.y, d.area = int(centro[0]), int(centro[1]), int(area)
            det.deteccoes = [d]
        det.total = len(det.deteccoes)
        self.pub_det.publish(det)

        cmd = ComandoMovimento()
        cmd.acao, cmd.motivo = acao, motivo
        cmd.erro_x, cmd.erro_y, cmd.erro_area = float(ex), float(ey), float(ea)
        self.pub_cmd.publish(cmd)

        self.publicar_imagem(frame)

        if self.janela:
            try:
                cv2.imshow('DEMO 1 - a seta que um dia sera um motor', frame)
                cv2.waitKey(1)
            except cv2.error:
                self.janela = False              # degradar, nao quebrar
                self.get_logger().warn(
                    'sem janela grafica aqui. Seguindo so por topico: '
                    'ros2 run rqt_image_view rqt_image_view  (escolha /demo/imagem_anotada)')

    def publicar_imagem(self, bgr):
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'
        msg.height, msg.width = bgr.shape[0], bgr.shape[1]
        msg.encoding, msg.is_bigendian, msg.step = 'bgr8', 0, bgr.shape[1] * 3
        msg.data = bgr.tobytes()
        self.pub_img.publish(msg)


def main():
    rclpy.init()
    no = GuiaVisual()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.cap.release()
        cv2.destroyAllWindows()
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
