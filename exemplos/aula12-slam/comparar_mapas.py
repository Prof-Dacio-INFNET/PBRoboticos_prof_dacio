#!/usr/bin/env python3
"""Mede o mapa que o SLAM construiu contra o mundo de verdade.

Por que isto e' raro: num robo real voce NAO tem a verdade -- so' tem o mapa, e
"parece bom" e' tudo o que da' para dizer. Como o nosso mundo e' sintetico, a
verdade existe, e da' para transformar "parece bom" em numero. E' a mesma
disciplina da Aula 9, agora aplicada a mapa em vez de detector.

    python3 comparar_mapas.py mapa.yaml
    python3 comparar_mapas.py mapa.yaml --origem-robo 2.0 4.0

Nao precisa de ROS 2. Precisa do par mapa.pgm + mapa.yaml que o map_saver_cli
gera, e do pacote aula11_mundo (para saber onde ficam as paredes) -- que ele
procura ao lado, na raiz do workspace, em $PB_WS/src e no pacote instalado,
nessa ordem. Copie-o para a raiz do workspace e ele sobrevive ao reboot: /tmp
nao sobrevive, e a tarefa da semana e' feita depois da aula.

SOBRE A ORIGEM: o quadro `map` do SLAM nasce onde o ROBO comecou, nao onde o
mundo comeca. No nosso mundo o robo parte de (2, 4), entao e' esse o desconto
entre os dois sistemas. Errar isto faz o mapa parecer pessimo estando certo.
"""
import argparse
import os
import pathlib
import sys

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent


def achar_cenario() -> str:
    """Acha o pacote aula11_mundo, que e' a VERDADE contra a qual se mede.

    Este script roda durante a semana, fora da aula, e a essa altura a copia do
    material costuma ja' ter sumido de /tmp -- que o sistema limpa no reboot.
    Entao procure em mais de um lugar, e, se nao achar, diga exatamente o que
    faltou: um ImportError de tres linhas nao ensina nada a ninguem.
    """
    candidatos = [
        AQUI.parent / 'aula11-mundo' / 'aula11_mundo',   # rodando de dentro do material
        AQUI / 'src' / 'aula11_mundo',                   # copiado para a raiz do workspace
    ]
    if os.environ.get('PB_WS'):
        candidatos.append(pathlib.Path(os.environ['PB_WS']) / 'src' / 'aula11_mundo')
    for c in candidatos:
        if (c / 'aula11_mundo' / 'mapa.py').is_file():
            sys.path.insert(0, str(c))
            return str(c)
    try:                                                 # workspace sourceado: pacote instalado
        import aula11_mundo.mapa                         # noqa: F401
        return 'pacote aula11_mundo instalado (workspace sourceado)'
    except ImportError:
        sys.exit(
            'nao achei o cenario de verdade (o pacote aula11_mundo).\n'
            'Ele e a regua: sem ele nao da para medir mapa nenhum. Tres saidas:\n'
            '  1) rode este script de dentro do material, onde aula11-mundo fica ao lado;\n'
            '  2) copie-o para a raiz do seu workspace, ao lado de src/aula11_mundo;\n'
            '  3) ou sourceie o workspace:  source "$PB_WS/install/setup.bash"')


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


def desenhar_diferenca(verdade, ocup_slam, conhece, caminho, escala=3):
    """Pinta cada celula pela categoria. Um numero diz QUANTO; a figura diz ONDE.

    E' a mesma ideia do OSD da Aula 9: o agregado esconde o lugar da falha, e
    olhar para o lugar costuma explicar o numero.
    """
    import cv2

    img = np.full((*verdade.shape, 3), 245, np.uint8)      # livre e concordando
    img[~conhece] = (205, 205, 205)                        # nao explorado
    img[verdade & ocup_slam & conhece] = (61, 33, 20)      # parede encontrada  (NAVY)
    img[verdade & ~ocup_slam & conhece] = (17, 163, 252)   # parede PERDIDA     (AMBER)
    img[~verdade & ocup_slam & conhece] = (60, 60, 220)    # parede FANTASMA    (vermelho)

    img = np.flipud(img).copy()                            # y cresce para cima
    img = cv2.resize(img, (img.shape[1] * escala, img.shape[0] * escala),
                     interpolation=cv2.INTER_NEAREST)

    # Legenda embutida: a figura vai para o relatorio sozinha.
    faixa = np.full((26 * 4, img.shape[1], 3), 255, np.uint8)
    for i, (cor, texto) in enumerate((
            ((61, 33, 20), 'parede encontrada'),
            ((17, 163, 252), 'parede perdida (o SLAM nao viu)'),
            ((60, 60, 220), 'parede fantasma (o SLAM inventou)'),
            ((205, 205, 205), 'nao explorado'))):
        y = 10 + i * 26
        cv2.rectangle(faixa, (10, y), (30, y + 16), cor, -1)
        cv2.putText(faixa, texto, (40, y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (40, 40, 40), 1, cv2.LINE_AA)

    cv2.imwrite(caminho, np.vstack([img, faixa]))
    return caminho


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mapa_yaml', help='o .yaml que o map_saver_cli gerou')
    ap.add_argument('--origem-robo', nargs=2, type=float, default=[2.0, 4.0],
                    metavar=('X', 'Y'), help='onde o robo comecou, no mundo (padrao 2 4)')
    ap.add_argument('--imagem', metavar='ARQ.png',
                    help='desenha a diferenca: o que bateu, o que faltou e o que foi inventado')
    a = ap.parse_args()

    try:
        import yaml
    except ImportError:
        sys.exit('falta o pyyaml:  sudo apt install python3-yaml')
    onde_cenario = achar_cenario()
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
    print(f'verdade de  : {onde_cenario}')
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

    if a.imagem:
        print(f'figura      : {desenhar_diferenca(verdade, ocup_slam, conhece, a.imagem)}')
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
