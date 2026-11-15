"""Poe (ou tira) uma caixa na frente do Panda: o Collision Object do TP5.

    ros2 run aula18_moveit cena
    ros2 run aula18_moveit cena --ros-args -p acao:=remover
    ros2 run aula18_moveit cena --ros-args -p centro:="[0.45, 0.0, 0.2]" \\
        -p tamanho:="[0.1, 0.2, 0.4]"

ADVERTENCIA: NUNCA EXECUTADO com ROS 2. A mensagem foi montada campo por
campo contra a fonte do Humble e conferida pelo testar.py com dubles; a
geometria (a caixa nao encosta no Panda em `ready`, e fica entre as poses A e
B do tres_poses) e uma conta aproximada do testar.py, grupo 6, nao um teste
de colisao do MoveIt.

O QUE E UM COLLISION OBJECT:

    O MoveIt nao enxerga nada. Ele planeja contra a CENA DE PLANEJAMENTO
    (planning scene): o robo, os objetos que alguem declarou e, se houver
    sensor, um octomap. Esta caixa nao existe no mundo; existe na cena, e e
    isso que faz o planejador desviar dela. Voce a ve no RViz2 porque o
    display PlanningScene desenha a cena que o move_group publica em
    /monitored_planning_scene.

A CAIXA PADRAO:

    centro (0,45; 0,0; 0,20) m, tamanho (0,10 x 0,20 x 0,40) m, no quadro
    panda_link0: um bloco de 40 cm de altura, em pe no chao, 40-50 cm a frente
    do robo, ocupando y de -0,10 a +0,10. As poses A (y = +0,30) e B
    (y = -0,30) do tres_poses ficam uma de cada lado -- ir de uma a outra pelo
    caminho mais curto atravessa a caixa, e o planejador tem de dar a volta.
"""
import rclpy

from aula18_moveit import mensagens
from aula18_moveit.cliente import ClienteMoveIt

CAIXA_ID = 'caixa'
CAIXA_CENTRO = [0.45, 0.0, 0.20]
CAIXA_TAMANHO = [0.10, 0.20, 0.40]


def diff_adicionar(ident=CAIXA_ID, centro=CAIXA_CENTRO, tamanho=CAIXA_TAMANHO):
    return mensagens.cena_diff(objetos=[mensagens.caixa(ident, centro, tamanho)])


def diff_remover(ident=CAIXA_ID):
    return mensagens.cena_diff(objetos=[mensagens.remocao(ident)])


class Cena(ClienteMoveIt):

    def __init__(self):
        super().__init__('cena')
        self.declare_parameter('acao', 'adicionar')
        self.declare_parameter('id', CAIXA_ID)
        self.declare_parameter('centro', CAIXA_CENTRO)
        self.declare_parameter('tamanho', CAIXA_TAMANHO)
        self.acao = self.get_parameter('acao').value
        self.ident = self.get_parameter('id').value
        self.centro = [float(v) for v in self.get_parameter('centro').value]
        self.tamanho = [float(v) for v in self.get_parameter('tamanho').value]

    def rodar(self):
        if self.acao not in ('adicionar', 'remover'):
            self.get_logger().error("acao:='%s' -- use adicionar ou remover" % self.acao)
            return 2
        if len(self.centro) != 3 or len(self.tamanho) != 3:
            self.get_logger().error('centro e tamanho tem de ter 3 numeros cada')
            return 2
        if not self.esperar_move_group(precisa_executar=False):
            return 1
        if self.acao == 'adicionar':
            diff = diff_adicionar(self.ident, self.centro, self.tamanho)
            self.get_logger().info('pedindo: adicionar "%s" centro %s tamanho %s (panda_link0)'
                                   % (self.ident, self.centro, self.tamanho))
        else:
            diff = diff_remover(self.ident)
            self.get_logger().info('pedindo: remover "%s"' % self.ident)
        ok = self.aplicar_cena(diff)
        if ok is None:
            return 1
        if ok:
            self.get_logger().info(
                'o move_group respondeu success = True. Olhe o RViz2: a caixa tem de '
                '%s no display PlanningScene.'
                % ('aparecer (verde)' if self.acao == 'adicionar' else 'sumir'))
            return 0
        # Remover um id que nao existe tambem cai aqui: o move_group devolve
        # success = False e escreve no log dele que nao achou o objeto.
        self.get_logger().warn(
            'o move_group respondeu success = False. Olhe o Terminal A. Se a acao foi '
            'remover, o mais comum e nao haver objeto "%s" na cena.' % self.ident)
        return 1


def main():
    rclpy.init()
    no = Cena()
    try:
        codigo = no.rodar()
    except KeyboardInterrupt:
        codigo = 130
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(codigo)


if __name__ == '__main__':
    main()
