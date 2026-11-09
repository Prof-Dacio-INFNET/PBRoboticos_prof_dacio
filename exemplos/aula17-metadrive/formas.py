#!/usr/bin/env python3
"""Hough Circle e Harris Corner sobre quadros do MetaDrive -- e o que ha para achar.

    python3 formas.py --pasta amostra
    python3 formas.py --pasta amostra --sobreposicao formas-020.png --quadro 4

Imprime, por quadro, quantos circulos o cv2.HoughCircles achou (e quantos deles
estao ACIMA do horizonte, onde nao ha nada redondo na cena) e quantos cantos o
cv2.cornerHarris marcou. Com --sobreposicao, grava um quadro com os circulos em
magenta e os cantos em vermelho.

O QUE EXISTE NA CENA DO METADRIVE 0.4.3 (mapa procedural, MetaDriveEnv),
lido no codigo instalado (metadrive/component/static_object/traffic_object.py e
metadrive/engine) e visto nos quadros:

    - NAO HA PLACA DE TRANSITO. Nenhuma classe de placa existe no pacote.
    - NAO HA SEMAFORO no mapa procedural; ha um modelo de semaforo nos assets,
      mas ele so e usado pelo ScenarioEnv (cenarios reais, Waymo/nuScenes).
    - HA cones (TrafficCone, laranja), triangulos de advertencia
      (TrafficWarning), barreiras (TrafficBarrier) e veiculos de cinco tamanhos.

Ou seja: o enunciado diz "formas geometricas (placas)", e placa nao ha. O que
o Hough Circle pode honestamente achar aqui e nada (o cone visto de tras e um
triangulo, a roda do carro da frente nao aparece). Medido nos 60 quadros da
semente 7: com param2 = 30, ZERO circulos; com 20, 16 circulos em 15 quadros,
12 deles no ceu; com 15, 151 circulos, 89 no ceu. Todo circulo que aparece e
falso positivo -- nuvem, borda de caminhao --, e a contagem acima do horizonte
mede isso. Experimente com --param2. O Harris acha cantos, e cantos ha
muitos: caminhao, carro, ponta de faixa tracejada, cone. Quem quiser circulo
de verdade precisa por um objeto redondo na cena (veja o README, "Como
adequar").
"""
import argparse
import pathlib
import sys

import cv2
import numpy as np

# --- parametros declarados antes de medir ---
# HoughCircles: dp=1 (acumulador do tamanho da imagem), distancia minima entre
# centros, limiar alto do Canny interno (param1) e votos minimos (param2).
# param2 baixo acha circulo em tudo; alto nao acha nada. 30 e o meio-termo
# classico para quadros de 320x240.
HOUGH_DP = 1.0
HOUGH_DIST_MIN = 20
HOUGH_PARAM1 = 100
HOUGH_PARAM2 = 30
HOUGH_RAIO_MIN = 4
HOUGH_RAIO_MAX = 40
DESFOQUE_MEDIANA = 5          # antes do Hough: tira o serrilhado do render

# cornerHarris: vizinhanca 2, Sobel 3, k = 0,04 (o valor do artigo de 1988).
HARRIS_BLOCO = 2
HARRIS_SOBEL = 3
HARRIS_K = 0.04
# Limiar RELATIVO ao maior valor do quadro. Atencao: limiar relativo garante
# cantos em QUALQUER imagem, ate numa parede lisa -- o maior valor sempre
# passa. Por isso o numero de cantos nao e prova de que ha objeto.
HARRIS_LIMIAR_REL = 0.01

# Linha do horizonte, em fracao da altura. Medida nos quadros do MetaDrive com
# a camera padrao do RGBCamera: o horizonte cai em ~0,55 da altura.
HORIZONTE = 0.55

AVISO_CENA = ("cena: o MetaDrive (mapa procedural) NAO TEM PLACA nem semaforo; "
              "ha cones, triangulos, barreiras e veiculos.")


def circulos(bgr, param2=None):
    """Devolve uma lista de (x, y, r) inteiros. Vazia se nao achar nada."""
    param2 = HOUGH_PARAM2 if param2 is None else param2
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cinza = cv2.medianBlur(cinza, DESFOQUE_MEDIANA)
    achados = cv2.HoughCircles(cinza, cv2.HOUGH_GRADIENT, HOUGH_DP, HOUGH_DIST_MIN,
                               param1=HOUGH_PARAM1, param2=param2,
                               minRadius=HOUGH_RAIO_MIN, maxRadius=HOUGH_RAIO_MAX)
    if achados is None:
        return []
    # OpenCV 4 devolve (1, N, 3) e o 5 pode devolver (N, 3): normaliza aqui.
    return [tuple(int(round(v)) for v in c) for c in np.asarray(achados).reshape(-1, 3)]


def cantos(bgr):
    """Devolve a lista de (x, y) dos cantos Harris, um por aglomerado.

    O mapa do Harris marca VARIOS pixels vizinhos para cada canto; contar
    pixels inflaria o numero. Cada componente conexo do mapa limiarizado conta
    uma vez, e o ponto devolvido e o centroide dele.
    """
    cinza = np.float32(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    resp = cv2.cornerHarris(cinza, HARRIS_BLOCO, HARRIS_SOBEL, HARRIS_K)
    if resp.max() <= 0:
        return []
    marca = np.uint8(resp > HARRIS_LIMIAR_REL * resp.max()) * 255
    n, _, _, centros = cv2.connectedComponentsWithStats(marca)
    return [(int(round(x)), int(round(y))) for x, y in centros[1:n]]


def analisar(bgr, param2=None):
    """O resumo de um quadro: contagens e as listas, para desenhar depois."""
    alt = bgr.shape[0]
    cs = circulos(bgr, param2)
    ks = cantos(bgr)
    y_hor = HORIZONTE * alt
    return {
        "circulos": cs,
        "circulos_no_ceu": sum(1 for _, y, _ in cs if y < y_hor),
        "cantos": ks,
        "cantos_na_pista": sum(1 for _, y in ks if y >= y_hor),
    }


def desenhar(bgr, res):
    """Circulos em magenta, cantos em vermelho, horizonte em cinza."""
    out = bgr.copy()
    alt, larg = out.shape[:2]
    y_hor = int(HORIZONTE * alt)
    cv2.line(out, (0, y_hor), (larg - 1, y_hor), (130, 130, 135), 1)
    for x, y, r in res["circulos"]:
        cv2.circle(out, (x, y), r, (200, 70, 215), 2)
    for x, y in res["cantos"]:
        cv2.circle(out, (x, y), 2, (48, 48, 235), -1)
    cv2.putText(out, "circ %d (ceu %d)  cantos %d" % (
        len(res["circulos"]), res["circulos_no_ceu"], len(res["cantos"])),
        (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.putText(out, "sem placa na cena", (6, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (48, 48, 235), 1, cv2.LINE_AA)
    return out


def percorrer(pasta, param2=None):
    """Lista (nome, resultado) para cada quadroNNN.png da pasta, em ordem."""
    saida = []
    for caminho in sorted(pathlib.Path(pasta).glob("quadro*.png")):
        bgr = cv2.imread(str(caminho))
        if bgr is not None:
            saida.append((caminho.name, analisar(bgr, param2)))
    return saida


def principal(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", required=True, help="pasta com quadroNNN.png")
    p.add_argument("--sobreposicao", help="grava a sobreposicao de um quadro neste PNG")
    p.add_argument("--quadro", type=int, default=0,
                   help="qual quadro (posicao na pasta) vai para a sobreposicao (0)")
    p.add_argument("--param2", type=int, default=HOUGH_PARAM2,
                   help="votos minimos do HoughCircles (%d); baixe para ver os falsos"
                   % HOUGH_PARAM2)
    args = p.parse_args(argv)
    linhas = percorrer(args.pasta, args.param2)
    if not linhas:
        print("nenhum quadroNNN.png em %s" % args.pasta)
        return 1
    print(AVISO_CENA)
    print("%-14s %9s %14s %7s %15s" % ("quadro", "circulos", "circ. no ceu", "cantos",
                                      "cantos na pista"))
    for nome, r in linhas:
        print("%-14s %9d %14d %7d %15d" % (nome, len(r["circulos"]), r["circulos_no_ceu"],
                                          len(r["cantos"]), r["cantos_na_pista"]))
    tc = sum(len(r["circulos"]) for _, r in linhas)
    tceu = sum(r["circulos_no_ceu"] for _, r in linhas)
    kk = [len(r["cantos"]) for _, r in linhas]
    print("total: %d quadros, %d circulos (%d acima do horizonte, falsos por construcao), "
          "cantos por quadro min %d, mediana %d, max %d"
          % (len(linhas), tc, tceu, min(kk), sorted(kk)[len(kk) // 2], max(kk)))
    print("PLACA: nenhuma -- o MetaDrive nao tem placa; nenhum circulo acima e placa.")
    if args.sobreposicao:
        i = min(max(args.quadro, 0), len(linhas) - 1)
        nome = linhas[i][0]
        bgr = cv2.imread(str(pathlib.Path(args.pasta) / nome))
        cv2.imwrite(args.sobreposicao, desenhar(bgr, linhas[i][1]))
        print("sobreposicao: %s (de %s)" % (args.sobreposicao, nome))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
