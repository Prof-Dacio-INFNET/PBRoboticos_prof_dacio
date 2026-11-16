"""Montagem das mensagens do MoveIt, campo por campo, sem esconder nada.

ADVERTENCIA: escrito SEM ROS 2. Cada campo foi conferido contra as definicoes
da branch humble (URLs abaixo) e o testar.py monta cada mensagem com dubles
que recusam campo inexistente e tipo errado, como as classes geradas pelo
rosidl. No ensaio de 16/11 a caixa, o goal por juntas e o goal por pose
chegaram a um move_group de verdade e foram aceitos; a anexacao, a soltura e
a mensagem da garra ainda nao.

Este modulo nao fala com ninguem: so constroi mensagens. Quem envia e o
`cliente.py`. A separacao existe para que o testar.py possa conferir a
montagem sem ROS 2, e para que voce possa ler, num lugar so, tudo o que um
pedido ao MoveIt carrega.

AS DEFINICOES (moveit_msgs, branch humble = apt 2.2.3):
    https://github.com/moveit/moveit_msgs/blob/humble/action/MoveGroup.action
    https://github.com/moveit/moveit_msgs/blob/humble/msg/MotionPlanRequest.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/Constraints.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/PositionConstraint.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/OrientationConstraint.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/JointConstraint.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/PlanningOptions.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/PlanningScene.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/CollisionObject.msg
    https://github.com/moveit/moveit_msgs/blob/humble/msg/AttachedCollisionObject.msg
    https://github.com/ros2/common_interfaces/blob/humble/shape_msgs/msg/SolidPrimitive.msg

TRES ARMADILHAS DO PYTHON GERADO PELO ROSIDL, todas cobradas no testar.py:

    1. float64 nao aceita int. `pose.position.x = 1` levanta AssertionError
       ("The 'x' field must be of type 'float'"). Tudo aqui passa por float().
    2. `CollisionObject.operation` e do tipo `byte`, que no Python e `bytes`
       de tamanho 1. `objeto.operation = 0` levanta AssertionError; o certo e
       `CollisionObject.ADD` (que vale b'\\x00'). Use SEMPRE a constante.
    3. `SolidPrimitive.dimensions` e float64[<=3]: lista de floats, no maximo 3.
"""
import math

from geometry_msgs.msg import Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (AttachedCollisionObject, CollisionObject, Constraints,
                             JointConstraint, OrientationConstraint, PlanningScene,
                             PositionConstraint)
from shape_msgs.msg import SolidPrimitive

# ---------------------------------------------------------------- o Panda
# Lido no SRDF e no URDF de moveit_resources, branch humble:
#   panda_moveit_config/config/panda_arm.xacro    (grupo panda_arm, estados)
#   panda_moveit_config/config/panda_arm_hand.srdf.xacro (garra, efetuador)
GRUPO = 'panda_arm'          # <chain base_link="panda_link0" tip_link="panda_link8"/>
LINK_EFETUADOR = 'panda_link8'  # a ponta da cadeia, onde a IK do KDL e resolvida
QUADRO = 'panda_link0'       # a base; o demo publica world -> panda_link0 identidade
LINK_MAO = 'panda_hand'      # onde o objeto pego e anexado
DEDOS = ['panda_hand', 'panda_leftfinger', 'panda_rightfinger']
JUNTAS = ['panda_joint%d' % i for i in range(1, 8)]

# Os estados nomeados do SRDF (group_state do grupo panda_arm). `ready` e
# tambem a posicao inicial do ros2_control falso (initial_positions.yaml).
ESTADOS = {
    'ready': [0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
    'extended': [0.0, 0.0, 0.0, 0.0, 0.0, 1.571, 0.785],
    'transport': [0.0, -0.5599, 0.0, -2.97, 0.0, 0.0, 0.785],
}

# A garra "apontando para baixo", alinhada aos eixos: e a orientacao do
# panda_link8 no estado `ready` (conta de cinematica direta no testar.py,
# grupo 6). Em (x, y, z, w).
PARA_BAIXO = (0.92388, -0.38268, 0.0, 0.0)

# Distancia do panda_link8 ao meio dos dedos (0,0584 da base dos dedos + ~0,045
# de dedo). Serve para por a pinca na altura do objeto. Valor do
# panda_hand_tcp das descricoes mais novas do Panda; aproximado.
TCP = 0.1034


def _normalizar(q):
    x, y, z, w = (float(v) for v in q)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-6:
        raise ValueError('quaternio nulo: (%g, %g, %g, %g)' % (x, y, z, w))
    return x / n, y / n, z / n, w / n


def pose(x, y, z, q=(0.0, 0.0, 0.0, 1.0)):
    """geometry_msgs/Pose com tudo em float (armadilha 1)."""
    p = Pose()
    p.position.x, p.position.y, p.position.z = float(x), float(y), float(z)
    qx, qy, qz, qw = _normalizar(q)
    p.orientation.x, p.orientation.y = qx, qy
    p.orientation.z, p.orientation.w = qz, qw
    return p


def restricoes_de_pose(x, y, z, q=PARA_BAIXO, quadro=QUADRO, link=LINK_EFETUADOR,
                       tol_pos=0.005, tol_ang=0.01):
    """O objetivo "ponha o panda_link8 AQUI, virado ASSIM".

    E a mesma montagem do C++ `kinematic_constraints::constructGoalConstraints`
    (moveit_core/kinematic_constraints/src/utils.cpp, branch humble), que e o
    que o MoveGroupInterface faz por baixo do `setPoseTarget`:

      - PositionConstraint: uma ESFERA de raio `tol_pos` centrada no ponto.
        O link tem de terminar dentro dela.
      - OrientationConstraint: o quaternio, com tolerancia `tol_ang` (rad) em
        cada eixo.

    ONDE ESTA A CINEMATICA INVERSA: em lugar nenhum deste arquivo. Voce pede
    uma POSE; o planejador (OMPL) precisa de um ESTADO DAS JUNTAS no fim. Quem
    converte e o amostrador de objetivo do MoveIt, que chama o solver de IK
    configurado em kinematics.yaml (KDL, no Panda) para achar juntas que
    ponham o panda_link8 dentro da esfera -- e descarta as que colidem. Pose
    sem IK, ou com IK so dentro da caixa, nao vira objetivo valido.

    As tolerancias sao mais folgadas que as do MoveGroupInterface (1e-4 m e
    1e-3 rad) de proposito: 5 mm e 0,01 rad nao mudam nada no RViz2 e dao
    margem ao amostrador.
    """
    c = Constraints()
    c.name = 'pose_%s' % link

    pc = PositionConstraint()
    pc.header.frame_id = quadro
    pc.link_name = link
    pc.target_point_offset.x = 0.0
    pc.target_point_offset.y = 0.0
    pc.target_point_offset.z = 0.0
    esfera = SolidPrimitive()
    esfera.type = SolidPrimitive.SPHERE
    esfera.dimensions = [float(tol_pos)]
    pc.constraint_region.primitives.append(esfera)
    # A orientacao da regiao nao importa (e uma esfera); vai a identidade.
    pc.constraint_region.primitive_poses.append(pose(x, y, z))
    pc.weight = 1.0
    c.position_constraints.append(pc)

    oc = OrientationConstraint()
    oc.header.frame_id = quadro
    oc.link_name = link
    qx, qy, qz, qw = _normalizar(q)
    oc.orientation.x, oc.orientation.y = qx, qy
    oc.orientation.z, oc.orientation.w = qz, qw
    oc.absolute_x_axis_tolerance = float(tol_ang)
    oc.absolute_y_axis_tolerance = float(tol_ang)
    oc.absolute_z_axis_tolerance = float(tol_ang)
    oc.weight = 1.0
    c.orientation_constraints.append(oc)
    return c


def restricoes_de_juntas(valores, nomes=JUNTAS, tol=0.01):
    """O objetivo "ponha as juntas NESTES angulos" -- sem IK nenhuma.

    E a outra forma de objetivo, e e o que o botao de estado nomeado (`ready`)
    do RViz2 faz. Aqui nao ha cinematica inversa: o objetivo ja esta no
    espaco das juntas, e o planejador so procura o caminho.
    """
    if len(valores) != len(nomes):
        raise ValueError('%d valores para %d juntas' % (len(valores), len(nomes)))
    c = Constraints()
    c.name = 'juntas'
    for n, v in zip(nomes, valores):
        jc = JointConstraint()
        jc.joint_name = n
        jc.position = float(v)
        jc.tolerance_above = float(tol)
        jc.tolerance_below = float(tol)
        jc.weight = 1.0
        c.joint_constraints.append(jc)
    return c


def pedido(restricoes, so_planejar=True, grupo=GRUPO, tempo=5.0, tentativas=1,
           velocidade=0.5, aceleracao=0.5):
    """O goal da acao moveit_msgs/action/MoveGroup (servidor /move_action).

    Espelha o que o MoveGroupInterface do Humble monta em `plan()`
    (moveit_ros/planning_interface/move_group_interface/src/
    move_group_interface.cpp): estado inicial = o ATUAL (RobotState vazio com
    is_diff = True), cena = sem mudanca (PlanningScene vazio com is_diff =
    True), sem replanejar, sem "olhar em volta".

    `so_planejar` vira `planning_options.plan_only`: True devolve a
    trajetoria e NAO mexe o robo; False planeja e executa no mesmo pedido.

    `pipeline_id` e `planner_id` vazios: o pipeline padrao do demo do Panda
    (ompl) e o planejador padrao dele.
    """
    g = MoveGroup.Goal()
    r = g.request
    r.group_name = grupo
    r.goal_constraints.append(restricoes)
    r.start_state.is_diff = True
    r.num_planning_attempts = int(tentativas)
    r.allowed_planning_time = float(tempo)
    r.max_velocity_scaling_factor = float(velocidade)
    r.max_acceleration_scaling_factor = float(aceleracao)
    r.pipeline_id = ''
    r.planner_id = ''

    o = g.planning_options
    o.plan_only = bool(so_planejar)
    o.look_around = False
    o.replan = False
    o.planning_scene_diff.is_diff = True
    o.planning_scene_diff.robot_state.is_diff = True
    return g


# ------------------------------------------------------------------ a cena

def caixa(ident, centro, tamanho, quadro=QUADRO):
    """CollisionObject com UMA caixa, operacao ADD.

    `centro` e o meio da caixa (nao o canto), em metros, no `quadro`.
    `tamanho` e (x, y, z) -- a caixa INTEIRA, nao a metade.
    """
    o = CollisionObject()
    o.header.frame_id = quadro
    o.id = ident
    forma = SolidPrimitive()
    forma.type = SolidPrimitive.BOX
    forma.dimensions = [float(v) for v in tamanho]
    o.primitives.append(forma)
    o.primitive_poses.append(pose(*centro))
    o.operation = CollisionObject.ADD          # armadilha 2: nunca o numero 0
    return o


def remocao(ident, quadro=QUADRO):
    """CollisionObject que so diz "tire o objeto `ident` do mundo"."""
    o = CollisionObject()
    o.header.frame_id = quadro
    o.id = ident
    o.operation = CollisionObject.REMOVE
    return o


def anexacao(ident, link=LINK_MAO, toque=DEDOS):
    """AttachedCollisionObject que pega um objeto QUE JA ESTA NO MUNDO.

    O objeto vai sem geometria nenhuma, so com o id e ADD. Lido em
    moveit_core/planning_scene/src/planning_scene.cpp (humble),
    processAttachedCollisionObjectMsg: ADD sem primitivas e sem malhas, com um
    objeto de mesmo id no mundo, usa a geometria do mundo, prende o objeto ao
    link na posicao em que ele esta e o TIRA do mundo -- tudo numa mensagem.

    `touch_links`: os links que podem encostar no objeto sem isso contar como
    colisao. Sem os dedos aqui, a garra fechada sobre o cubo e uma colisao, e
    o planejamento seguinte falha com START_STATE_IN_COLLISION.
    """
    a = AttachedCollisionObject()
    a.link_name = link
    a.object.id = ident
    a.object.header.frame_id = link
    a.object.operation = CollisionObject.ADD
    a.touch_links = list(toque)
    return a


def soltura(ident, link=LINK_MAO):
    """AttachedCollisionObject que solta: operacao REMOVE.

    Mesma fonte: o REMOVE de um objeto anexado o desprende e o devolve ao
    mundo NA POSICAO EM QUE ELE ESTA -- ele nao some, fica onde a garra o
    deixou. (Se ja houver no mundo um objeto com o mesmo id, ele NAO e
    devolvido, e o move_group avisa no log.)
    """
    a = AttachedCollisionObject()
    a.link_name = link
    a.object.id = ident
    a.object.header.frame_id = link
    a.object.operation = CollisionObject.REMOVE
    return a


def cena_diff(objetos=(), anexados=()):
    """PlanningScene de DIFERENCA: so o que muda, o resto fica como esta.

    `is_diff = True` nao e detalhe. Lido em planning_scene_monitor.cpp
    (newPlanningSceneMessage, humble): uma cena com is_diff = False SUBSTITUI
    a cena inteira -- e a caixa de outro terminal some sem aviso.
    """
    s = PlanningScene()
    s.is_diff = True
    s.robot_state.is_diff = True
    for o in objetos:
        s.world.collision_objects.append(o)
    for a in anexados:
        s.robot_state.attached_collision_objects.append(a)
    return s


# ------------------------------------------------------- lendo o resultado

def pontos(trajetoria):
    """Numero de pontos de uma moveit_msgs/RobotTrajectory."""
    return len(trajetoria.joint_trajectory.points)


def comprimento_juntas(trajetoria):
    """Soma de |delta| das juntas ao longo da trajetoria, em radianos.

    E a medida mais simples de "a trajetoria mudou": o mesmo par de poses,
    com e sem a caixa, da comprimentos diferentes, porque o caminho desviou.
    Tambem muda entre duas execucoes SEM mudar nada -- o OMPL e aleatorio.
    """
    pts = trajetoria.joint_trajectory.points
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        total += math.sqrt(sum((float(vb) - float(va)) ** 2
                               for va, vb in zip(a.positions, b.positions)))
    return total


def duracao(trajetoria):
    """Tempo do ultimo ponto (time_from_start), em segundos."""
    pts = trajetoria.joint_trajectory.points
    if not pts:
        return 0.0
    t = pts[-1].time_from_start
    return float(t.sec) + float(t.nanosec) * 1e-9
