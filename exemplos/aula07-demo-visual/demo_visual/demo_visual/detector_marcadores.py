"""DEMO 2 -- a folha levantada que dispara um servico.

Cada aluno recebe uma folha com uma forma. Quando a forma aparece na camera,
este no CHAMA UM SERVICO -- um por forma. E a mesma ideia do Demo 1 num outro
regime: la o comando era continuo (uma seta a cada quadro), aqui ele e
pontual (um evento, uma vez).

Essa diferenca nao e detalhe de implementacao, e a resposta para "quando uso
topico e quando uso servico":

  * seta a cada quadro  -> fluxo continuo, ninguem espera resposta  -> TOPICO
  * folha levantada     -> evento pontual, com confirmacao          -> SERVICO
  * "va ate a bancada"  -> demora, informa progresso, cancelavel    -> ACTION

    ros2 run demo_visual detector_marcadores
"""
import cv2
import numpy as np
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from .formas import SERVICO_DE, classificar

V_MAX = 120          # marcador e PRETO: valor baixo. Ver a nota sobre saturacao abaixo.
AMARELO, VERDE, BRANCO = (0, 200, 255), (60, 220, 60), (245, 245, 245)


class DetectorMarcadores(Node):
    def __init__(self):
        super().__init__('detector_marcadores')
        self.declare_parameter('dispositivo', 0)
        self.declare_parameter('fps', 12.0)
        self.declare_parameter('janela', True)
        self.declare_parameter('espelhar', True)
        self.declare_parameter('area_min_frac', 0.03)   # fracao da tela
        self.declare_parameter('confirmacoes', 3)       # quadros seguidos antes de disparar
        self.declare_parameter('descanso_s', 3.0)       # nao redispara o mesmo antes disto

        self.clientes = {nome: self.create_client(Trigger, srv)
                         for nome, srv in SERVICO_DE.items()}
        self.pub_img = self.create_publisher(Image, '/demo/marcadores_anotado', 10)

        self.visto_seguido = {}      # nome -> quantos quadros seguidos
        self.ultimo_disparo = {}     # nome -> instante monotonico

        self.cap = cv2.VideoCapture(int(self.get_parameter('dispositivo').value), cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.get_logger().error("camera nao abriu - no WSL2, refaca o 'usbipd attach'")
            raise SystemExit(1)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.janela = bool(self.get_parameter('janela').value)
        fps = float(self.get_parameter('fps').value)
        try:
            self.create_timer(1.0 / fps, self.tick,
                              clock=Clock(clock_type=ClockType.STEADY_TIME))
        except TypeError:
            self.create_timer(1.0 / fps, self.tick)

        self.get_logger().info('detector de marcadores no ar - %s'
                               % ', '.join('%s->%s' % (n, s) for n, s in SERVICO_DE.items()))

    # ------------------------------------------------------------- deteccao
    def encontrar(self, bgr):
        cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, binaria = cv2.threshold(cinza, 0, 255,
                                   cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        h, w = cinza.shape
        area_min = float(self.get_parameter('area_min_frac').value) * h * w
        achados = []
        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contornos:
            if cv2.contourArea(c) < area_min:
                continue
            # O marcador e PRETO. Usamos o VALOR (V), nao a saturacao.
            # Armadilha do HSV: quando V e proximo de zero, S vira ruido puro --
            # um preto com um pingo de ruido pode marcar S=200. Saturacao so
            # significa alguma coisa quando ha luz. E por isso que a folha
            # vermelha do Demo 1 nao dispara servico nenhum aqui.
            mascara = np.zeros((h, w), np.uint8)
            cv2.drawContours(mascara, [c], -1, 255, -1)
            if cv2.mean(hsv[:, :, 2], mask=mascara)[0] > V_MAX:
                continue
            nome = classificar(c, cv2)
            if nome:
                achados.append((nome, c))
        return achados

    # ------------------------------------------------------------- disparo
    def talvez_disparar(self, nome, agora):
        """Histerese: N quadros seguidos, e um descanso depois de disparar.

        Sem isto o servico e chamado dezenas de vezes por segundo enquanto a
        folha estiver levantada, e a demonstracao vira ruido. Debounce nao e
        firula: e o que separa 'detectou' de 'decidiu'.
        """
        precisa = int(self.get_parameter('confirmacoes').value)
        descanso = float(self.get_parameter('descanso_s').value)
        if self.visto_seguido.get(nome, 0) < precisa:
            return False
        if agora - self.ultimo_disparo.get(nome, -1e9) < descanso:
            return False
        self.ultimo_disparo[nome] = agora

        cli = self.clientes[nome]
        if not cli.service_is_ready():
            self.get_logger().warn("servico %s nao esta no ar (o painel_robo esta rodando?)"
                                   % SERVICO_DE[nome])
            return False
        self.get_logger().info('>>> %s detectado - chamando %s' % (nome.upper(), SERVICO_DE[nome]))
        cli.call_async(Trigger.Request())
        return True

    # ------------------------------------------------------------- laco
    def tick(self):
        import time
        ok, frame = self.cap.read()
        if not ok:
            return
        if bool(self.get_parameter('espelhar').value):
            frame = cv2.flip(frame, 1)

        achados = self.encontrar(frame)
        presentes = {n for n, _ in achados}
        for nome in SERVICO_DE:
            self.visto_seguido[nome] = self.visto_seguido.get(nome, 0) + 1 if nome in presentes else 0

        agora = time.monotonic()
        disparados = {n for n in presentes if self.talvez_disparar(n, agora)}

        for nome, c in achados:
            cor = VERDE if nome in disparados else AMARELO
            cv2.drawContours(frame, [c], -1, cor, 4)
            x, y, w_, h_ = cv2.boundingRect(c)
            rot = '%s -> %s' % (nome.upper(), SERVICO_DE[nome])
            cv2.putText(frame, rot, (x, max(24, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 6, cv2.LINE_AA)
            cv2.putText(frame, rot, (x, max(24, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, cor, 2, cv2.LINE_AA)

        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 40), (25, 25, 25), -1)
        txt = ('DETECTADO: ' + ', '.join(sorted(presentes))) if presentes \
              else 'levante uma folha para a camera'
        cv2.putText(frame, txt, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    VERDE if presentes else BRANCO, 2, cv2.LINE_AA)

        self.publicar(frame)
        if self.janela:
            try:
                cv2.imshow('DEMO 2 - a folha que chama um servico', frame)
                cv2.waitKey(1)
            except cv2.error:
                self.janela = False
                self.get_logger().warn('sem janela grafica; use rqt_image_view '
                                       'em /demo/marcadores_anotado')

    def publicar(self, bgr):
        m = Image()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'camera'
        m.height, m.width = bgr.shape[0], bgr.shape[1]
        m.encoding, m.is_bigendian, m.step = 'bgr8', 0, bgr.shape[1] * 3
        m.data = bgr.tobytes()
        self.pub_img.publish(m)


def main():
    rclpy.init()
    no = DetectorMarcadores()
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
