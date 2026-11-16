#!/usr/bin/env python3
"""Confere o exemplo da Aula 18 antes de alguem confiar nele. Sem ROS 2.

    python3 testar.py
    python3 testar.py --fonte /caminho/de/um/clone/moveit_msgs   # opcional

Nove grupos (e um decimo opcional), todos com a resposta sabida de antemao.
Aqui nao ha ROS 2 nem MoveIt: tudo o que depende deles roda contra DUBLES.
O que isso prova e o que NAO prova esta no README, em "O que foi e o que nao
foi verificado" -- e a separacao e o ponto.

Os dubles das mensagens nao sao enfeite: eles sao gerados a partir das
definicoes .msg da branch humble (copiadas abaixo, com as URLs) e se
comportam como as classes que o rosidl gera para o Python -- recusam campo
que nao existe, float64 que recebe int e `byte` que recebe numero. Sao
exatamente os tres erros que um script escrito sem ROS 2 costuma ter, e que
so apareceriam no ensaio, com a turma olhando.

`--fonte DIR` (grupo 10) compara as definicoes copiadas aqui com as de um
clone de https://github.com/moveit/moveit_msgs (branch humble). Sem ele, o
grupo 10 e pulado e o teste diz isso.
"""
import ast
import math
import pathlib
import py_compile
import re
import sys
import tempfile
import time
import types
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True      # nada de __pycache__ no material

AQUI = pathlib.Path(__file__).resolve().parent
PACOTE = AQUI / 'aula18_moveit'
MODULOS = PACOTE / 'aula18_moveit'

falhas = []


def conferir(nome, ok, detalhe=''):
    print('  %s  %s%s' % ('ok  ' if ok else 'FALHA', nome,
                          '  -- ' + detalhe if detalhe else ''))
    if not ok:
        falhas.append(nome)


def levanta(f, *a, **kw):
    """True se f(*a) levantar AssertionError, AttributeError, ValueError ou TypeError."""
    try:
        f(*a, **kw)
    except (AssertionError, AttributeError, ValueError, TypeError):
        return True
    return False


t_inicio = time.perf_counter()
FONTES = sorted(AQUI.rglob('*.py'))

# ---------------------------------------------------------------------- 1
print('1. todo .py: sintaxe, ASCII, 99 colunas, e ADVERTENCIA onde nunca rodou')
tmp = pathlib.Path(tempfile.mkdtemp(prefix='aula18-'))
for f in FONTES:
    texto = f.read_text(encoding='utf-8')
    rel = f.relative_to(AQUI)
    try:
        ast.parse(texto, filename=str(f))
        py_compile.compile(str(f), cfile=str(tmp / (f.stem + '.pyc')), doraise=True)
        sint = True
    except (SyntaxError, py_compile.PyCompileError):
        sint = False
    largas = [i for i, l in enumerate(texto.splitlines(), 1) if len(l) > 99]
    nao_ascii = [i for i, l in enumerate(texto.splitlines(), 1)
                 if any(ord(c) > 127 for c in l)]
    conferir('%s: compila, ASCII, <= 99 colunas' % rel,
             sint and not largas and not nao_ascii,
             'linhas largas %s, nao-ASCII %s' % (largas[:3], nao_ascii[:3])
             if (largas or nao_ascii) else '')
NUNCA_RODARAM = ['codigos.py', 'mensagens.py', 'sequencia.py', 'cliente.py', 'cena.py',
                 'tres_poses.py', 'pegar_e_soltar.py']
for nome in NUNCA_RODARAM:
    doc = ast.get_docstring(ast.parse((MODULOS / nome).read_text(encoding='utf-8'))) or ''
    conferir('%s tem ADVERTENCIA na docstring' % nome, 'ADVERTENCIA' in doc)

# ---------------------------------------------------------------------- 2
print('2. o pacote: package.xml, setup.py, setup.cfg e os imports declarados')
raiz = ET.parse(PACOTE / 'package.xml').getroot()
conferir('package.xml e XML bem formado, formato 3, nome aula18_moveit',
         raiz.get('format') == '3' and raiz.findtext('name') == 'aula18_moveit')
conferir('build_type ament_python',
         raiz.findtext('export/build_type') == 'ament_python')
deps = {e.text for e in raiz if e.tag in ('depend', 'exec_depend')}
PEDIDAS = {'rclpy', 'moveit_msgs', 'shape_msgs', 'geometry_msgs', 'control_msgs',
           'moveit_resources_panda_moveit_config', 'moveit_ros_move_group'}
conferir('exec_depend tem as 7 dependencias', PEDIDAS <= deps,
         'faltam %s' % sorted(PEDIDAS - deps) if not PEDIDAS <= deps else '')
importados = set()
for f in MODULOS.glob('*.py'):
    for no in ast.walk(ast.parse(f.read_text(encoding='utf-8'))):
        if isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            importados.add(no.module.split('.')[0])
        elif isinstance(no, ast.Import):
            importados.update(a.name.split('.')[0] for a in no.names)
ros = importados - {'math', 'time', 'aula18_moveit', 'sys'}
conferir('todo pacote ROS importado esta no package.xml', ros <= deps,
         'importados %s; sem declarar %s' % (sorted(ros), sorted(ros - deps)))
setup_txt = (PACOTE / 'setup.py').read_text(encoding='utf-8')
pontos_entrada = re.findall(r"'(\w+) = aula18_moveit\.(\w+):main'", setup_txt)
conferir('setup.py declara cena, tres_poses e pegar_e_soltar',
         sorted(p[0] for p in pontos_entrada) == ['cena', 'pegar_e_soltar', 'tres_poses'])
for exe, mod in pontos_entrada:
    arv = ast.parse((MODULOS / (mod + '.py')).read_text(encoding='utf-8'))
    tem_main = any(isinstance(n, ast.FunctionDef) and n.name == 'main' for n in arv.body)
    conferir('entry point %s -> %s.py tem main()' % (exe, mod), tem_main)
cfg = (PACOTE / 'setup.cfg').read_text(encoding='utf-8')
conferir('setup.cfg instala em lib/aula18_moveit (ros2 run acha)',
         cfg.count('$base/lib/aula18_moveit') == 2)
conferir('resource/aula18_moveit existe', (PACOTE / 'resource' / 'aula18_moveit').is_file())
conferir('nenhum __pycache__ no exemplo', not list(AQUI.rglob('__pycache__')))

# ---------------------------------------------------------------------- 3
print('3. os codigos de erro: a tabela e a da fonte, e a traducao funciona')
sys.path.insert(0, str(PACOTE))
from aula18_moveit import codigos  # noqa: E402  (sem ROS 2: importa direto)

# Copia de moveit_msgs/msg/MoveItErrorCodes.msg, branch humble (2.2.3):
# https://github.com/moveit/moveit_msgs/blob/humble/msg/MoveItErrorCodes.msg
SPEC_CODIGOS = (
    'SUCCESS=1 FAILURE=99999 PLANNING_FAILED=-1 INVALID_MOTION_PLAN=-2 '
    'MOTION_PLAN_INVALIDATED_BY_ENVIRONMENT_CHANGE=-3 CONTROL_FAILED=-4 '
    'UNABLE_TO_AQUIRE_SENSOR_DATA=-5 TIMED_OUT=-6 PREEMPTED=-7 '
    'START_STATE_IN_COLLISION=-10 START_STATE_VIOLATES_PATH_CONSTRAINTS=-11 '
    'START_STATE_INVALID=-26 GOAL_IN_COLLISION=-12 GOAL_VIOLATES_PATH_CONSTRAINTS=-13 '
    'GOAL_CONSTRAINTS_VIOLATED=-14 GOAL_STATE_INVALID=-27 UNRECOGNIZED_GOAL_TYPE=-28 '
    'INVALID_GROUP_NAME=-15 INVALID_GOAL_CONSTRAINTS=-16 INVALID_ROBOT_STATE=-17 '
    'INVALID_LINK_NAME=-18 INVALID_OBJECT_NAME=-19 FRAME_TRANSFORM_FAILURE=-21 '
    'COLLISION_CHECKING_UNAVAILABLE=-22 ROBOT_STATE_STALE=-23 SENSOR_INFO_STALE=-24 '
    'COMMUNICATION_FAILURE=-25 CRASH=-29 ABORT=-30 NO_IK_SOLUTION=-31')
esperado = {int(v): k for k, v in (p.split('=') for p in SPEC_CODIGOS.split())}
conferir('as 30 constantes do Humble, nem uma a mais', codigos.CODIGOS == esperado,
         '%d na tabela' % len(codigos.CODIGOS))
conferir('-27 -> GOAL_STATE_INVALID, 1 -> SUCCESS, -1 -> PLANNING_FAILED',
         codigos.nome(-27) == 'GOAL_STATE_INVALID' and codigos.nome(1) == 'SUCCESS'
         and codigos.nome(-1) == 'PLANNING_FAILED')
conferir('codigo desconhecido nao quebra: -400 -> CODIGO_-400, None -> CODIGO_?',
         codigos.nome(-400) == 'CODIGO_-400' and codigos.nome(None) == 'CODIGO_?')
conferir('descrever(-6) == "TIMED_OUT (-6)"', codigos.descrever(-6) == 'TIMED_OUT (-6)')
conferir('os dois codigos locais ficam fora da faixa do MoveIt e fora da tabela',
         codigos.EXEC_RECUSADA not in esperado and codigos.EXEC_SEM_RESPOSTA not in esperado
         and codigos.nome(codigos.EXEC_SEM_RESPOSTA) == 'EXECUCAO_SEM_RESPOSTA')
nomes_validos = set(esperado.values()) | set(codigos.LOCAIS.values())
conferir('toda DICA e de um codigo que existe', set(codigos.DICAS) <= nomes_validos,
         str(sorted(set(codigos.DICAS) - nomes_validos)))
conferir('os codigos que o caminho OMPL devolve tem dica',
         all(n in codigos.DICAS for n in ('PLANNING_FAILED', 'TIMED_OUT', 'GOAL_STATE_INVALID',
                                         'START_STATE_IN_COLLISION', 'CONTROL_FAILED')))
VEREDITO = re.compile(r'\b(ok|OK|correto|aprovad[oa]|reprovad[oa])\b')
conferir('nenhuma dica da veredito (ok/correto/aprovado)',
         not any(VEREDITO.search(d) for d in codigos.DICAS.values()))

# ---------------------------------------------------------------------- dubles
# As definicoes, sem comentarios, copiadas da branch humble:
#   https://github.com/moveit/moveit_msgs/tree/humble/msg  (e action/, srv/)
#   https://github.com/ros2/common_interfaces/tree/humble  (geometry, std, shape,
#                                                          trajectory)
#   https://github.com/ros2/rcl_interfaces/tree/humble/builtin_interfaces/msg
#   https://github.com/ros-controls/control_msgs/tree/humble/control_msgs
# Tipo que nao esta aqui (octomap, sensor_msgs/JointState, ...) vira um
# objeto opaco: este exemplo nao toca neles.
SPECS = {
    'builtin_interfaces/Time': 'int32 sec; uint32 nanosec',
    'builtin_interfaces/Duration': 'int32 sec; uint32 nanosec',
    'std_msgs/Header': 'builtin_interfaces/Time stamp; string frame_id',
    'geometry_msgs/Point': 'float64 x; float64 y; float64 z',
    'geometry_msgs/Vector3': 'float64 x; float64 y; float64 z',
    'geometry_msgs/Quaternion': 'float64 x 0; float64 y 0; float64 z 0; float64 w 1',
    'geometry_msgs/Pose': 'Point position; Quaternion orientation',
    'shape_msgs/SolidPrimitive': (
        'uint8 BOX=1; uint8 SPHERE=2; uint8 CYLINDER=3; uint8 CONE=4; uint8 PRISM=5; '
        'uint8 type; float64[<=3] dimensions; uint8 BOX_X=0; uint8 BOX_Y=1; uint8 BOX_Z=2; '
        'uint8 SPHERE_RADIUS=0; uint8 CYLINDER_HEIGHT=0; uint8 CYLINDER_RADIUS=1; '
        'uint8 CONE_HEIGHT=0; uint8 CONE_RADIUS=1; uint8 PRISM_HEIGHT=0; '
        'geometry_msgs/Polygon polygon'),
    'trajectory_msgs/JointTrajectory': (
        'std_msgs/Header header; string[] joint_names; JointTrajectoryPoint[] points'),
    'trajectory_msgs/JointTrajectoryPoint': (
        'float64[] positions; float64[] velocities; float64[] accelerations; '
        'float64[] effort; builtin_interfaces/Duration time_from_start'),
    'control_msgs/GripperCommand': 'float64 position; float64 max_effort',
    'control_msgs/GripperCommand_Goal': 'GripperCommand command',
    'control_msgs/GripperCommand_Result': (
        'float64 position; float64 effort; bool stalled; bool reached_goal'),
    'control_msgs/GripperCommand_Feedback': (
        'float64 position; float64 effort; bool stalled; bool reached_goal'),
    'moveit_msgs/MotionPlanRequest': (
        'WorkspaceParameters workspace_parameters; RobotState start_state; '
        'Constraints[] goal_constraints; Constraints path_constraints; '
        'TrajectoryConstraints trajectory_constraints; '
        'GenericTrajectory[] reference_trajectories; string pipeline_id; string planner_id; '
        'string group_name; int32 num_planning_attempts; float64 allowed_planning_time; '
        'float64 max_velocity_scaling_factor; float64 max_acceleration_scaling_factor; '
        'string cartesian_speed_end_effector_link; float64 max_cartesian_speed'),
    'moveit_msgs/WorkspaceParameters': (
        'std_msgs/Header header; geometry_msgs/Vector3 min_corner; '
        'geometry_msgs/Vector3 max_corner'),
    'moveit_msgs/RobotState': (
        'sensor_msgs/JointState joint_state; sensor_msgs/MultiDOFJointState '
        'multi_dof_joint_state; AttachedCollisionObject[] attached_collision_objects; '
        'bool is_diff'),
    'moveit_msgs/Constraints': (
        'string name; JointConstraint[] joint_constraints; '
        'PositionConstraint[] position_constraints; '
        'OrientationConstraint[] orientation_constraints; '
        'VisibilityConstraint[] visibility_constraints'),
    'moveit_msgs/JointConstraint': (
        'string joint_name; float64 position; float64 tolerance_above; '
        'float64 tolerance_below; float64 weight'),
    'moveit_msgs/PositionConstraint': (
        'std_msgs/Header header; string link_name; geometry_msgs/Vector3 target_point_offset; '
        'BoundingVolume constraint_region; float64 weight'),
    'moveit_msgs/OrientationConstraint': (
        'std_msgs/Header header; geometry_msgs/Quaternion orientation; string link_name; '
        'float64 absolute_x_axis_tolerance; float64 absolute_y_axis_tolerance; '
        'float64 absolute_z_axis_tolerance; uint8 parameterization; '
        'uint8 XYZ_EULER_ANGLES=0; uint8 ROTATION_VECTOR=1; float64 weight'),
    'moveit_msgs/BoundingVolume': (
        'shape_msgs/SolidPrimitive[] primitives; geometry_msgs/Pose[] primitive_poses; '
        'shape_msgs/Mesh[] meshes; geometry_msgs/Pose[] mesh_poses'),
    'moveit_msgs/PlanningOptions': (
        'PlanningScene planning_scene_diff; bool plan_only; bool look_around; '
        'int32 look_around_attempts; float64 max_safe_execution_cost; bool replan; '
        'int32 replan_attempts; float64 replan_delay'),
    'moveit_msgs/PlanningScene': (
        'string name; RobotState robot_state; string robot_model_name; '
        'geometry_msgs/TransformStamped[] fixed_frame_transforms; '
        'AllowedCollisionMatrix allowed_collision_matrix; LinkPadding[] link_padding; '
        'LinkScale[] link_scale; ObjectColor[] object_colors; PlanningSceneWorld world; '
        'bool is_diff'),
    'moveit_msgs/PlanningSceneWorld': (
        'CollisionObject[] collision_objects; octomap_msgs/OctomapWithPose octomap'),
    'moveit_msgs/CollisionObject': (
        'std_msgs/Header header; geometry_msgs/Pose pose; string id; '
        'object_recognition_msgs/ObjectType type; shape_msgs/SolidPrimitive[] primitives; '
        'geometry_msgs/Pose[] primitive_poses; shape_msgs/Mesh[] meshes; '
        'geometry_msgs/Pose[] mesh_poses; shape_msgs/Plane[] planes; '
        'geometry_msgs/Pose[] plane_poses; string[] subframe_names; '
        'geometry_msgs/Pose[] subframe_poses; byte ADD=0; byte REMOVE=1; byte APPEND=2; '
        'byte MOVE=3; byte operation'),
    'moveit_msgs/AttachedCollisionObject': (
        'string link_name; CollisionObject object; string[] touch_links; '
        'trajectory_msgs/JointTrajectory detach_posture; float64 weight'),
    'moveit_msgs/MoveItErrorCodes': 'int32 val',
    'moveit_msgs/RobotTrajectory': (
        'trajectory_msgs/JointTrajectory joint_trajectory; '
        'trajectory_msgs/MultiDOFJointTrajectory multi_dof_joint_trajectory'),
    'moveit_msgs/MoveGroup_Goal': 'MotionPlanRequest request; PlanningOptions planning_options',
    'moveit_msgs/MoveGroup_Result': (
        'MoveItErrorCodes error_code; moveit_msgs/RobotState trajectory_start; '
        'moveit_msgs/RobotTrajectory planned_trajectory; '
        'moveit_msgs/RobotTrajectory executed_trajectory; float64 planning_time'),
    'moveit_msgs/MoveGroup_Feedback': 'string state',
    'moveit_msgs/ExecuteTrajectory_Goal': 'RobotTrajectory trajectory',
    'moveit_msgs/ExecuteTrajectory_Result': 'MoveItErrorCodes error_code',
    'moveit_msgs/ExecuteTrajectory_Feedback': 'string state',
    'moveit_msgs/ApplyPlanningScene_Request': 'PlanningScene scene',
    'moveit_msgs/ApplyPlanningScene_Response': 'bool success',
}
PRIMITIVOS = {'float64': float, 'float32': float, 'int32': int, 'uint32': int, 'int16': int,
              'uint8': int, 'int8': int, 'int64': int, 'uint64': int, 'bool': bool,
              'string': str, 'byte': bytes}
CLASSES = {}


class _Opaco:
    """Tipo que o exemplo nunca toca: so precisa existir."""


def _parse(nome):
    pkg = nome.split('/')[0]
    campos, consts = [], {}
    for item in SPECS[nome].split(';'):
        partes = item.split()
        tipo, resto = partes[0], partes[1]
        if '=' in resto:
            n, v = resto.split('=')
            consts[n] = bytes([int(v)]) if tipo == 'byte' else PRIMITIVOS[tipo](int(v))
            continue
        padrao = float(partes[2]) if len(partes) > 2 else None
        seq, limite = False, None
        m = re.match(r'(.+)\[(<=)?(\d*)\]$', tipo)
        if m:
            tipo, seq = m.group(1), True
            limite = int(m.group(3)) if m.group(3) else None
        if tipo not in PRIMITIVOS and '/' not in tipo:
            tipo = pkg + '/' + tipo
        campos.append((resto, tipo, seq, limite, padrao))
    return campos, consts


def _tipo_ok(tipo, v):
    if tipo in PRIMITIVOS:
        py = PRIMITIVOS[tipo]
        if py is bytes:
            return isinstance(v, bytes) and len(v) == 1
        if py is int:
            return isinstance(v, int) and not isinstance(v, float)
        return isinstance(v, py)
    if tipo in SPECS:
        return isinstance(v, classe(tipo))
    return isinstance(v, _Opaco)


def classe(nome):
    """A classe-duble de `pkg/Nome`, gerada uma vez a partir de SPECS."""
    if nome in CLASSES:
        return CLASSES[nome]
    campos, consts = _parse(nome)
    tabela = {c[0]: c for c in campos}

    def __init__(self):
        for n, tipo, seq, _lim, padrao in campos:
            if seq:
                v = []
            elif tipo in PRIMITIVOS:
                py = PRIMITIVOS[tipo]
                v = (b'\x00' if py is bytes else
                     py(padrao) if padrao is not None else py())
            elif tipo in SPECS:
                v = classe(tipo)()
            else:
                v = _Opaco()
            object.__setattr__(self, n, v)

    def __setattr__(self, n, v):
        if n not in tabela:
            raise AttributeError('%s nao tem o campo %r' % (nome, n))
        _n, tipo, seq, lim, _p = tabela[n]
        if seq:
            ok = (isinstance(v, (list, tuple)) and (lim is None or len(v) <= lim)
                  and all(_tipo_ok(tipo, e) for e in v))
            v = list(v) if ok else v
        else:
            ok = _tipo_ok(tipo, v)
        if not ok:
            raise AssertionError("The '%s' field of %s got %r" % (n, nome, v))
        object.__setattr__(self, n, v)

    atributos = {'__init__': __init__, '__setattr__': __setattr__,
                 '__slots__': tuple(tabela), '_campos': campos}
    atributos.update(consts)
    cls = type(nome.split('/')[1], (), atributos)
    CLASSES[nome] = cls
    return cls


def _modulo(nome, **attrs):
    mod = types.ModuleType(nome)
    mod.__dict__.update(attrs)
    return mod


def _acao(pkg, nome):
    return types.SimpleNamespace(Goal=classe('%s/%s_Goal' % (pkg, nome)),
                                 Result=classe('%s/%s_Result' % (pkg, nome)),
                                 Feedback=classe('%s/%s_Feedback' % (pkg, nome)))


# ---- dubles do rclpy: um "mundo" com servidores e respostas roteirizadas

class _Futuro:
    def __init__(self, valor=None, pronto=True):
        self._valor, self._pronto = valor, pronto

    def done(self):
        return self._pronto

    def result(self):
        return self._valor if self._pronto else None


class _Mundo:
    """Quem esta no ar e o que cada servidor responde, em ordem."""

    def __init__(self):
        self.no_ar = set()
        self.respostas = {}     # nome -> lista de ('recusa'|'sem_resposta'|resultado)
        self.enviados = {}      # nome -> lista de goals/requests
        self.ordem = []         # (nome, pedido) na ordem em que chegaram, de todos

    def proxima(self, nome, pedido):
        self.enviados.setdefault(nome, []).append(pedido)
        self.ordem.append((nome, pedido))
        fila = self.respostas.get(nome, [])
        return fila.pop(0) if fila else 'sem_resposta'


MUNDO = _Mundo()


class _Punho:
    def __init__(self, aceito, resposta):
        self.accepted = aceito
        self._resposta = resposta
        self.cancelado = False

    def get_result_async(self):
        if self._resposta == 'sem_resposta':
            return _Futuro(pronto=False)
        return _Futuro(types.SimpleNamespace(result=self._resposta, status=4))

    def cancel_goal_async(self):
        self.cancelado = True
        return _Futuro()


class _ActionClient:
    def __init__(self, no, tipo, nome):
        self.tipo, self.nome = tipo, nome

    def wait_for_server(self, timeout_sec=None):
        return self.nome in MUNDO.no_ar

    def send_goal_async(self, goal, feedback_callback=None):
        assert isinstance(goal, self.tipo.Goal), 'goal de tipo errado para ' + self.nome
        r = MUNDO.proxima(self.nome, goal)
        if r == 'recusa':
            return _Futuro(_Punho(False, None))
        return _Futuro(_Punho(True, r))


class _ServiceClient:
    def __init__(self, tipo, nome):
        self.tipo, self.nome = tipo, nome

    def wait_for_service(self, timeout_sec=None):
        return self.nome in MUNDO.no_ar

    def call_async(self, req):
        assert isinstance(req, self.tipo.Request), 'request de tipo errado'
        r = MUNDO.proxima(self.nome, req)
        if r == 'sem_resposta':
            return _Futuro(pronto=False)
        return _Futuro(r)


class _Log:
    def __init__(self):
        self.linhas = []

    def info(self, s):
        self.linhas.append(str(s))

    warn = error = warning = info


class _Node:
    parametros = {}

    def __init__(self, nome):
        self._par, self.log = {}, _Log()

    def declare_parameter(self, nome, valor):
        self._par[nome] = _Node.parametros.get(nome, valor)

    def get_parameter(self, nome):
        return types.SimpleNamespace(value=self._par[nome])

    def get_logger(self):
        return self.log

    def create_client(self, tipo, nome):
        return _ServiceClient(tipo, nome)

    def destroy_node(self):
        pass


def _apply_srv():
    return types.SimpleNamespace(Request=classe('moveit_msgs/ApplyPlanningScene_Request'),
                                 Response=classe('moveit_msgs/ApplyPlanningScene_Response'))


MSG_MOVEIT = {n.split('/')[1]: classe(n) for n in SPECS
              if n.startswith('moveit_msgs/') and '_' not in n.split('/')[1]}
dubles = {
    'rclpy': _modulo('rclpy', init=lambda: None, ok=lambda: False, shutdown=lambda: None,
                     spin_until_future_complete=lambda no, fut, timeout_sec=None: None),
    'rclpy.node': _modulo('rclpy.node', Node=_Node),
    'rclpy.action': _modulo('rclpy.action', ActionClient=_ActionClient),
    'geometry_msgs': _modulo('geometry_msgs'),
    'geometry_msgs.msg': _modulo('geometry_msgs.msg', Pose=classe('geometry_msgs/Pose')),
    'shape_msgs': _modulo('shape_msgs'),
    'shape_msgs.msg': _modulo('shape_msgs.msg',
                              SolidPrimitive=classe('shape_msgs/SolidPrimitive')),
    'moveit_msgs': _modulo('moveit_msgs'),
    'moveit_msgs.msg': _modulo('moveit_msgs.msg', **MSG_MOVEIT),
    'moveit_msgs.action': _modulo('moveit_msgs.action',
                                  MoveGroup=_acao('moveit_msgs', 'MoveGroup'),
                                  ExecuteTrajectory=_acao('moveit_msgs', 'ExecuteTrajectory')),
    'moveit_msgs.srv': _modulo('moveit_msgs.srv', ApplyPlanningScene=_apply_srv()),
    'control_msgs': _modulo('control_msgs'),
    'control_msgs.action': _modulo('control_msgs.action',
                                   GripperCommand=_acao('control_msgs', 'GripperCommand')),
}
sys.modules.update(dubles)
from aula18_moveit import mensagens, sequencia  # noqa: E402
from aula18_moveit import cliente, cena, tres_poses, pegar_e_soltar  # noqa: E402

# ---------------------------------------------------------------------- 4
print('4. as mensagens, montadas contra dubles que mordem como o rosidl')
Pose = classe('geometry_msgs/Pose')
p = Pose()
conferir('o duble morde: float64 recusa int (pose.position.x = 1)',
         levanta(setattr, p.position, 'x', 1))
conferir('o duble morde: campo inexistente (pose.posicao)', levanta(setattr, p, 'posicao', 1))
CO = MSG_MOVEIT['CollisionObject']
conferir('o duble morde: byte recusa o numero 0 (operation = 0)',
         levanta(setattr, CO(), 'operation', 0))
conferir('Quaternion nasce com w = 1, como no Humble', Pose().orientation.w == 1.0)

c = mensagens.restricoes_de_pose(0.45, 0.30, 0.35)
pc, oc = c.position_constraints[0], c.orientation_constraints[0]
esf = pc.constraint_region.primitives[0]
conferir('pose: 1 PositionConstraint + 1 OrientationConstraint, nenhuma de junta',
         len(c.position_constraints) == 1 and len(c.orientation_constraints) == 1
         and not c.joint_constraints)
conferir('posicao: panda_link8 em panda_link0, esfera de 5 mm no ponto pedido',
         pc.link_name == 'panda_link8' and pc.header.frame_id == 'panda_link0'
         and esf.type == 2 and esf.dimensions == [0.005]
         and pc.constraint_region.primitive_poses[0].position.y == 0.30
         and pc.weight == 1.0)
q = oc.orientation
conferir('orientacao: garra para baixo, quaternio unitario, 0,01 rad nos 3 eixos',
         oc.link_name == 'panda_link8' and abs(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w
                                               - 1) < 1e-9
         and abs(q.x - 0.92388) < 1e-4 and abs(q.y + 0.38268) < 1e-4
         and oc.absolute_x_axis_tolerance == oc.absolute_z_axis_tolerance == 0.01)
conferir('quaternio nulo e recusado com mensagem',
         levanta(mensagens.restricoes_de_pose, 0.4, 0, 0.4, (0, 0, 0, 0)))
j = mensagens.restricoes_de_juntas(mensagens.ESTADOS['ready'])
conferir('juntas: 7 JointConstraint, panda_joint1..7, valores do `ready`',
         [k.joint_name for k in j.joint_constraints] == mensagens.JUNTAS
         and j.joint_constraints[3].position == -2.356 and not j.position_constraints)
conferir('juntas com numero errado de valores e recusado',
         levanta(mensagens.restricoes_de_juntas, [0.0] * 6))
g = mensagens.pedido(c, so_planejar=True, tempo=5, tentativas=1)
r = g.request
conferir('pedido: grupo panda_arm, 1 objetivo, 5 s, inicio = estado atual (is_diff)',
         r.group_name == 'panda_arm' and len(r.goal_constraints) == 1
         and r.allowed_planning_time == 5.0 and r.start_state.is_diff
         and not r.start_state.attached_collision_objects)
conferir('pedido: plan_only True, cena de diferenca vazia, sem replan',
         g.planning_options.plan_only and g.planning_options.planning_scene_diff.is_diff
         and g.planning_options.planning_scene_diff.robot_state.is_diff
         and not g.planning_options.replan and not g.planning_options.look_around)
conferir('pedido direto: plan_only False',
         not mensagens.pedido(c, so_planejar=False).planning_options.plan_only)
cx = cena.diff_adicionar()
obj = cx.world.collision_objects[0]
conferir('caixa: cena de DIFERENCA, um objeto "caixa", ADD (b"\\x00"), BOX 0,1x0,2x0,4',
         cx.is_diff and cx.robot_state.is_diff and obj.id == 'caixa'
         and obj.operation == CO.ADD == b'\x00' and obj.primitives[0].type == 1
         and obj.primitives[0].dimensions == [0.10, 0.20, 0.40]
         and obj.header.frame_id == 'panda_link0'
         and obj.primitive_poses[0].position.z == 0.20)
rm = cena.diff_remover().world.collision_objects[0]
conferir('remocao: so id e REMOVE, sem geometria',
         rm.operation == CO.REMOVE and not rm.primitives and rm.id == 'caixa')
an = mensagens.anexacao('peca')
conferir('anexacao: ADD sem geometria, no panda_hand, dedos em touch_links',
         an.object.operation == CO.ADD and not an.object.primitives
         and an.link_name == 'panda_hand'
         and an.touch_links == ['panda_hand', 'panda_leftfinger', 'panda_rightfinger'])
so = mensagens.soltura('peca')
conferir('soltura: REMOVE do anexado', so.object.operation == CO.REMOVE)
diff_anexo = mensagens.cena_diff(anexados=[an])
conferir('cena com anexo: vai em robot_state, com is_diff nos dois niveis',
         diff_anexo.is_diff and diff_anexo.robot_state.is_diff
         and diff_anexo.robot_state.attached_collision_objects[0] is an
         and not diff_anexo.world.collision_objects)
RT = MSG_MOVEIT['RobotTrajectory']
JTP = classe('trajectory_msgs/JointTrajectoryPoint')


def trajetoria(*posicoes, t_final=2.5):
    tr = RT()
    for i, pos in enumerate(posicoes):
        pt = JTP()
        pt.positions = [float(v) for v in pos]
        pt.time_from_start.sec = int(t_final) if i == len(posicoes) - 1 else 0
        pt.time_from_start.nanosec = int((t_final % 1) * 1e9) if i == len(posicoes) - 1 else 0
        tr.joint_trajectory.points.append(pt)
    return tr


tr = trajetoria([0] * 7, [0.3, 0.4] + [0] * 5, [0.3, 0.4, 1.0] + [0] * 4)
conferir('pontos = 3, comprimento = 0,5 + 1,0 rad, duracao 2,5 s',
         mensagens.pontos(tr) == 3 and abs(mensagens.comprimento_juntas(tr) - 1.5) < 1e-12
         and abs(mensagens.duracao(tr) - 2.5) < 1e-9)
conferir('trajetoria vazia: 0 pontos, 0 rad, 0 s',
         mensagens.pontos(RT()) == 0 and mensagens.comprimento_juntas(RT()) == 0.0
         and mensagens.duracao(RT()) == 0.0)

# ---------------------------------------------------------------------- 5
print('5. a sequencia: nao para no tropeco, e as tabelas nao dao veredito')
R = sequencia.Resultado
roteiro_falso = {
    'ready': R('ready', codigo=1, tempo_moveit=0.02, tempo_relogio=0.1, pontos=2,
               comprimento=0.0, execucao=1),
    'A': R('A', codigo=1, tempo_moveit=0.05, tempo_relogio=0.2, pontos=12, comprimento=2.1,
           execucao=1),
    'B': R('B', codigo=-1, tempo_relogio=5.1),
    'C': R('C', recusado=True),
    'D': R('D', sem_resposta=True, tempo_relogio=15.0),
    'E': R('E', codigo=1, pontos=9, comprimento=1.0, execucao=-4),
}
log5 = []
res = sequencia.percorrer([{'nome': n} for n in roteiro_falso],
                          lambda a: roteiro_falso[a['nome']], log=log5.append)
conferir('percorre os 6 alvos mesmo com falha no meio', [x.nome for x in res]
         == list(roteiro_falso))
conferir('planejou/executou contados certo',
         [x.planejou for x in res] == [True, True, False, False, False, True]
         and [x.executou for x in res] == [True, True, False, False, False, False])
texto5 = '\n'.join(log5)
conferir('falha de planejamento sai com nome e dica',
         'PLANNING_FAILED (-1)' in texto5 and 'rode de novo' in texto5)
conferir('goal recusado e sem resposta sao ditos como tais',
         'goal RECUSADO' in texto5 and 'SEM RESPOSTA' in texto5 and 'DDS' in texto5)
conferir('execucao que falha (CONTROL_FAILED) aponta o list_controllers',
         'olhe (execucao)' in texto5 and 'list_controllers' in texto5)
tab = sequencia.tabela(res, 'teste')
conferir('tabela: cabecalho + 6 linhas, numeros so de quem planejou',
         len(tab) == 8 and '12' in tab[3] and tab[4].split()[3] == '-')
cmp_ = sequencia.comparar(res[:3], [R('A', codigo=-27), R('B', codigo=1, comprimento=3.3)])
conferir('comparar: lado a lado, alvo ausente marcado "(nao pedido)"',
         'GOAL_STATE_INVALID (-27)' in cmp_[2] and '3.30r' in cmp_[3]
         and '(nao pedido)' in cmp_[1])
rs = '\n'.join(sequencia.resumo(res))
conferir('resumo conta (3 de 6) e diz o que NAO significa',
         'contei: 3 de 6' in rs and 'nao uma conferencia do TP5' in rs and 'RViz2' in rs)
conferir('nenhuma linha impressa da veredito',
         not any(VEREDITO.search(x) for x in log5 + tab + cmp_ + rs.splitlines()))
vazio = R('ready', codigo=1, pontos=0, execucao=1)
conferir('SUCCESS com trajetoria vazia diz "ja estava no alvo"',
         'ja estava no alvo' in sequencia.linha(vazio))

# ---------------------------------------------------------------------- 6
print('6. a geometria das poses padrao, pela cinematica do URDF (aproximada)')
# Juntas do Panda, copiadas de moveit_resources branch humble:
# https://github.com/moveit/moveit_resources/blob/humble/panda_description/urdf/panda.urdf
# (origin xyz, origin rpy, limite inferior, limite superior); eixo z em todas.
H = math.pi / 2
URDF = [((0, 0, 0.333), (0, 0, 0), -2.9671, 2.9671),
        ((0, 0, 0), (-H, 0, 0), -1.8326, 1.8326),
        ((0, -0.316, 0), (H, 0, 0), -2.9671, 2.9671),
        ((0.0825, 0, 0), (H, 0, 0), -3.1416, 0.0873),
        ((-0.0825, 0.384, 0), (-H, 0, 0), -2.9671, 2.9671),
        ((0, 0, 0), (H, 0, 0), -0.0873, 3.8223),
        ((0.088, 0, 0), (H, 0, 0), -2.9671, 2.9671)]
FLANGE = 0.107      # panda_joint8 (fixa): panda_link7 -> panda_link8


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _tf(rpy, xyz):
    r, p_, y = rpy
    cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p_), math.sin(p_),
                              math.cos(y), math.sin(y))
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, xyz[0]],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, xyz[1]],
            [-sp, cp * sr, cp * cr, xyz[2]], [0, 0, 0, 1]]


def fk(qs, todos=False):
    T = _tf((0, 0, 0), (0, 0, 0))
    quadros = [T]
    for (xyz, rpy, _lo, _hi), qi in zip(URDF, qs):
        T = _mul(_mul(T, _tf(rpy, xyz)), _tf((0, 0, qi), (0, 0, 0)))
        quadros.append(T)
    T = _mul(T, _tf((0, 0, 0), (0, 0, FLANGE)))
    quadros.append(T)
    return quadros if todos else T


def rot_q(qq):
    x, y, z, w = qq
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def _erro(T, pos, Rd):
    e = [pos[i] - T[i][3] for i in range(3)]
    w = [0.0, 0.0, 0.0]
    for col in range(3):
        a = [T[i][col] for i in range(3)]
        b = [Rd[i][col] for i in range(3)]
        cr = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        for i in range(3):
            w[i] += 0.5 * cr[i]
    return e + w


def _resolver(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda rr: abs(M[rr][col]))
        M[col], M[piv] = M[piv], M[col]
        for rr in range(n):
            if rr != col:
                f = M[rr][col] / M[col][col]
                for k in range(col, n + 1):
                    M[rr][k] -= f * M[col][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def ik(pos, qq, semente, iters=400):
    """IK numerica (minimos quadrados amortecidos) DENTRO dos limites das juntas."""
    Rd = rot_q(qq)
    qs = list(semente)
    for _ in range(iters):
        e = _erro(fk(qs), pos, Rd)
        if math.sqrt(sum(v * v for v in e)) < 1e-6:
            return qs
        J = [[0.0] * 7 for _ in range(6)]
        for jj in range(7):
            d = list(qs)
            d[jj] += 1e-6
            e2 = _erro(fk(d), pos, Rd)
            for i in range(6):
                J[i][jj] = -(e2[i] - e[i]) / 1e-6
        JJt = [[sum(J[i][k] * J[rr][k] for k in range(7)) + (0.01 if i == rr else 0.0)
                for rr in range(6)] for i in range(6)]
        y = _resolver(JJt, e)
        qs = [min(max(qs[jj] + sum(J[i][jj] * y[i] for i in range(6)), URDF[jj][2]),
                  URDF[jj][3]) for jj in range(7)]
    return None


CAIXA = [(c - t / 2, c + t / 2) for c, t in zip(cena.CAIXA_CENTRO, cena.CAIXA_TAMANHO)]


def colide(qs, caixa=CAIXA):
    """Teste GROSSEIRO: esferas ao longo dos elos (r = 6 cm) e pontos da mao.

    Nao e o FCL do MoveIt, nao conhece a malha do Panda e nao testa
    autocolisao. Serve para uma coisa: saber se a pose esta obviamente dentro
    ou obviamente longe da caixa.
    """
    quadros = fk(qs, True)
    origens = [tuple(f[i][3] for i in range(3)) for f in quadros]
    pts = []
    for a, b in zip(origens[1:], origens[2:]):
        for k in range(11):
            pts.append((tuple(a[i] + k / 10 * (b[i] - a[i]) for i in range(3)), 0.06))
    T8 = quadros[-1]
    z8 = [T8[i][2] for i in range(3)]
    cs, sn = math.cos(-math.pi / 4), math.sin(-math.pi / 4)
    ymao = [T8[i][0] * (-sn) + T8[i][1] * cs for i in range(3)]   # y do panda_hand
    for dz in (0.0, 0.05, 0.10):
        for dy in (-0.1, -0.05, 0.0, 0.05, 0.1):
            if dz == 0.10 and abs(dy) > 0.05:
                continue
            pts.append((tuple(T8[i][3] + z8[i] * dz + ymao[i] * dy for i in range(3)), 0.02))
    return any(all(caixa[i][0] - r <= pt[i] <= caixa[i][1] + r for i in range(3))
               for pt, r in pts)


READY = mensagens.ESTADOS['ready']
T = fk(READY)
conferir('cinematica direta: `ready` poe o panda_link8 em (0,307; 0; 0,590)',
         abs(T[0][3] - 0.3069) < 1e-3 and abs(T[1][3]) < 1e-6 and abs(T[2][3] - 0.5903) < 1e-3,
         'valor conhecido do Panda em `ready`')
Rp = rot_q(mensagens.PARA_BAIXO)
conferir('PARA_BAIXO e a orientacao do panda_link8 em `ready` (eixo z para baixo)',
         all(abs(T[i][k] - Rp[i][k]) < 2e-3 for i in range(3) for k in range(3))
         and T[2][2] < -0.999)
alvos = tres_poses.montar_alvos(tres_poses.POSES_PADRAO, com_proibida=True)
sol = {}
for a in alvos[1:]:
    s = ik(a['valores'], mensagens.PARA_BAIXO, READY)
    sol[a['nome']] = s
    dist = math.sqrt(sum(v * v for v in a['valores'][:2]) + (a['valores'][2] - 0.333) ** 2)
    conferir('pose %s %s: IK dentro dos limites das juntas, a %.2f m do ombro'
             % (a['nome'], a['valores'], dist), s is not None and dist < 0.855)
conferir('`ready` nao encosta na caixa', not colide(READY))
for n in 'ABC':
    conferir('pose %s fora da caixa (com a IK achada aqui)' % n,
             sol[n] is not None and not colide(sol[n]))
conferir('pose D DENTRO da caixa: com a caixa, nao ha estado valido',
         sol['D'] is not None and colide(sol['D']))
a_, b_ = sol['A'], sol['B']
meio = [k for k in range(21) if colide([a_[jj] + k / 20 * (b_[jj] - a_[jj]) for jj in range(7)])]
conferir('de A para B a reta nas juntas ATRAVESSA a caixa: o planejador tem de desviar',
         len(meio) >= 5, 'colide em %d de 21 pontos da reta' % len(meio))
for p_ in pegar_e_soltar.roteiro():
    if p_['tipo'] == 'pose':
        s = ik(p_['valores'], mensagens.PARA_BAIXO, READY)
        conferir('pegar_e_soltar passo %d (%s): IK dentro dos limites'
                 % (p_['n'], p_['nome']), s is not None)

# ---------------------------------------------------------------------- 7
print('7. o cliente, com dubles do rclpy: prazos, recusas, plan x execute')
RES_MG = dubles['moveit_msgs.action'].MoveGroup.Result
RES_EX = dubles['moveit_msgs.action'].ExecuteTrajectory.Result
RES_GR = dubles['control_msgs.action'].GripperCommand.Result
RESP_CENA = _apply_srv().Response


def res_mg(val, pts=4, t=0.04):
    rr = RES_MG()
    rr.error_code.val = val
    rr.planning_time = t
    rr.planned_trajectory = trajetoria(*([[0.1 * k] * 7 for k in range(pts)]))
    return rr


def res_ex(val):
    rr = RES_EX()
    rr.error_code.val = val
    return rr


def resp_cena(ok):
    rr = RESP_CENA()
    rr.success = ok
    return rr


TODOS = {cliente.ACAO_MOVER, cliente.ACAO_EXECUTAR, cliente.SERVICO_CENA, cliente.ACAO_GARRA}


def novo_mundo(no_ar=TODOS, **respostas):
    MUNDO.no_ar = set(no_ar)
    MUNDO.respostas = {k.replace('__', '/'): list(v) for k, v in respostas.items()}
    MUNDO.enviados = {}
    MUNDO.ordem = []


_Node.parametros = {}
alvo_a = alvos[1]
novo_mundo(**{'/move_action': [res_mg(1)], '/execute_trajectory': [res_ex(1)]})
cl = cliente.ClienteMoveIt('teste')
conferir('com tudo no ar, esperar_move_group devolve True', cl.esperar_move_group())
rr = cl.mover(alvo_a, 'executar')
g_env = MUNDO.enviados['/move_action'][0]
e_env = MUNDO.enviados['/execute_trajectory'][0]
conferir('modo executar: planeja com plan_only = True e executa O MESMO plano',
         rr.executou and g_env.planning_options.plan_only
         and e_env.trajectory is rr.trajetoria and rr.pontos == 4)
conferir('o goal leva a pose A no panda_link8',
         g_env.request.goal_constraints[0].position_constraints[0]
         .constraint_region.primitive_poses[0].position.y == 0.30)
novo_mundo(**{'/move_action': [res_mg(1)]})
rr = cl.mover(alvo_a, 'planejar')
conferir('modo planejar: nao chama o /execute_trajectory',
         rr.planejou and rr.execucao is None and '/execute_trajectory' not in MUNDO.enviados)
novo_mundo(**{'/move_action': [res_mg(1, t=0.0)]})
rr = cl.mover(alvo_a, 'direto')
conferir('modo direto: plan_only = False, execucao = codigo do pedido',
         not MUNDO.enviados['/move_action'][0].planning_options.plan_only
         and rr.execucao == 1)
novo_mundo(**{'/move_action': [res_mg(-27, pts=0, t=0.0)]})
rr = cl.mover(alvo_a, 'executar')
conferir('GOAL_STATE_INVALID: nao executa, codigo -27 guardado',
         not rr.planejou and rr.codigo == -27 and '/execute_trajectory' not in MUNDO.enviados)
novo_mundo(**{'/move_action': ['recusa']})
rr = cl.mover(alvo_a, 'executar')
conferir('goal recusado vira Resultado.recusado', rr.recusado and not rr.planejou)
novo_mundo(**{'/move_action': ['sem_resposta']})
rr = cl.mover(alvo_a, 'executar')
conferir('aceito e sem resposta vira sem_resposta (nao fica pendurado)',
         rr.sem_resposta and not rr.planejou)
novo_mundo(**{'/move_action': [res_mg(1)], '/execute_trajectory': ['sem_resposta']})
rr = cl.mover(alvo_a, 'executar')
conferir('execucao sem resposta: EXECUCAO_SEM_RESPOSTA, nao SUCCESS',
         rr.planejou and not rr.executou and rr.execucao == codigos.EXEC_SEM_RESPOSTA)
novo_mundo(**{'/move_action': [res_mg(1, pts=0)]})
rr = cl.mover(alvo_a, 'executar')
conferir('plano vazio (ja estava la): conta como executado sem chamar a execucao',
         rr.executou and '/execute_trajectory' not in MUNDO.enviados)
novo_mundo(no_ar=set())
cl2 = cliente.ClienteMoveIt('teste')
conferir('move_group fora do ar: devolve False', not cl2.esperar_move_group())
conferir('... e diz o que conferir (node list, action list, a frase do Terminal A)',
         'ros2 action list' in cl2.log.linhas[-1] and 'grep move_group' in cl2.log.linhas[-1]
         and 'You can start planning now!' in cl2.log.linhas[-1])
novo_mundo(**{'/apply_planning_scene': ['sem_resposta']})
conferir('servico de cena sem resposta: None, com mensagem',
         cl.aplicar_cena(cena.diff_adicionar()) is None and 'nao respondeu' in cl.log.linhas[-1])
rg = RES_GR()
rg.reached_goal = True
novo_mundo(**{'/panda_hand_controller/gripper_cmd': [rg]})
conferir('garra: acha o servidor, manda position em float e le reached_goal',
         cl.esperar_garra() and cl.garra(0.035)
         and MUNDO.enviados['/panda_hand_controller/gripper_cmd'][0].command.position == 0.035)

# ---------------------------------------------------------------------- 8
print('8. os nos inteiros: cena, tres_poses (com comparar) e o roteiro')
conferir('montar_alvos padrao: ready + A, B, C; ready por juntas, o resto por pose',
         [a['nome'] for a in tres_poses.montar_alvos(tres_poses.POSES_PADRAO)]
         == ['ready', 'A', 'B', 'C']
         and alvos[0]['tipo'] == 'juntas' and alvos[1]['tipo'] == 'pose')
conferir('com_proibida acrescenta D (0,45; 0; 0,30)',
         alvos[-1]['nome'] == 'D' and alvos[-1]['valores'] == [0.45, 0.0, 0.30])
conferir('poses com tamanho que nao e multiplo de 3 e recusado',
         levanta(tres_poses.montar_alvos, [0.4, 0.2]))
novo_mundo(**{'/apply_planning_scene': [resp_cena(True)]})
no = cena.Cena()
conferir('cena (adicionar): devolve 0 e pede a caixa padrao',
         no.rodar() == 0 and MUNDO.enviados['/apply_planning_scene'][0].scene
         .world.collision_objects[0].operation == CO.ADD)
_Node.parametros = {'acao': 'remover'}
novo_mundo(**{'/apply_planning_scene': [resp_cena(False)]})
no = cena.Cena()
conferir('cena (remover sem caixa): devolve 1 e diz que pode nao haver objeto',
         no.rodar() == 1 and 'nao haver objeto' in no.log.linhas[-1])
_Node.parametros = {'acao': 'apagar'}
conferir('cena com acao invalida: devolve 2', cena.Cena().rodar() == 2)
_Node.parametros = {'comparar': True, 'com_proibida': True}
ok_mg = [res_mg(1) for _ in range(5)]
com_mg = [res_mg(1), res_mg(1), res_mg(1), res_mg(1), res_mg(-27, pts=0)]
volta = [res_mg(1)]
novo_mundo(**{'/apply_planning_scene': [resp_cena(False), resp_cena(True)],
              '/move_action': ok_mg + volta + com_mg + volta,
              '/execute_trajectory': [res_ex(1) for _ in range(11)]})
no = tres_poses.TresPoses()
cod = no.rodar()
cenas = MUNDO.enviados['/apply_planning_scene']
saida = '\n'.join(no.log.linhas)


def _e_ready(goal):
    jc = goal.request.goal_constraints[0].joint_constraints
    return (len(jc) == 7 and not goal.request.goal_constraints[0].position_constraints
            and [j.position for j in jc] == list(mensagens.ESTADOS['ready']))


seq_ = [(n, p_) for n, p_ in MUNDO.ordem if n in ('/apply_planning_scene', '/move_action')]
rotulos = [('cena-' + ('remove' if p_.scene.world.collision_objects[0].operation == CO.REMOVE
                       else 'add')) if n == '/apply_planning_scene'
           else ('ready' if _e_ready(p_) else 'pose') for n, p_ in seq_]
conferir('comparar: remove, ready + 4 poses, VOLTA AO READY, adiciona, ready + 4, volta',
         cod == 0 and rotulos == (['cena-remove', 'ready'] + ['pose'] * 4 + ['ready', 'cena-add',
                                  'ready'] + ['pose'] * 4 + ['ready']), str(rotulos))
conferir('comparar: a volta antes da caixa e EXECUTADA, nao so planejada',
         len(MUNDO.enviados['/execute_trajectory']) == 11)
conferir('comparar: a volta e dita no log, como servico fora da tabela',
         'antes de por a caixa' in saida and '(servico) o braco esta no ready' in saida)
conferir('comparar: a tabela lado a lado mostra D falhando so com a caixa',
         'lado a lado' in saida and re.search(r'D\s+\|\s+SUCCESS \(1\).*GOAL_STATE_INVALID',
                                              saida) is not None)
conferir('comparar: cada rodada continua com 5 alvos na tabela (a volta nao entra)',
         len(re.findall(r'^\[\d/5\]', saida, re.M)) == 10
         and not re.search(r'^\[\d/6\]', saida, re.M))
conferir('comparar: avisa que a caixa ficou na cena', 'FICOU na cena' in saida)

# a volta antes da caixa FALHA (o braco nao saiu de onde estava): a caixa nao entra
_Node.parametros = {'comparar': True, 'com_proibida': True}
novo_mundo(**{'/apply_planning_scene': [resp_cena(False), resp_cena(True)],
              '/move_action': ok_mg + [res_mg(-26, pts=0)],
              '/execute_trajectory': [res_ex(1) for _ in range(5)]})
no = tres_poses.TresPoses()
cod = no.rodar()
saida = '\n'.join(no.log.linhas)
conferir('comparar: se a volta ao ready falha, NAO poe a caixa e devolve 1',
         cod == 1 and len(MUNDO.enviados['/apply_planning_scene']) == 1
         and MUNDO.enviados['/apply_planning_scene'][0].scene.world.collision_objects[0]
         .operation == CO.REMOVE and len(MUNDO.enviados['/move_action']) == 6)
conferir('... e diz por que, com a dica de sair de dentro do objeto',
         'NAO pus a caixa' in saida and 'NAO consegui voltar ao ready' in saida
         and 'acao:=remover' in saida)

# sem comparar: no fim, volta ao ready (padrao), e nao volta com voltar_ao_ready:=false
_Node.parametros = {'com_proibida': True}
novo_mundo(**{'/move_action': [res_mg(1) for _ in range(6)],
              '/execute_trajectory': [res_ex(1) for _ in range(6)]})
no = tres_poses.TresPoses()
cod = no.rodar()
gols = MUNDO.enviados['/move_action']
conferir('sem comparar: depois de D, o ultimo pedido e a volta ao ready (por juntas)',
         cod == 0 and len(gols) == 6 and _e_ready(gols[-1]) and not _e_ready(gols[-2]))
_Node.parametros = {'com_proibida': True, 'voltar_ao_ready': False}
novo_mundo(**{'/move_action': [res_mg(1) for _ in range(5)],
              '/execute_trajectory': [res_ex(1) for _ in range(5)]})
no = tres_poses.TresPoses()
conferir('voltar_ao_ready:=false: nenhum pedido alem dos 5 alvos',
         no.rodar() == 0 and len(MUNDO.enviados['/move_action']) == 5)
_Node.parametros = {'modo': 'planejar'}
novo_mundo(**{'/move_action': [res_mg(1) for _ in range(4)]})
no = tres_poses.TresPoses()
conferir('modo planejar: o braco nao se mexe, e nao ha volta ao ready',
         no.rodar() == 0 and len(MUNDO.enviados['/move_action']) == 4
         and 'voltando ao ready' not in '\n'.join(no.log.linhas))

# a dica nova do START_STATE_INVALID (visto no ensaio de 16/11)
d26 = codigos.dica(-26)
conferir('START_STATE_INVALID: a dica diz que o braco esta DENTRO de um objeto, e a saida',
         'DENTRO' in d26 and d26.index('acao:=remover') < d26.index('tres_poses')
         < d26.rindex('aula18_moveit cena') and 'Found a contact' in d26)
conferir('START_STATE_IN_COLLISION: a mesma dica', codigos.dica(-10) == d26)
_Node.parametros = {}
novo_mundo(**{'/move_action': [res_mg(-26, pts=0)]})
no = tres_poses.TresPoses()
no.rodar()
conferir('tres_poses: o START_STATE_INVALID no ready imprime a dica nova',
         any('olhe:' in l_ and 'acao:=remover' in l_ for l_ in no.log.linhas))
_Node.parametros = {'modo': 'rapido'}
conferir('tres_poses com modo invalido: devolve 2', tres_poses.TresPoses().rodar() == 2)
_Node.parametros = {}
passos = pegar_e_soltar.roteiro()
conferir('roteiro: 14 passos, na ordem pre-pegada -> pegada -> fechar -> anexar -> levar',
         [p_['nome'] for p_ in passos][3:9] == ['pre-pegada', 'pegada', 'fechar', 'anexar',
                                                'subir', 'levar'] and len(passos) == 14)
z_pega = passos[4]['valores'][2]
conferir('pegada: dedos na metade de cima do cubo de 4 cm (z do link8 = 0,02 + TCP + 0,01)',
         abs(z_pega - (0.02 + mensagens.TCP + 0.01)) < 1e-12
         and abs(passos[3]['valores'][2] - z_pega - 0.10) < 1e-12)
conferir('garra abre a 0,035 (estado `open` do SRDF) e fecha a 0,02 (meio cubo)',
         passos[2]['posicao'] == 0.035 and passos[5]['posicao'] == 0.02)
log9 = []
feito = pegar_e_soltar.cumprir(passos, lambda p_: (p_['n'] != 5, 'x'), log=log9.append)
conferir('cumprir para no passo que falha (5) e nao anexa nada', feito == 4
         and 'parei no passo 5' in log9[-1])
feito = pegar_e_soltar.cumprir(passos, lambda p_: (True, 'x'), log=log9.append, ate=6)
conferir('ate_passo:=6 para antes do 7', feito == 6 and 'ate_passo:=6' in log9[-1])
conferir('o passo 1 so ACRESCENTA o cubo: nao tira a caixa do cena',
         [o.id for o in mensagens.cena_diff(passos[0]['objetos']).world.collision_objects]
         == ['peca'] and all(o.operation == CO.ADD for o in
                             mensagens.cena_diff(passos[0]['objetos']).world.collision_objects))
novo_mundo(**{'/move_action': [res_mg(-26, pts=0)]})
pes = pegar_e_soltar.PegarESoltar()
ok_, texto_ = pes.fazer(passos[1])
conferir('pegar_e_soltar: ready com START_STATE_INVALID para e da a dica de sair de dentro',
         not ok_ and 'START_STATE_INVALID (-26)' in texto_ and 'acao:=remover' in texto_)

# ---------------------------------------------------------------------- 9
print('9. o README cita o que o codigo usa')
readme = (AQUI / 'README.md').read_text(encoding='utf-8')
for termo in ('/move_action', '/apply_planning_scene', '/execute_trajectory',
              '/panda_hand_controller/gripper_cmd', 'moveit_resources_panda_moveit_config',
              'panda_arm', 'panda_link8', 'panda_link0', 'GOAL_STATE_INVALID',
              'O que foi e o que NAO foi verificado', 'tf2_echo panda_link0 panda_link8'):
    conferir('README menciona %s' % termo, termo in readme)

# --------------------------------------------------------------------- 10
print('10. (opcional) as definicoes copiadas aqui contra um clone do moveit_msgs')
if '--fonte' in sys.argv:
    dirf = pathlib.Path(sys.argv[sys.argv.index('--fonte') + 1])

    def _limpa(texto):
        return '; '.join(re.sub(r'\s+', ' ', ln.split('#')[0].strip())
                         for ln in texto.splitlines() if ln.split('#')[0].strip())

    for nome in sorted(SPECS):
        pkg, n = nome.split('/')
        if pkg != 'moveit_msgs' or n == 'MoveItErrorCodes':
            continue
        if '_' in n:
            base, parte = n.split('_')
            ext, partes = (('srv', ['Request', 'Response']) if parte in ('Request', 'Response')
                           else ('action', ['Goal', 'Result', 'Feedback']))
            blocos = (dirf / ext / ('%s.%s' % (base, ext))).read_text().split('---')
            orig = _limpa(blocos[partes.index(parte)])
        else:
            orig = _limpa((dirf / 'msg' / (n + '.msg')).read_text())
        conferir('%s igual a fonte' % nome, orig == SPECS[nome])
    orig = _limpa((dirf / 'msg' / 'MoveItErrorCodes.msg').read_text())
    conferir('MoveItErrorCodes igual a fonte',
             orig == 'int32 val; ' + '; '.join('int32 ' + p_ for p_ in SPEC_CODIGOS.split()))
else:
    print('  (pulado: rode com --fonte <clone de moveit_msgs, branch humble>)')

print()
print('tempo total: %.1f s' % (time.perf_counter() - t_inicio))
print('NAO testado aqui: tudo o que precisa de ROS 2 -- o move_group de verdade, o')
print('OMPL, a colisao do MoveIt (o grupo 6 e uma conta grosseira), o ros2_control,')
print('o RViz2. Os grupos 4, 7 e 8 usam DUBLES. Veja "O que foi e o que NAO foi')
print('verificado" no README.')
if falhas:
    print('%d FALHA(S): %s' % (len(falhas), '; '.join(falhas)))
    raise SystemExit(1)
print('todos os testes passaram.')
