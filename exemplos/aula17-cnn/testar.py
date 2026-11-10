#!/usr/bin/env python3
"""Prova o que da para provar sem treinar de verdade. Roda com o Python do venv.

    "$PB_DIR/.venv-cnn/bin/python" testar.py

Sete grupos, cada um com a resposta sabida de antemao:

    1  higiene dos .py: so ASCII, linhas de ate 99 colunas
    2  o gerador sintetico: contagem por classe, CSV, determinismo byte a byte
    3  o rotular.py: o teclado (funcoes puras: codigos do GTK/Qt/Windows e bytes
       do terminal), a retomada pela coluna `revisado`, o --so-sugestao sobre a
       amostra da aula17-metadrive e a revisao pelo terminal dirigida por um pty
       (sem janela: a janela de verdade nao e testada aqui)
    4  a mesma inicializacao: `sem` e `com` comecam com os MESMOS pesos
    5  o treinar.py de ponta a ponta, 1 epoca, 24 imagens em DUAS pastas:
       arquivos, JSON, matriz 3x3 que soma o tamanho da validacao
    6  o treinar.py sobre os 12 quadros REAIS da amostra (classe com 1 exemplo,
       classe ausente): nao pode quebrar, e a matriz continua 3x3
    7  o curvas.py gera um PNG nao vazio

Nao prova que a rede aprende -- isso so o treino de 20 epocas mostra, e os
numeros estao no README. Termina em `todos os testes passaram.` e sai com 0,
ou com 1 e a lista do que falhou.
"""
import contextlib
import csv
import hashlib
import io
import json
import os
import pathlib
import select
import subprocess
import sys
import tempfile
import time

# o teste importa os modulos daqui: sem __pycache__ deixado para tras
sys.dont_write_bytecode = True
AQUI = pathlib.Path(__file__).resolve().parent
AMOSTRA_MD = AQUI.parent / 'aula17-metadrive' / 'amostra'
PY = sys.executable
FALHAS = []


def confere(cond, msg):
    print(('  passou  ' if cond else '  FALHOU  ') + msg)
    if not cond:
        FALHAS.append(msg)


def rodar(*args):
    """Roda um script deste diretorio com o mesmo Python; devolve (codigo, saida)."""
    env = dict(os.environ, TF_CPP_MIN_LOG_LEVEL='3', PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([PY, *map(str, args)], cwd=AQUI, capture_output=True, text=True,
                       env=env)
    return r.returncode, r.stdout + r.stderr


def hash_pasta(pasta):
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(pasta).iterdir()):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def ler_csv(caminho):
    with open(caminho, newline='') as f:
        return list(csv.DictReader(f))


def grupo1_higiene():
    print('1. higiene dos .py')
    for p in sorted(AQUI.glob('*.py')):
        texto = p.read_bytes()
        confere(all(b < 128 for b in texto), f'{p.name}: so ASCII')
        longas = [i for i, l in enumerate(texto.decode().splitlines(), 1) if len(l) > 99]
        confere(not longas, f'{p.name}: linhas <= 99 colunas {longas[:3] if longas else ""}')


def grupo2_sintetico(tmp):
    print('2. gerador sintetico')
    sys.path.insert(0, str(AQUI))
    import gerar_sintetico as gs
    confere(gs.contar_por_classe(500, (1, 1, 1)) == [167, 167, 166], '500 em 1:1:1 -> 167/167/166')
    confere(gs.contar_por_classe(500, (54, 0, 6)) == [450, 0, 50], '500 em 54:0:6 -> 450/0/50')
    confere(sum(gs.contar_por_classe(37, (3, 5, 7))) == 37, 'a soma e sempre n')
    cena = gs.carregar_cena()
    for nome in ('geometria', '_fundo', '_acima_do_horizonte', '_pintar', '_poligono_faixa',
                 '_ruido', 'A', 'L', 'Y_BASE', 'ASFALTO', 'PINTURA', 'AMARELO'):
        confere(hasattr(cena, nome), f'cena_estrada.py da Aula 13 ainda tem {nome}')
    a, b = tmp / 'a', tmp / 'b'
    for pasta in (a, b):
        cod, out = rodar('gerar_sintetico.py', '--n', 12, '--saida', pasta)
        confere(cod == 0, f'gerar_sintetico.py --saida {pasta.name} sai com 0')
    confere(hash_pasta(a) == hash_pasta(b), 'mesma semente -> mesmos PNG e CSV, byte a byte')
    linhas = ler_csv(a / 'rotulos.csv')
    confere(list(linhas[0]) == ['arquivo', 'classe'], 'rotulos.csv tem as colunas arquivo,classe')
    confere(len(linhas) == 12, '12 linhas')
    confere({r['classe'] for r in linhas} == set(gs.CLASSES), 'as tres classes aparecem')
    confere(all((a / r['arquivo']).exists() for r in linhas), 'todo arquivo do CSV existe')
    import cv2
    img = cv2.imread(str(a / linhas[0]['arquivo']))
    confere(img is not None and img.shape == (96, 128, 3), 'PNG 128x96, 3 canais')
    cod, _ = rodar('gerar_sintetico.py', '--n', 12, '--saida', tmp / 'c', '--semente', 8)
    confere(hash_pasta(a) != hash_pasta(tmp / 'c'), 'outra semente -> outras imagens')
    cod, _ = rodar('gerar_sintetico.py', '--n', 20, '--proporcao', '54:0:6', '--saida', tmp / 'd')
    cl = [r['classe'] for r in ler_csv(tmp / 'd' / 'rotulos.csv')]
    confere((cl.count('via_livre'), cl.count('obstaculo'), cl.count('cruzamento')) == (18, 0, 2),
            '--proporcao 54:0:6 com n=20 -> 18 via_livre, 0 obstaculo, 2 cruzamento')


def rodar_pty(args, envios, prazo=30):
    """Roda o rotular.py com stdin/stdout num pty, como num terminal de verdade.

    Espera a linha de teclas aparecer, manda cada `bytes` de `envios` com uma
    pausa (um Esc sozinho precisa dos ~50 ms de silencio), e devolve
    (codigo, saida, atributos do terminal antes, atributos depois). Com
    b'\\x03' o pty gera SIGINT, como o Ctrl+C.
    """
    import pty
    import termios
    mestre, escravo = pty.openpty()
    antes = termios.tcgetattr(escravo)

    def controlador():                 # o pty vira o terminal do processo: Ctrl+C funciona
        os.setsid()
        import fcntl
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    p = subprocess.Popen([PY, 'rotular.py', *map(str, args)], cwd=AQUI, stdin=escravo,
                         stdout=escravo, stderr=escravo, preexec_fn=controlador,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    saida, fim = b'', time.time() + prazo

    def ler(ate):
        nonlocal saida
        while time.time() < ate:
            pronto, _, _ = select.select([mestre], [], [], 0.05)
            if pronto:
                try:
                    saida += os.read(mestre, 4096)
                except OSError:
                    return
            elif p.poll() is not None:
                return
    while b'Teclas' not in saida and b'teclas' not in saida and time.time() < fim \
            and p.poll() is None:
        ler(time.time() + 0.1)
    for b in envios:
        os.write(mestre, b)
        ler(time.time() + 0.3)
    try:
        p.wait(timeout=max(1, fim - time.time()))
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
    ler(time.time() + 0.3)
    depois = termios.tcgetattr(escravo)
    os.close(mestre)
    os.close(escravo)
    return p.returncode, saida.decode(errors='replace'), antes, depois


def grupo3_rotular(tmp):
    print('3. rotular.py')
    import rotular as rt
    nt = rt.normalizar_tecla
    casos = [
        (ord('1'), '1', "'1' em ASCII"), (1048625, '1', "'1' no GTK com NumLock (0x100031)"),
        (0xFFB1, '1', 'KP_1 do teclado numerico'), (0x10FFB3, '3', 'KP_3 com NumLock'),
        (65361, 'volta', 'seta esq. GTK'), (65363, 'avanca', 'seta dir. GTK'),
        (2424832, 'volta', 'seta esq. Windows'), (2555904, 'avanca', 'seta dir. Windows'),
        (16777234, 'volta', 'seta esq. Qt'), (16777236, 'avanca', 'seta dir. Qt'),
        (0x10FF51, 'volta', 'seta esq. GTK com NumLock (0x10FF51)'),
        (0x10FF53, 'avanca', 'seta dir. GTK com NumLock'),
        (0xFF96, 'volta', 'KP_Left'), (0xFF98, 'avanca', 'KP_Right'),
        (0xFF8D, 'aceita', 'KP_Enter'), (0xFF0D, 'aceita', 'Return GTK'),
        (0x10FF0D, 'aceita', 'Return GTK com NumLock'), (13, 'aceita', 'Enter (13)'),
        (10, 'aceita', 'Enter do terminal (10)'), (32, 'aceita', 'espaco'),
        (0xFF1B, 'sai', 'Escape GTK'), (27, 'sai', 'Esc (27)'), (ord('q'), 'sai', 'q'),
        (ord('Q'), 'sai', "'Q' (CapsLock)"), (0x20051, 'sai', "'Q' GTK com o bit do CapsLock"),
        (0x100071, 'sai', "'q' GTK com NumLock"), (ord('S'), 'grava', "'S'"),
        (ord('A'), 'volta', "'A'"), (ord('d'), 'avanca', "'d'"),
        (0xFF52, None, 'seta cima: sem funcao (e nao vira R)'),
        (0xFFE1, None, 'Shift_L: sem funcao'), (-1, None, '-1 (nenhuma tecla)'),
    ]
    erradas = [(c, d, nt(c)) for c, esperado, d in casos if nt(c) != esperado]
    confere(not erradas, f'normalizar_tecla: {len(casos)} codigos'
            + (f' -- errados: {erradas}' if erradas else ''))
    ev, resto = rt.decodificar_terminal(b'1\x1b[C2\x1bOD3\x1b[1;5Cq\n', fim=False)
    confere([e[0] for e in ev] == ['1', 'avanca', '2', 'volta', '3', 'avanca', 'sai', 'aceita']
            and resto == b'', 'terminal: 1, ESC[C, 2, ESC O D, 3, Ctrl+seta, q, Enter')
    ev, resto = rt.decodificar_terminal(b'2\x1b', fim=False)
    confere([e[0] for e in ev] == ['2'] and resto == b'\x1b',
            'terminal: ESC no fim fica esperando o resto da seta')
    ev, resto = rt.decodificar_terminal(b'\x1b', fim=True)
    confere([e[0] for e in ev] == ['sai'] and resto == b'', 'terminal: Esc sozinho sai')
    ev, _ = rt.decodificar_terminal(b'\x1b[Ax', fim=True)
    confere([e[0] for e in ev] == [None, None] and 'ESC[A' in ev[0][1]
            and '120 (0x78)' in ev[1][1], 'terminal: seta cima e x sem funcao, com o codigo')

    rot = {}
    i, sair, salvar = rt.aplicar_tecla('2', 0, 5, 'q0.png', 'via_livre', rot)
    confere((i, sair, rot.get('q0.png')) == (1, False, 'obstaculo'),
            'tecla 2 -> obstaculo e avanca')
    i, *_ = rt.aplicar_tecla(nt(13), 1, 5, 'q1.png', 'cruzamento', rot)
    confere(rot.get('q1.png') == 'cruzamento' and i == 2, 'Enter aceita a sugestao e avanca')
    i, *_ = rt.aplicar_tecla(nt(65361), 2, 5, 'q2.png', 'via_livre', rot)
    confere(i == 1 and 'q2.png' not in rot, 'seta esquerda volta sem rotular')
    i, *_ = rt.aplicar_tecla(nt(1048625 + 2), 4, 5, 'q4.png', 'via_livre', rot)
    confere(i == 4 and rot.get('q4.png') == 'cruzamento',
            "'3' com NumLock rotula; no ultimo quadro nao passa do fim")
    _, sair, salvar = rt.aplicar_tecla(nt(ord('q')), 0, 5, 'q0.png', 'via_livre', rot)
    confere(sair and salvar, 'q grava e sai')
    i, sair, salvar = rt.aplicar_tecla(None, 3, 5, 'q3.png', 'via_livre', rot)
    confere((i, sair, salvar) == (3, False, False), 'tecla desconhecida nao faz nada')

    # retomada: so volta o que foi revisado
    estado = [(f'q{k}.png', 'via_livre') for k in range(10)]
    rot = {'q1.png': 'obstaculo', 'q4.png': 'via_livre', 'q7.png': 'cruzamento'}
    csv10 = tmp / 'retomada.csv'
    dif = rt.gravar(csv10, estado, rot)
    linhas = ler_csv(csv10)
    confere(list(linhas[0]) == ['arquivo', 'classe', 'sugerido', 'revisado'],
            'gravar: colunas arquivo,classe,sugerido,revisado')
    confere(sum(r['revisado'] == '1' for r in linhas) == 3 and dif == 2,
            'gravar: 3 de 10 com revisado=1, 2 diferentes da sugestao')
    with contextlib.redirect_stdout(io.StringIO()):
        relido = rt.ler_rotulos_existentes(csv10)
    confere(relido == rot, 'reler: os mesmos 3 revisados, nao os 10')
    antigo = tmp / 'antigo' / 'rotulos.csv'
    antigo.parent.mkdir()
    antigo.write_text('arquivo,classe,sugerido\n'
                      + ''.join(f'q{k}.png,via_livre,via_livre\n' for k in range(10)))
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        relido = rt.ler_rotulos_existentes(antigo)
    confere(relido == {} and 'nao tem a coluna `revisado`' in buf.getvalue(),
            'rotulos.csv antigo, sem a coluna: 0 revisados e aviso')
    confere(not (antigo.parent / 'rotulos.antigo.csv').exists(),
            'antigo igual a sugestao: nao precisa de copia')
    antigo.write_text('arquivo,classe,sugerido\nq0.png,obstaculo,via_livre\n')
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        rt.ler_rotulos_existentes(antigo)
    confere((antigo.parent / 'rotulos.antigo.csv').exists() and 'copiei' in buf.getvalue(),
            'antigo com classe corrigida: copia guardada antes de regravar')

    if not (AMOSTRA_MD / 'estado.csv').exists():
        print('  [pulado] a aula17-metadrive/amostra nao esta ao lado desta pasta')
        return None
    saida = tmp / 'rotulos_amostra.csv'
    cod, out = rodar('rotular.py', '--pasta', AMOSTRA_MD, '--so-sugestao', '--saida', saida)
    confere(cod == 0, 'rotular.py --so-sugestao sobre a amostra sai com 0')
    linhas = ler_csv(saida)
    confere(list(linhas[0]) == ['arquivo', 'classe', 'sugerido', 'revisado'],
            'colunas arquivo,classe,sugerido,revisado')
    confere(len(linhas) == 12, '12 linhas: so os PNG que existem na amostra')
    confere(all(r['classe'] == r['sugerido'] and r['revisado'] == '0' for r in linhas),
            'sem revisao, classe = sugerido e revisado = 0')
    confere('nenhuma imagem de obstaculo' in out, 'avisa que obstaculo ficou vazio')
    cod, out = rodar('rotular.py', '--pasta', AMOSTRA_MD, '--so-sugestao', '--saida', saida)
    confere('ja revisados' not in out and 'revisados a mao: 0' in out,
            'regravar a sugestao nao inventa revisados (o defeito da 1a versao)')
    grupo3_pty(tmp)
    return saida


def grupo3_pty(tmp):
    """A revisao pelo terminal (--sem-janela), com bytes de verdade num pty."""
    import termios
    saida = tmp / 'rotulos_pty.csv'
    args = ('--pasta', AMOSTRA_MD, '--saida', saida, '--sem-janela')
    # 1a: quadro000 <- 1 (igual), seta dir. pula o 005, quadro010 <- 2 (diferente), q
    cod, out, antes, depois = rodar_pty(args, [b'1', b'\x1b[C', b'2', b'x', b'q'])
    lin = {r['arquivo']: r for r in ler_csv(saida)} if saida.exists() else {}
    confere(cod == 0 and 'revisao pelo terminal' in out, 'pty --sem-janela sai com 0'
            + ('' if cod == 0 else '\n' + out[-600:]))
    confere(lin and [k for k, r in lin.items() if r['revisado'] == '1']
            == ['quadro000.png', 'quadro010.png'] and lin['quadro010.png']['classe']
            == 'obstaculo' and lin['quadro005.png']['classe'] == 'via_livre',
            'pty: 1, seta dir., 2, q -> 000 e 010 revisados, 010 obstaculo, 005 intocado')
    confere('revisados a mao: 2; diferentes da sugestao: 1' in out,
            'pty: "revisados 2; diferentes 1" bate com o CSV')
    confere('3/12 quadro010.png -> obstaculo (sugerido via_livre)' in out,
            'pty: linha de progresso do quadro rotulado')
    confere('tecla sem funcao: codigo 120 (0x78)' in out, "pty: 'x' -> tecla sem funcao")
    confere(depois == antes, 'pty: terminal restaurado ao sair com q (eco e modo linha)')
    confere(antes[3] & termios.ECHO and antes[3] & termios.ICANON,
            'pty: o terminal de partida tinha eco e modo linha')
    # 2a: continua do primeiro nao revisado (005); 3 -> cruzamento; Esc sozinho
    cod, out, antes, depois = rodar_pty(args, [b'3', b'\x1b'])
    lin = {r['arquivo']: r for r in ler_csv(saida)}
    confere(cod == 0 and 'continuando' in out and '2 quadros ja revisados' in out,
            'retomada: diz 2 ja revisados')
    confere(lin['quadro005.png']['classe'] == 'cruzamento'
            and 'revisados a mao: 3; diferentes da sugestao: 2' in out,
            'retomada comeca no 005; Esc sozinho grava e sai: 3 revisados, 2 diferentes')
    confere(depois == antes, 'pty: terminal restaurado ao sair com Esc')
    # 3a: comeca no 015; ESC O D volta ao 010; 1 -> via_livre; Ctrl+C
    cod, out, antes, depois = rodar_pty(args, [b'\x1bOD', b'1', b'\x03'])
    lin = {r['arquivo']: r for r in ler_csv(saida)}
    dif = sum(r['classe'] != r['sugerido'] for r in lin.values())
    confere(cod == 0 and 'Ctrl+C: gravando e saindo' in out and 'Traceback' not in out,
            'Ctrl+C grava e sai limpo, sem Traceback')
    confere(lin['quadro010.png']['classe'] == 'via_livre' and dif == 1
            and f'revisados a mao: 3; diferentes da sugestao: {dif}' in out,
            'ESC O D volta, 1 corrige: "diferentes da sugestao" = o que o CSV mostra')
    confere(depois == antes, 'pty: terminal restaurado depois do Ctrl+C')
    cod, out = rodar('rotular.py', '--pasta', AMOSTRA_MD, '--saida', tmp / 'x.csv',
                     '--sem-janela')
    confere(cod != 0 and 'nao e um terminal' in out, '--sem-janela sem terminal: para e diz')


def grupo4_inicializacao():
    print('4. mesma inicializacao nas duas rodadas')
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    import numpy as np
    import treinar
    m_sem = treinar.construir_modelo(False, (64, 48), 7)
    m_com = treinar.construir_modelo(True, (64, 48), 7)
    w_sem = m_sem.get_layer('nucleo').get_weights()
    w_com = m_com.get_layer('nucleo').get_weights()
    confere(len(w_sem) == len(w_com) and all(np.array_equal(a, b) for a, b in zip(w_sem, w_com)),
            f'os {len(w_sem)} tensores de peso do nucleo sao identicos')
    nomes = [c.name for c in m_com.layers]
    confere(all(n in nomes for n in ('rotacao', 'zoom', 'flip')), 'com: rotacao, zoom e flip')
    confere(not any(n in [c.name for c in m_sem.layers] for n in ('rotacao', 'zoom', 'flip')),
            'sem: nenhuma camada de augmentation')
    nucleo = [c.__class__.__name__ for c in m_sem.get_layer('nucleo').layers]
    confere(nucleo.count('BatchNormalization') == 3 and 'Dropout' in nucleo,
            'nucleo tem BatchNormalization e Dropout')
    drop = m_sem.get_layer('nucleo').get_layer('dropout')
    confere(abs(drop.rate - 0.5) < 1e-9, 'Dropout(0.5)')
    rot = m_com.get_layer('rotacao')
    confere(abs(rot.factor[1] * 360 - 15) < 1e-6, 'RandomRotation de +-15 graus')
    fz = m_com.get_layer('zoom').height_factor
    fz = fz[1] if isinstance(fz, (tuple, list)) else fz
    confere(abs(abs(fz) - 0.2) < 1e-9, 'RandomZoom(0.2)')


def conferir_saida_treino(saida, n_val, rotulo):
    for nome in ('historico_sem.json', 'historico_com.json', 'modelo_sem.keras',
                 'modelo_com.keras', 'matriz_sem.png', 'matriz_com.png', 'matriz_sem.csv',
                 'matriz_com.csv', 'divisao.csv', 'tabela.txt', 'exemplos_augmentation.png'):
        p = saida / nome
        confere(p.exists() and p.stat().st_size > 0, f'{rotulo}: {nome} existe e nao e vazio')
    h = json.loads((saida / 'historico_sem.json').read_text())
    confere(all(k in h for k in ('accuracy', 'val_accuracy', 'loss', 'val_loss')),
            f'{rotulo}: historico tem as 4 curvas')
    for nome in ('sem', 'com'):
        m = ler_csv(saida / f'matriz_{nome}.csv')
        valores = [[int(v) for k, v in r.items() if k != 'verdade\\previsto'] for r in m]
        confere(len(valores) == 3 and all(len(l) == 3 for l in valores),
                f'{rotulo}: matriz_{nome} e 3x3')
        confere(sum(map(sum, valores)) == n_val, f'{rotulo}: matriz_{nome} soma {n_val}')


def grupo5_treino(tmp):
    print('5. treinar.py de ponta a ponta (1 epoca)')
    # duas pastas de 12, como duas sementes do MetaDrive: o treinar.py as junta
    for nome, sem in (('mini-a', 7), ('mini-b', 8)):
        rodar('gerar_sintetico.py', '--n', 12, '--saida', tmp / nome, '--tamanho', '64x48',
              '--semente', sem)
    saida = tmp / 'res'
    cod, out = rodar('treinar.py', '--pasta', tmp / 'mini-a', tmp / 'mini-b', '--epocas', 1,
                     '--tamanho', '64x48', '--saida', saida)
    confere(cod == 0, 'treinar.py --epocas 1 sai com 0' + ('' if cod == 0 else '\n' + out[-800:]))
    if cod != 0:
        return None
    conferir_saida_treino(saida, 5, 'mini')
    confere('linha de base' in out and 'pior recall' in out and 'acc_val_pert' in out,
            'a tabela tem linha de base, pior recall e acc_val_pert')
    div = ler_csv(saida / 'divisao.csv')
    confere(sum(r['conjunto'] == 'validacao' for r in div) == 5, '24 imagens -> 5 na validacao')
    confere(len(div) == 24 and {pathlib.Path(r['arquivo']).parent.name for r in div}
            == {'mini-a', 'mini-b'}, 'duas --pasta: 24 linhas, das duas pastas')
    return saida


def grupo6_metadrive(tmp, rotulos):
    print('6. treinar.py sobre os 12 quadros reais da amostra')
    if rotulos is None:
        print('  [pulado] sem a amostra da aula17-metadrive')
        return
    cod, out = rodar('treinar.py', '--pasta', AMOSTRA_MD, '--rotulos', rotulos, '--epocas', 1,
                     '--saida', tmp / 'res_md')
    confere(cod == 0, 'roda com 11 via_livre, 1 cruzamento e 0 obstaculo'
            + ('' if cod == 0 else '\n' + out[-800:]))
    if cod == 0:
        confere('sem estratificar' in out, 'avisa que nao deu para estratificar')
        conferir_saida_treino(tmp / 'res_md', 2, 'metadrive')


def grupo7_curvas(tmp, res):
    print('7. curvas.py')
    if res is None:
        print('  [pulado] o grupo 5 falhou')
        return
    png = tmp / 'curvas.png'
    cod, out = rodar('curvas.py', '--pasta', res, '--saida', png)
    confere(cod == 0, 'curvas.py sai com 0')
    confere(png.exists() and png.stat().st_size > 5000, 'PNG gerado e nao vazio')
    if png.exists():
        confere(png.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', 'e PNG de verdade')
    cod, out = rodar('curvas.py', '--pasta', tmp / 'nao-existe', '--saida', tmp / 'x.png')
    confere(cod != 0 and 'nao achei' in out, 'sem historico: para e diz o que falta')


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        grupo1_higiene()
        grupo2_sintetico(tmp)
        rotulos = grupo3_rotular(tmp)
        grupo4_inicializacao()
        res = grupo5_treino(tmp)
        grupo6_metadrive(tmp, rotulos)
        grupo7_curvas(tmp, res)
    if FALHAS:
        print(f'\n{len(FALHAS)} conferencia(s) falharam:')
        for f in FALHAS:
            print('  - ' + f.splitlines()[0])
        sys.exit(1)
    print('\ntodos os testes passaram.')


if __name__ == '__main__':
    main()
