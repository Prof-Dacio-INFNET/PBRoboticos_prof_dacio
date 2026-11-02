#!/usr/bin/env python3
"""Prova a INTERPRETACAO do diagnostico, sem ROS 2 na maquina.

    python3 testar.py

O truque e um `ros2` de mentira: um diretorio temporario com um script
executavel chamado `ros2` posto no INICIO do PATH, que devolve saidas fixas
conforme os argumentos que recebe. O `diagnosticar_nav2.py` roda inteiro, de
verdade, por subprocess -- ele nao sabe que o `ros2` e falso, e e exatamente
isso que faz o teste valer.

O que estes grupos provam: que o diagnostico LE certo a saida dos comandos --
que `unconfigured [1]` vira "nao achei" no no certo, que dois publicadores em
/cmd_vel sao achados e nomeados, que map -> odom ausente aponta a pose inicial.
O que eles NAO provam: que `ros2 lifecycle get` de verdade responde assim na
maquina do aluno. Nenhum teste aqui chega perto de um Nav2 real -- isso so a
Aula 16 dira.

Aqui o vocabulario e `ok` / `FALHA`, e nao o `achei` / `nao achei` do
diagnostico. A diferenca e de autoridade, nao de estilo: um teste SABE a
resposta de antemao -- ele mesmo escreveu a saida do `ros2` --, e por isso pode
dar veredito. O diagnostico, rodando contra o Nav2 do aluno, nao sabe nada, e
por isso nao pode.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = pathlib.Path(__file__).resolve().parent
NOS_NAV2 = ['/map_server', '/amcl', '/lifecycle_manager_localization',
            '/controller_server', '/smoother_server', '/planner_server',
            '/behavior_server', '/bt_navigator', '/waypoint_follower',
            '/velocity_smoother', '/lifecycle_manager_navigation']
ACOES_TODAS = ['/assisted_teleop', '/backup', '/compute_path_through_poses',
               '/compute_path_to_pose', '/drive_on_heading', '/follow_path',
               '/follow_waypoints', '/navigate_through_poses', '/navigate_to_pose',
               '/smooth_path', '/spin', '/wait']

# O `ros2` de mentira. Le o cenario de um JSON apontado por PB_CENARIO e
# devolve o texto que o comando de verdade devolveria. Os comandos que nao
# terminam por conta propria (`topic hz`, `tf2_echo`, `topic echo` sem
# mensagem) imprimem o que tem e DORMEM: assim o teste exercita o caminho do
# timeout do subprocess, que e por onde a saida util chega de verdade.
FALSO = r'''#!/usr/bin/env python3
"""Um `ros2` de mentira, para provar a leitura das saidas sem ROS 2."""
import json
import os
import sys
import time

CEN = json.loads(open(os.environ['PB_CENARIO'], encoding='utf-8').read())
ARGS = sys.argv[1:]
PENDURA = 3.0        # maior que o --timeout dos testes, de proposito


def sai(texto='', codigo=0, dorme=0.0, saida=sys.stdout):
    saida.write(texto)
    saida.flush()
    if dorme:
        time.sleep(dorme)
    raise SystemExit(codigo)


def bloco(no, tipo, msg, dur):
    return ['Node name: ' + no.lstrip('/'), 'Node namespace: /', 'Topic type: ' + msg,
            'Endpoint type: ' + tipo, 'GID: 01.0f.' + '00.' * 21,
            'QoS profile:', '  Reliability: RELIABLE', '  History (Depth): UNKNOWN',
            '  Durability: ' + dur, '  Lifespan: Infinite', '  Deadline: Infinite',
            '  Liveliness: AUTOMATIC', '  Liveliness lease duration: Infinite', '']


def topico_info(nome):
    t = CEN.get('topicos', {}).get(nome)
    if t is None:
        return 'Type: Unknown\n\nPublisher count: 0\n\nSubscription count: 0\n'
    msg, dur = t.get('tipo', 'std_msgs/msg/String'), t.get('dur', 'VOLATILE')
    pubs, subs = t.get('pubs', []), t.get('subs', [])
    linhas = ['Type: ' + msg, '', 'Publisher count: %d' % len(pubs), '']
    for no in pubs:
        linhas += bloco(no, 'PUBLISHER', msg, dur)
    linhas += ['Subscription count: %d' % len(subs), '']
    for no in subs:
        linhas += bloco(no, 'SUBSCRIPTION', msg, 'VOLATILE')
    return '\n'.join(linhas) + '\n'


TF_STATIC = """transforms:
- header:
    stamp:
      sec: 1762140000
      nanosec: 0
    frame_id: base_footprint
  child_frame_id: laser_frame
  transform:
    translation:
      x: 0.12
      y: 0.0
      z: 0.18
    rotation:
      x: 0.0
      y: 0.0
      z: 0.0
      w: 1.0
---
"""

AMCL_POSE = """header:
  stamp:
    sec: 1762140001
    nanosec: 500000000
  frame_id: map
pose:
  pose:
    position:
      x: 2.01
      y: 3.98
      z: 0.0
    orientation:
      x: 0.0
      y: 0.0
      z: 0.006
      w: 1.0
  covariance:
  - 0.021
  - 0.0
---
"""

MAP_ODOM = """At time 1762140002.400000000
- Translation: [0.043, -0.011, 0.000]
- Rotation: in Quaternion [0.000, 0.000, 0.004, 1.000]
- Rotation: in RPY (radian) [0.000, 0.000, 0.008]
- Rotation: in RPY (degree) [0.000, 0.000, 0.458]
"""

if ARGS[:2] == ['node', 'list']:
    sai('\n'.join(CEN['nos']) + '\n' if CEN['nos'] else '')

if ARGS[:2] == ['lifecycle', 'get']:
    estado = CEN.get('estados', {}).get(ARGS[2], CEN.get('estado_padrao', 'active [3]'))
    if estado == 'ausente':
        sai('Node not found\n', 1, saida=sys.stderr)
    sai(estado + '\n')

if ARGS[:2] == ['action', 'list']:
    sai('\n'.join(CEN.get('acoes', [])) + '\n' if CEN.get('acoes') else '')

if ARGS[:2] == ['topic', 'info']:
    sai(topico_info(ARGS[2]))

if ARGS[:2] == ['topic', 'echo']:
    # O `--qos-durability` existe no Humble, mas nem em toda versao: o cenario
    # pode recusa-lo para que o diagnostico tenha de cair no echo simples.
    if CEN.get('recusa_qos') and '--qos-durability' in ARGS:
        sai('usage: ros2 topic echo [-h]\nros2 topic echo: error: unrecognized arguments: '
            '--qos-durability\n', 2, saida=sys.stderr)
    if ARGS[2] == '/tf_static':
        sai(TF_STATIC if CEN.get('tf_static') else '', dorme=PENDURA)
    if ARGS[2] == '/amcl_pose':
        sai(AMCL_POSE if CEN.get('amcl_pose_msg') else '', dorme=PENDURA)
    sai('', dorme=PENDURA)

if ARGS[:2] == ['topic', 'hz']:
    taxa = CEN.get('hz', {}).get(ARGS[2])
    if taxa is None:
        sai('', dorme=PENDURA)
    sai('average rate: %s\n\tmin: 0.049s max: 0.051s std dev: 0.00050s window: 20\n'
        % taxa, dorme=PENDURA)

if ARGS[:3] == ['run', 'tf2_ros', 'tf2_echo']:
    if CEN.get('map_odom') and ARGS[3:5] == ['map', 'odom']:
        sai(MAP_ODOM, dorme=PENDURA)
    sai('Failure at 1762140002.400000000\nException thrown:"map" passed to lookupTransform '
        'argument target_frame does not exist.\n', dorme=PENDURA, saida=sys.stderr)

sai('ros2: comando de mentira nao sabe responder: %s\n' % ' '.join(ARGS), 2,
    saida=sys.stderr)
'''


# ---------------------------------------------------------------- cenarios

def topicos_saudaveis(cmd_vel_pubs=('/velocity_smoother',)):
    """A fotografia de um Nav2 que subiu inteiro, para os cenarios variarem."""
    return {
        '/cmd_vel': {'tipo': 'geometry_msgs/msg/Twist', 'pubs': list(cmd_vel_pubs),
                     'subs': ['/mundo']},
        '/cmd_vel_nav': {'tipo': 'geometry_msgs/msg/Twist', 'pubs': ['/controller_server'],
                         'subs': ['/velocity_smoother']},
        '/amcl_pose': {'tipo': 'geometry_msgs/msg/PoseWithCovarianceStamped',
                       'pubs': ['/amcl'], 'subs': []},
        '/global_costmap/costmap': {'tipo': 'nav_msgs/msg/OccupancyGrid',
                                    'pubs': ['/planner_server'], 'subs': [],
                                    'dur': 'TRANSIENT_LOCAL'},
        '/local_costmap/costmap': {'tipo': 'nav_msgs/msg/OccupancyGrid',
                                   'pubs': ['/controller_server'], 'subs': [],
                                   'dur': 'TRANSIENT_LOCAL'},
        '/map': {'tipo': 'nav_msgs/msg/OccupancyGrid', 'pubs': ['/map_server'],
                 'subs': ['/amcl'], 'dur': 'TRANSIENT_LOCAL'},
    }


def cenario_a():
    """(a) Tudo no ar e ativo, pose inicial dada, um publicador em /cmd_vel."""
    return {'nos': NOS_NAV2 + ['/mundo', '/rviz2'], 'estado_padrao': 'active [3]',
            'tf_static': True, 'map_odom': True, 'amcl_pose_msg': True,
            'acoes': ACOES_TODAS, 'topicos': topicos_saudaveis(),
            'hz': {'/cmd_vel_nav': '19.918'}}


def cenario_b():
    """(b) Nenhum no do Nav2 no ar -- so o mundo e o RViz2."""
    return {'nos': ['/mundo', '/rviz2', '/transform_listener_impl_5581f0a2e3c0'],
            'estado_padrao': 'ausente', 'tf_static': True, 'map_odom': False,
            'amcl_pose_msg': False, 'acoes': [], 'topicos': {}, 'hz': {}}


def cenario_c():
    """(c) Nos no ar, mas o gerenciador parou no bt_navigator.

    Os tres ultimos da ordem de subida ficam em unconfigured, que e o que o
    lifecycle_manager de verdade produz: ele ativa um no por vez e PARA. Sem o
    velocity_smoother ativo ninguem publica /cmd_vel, e sem o bt_navigator nao
    existe /navigate_to_pose -- os dois sintomas vem juntos no mundo real.
    """
    topicos = topicos_saudaveis()
    topicos['/cmd_vel']['pubs'] = []
    topicos['/cmd_vel_nav']['subs'] = []
    return {'nos': NOS_NAV2 + ['/mundo'], 'estado_padrao': 'active [3]',
            'estados': {'/bt_navigator': 'unconfigured [1]',
                        '/waypoint_follower': 'unconfigured [1]',
                        '/velocity_smoother': 'unconfigured [1]'},
            'tf_static': True, 'map_odom': True, 'amcl_pose_msg': True,
            'recusa_qos': True,
            'acoes': ['/compute_path_to_pose', '/follow_path', '/spin', '/backup'],
            'topicos': topicos, 'hz': {}}


def cenario_d():
    """(d) Tudo ativo e NINGUEM deu a pose inicial: sem map -> odom, /amcl_pose calado."""
    return {'nos': NOS_NAV2 + ['/mundo', '/rviz2'], 'estado_padrao': 'active [3]',
            'tf_static': True, 'map_odom': False, 'amcl_pose_msg': False,
            'acoes': ACOES_TODAS, 'topicos': topicos_saudaveis(), 'hz': {}}


def cenario_d2():
    """(d2) O que a maquina do professor mostrou em 26/10: sem pose inicial, o
    planner_server fica preso em "Timed out waiting for transform ... map" e o
    gerenciador de navegacao para nele -- planner, behavior, bt_navigator,
    waypoint_follower e velocity_smoother ficam inativos. A CAUSA e a pose
    inicial; os nos inativos sao consequencia. A lista tem de dizer isso nessa
    ordem, senao o aluno vai ler o terminal do gerenciador atras de um erro que
    nao esta la.
    """
    topicos = topicos_saudaveis()
    topicos['/cmd_vel']['pubs'] = []
    topicos['/cmd_vel_nav']['subs'] = []
    return {'nos': NOS_NAV2 + ['/mundo', '/rviz2'], 'estado_padrao': 'active [3]',
            'estados': {'/planner_server': 'inactive [2]',
                        '/behavior_server': 'inactive [2]',
                        '/bt_navigator': 'inactive [2]',
                        '/waypoint_follower': 'inactive [2]',
                        '/velocity_smoother': 'inactive [2]'},
            'tf_static': True, 'map_odom': False, 'amcl_pose_msg': False,
            'acoes': ['/compute_path_to_pose', '/follow_path'],
            'topicos': topicos, 'hz': {}}


def cenario_e():
    """(e) Dois publicadores em /cmd_vel -- o piloto da Aula 11 ficou no ar."""
    return {'nos': NOS_NAV2 + ['/mundo', '/rviz2', '/piloto'],
            'estado_padrao': 'active [3]', 'tf_static': True, 'map_odom': True,
            'amcl_pose_msg': True, 'acoes': ACOES_TODAS,
            'topicos': topicos_saudaveis(('/velocity_smoother', '/piloto')),
            'hz': {'/cmd_vel_nav': '19.918'}}


# ---------------------------------------------------------------- execucao

MARCAS = ('achei', 'nao achei', 'olhe')
# A lista final numera com `{i:>2}.`: ' 1.' com dois espacos a esquerda, '10.' com
# um. O re.M nao e opcional aqui -- sem ele o findall procura o inicio do TEXTO,
# nao o de cada linha, e a lista volta sempre vazia (foi o primeiro bug deste teste).
ITEM_DA_LISTA = re.compile(r'^ {2,3}\d+\. (.+)$', re.M)


class Diagnostico:
    """A saida de uma rodada, com os acessos que os testes precisam."""

    def __init__(self, texto, codigo):
        self.texto = texto
        self.codigo = codigo
        self.linhas = []
        for linha in texto.splitlines():
            if not linha.startswith('  ') or len(linha) < 13:
                continue
            marca = linha[2:11].strip()
            if marca not in MARCAS:
                continue
            self.linhas.append((marca, linha[13:57].strip(), linha[57:].strip()))

    def estado(self, nome):
        return next((m for m, n, _ in self.linhas if n == nome), None)

    def detalhe(self, nome):
        return next((d for m, n, d in self.linhas if n == nome), '')

    def nomes(self):
        return [n for _, n, _ in self.linhas]

    def lista(self):
        """Os nomes da lista final 'Onde olhar', na ordem em que saiu."""
        corte = self.texto.find('Onde olhar, na ordem')
        if corte < 0:
            return []
        return ITEM_DA_LISTA.findall(self.texto[corte:])

    def receita(self, nome):
        """O 'o que fazer a seguir' de um item da lista final, em uma linha."""
        corte = self.texto.find('Onde olhar, na ordem')
        bloco, pegando = [], False
        for linha in self.texto[corte:].splitlines():
            m = ITEM_DA_LISTA.match(linha)
            if m:
                pegando = m.group(1) == nome
                continue
            if pegando and linha.startswith('      '):
                bloco.append(linha.strip())
            elif pegando and bloco:
                break
        return ' '.join(bloco)


def preparar(base):
    """Escreve o `ros2` de mentira e devolve o diretorio que vai no PATH."""
    pasta = base / 'bin'
    pasta.mkdir(parents=True, exist_ok=True)
    falso = pasta / 'ros2'
    falso.write_text(FALSO, encoding='utf-8')
    falso.chmod(0o755)
    return pasta


def diagnosticar(base, pasta_falsa, cenario, extra=(), com_ros2=True, distro='humble'):
    """Roda o diagnostico de verdade contra o `ros2` de mentira."""
    arquivo = base / 'cenario.json'
    arquivo.write_text(json.dumps(cenario), encoding='utf-8')

    ambiente = dict(os.environ)
    caminhos = [] if not com_ros2 else [str(pasta_falsa)]
    ambiente['PATH'] = os.pathsep.join(caminhos + ['/usr/bin', '/bin'])
    ambiente['PB_CENARIO'] = str(arquivo)
    ambiente['AMENT_PREFIX_PATH'] = os.pathsep.join(
        [str(base / 'ros2_ws' / 'install'), '/opt/ros/humble'])
    if distro:
        ambiente['ROS_DISTRO'] = distro
    else:
        ambiente.pop('ROS_DISTRO', None)

    r = subprocess.run(
        [sys.executable, str(AQUI / 'diagnosticar_nav2.py'), '--sem-cor',
         '--timeout', '1', *extra],
        capture_output=True, text=True, cwd=str(AQUI), env=ambiente, timeout=180)
    return Diagnostico(r.stdout + r.stderr, r.returncode)


falhas = []


def conferir(nome, ok, detalhe=''):
    print('  %s  %s%s' % ('ok  ' if ok else 'FALHA', nome,
                          '  -- ' + detalhe if detalhe else ''))
    if not ok:
        falhas.append(nome)


def main() -> int:
    t_inicio = time.perf_counter()
    base = pathlib.Path(tempfile.mkdtemp(prefix='clinica-nav2-'))
    try:
        pasta = preparar(base)
        conferir('o `ros2` de mentira esta no PATH e nao e o de verdade',
                 shutil.which('ros2', path=str(pasta)) == str(pasta / 'ros2'),
                 str(pasta / 'ros2'))

        print('1. cenario (a): tudo no ar e ativo, pose dada, UM publicador em /cmd_vel')
        a = diagnosticar(base, pasta, cenario_a())
        conferir('nao sobrou pendencia', a.lista() == [], '%d item(ns)' % len(a.lista()))
        conferir('sai com codigo 0', a.codigo == 0, 'codigo %d' % a.codigo)
        conferir('os onze nos esperados aparecem como achei',
                 all(a.estado('no ' + n.lstrip('/')) == 'achei' for n in NOS_NAV2),
                 '%d nos conferidos' % len(NOS_NAV2))
        conferir('os nove nos gerenciaveis aparecem como ativos',
                 sum(1 for m, n, _ in a.linhas if n.startswith('ativo: ') and m == 'achei') == 9)
        conferir('os gerenciadores NAO entram no lifecycle get',
                 'ativo: lifecycle_manager_navigation' not in a.nomes(),
                 'eles gerenciam o ciclo de vida, nao o tem')
        conferir('a aresta map -> odom e achada', a.estado('aresta map -> odom') == 'achei',
                 a.detalhe('aresta map -> odom')[:34])
        conferir('/cmd_vel com UM publicador, nomeado',
                 a.estado('/cmd_vel tem UM publicador') == 'achei'
                 and 'velocity_smoother' in a.detalhe('/cmd_vel tem UM publicador'))
        conferir('a taxa de /cmd_vel_nav e lida da saida parcial do timeout',
                 a.estado('trafego em /cmd_vel_nav') == 'achei'
                 and '19.918' in a.detalhe('trafego em /cmd_vel_nav'),
                 a.detalhe('trafego em /cmd_vel_nav')[:40])
        conferir('a durabilidade de /map e lida do bloco do PUBLICADOR',
                 a.estado('/map durabilidade transient local') == 'achei',
                 a.detalhe('/map durabilidade transient local'))
        conferir('lista vazia NAO e declarada como pronto',
                 'NAO quer dizer que o Nav2 esta pronto' in a.texto
                 and 'esgotei o que um script enxerga' in a.texto)

        print('2. cenario (b): nenhum no do Nav2 no ar')
        b = diagnosticar(base, pasta, cenario_b())
        conferir('acha a lista de nos, e nenhum deles e do Nav2',
                 b.estado('ros2 node list responde') == 'achei'
                 and b.estado('algum no do Nav2 no ar') == 'nao achei')
        conferir('UMA pendencia, e e essa', b.lista() == ['algum no do Nav2 no ar'],
                 ', '.join(b.lista()) or 'nenhuma')
        conferir('nao imprime onze linhas de no ausente',
                 not any(n.startswith('no ') for n in b.nomes()),
                 'dez pendencias de eco esconderiam a unica que importa')
        conferir('declara que 3 a 10 nao foram olhadas',
                 b.estado('ciclo de vida, TF, pose, topicos e acoes') == 'olhe')
        conferir('a receita manda subir o Nav2 e cita o ROS_DOMAIN_ID',
                 'ros2 launch' in b.receita('algum no do Nav2 no ar')
                 and 'ROS_DOMAIN_ID' in b.receita('algum no do Nav2 no ar'))
        conferir('sai com codigo 1', b.codigo == 1, 'codigo %d' % b.codigo)

        print('3. cenario (c): nos no ar, bt_navigator em unconfigured')
        c = diagnosticar(base, pasta, cenario_c())
        conferir('o bt_navigator aparece como nao achei, com o estado no detalhe',
                 c.estado('ativo: bt_navigator') == 'nao achei'
                 and 'unconfigured [1]' in c.detalhe('ativo: bt_navigator'),
                 c.detalhe('ativo: bt_navigator'))
        conferir('os nos ANTES dele continuam achei',
                 all(c.estado('ativo: ' + n) == 'achei'
                     for n in ('map_server', 'amcl', 'controller_server', 'planner_server')))
        conferir('o bt_navigator e o PRIMEIRO da lista final',
                 c.lista()[:1] == ['ativo: bt_navigator'], ', '.join(c.lista()[:3]))
        conferir('e a receita dele diz que o gerenciador parou ALI',
                 'parou AQUI' in c.receita('ativo: bt_navigator')
                 and 'lifecycle set' in c.receita('ativo: bt_navigator'))
        conferir('os de baixo sao tratados como consequencia, nao como causa',
                 'consequencia' in c.receita('ativo: waypoint_follower')
                 and 'consequencia' in c.receita('ativo: velocity_smoother'))
        conferir('sem velocity_smoother ativo, /cmd_vel fica sem publicador',
                 c.estado('/cmd_vel tem UM publicador') == 'nao achei'
                 and 'count: 0' in c.detalhe('/cmd_vel tem UM publicador'))
        conferir('e /navigate_to_pose desaparece da lista de acoes',
                 c.estado('/navigate_to_pose existe') == 'nao achei'
                 and 'bt_navigator' in c.receita('/navigate_to_pose existe'))
        conferir('a acao de rota do G4.2 tambem some, e a receita cita as duas',
                 c.estado('acao de rota para o G4.2') == 'nao achei'
                 and 'follow_waypoints' in c.receita('acao de rota para o G4.2'))
        conferir('o `ros2` que recusa --qos-durability nao cega o /tf_static',
                 c.estado('/tf_static tem mensagem') == 'achei',
                 'caiu no echo simples: ' + c.detalhe('/tf_static tem mensagem'))

        print('4. cenario (d): tudo ativo e NINGUEM deu a pose inicial')
        d = diagnosticar(base, pasta, cenario_d())
        conferir('todos os nove nos gerenciaveis estao ativos',
                 sum(1 for m, n, _ in d.linhas if n.startswith('ativo: ') and m == 'achei') == 9,
                 'o ciclo de vida nao acusa nada -- e e por isso que esta aula existe')
        conferir('a aresta map -> odom nao e achada',
                 d.estado('aresta map -> odom') == 'nao achei')
        conferir('/amcl_pose tem publicador E nao publicou -- duas linhas separadas',
                 d.estado('/amcl_pose tem publicador') == 'achei'
                 and d.estado('/amcl_pose ja publicou') == 'nao achei')
        conferir('map -> odom e a PRIMEIRA da lista final',
                 d.lista()[:1] == ['aresta map -> odom'], ', '.join(d.lista()))
        conferir('as duas receitas mandam dar a pose inicial, concretamente',
                 '2D Pose Estimate' in d.receita('aresta map -> odom')
                 and '2D Pose Estimate' in d.receita('/amcl_pose ja publicou'))
        conferir('e a de map -> odom nomeia a causa no codigo do AMCL do Humble',
                 'initial_pose_is_known_' in d.receita('aresta map -> odom'))
        conferir('duas pendencias, e sao essas duas', len(d.lista()) == 2,
                 ', '.join(d.lista()))

        print('4b. cenario (d2): sem pose inicial E o gerenciador parado no planner_server')
        d2 = diagnosticar(base, pasta, cenario_d2())
        conferir('map -> odom vem ANTES do planner_server inativo na lista final',
                 d2.lista().index('aresta map -> odom')
                 < d2.lista().index('ativo: planner_server'), ', '.join(d2.lista()))
        conferir('o primeiro inativo e o planner_server, e os de baixo sao consequencia',
                 d2.estado('ativo: planner_server') == 'nao achei'
                 and 'consequencia' in d2.receita('ativo: bt_navigator'))
        conferir('a receita do planner_server manda comecar pela aresta',
                 'map -> odom' in d2.receita('ativo: planner_server'))
        conferir('a receita da aresta explica a cadeia ate o planner_server',
                 'planner_server' in d2.receita('aresta map -> odom'))

        print('5. cenario (e): DOIS publicadores em /cmd_vel')
        e = diagnosticar(base, pasta, cenario_e())
        conferir('acha dois publicadores e os NOMEIA',
                 e.estado('/cmd_vel tem UM publicador') == 'nao achei'
                 and '2 publicadores' in e.detalhe('/cmd_vel tem UM publicador')
                 and 'piloto' in e.detalhe('/cmd_vel tem UM publicador'),
                 e.detalhe('/cmd_vel tem UM publicador'))
        conferir('UMA pendencia: nada mais esta errado neste cenario',
                 e.lista() == ['/cmd_vel tem UM publicador'], ', '.join(e.lista()))
        conferir('a receita diz o que derrubar, e como',
                 'piloto:=false' in e.receita('/cmd_vel tem UM publicador')
                 and 'ultimo que falou' in e.receita('/cmd_vel tem UM publicador'))
        conferir('o ciclo de vida nao acusa nada: dois publicadores nao dao erro',
                 not any(n.startswith('ativo: ') and m == 'nao achei'
                         for m, n, _ in e.linhas))

        print('6. cenario (f): sem `ros2` no PATH -- rodar no Windows nao quebra nada')
        f = diagnosticar(base, pasta, cenario_a(), com_ros2=False, distro='')
        conferir('acusa o comando ausente e a variavel vazia',
                 f.estado('comando ros2 no PATH') == 'nao achei'
                 and f.estado('ROS_DISTRO=humble') == 'nao achei')
        conferir('e para ali, declarando que 2 a 10 nao foram olhadas',
                 f.estado('nos, ciclo de vida, TF, pose e topicos') == 'olhe')
        conferir('nao tenta chamar o ros2 ausente',
                 'ros2 node list responde' not in f.nomes())

        print('7. as opcoes e as regras que valem em TODO cenario')
        r = diagnosticar(base, pasta, cenario_d(), extra=['--rapido'])
        conferir('--rapido olha 1, 2, 3 e 6', r.estado('/cmd_vel tem UM publicador') == 'achei'
                 and r.estado('ativo: amcl') == 'achei')
        conferir('--rapido NAO olha 4, 5, 7, 8, 9 e 10',
                 r.estado('aresta map -> odom') is None
                 and r.estado('/map com publicador') is None
                 and r.estado('TF, pose, cadeia, acoes, costmaps e mapa') == 'olhe')
        conferir('--rapido nao esconde a pendencia que ele nao olhou: ele a declara',
                 r.lista() == [], 'em --rapido o cenario (d) parece limpo, e a saida avisa')
        todos = {'(a)': a, '(b)': b, '(c)': c, '(d)': d, '(e)': e, '(f)': f, '--rapido': r}
        conferir('--sem-cor nao deixa nenhum codigo de escape na saida',
                 not any('\033' in x.texto for x in todos.values()))
        conferir('o vocabulario e so achei / nao achei / olhe, em todo cenario',
                 all(m in MARCAS for x in todos.values() for m, _, _ in x.linhas),
                 '%d linhas de relatorio conferidas'
                 % sum(len(x.linhas) for x in todos.values()))
        proibidas = ('ok ', 'falha', 'erro ', 'passou', 'aprovado', 'reprovado')
        marcas_erradas = [p for p in proibidas
                          for x in todos.values() for m, _, _ in x.linhas if p in m.lower()]
        conferir('nenhuma marca diz ok, falha, erro, passou nem aprovado',
                 not marcas_erradas, ', '.join(marcas_erradas) or 'nenhuma')
        conferir('o cabecalho diz as quatro coisas que ele nao faz',
                 all(all(p in x.texto for p in ('nao corrige', 'nao valida',
                                                'nao antecipa nota',
                                                'nao substitui o enunciado'))
                     for x in todos.values()))
        conferir('e declara, sempre, o que esta fora do alcance dele',
                 all(x.estado('o robo realmente anda') == 'olhe'
                     and x.estado("o mapa e' do SEU cenario") == 'olhe'
                     and x.estado('a rota faz sentido') == 'olhe'
                     and x.estado('o relatorio responde ao enunciado') == 'olhe'
                     for x in todos.values()),
                 'inclusive em --rapido e inclusive quando nao sobrou pendencia')
        conferir('todo item da lista final vem com o que fazer a seguir',
                 all(len(x.receita(n)) > 40 for x in todos.values() for n in x.lista()),
                 '%d receita(s)' % sum(len(x.lista()) for x in todos.values()))
        conferir('o codigo de saida acompanha a lista final, nos sete casos',
                 all(x.codigo == (1 if x.lista() else 0) for x in todos.values()))
        mau = diagnosticar(base, pasta, cenario_a(), extra=['--timeout', '0'])
        conferir('--timeout 0 e recusado com codigo 2', mau.codigo == 2,
                 'codigo %d' % mau.codigo)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print()
    print('tempo total: %.1f s' % (time.perf_counter() - t_inicio))
    if falhas:
        print('%d FALHA(S): %s' % (len(falhas), '; '.join(falhas)))
        return 1
    print('todos os testes passaram.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
