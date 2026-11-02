#!/usr/bin/env python3
"""Onde olhar quando o Nav2 nao navega -- um apoio, nunca um veredito.

ISTO NAO CORRIGE, NAO VALIDA, NAO ANTECIPA NOTA E NAO SUBSTITUI O ENUNCIADO.
E um apoio de clinica: com o Nav2 no ar, ele roda uma sequencia de comandos do
ROS 2 e diz ONDE olhar primeiro. A referencia e' o enunciado do TP4, e a
responsabilidade pela entrega e' sua -- antes e depois de rodar isto.

Por que existe: "o Nav2 nao navega" tem umas dez causas, e nove delas nao dao
mensagem de erro nenhuma. O gerenciador de ciclo de vida que para calado, a
pose inicial que ninguem deu, o segundo publicador em /cmd_vel. Sozinho na
vespera do G4.1, o aluno testa essas dez coisas na ordem errada e gasta a noite
na ultima. Este script testa na ordem em que compensa.

A ordem nao e' decorativa: cada verificacao supoe a anterior. Sem `ros2` no
PATH nao ha o que olhar; sem no no ar nao ha ciclo de vida para consultar; sem
a aresta map -> odom o planejador nao tem onde planejar. Por isso ele PARA
quando a base cai, em vez de imprimir dez linhas que sao todas eco da primeira.

Ele chama o CLI (`ros2 node list`, `ros2 lifecycle get`, ...) por subprocess e
le a saida. Nao usa rclpy de proposito: assim roda com qualquer workspace
sourceado, nao assina topico nenhum, nao cria no nenhum e nao concorre com o
seu Nav2 pelo discovery.

    python3 diagnosticar_nav2.py
    python3 diagnosticar_nav2.py --rapido
    python3 diagnosticar_nav2.py --timeout 10 --sem-cor

Os estados sao `achei`, `nao achei` e `olhe`. Nao existe `ok`, nem `falha`, nem
`passou`: o script nao tem como saber se esta' certo. "achei" nao quer dizer
certo e "nao achei" nao quer dizer errado -- quer dizer, nos dois casos: va'
olhar isso.

O QUE ELE NAO ALCANCA, e e' justamente o que os gates cobram: se o robo
realmente anda, se o mapa e' do seu cenario, se a rota faz sentido, se o
relatorio responde ao que foi pedido. Isso nao sai de comando nenhum.

Saida 1 quando sobrou algo para olhar, 0 quando nao sobrou -- e nenhuma das
duas e' um julgamento sobre a sua entrega.
Gates do TP4 em jogo: G4.1 (vai a um goal sem intervencao, 04/11) e G4.2 (rota
com tres ou mais waypoints, 09/11).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

VERDE, VERMELHO, AMARELO, NEGRITO, FIM = (
    '\033[32m', '\033[31m', '\033[33m', '\033[1m', '\033[0m')

# Degrada para texto puro quando a saida nao e' terminal: redirecionar para
# arquivo ou canalizar para `tee` nao deve encher o texto de lixo de escape.
if not sys.stdout.isatty():
    VERDE = VERMELHO = AMARELO = NEGRITO = FIM = ''

# A ordem e' a do bringup oficial do Humble -- `localization_launch.py` e
# depois `navigation_launch.py`, cada gerenciador ativando um no por vez nesta
# sequencia. Ela importa: o PRIMEIRO no que nao esta ativo e' onde o
# gerenciador parou, e os de baixo estao inativos por consequencia, nao por
# causa propria. Listar em outra ordem apontaria o lugar errado.
ESPERADOS = (
    'map_server', 'amcl', 'lifecycle_manager_localization',
    'controller_server', 'smoother_server', 'planner_server',
    'behavior_server', 'bt_navigator', 'waypoint_follower',
    'velocity_smoother', 'lifecycle_manager_navigation',
)

# Os gerenciadores NAO sao nos de ciclo de vida -- eles o gerenciam nos outros.
# `ros2 lifecycle get /lifecycle_manager_navigation` responde que nao achou o
# no, e isso nao e' defeito: e' o jeito como o Nav2 e' montado.
GERENCIADORES = ('lifecycle_manager_localization', 'lifecycle_manager_navigation')

# O que fazer a seguir quando um no esperado nao esta' na lista. Uma linha por
# no, porque "falta algo no Nav2" nao ajuda ninguem: saber que falta o
# velocity_smoother resolve o problema em dez segundos.
CURA_NO = {
    'map_server':
        'confira o caminho do mapa que o launch passa (`mapa:=...`): com um .yaml que nao '
        'existe o map_server morre na partida e o resto do Nav2 fica esperando por ele',
    'amcl':
        'sem o amcl nao existe map -> odom nem /amcl_pose: confira se ele esta no launch e '
        'se o lifecycle_manager_localization o tem em `node_names`',
    'lifecycle_manager_localization':
        'sem este gerenciador o map_server e o amcl ficam em unconfigured para sempre, '
        'porque ninguem vai ativa-los: acrescente-o ao launch com node_names '
        "['map_server', 'amcl']",
    'controller_server':
        'e\' ele que gera velocidade (o DWB): confira o launch e o bloco controller_server do '
        'seu nav2.yaml -- sem ele nenhum goal vira movimento',
    'smoother_server':
        'ele esta na lista do lifecycle_manager oficial do Humble: se nao sobe, o gerenciador '
        'trava esperando por ele e os nos seguintes nunca sao ativados',
    'planner_server':
        'e\' ele que calcula a rota (o NavFn): confira o launch e o bloco planner_server do '
        'seu nav2.yaml -- sem ele o goal e\' recusado antes de qualquer movimento',
    'behavior_server':
        'e\' ele que executa backup, spin e wait na recuperacao: sem ele o bt_navigator aborta '
        'no primeiro desvio em vez de se recuperar',
    'bt_navigator':
        'sem o bt_navigator nao existe a acao /navigate_to_pose, e o botao Nav2 Goal do '
        'RViz2 nao tem com quem falar -- e\' o no do G4.1',
    'waypoint_follower':
        'sem o waypoint_follower nao existe /follow_waypoints, que e\' a acao da rota do '
        'G4.2: acrescente-o ao launch e a\' lista do gerenciador de navegacao',
    'velocity_smoother':
        'sem o velocity_smoother ninguem traduz /cmd_vel_nav em /cmd_vel: o controller_server '
        'fala sozinho, o robo nao anda e nenhum no reclama',
    'lifecycle_manager_navigation':
        'sem este gerenciador os seis nos de navegacao ficam em unconfigured, porque ninguem '
        'vai ativa-los: acrescente-o ao launch com a lista do navigation_launch.py',
}

ATIVO = re.compile(r'\bactive\s*\[3\]')
TAXA_HZ = re.compile(r'average rate:\s*([\d.]+)')
TEM_TF = re.compile(r'(?:At time|Translation:|- Translation:)')
SEM_OPCAO = re.compile(r'unrecognized arguments|invalid choice|no such option')

# O limite de cada subprocess, em segundos. Mora num dicionario porque e'
# decidido em `main`, depois do import, e assim nenhuma funcao precisa de
# `global` nem de carregar o valor por seis niveis de chamada.
OPCOES = {'timeout': 6}
# O que a secao 3 viu de cada no (nome curto -> True se `active [3]`). A secao 4
# consulta isto: aresta map -> odom ausente com o AMCL ATIVO e' pose inicial que
# faltou (causa); com o AMCL inativo e' consequencia do ciclo de vida parado.
ATIVOS = {}

pendencias = []                                   # (ordem, nome, o que fazer)
quantos = {'achei': 0, 'nao': 0, 'olhe': 0}


# ---------------------------------------------------------------- relatorio

def marca_de(estado):
    """Cor e rotulo de um estado, lidos na hora de imprimir.

    Lidos na hora, e nao de um dicionario de modulo, porque `--sem-cor` so' e'
    conhecido depois do argparse: um dicionario montado no import guardaria as
    cores antigas.
    """
    return {'achei': (VERDE, 'achei    '),
            'nao': (VERMELHO, 'nao achei'),
            'olhe': (AMARELO, 'olhe     ')}[estado]


def secao(titulo):
    print()
    print(f'{NEGRITO}{titulo}{FIM}')


def conferir(nome, estado, detalhe='', ordem=99, cura=''):
    """Imprime uma linha e, se nao achou, guarda o que fazer para o fim.

    So' `nao achei` entra na lista final. `olhe` nao entra de proposito: ele
    nao e' pendencia, e' o reconhecimento de que um comando nao decide aquilo.
    """
    cor, marca = marca_de(estado)
    quantos[estado] += 1
    print(f'  {cor}{marca}{FIM}  {nome:<44}{detalhe}'.rstrip())
    if estado == 'nao':
        pendencias.append((ordem, nome, cura or detalhe))


def quebrar(texto, largura):
    """Quebra o texto em linhas curtas sem cortar palavra no meio."""
    linhas, atual = [], ''
    for palavra in texto.split():
        if atual and len(atual) + 1 + len(palavra) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f'{atual} {palavra}'.strip()
    if atual:
        linhas.append(atual)
    return linhas


# ---------------------------------------------------------------- subprocess

def rodar(cmd):
    """Roda um comando e devolve (terminou_bem, saida). Nunca levanta excecao.

    Timeout, binario ausente e erro de execucao voltam como terminou_bem=False
    com a saida PARCIAL -- que e' exatamente o que interessa em `ros2 topic hz`
    e em `tf2_echo`, comandos que nao terminam por conta propria: a saida util
    e' a que o timeout interrompe.
    """
    limite = OPCOES['timeout']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=limite)
        return r.returncode == 0, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired as exc:
        partes = []
        for fluxo in (exc.stdout, exc.stderr):
            if not fluxo:
                continue
            partes.append(fluxo.decode('utf-8', 'replace')
                          if isinstance(fluxo, bytes) else fluxo)
        return False, ''.join(partes)
    except (OSError, ValueError) as exc:
        return False, str(exc)


def ultima_linha(saida, padrao='sem saida'):
    linhas = [l.strip() for l in saida.strip().splitlines() if l.strip()]
    return linhas[-1][:56] if linhas else padrao


# ------------------------------------------------- leitura do `topic info`

def contagem(texto, rotulo):
    """O numero de `Publisher count:` / `Subscription count:`, ou None."""
    m = re.search(rotulo + r':\s*(\d+)', texto)
    return int(m.group(1)) if m else None


def pontas(texto, tipo):
    """Nomes de no das pontas de um tipo ('PUBLISHER' ou 'SUBSCRIPTION').

    Le os NOMES e nao so' a contagem porque, com dois publicadores em /cmd_vel,
    saber que sao dois nao ajuda: saber que um deles e' o `piloto` da Aula 11
    diz o que derrubar.
    """
    nomes = []
    for bloco in texto.split('Node name:')[1:]:
        if f'Endpoint type: {tipo}' not in bloco:
            continue
        nomes.append(bloco.splitlines()[0].strip())
    return nomes


def durabilidade_do_publicador(texto):
    """A durabilidade declarada pelo primeiro bloco PUBLISHER, ou ''."""
    for bloco in texto.split('Node name:')[1:]:
        if 'Endpoint type: PUBLISHER' not in bloco:
            continue
        m = re.search(r'Durability:\s*(\w+)', bloco)
        if m:
            return m.group(1)
    return ''


def info_topico(topico):
    return rodar(['ros2', 'topic', 'info', topico, '--verbose'])


def nome_curto(no):
    """O ultimo segmento de /ns/amcl -- o nome que o launch escreveu."""
    return no.rsplit('/', 1)[-1]


# ---------------------------------------------------------------- 1. ambiente

def secao_1_ambiente():
    """O ambiente. Devolve False quando nao ha `ros2` para chamar."""
    secao('1. O ambiente -- sem isto, nada abaixo quer dizer nada')

    caminho = shutil.which('ros2')
    if caminho:
        conferir('comando ros2 no PATH', 'achei', caminho)
    else:
        conferir('comando ros2 no PATH', 'nao', 'which ros2 nao achou nada', ordem=1,
                 cura='rode `source /opt/ros/humble/setup.bash` neste terminal -- sem o ros2 '
                      'no PATH nenhuma outra verificacao deste script quer dizer coisa alguma')

    distro = os.environ.get('ROS_DISTRO', '')
    if distro == 'humble':
        conferir('ROS_DISTRO=humble', 'achei', distro)
    elif distro:
        conferir('ROS_DISTRO=humble', 'olhe',
                 f'ROS_DISTRO={distro} -- a disciplina e\' no Humble; nomes de parametro e '
                 'de plugin mudam entre distros')
    else:
        conferir('ROS_DISTRO=humble', 'nao', 'a variavel nao esta definida', ordem=1,
                 cura='rode `source /opt/ros/humble/setup.bash`: a variavel vazia e\' o '
                      'sinal mais confiavel de que este terminal nunca sourceou o ROS 2')

    # Workspace sourceado: o AMENT_PREFIX_PATH do aluno tem de citar o install
    # do PROJETO dele, e nao so' o /opt/ros. Sem isso o `ros2 launch
    # aula15_nav2 ...` nao acha o pacote, e o erro fala de pacote, nao de source.
    prefixos = [p for p in os.environ.get('AMENT_PREFIX_PATH', '').split(os.pathsep) if p]
    proprios = [p for p in prefixos if not p.startswith('/opt/ros')]
    if proprios:
        conferir('workspace sourceado', 'achei', proprios[0][:56])
    elif prefixos:
        conferir('workspace sourceado', 'nao',
                 f'{len(prefixos)} prefixo(s), todos sob /opt/ros', ordem=1,
                 cura='rode `source "$PB_WS/install/setup.bash"` neste terminal -- sem ele o '
                      '`ros2 launch` nao acha o seu pacote e o erro fala de pacote ausente')
    else:
        conferir('workspace sourceado', 'nao', 'AMENT_PREFIX_PATH vazio', ordem=1,
                 cura='rode `source /opt/ros/humble/setup.bash` e depois `source '
                      '"$PB_WS/install/setup.bash"`, nesta ordem, neste terminal')

    return bool(caminho)


# ---------------------------------------------------------------- 2. nos

def secao_2_nos():
    """Quais dos nos esperados estao no ar. Devolve {curto: nome completo}."""
    secao('2. Os nos no ar -- `ros2 node list`')

    ok, saida = rodar(['ros2', 'node', 'list'])
    nos = [l.strip() for l in saida.splitlines() if l.strip().startswith('/')]
    if not nos:
        conferir('ros2 node list responde', 'olhe', ultima_linha(saida))
        return {}
    conferir('ros2 node list responde', 'achei', f'{len(nos)} no(s) no ar')

    presentes = {}
    for no in nos:
        presentes.setdefault(nome_curto(no), no)

    # Nenhum no do Nav2 no ar: as oito verificacoes seguintes seriam todas eco
    # desta, e uma lista de dez pendencias esconde a unica que importa.
    if not any(n in presentes for n in ESPERADOS):
        conferir('algum no do Nav2 no ar', 'nao',
                 f'nenhum dos {len(ESPERADOS)} nos esperados', ordem=2,
                 cura='suba o Nav2 em OUTRO terminal (`ros2 launch aula15_nav2 '
                      'nav2.launch.py`, ou o launch do SEU projeto) e rode isto de novo; se o '
                      'launch esta no ar e a lista continua vazia, o ROS_DOMAIN_ID dos dois '
                      'terminais nao bate')
        return {}

    for nome in ESPERADOS:
        if nome in presentes:
            conferir(f'no {nome}', 'achei', presentes[nome])
        else:
            conferir(f'no {nome}', 'nao', 'nao esta na lista', ordem=3,
                     cura=CURA_NO[nome])
    return {n: presentes[n] for n in ESPERADOS if n in presentes}


# ---------------------------------------------------------------- 3. ciclo

def secao_3_ciclo(presentes):
    secao('3. O ciclo de vida -- `ros2 lifecycle get` (ativo e\' active [3])')

    alvos = [n for n in ESPERADOS if n in presentes and n not in GERENCIADORES]
    if not alvos:
        conferir('nos de ciclo de vida para consultar', 'olhe',
                 'nenhum no gerenciavel no ar -- so\' os gerenciadores')
        return

    primeiro_inativo = True
    for nome in alvos:
        _, saida = rodar(['ros2', 'lifecycle', 'get', presentes[nome]])
        estado = ultima_linha(saida, '')
        ATIVOS[nome] = bool(ATIVO.search(saida))
        if ATIVOS[nome]:
            conferir(f'ativo: {nome}', 'achei', estado)
        elif not estado:
            conferir(f'ativo: {nome}', 'olhe',
                     f'lifecycle get nao respondeu em {OPCOES["timeout"]}s')
        elif primeiro_inativo:
            # O primeiro da ordem de subida que nao esta ativo e' onde o
            # gerenciador parou. Os de baixo estao inativos por consequencia:
            # tratar todos como causa manda o aluno consertar o lugar errado.
            primeiro_inativo = False
            conferir(f'ativo: {nome}', 'nao', estado, ordem=5,
                     cura=f'este e\' o primeiro da ordem de subida que nao esta ativo: o '
                          f'gerenciador parou AQUI -- ou alguem o desativou a mao. Se a '
                          f'lista tambem acusar `map -> odom` ausente ACIMA desta linha, '
                          f'comece por ela (e\' a pose inicial, e este no e\' consequencia). '
                          f'Senao, leia o terminal do lifecycle_manager, que nomeia o no em '
                          f'que travou, e tente a mao com `ros2 lifecycle set '
                          f'{presentes[nome]} configure` para ver o erro que ele engoliu')
        else:
            conferir(f'ativo: {nome}', 'nao', estado, ordem=6,
                     cura=f'provavelmente consequencia, nao causa: o gerenciador ativa um no '
                          f'por vez e parou antes de chegar em {nome}. Conserte o primeiro '
                          f'inativo da lista acima e rode isto de novo')


# ---------------------------------------------------------------- 4. TF

def secao_4_tf():
    secao('4. A TF -- /tf_static e a aresta map -> odom')

    # /tf_static e' transient local: um `topic echo` com durabilidade volatile
    # (o padrao) NAO recebe a mensagem latched e parece que ninguem publica. E'
    # a mesma armadilha de QoS da Aula 13, de novo.
    cmd = ['ros2', 'topic', 'echo', '/tf_static', '--once',
           '--qos-durability', 'transient_local', '--qos-reliability', 'reliable']
    _, saida = rodar(cmd)
    if SEM_OPCAO.search(saida):
        _, saida = rodar(['ros2', 'topic', 'echo', '/tf_static', '--once'])
    quantas = saida.count('child_frame_id')
    if quantas:
        conferir('/tf_static tem mensagem', 'achei', f'{quantas} transformada(s) estatica(s)')
    else:
        conferir('/tf_static tem mensagem', 'nao',
                 f'nada chegou em {OPCOES["timeout"]}s', ordem=20,
                 cura='rode `ros2 run tf2_tools view_frames` e abra o PDF: se faltar a aresta '
                      'base_footprint -> laser_frame, e\' um static_transform_publisher que '
                      'nao subiu, e sem ela o AMCL descarta todo /scan que chega')

    # A aresta que decide o TP4. tf2_echo nao termina sozinho no Humble e nao
    # aceita --timeout: quem corta e' o timeout do subprocess, e a saida
    # parcial ja' tem a transformada se ela existir.
    _, tf = rodar(['ros2', 'run', 'tf2_ros', 'tf2_echo', 'map', 'odom'])
    if TEM_TF.search(tf):
        linha = next((l.strip() for l in tf.splitlines() if 'Translation' in l), 'existe')
        conferir('aresta map -> odom', 'achei', linha[:56])
    elif ATIVOS.get('amcl') is False:
        # O AMCL nem esta ativo: a aresta ausente e' consequencia do ciclo de
        # vida, e mandar dar a pose inicial seria apontar para o lugar errado.
        conferir('aresta map -> odom', 'nao',
                 'o AMCL nao esta ativo -- ninguem publica esta aresta ainda', ordem=10,
                 cura='consequencia, nao causa: resolva primeiro o ciclo de vida (a secao 3 '
                      'acima diz onde o gerenciador parou). A aresta aparece sozinha depois '
                      'que o AMCL ativar E receber a pose inicial')
    else:
        conferir('aresta map -> odom', 'nao',
                 f'tf2_echo map odom nao devolveu transformada em {OPCOES["timeout"]}s',
                 ordem=4,
                 cura='quem publica essa aresta e\' o AMCL, e no Humble ele nao publica NADA '
                      'antes da pose inicial (`if (!initial_pose_is_known_) return;`): clique '
                      'o 2D Pose Estimate no RViz2, ou suba o launch com '
                      '`pose_inicial_auto:=true`. Sem o quadro `map` o planner_server fica '
                      'preso em "Timed out waiting for transform from base_footprint to '
                      'map" e o gerenciador de navegacao para nele -- por isso este item vem '
                      'ANTES de qualquer no inativo na lista: de a pose e rode isto de novo')


# ---------------------------------------------------------------- 5. pose

def secao_5_pose():
    secao('5. A pose inicial -- /amcl_pose')

    _, info = info_topico('/amcl_pose')
    pubs = contagem(info, 'Publisher count')
    if pubs is None:
        conferir('/amcl_pose tem publicador', 'olhe', ultima_linha(info))
        return
    if pubs >= 1:
        conferir('/amcl_pose tem publicador', 'achei',
                 ', '.join(pontas(info, 'PUBLISHER')) or f'{pubs} publicador(es)')
    else:
        conferir('/amcl_pose tem publicador', 'nao', 'Publisher count: 0', ordem=11,
                 cura='o amcl nao esta no ar ou nao esta ativo: volte as secoes 2 e 3 -- este '
                      'topico so\' existe porque o amcl o cria')
        return

    # Ter publicador nao e' ter publicado. No Humble o AMCL cria o topico na
    # configuracao e so' escreve nele depois da pose inicial, e e' por isso que
    # esta linha e' separada da de cima.
    _, msg = rodar(['ros2', 'topic', 'echo', '/amcl_pose', '--once'])
    if 'covariance' in msg or 'position' in msg:
        conferir('/amcl_pose ja publicou', 'achei', 'chegou uma mensagem')
    else:
        conferir('/amcl_pose ja publicou', 'nao',
                 f'nenhuma mensagem em {OPCOES["timeout"]}s', ordem=11,
                 cura='de a pose inicial: 2D Pose Estimate no RViz2, ou suba com '
                      '`pose_inicial_auto:=true`. Se voce JA deu, mande um goal e rode isto de '
                      'novo -- parado o AMCL pode ficar calado, e nuvem que nao aparece no '
                      'RViz2 tem essa mesma causa')


# ---------------------------------------------------------------- 6. cmd_vel

def secao_6_cmd_vel():
    secao('6. O /cmd_vel -- dois publicadores e\' defeito, e nao da erro')

    _, info = info_topico('/cmd_vel')
    pubs = contagem(info, 'Publisher count')
    assina = contagem(info, 'Subscription count')
    if pubs is None:
        conferir('/cmd_vel tem UM publicador', 'olhe', ultima_linha(info))
        return

    nomes = pontas(info, 'PUBLISHER')
    if pubs == 1:
        conferir('/cmd_vel tem UM publicador', 'achei', ', '.join(nomes) or '1 publicador')
    elif pubs == 0:
        conferir('/cmd_vel tem UM publicador', 'nao', 'Publisher count: 0', ordem=12,
                 cura='ninguem fala em /cmd_vel: o velocity_smoother nao esta ativo (secao 3), '
                      'ou o remapeamento cmd_vel_smoothed -> cmd_vel saiu do launch')
    else:
        conferir('/cmd_vel tem UM publicador', 'nao',
                 f'{pubs} publicadores: ' + ', '.join(nomes), ordem=6,
                 cura='derrube o que NAO e\' o velocity_smoother (o piloto reativo da Aula '
                      '11 com `piloto:=false`, um teleop_twist_keyboard esquecido, um segundo '
                      'launch no ar): o robo obedece ao ultimo que falou, o sintoma e\' andar '
                      'truncado e nenhum no emite aviso')

    if assina is None or assina >= 1:
        conferir('/cmd_vel tem assinante', 'achei',
                 ', '.join(pontas(info, 'SUBSCRIPTION')) or 'ha assinante')
    else:
        conferir('/cmd_vel tem assinante', 'nao', 'Subscription count: 0', ordem=12,
                 cura='o Nav2 manda velocidade e ninguem ouve: suba o no do robo (o `mundo` da '
                      'Aula 11, ou a sua base) -- planejar funciona e o robo fica parado')


# ---------------------------------------------------------------- 7. cadeia

def secao_7_cadeia():
    secao('7. A cadeia do /cmd_vel -- /cmd_vel_nav, do controlador ao suavizador')

    _, info = info_topico('/cmd_vel_nav')
    pubs = contagem(info, 'Publisher count')
    assina = contagem(info, 'Subscription count')
    if pubs is None:
        conferir('/cmd_vel_nav ligado nas duas pontas', 'olhe', ultima_linha(info))
    elif pubs >= 1 and (assina or 0) >= 1:
        conferir('/cmd_vel_nav ligado nas duas pontas', 'achei',
                 f'{pubs} -> {assina}: ' + ', '.join(pontas(info, 'PUBLISHER') +
                                                     pontas(info, 'SUBSCRIPTION')))
    elif pubs >= 1:
        conferir('/cmd_vel_nav ligado nas duas pontas', 'nao',
                 f'{pubs} publicador(es) e nenhum assinante', ordem=13,
                 cura='o controller_server fala em /cmd_vel_nav e ninguem ouve: o '
                      'velocity_smoother saiu do launch, ou saiu com os remapeamentos '
                      '(cmd_vel -> cmd_vel_nav, cmd_vel_smoothed -> cmd_vel) ainda no lugar')
    else:
        conferir('/cmd_vel_nav ligado nas duas pontas', 'nao',
                 'nenhum publicador', ordem=13,
                 cura='o remapeamento `cmd_vel -> cmd_vel_nav` do controller_server nao esta '
                      'no launch: compare com o navigation_launch.py do Humble')

    # Trafego aqui so' existe com goal ativo. Por isso a ausencia NUNCA vira
    # pendencia: o script nao tem como saber se ha um goal em curso, e acusar
    # defeito num robo parado seria inventar um veredito.
    _, hz = rodar(['ros2', 'topic', 'hz', '/cmd_vel_nav'])
    m = TAXA_HZ.search(hz)
    if m:
        conferir('trafego em /cmd_vel_nav', 'achei',
                 f'{m.group(1)} Hz -- ha um goal em curso')
    else:
        conferir('trafego em /cmd_vel_nav', 'olhe',
                 f'sem taxa em {OPCOES["timeout"]}s -- sem goal ativo isto nao quer dizer '
                 f'nada; COM um goal em curso, aponta o controller_server')


# ---------------------------------------------------------------- 8. acoes

def secao_8_acoes():
    secao('8. Os servidores de acao -- `ros2 action list`')

    ok, saida = rodar(['ros2', 'action', 'list'])
    acoes = [l.strip() for l in saida.splitlines() if l.strip().startswith('/')]
    if not acoes:
        conferir('ros2 action list responde', 'olhe', ultima_linha(saida))
        return
    conferir('ros2 action list responde', 'achei', f'{len(acoes)} acao(oes)')

    if '/navigate_to_pose' in acoes:
        conferir('/navigate_to_pose existe', 'achei', 'e\' a acao do G4.1')
    else:
        conferir('/navigate_to_pose existe', 'nao', 'nao esta na lista', ordem=14,
                 cura='quem serve essa acao e\' o bt_navigator: confira se ele esta no ar '
                      '(secao 2) e ATIVO (secao 3) -- sem ela o Nav2 Goal do RViz2 nao tem '
                      'com quem falar, e o G4.1 nao tem como fechar')

    rota = [a for a in ('/follow_waypoints', '/navigate_through_poses') if a in acoes]
    if rota:
        conferir('acao de rota para o G4.2', 'achei', ', '.join(rota))
    else:
        conferir('acao de rota para o G4.2', 'nao',
                 'nem /follow_waypoints nem /navigate_through_poses', ordem=15,
                 cura='uma das duas basta para a rota de tres waypoints: '
                      '/follow_waypoints vem do waypoint_follower e '
                      '/navigate_through_poses vem do bt_navigator -- confira esses dois nos '
                      'nas secoes 2 e 3')


# ---------------------------------------------------------------- 9. costmaps

def secao_9_costmaps():
    secao('9. Os costmaps -- global e local com publicador')

    alvos = (('/global_costmap/costmap', 'planner_server',
              'e\' o planner_server que publica este: confira se ele esta ativo e se o '
              'bloco global_costmap do seu nav2.yaml tem o mesmo nome de frame que a sua TF'),
             ('/local_costmap/costmap', 'controller_server',
              'e\' o controller_server que publica este: confira se ele esta ativo e se o '
              'bloco local_costmap do seu nav2.yaml aponta o /scan e o frame do SEU robo'))
    for topico, dono, cura in alvos:
        _, info = info_topico(topico)
        pubs = contagem(info, 'Publisher count')
        if pubs is None:
            conferir(f'{topico} com publicador', 'olhe', ultima_linha(info))
        elif pubs >= 1:
            conferir(f'{topico} com publicador', 'achei', dono)
        else:
            conferir(f'{topico} com publicador', 'nao', 'Publisher count: 0', ordem=16,
                     cura=cura)


# ---------------------------------------------------------------- 10. mapa

def secao_10_mapa():
    secao('10. O mapa -- /map com durabilidade transient local')

    _, info = info_topico('/map')
    pubs = contagem(info, 'Publisher count')
    if pubs is None:
        conferir('/map com publicador', 'olhe', ultima_linha(info))
        return
    if pubs >= 1:
        conferir('/map com publicador', 'achei',
                 ', '.join(pontas(info, 'PUBLISHER')) or f'{pubs} publicador(es)')
    else:
        conferir('/map com publicador', 'nao', 'Publisher count: 0', ordem=17,
                 cura='o map_server nao esta ativo (secoes 2 e 3), ou morreu lendo o '
                      'mapa.yaml: leia o terminal do launch, que traz o caminho que ele tentou')
        return

    # O mapa e' publicado UMA vez. Sem transient local, quem assina depois --
    # o RViz2, o AMCL, os costmaps -- nunca recebe nada, e o sintoma e' um
    # RViz2 cinza sem nenhuma mensagem de erro.
    durabilidade = durabilidade_do_publicador(info).upper()
    if durabilidade == 'TRANSIENT_LOCAL':
        conferir('/map durabilidade transient local', 'achei', durabilidade)
    elif durabilidade:
        conferir('/map durabilidade transient local', 'nao', durabilidade, ordem=18,
                 cura='o mapa e\' publicado uma unica vez: com durabilidade VOLATILE quem '
                      'assina depois (RViz2, AMCL, costmaps) nunca recebe nada. No RViz2, o '
                      'display Map tem de estar com Durability Policy = Transient Local')
    else:
        conferir('/map durabilidade transient local', 'olhe',
                 'o topic info --verbose nao trouxe a linha Durability')


# ------------------------------------------------- o que nao alcanca

def secao_fora_de_alcance():
    """O que este script nao alcanca -- declarado, nao insinuado.

    Esta secao imprime sempre, inclusive com --rapido e inclusive quando nao
    sobrou pendencia nenhuma. E' a parte mais importante da saida: tudo que
    decide o G4.1 e o G4.2 esta' aqui, e nada disto sai de comando nenhum.
    """
    secao('O que este script NAO alcanca -- e e\' o que os gates cobram')
    conferir('o robo realmente anda', 'olhe',
             'topico com trafego nao e\' robo em movimento; olhe o RViz2 e o Gazebo')
    conferir('o mapa e\' do SEU cenario', 'olhe',
             'ele confere que /map tem publicador, nao QUE mapa e\' esse')
    conferir('a rota faz sentido', 'olhe',
             'tres waypoints alcancaveis, na sua planta, sao leitura sua')
    conferir('o relatorio responde ao enunciado', 'olhe',
             'a referencia e\' o enunciado do TP4, e quem le e\' o professor')


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(
        prog='diagnosticar_nav2.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Diz ONDE olhar quando o Nav2 nao navega, com ele no ar. NAO corrige, '
                    'NAO valida, NAO antecipa nota e NAO substitui o enunciado do TP4.',
        epilog='Dez verificacoes, na ordem em que compensa olhar: ambiente, nos no ar, ciclo '
               'de vida, TF, pose inicial, publicadores de /cmd_vel, a cadeia do /cmd_vel, '
               'servidores de acao, costmaps e o mapa.\n\n'
               'Rode com o Nav2 no ar, em OUTRO terminal:\n'
               '  python3 diagnosticar_nav2.py\n'
               '  python3 diagnosticar_nav2.py --rapido        # so 1, 2, 3 e 6\n'
               '  python3 diagnosticar_nav2.py --timeout 10    # rede lenta, maquina cheia\n'
               '  python3 diagnosticar_nav2.py --sem-cor | tee diagnostico.txt\n\n'
               'Estados: achei / nao achei / olhe. Nao existe ok, falha nem passou -- o '
               'script nao tem como saber se esta certo. Saida 1 quando sobrou algo para '
               'olhar, 0 quando nao sobrou, e nenhuma das duas e um julgamento da entrega.')
    ap.add_argument('--rapido', action='store_true',
                    help='so as quatro verificacoes mais rapidas (1 ambiente, 2 nos, '
                         '3 ciclo de vida, 6 publicadores de /cmd_vel)')
    ap.add_argument('--timeout', type=int, default=6, metavar='N',
                    help='segundos de paciencia com cada comando (padrao: 6)')
    ap.add_argument('--sem-cor', action='store_true',
                    help='sem codigos de cor, mesmo em terminal')
    args = ap.parse_args()

    if args.timeout < 1:
        print('--timeout precisa ser pelo menos 1 segundo', file=sys.stderr)
        return 2
    OPCOES['timeout'] = args.timeout

    if args.sem_cor:
        global VERDE, VERMELHO, AMARELO, NEGRITO, FIM        # noqa: PLW0603
        VERDE = VERMELHO = AMARELO = NEGRITO = FIM = ''

    print(f'{NEGRITO}diagnosticar_nav2{FIM} -- onde olhar quando o Nav2 nao navega '
          f'(Aula 16, clinica)')
    print(f'{AMARELO}Isto nao corrige, nao valida, nao antecipa nota e nao substitui o '
          f'enunciado.{FIM}')
    print('E um apoio: ele diz ONDE olhar primeiro. A referencia e o enunciado do TP4, e a')
    print('responsabilidade pela entrega e sua. "achei" nao quer dizer certo; "nao achei"')
    print('nao quer dizer errado. Quer dizer, nos dois casos: va olhar isso.')
    print(f'paciencia por comando: {args.timeout}s'
          + ('   modo --rapido: so as verificacoes 1, 2, 3 e 6' if args.rapido else ''))

    tem_ros2 = secao_1_ambiente()
    if not tem_ros2:
        secao('2 a 10 -- nao olhado')
        conferir('nos, ciclo de vida, TF, pose e topicos', 'olhe',
                 'sem o comando ros2 nao ha o que consultar')
        secao_fora_de_alcance()
        return fechar()

    presentes = secao_2_nos()
    if not presentes:
        secao('3 a 10 -- nao olhado')
        conferir('ciclo de vida, TF, pose, topicos e acoes', 'olhe',
                 'sem no do Nav2 no ar, tudo abaixo seria eco da linha acima')
        secao_fora_de_alcance()
        return fechar()

    secao_3_ciclo(presentes)
    # As secoes saem sempre em ordem numerica, inclusive com --rapido: a saida
    # e' lida numa clinica, em voz alta, e um relatorio que pula de 3 para 6 e
    # volta para 4 custa a atencao de quem esta ouvindo.
    if args.rapido:
        secao_6_cmd_vel()
        secao('4, 5, 7, 8, 9 e 10 -- nao olhado')
        conferir('TF, pose, cadeia, acoes, costmaps e mapa', 'olhe',
                 'rode sem --rapido para olhar tambem estas')
    else:
        secao_4_tf()
        secao_5_pose()
        secao_6_cmd_vel()
        secao_7_cadeia()
        secao_8_acoes()
        secao_9_costmaps()
        secao_10_mapa()

    secao_fora_de_alcance()
    return fechar()


def fechar() -> int:
    """A contagem, a lista do que fazer, e o que a lista vazia nao significa."""
    print()
    print(f'{quantos["achei"]} achei, {quantos["nao"]} nao achei, {quantos["olhe"]} '
          f'fora do alcance de um comando')

    if not pendencias:
        print(f'{VERDE}Nao sobrou nada para olhar do que este script alcanca.{FIM}')
        print('Isso NAO quer dizer que o Nav2 esta pronto, e nao quer dizer que o G4.1 fecha.')
        print('Quer dizer que esgotei o que um script enxerga -- e o que ele nao enxerga (se')
        print('o robo anda mesmo, se o mapa e do seu cenario, se a rota faz sentido, se o')
        print('relatorio responde ao que foi pedido) e justamente o que os gates cobram.')
        print('Releia os "olhe" acima e o enunciado do TP4.')
        return 0

    print()
    print(f'{NEGRITO}Onde olhar, na ordem em que costuma compensar:{FIM}')
    for i, (_, nome, cura) in enumerate(sorted(pendencias, key=lambda x: x[0]), 1):
        print(f'  {i:>2}. {VERMELHO}{nome}{FIM}')
        for linha in quebrar(cura, 72):
            print(f'      {linha}')
    print()
    print('Nenhuma dessas linhas e um veredito sobre a sua entrega: sao lugares para olhar.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
