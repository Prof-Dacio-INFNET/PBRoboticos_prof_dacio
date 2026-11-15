"""ROTEIRO de pick-and-place SEM fisica: pegar um cubo e deixa-lo do outro lado.

    ros2 run aula18_moveit pegar_e_soltar
    ros2 run aula18_moveit pegar_e_soltar --ros-args -p ate_passo:=6

ADVERTENCIA -- LEIA ANTES: este arquivo e um ROTEIRO, nunca executado, nem
pelo professor. A sequencia e as mensagens foram montadas contra a fonte do
Humble e o testar.py confere a ordem dos passos, as alturas e que ele para no
primeiro passo que falhar. O que NAO se sabe: se a pegada (dedos em volta do
cubo) e aceita pelo verificador de colisao do MoveIt com a malha de colisao
dos dedos do Panda, e se o OMPL faz a descida de 10 cm em linha razoavel (ele
nao promete linha reta; veja "Como adequar" no README). E o ponto de partida
da tarefa da semana, nao uma demonstracao pronta. `ate_passo:=N` para no
passo N, para voce depurar um passo de cada vez.

SEM FISICA quer dizer: nada cai, nada escorrega, a garra nao sente o cubo. O
que faz o cubo "ir junto" com a mao e a ANEXACAO -- um AttachedCollisionObject:
a partir dali o cubo faz parte do robo para o verificador de colisao, e o
planejador desvia COM ele. Sem anexar, o braco levaria a mao vazia e o cubo
ficaria parado no chao da cena.

A SEQUENCIA (todas as poses no panda_link8, garra para baixo):

    1 cena      poe o cubo "peca" (4 cm) no chao, em (0,45; -0,30)
    2 ready     estado nomeado, por juntas
    3 abrir     garra a 0,035 (o estado `open` do SRDF); ela nasce FECHADA
                no demo (initial_value 0.0 no panda_hand.ros2_control.xacro)
    4 pre       10 cm acima da pegada
    5 pegada    dedos na altura do meio do cubo
    6 fechar    garra a 0,02: cada dedo a 2 cm do centro = o cubo de 4 cm
    7 anexar    AttachedCollisionObject: o cubo passa a ser parte da mao
    8 subir     de volta a pre-pegada
    9 levar     10 cm acima do destino, (0,45; +0,30) -- do outro lado da caixa,
                se ela estiver na cena
   10 descer    altura de soltura
   11 abrir     garra a 0,035
   12 soltar    REMOVE do anexado: o cubo volta ao mundo onde a mao o deixou
   13 recuar    10 cm acima
   14 ready     de volta

A GARRA: control_msgs/action/GripperCommand em
/panda_hand_controller/gripper_cmd (gripper_controllers do ros2_controllers,
branch humble: create_server(..., "~/gripper_cmd")). O `position` e o da
junta panda_finger_joint1, nao a abertura entre os dedos. Com hardware falso
a junta vai exatamente aonde mandou e o controlador responde reached_goal
na hora; num Panda de verdade, fechar sobre um cubo PARA antes do alvo, e o
controlador so devolve sucesso se `allow_stalling` for true.
"""
import rclpy

from aula18_moveit import codigos, mensagens
from aula18_moveit.cliente import ClienteMoveIt

PECA_ID = 'peca'
PECA_LADO = 0.04
PECA_ORIGEM = (0.45, -0.30)
PECA_DESTINO = (0.45, 0.30)
ABERTA = 0.035
FECHADA_NO_CUBO = PECA_LADO / 2.0
SUBIDA = 0.10
FOLGA = 0.01     # a pegada fica 1 cm acima do meio do cubo: margem para a palma


def roteiro(origem=PECA_ORIGEM, destino=PECA_DESTINO, lado=PECA_LADO):
    """A lista de passos. Sem ROS 2: o testar.py confere alturas e ordem."""
    z_pega = lado / 2.0 + mensagens.TCP + FOLGA      # panda_link8 na pegada
    z_pre = z_pega + SUBIDA
    ox, oy = origem
    dx, dy = destino
    ready = mensagens.ESTADOS['ready']
    return [
        {'n': 1, 'nome': 'cena', 'tipo': 'cena',
         'objetos': [mensagens.caixa(PECA_ID, (ox, oy, lado / 2.0), (lado, lado, lado))]},
        {'n': 2, 'nome': 'ready', 'tipo': 'juntas', 'valores': ready},
        {'n': 3, 'nome': 'abrir', 'tipo': 'garra', 'posicao': ABERTA},
        {'n': 4, 'nome': 'pre-pegada', 'tipo': 'pose', 'valores': [ox, oy, z_pre]},
        {'n': 5, 'nome': 'pegada', 'tipo': 'pose', 'valores': [ox, oy, z_pega]},
        {'n': 6, 'nome': 'fechar', 'tipo': 'garra', 'posicao': FECHADA_NO_CUBO},
        {'n': 7, 'nome': 'anexar', 'tipo': 'cena',
         'anexados': [mensagens.anexacao(PECA_ID)]},
        {'n': 8, 'nome': 'subir', 'tipo': 'pose', 'valores': [ox, oy, z_pre]},
        {'n': 9, 'nome': 'levar', 'tipo': 'pose', 'valores': [dx, dy, z_pre]},
        {'n': 10, 'nome': 'descer', 'tipo': 'pose', 'valores': [dx, dy, z_pega]},
        {'n': 11, 'nome': 'abrir', 'tipo': 'garra', 'posicao': ABERTA},
        {'n': 12, 'nome': 'soltar', 'tipo': 'cena',
         'anexados': [mensagens.soltura(PECA_ID)]},
        {'n': 13, 'nome': 'recuar', 'tipo': 'pose', 'valores': [dx, dy, z_pre]},
        {'n': 14, 'nome': 'ready', 'tipo': 'juntas', 'valores': ready},
    ]


def cumprir(passos, fazer, log=print, ate=0):
    """Executa os passos em ordem e PARA no primeiro que nao der certo.

    Aqui parar e o certo (o contrario do tres_poses): sem a pegada, anexar
    prende ao robo um cubo que esta no chao. `fazer(passo)` devolve
    (deu_certo, texto). Devolve o numero do ultimo passo cumprido.
    """
    feito = 0
    for p in passos:
        if ate and p['n'] > ate:
            log('parei antes do passo %d, como pedido (ate_passo:=%d)' % (p['n'], ate))
            break
        ok, texto = fazer(p)
        log('passo %2d %-11s %s' % (p['n'], p['nome'], texto))
        if not ok:
            log('parei no passo %d. Os seguintes dependem dele.' % p['n'])
            break
        feito = p['n']
    return feito


class PegarESoltar(ClienteMoveIt):

    def __init__(self):
        super().__init__('pegar_e_soltar')
        self.declare_parameter('ate_passo', 0)
        self.ate = int(self.get_parameter('ate_passo').value)

    def fazer(self, p):
        if p['tipo'] == 'cena':
            ok = self.aplicar_cena(mensagens.cena_diff(p.get('objetos', ()),
                                                        p.get('anexados', ())))
            return ok is True, 'cena: success = %s' % ok
        if p['tipo'] == 'garra':
            ok = self.garra(p['posicao'])
            return ok, 'garra -> %.3f: reached_goal = %s' % (p['posicao'], ok)
        alvo = {'nome': p['nome'], 'tipo': p['tipo'], 'valores': p['valores']}
        r = self.mover(alvo, 'executar')
        texto = 'planejamento %s, execucao %s' % (
            r.situacao(), '-' if r.execucao is None else codigos.descrever(r.execucao))
        return r.executou, texto

    def rodar(self):
        if not self.esperar_move_group() or not self.esperar_garra():
            return 1
        feito = cumprir(roteiro(), self.fazer, log=self.get_logger().info, ate=self.ate)
        self.get_logger().info(
            'ultimo passo cumprido: %d de 14. Isto conta respostas do move_group e do '
            'controlador da garra; se o cubo foi parar onde devia, quem diz e o RViz2.' % feito)
        return 0 if feito == 14 or (self.ate and feito == self.ate) else 1


def main():
    rclpy.init()
    no = PegarESoltar()
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
