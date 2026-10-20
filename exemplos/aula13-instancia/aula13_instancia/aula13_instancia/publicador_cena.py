"""Publica os quadros de `cena/` em /camera/image_raw. Sem camera nenhuma.

Serve para o launch subir em qualquer maquina -- inclusive no WSL2 sem usbipd,
inclusive na aula com a turma inteira na mesma rede. E serve para outra coisa,
mais importante: os quadros publicados sao OS MESMOS que o `avaliar.py` mede
offline. O numero que aparece no `/vision/instancias` tem de bater com a coluna
`previstas` da tabela. Quando nao bate, o problema esta na fronteira ROS 2 (QoS,
parametro, encoding), nao no algoritmo -- e isso ja e meio diagnostico pronto.

    ros2 run aula13_instancia publicador_cena --ros-args -p pasta:=/caminho/cena
    ros2 run aula13_instancia publicador_cena --ros-args -p fps:=2.0

Se a pasta nao for encontrada, o no publica um quadro de RESERVA, desenhado
aqui mesmo: duas pecas encostadas e uma solta. Nao e a cena medida -- e o
minimo para o launch nao subir vazio e para dar o que olhar no RViz2 (ou no
rqt_image_view, se preferir).
"""
import os
import pathlib

import cv2
import numpy as np
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from .ponte import descrever_ponte, para_msg

QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


def quadro_de_reserva(largura=640, altura=480):
    """Cena minima, desenhada em oito linhas: um par colado e uma peca solta.

    Existe so para o caso de a pasta `cena/` nao estar por perto. A cena de
    verdade -- 12 quadros, verdade por pixel, determinismo -- sai do `cena.py`,
    e e com ela que se mede.
    """
    img = np.full((altura, largura, 3), 232, np.uint8)
    cv2.circle(img, (int(largura * 0.32), altura // 2), 46, (40, 40, 210), -1, cv2.LINE_AA)
    cv2.circle(img, (int(largura * 0.32) + 86, altura // 2), 46, (40, 40, 210), -1,
               cv2.LINE_AA)
    cv2.circle(img, (int(largura * 0.72), altura // 2), 44, (200, 110, 40), -1, cv2.LINE_AA)
    cv2.putText(img, 'quadro de reserva - rode python3 cena.py', (14, altura - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (90, 90, 90), 1, cv2.LINE_AA)
    return img


class PublicadorCena(Node):
    def __init__(self):
        super().__init__('publicador_cena')
        self.declare_parameter('pasta', '')
        self.declare_parameter('fps', 4.0)

        self.pub = self.create_publisher(Image, '/camera/image_raw', QOS_SENSOR)
        self.k = 0

        self.quadros = self.carregar(self.get_parameter('pasta').value)
        fps = max(0.2, float(self.get_parameter('fps').value))
        # Timer no relogio MONOTONICO, como na Aula 3: ajuste de horario no
        # WSL2 (que acontece depois de suspender a maquina) nao pode congelar
        # o publicador esperando o relogio de parede alcancar o proximo tique.
        self.timer = self.create_timer(1.0 / fps, self.publicar,
                                       clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info('%d quadro(s) em %.1f fps | %s'
                               % (len(self.quadros), fps, descrever_ponte()))

    def carregar(self, pasta):
        """Procura a cena em mais de um lugar antes de desistir.

        O aluno pode lancar de qualquer diretorio, e /tmp some no reboot. Dizer
        onde se procurou vale mais do que uma excecao -- a licao e a mesma do
        comparar_mapas.py da Aula 12.
        """
        candidatos = [pathlib.Path(pasta)] if pasta else []
        candidatos += [pathlib.Path.cwd() / 'cena']
        # Onde a pagina da aula manda o aluno copiar o exemplo: $PB_DIR. O no
        # roda com o cwd do launch, entao sem isto ele cai no quadro de reserva
        # justamente na maquina de quem seguiu a instrucao.
        for var in ('PB_DIR', 'PB_WS'):
            raiz = os.environ.get(var)
            if raiz:
                base = pathlib.Path(raiz)
                candidatos.append(base / 'aula13-instancia' / 'cena')
                candidatos.append(base.parent / 'aula13-instancia' / 'cena')
        candidatos += sorted(pathlib.Path.home().glob('projeto-pb-*/aula13-instancia/cena'))
        candidatos.append(pathlib.Path.home() / 'aula13-instancia' / 'cena')
        for c in candidatos:
            arquivos = sorted(c.glob('quadro*.png')) if c.is_dir() else []
            if arquivos:
                quadros = [cv2.imread(str(a), cv2.IMREAD_COLOR) for a in arquivos]
                quadros = [q for q in quadros if q is not None]
                if quadros:
                    self.get_logger().info('cena: %s' % c)
                    return quadros
        self.get_logger().warn(
            'nao achei quadro*.png em: %s -- publicando o quadro de reserva. '
            'Gere a cena com `python3 cena.py` e aponte -p pasta:=<caminho>/cena'
            % ', '.join(str(c) for c in candidatos))
        return [quadro_de_reserva()]

    def publicar(self):
        quadro = self.quadros[self.k % len(self.quadros)]
        self.pub.publish(para_msg(quadro, stamp=self.get_clock().now().to_msg(),
                                  frame_id='camera'))
        self.k += 1


def main():
    rclpy.init()
    no = PublicadorCena()
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
