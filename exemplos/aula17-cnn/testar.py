#!/usr/bin/env python3
"""Prova o que da para provar sem treinar de verdade. Roda com o Python do venv.

    "$PB_DIR/.venv-cnn/bin/python" testar.py

Sete grupos, cada um com a resposta sabida de antemao:

    1  higiene dos .py: so ASCII, linhas de ate 99 colunas
    2  o gerador sintetico: contagem por classe, CSV, determinismo byte a byte
    3  o rotular.py: o teclado (funcao pura) e o --so-sugestao sobre a amostra
       da aula17-metadrive, se ela estiver ao lado
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
import csv
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

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


def grupo3_rotular(tmp):
    print('3. rotular.py')
    import rotular as rt
    rot = {}
    i, sair, salvar = rt.aplicar_tecla(ord('2'), 0, 5, 'q0.png', 'via_livre', rot)
    confere((i, sair, rot.get('q0.png')) == (1, False, 'obstaculo'),
            'tecla 2 -> obstaculo e avanca')
    i, *_ = rt.aplicar_tecla(13, 1, 5, 'q1.png', 'cruzamento', rot)
    confere(rot.get('q1.png') == 'cruzamento' and i == 2, 'Enter aceita a sugestao e avanca')
    i, *_ = rt.aplicar_tecla(65361, 2, 5, 'q2.png', 'via_livre', rot)
    confere(i == 1 and 'q2.png' not in rot, 'seta esquerda volta sem rotular')
    i, *_ = rt.aplicar_tecla(ord('3'), 4, 5, 'q4.png', 'via_livre', rot)
    confere(i == 4, 'no ultimo quadro, rotular nao passa do fim')
    _, sair, salvar = rt.aplicar_tecla(ord('q'), 0, 5, 'q0.png', 'via_livre', rot)
    confere(sair and salvar, 'q grava e sai')
    if not (AMOSTRA_MD / 'estado.csv').exists():
        print('  [pulado] a aula17-metadrive/amostra nao esta ao lado desta pasta')
        return None
    saida = tmp / 'rotulos_amostra.csv'
    cod, out = rodar('rotular.py', '--pasta', AMOSTRA_MD, '--so-sugestao', '--saida', saida)
    confere(cod == 0, 'rotular.py --so-sugestao sobre a amostra sai com 0')
    linhas = ler_csv(saida)
    confere(list(linhas[0]) == ['arquivo', 'classe', 'sugerido'],
            'colunas arquivo,classe,sugerido')
    confere(len(linhas) == 12, '12 linhas: so os PNG que existem na amostra')
    confere(all(r['classe'] == r['sugerido'] for r in linhas), 'sem revisao, classe = sugerido')
    confere('nenhuma imagem de obstaculo' in out, 'avisa que obstaculo ficou vazio')
    return saida


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
