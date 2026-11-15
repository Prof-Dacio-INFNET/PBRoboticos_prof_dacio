#!/usr/bin/env python3
"""Prova o que da para provar -- sem simulador, e com ele se estiver instalado.

    python3 testar.py                                        # grupos 1 a 7
    python3 testar.py --metadrive "$PB_DIR/.venv-metadrive/bin/python" \
                      --cnn "$PB_DIR/.venv-cnn/bin/python"   # forca o 8 e o 9

Grupos:
    1. pid.py: angulo, ponto a frente, acelerador e o SINAL do erro (faixa falsa)
    2. coletar.py: teclas do terminal (setas, letras, escape pela metade),
       volante saturado, perturbacao deterministica e com a escala pedida
    3. coletar.py de verdade num pseudoterminal: as teclas chegam sem Enter
    4. rede.py: preparo, convolucao contra um laco ingenuo, maxpool, e a rede
       NumPy contra a saida do KERAS gravada em amostra/modelo/referencia.npz
    5. avaliar.py: colunas da regua, media e desvio, motivo; as tabelas da
       amostra tem as colunas comuns e os numeros do README
    6. amostra/: acoes.csv com as colunas do coletar.py, PNG 160x120 BGR,
       mais de um episodio; o histograma.py roda nela
    7. higiene: ast.parse, ASCII puro, linhas <= 99 colunas, nada > 2 MB
    8. SO COM O VENV DO METADRIVE: o PID conclui 2 episodios; o coletar.py grava
       3 quadros; o BC da amostra roda 5 passos com a camera; o humano-terminal
       num pseudoterminal muda o volante com a tecla `a`
    9. SO COM O VENV DA CNN: treinar_bc.py --epocas 1 na amostra, e o pesos.npz
       que ele exporta bate com o Keras no rede.py

Termina em "todos os testes passaram." e sai com 0, ou 1 se algo falhou.
Precisa so de NumPy (e do OpenCV, para ler os PNG) no Python que o roda.
"""
import argparse
import ast
import csv
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
AMOSTRA = AQUI / 'amostra'
sys.path.insert(0, str(AQUI))

import avaliar  # noqa: E402  (nenhum deles importa o metadrive no topo)
import coletar  # noqa: E402
import pid  # noqa: E402
import rede  # noqa: E402

FALHAS = []
COMUNS = ['episodio', 'semente', 'concluiu', 'colidiu', 'vel_media', 'passos', 'recompensa']
XVFB = ['xvfb-run', '-a', '-s', '-screen 0 1280x1024x24']


def confere(cond, msg):
    print('  [%s] %s' % ('ok' if cond else 'FALHOU', msg))
    if not cond:
        FALHAS.append(msg)


class _Faixa:
    """Faixa reta ao longo de x, centro em y=0: lateral > 0 a DIREITA (y < 0)."""

    def local_coordinates(self, pos):
        return pos[0], -pos[1]

    def heading_theta_at(self, lon):
        return 0.0


class _Nav:
    current_ref_lanes = [_Faixa(), _Faixa(), _Faixa()]


class _Carro:
    def __init__(self, x, y, rumo):
        self.position, self.heading_theta, self.navigation = (x, y), rumo, _Nav()


def grupo1():
    print('1. pid.py')
    confere(abs(pid.ajustar_angulo(math.radians(359)) - math.radians(-1)) < 1e-9,
            'ajustar_angulo(359 graus) = -1 grau')
    confere(abs(pid.medida_a_frente(0.0, math.radians(10), 5.0) - 5 * math.sin(math.radians(10)))
            < 1e-12, 'ponto a frente: 0 m de desvio, 10 graus de rumo, 5 m -> 0,87 m')
    confere(pid.acelerador(0.0) == 1.0 and pid.acelerador(200.0) == -1.0,
            'acelerador satura em +1 (parado) e -1 (rapido demais)')
    confere(abs(pid.acelerador(35.0, 40.0) - 0.5) < 1e-12, '5 km/h abaixo do alvo -> 0,5')
    d, r = pid.erros_da_faixa(_Carro(10.0, 1.0, 0.2))
    confere(d == 1.0 and abs(r - 0.2) < 1e-12,
            'carro 1 m a esquerda, apontando 0,2 rad a esquerda -> desvio +1, rumo +0,2')
    confere(pid.KD == 0 and pid.OLHAR_M > 0,
            'os ganhos do topo: o amortecimento e o termo de rumo (olhar > 0), nao o Kd')


def grupo2():
    print('2. coletar.py: teclas e perturbacao')
    s, resto = coletar.decodificar(b'aa\x1b[D d\x1b[Cq')
    confere(s == ['esq', 'esq', 'esq', 'centro', 'dir', 'dir', 'sai'] and resto == b'',
            'letras, espaco e setas viram simbolos: %s' % s)
    s, resto = coletar.decodificar(b'a\x1b[')
    confere(s == ['esq'] and resto == b'\x1b[', 'seta pela metade fica para a proxima leitura')
    s, _ = coletar.decodificar(resto + b'C')
    confere(s == ['dir'], 'e completa na leitura seguinte')
    confere(coletar.decodificar(b'A')[0] == ['esq'], 'maiuscula vale (CapsLock)')
    v, alvo, sair = coletar.aplicar_teclas(['esq'] * 3, 0.0, 40.0)
    confere(v == 0.06 and not sair, 'tres toques a esquerda: +0,06, o volante de uma curva')
    v, alvo, sair = coletar.aplicar_teclas(['esq'] * 80, 0.0, 40.0)
    confere(v == 1.0 and not sair, 'oitenta toques saturam o volante em +1')
    v, alvo, sair = coletar.aplicar_teclas(['dir', 'dir', 'mais', 'sai'], 0.0, 40.0)
    confere(v == -0.04 and alvo == 45.0 and sair, 'direita = negativo, w sobe 5 km/h, q sai')
    a = [coletar.Perturbacao(0.3, 5)() for _ in range(3)]
    b = [coletar.Perturbacao(0.3, 5)() for _ in range(3)]
    confere(a == b, 'a perturbacao repete com a mesma semente')
    p = coletar.Perturbacao(0.3, 1)
    xs = np.array([p() for _ in range(20000)])
    confere(0.24 < xs.std() < 0.36, 'desvio da perturbacao ~ a escala pedida (%.3f para 0,3)'
            % xs.std())


def grupo3():
    print('3. o Teclado num pseudoterminal')
    try:
        import pty
    except ImportError:
        print('  [pulado] sem pty (Windows)')
        return
    codigo = ('import sys, time; sys.path.insert(0, %r); import coletar\n'
              'with coletar.Teclado() as t:\n'
              '    print("pronto", flush=True); vistos = []\n'
              '    fim = time.time() + 5\n'
              '    while time.time() < fim and "sai" not in vistos:\n'
              '        vistos += t.ler(); time.sleep(0.02)\n'
              '    print("VISTOS", vistos, flush=True)\n' % str(AQUI))
    mestre, escravo = pty.openpty()
    proc = subprocess.Popen([sys.executable, '-B', '-c', codigo], stdin=escravo, stdout=escravo,
                            stderr=escravo, close_fds=True)
    os.close(escravo)
    saida = b''
    fim = time.time() + 8
    enviado = False
    import select
    while time.time() < fim:
        if select.select([mestre], [], [], 0.1)[0]:
            try:
                bloco = os.read(mestre, 1024)
            except OSError:
                break
            if not bloco:
                break
            saida += bloco
        if b'pronto' in saida and not enviado:
            os.write(mestre, b'a\x1b[Dd q')        # sem Enter
            enviado = True
        if b'VISTOS' in saida and saida.endswith(b'\n'):
            break
    proc.wait(timeout=5)
    os.close(mestre)
    texto = saida.decode(errors='replace')
    confere("['esq', 'esq', 'dir', 'centro', 'sai']" in texto,
            'a, seta esq., d, espaco e q chegam sem Enter e na ordem')


def grupo4():
    print('4. rede.py')
    img = np.arange(120 * 160 * 3, dtype=np.uint32).reshape(120, 160, 3) % 251
    img = img.astype(np.uint8)
    e = rede.preparar(img)
    confere(e.shape == rede.ENTRADA, 'preparar: 160x120 -> %s' % (e.shape,))
    confere(np.array_equal(e[0, 0], img[rede.CORTE_TOPO, 0]) and
            np.array_equal(e[1, 1], img[rede.CORTE_TOPO + 2, 2]),
            'preparar corta o topo e pega 1 pixel a cada 2, sem mexer nos canais')
    rng = np.random.default_rng(0)
    x = rng.normal(size=(5, 6, 2)).astype(np.float32)
    k = rng.normal(size=(3, 3, 2, 4)).astype(np.float32)
    xp = np.pad(x, ((1, 1), (1, 1), (0, 0)))
    ingenua = np.zeros((5, 6, 4), np.float32)
    for i in range(5):
        for j in range(6):
            for f in range(4):
                ingenua[i, j, f] = np.sum(xp[i:i + 3, j:j + 3, :] * k[:, :, :, f])
    confere(np.allclose(rede._conv_same(x, k), ingenua, atol=1e-5),
            'convolucao same = o laco ingenuo')
    confere(np.array_equal(rede._maxpool2(np.arange(15.0).reshape(3, 5, 1))[..., 0],
                           np.array([[6.0, 8.0]])), 'maxpool 2x2 descarta a sobra (3x5 -> 1x2)')
    ref = AMOSTRA / 'modelo' / 'referencia.npz'
    pesos = AMOSTRA / 'modelo' / 'pesos.npz'
    if not (ref.exists() and pesos.exists()):
        confere(False, 'amostra/modelo/ tem pesos.npz e referencia.npz')
        return
    r = np.load(ref)
    n = rede.Rede(pesos)
    p = np.array([n(xi) for xi in r['entrada']])
    dif = float(np.max(np.abs(p - r['saida'])))
    confere(dif < 1e-4, 'a rede em NumPy reproduz o Keras nas %d entradas gravadas '
            '(maior diferenca %.1e)' % (len(p), dif))
    p_rgb = np.array([n(xi[..., ::-1]) for xi in r['entrada']])
    confere(np.max(np.abs(p_rgb - p)) > 1e-3, 'trocar BGR por RGB muda a saida (%.3f)'
            % float(np.max(np.abs(p_rgb - p))))


def ler_csv(caminho):
    with open(caminho, newline='') as f:
        leitor = csv.DictReader(f)
        return leitor.fieldnames, list(leitor)


def grupo5():
    print('5. avaliar.py e as tabelas da amostra')
    confere(avaliar.COLUNAS[:7] == COMUNS, 'as 7 primeiras colunas sao as comuns (PID, BC, PPO)')
    m, s = avaliar.media_desvio([1.0, 2.0, 3.0])
    confere(m == 2.0 and abs(s - 1.0) < 1e-12, 'media 2, desvio amostral 1 para [1, 2, 3]')
    confere(avaliar.media_desvio([5.0]) == (5.0, 0.0), 'um valor so: desvio 0')
    confere(avaliar.motivo({'out_of_road': True, 'max_step': True}) == 'out_of_road',
            'motivo: out_of_road antes de max_step')
    confere(avaliar.motivo({'arrive_dest': True}) == 'arrive_dest', 'motivo: arrive_dest')
    tabelas = sorted(t for t in (AMOSTRA / 'resultados').glob('*.csv')
                     if not t.name.startswith('traj-'))
    confere(len(tabelas) >= 2, '%d tabelas em amostra/resultados/' % len(tabelas))
    for t in tabelas:
        cab, linhas = ler_csv(t)
        confere(cab == avaliar.COLUNAS and linhas, '%s: colunas da regua, %d episodios'
                % (t.name, len(linhas)))
        texto = avaliar.texto_resumo([{k: (v if k == 'motivo' else float(v))
                                       for k, v in x.items()} for x in linhas], t.stem)
        md = t.with_name(t.stem + '-resumo.md')
        if md.exists():
            confere(texto.split('\n')[4:] == md.read_text().rstrip('\n').split('\n')[4:],
                    '%s: o resumo gravado bate com o CSV' % md.name)
    pidcsv = AMOSTRA / 'resultados' / 'pid.csv'
    if pidcsv.exists():
        _, linhas = ler_csv(pidcsv)
        confere(len(linhas) == 10 and all(x['concluiu'] == '1' for x in linhas),
                'pid.csv: 10 episodios, 10 concluidos (o numero do README)')
    bccsv = AMOSTRA / 'resultados' / 'bc.csv'
    if bccsv.exists():
        _, linhas = ler_csv(bccsv)
        confere(len(linhas) == 10 and sum(x['concluiu'] == '1' for x in linhas) == 8,
                'bc.csv: 10 episodios, 8 concluidos (o numero do README)')
    for t in sorted((AMOSTRA / 'resultados').glob('traj-*.csv')):
        cab, linhas = ler_csv(t)
        confere(cab[:4] == ['episodio', 'semente', 'passo', 'desvio_m'] and len(linhas) > 400,
                '%s: trajetoria com %d passos' % (t.name, len(linhas)))
    trajs = sorted(str(t) for t in (AMOSTRA / 'resultados').glob('traj-*.csv'))
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print('  [pulado] sem matplotlib: o trajetorias.py nao foi rodado')
        return
    with tempfile.TemporaryDirectory() as d:
        png = os.path.join(d, 't.png')
        r = subprocess.run([sys.executable, '-B', str(AQUI / 'trajetorias.py'), '--csv'] + trajs
                           + ['--png', png, '--empurrao'], capture_output=True, text=True)
        ok = r.returncode == 0 and os.path.getsize(png) > 1000
        confere(ok and 'desvio max 3.65' in r.stdout,
                'trajetorias.py desenha as trajetorias da amostra (BC chega a 3,65 m)')


def grupo6():
    print('6. amostra/dataset')
    pasta = AMOSTRA / 'dataset'
    cab, linhas = ler_csv(pasta / 'acoes.csv')
    confere(cab == coletar.COLUNAS, 'acoes.csv tem as colunas do coletar.COLUNAS')
    confere(len({x['episodio'] for x in linhas}) >= 2,
            'mais de um episodio (a divisao por episodio precisa)')
    confere(all(-1.0 <= float(x['direcao']) <= 1.0 for x in linhas), 'direcao em [-1, 1]')
    try:
        import cv2
    except ImportError:
        print('  [pulado] sem cv2 neste Python: os PNG nao foram abertos')
        cv2 = None
    if cv2 is not None:
        formas = {cv2.imread(str(pasta / x['arquivo']), cv2.IMREAD_UNCHANGED).shape
                  for x in linhas}
        confere(formas == {(120, 160, 3)}, 'todos os %d PNG sao 160x120x3' % len(linhas))
        img = cv2.imread(str(pasta / linhas[0]['arquivo']))
        ceu = img[:20].reshape(-1, 3).mean(axis=0)
        confere(ceu[0] > ceu[2], 'o ceu e azul no canal 0: o PNG esta em BGR (B %.0f, R %.0f)'
                % (ceu[0], ceu[2]))
    r = subprocess.run([sys.executable, '-B', str(AQUI / 'histograma.py'), '--pasta', str(pasta)],
                       capture_output=True, text=True)
    confere(r.returncode == 0 and '| quadros | %d |' % len(linhas) in r.stdout,
            'histograma.py roda na amostra e conta %d quadros' % len(linhas))


def grupo7():
    print('7. higiene')
    for p in sorted(AQUI.glob('*.py')):
        texto = p.read_bytes()
        try:
            ast.parse(texto)
            ok = True
        except SyntaxError:
            ok = False
        confere(ok, '%s: ast.parse' % p.name)
        confere(all(b < 128 for b in texto), '%s: ASCII puro' % p.name)
        longas = [i for i, l in enumerate(texto.decode().splitlines(), 1) if len(l) > 99]
        confere(not longas, '%s: linhas <= 99 colunas %s' % (p.name, longas[:3] or ''))
    grandes = [str(p.relative_to(AQUI)) for p in AQUI.rglob('*')
               if p.is_file() and p.stat().st_size > 2 * 1024 * 1024]
    confere(not grandes, 'nenhum arquivo > 2 MB %s' % (grandes or ''))
    total = sum(p.stat().st_size for p in (AMOSTRA / 'dataset').glob('*'))
    confere(total < 2 * 1024 * 1024, 'amostra/dataset tem %.2f MB (< 2)' % (total / 2 ** 20))


def achar(pedido, var, venv):
    for c in (pedido, os.environ.get(var),
              os.path.join(os.environ.get('PB_DIR', ''), venv, 'bin', 'python')):
        if c and os.path.exists(c):
            return c
    return None


def rodar(cmd, camera=False, **kw):
    if camera and not os.environ.get('DISPLAY'):
        if not shutil.which('xvfb-run'):
            return None
        cmd = XVFB + cmd
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(AQUI), **kw)


def grupo8(pedido):
    print('8. com o MetaDrive')
    py = achar(pedido, 'METADRIVE_PYTHON', '.venv-metadrive')
    if py is None:
        print('  [pulado] nenhum Python com metadrive (--metadrive ou METADRIVE_PYTHON)')
        return
    r = rodar([py, '-B', 'pid.py', '--episodios', '2'])
    confere(r.returncode == 0 and r.stdout.count('arrive_dest') == 2,
            'pid.py --episodios 2: dois arrive_dest')
    with tempfile.TemporaryDirectory() as d:
        r = rodar([py, '-B', 'coletar.py', '--piloto', 'pid', '--quadros', '3',
                   '--saida', d], camera=True)
        if r is None:
            print('  [pulado] sem DISPLAY e sem xvfb-run')
            return
        _, linhas = ler_csv(os.path.join(d, 'acoes.csv'))
        confere(r.returncode == 0 and len(linhas) == 3, 'coletar.py --piloto pid grava 3 quadros')
        r = rodar([py, '-B', 'avaliar.py', '--controlador', 'bc', '--modelo',
                   str(AMOSTRA / 'modelo' / 'pesos.npz'), '--episodios', '1',
                   '--horizonte', '5', '--saida', os.path.join(d, 'bc')], camera=True)
        _, linhas = ler_csv(os.path.join(d, 'bc.csv')) if r.returncode == 0 else (None, [])
        confere(len(linhas) == 1 and linhas[0]['passos'] == '5',
                'o BC da amostra dirige 5 passos com a camera, no venv do MetaDrive')
        confere(_humano_terminal(py, d), 'humano-terminal: a tecla `a` vira direcao > 0 no CSV')


def _humano_terminal(py, d):
    """coletar.py --piloto humano-terminal num pty, com a janela no X (ou Xvfb)."""
    import pty
    import select
    saida = os.path.join(d, 'humano')
    cmd = [py, '-B', 'coletar.py', '--piloto', 'humano-terminal', '--quadros', '8',
           '--passo', '1', '--saida', saida]
    if not os.environ.get('DISPLAY'):
        cmd = XVFB + cmd
    mestre, escravo = pty.openpty()
    proc = subprocess.Popen(cmd, stdin=escravo, stdout=escravo, stderr=escravo,
                            cwd=str(AQUI), close_fds=True)
    os.close(escravo)
    t0, buf = time.time(), b''
    # manda `a` de tempos em tempos ate o processo acabar (8 quadros)
    while proc.poll() is None and time.time() - t0 < 300:
        if select.select([mestre], [], [], 0.5)[0]:
            try:
                buf += os.read(mestre, 4096)
            except OSError:
                pass
        if b'episodio' not in buf:
            os.write(mestre, b'a')
    proc.wait(timeout=30)
    os.close(mestre)
    try:
        _, linhas = ler_csv(os.path.join(saida, 'acoes.csv'))
    except OSError:
        return False
    return len(linhas) == 8 and max(float(x['direcao']) for x in linhas) > 0.0


def grupo9(pedido):
    print('9. com o TensorFlow')
    py = achar(pedido, 'CNN_PYTHON', '.venv-cnn')
    if py is None:
        print('  [pulado] nenhum Python com tensorflow (--cnn ou CNN_PYTHON)')
        return
    with tempfile.TemporaryDirectory() as d:
        r = rodar([py, '-B', 'treinar_bc.py', '--pasta', str(AMOSTRA / 'dataset'),
                   '--epocas', '1', '--saida', d, '--comparar-divisao'],
                  env=dict(os.environ, OMP_NUM_THREADS='1'))
        confere(r.returncode == 0, 'treinar_bc.py --epocas 1 --comparar-divisao na amostra%s'
                % ('' if r.returncode == 0 else ': ' + r.stderr.strip()[-300:]))
        if r.returncode:
            return
        for nome in ('pesos.npz', 'referencia.npz', 'modelo.keras', 'tabela.txt',
                     'curvas.png', 'divisao.csv', 'historico.json'):
            confere(os.path.exists(os.path.join(d, nome)), 'gravou %s' % nome)
        ref = np.load(os.path.join(d, 'referencia.npz'))
        n = rede.Rede(os.path.join(d, 'pesos.npz'))
        dif = max(abs(n(x) - y) for x, y in zip(ref['entrada'], ref['saida']))
        confere(dif < 1e-4, 'o pesos.npz recem-exportado bate com o Keras (%.1e)' % dif)
        tabela = open(os.path.join(d, 'tabela.txt')).read()
        confere('por episodio' in tabela and 'por quadro' in tabela,
                'a tabela tem as duas divisoes')


def principal():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--metadrive', help='Python do venv do MetaDrive (grupo 8)')
    p.add_argument('--cnn', help='Python do venv da CNN (grupo 9)')
    args = p.parse_args()
    for g in (grupo1, grupo2, grupo3, grupo4, grupo5, grupo6, grupo7):
        g()
    grupo8(args.metadrive)
    grupo9(args.cnn)
    if FALHAS:
        print('%d falha(s).' % len(FALHAS))
        return 1
    print('todos os testes passaram.')
    return 0


if __name__ == '__main__':
    sys.exit(principal())
