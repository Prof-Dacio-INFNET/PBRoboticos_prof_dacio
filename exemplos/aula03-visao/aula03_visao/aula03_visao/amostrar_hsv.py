"""Amostrador de HSV — clique no objeto e descubra os limiares dele.

Existe porque "chutar o h_min" é a forma mais cara de perder uma tarde. Você
clica no seu objeto em alguns pontos, o nó lê a cor mediana da vizinhança de
cada clique e, no fim, imprime um bloco de YAML pronto para colar no
`config/segmentacao.yaml`.

Dois modos:

    # 1) ao vivo, com o pipeline rodando (assina /camera/image_raw)
    ros2 launch aula03_visao visao.launch.py
    ros2 run aula03_visao amostrar_hsv

    # 2) sobre uma foto, sem precisar de câmera nem do pipeline no ar
    ros2 run aula03_visao amostrar_hsv --ros-args -p imagem:=/home/eu/objeto.jpg

Na janela: clique com o botão esquerdo sobre o objeto (várias vezes, em partes
claras E escuras dele), `r` limpa as amostras, `q` fecha e imprime o YAML.

Por que a MEDIANA da vizinhança e não o pixel do clique: um pixel isolado pega
ruído do sensor e compressão JPEG; a mediana de um quadrado 9x9 é estável e não
se desloca por causa de um pixel espúrio, como a média se deslocaria.
"""
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image

from .ponte import para_cv

QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

JANELA = 'amostrar_hsv  ·  clique no objeto  ·  r=limpar  q=sair'


def sugerir_faixas(amostras, margem_h=8, folga_s=30, folga_v=40):
    """Transforma uma lista de (h, s, v) nos parâmetros do segmentador.

    Função pura de propósito: é a única parte com regra de negócio, e assim dá
    para testá-la sem ROS, sem janela e sem câmera (ver teste_offline.py).

    O vermelho é o caso chato: ele mora nas DUAS pontas do círculo de matiz
    (perto de 0 e perto de 179), então a nuvem de amostras aparece partida em
    dois grupos distantes. Detectamos isso pelo buraco no meio: se existe um
    vão maior que a largura útil da faixa, não é uma faixa larga — são duas
    estreitas, e devolvemos h_min/h_max + h_min2/h_max2.
    """
    if not amostras:
        return None
    hs = sorted(int(a[0]) for a in amostras)
    ss = [int(a[1]) for a in amostras]
    vs = [int(a[2]) for a in amostras]

    # Maior vão entre matizes consecutivos, considerando a volta 179 -> 0.
    vaos = [(hs[i + 1] - hs[i], i) for i in range(len(hs) - 1)]
    vaos.append((hs[0] + 180 - hs[-1], len(hs) - 1))
    maior_vao, corte = max(vaos)

    duas_faixas = maior_vao > 40 and len(hs) > 1 and corte != len(hs) - 1
    if duas_faixas:
        baixo, alto = hs[:corte + 1], hs[corte + 1:]
        faixas = [(min(baixo), max(baixo)), (min(alto), max(alto))]
    else:
        faixas = [(hs[0], hs[-1])]

    def limita(v, teto):
        return int(max(0, min(teto, v)))

    p = {
        's_min': limita(min(ss) - folga_s, 255),
        'v_min': limita(min(vs) - folga_v, 255),
    }
    (a, b) = faixas[0]
    p['h_min'] = limita(a - margem_h, 179)
    p['h_max'] = limita(b + margem_h, 179)
    if len(faixas) == 2:
        (c, d) = faixas[1]
        p['h_min2'] = limita(c - margem_h, 179)
        p['h_max2'] = limita(d + margem_h, 179)
    else:
        # Sem volta no círculo: a segunda faixa repete a primeira, que é o
        # jeito de neutralizá-la sem mexer no código do segmentador.
        p['h_min2'], p['h_max2'] = p['h_min'], p['h_max']
    p['_duas_faixas'] = len(faixas) == 2
    return p


def yaml_sugerido(p, area_min=400.0):
    if p is None:
        return '# nenhuma amostra coletada — clique no objeto antes de sair.'
    nota = ('# duas faixas de matiz: a cor dá a volta no círculo (típico do vermelho).'
            if p['_duas_faixas'] else
            '# uma faixa de matiz só; h_min2/h_max2 repetem a primeira (inofensivo).')
    return '\n'.join([
        '# ---- cole em config/segmentacao.yaml ----',
        nota,
        'segmentador_hsv:',
        '  ros__parameters:',
        f"    h_min: {p['h_min']}",
        f"    h_max: {p['h_max']}",
        f"    h_min2: {p['h_min2']}",
        f"    h_max2: {p['h_max2']}",
        f"    s_min: {p['s_min']}",
        f"    v_min: {p['v_min']}",
        f'    area_min: {area_min}',
        '    desenhar_contornos: true',
        '# Confira rodando o pipeline: se a máscara ficar toda branca, aperte s_min/v_min;',
        '# se ficar toda preta, afrouxe-os. Ajuste medido é ponto de partida, não verdade.',
    ])


class AmostradorHSV(Node):
    def __init__(self):
        super().__init__('amostrar_hsv')
        self.declare_parameter('imagem', '')      # foto em vez do tópico
        self.declare_parameter('raio', 4)         # vizinhança do clique: (2r+1)²
        self.declare_parameter('area_min', 400.0)  # só para compor o YAML final

        self.raio = int(self.get_parameter('raio').value)
        caminho = str(self.get_parameter('imagem').value)
        self.amostras = []
        self.frame = None
        self.sem_janela = False

        if caminho:
            self.frame = cv2.imread(caminho)
            if self.frame is None:
                self.get_logger().error(
                    f"Nao consegui abrir a imagem '{caminho}'. Caminho certo? "
                    'Dentro do WSL o disco do Windows fica em /mnt/c/...')
                raise SystemExit(1)
            self.get_logger().info(f'Modo foto: {caminho} ({self.frame.shape[1]}x{self.frame.shape[0]})')
        else:
            self.create_subscription(Image, '/camera/image_raw', self.on_frame, QOS_SENSOR)
            self.get_logger().info(
                'Modo ao vivo: assinando /camera/image_raw. Se a janela ficar vazia, '
                'o publicador nao esta no ar (ros2 launch aula03_visao visao.launch.py).')

        cv2.namedWindow(JANELA, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(JANELA, self.on_click)
        self.create_timer(1 / 20, self.tick)

    def on_frame(self, msg):
        self.frame = para_cv(msg)

    # ------------------------------------------------------------- amostragem
    def on_click(self, evento, x, y, _flags, _param):
        if evento != cv2.EVENT_LBUTTONDOWN or self.frame is None:
            return
        h, w = self.frame.shape[:2]
        r = self.raio
        y0, y1 = max(0, y - r), min(h, y + r + 1)
        x0, x1 = max(0, x - r), min(w, x + r + 1)
        bloco = cv2.cvtColor(self.frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
        hsv = np.median(bloco.reshape(-1, 3), axis=0)
        self.amostras.append(tuple(int(v) for v in hsv))
        self.get_logger().info(
            f'amostra {len(self.amostras):2d} em ({x},{y}): '
            f'H={self.amostras[-1][0]:3d}  S={self.amostras[-1][1]:3d}  V={self.amostras[-1][2]:3d}')

    # ------------------------------------------------------------------- loop
    def desenhar(self):
        vista = self.frame.copy()
        p = sugerir_faixas(self.amostras)
        linhas = [f'amostras: {len(self.amostras)}']
        if p:
            faixa2 = f"  +  {p['h_min2']}-{p['h_max2']}" if p['_duas_faixas'] else ''
            linhas.append(f"H {p['h_min']}-{p['h_max']}{faixa2}")
            linhas.append(f"S >= {p['s_min']}   V >= {p['v_min']}")
            # Pré-visualização: o que ESTES limiares pegariam agora.
            hsv = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
            m = cv2.bitwise_or(
                cv2.inRange(hsv, np.array([p['h_min'], p['s_min'], p['v_min']]),
                            np.array([p['h_max'], 255, 255])),
                cv2.inRange(hsv, np.array([p['h_min2'], p['s_min'], p['v_min']]),
                            np.array([p['h_max2'], 255, 255])))
            verde = np.zeros_like(vista)
            verde[:, :, 1] = m
            vista = cv2.addWeighted(vista, 1.0, verde, 0.45, 0)
        for i, texto in enumerate(linhas):
            cv2.putText(vista, texto, (12, 26 + 24 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
        return vista

    def tick(self):
        if self.frame is None or self.sem_janela:
            return
        try:
            cv2.imshow(JANELA, self.desenhar())
            tecla = cv2.waitKey(1) & 0xFF
        except cv2.error as e:
            # Sem servidor gráfico não dá para clicar em nada: avisa uma vez,
            # explica a correção e para de tentar, em vez de inundar o log.
            self.sem_janela = True
            self.get_logger().error(
                f'Nao consegui abrir a janela ({e.__class__.__name__}). No WSL2 isso e o WSLg: '
                'rode `wsl --update` no PowerShell e reabra o terminal. '
                'Sem interface grafica, meca o HSV pelo teste_offline.py sobre uma foto.')
            return
        if tecla == ord('r'):
            self.amostras.clear()
            self.get_logger().info('amostras limpas.')
        elif tecla in (ord('q'), 27):
            raise KeyboardInterrupt

    def relatorio(self):
        p = sugerir_faixas(self.amostras)
        print('\n' + yaml_sugerido(p, float(self.get_parameter('area_min').value)) + '\n')


def main():
    rclpy.init()
    no = AmostradorHSV()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.relatorio()
        cv2.destroyAllWindows()
        no.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
