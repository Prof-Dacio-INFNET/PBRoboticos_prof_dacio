"""Leva o efetuador do Panda a tres poses, uma de cada vez, e conta o que houve.

    ros2 run aula18_moveit tres_poses
    ros2 run aula18_moveit tres_poses --ros-args -p modo:=planejar
    ros2 run aula18_moveit tres_poses --ros-args -p com_proibida:=true
    ros2 run aula18_moveit tres_poses --ros-args -p comparar:=true
    ros2 run aula18_moveit tres_poses --ros-args -p voltar_ao_ready:=false
    ros2 run aula18_moveit tres_poses --ros-args \\
        -p poses:="[0.45, 0.30, 0.35, 0.45, -0.30, 0.35, 0.45, 0.0, 0.60]"

ADVERTENCIA: EXECUTADO pela primeira vez em 16/11 (WSL2 do professor,
Humble, MoveIt 2.5.10 pelo apt): com a caixa na cena, ready, A, B e C deram
SUCCESS no planejamento e na execucao em tres execucoes seguidas. O que NAO
rodou ainda: a VOLTA AO READY (parametro voltar_ao_ready, e a volta antes de
por a caixa no comparar), escrita depois do ensaio para corrigir o defeito que
ele achou -- a rodada sem a caixa terminava na pose D, DENTRO do volume da
caixa, e a caixa era posta em cima do braco (START_STATE_INVALID em tudo
depois). Essa parte so foi conferida pelo testar.py, com dubles.

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

A VOLTA AO READY (movimento de servico, fora da tabela, dito no log):

    no comparar, entre as duas rodadas: o braco volta ao ready ANTES de a
    caixa entrar. Sem isso, a rodada sem a caixa termina onde a ultima pose
    deixou o braco -- com com_proibida, na D, dentro do volume da caixa -- e
    a caixa nasce em cima dele. Se a volta falhar, a caixa NAO e posta.

    no fim de toda execucao que mexe o braco (modos executar e direto), com
    voltar_ao_ready (padrao true): o proximo comando -- o cena, o
    pegar_e_soltar, este mesmo -- parte de um estado conhecido, fora da
    caixa. No modo planejar o braco nao se mexe, e nao ha volta.
"""
import rclpy

from aula18_moveit import cena, codigos, mensagens, sequencia
from aula18_moveit.cliente import ClienteMoveIt

POSES_PADRAO = [
    0.45, 0.30, 0.35,     # A
    0.45, -0.30, 0.35,    # B
    0.45, 0.00, 0.60,     # C
]
POSE_PROIBIDA = [0.45, 0.00, 0.30]   # D: dentro da caixa padrao do `cena`
ALVO_READY = {'nome': 'ready', 'tipo': 'juntas', 'valores': mensagens.ESTADOS['ready'],
              'descricao': 'estado nomeado do SRDF, por juntas (sem IK)'}


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
        alvos.append(dict(ALVO_READY))
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
        self.declare_parameter('voltar_ao_ready', True)
        self.modo = self.get_parameter('modo').value
        self.alvos = montar_alvos(
            self.get_parameter('poses').value,
            [float(v) for v in self.get_parameter('orientacao').value],
            bool(self.get_parameter('comecar_em_ready').value),
            bool(self.get_parameter('com_proibida').value))
        self.comparar = bool(self.get_parameter('comparar').value)
        self.voltar = bool(self.get_parameter('voltar_ao_ready').value)

    def _rodada(self, titulo):
        log = self.get_logger().info
        log('=== %s (modo %s) ===' % (titulo, self.modo))
        res = sequencia.percorrer(self.alvos, lambda a: self.mover(a, self.modo), log=log)
        for linha in sequencia.tabela(res, titulo):
            log(linha)
        return res

    def voltar_ao_ready(self, motivo):
        """Movimento de servico: leva o braco ao ready, FORA da tabela.

        Devolve True se o braco esta no ready ao fim (ou se o modo nao mexe
        o braco). Diz no log o que fez e, se falhou, o que olhar.
        """
        log = self.get_logger()
        if self.modo == 'planejar':
            return True      # o braco nao se mexeu: nao ha de onde voltar
        log.info('(servico, fora da tabela) voltando ao ready %s...' % motivo)
        r = self.mover(dict(ALVO_READY), self.modo)
        if r.executou:
            log.info('(servico) o braco esta no ready: %d pontos, %.2f rad'
                     % (r.pontos, r.comprimento))
            return True
        exe = '-' if r.execucao is None else codigos.descrever(r.execucao)
        log.error('(servico) NAO consegui voltar ao ready: planejamento %s, execucao %s'
                  % (r.situacao(), exe))
        log.error('      olhe: %s' % (codigos.dica(r.execucao) if r.planejou
                                     else sequencia.dica(r)))
        return False

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
            if self.voltar:
                self.voltar_ao_ready('para o proximo comando partir dele')
            for linha in sequencia.resumo(res):
                log(linha)
            return 0

        # Sem a caixa. success = False aqui so quer dizer que ela nao estava la.
        self.aplicar_cena(cena.diff_remover())
        sem = self._rodada('SEM a caixa')
        # A ultima pose da rodada sem a caixa pode estar DENTRO dela (a D
        # esta, de proposito). Por a caixa ali e prender o braco: todo plano
        # seguinte daria START_STATE_INVALID. Visto no ensaio de 16/11.
        if not self.voltar_ao_ready('antes de por a caixa (a ultima pose pode estar '
                                    'dentro dela)'):
            self.get_logger().error('NAO pus a caixa: com o braco fora do ready, ele poderia '
                                    'ficar dentro dela. Parei antes da segunda rodada.')
            return 1
        if self.aplicar_cena(cena.diff_adicionar()) is not True:
            self.get_logger().error('nao consegui por a caixa na cena; parei antes da '
                                    'segunda rodada. Olhe o Terminal A.')
            return 1
        com = self._rodada('COM a caixa')
        if self.voltar:
            self.voltar_ao_ready('para o proximo comando partir dele')
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
