#!/usr/bin/env python3
"""Confere a entrega do TP3 item por item e diz o que ainda falta.

Por que isto existe: na quinta-feira ninguem tem tempo de reler o enunciado e
cruzar com o repositorio. O que sobra para fazer e' rodar uma verificacao que
falha sozinha. Cada linha abaixo e' um fato sobre o SEU repositorio -- existe
ou nao existe, parseia ou nao parseia, esta' no git ou nao esta'.

O que ele NAO faz: nota. Qualidade do texto, explicacao de cada frame no
relatorio, adequacao das escolhas ao seu projeto -- isso o professor avalia
lendo. Um "ok" aqui nao e' nota, e um "?" nao e' erro: e' algo que este script
nao consegue provar por comando.

    cd ~/projeto-pb-SEU-USUARIO
    python3 conferir_tp3.py                   # o que da' para conferir sem ROS 2
    python3 conferir_tp3.py --ao-vivo         # tambem topicos e TF, com tudo no ar
    python3 conferir_tp3.py --raiz ~/projeto-pb-SEU-USUARIO

Saida 0 quando nada falta; 1 quando falta alguma coisa.
Gates cobertos: G3.0 a G3.6 (recursos/gates-tps.md).
"""
import argparse
import ast
import pathlib
import re
import subprocess
import sys

TP = 'tp3'
PRAZO = 'sexta, 23/10'

# Pastas que sao resultado de build ou do git: achado la' dentro nao e' entrega.
IGNORAR = {'.git', 'build', 'install', 'log', '__pycache__', 'node_modules',
           '.venv', 'venv', '.mypy_cache', '.pytest_cache'}

IMAGENS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')

REF_RVIZ = re.compile(r'[\w./-]*\.rviz\b')
REF_YAML = re.compile(r'[\w./-]*\.ya?ml\b')
REF_URDF = re.compile(r'[\w./-]*\.(?:urdf|xacro)\b')
PUBLISHERS = re.compile(r'[Pp]ublisher count:\s*(\d+)')
TAXA_HZ = re.compile(r'average rate:\s*([\d.]+)')
TEM_TF = re.compile(r'(?:At time|Translation:|- Translation:)')

VERDE, VERMELHO, AMARELO, NEGRITO, FIM = (
    '\033[32m', '\033[31m', '\033[33m', '\033[1m', '\033[0m')

# Degrada para texto puro quando a saida nao e' terminal -- redirecionar para
# arquivo ou canalizar para `tee` nao deve encher o texto de lixo de escape.
if not sys.stdout.isatty():
    VERDE = VERMELHO = AMARELO = NEGRITO = FIM = ''

ESTADOS = {'ok': (VERDE, 'ok   '), 'falta': (VERMELHO, 'falta'), '?': (AMARELO, '?    ')}

pendencias = []          # (ordem, nome, cura) -- so' do que esta' faltando
quantos = {'ok': 0, 'falta': 0, '?': 0}


# ---------------------------------------------------------------- relatorio

def secao(titulo):
    print()
    print(f'{NEGRITO}{titulo}{FIM}')


def conferir(nome, estado, detalhe='', ordem=99, cura=''):
    """Imprime uma linha do relatorio e, se faltou, guarda para a lista final."""
    cor, marca = ESTADOS[estado]
    quantos[estado] += 1
    print(f'  {cor}{marca}{FIM}  {nome:<46}{detalhe}'.rstrip())
    if estado == 'falta':
        pendencias.append((ordem, nome, cura or detalhe))


# ---------------------------------------------------------------- arquivos

def achar(raiz, padrao):
    """Arquivos que casam com o padrao, fora das pastas de build e do .git."""
    return sorted(p for p in raiz.rglob(padrao) if not IGNORAR & set(p.parts))


def rel(raiz, caminho):
    try:
        return str(caminho.relative_to(raiz))
    except ValueError:
        return str(caminho)


def resolver(raiz, ref):
    """Onde um caminho citado no launch realmente esta', se estiver em algum lugar.

    O launch quase nunca cita o caminho completo -- ele monta com
    os.path.join(share, 'rviz', 'x.rviz'). Entao: tenta como caminho relativo a'
    raiz e, se nao achar, procura pelo nome do arquivo no repositorio inteiro.
    """
    ref = ref.strip().strip('\'"')
    if not ref or ref.startswith('/'):
        return None
    alvo = raiz / ref
    if alvo.exists():
        return alvo
    achados = achar(raiz, pathlib.Path(ref).name)
    return achados[0] if achados else None


def imagens_de(pasta):
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGENS)


def com_pista(arquivos, pistas):
    return [p for p in arquivos if any(x in p.name.lower() for x in pistas)]


def ler(caminho):
    try:
        return caminho.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def sem_comentarios(texto):
    """O texto sem as linhas de comentario: um `# falta Gazebo` nao e' Gazebo."""
    return '\n'.join(re.sub(r'#.*$', '', l) for l in texto.splitlines())


def texto_efetivo(caminho):
    """O que o arquivo DIZ ao ROS 2, sem comentarios e sem docstring.

    Existe porque um docstring escrito "falta subir o Gazebo" fazia este
    conferidor responder que o launch menciona Gazebo -- verificacao que se
    engana com a anotacao do proprio aluno nao vale nada. Num .py o arquivo e'
    lido pela arvore sintatica: nomes, atributos, argumentos e literais de
    texto que nao sejam docstring. Se nao parseia, cai para o texto cru sem
    comentario, que e' pior mas ainda melhor que nada.
    """
    texto = ler(caminho)
    if caminho.suffix != '.py':
        return sem_comentarios(texto)
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return sem_comentarios(texto)

    docstrings = set()
    for no in ast.walk(arvore):
        corpo = getattr(no, 'body', None)
        if not isinstance(corpo, list) or not corpo:
            continue
        if not isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef,
                               ast.AsyncFunctionDef)):
            continue
        zero = corpo[0]
        if (isinstance(zero, ast.Expr) and isinstance(zero.value, ast.Constant)
                and isinstance(zero.value.value, str)):
            docstrings.add(id(zero.value))

    pedacos = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            if id(no) not in docstrings:
                pedacos.append(no.value)
        elif isinstance(no, ast.Name):
            pedacos.append(no.id)
        elif isinstance(no, ast.Attribute):
            pedacos.append(no.attr)
        elif isinstance(no, ast.keyword) and no.arg:
            pedacos.append(no.arg)
        elif isinstance(no, ast.alias):
            pedacos.append(f'{no.name} {no.asname or ""}')
    return '\n'.join(pedacos)


# ---------------------------------------------------------------- subprocess

def rodar(cmd, timeout=8):
    """Roda um comando e devolve (terminou_bem, saida). Nunca levanta excecao.

    Timeout, binario ausente e erro de execucao voltam como terminou_bem=False
    com a saida parcial -- que e' o que interessa em `ros2 topic hz`, um comando
    que nao termina por conta propria: a saida util e' justamente a parcial.
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
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


def git(raiz, *args, timeout=15):
    return rodar(['git', '-C', str(raiz), *args], timeout=timeout)


# ---------------------------------------------------------------- item 1

def item1(raiz):
    """Launch principal: um comando sobe o sistema inteiro (G3.0, G3.1)."""
    secao('1. Launch principal -- um comando sobe tudo        [G3.0, G3.1]')
    launches = achar(raiz, 'bringup.launch.py')

    if not launches:
        conferir('existe bringup.launch.py', 'falta', 'nao achei nenhum', ordem=10,
                 cura='crie launch/bringup.launch.py no seu pacote -- este e\' o G3.0, '
                      'e tudo depois dele depende dele')
        return None
    if len(launches) > 1:
        conferir('existe UM bringup.launch.py', 'falta',
                 f'achei {len(launches)}: ' + ', '.join(rel(raiz, p) for p in launches),
                 ordem=10,
                 cura='mantenha um so\' bringup.launch.py -- com dois, nem voce nem o '
                      'professor sabem qual `ros2 launch` vai pegar')
    else:
        conferir('existe UM bringup.launch.py', 'ok', rel(raiz, launches[0]))

    launch = launches[0]

    try:
        ast.parse(ler(launch), filename=str(launch))
        conferir('sintaxe valida (ast.parse)', 'ok')
    except SyntaxError as exc:
        conferir('sintaxe valida (ast.parse)', 'falta',
                 f'linha {exc.lineno}: {exc.msg}', ordem=11,
                 cura=f'conserte a sintaxe de {rel(raiz, launch)} linha {exc.lineno} '
                      f'({exc.msg}) -- launch que nao parseia nao sobe nada')

    # Daqui para baixo le o launch sem docstring nem comentario: e' o que ele
    # manda o ROS 2 fazer, nao o que ele diz que pretende fazer.
    texto = texto_efetivo(launch)

    # Cada um reportado separado: saber que "falta algo no launch" nao ajuda;
    # saber que falta o robot_state_publisher ajuda.
    if re.search(r'ros_gz|gz_sim|gazebo', texto, re.I):
        achado = re.search(r'ros_gz\w*|gz_sim\w*|gazebo\w*', texto, re.I)
        conferir('menciona Gazebo', 'ok', achado.group(0))
    else:
        conferir('menciona Gazebo', 'falta', 'procurei ros_gz, gz_sim, gazebo', ordem=12,
                 cura='inclua a subida do Gazebo com o mundo do projeto no bringup '
                      '(ros_gz_sim / gz_sim / gazebo_ros)')

    if 'robot_state_publisher' in texto:
        conferir('menciona robot_state_publisher', 'ok')
    else:
        conferir('menciona robot_state_publisher', 'falta', 'nao achei', ordem=13,
                 cura='adicione o robot_state_publisher com o URDF ao bringup -- sem ele '
                      'nao ha\' TF do robo, e o G3.2 nao fecha')

    # RViz2 + o .rviz salvo, que o enunciado pede que esteja no repositorio.
    tem_rviz2 = bool(re.search(r'\brviz2\b', texto))
    conferir('menciona rviz2', 'ok' if tem_rviz2 else 'falta',
             '' if tem_rviz2 else 'nao achei "rviz2" no launch', ordem=14,
             cura='suba o rviz2 pelo bringup, com -d apontando para o seu .rviz')

    refs_rviz = sorted({m.group(0) for m in REF_RVIZ.finditer(texto) if m.group(0)})
    if not refs_rviz:
        conferir('.rviz referenciado existe no disco', 'falta',
                 'o launch nao cita nenhum arquivo .rviz', ordem=14,
                 cura='salve a configuracao do RViz2 (File > Save Config As) em '
                      'rviz/*.rviz, versione, e aponte o launch para ela')
    else:
        achados = [(r, resolver(raiz, r)) for r in refs_rviz]
        faltando = [r for r, p in achados if p is None]
        if faltando:
            conferir('.rviz referenciado existe no disco', 'falta',
                     'citado e nao achado: ' + ', '.join(faltando), ordem=14,
                     cura=f'o launch pede {faltando[0]} e esse arquivo nao esta\' no '
                          f'repositorio -- salve e commite o .rviz')
        else:
            conferir('.rviz referenciado existe no disco', 'ok',
                     ', '.join(rel(raiz, p) for _, p in achados))

    # YAML de parametros: os mapas nao contam, eles sao o G3.3.
    refs_yaml = sorted({m.group(0) for m in REF_YAML.finditer(texto) if m.group(0)})
    params = []
    for r in refs_yaml:
        alvo = resolver(raiz, r)
        if alvo is not None and 'maps' not in alvo.parts:
            params.append(alvo)
    if params:
        conferir('YAML de parametros existe no disco', 'ok',
                 ', '.join(rel(raiz, p) for p in params[:3]))
    elif refs_yaml:
        conferir('YAML de parametros existe no disco', 'falta',
                 'citados e nao achados (ou so\' mapas): ' + ', '.join(refs_yaml), ordem=15,
                 cura='o launch cita YAML que nao esta\' no repositorio -- commite o '
                      'config/*.yaml de parametros (mapa.yaml nao conta, e\' o G3.3)')
    else:
        conferir('YAML de parametros existe no disco', 'falta',
                 'o launch nao cita nenhum .yaml de parametros', ordem=15,
                 cura='tire os numeros do codigo e passe por config/*.yaml no bringup -- '
                      'o enunciado pede parametros via YAML')

    urdfs = achar(raiz, '*.urdf') + achar(raiz, '*.xacro')
    if urdfs:
        conferir('existe URDF/xacro', 'ok', f'{len(urdfs)}: ' + rel(raiz, urdfs[0]))
    else:
        conferir('existe URDF/xacro', 'falta', 'nenhum .urdf nem .xacro', ordem=16,
                 cura='versione o URDF/xacro do robo (vem do TP2) -- e\' o que o '
                      'robot_state_publisher carrega')
    return launch


# ---------------------------------------------------------------- item 2

def item2(raiz, launch, evid):
    """TFs e SLAM: arvore completa e mapa persistido (G3.2, G3.3)."""
    secao('2. TFs e SLAM -- arvore completa e mapa salvo      [G3.2, G3.3]')

    frames = evid / 'frames.pdf'
    if frames.is_file() and frames.stat().st_size > 0:
        conferir('docs/evidencias/tp3/frames.pdf', 'ok', f'{frames.stat().st_size} bytes')
    else:
        conferir('docs/evidencias/tp3/frames.pdf', 'falta', 'nao achei (ou vazio)', ordem=20,
                 cura='com o sistema no ar: `ros2 run tf2_tools view_frames` e mova o PDF '
                      'para docs/evidencias/tp3/frames.pdf -- e\' o G3.2, o gate de verdade '
                      'deste TP')
    conferir('cada frame explicado no relatorio', '?',
             'leitura do professor -- confira que map, odom e base_link tem paragrafo')

    # SLAM Toolbox integrado: o que da' para provar por comando e' a referencia
    # em launch ou config; se o mapa saiu, ele rodou.
    fontes = [launch] if launch else []
    fontes += achar(raiz, '*.launch.py') + achar(raiz, '*.yaml') + achar(raiz, '*.py')
    citou = next((p for p in fontes if 'slam_toolbox' in texto_efetivo(p)), None)
    if citou is not None:
        conferir('slam_toolbox referenciado', 'ok', rel(raiz, citou))
    else:
        conferir('slam_toolbox referenciado', 'falta',
                 'nao achei "slam_toolbox" em launch nem config', ordem=21,
                 cura='integre o slam_toolbox ao bringup (online_async) com o YAML de '
                      'parametros apontando base_frame e scan_topic do SEU robo')

    mapas = raiz / 'maps'
    pgm, mapa_yaml = mapas / 'mapa.pgm', mapas / 'mapa.yaml'
    tem_par = pgm.is_file() and mapa_yaml.is_file()
    if tem_par:
        conferir('maps/mapa.pgm + maps/mapa.yaml', 'ok',
                 f'{pgm.stat().st_size} bytes no .pgm')
    else:
        achou = [rel(raiz, p) for p in achar(raiz, 'mapa.*')]
        conferir('maps/mapa.pgm + maps/mapa.yaml', 'falta',
                 ('achei fora de maps/: ' + ', '.join(achou)) if achou else 'nao achei',
                 ordem=30,
                 cura='com o launch rodando: `mkdir -p "$PB_DIR/maps" && cd "$PB_DIR/maps" '
                      '&& ros2 run nav2_map_server map_saver_cli -f mapa` (G3.3)')

    if tem_par:
        conferir_mapa_yaml(raiz, mapa_yaml, pgm)


def conferir_mapa_yaml(raiz, mapa_yaml, pgm):
    """O mapa.yaml parseia e a chave image aponta para um PGM que existe?

    O erro comum e' commitar o .yaml de um salvamento e o .pgm de outro, ou
    renomear um dos dois: o par quebra e o map_server nao abre o mapa.
    """
    texto = ler(mapa_yaml)
    doc, como = None, ''
    try:
        import yaml                                                   # noqa: PLC0415
        try:
            doc = yaml.safe_load(texto) or {}
            conferir('mapa.yaml parseia', 'ok', 'yaml.safe_load')
        except Exception as exc:                                      # noqa: BLE001
            conferir('mapa.yaml parseia', 'falta',
                     str(exc).splitlines()[0][:60], ordem=30,
                     cura=f'{rel(raiz, mapa_yaml)} nao e\' YAML valido -- salve o mapa de '
                          f'novo com map_saver_cli em vez de editar a mao')
            return
    except ImportError:
        como = ' (sem python3-yaml: leitura simples da chave image)'
        conferir('mapa.yaml parseia', '?',
                 'falta python3-yaml -- `sudo apt install python3-yaml` para conferir '
                 'de verdade')

    if doc is not None:
        imagem = str(doc.get('image', '') or '')
    else:
        m = re.search(r'^\s*image\s*:\s*(.+?)\s*$', texto, re.M)
        imagem = m.group(1).strip().strip('\'"') if m else ''

    if not imagem:
        conferir('mapa.yaml aponta para o PGM', 'falta', 'sem chave "image"' + como,
                 ordem=30,
                 cura=f'{rel(raiz, mapa_yaml)} nao tem a chave image: -- salve com '
                      f'map_saver_cli, que gera o par certo')
        return

    alvo = (mapa_yaml.parent / imagem)
    if alvo.is_file():
        igual = alvo.resolve() == pgm.resolve()
        conferir('mapa.yaml aponta para o PGM', 'ok' if igual else '?',
                 f'image: {imagem}' + ('' if igual else ' -- nao e\' maps/mapa.pgm') + como)
    else:
        conferir('mapa.yaml aponta para o PGM', 'falta',
                 f'image: {imagem} nao existe ao lado do yaml' + como, ordem=30,
                 cura=f'o mapa.yaml pede {imagem} e esse arquivo nao esta\' em maps/ -- '
                      f'o par .pgm/.yaml tem de vir do mesmo salvamento')


# ---------------------------------------------------------------- item 3

def item3(raiz, evid):
    """Segmentacao semantica publicada em /vision/segmented (G3.4)."""
    secao('3. Segmentacao semantica por instancia            [G3.4]')

    fontes = achar(raiz, '*.py') + achar(raiz, '*.cpp') + achar(raiz, '*.launch.py')
    citou = next((p for p in fontes if '/vision/segmented' in texto_efetivo(p)), None)
    if citou is not None:
        conferir('/vision/segmented no codigo', 'ok', rel(raiz, citou))
    else:
        conferir('/vision/segmented no codigo', 'falta',
                 'nenhum fonte cita o topico', ordem=51,
                 cura='publique o frame com as mascaras em /vision/segmented '
                      '(sensor_msgs/Image) -- e\' o nome que o enunciado fixa')

    # Transparencia 0,5 e cor por classe: lembrete, nao nota. Encontrar
    # addWeighted(..., 0.5, ...) nao prova que ficou bonito, e nao encontrar nao
    # prova que esta' errado -- pode estar numa variavel ou num parametro.
    # Aqui o texto CRU serve: um comentario "mistura com alfa 0,5" ja' e' indicio
    # suficiente para uma linha que nunca passa de "?".
    alpha = next((p for p in fontes
                  if re.search(r'addWeighted|0\.5\s*\*|alpha', ler(p))), None)
    conferir('mistura com transparencia', '?',
             ('indicio em ' + rel(raiz, alpha)) if alpha else
             'nao achei addWeighted/alpha -- confira o 0,5 e a cor POR CLASSE a olho')

    imgs = imagens_de(evid)
    pistas = ('seg', 'yolo', 'instancia', 'instance', 'mask', 'mascara', 'vision')
    marcadas = com_pista(imgs, pistas)
    if marcadas:
        conferir('imagem da segmentacao em docs/evidencias/tp3/', 'ok',
                 ', '.join(p.name for p in marcadas[:3]))
    elif imgs:
        conferir('imagem da segmentacao em docs/evidencias/tp3/', '?',
                 f'{len(imgs)} imagem(ns) la\', nenhuma com seg/yolo/mask no nome')
    else:
        conferir('imagem da segmentacao em docs/evidencias/tp3/', 'falta',
                 'nenhuma imagem na pasta', ordem=50,
                 cura='salve o print do rqt_image_view ou do RViz2 mostrando '
                      '/vision/segmented em docs/evidencias/tp3/segmentacao.png (G3.4)')


# ---------------------------------------------------------------- item 4

def item4(raiz, evid):
    """Analise de arquitetura de percepcao veicular (G3.5)."""
    secao('4. Arquitetura de percepcao veicular               [G3.5]')
    doc = evid / 'veicular.md'
    if not doc.is_file():
        conferir('docs/evidencias/tp3/veicular.md', 'falta', 'nao achei', ordem=60,
                 cura='escreva docs/evidencias/tp3/veicular.md: protocolos (CAN, '
                      'Ethernet), tipos de sensor, e onde cada um entraria no SEU '
                      'pipeline ROS 2 (G3.5)')
        return
    conferir('docs/evidencias/tp3/veicular.md', 'ok', f'{doc.stat().st_size} bytes')

    # Lembrete de palavra-chave, nao nota: a presenca da palavra nao prova
    # analise, e a ausencia so' quer dizer "confira se voce nao esqueceu".
    texto = ler(doc).lower()
    grupos = {
        'CAN': ('can bus', 'can-bus', 'canbus', 'controller area network', ' can ',
                'can fd', '(can'),
        'Ethernet': ('ethernet', 'automotive ethernet', '100base', '1000base',
                     'someip', 'some/ip'),
        # "mera" pega camera e cam<e-circunflexo>ra sem este arquivo ter acento.
        'sensores': ('lidar', 'radar', 'camera', 'mera', 'imu', 'ultrass',
                     'sonar', 'encoder', 'gnss', 'gps'),
    }
    faltam = [rotulo for rotulo, chaves in grupos.items()
              if not any(c in texto for c in chaves)]
    if faltam:
        conferir('cita CAN, Ethernet e sensores', '?',
                 'nao achei: ' + ', '.join(faltam) + ' -- lembrete, nao nota')
    else:
        conferir('cita CAN, Ethernet e sensores', 'ok', 'as tres familias aparecem')
    conferir('relacionado as escolhas do seu projeto', '?',
             'leitura do professor -- texto generico de internet nao pontua')


# ---------------------------------------------------------------- entrega

def entrega(raiz, evid):
    """Relatorio, branch, tag, e o que precisa estar commitado (G3.6)."""
    secao('Entrega -- relatorio, branch, tag, Moodle          [G3.6]')

    docs = raiz / 'docs'
    # "relat" pega relatorio, relat<o-agudo>rio e relatorio-tp3 sem acento aqui.
    relatorios = [p for p in (achar(docs, '*.pdf') + achar(docs, '*.md'))
                  if 'relat' in p.name.lower()]
    if relatorios:
        conferir('relatorio em docs/', 'ok',
                 ', '.join(rel(raiz, p) for p in relatorios[:3]))
    else:
        quaisquer = achar(docs, '*.pdf') + achar(docs, '*.md')
        conferir('relatorio em docs/', 'falta',
                 (f'{len(quaisquer)} arquivo(s) em docs/, nenhum chamado relatorio*')
                 if quaisquer else 'docs/ vazio ou inexistente', ordem=70,
                 cura='escreva docs/relatorio-tp3.md (ou .pdf) -- e\' o documento que a '
                      'rubrica le')

    capturas = com_pista(imagens_de(evid), ('launch', 'bringup', 'gazebo', 'rviz', 'um-comando'))
    if capturas:
        conferir('captura do launch rodando', 'ok', ', '.join(p.name for p in capturas[:3]))
    elif imagens_de(evid):
        conferir('captura do launch rodando', '?',
                 'ha\' imagens em docs/evidencias/tp3/, nenhuma com launch/bringup/rviz '
                 'no nome')
    else:
        conferir('captura do launch rodando', 'falta',
                 'nenhuma imagem em docs/evidencias/tp3/', ordem=40,
                 cura='o enunciado pede o launch documentado com captura de tela: salve '
                      'docs/evidencias/tp3/bringup.png com Gazebo e RViz2 abertos')

    git_entrega(raiz, evid)


def git_entrega(raiz, evid):
    """Branch, tag, pendencias e -- o classico -- arquivos fora do git."""
    ok, _ = git(raiz, 'rev-parse', '--git-dir', timeout=10)
    if not ok:
        conferir('e\' um repositorio git', '?',
                 f'{raiz.name} nao e\' repo git (ou falta o git): branch, tag e '
                 f'commits ficaram sem conferir')
        return
    conferir('e\' um repositorio git', 'ok')

    ok, saida = git(raiz, 'for-each-ref', '--format=%(refname:short)',
                    'refs/heads', 'refs/remotes')
    refs = [l.strip() for l in saida.splitlines() if l.strip()] if ok else []
    tem_branch = any(r == f'entrega-{TP}' or r.endswith(f'/entrega-{TP}') for r in refs)
    if tem_branch:
        conferir(f'branch entrega-{TP} existe', 'ok')
    else:
        conferir(f'branch entrega-{TP} existe', 'falta',
                 f'{len(refs)} ref(s), nenhuma entrega-{TP}', ordem=82,
                 cura=f'git switch -c entrega-{TP} && git push -u origin entrega-{TP}')

    ok, saida = git(raiz, 'tag', '--list', TP)
    if ok and TP in saida.split():
        conferir(f'tag {TP} existe', 'ok')
    else:
        conferir(f'tag {TP} existe', 'falta', 'git tag --list nao mostra', ordem=83,
                 cura=f'git tag -a {TP} -m "entrega TP3" && git push origin {TP} '
                      f'-- e\' isto que o G3.6 verifica')

    ok, saida = git(raiz, 'status', '--porcelain', '--untracked-files=all')
    if not ok:
        conferir('nada pendente de commit', '?', 'git status nao respondeu')
        return
    linhas = [l for l in saida.splitlines() if l.strip()]
    if linhas:
        conferir('nada pendente de commit', 'falta',
                 f'{len(linhas)} arquivo(s) modificado(s) ou nao rastreado(s)', ordem=81,
                 cura='git add -A && git commit -m "G3.x: ..." && git push -- '
                      'trabalho nao commitado nao existe para a correcao')
    else:
        conferir('nada pendente de commit', 'ok', 'arvore limpa')

    # O erro classico: o mapa e as evidencias estao no disco e nao estao no git.
    # Quem corrige faz clone -- e nao ve nada.
    vigiadas = ('maps/', f'docs/evidencias/{TP}/')
    fora = [l[3:].strip().strip('"') for l in linhas
            if l[:2].strip() == '??' and any(l[3:].strip().strip('"').startswith(v)
                                             for v in vigiadas)]
    existe_algo = (raiz / 'maps').is_dir() or evid.is_dir()
    if fora:
        conferir('maps/ e evidencias rastreados pelo git', 'falta',
                 f'{len(fora)} fora do git: ' + ', '.join(fora[:3]), ordem=80,
                 cura='git add maps docs/evidencias && git commit -m "evidencias do TP3" '
                      '-- quem corrige faz clone; arquivo nao rastreado desaparece')
    elif existe_algo:
        conferir('maps/ e evidencias rastreados pelo git', 'ok')
    else:
        conferir('maps/ e evidencias rastreados pelo git', '?',
                 'nao ha\' maps/ nem docs/evidencias/tp3/ para rastrear')


# ---------------------------------------------------------------- ao vivo

def ao_vivo():
    """Confere o sistema no ar. Toda falha vira "?", nunca derruba o script."""
    secao('Ao vivo -- com o sistema rodando (tolerante a falha)')

    ok, saida = rodar(['ros2', 'topic', 'list'], timeout=12)
    if not ok and 'ros2' in saida and 'No such file' in saida:
        conferir('ros2 responde', '?', 'nao achei o comando ros2 -- `source` o setup.bash')
        return
    if not ok:
        conferir('ros2 topic list responde', '?',
                 (saida.strip().splitlines() or ['sem saida'])[-1][:60])
        return
    topicos = [l.strip() for l in saida.splitlines() if l.strip().startswith('/')]
    conferir('ros2 topic list responde', 'ok', f'{len(topicos)} topico(s)')

    if '/vision/segmented' in topicos:
        conferir('/vision/segmented no ar', 'ok')
        ok, info = rodar(['ros2', 'topic', 'info', '/vision/segmented'], timeout=12)
        m = PUBLISHERS.search(info)
        if m and int(m.group(1)) >= 1:
            conferir('/vision/segmented com publisher', 'ok', f'{m.group(1)} publisher(s)')
        elif m:
            conferir('/vision/segmented com publisher', '?',
                     'publisher count 0 -- o topico existe porque alguem o assina')
        else:
            conferir('/vision/segmented com publisher', '?', 'topic info nao respondeu')
    else:
        conferir('/vision/segmented no ar', '?',
                 'nao esta\' em ros2 topic list -- o no de segmentacao subiu?')

    # `topic hz` nao termina sozinho: a saida que interessa e' a parcial que o
    # timeout interrompe.
    _, hz = rodar(['ros2', 'topic', 'hz', '/scan'], timeout=10)
    m = TAXA_HZ.search(hz)
    if m:
        conferir('/scan publicando', 'ok', f'{m.group(1)} Hz')
    else:
        conferir('/scan publicando', '?',
                 'topic hz /scan nao deu taxa em 10 s -- sem scan o SLAM nao mapeia')

    achou = None
    for cmd in (['ros2', 'run', 'tf2_ros', 'tf2_echo', 'map', 'odom', '--once'],
                ['ros2', 'run', 'tf2_ros', 'tf2_echo', 'map', 'odom']):
        _, tf = rodar(cmd, timeout=10)
        if TEM_TF.search(tf):
            achou = tf
            break
    if achou:
        linha = next((l.strip() for l in achou.splitlines() if 'Translation' in l), 'ok')
        conferir('TF map -> odom existe', 'ok', linha[:52])
    else:
        conferir('TF map -> odom existe', '?',
                 'tf2_echo map odom nao devolveu transformada -- quem publica essa '
                 'aresta e\' o SLAM')

    ok, saida = rodar(['ros2', 'node', 'list'], timeout=12)
    nos = [l.strip() for l in saida.splitlines() if l.strip().startswith('/')] if ok else []
    if len(nos) > 1:
        conferir('mais de um no no ar', 'ok', f'{len(nos)} nos')
    else:
        conferir('mais de um no no ar', '?',
                 f'{len(nos)} no(s) -- o bringup sobe o sistema inteiro, nao um no')


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(
        description='Confere a entrega do TP3 contra o enunciado e os gates G3.0-G3.6.')
    ap.add_argument('--raiz', default='.',
                    help='raiz do repositorio do projeto (padrao: diretorio atual)')
    ap.add_argument('--ao-vivo', action='store_true',
                    help='tambem confere topicos e TF, com o sistema ROS 2 rodando')
    args = ap.parse_args()

    raiz = pathlib.Path(args.raiz).expanduser().resolve()
    if not raiz.is_dir():
        print(f'nao existe: {raiz}', file=sys.stderr)
        return 2

    print(f'{NEGRITO}conferir_tp3{FIM} -- PB Sistemas Roboticos, TP3 (entrega {PRAZO})')
    print(f'raiz: {raiz}')
    print('Confere o que um comando prova. Qualidade do texto, explicacao dos frames e')
    print('adequacao ao seu projeto sao avaliadas pelo professor: "ok" aqui nao e\' nota,')
    print('"?" nao e\' erro -- e\' o que este script nao consegue provar sozinho.')

    evid = raiz / 'docs' / 'evidencias' / TP
    launch = item1(raiz)
    item2(raiz, launch, evid)
    item3(raiz, evid)
    item4(raiz, evid)
    entrega(raiz, evid)
    if args.ao_vivo:
        ao_vivo()
    else:
        secao('Ao vivo -- nao conferido')
        conferir('topicos, TF e nos', '?', 'rode com --ao-vivo e o sistema no ar')

    print()
    print(f'{quantos["ok"]} ok, {quantos["falta"]} faltando, {quantos["?"]} '
          f'nao conferivel por comando')

    if not pendencias:
        print(f'{VERDE}Nada falta do que da\' para conferir por comando.{FIM} '
              f'Releia os "?" antes de postar no Moodle.')
        return 0

    print()
    print(f'{NEGRITO}O que falta, na ordem em que compensa resolver:{FIM}')
    for i, (_, nome, cura) in enumerate(sorted(pendencias, key=lambda x: x[0]), 1):
        print(f'  {i:>2}. {VERMELHO}{nome}{FIM}')
        for linha in quebrar(cura, 72):
            print(f'      {linha}')
    return 1


def quebrar(texto, largura):
    """Quebra a cura em linhas curtas sem cortar palavra no meio."""
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


if __name__ == '__main__':
    raise SystemExit(main())
