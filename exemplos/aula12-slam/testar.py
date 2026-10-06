#!/usr/bin/env python3
"""Confere o comparador de mapas antes de voce confiar no numero que ele da'.

Nao precisa de ROS 2 nem do slam_toolbox: os mapas de teste sao SINTETIZADOS a
partir do mundo de verdade, com defeitos conhecidos. Se o comparador acerta num
mapa cujo erro voce mesmo injetou, ele serve para medir o mapa do SLAM.

    python3 testar.py
"""
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'aula11-mundo' / 'aula11_mundo'))
from aula11_mundo.mapa import Mundo                                   # noqa: E402

ROBO = (2.0, 4.0)          # onde o robo comeca, no mundo
falhas = []


def conferir(nome, ok, detalhe=''):
    print(f'  {"ok  " if ok else "FALHA"}  {nome}{"  — " + detalhe if detalhe else ""}')
    if not ok:
        falhas.append(nome)


def escrever_mapa(destino: pathlib.Path, grade: np.ndarray, res: float,
                  origem, desconhecido=None):
    """Grava o par .pgm/.yaml no formato do map_saver_cli."""
    img = np.where(grade, 0, 254).astype(np.uint8)
    if desconhecido is not None:
        img[desconhecido] = 205
    img = np.flipud(img)                       # PGM cresce para baixo
    alt, larg = img.shape
    pgm = destino.with_suffix('.pgm')
    pgm.write_bytes(b'P5\n%d %d\n255\n' % (larg, alt) + img.tobytes())
    destino.write_text(
        f"image: {pgm.name}\nresolution: {res}\n"
        f"origin: [{origem[0]}, {origem[1]}, 0.0]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n", encoding='utf-8')
    return destino


def rodar(mapa_yaml, *extra):
    r = subprocess.run([sys.executable, str(AQUI / 'comparar_mapas.py'), str(mapa_yaml), *extra],
                       capture_output=True, text=True)
    return r.stdout, r.returncode


def numero(saida, rotulo):
    for linha in saida.splitlines():
        if linha.startswith(rotulo):
            return float(linha.split(':')[1].strip().split('%')[0])
    return float('nan')


mundo = Mundo()
tmp = pathlib.Path(tempfile.mkdtemp())

# O quadro `map` nasce no robo: a origem do mapa, em coordenadas de map, e'
# o canto do mundo visto de la'.
ORIGEM = (-ROBO[0], -ROBO[1])

print('1. mapa perfeito: o comparador tem de dizer que bate')
m = escrever_mapa(tmp / 'perfeito.yaml', mundo.grade, mundo.res, ORIGEM)
saida, rc = rodar(m)
conferir('concordancia >= 99%', numero(saida, 'concordancia') >= 99.0,
         f"{numero(saida, 'concordancia'):.1f}%")
conferir('paredes encontradas >= 99%', numero(saida, 'paredes') >= 99.0,
         f"{numero(saida, 'paredes'):.1f}%")
conferir('saida 0 (consistente)', rc == 0)

print('2. mapa deslocado 20 cm: tem de piorar, e de forma visivel')
m = escrever_mapa(tmp / 'torto.yaml', np.roll(mundo.grade, 4, axis=1), mundo.res, ORIGEM)
saida_t, _ = rodar(m)
conferir('concordancia cai', numero(saida_t, 'concordancia') < numero(saida, 'concordancia'),
         f"{numero(saida_t, 'concordancia'):.1f}%")
conferir('aparecem paredes fantasma',
         int([l for l in saida_t.splitlines() if 'fantasmas' in l][0].split(':')[1].split()[0]) > 100)

print('3. metade do mundo inexplorada: cobertura tem de cair, concordancia nao')
desc = np.zeros_like(mundo.grade, dtype=bool)
desc[:, mundo.nx // 2:] = True
m = escrever_mapa(tmp / 'parcial.yaml', mundo.grade, mundo.res, ORIGEM, desconhecido=desc)
saida_p, _ = rodar(m)
conferir('cobertura ~50%', 40 <= numero(saida_p, 'cobertura') <= 60,
         f"{numero(saida_p, 'cobertura'):.1f}%")
conferir('concordancia continua alta', numero(saida_p, 'concordancia') >= 99.0,
         f"{numero(saida_p, 'concordancia'):.1f}%")

print('4. origem errada: o comparador tem de acusar, nao inventar')
m = escrever_mapa(tmp / 'perfeito2.yaml', mundo.grade, mundo.res, ORIGEM)
saida_o, rc_o = rodar(m, '--origem-robo', '0', '0')
conferir('concordancia despenca ou nao cobre', numero(saida_o, 'concordancia') < 95.0
         or 'nao cobre' in saida_o, f"{numero(saida_o, 'concordancia'):.1f}%")
conferir('saida diferente de 0', rc_o != 0)

print()
if falhas:
    print(f'{len(falhas)} FALHA(S): ' + '; '.join(falhas))
    raise SystemExit(1)
print('todos os testes passaram.')
