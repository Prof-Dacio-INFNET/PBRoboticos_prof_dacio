#!/usr/bin/env python3
"""Mede o mapa que o SLAM construiu contra o mundo de verdade.

Por que isto e' raro: num robo real voce NAO tem a verdade -- so' tem o mapa, e
"parece bom" e' tudo o que da' para dizer. Como o nosso mundo e' sintetico, a
verdade existe, e da' para transformar "parece bom" em numero. E' a mesma
disciplina da Aula 9, agora aplicada a mapa em vez de detector.

    python3 comparar_mapas.py mapa.yaml
    python3 comparar_mapas.py mapa.yaml --origem-robo 2.0 4.0

Nao precisa de ROS 2. Precisa do par mapa.pgm + mapa.yaml que o map_saver_cli
gera, e do pacote aula11_mundo ao lado (para saber onde ficam as paredes).

SOBRE A ORIGEM: o quadro `map` do SLAM nasce onde o ROBO comecou, nao onde o
mundo comeca. No nosso mundo o robo parte de (2, 4), entao e' esse o desconto
entre os dois sistemas. Errar isto faz o mapa parecer pessimo estando certo.
"""
import argparse
import pathlib
import sys

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'aula11-mundo' / 'aula11_mundo'))

VERDE, VERMELHO, AMARELO, FIM = '\033[32m', '\033[31m', '\033[33m', '\033[0m'


def ler_pgm(caminho: pathlib.Path) -> np.ndarray:
    """Le um PGM binario (P5). A linha 0 do arquivo e' o TOPO da imagem."""
    dados = caminho.read_bytes()
    if not dados.startswith(b'P5'):
        raise ValueError(f'{caminho} nao e um PGM binario (P5)')

    campos, i = [], 2
    while len(campos) < 3:
        while i < len(dados) and dados[i:i + 1].isspace():
            i += 1
        if dados[i:i + 1] == b'#':                       # comentario ate o fim da linha
            while i < len(dados) and dados[i:i + 1] != b'\n':
                i += 1
            continue
        j = i
        while j < len(dados) and not dados[j:j + 1].isspace():
            j += 1
        campos.append(int(dados[i:j]))
        i = j
    largura, altura, _maxval = campos
    i += 1                                               # o unico whitespace apos maxval
    return np.frombuffer(dados[i:i + largura * altura], dtype=np.uint8).reshape(altura, largura)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mapa_yaml', help='o .yaml que o map_saver_cli gerou')
    ap.add_argument('--origem-robo', nargs=2, type=float, default=[2.0, 4.0],
                    metavar=('X', 'Y'), help='onde o robo comecou, no mundo (padrao 2 4)')
    a = ap.parse_args()

    try:
        import yaml
    except ImportError:
        sys.exit('falta o pyyaml:  sudo apt install python3-yaml')
    from aula11_mundo.mapa import Mundo

    cam_yaml = pathlib.Path(a.mapa_yaml).resolve()
    meta = yaml.safe_load(cam_yaml.read_text(encoding='utf-8'))
    pgm = ler_pgm(cam_yaml.parent / meta['image'])

    res = float(meta['resolution'])
    ox, oy, *_ = [float(v) for v in meta['origin']]
    ocupado_ate = float(meta.get('occupied_thresh', 0.65))
    livre_a_partir = float(meta.get('free_thresh', 0.196))

    # p = probabilidade de ocupacao. Com negate=0, pixel branco (254) e' livre.
    p = (255.0 - pgm.astype(np.float64)) / 255.0
    slam_ocupado = p > ocupado_ate
    slam_livre = p < livre_a_partir
    slam_conhece = slam_ocupado | slam_livre

    mundo = Mundo()
    rx, ry = a.origem_robo
    alt, larg = pgm.shape

    # Para cada celula do mundo, onde ela cai no PGM.
    ys, xs = np.mgrid[0:mundo.ny, 0:mundo.nx]
    wx = (xs + 0.5) * mundo.res
    wy = (ys + 0.5) * mundo.res
    col = ((wx - rx - ox) / res).astype(np.int64)
    linha_de_baixo = ((wy - ry - oy) / res).astype(np.int64)
    lin = alt - 1 - linha_de_baixo                        # PGM cresce para baixo

    dentro = (col >= 0) & (col < larg) & (lin >= 0) & (lin < alt)
    cc, ll = np.clip(col, 0, larg - 1), np.clip(lin, 0, alt - 1)

    verdade = mundo.grade
    conhece = slam_conhece[ll, cc] & dentro
    ocup_slam = slam_ocupado[ll, cc] & dentro

    n_conhece = int(conhece.sum())
    if n_conhece == 0:
        print('O mapa nao cobre nenhuma celula do mundo. Confira --origem-robo.')
        return 1

    parede_v = verdade & conhece
    livre_v = (~verdade) & conhece
    achou = int((parede_v & ocup_slam).sum())
    perdeu = int((parede_v & ~ocup_slam).sum())
    fantasma = int((livre_v & ocup_slam).sum())
    concorda = int(((verdade == ocup_slam) & conhece).sum())

    print(f'mapa        : {cam_yaml.name}  ({larg} x {alt} celulas, {res} m)')
    print(f'mundo       : {mundo.nx} x {mundo.ny} celulas, {mundo.res} m')
    print(f'origem robo : ({rx}, {ry})')
    print()
    print(f'cobertura   : {100 * n_conhece / verdade.size:5.1f}% do mundo foi explorado')
    print(f'concordancia: {100 * concorda / n_conhece:5.1f}% das celulas conhecidas batem')
    print()
    if parede_v.sum():
        print(f'paredes     : {100 * achou / parede_v.sum():5.1f}% encontradas '
              f'({achou} de {int(parede_v.sum())})')
        print(f'  perdidas  : {perdeu:6d} celulas de parede que o mapa acha livres')
    print(f'  fantasmas : {fantasma:6d} celulas livres que o mapa acha parede')
    print()

    acerto = concorda / n_conhece
    if acerto >= 0.95:
        v, cor = 'mapa consistente com o mundo', VERDE
    elif acerto >= 0.85:
        v, cor = 'mapa utilizavel, com deriva residual visivel', AMARELO
    else:
        v, cor = 'mapa inconsistente -- confira a origem, a TF e o fechamento de laco', VERMELHO
    print(f'Veredito: {cor}{v}{FIM}')
    return 0 if acerto >= 0.85 else 1


if __name__ == '__main__':
    raise SystemExit(main())
