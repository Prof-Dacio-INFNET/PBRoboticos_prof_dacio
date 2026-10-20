"""Assina /camera/image_raw, segmenta POR INSTANCIA e publica a contagem.

E a evolucao direta do `segmentador_hsv` da Aula 3: la a cor da saida dizia
apenas a CLASSE do pixel, aqui o no sabe separar INSTANCIA de CLASSE -- e
publica a figura que voce pedir.

  entrada   /camera/image_raw     (sensor_msgs/Image)
  saidas    /vision/segmented     (sensor_msgs/Image -- ver o parametro `saida`)
            /vision/instancias    (std_msgs/Int32 -- quantas no ultimo quadro)

O parametro `saida` escolhe O QUE vai no /vision/segmented:

  classe_alpha  (PADRAO)  mascaras coloridas POR CLASSE, com transparencia
                          `alpha` sobre o frame e contorno por instancia. E o
                          que o item 3 do enunciado do TP3 pede, literalmente.
  instancia               uma cor por INSTANCIA, a figura da aula -- duas pecas
                          encostadas de uma cor so e a fusao na tela.
  mascara                 so a camada por classe, sobre fundo preto, sem o
                          frame. Util quando o fundo polui a conferencia.

O padrao mudou de `instancia` para `classe_alpha` por causa do enunciado; o
comportamento antigo continua a uma linha de distancia (`saida:=instancia`).

E o que o gate G3.4 do TP3 pede. O miolo nao esta aqui: esta em
`instancia.py`, ao lado, e e o MESMO codigo que o `avaliar.py` mede offline.
Este arquivo so faz a fronteira ROS 2 -- parametro entra, imagem entra,
mensagem sai.

    ros2 run aula13_instancia segmentador_instancia --ros-args \\
        --params-file config/instancia.yaml
    ros2 param set /segmentador_instancia metodo cor_watershed
    ros2 param set /segmentador_instancia saida instancia
"""
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import Int32

from .instancia import (CLASSES_PADRAO, CONFIG_PADRAO, detectar,
                        pintar_instancias, sobrepor_classes)
from .ponte import descrever_ponte, para_cv, para_msg

# BEST_EFFORT porque imagem e dado de sensor: quadro atrasado nao vale a espera.
# Isso tem consequencia na hora de VER: um display que pede RELIABLE nao recebe
# nada deste publicador, e nao aparece erro nenhum -- a tela fica cinza. No
# RViz2 ponha o display Image em "Best Effort" (o rviz/segmentacao.rviz do
# pacote ja vem assim); no rqt_image_view a opcao esta no proprio widget.
QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

SAIDAS = ('classe_alpha', 'instancia', 'mascara')


class SegmentadorInstancia(Node):
    def __init__(self):
        super().__init__('segmentador_instancia')
        self.declare_parameter('metodo', 'cor_conectada')
        # `saida` escolhe a FIGURA que vai no /vision/segmented, nao o
        # algoritmo. O padrao e o do enunciado do TP3 (item 3): cor por classe,
        # translucida sobre o frame. `instancia` traz de volta o comportamento
        # anterior deste no, cor por instancia.
        self.declare_parameter('saida', 'classe_alpha')
        self.declare_parameter('alpha', 0.5)
        self.declare_parameter('area_min', 400.0)
        self.declare_parameter('nucleo', 5)
        self.declare_parameter('fracao_semente', 0.60)
        self.declare_parameter('classes', list(CLASSES_PADRAO))
        # Uma faixa por classe, em seis inteiros:
        #   h1_min, h1_max, h2_min, h2_max, s_min, v_min
        # Duas faixas de matiz porque o vermelho da a volta no circulo de H.
        # Para as outras cores as duas sao iguais -- a convencao da Aula 3.
        for nome, d in CLASSES_PADRAO.items():
            self.declare_parameter('faixa.%s' % nome, [int(v) for v in d['faixa']])

        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.ao_receber, QOS_SENSOR)
        self.pub_img = self.create_publisher(Image, '/vision/segmented', QOS_SENSOR)
        self.pub_n = self.create_publisher(Int32, '/vision/instancias', 10)

        self.quadros = 0
        self.ultima = 0
        self.avisados = set()
        self.get_logger().info(
            'Segmentador de instancia no ar: /camera/image_raw -> '
            '/vision/segmented + /vision/instancias')
        self.get_logger().info(
            'metodo=%s | saida=%s alpha=%.2f | %s'
            % (self.get_parameter('metodo').value, self.get_parameter('saida').value,
               float(self.get_parameter('alpha').value), descrever_ponte()))

    def montar_cfg(self):
        """Le os parametros e monta o cfg que `instancia.detectar` entende.

        Toda a configuracao do algoritmo entra por aqui. E por isso que trocar
        de metodo em producao e, de verdade, uma linha no YAML: o no nao sabe
        o que `cor_watershed` faz, so repassa o nome.
        """
        classes = {}
        for nome in self.get_parameter('classes').value:
            chave = 'faixa.%s' % nome
            if not self.has_parameter(chave):
                # Classe que so existe no SEU YAML (amarelo, laranja...): declare
                # na hora, e o valor do arquivo entra como sobreposicao. E assim
                # que o exemplo aceita o dominio do aluno sem tocar no codigo.
                self.declare_parameter(chave, [0, 0, 0, 0, 0, 0])
            faixa = tuple(int(v) for v in self.get_parameter(chave).value)
            if len(faixa) != 6 or not any(faixa):
                self.get_logger().warn(
                    "classe '%s' sem faixa HSV valida em %s -- ignorada" % (nome, chave))
                continue
            classes[nome] = {'faixa': faixa,
                             'cor': CLASSES_PADRAO.get(nome, {}).get('cor', (0, 0, 0))}
        return {'metodo': self.get_parameter('metodo').value,
                'classes': classes or CONFIG_PADRAO['classes'],
                'area_min': float(self.get_parameter('area_min').value),
                'nucleo': int(self.get_parameter('nucleo').value),
                'fracao_semente': float(self.get_parameter('fracao_semente').value)}

    def avisar_uma_vez(self, chave, texto):
        """Aviso de parametro errado, uma vez por valor -- nao a 30 Hz."""
        if chave not in self.avisados:
            self.avisados.add(chave)
            self.get_logger().warn(texto)

    def desenhar(self, quadro, instancias):
        """A FIGURA de /vision/segmented, escolhida pelo parametro `saida`.

        Nenhuma das tres linhas faz conta de visao: o desenho mora no
        `instancia.py`, junto do algoritmo, para a figura do topico e a do
        avaliador offline sairem da mesma funcao.
        """
        saida = str(self.get_parameter('saida').value)
        alpha = float(self.get_parameter('alpha').value)
        if saida not in SAIDAS:
            self.avisar_uma_vez(
                'saida:' + saida,
                "saida='%s' nao existe (tenho: %s) -- usando classe_alpha"
                % (saida, ', '.join(SAIDAS)))
            saida = 'classe_alpha'
        if saida == 'instancia':
            # Cor por INSTANCIA, como este no fazia antes do parametro existir.
            return pintar_instancias(quadro, instancias)
        if saida == 'mascara':
            # So a camada: a MESMA funcao, com alpha 1,0 sobre um quadro preto.
            return sobrepor_classes(np.zeros_like(quadro), instancias, 1.0, False)
        return sobrepor_classes(quadro, instancias, alpha)

    def ao_receber(self, msg):
        quadro = para_cv(msg)
        instancias = detectar(quadro, self.montar_cfg())
        saida = self.desenhar(quadro, instancias)
        cv2.putText(saida, 'instancias: %d  (%s, %s)'
                    % (len(instancias), self.get_parameter('metodo').value,
                       self.get_parameter('saida').value),
                    (12, saida.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (30, 30, 30), 2, cv2.LINE_AA)

        self.ultima = len(instancias)
        self.quadros += 1
        self.pub_img.publish(para_msg(saida, stamp=msg.header.stamp, frame_id='camera'))
        self.pub_n.publish(Int32(data=self.ultima))


def main():
    rclpy.init()
    no = SegmentadorInstancia()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        # Ctrl+C: o rclpy do Humble ja pode ter derrubado o contexto pelo
        # signal handler, e chamar shutdown() de novo levanta barulho de saida
        # que assusta a turma sem que nada tenha quebrado.
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
