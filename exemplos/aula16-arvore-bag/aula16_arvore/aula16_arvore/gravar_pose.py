"""Transforma a sessao gravada no bag no CSV que a analise offline le.

    ros2 run aula16_arvore gravar_pose
    ros2 run aula16_arvore gravar_pose --ros-args -p saida:=sessao.csv -p hz:=10.0
    ros2 launch aula16_arvore analise.launch.py saida:=sessao.csv

O QUE JA FOI EXECUTADO: em 09/11/2026, numa maquina com Humble, pelo
`analise.launch.py` ao lado de um `ros2 bag play --clock`, este no gravou
1157 linhas a 10 Hz de um bag de 123 s. A secao "O que foi e o que nao foi
verificado" do README separa o que foi visto rodando do que nao foi.

O QUE ELE E: o caminho garantido do gate G4.4.

    O G4.4 cobra um bag REPRODUZIVEL -- que da para rodar a analise com o
    robo desligado. Ha dois jeitos de ler um bag:

      1. `rosbag2_py`, lendo o arquivo direto, em Python. Funciona, e tem
         detalhe: serializacao, tipo por topico, `rclpy.serialization`, e um
         erro de versao de armazenamento que custa uma tarde.
      2. `ros2 bag play` + um no assinando os topicos, como se o robo
         estivesse no ar.

    Este no e o caminho 2, e ele e o garantido: se o seu codigo funcionou com
    o robo, ele funciona com o bag tocando, porque do lado do assinante NAO
    HA DIFERENCA NENHUMA. E o melhor argumento a favor de ROS 2 que a
    disciplina tem para dar, e ele cabe em uma frase: o bag e indistinguivel
    do robo.

    O preco e um so, e e o `use_sim_time`. Veja abaixo.

AS DUAS DECISOES QUE VALEM LEITURA:

  QoS em Best Effort nos CINCO assinantes.
    A regra da Aula 13 e da Aula 15: um assinante pode pedir MENOS garantia
    que o publicador, nunca mais. Best Effort casa com publicador Reliable E
    com publicador Best Effort; Reliable casa so com Reliable, e contra um
    publicador Best Effort fica em silencio -- sem erro, sem aviso, sem
    mensagem. O /scan do Nav2 e Best Effort (SensorDataQoS); o /odom e o
    /amcl_pose costumam ser Reliable. Pedindo Best Effort nos cinco, nenhuma
    combinacao fica muda. Em troca, pode cair uma amostra aqui e ali -- o que,
    para uma analise a 10 Hz, custa nada.

  Temporizador com retencao do ultimo valor, e nao sincronizacao de mensagens.
    Os cinco topicos chegam em taxas diferentes e sem relacao nenhuma entre
    si: o /scan a 5-10 Hz, o /amcl_pose so quando o AMCL atualiza, o /cmd_vel
    a 20 Hz, o /estado_vigia a 10 Hz e em cada transicao. Um
    `message_filters.ApproximateTimeSynchronizer` neles jogaria fora quase
    tudo: ele so emite quando todos chegam perto um do outro, e o
    /estado_vigia pode ficar minutos sem publicar.

    Por isso o padrao certo aqui e o outro: cada callback guarda o ULTIMO
    valor, e um temporizador a 10 Hz grava uma linha com o que houver.
    Chama-se retencao de ordem zero, e e o que qualquer registrador de
    telemetria faz. O custo e conhecido e tem de estar no relatorio: uma
    linha do CSV mistura amostras de ate 100 ms de idade.

O `use_sim_time`, que e onde todo mundo tropeca:

    `ros2 bag play --clock` publica o relogio do BAG no topico /clock. Um no
    com `use_sim_time:=true` usa esse relogio; sem ele, usa o relogio de
    parede. Se voce gravou a sessao ontem e toca o bag hoje, a coluna `t` sai
    com a data de hoje e nada bate com nada.

    Este no se defende de um jeito simples: a coluna `t` e sempre RELATIVA a
    primeira linha gravada. Com ou sem `use_sim_time`, ela comeca em zero.
    Mas o intervalo entre linhas so sai certo com `--clock` + `use_sim_time`,
    e e por isso que o `analise.launch.py` vem com `use_sim_time:=true` por
    padrao. Tocando o bag em `--rate 2.0` sem `--clock`, a sua sessao de 90 s
    vira um CSV de 45 s -- e a regua vai dizer que a espera durou 1 s.
"""
import csv
import math

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from aula16_arvore.varredura import SETOR_PADRAO_GRAUS, menor_distancia

# O contrato de colunas. E o MESMO do `simular_sessao.py`, e tem de continuar
# sendo: o `plotar_trajetoria.py` e o `medir_sessao.py` leem estes nomes nesta
# ordem, e nao sabem (nem precisam saber) se o CSV veio do simulador ou do bag.
CAMPOS_CSV = ('t', 'odom_x', 'odom_y', 'odom_yaw', 'amcl_x', 'amcl_y',
              'amcl_yaw', 'dist_min_scan', 'cmd_v', 'cmd_w', 'estado')

# O que vai na coluna `estado` enquanto o /estado_vigia nao publicou nada.
# Nao e `desconhecido` de proposito: uma sessao sem o vigia no ar e uma
# sessao em que o robo navegou o tempo todo, e e isso que a regua deve ver.
ESTADO_PADRAO = 'navegando'

# Quando nenhum /scan chegou ainda, nao ha `range_max` para consultar. Este
# valor so aparece nas primeiras linhas do CSV, e e generoso de proposito:
# um numero grande na coluna `dist_min_scan` nunca e confundido com obstaculo.
ALCANCE_SEM_SCAN = 10.0


def yaw_de_quaternio(q):
    """Yaw a partir do quaternio da mensagem. So a rotacao em z importa aqui.

    A formula completa e o atan2 abaixo; para um robo que anda no plano, x e
    y do quaternio sao ~0 e isto vira `2*atan2(z, w)`. Mantido completo
    porque custa uma linha e nao depende de o seu robo ser mesmo planar.
    """
    seno = 2.0 * (q.w * q.z + q.x * q.y)
    cosseno = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(seno, cosseno)


class GravarPose(Node):
    """Assina os quatro topicos da sessao e grava uma linha a cada 1/hz s."""

    def __init__(self):
        super().__init__('gravar_pose')
        self.declare_parameter('saida', 'sessao.csv')
        self.declare_parameter('hz', 10.0)
        self.declare_parameter('setor_graus', SETOR_PADRAO_GRAUS)
        # Nao grave linha nenhuma antes de o /amcl_pose aparecer: sem ele as
        # colunas amcl_* seriam zeros, e zero e um lugar valido no mapa. Um
        # CSV que comeca com dez linhas em (0, 0) poe uma perna falsa no
        # grafico do relatorio. Em `false`, grava assim que o /odom chegar.
        self.declare_parameter('exigir_amcl', True)

        self.caminho = self.get_parameter('saida').value
        self.hz = float(self.get_parameter('hz').value)
        self.setor = float(self.get_parameter('setor_graus').value)
        self.exigir_amcl = bool(self.get_parameter('exigir_amcl').value)

        self.odom = None
        self.amcl = None
        self.dist = float('inf')
        self.alcance_max = ALCANCE_SEM_SCAN
        self.cmd = (0.0, 0.0)
        self.estado = ESTADO_PADRAO
        self.t_zero = None
        self.linhas = 0

        # Best Effort nos cinco -- veja o docstring do modulo.
        self.create_subscription(Odometry, 'odom', self.ao_odom,
                                 qos_profile_sensor_data)
        self.create_subscription(PoseWithCovarianceStamped, 'amcl_pose',
                                 self.ao_amcl, qos_profile_sensor_data)
        self.create_subscription(LaserScan, 'scan', self.ao_scan,
                                 qos_profile_sensor_data)
        self.create_subscription(Twist, 'cmd_vel', self.ao_cmd,
                                 qos_profile_sensor_data)
        self.create_subscription(String, 'estado_vigia', self.ao_estado,
                                 qos_profile_sensor_data)

        self.arquivo = open(self.caminho, 'w', newline='', encoding='utf-8')
        self.escritor = csv.DictWriter(self.arquivo, fieldnames=CAMPOS_CSV)
        self.escritor.writeheader()
        self.arquivo.flush()

        self.create_timer(1.0 / self.hz, self.ao_tempo)
        self.create_timer(5.0, self.ao_relatar)
        self.get_logger().info(
            'gravando %s a %.1f Hz; toque o bag em outro terminal:\n'
            '  ros2 bag play <sua-sessao> --clock' % (self.caminho, self.hz))

    # ------------------------------------------------------ os assinantes
    def ao_odom(self, msg):
        p = msg.pose.pose
        self.odom = (p.position.x, p.position.y, yaw_de_quaternio(p.orientation))

    def ao_amcl(self, msg):
        p = msg.pose.pose
        self.amcl = (p.position.x, p.position.y, yaw_de_quaternio(p.orientation))

    def ao_scan(self, msg):
        self.dist = menor_distancia(msg, self.setor)
        # O alcance do laser vem do proprio cabecalho: e ele que vai para o
        # CSV quando o setor inteiro estiver vazio (veja `ao_tempo`).
        self.alcance_max = float(msg.range_max)

    def ao_cmd(self, msg):
        self.cmd = (msg.linear.x, msg.angular.z)

    def ao_estado(self, msg):
        # Retencao de ordem zero aqui tambem: fica o ULTIMO estado ouvido.
        # Um `interrompido` de 2 ms e' sobrescrito pelo `esperando` antes da
        # proxima linha, e por isso o CSV de um bag real quase so' tem
        # `navegando` e `esperando`. O bag guarda os quatro; a regua conta o
        # evento pelo `esperando`, que dura 2 s (veja `medir_sessao.eventos`).
        self.estado = msg.data

    # ------------------------------------------------------ o temporizador
    def ao_tempo(self):
        """Grava uma linha com o ultimo valor de cada topico."""
        if self.odom is None:
            return
        if self.exigir_amcl and self.amcl is None:
            return
        agora = self.get_clock().now().nanoseconds * 1e-9
        if self.t_zero is None:
            self.t_zero = agora
        amcl = self.amcl if self.amcl is not None else self.odom
        # `inf` no CSV quebra a regua de dois jeitos: o `min()` dela deixa de
        # significar alguma coisa e o grafico ganha um pico infinito. Vira o
        # `range_max` do proprio laser, que e o que "nao vi nada" quer dizer.
        # Zero seria pior do que inf: zero e obstaculo encostado no robo, e o
        # portao de 0,5 m leria a sessao inteira como obstaculo.
        dist = self.dist if math.isfinite(self.dist) else self.alcance_max
        self.escritor.writerow({
            't': round(agora - self.t_zero, 4),
            'odom_x': self.odom[0], 'odom_y': self.odom[1],
            'odom_yaw': self.odom[2],
            'amcl_x': amcl[0], 'amcl_y': amcl[1], 'amcl_yaw': amcl[2],
            'dist_min_scan': dist, 'cmd_v': self.cmd[0], 'cmd_w': self.cmd[1],
            'estado': self.estado})
        # Um flush por linha, a 10 Hz, para que um Ctrl-C no meio da sessao
        # deixe um CSV completo ate ali em vez de um arquivo vazio com o
        # buffer por gravar.
        self.arquivo.flush()
        self.linhas += 1

    def ao_relatar(self):
        if self.linhas == 0:
            self.get_logger().warn(
                'nenhuma linha ainda. Falta %s. Confira: ros2 topic hz /odom'
                % ('o /odom' if self.odom is None else 'o /amcl_pose'))
            return
        self.get_logger().info('%d linhas em %s' % (self.linhas, self.caminho))

    def fechar(self):
        self.arquivo.close()
        self.get_logger().info(
            '%d linhas gravadas em %s. Agora, com o robo DESLIGADO:\n'
            '  python3 medir_sessao.py %s\n'
            '  python3 plotar_trajetoria.py %s --saida trajetoria.png'
            % (self.linhas, self.caminho, self.caminho, self.caminho))


def main():
    rclpy.init()
    no = GravarPose()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.fechar()
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
