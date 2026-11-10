#!/usr/bin/env python3
"""Gera um conjunto SINTETICO, deterministico e rotulado para a CNN do item 4.

    python3 gerar_sintetico.py                            # 500 imagens, 3 classes iguais
    python3 gerar_sintetico.py --n 60 --saida /tmp/mini
    python3 gerar_sintetico.py --proporcao 54:0:6 --saida desequilibrado   # como a amostra

Escreve SAIDA/imgNNNN.png e SAIDA/rotulos.csv (colunas `arquivo,classe`) -- o
mesmo contrato que o rotular.py escreve para os quadros do MetaDrive. Quem le
um, le o outro: o treinar.py nao sabe de onde vieram as imagens.

POR QUE SINTETICO. O enunciado pede 500 quadros do MetaDrive, e capturar 500
quadros leva uns 23 minutos com renderizacao por software (com GPU, um a
dois minutos) -- e, com o piloto
IDM dirigindo, a classe `obstaculo` sai VAZIA (0 em 60 na amostra da semente
7). Para a aula ter numeros medidos hoje, e para a comparacao sem x com
augmentation ser feita sobre classes que EXISTEM, as imagens sao desenhadas. O
README diz isso na primeira linha, e o relatorio do aluno tem de usar os
quadros do MetaDrive, nao estes.

AS TRES CLASSES, desenhadas sobre a estrada da Aula 13 (cena_estrada.py,
importado pelo caminho -- a estetica e a mesma, a perspectiva e a mesma):

    via_livre   pista com as duas faixas; as vezes um carro na faixa VIZINHA
    obstaculo   um veiculo ou um cone NA faixa do carro, a distancia sorteada
    cruzamento  uma via transversal e a linha de parada; as faixas param nela

O carro na faixa vizinha nao e enfeite: e a mesma regra do estado.csv do
MetaDrive (so conta como obstaculo o que esta no corredor a frente). Sem ele,
"tem um retangulo escuro na imagem" separaria as classes sozinho, e a rede
aprenderia isso em vez de aprender ONDE o retangulo esta.

A faixa dupla amarela, quando aparece, fica SEMPRE a esquerda do carro, como
no Brasil e como no MetaDrive. E e ela que o flip horizontal do augmentation
leva para a direita -- a armadilha do README.

Determinismo: cada imagem vem de um gerador semeado por (semente, indice), e a
ordem das classes e embaralhada por um gerador semeado so pela semente. Mesma
semente e mesmos argumentos, mesmos PNG e mesmo CSV, byte a byte.
"""
import argparse
import csv
import importlib.util
import math
import pathlib
import sys

import cv2
import numpy as np

CLASSES = ('via_livre', 'obstaculo', 'cruzamento')
N_PADRAO = 500
SEMENTE_PADRAO = 7
TAMANHO_PADRAO = '128x96'      # LARGURA x ALTURA, a mesma razao 4:3 do MetaDrive

# Probabilidades das variacoes, declaradas aqui e nao no meio do desenho.
P_VIZINHO = 0.35               # carro na faixa vizinha (via_livre e cruzamento)
P_AMARELA = 0.5                # faixa dupla amarela a esquerda
GANHO = (0.65, 1.30)           # brilho global sorteado: dia nublado a sol forte
DIST_OBSTACULO = (0.25, 0.85)  # 0 = horizonte, 1 = para-choque; ver _y_de()

AQUI = pathlib.Path(__file__).resolve().parent
CENA = AQUI.parent / 'aula13-veicular' / 'cena_estrada.py'

VEICULOS = ((40, 40, 160), (150, 90, 30), (200, 200, 205), (30, 30, 32), (40, 120, 40))
CONE = (20, 110, 240)           # BGR: laranja


def carregar_cena(caminho=CENA):
    """Importa o cena_estrada.py da Aula 13 pelo caminho, sem copia-lo.

    Usamos as funcoes de desenho dele (geometria, _fundo, _pintar...). Elas
    tem sublinhado no nome -- sao internas daquele arquivo --, e por isso o
    testar.py confere que elas continuam existindo: se a Aula 13 mudar, o
    teste quebra aqui, e nao a aula.
    """
    if not caminho.exists():
        sys.exit(f'nao achei {caminho}: a pasta aula13-veicular tem de estar ao lado desta '
                 '(refaca o bloco de download do README)')
    spec = importlib.util.spec_from_file_location('cena_estrada', caminho)
    mod = importlib.util.module_from_spec(spec)
    # sem __pycache__ na pasta da Aula 13: importar um arquivo de outra aula
    # nao deve deixar lixo nela
    antes, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = antes
    return mod


def ler_tamanho(texto):
    """'128x96' -> (128, 96). Largura primeiro, como no cv2.resize."""
    try:
        w, h = (int(v) for v in texto.lower().split('x'))
    except ValueError:
        raise argparse.ArgumentTypeError(f'tamanho {texto!r}: use LARGURAxALTURA, ex. 128x96')
    if w < 32 or h < 32:
        raise argparse.ArgumentTypeError('tamanho minimo 32x32')
    return w, h


def ler_proporcao(texto):
    """'54:0:6' -> (54, 0, 6), na ordem de CLASSES: via_livre:obstaculo:cruzamento.

    A ordem e a do enunciado. A amostra do MetaDrive (54 via_livre, 0 obstaculo,
    6 cruzamento) e 54:0:6 -- e nao 54:6:0, que daria 6 OBSTACULOS.
    """
    try:
        partes = tuple(float(v) for v in texto.split(':'))
    except ValueError:
        partes = ()
    if len(partes) != 3 or min(partes) < 0 or sum(partes) <= 0:
        raise argparse.ArgumentTypeError(
            f'proporcao {texto!r}: tres numeros >= 0 separados por ":", na ordem '
            + ':'.join(CLASSES))
    return partes


def contar_por_classe(n, proporcao):
    """Quantas imagens de cada classe, somando exatamente n.

    Maior resto: arredondar cada parcela separadamente pode somar n - 1 ou
    n + 1, e um conjunto de 499 imagens quando se pediu 500 e o tipo de erro
    que so aparece na tabela do relatorio.
    """
    total = float(sum(proporcao))
    exatos = [n * p / total for p in proporcao]
    base = [int(math.floor(e)) for e in exatos]
    restos = sorted(range(3), key=lambda i: (-(exatos[i] - base[i]), i))
    for i in restos[:n - sum(base)]:
        base[i] += 1
    return base


def sequencia_de_classes(n, proporcao, semente):
    """A lista de n classes, embaralhada deterministicamente."""
    lista = []
    for classe, k in zip(CLASSES, contar_por_classe(n, proporcao)):
        lista += [classe] * k
    np.random.default_rng(semente).shuffle(lista)
    return lista


def _y_de(t, vy, cena):
    """Linha da imagem a uma 'distancia' t: 0 no horizonte, 1 na base."""
    return vy + t * (cena.Y_BASE - vy)


def _x_na_reta(x_base, y, vx, vy, cena):
    """x da reta (x_base, Y_BASE) -> (vx, vy) na linha y."""
    return vx + (y - vy) / (cena.Y_BASE - vy) * (x_base - vx)


def _veiculo(img, xc, y_chao, largura, cor):
    """Traseira de um veiculo: caixa, vidro, lanternas e sombra no chao."""
    w = int(round(largura))
    h = int(round(largura * 0.78))
    x0, x1 = int(round(xc - w / 2)), int(round(xc + w / 2))
    y1 = int(round(y_chao))
    y0 = y1 - h
    cv2.ellipse(img, (int(xc), y1), (w // 2 + 3, max(2, w // 9)), 0, 0, 360, (24, 24, 24), -1)
    cv2.rectangle(img, (x0, y0), (x1, y1 - max(1, h // 10)), cor, -1)
    vidro = (x0 + w // 8, y0 + h // 8, x1 - w // 8, y0 + h * 2 // 5)
    cv2.rectangle(img, vidro[:2], vidro[2:], (70, 60, 55), -1)
    lw = max(2, w // 7)
    ly = y0 + h // 2
    cv2.rectangle(img, (x0 + 2, ly), (x0 + 2 + lw, ly + max(2, h // 8)), (30, 30, 210), -1)
    cv2.rectangle(img, (x1 - 2 - lw, ly), (x1 - 2, ly + max(2, h // 8)), (30, 30, 210), -1)


def _cone(img, xc, y_chao, largura):
    """Cone de transito: triangulo laranja com uma faixa branca."""
    w = max(6.0, largura * 0.35)
    h = w * 1.6
    pts = np.array([[xc - w / 2, y_chao], [xc + w / 2, y_chao], [xc, y_chao - h]], np.int32)
    cv2.fillPoly(img, [pts], CONE, cv2.LINE_AA)
    yb = int(y_chao - h * 0.45)
    cv2.line(img, (int(xc - w * 0.28), yb), (int(xc + w * 0.28), yb), (235, 235, 235),
             max(1, int(w // 6)), cv2.LINE_AA)


def _cruzamento(img, rng, vx, vy, xe, xd, cena):
    """Via transversal e linha de parada, a uma distancia sorteada.

    A transversal e uma faixa horizontal de asfalto que atravessa a imagem
    inteira (inclusive o acostamento); a linha de parada e um traco branco
    grosso logo antes dela, so na pista do carro.
    """
    t0 = rng.uniform(0.30, 0.62)
    espessura = rng.uniform(0.10, 0.18)
    ya = _y_de(t0, vy, cena)
    yb = _y_de(t0 + espessura, vy, cena)
    cv2.rectangle(img, (0, int(ya)), (img.shape[1] - 1, int(yb)), cena.ASFALTO, -1)
    # tracejado central da transversal: ela tambem e uma estrada
    ym = int((ya + yb) / 2)
    for x in range(0, img.shape[1], 60):
        cv2.line(img, (x, ym), (x + 30, ym), cena.PINTURA, 2, cv2.LINE_AA)
    yp = yb + 6 + 18 * t0
    xl = _x_na_reta(xe, yp, vx, vy, cena)
    xr = _x_na_reta(xd, yp, vx, vy, cena)
    cv2.line(img, (int(xl), int(yp)), (int(xr), int(yp)), cena.PINTURA,
             max(4, int(22 * (t0 + espessura))), cv2.LINE_AA)


def desenhar(classe, semente, indice, cena, tamanho):
    """Uma imagem BGR de `classe`, ja no `tamanho` final."""
    rng = np.random.default_rng([semente, indice])
    vx, vy, xe, xd = cena.geometria(rng.uniform(0.0, 60.0))
    img = np.zeros((cena.A, cena.L, 3), np.uint8)
    cena._fundo(img, vx, vy, xe, xd)
    # a faixa vizinha, a direita, em TODAS as imagens: se ela so existisse quando
    # ha carro nela, o asfalto a mais viraria a pista que a rede usaria
    viz = np.array([[int(xd), cena.A], [int(vx), int(vy)],
                    [int(vx + 12), int(vy)], [int(xd + 0.9 * (xd - xe)), cena.A]], np.int32)
    cv2.fillPoly(img, [viz], cena.ASFALTO, cv2.LINE_AA)
    cena._acima_do_horizonte(img)
    cena._pintar(img, cena._poligono_faixa(xe, vx, vy, 9.0), cena.PINTURA)
    cena._pintar(img, cena._poligono_faixa(xd, vx, vy, 9.0), cena.PINTURA)
    if rng.random() < P_AMARELA:
        for d in (10.0, 24.0):
            cena._pintar(img, cena._poligono_faixa(xe + d, vx, vy, 7.0), cena.AMARELO)

    if classe == 'cruzamento':
        _cruzamento(img, rng, vx, vy, xe, xd, cena)
    if classe in ('via_livre', 'cruzamento') and rng.random() < P_VIZINHO:
        # faixa vizinha: a direita da faixa da direita, fora do corredor do carro.
        # Vem DEPOIS da transversal para nao ser apagada por ela.
        t = rng.uniform(0.25, 0.7)
        y = _y_de(t, vy, cena)
        x_dir = _x_na_reta(xd, y, vx, vy, cena)
        largura_pista = x_dir - _x_na_reta(xe, y, vx, vy, cena)
        _veiculo(img, x_dir + 0.55 * largura_pista, y, 0.42 * largura_pista,
                 VEICULOS[int(rng.integers(len(VEICULOS)))])

    if classe == 'obstaculo':
        t = rng.uniform(*DIST_OBSTACULO)
        y = _y_de(t, vy, cena)
        x_esq = _x_na_reta(xe, y, vx, vy, cena)
        x_dir = _x_na_reta(xd, y, vx, vy, cena)
        largura_pista = x_dir - x_esq
        xc = x_esq + largura_pista * rng.uniform(0.35, 0.65)
        if rng.random() < 0.75:
            _veiculo(img, xc, y, 0.42 * largura_pista,
                     VEICULOS[int(rng.integers(len(VEICULOS)))])
        else:
            for k in range(int(rng.integers(1, 4))):
                _cone(img, xc + (k - 1) * 0.18 * largura_pista, y + 4 * k, 0.42 * largura_pista)

    ganho = rng.uniform(*GANHO)
    img = np.clip(img.astype(np.float32) * ganho, 0, 255).astype(np.uint8)
    cena._ruido(img, rng, 3.0)
    # INTER_AREA: e o filtro certo para REDUZIR; o padrao (bilinear) serrilha as faixas
    return cv2.resize(img, tamanho, interpolation=cv2.INTER_AREA)


def gerar(saida, n, proporcao, semente, tamanho, cena=None):
    """Escreve os PNG e o rotulos.csv; devolve a lista (arquivo, classe)."""
    cena = cena or carregar_cena()
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    linhas = []
    for i, classe in enumerate(sequencia_de_classes(n, proporcao, semente)):
        nome = f'img{i:04d}.png'
        cv2.imwrite(str(saida / nome), desenhar(classe, semente, i, cena, tamanho))
        linhas.append((nome, classe))
    with open(saida / 'rotulos.csv', 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(('arquivo', 'classe'))
        w.writerows(linhas)
    return linhas


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--n', type=int, default=N_PADRAO, help=f'imagens (padrao {N_PADRAO})')
    ap.add_argument('--proporcao', type=ler_proporcao, default=(1.0, 1.0, 1.0),
                    help='pesos ' + ':'.join(CLASSES)
                    + ' (padrao 1:1:1; a amostra do MetaDrive e 54:0:6)')
    ap.add_argument('--saida', default='sintetico', help='pasta de saida (padrao sintetico)')
    ap.add_argument('--semente', type=int, default=SEMENTE_PADRAO,
                    help=f'semente (padrao {SEMENTE_PADRAO})')
    ap.add_argument('--tamanho', type=ler_tamanho, default=ler_tamanho(TAMANHO_PADRAO),
                    help=f'LARGURAxALTURA (padrao {TAMANHO_PADRAO})')
    a = ap.parse_args()
    if a.n < 3:
        ap.error('--n precisa ser pelo menos 3')
    linhas = gerar(a.saida, a.n, a.proporcao, a.semente, a.tamanho)
    contagem = {c: sum(1 for _, k in linhas if k == c) for c in CLASSES}
    print(f'{len(linhas)} imagens {a.tamanho[0]}x{a.tamanho[1]} em {a.saida}/ (+ rotulos.csv), '
          f'semente {a.semente}')
    print('por classe: ' + ', '.join(f'{c} {k}' for c, k in contagem.items()))
    print('SINTETICO: serve para a aula medir; o item 4 do TP4 pede quadros do MetaDrive.')


if __name__ == '__main__':
    main()
