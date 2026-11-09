#!/usr/bin/env python3
"""Roda o detector de faixas da Aula 13 sobre quadros do MetaDrive, duas vezes.

    python3 medir_faixas.py --pasta amostra
    python3 medir_faixas.py --pasta quadros --sobreposicao faixas-020.png --quadro 20

Nao muda uma linha do faixas.py da Aula 13: importa o arquivo de la e chama
detectar_faixas() com duas configuracoes, a PADRAO (a da Aula 13, afinada na
cena sintetica) e a AJUSTADA (declarada abaixo, antes de medir). A diferenca
entre as duas colunas da tabela e a aula: um detector afinado numa cena nao
viaja sozinho para outra.

POR QUE A PADRAO NAO ACHA NADA no MetaDrive (medido, nao suposto):

  1. a pintura branca do MetaDrive chega no maximo a V = 149 no HSV; o limiar
     da Aula 13 e branco_v_min = 150. Um ponto de diferenca, mascara vazia.
  2. a faixa amarela central tem 1 px de largura a 320x240 (2 px a 640x480),
     e a abertura morfologica 3x3 da etapa 1 apaga tudo o que tem menos de 3 px.
     Por isso a AJUSTADA amplia o quadro 3x (vizinho mais proximo) ANTES de
     detectar: a linha passa a ter 3 px e sobrevive.
  3. com a linha amarela inteira, o contraste dela no CINZA contra o asfalto e
     de uns 30 niveis -- pouco para Canny(50, 150). A AJUSTADA usa (20, 60).

Sem verdade de faixa nao ha erro a medir: a tabela diz QUANTAS vezes cada
faixa foi achada e com quantos segmentos, nao se ela esta no lugar certo.
"""
import argparse
import importlib.util
import os
import pathlib
import sys

import cv2

# --- a configuracao AJUSTADA, declarada antes de medir ---
ESCALA = 3                    # ampliacao do quadro antes do detector (1 = nenhuma)
AJUSTES = {
    "branco_v_min": 130,      # a pintura do MetaDrive para em V = 149
    "amarelo_v_min": 70,      # a amarela fica em V ~ 90..149
    "canny": (20, 60),        # contraste da amarela no cinza ~ 30 niveis
}

AQUI = pathlib.Path(__file__).resolve().parent
AULA13_PADRAO = AQUI.parent / "aula13-veicular" / "faixas.py"


def carregar_faixas(caminho):
    """Importa o faixas.py da Aula 13 pelo caminho, sem copiar o arquivo."""
    caminho = pathlib.Path(caminho)
    if not caminho.is_file():
        raise SystemExit("ERRO: nao achei %s. Baixe a aula13-veicular ao lado desta pasta "
                         "ou passe --faixas CAMINHO." % caminho)
    # Sem .pyc: importar nao deve deixar __pycache__ dentro da pasta da Aula 13.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("faixas_aula13", str(caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ampliar(bgr, escala):
    """Amplia por vizinho mais proximo: nao inventa cor nova entre pixels."""
    if escala == 1:
        return bgr
    return cv2.resize(bgr, None, fx=escala, fy=escala, interpolation=cv2.INTER_NEAREST)


def medir(F, pasta):
    """Devolve uma lista de linhas: (arquivo, resultado_padrao, resultado_ajustado)."""
    cfg_p = F.cfg_padrao()
    cfg_a = F.cfg_padrao(**AJUSTES)
    linhas = []
    for caminho in sorted(pathlib.Path(pasta).glob("quadro*.png")):
        bgr = cv2.imread(str(caminho))
        if bgr is None:
            continue
        rp = F.detectar_faixas(bgr, cfg_p)
        ra = F.detectar_faixas(ampliar(bgr, ESCALA), cfg_a)
        linhas.append((caminho.name, rp, ra))
    return linhas


def _resumo(r):
    d = r["diag"]
    return "%3d seg  %s %s" % (d["n_segmentos"], "E" if r["faixa_esq"] else ".",
                               "D" if r["faixa_dir"] else ".")


def imprimir(linhas):
    """A tabela por quadro e o total. E o que vai para o relatorio do item 3."""
    print("%-14s  %-14s  %-14s" % ("quadro", "PADRAO (A13)", "AJUSTADA"))
    for nome, rp, ra in linhas:
        print("%-14s  %-14s  %-14s" % (nome, _resumo(rp), _resumo(ra)))
    n = len(linhas)
    for rot, i in (("PADRAO  ", 1), ("AJUSTADA", 2)):
        seg = [lin[i]["diag"]["n_segmentos"] for lin in linhas]
        esq = sum(1 for lin in linhas if lin[i]["faixa_esq"])
        dir_ = sum(1 for lin in linhas if lin[i]["faixa_dir"])
        ambas = sum(1 for lin in linhas if lin[i]["faixa_esq"] and lin[i]["faixa_dir"])
        print("%s: %d quadros | segmentos Hough por quadro min %d, mediana %d, max %d | "
              "esq %d, dir %d, ambas %d"
              % (rot, n, min(seg), sorted(seg)[n // 2], max(seg), esq, dir_, ambas))
    print("legenda: E = faixa esquerda achada, D = direita, '.' = nao achada")


def sobrepor(F, caminho_quadro, saida):
    """Grava a sobreposicao da AJUSTADA no tamanho AMPLIADO: reduzida de volta, o
    texto do desenhar() da Aula 13 fica ilegivel."""
    bgr = cv2.imread(str(caminho_quadro))
    cfg = F.cfg_padrao(**AJUSTES)
    grande = ampliar(bgr, ESCALA)
    res = F.detectar_faixas(grande, cfg)
    out = F.desenhar(grande, res, cfg)
    cv2.imwrite(str(saida), out)
    print("sobreposicao   : %s (de %s)" % (saida, os.path.basename(str(caminho_quadro))))


def principal(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", required=True, help="pasta com quadroNNN.png")
    p.add_argument("--faixas", default=str(AULA13_PADRAO),
                   help="caminho do faixas.py da Aula 13 (padrao: ../aula13-veicular)")
    p.add_argument("--sobreposicao", help="grava a sobreposicao da AJUSTADA neste PNG")
    p.add_argument("--quadro", type=int, default=0,
                   help="qual quadro (posicao na pasta) vai para a sobreposicao (0)")
    args = p.parse_args(argv)
    F = carregar_faixas(args.faixas)
    linhas = medir(F, args.pasta)
    if not linhas:
        print("nenhum quadroNNN.png em %s" % args.pasta)
        return 1
    imprimir(linhas)
    if args.sobreposicao:
        nomes = [lin[0] for lin in linhas]
        i = min(max(args.quadro, 0), len(nomes) - 1)
        sobrepor(F, pathlib.Path(args.pasta) / nomes[i], args.sobreposicao)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
