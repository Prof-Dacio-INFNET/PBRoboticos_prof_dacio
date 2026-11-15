"""Leva o efetuador do Panda a tres poses, uma de cada vez, e conta o que houve.

    ros2 run aula18_moveit tres_poses
    ros2 run aula18_moveit tres_poses --ros-args -p modo:=planejar
    ros2 run aula18_moveit tres_poses --ros-args -p com_proibida:=true
    ros2 run aula18_moveit tres_poses --ros-args -p comparar:=true
    ros2 run aula18_moveit tres_poses --ros-args \\
        -p poses:="[0.45, 0.30, 0.35, 0.45, -0.30, 0.35, 0.45, 0.0, 0.60]"

ADVERTENCIA: NUNCA EXECUTADO com ROS 2. As poses padrao saem de uma conta de
cinematica feita SEM o MoveIt (testar.py, grupo 6: cinematica direta e
inversa numerica do URDF do Panda, com um teste de colisao grosseiro contra a
caixa). Elas sao plausiveis, nao testadas. Se alguma falhar no ensaio, o
README ensina a achar uma pose valida em um minuto, arrastando o marcador no
RViz2 e lendo a pose com o tf2_echo.

O QUE O ITEM 1 DO TP5 PEDE, e onde isso esta aqui:

    ">= 3 poses destino evitando colisoes" -- as poses A, B e C, com a caixa
    do `cena` na cena. "cinematica inversa" -- cada pose e uma POSE do
    efetuador, nao angulos de junta; o MoveIt resolve a IK dentro do
    planejamento (veja mensagens.restricoes_de_pose). "planejamento" -- o
    OMPL, e o tempo e o numero de pontos que este no imprime. "ros2_control"
    -- quem executa a trajetoria e o panda_arm_controller do demo, com
    hardware falso.

AS POSES PADRAO (panda_link8, quadro panda_link0, garra para baixo):

    ready  o estado nomeado do SRDF, por JUNTAS -- o ponto de partida fixo
    A      (0,45;  0,30; 0,35)  a esquerda da caixa
    B      (0,45; -0,30; 0,35)  a direita da caixa: de A para B a reta
                                atravessa a caixa, o planejador da a volta
    C      (0,45;  0,00; 0,60)  em cima da caixa, garra 10 cm acima dela
    D      (0,45;  0,00; 0,30)  DENTRO da caixa, so com com_proibida:=true:
                                sem a caixa ela e alcancavel; com a caixa nao
                                existe estado do braco que a satisfaca

OS MODOS (parametro `modo`):

    executar  (padrao) planeja, e se deu certo executa -- separados, como os
              botoes Plan e Execute do RViz2
    planejar  so planeja; o robo fica parado e o RViz2 mostra a trajetoria
              (todas partem do mesmo lugar)
    direto    planeja e executa num pedido so; sem tempo de planejamento do
              MoveIt na tabela, so o do relogio

`comparar:=true` roda a lista inteira duas vezes -- sem a caixa e com a
caixa -- e imprime as duas lado a lado. E a demonstracao da aula em um
comando. Ele DEIXA a caixa na cena ao terminar.
"""
import rclpy

from aula18_moveit import cena, mensagens, sequencia
from aula18_moveit.cliente import ClienteMoveIt

POSES_PADRAO = [
    0.45, 0.30, 0.35,     # A
    0.45, -0.30, 0.35,    # B
    0.45, 0.00, 0.60,     # C
]
POSE_PROIBIDA = [0.45, 0.00, 0.30]   # D: dentro da caixa padrao do `cena`


def montar_alvos(poses, orientacao=mensagens.PARA_BAIXO, comecar_em_ready=True,
                 com_proibida=False):
    """A lista de alvos que a sequencia percorre. Sem ROS 2: o testar.py usa."""
    bruta = [float(v) for v in poses]
    if not bruta or len(bruta) % 3 != 0:
        raise ValueError('poses tem de ter multiplos de 3 numeros (x, y, z por pose); '
                         'recebi %d' % len(bruta))
    if com_proibida:
        bruta += POSE_PROIBIDA
    alvos = []
    if comecar_em_ready:
        alvos.append({'nome': 'ready', 'tipo': 'juntas',
                      'valores': mensagens.ESTADOS['ready'],
                      'descricao': 'estado nomeado do SRDF, por juntas (sem IK)'})
    for i in range(0, len(bruta), 3):
        letra = chr(ord('A') + i // 3)
        x, y, z = bruta[i:i + 3]
        alvos.append({'nome': letra, 'tipo': 'pose', 'valores': [x, y, z],
                      'orientacao': tuple(orientacao),
                      'descricao': 'panda_link8 em (%.2f, %.2f, %.2f) m, garra %s'
                                   % (x, y, z, 'para baixo'
                                      if tuple(orientacao) == mensagens.PARA_BAIXO
                                      else 'na orientacao dada')})
    return alvos


class TresPoses(ClienteMoveIt):

    def __init__(self):
        super().__init__('tres_poses')
        self.declare_parameter('modo', 'executar')
        self.declare_parameter('poses', POSES_PADRAO)
        self.declare_parameter('orientacao', list(mensagens.PARA_BAIXO))
        self.declare_parameter('comecar_em_ready', True)
        self.declare_parameter('com_proibida', False)
        self.declare_parameter('comparar', False)
        self.modo = self.get_parameter('modo').value
        self.alvos = montar_alvos(
            self.get_parameter('poses').value,
            [float(v) for v in self.get_parameter('orientacao').value],
            bool(self.get_parameter('comecar_em_ready').value),
            bool(self.get_parameter('com_proibida').value))
        self.comparar = bool(self.get_parameter('comparar').value)

    def _rodada(self, titulo):
        log = self.get_logger().info
        log('=== %s (modo %s) ===' % (titulo, self.modo))
        res = sequencia.percorrer(self.alvos, lambda a: self.mover(a, self.modo), log=log)
        for linha in sequencia.tabela(res, titulo):
            log(linha)
        return res

    def rodar(self):
        if self.modo not in ('executar', 'planejar', 'direto'):
            self.get_logger().error("modo:='%s' -- use executar, planejar ou direto" % self.modo)
            return 2
        if not self.esperar_move_group(precisa_executar=(self.modo == 'executar'),
                                       precisa_cena=self.comparar):
            return 1
        log = self.get_logger().info
        if not self.comparar:
            res = self._rodada('as poses, com a cena como ela esta agora')
            for linha in sequencia.resumo(res):
                log(linha)
            return 0

        # Sem a caixa. success = False aqui so quer dizer que ela nao estava la.
        self.aplicar_cena(cena.diff_remover())
        sem = self._rodada('SEM a caixa')
        if self.aplicar_cena(cena.diff_adicionar()) is not True:
            self.get_logger().error('nao consegui por a caixa na cena; parei antes da '
                                    'segunda rodada. Olhe o Terminal A.')
            return 1
        com = self._rodada('COM a caixa')
        log('=== as mesmas poses, lado a lado ===')
        for linha in sequencia.comparar(sem, com):
            log(linha)
        for linha in sequencia.resumo(sem + com):
            log(linha)
        log('a caixa FICOU na cena. Para tirar: ros2 run aula18_moveit cena '
            '--ros-args -p acao:=remover')
        return 0


def main():
    rclpy.init()
    no = TresPoses()
    try:
        codigo = no.rodar()
    except KeyboardInterrupt:
        # Ctrl-C aqui NAO cancela um movimento em andamento no move_group.
        codigo = 130
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(codigo)


if __name__ == '__main__':
    main()
