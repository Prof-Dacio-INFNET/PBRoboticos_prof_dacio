#!/usr/bin/env python3
"""Histograma das acoes de um dataset do coletar.py: a evidencia do dataset.

    python3 histograma.py --pasta dataset --md dataset.md --png histograma.png
    python3 histograma.py --pasta amostra/dataset

Ferramenta de APOIO: relata o que achou no acoes.csv. Nao diz se o dataset
serve, nao valida a entrega e nao substitui o enunciado -- quem decide se a
distribuicao e boa para treinar e voce, olhando o histograma e a sua pista.

O que ela olha: quantos quadros, quantos episodios, e como a coluna `direcao`
se distribui -- em especial QUANTO dela esta perto de zero. Um piloto que
mantem o carro no centro de uma estrada quase reta gera um dataset quase todo
"direcao ~ 0", e uma rede treinada nele aprende que "volante parado" e quase
sempre a resposta certa. Ela vai bem no MAE e mal na curva.

So precisa de NumPy (o do apt serve); o PNG precisa do matplotlib e, sem ele,
e pulado com aviso. Nao precisa do MetaDrive.
"""
import argparse
import csv
import pathlib
import sys

import numpy as np

# |direcao| abaixo disto conta como "volante ~ parado": 0,02 e 0,8 grau de roda.
# A curva do mapa pede uns 0,05 a 0,07 de volante -- a escala e pequena.
LIMIAR_RETA = 0.02
# faixas de 0,02 entre -0,2 e +0,2, e uma faixa para cada ponta
FAIXAS = np.concatenate([[-1.0], np.round(np.arange(-0.2, 0.2001, 0.02), 2), [1.0001]])
FAIXAS[np.abs(FAIXAS) < 1e-9] = 0.0     # sem "-0.00" na tabela


def ler(pasta):
    caminho = pathlib.Path(pasta) / 'acoes.csv'
    if not caminho.exists():
        sys.exit('nao achei %s' % caminho)
    with open(caminho, newline='') as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        sys.exit('%s esta vazio' % caminho)
    return linhas


def resumo(linhas, nome):
    d = np.array([float(x['direcao']) for x in linhas])
    eps = sorted({x['episodio'] for x in linhas}, key=lambda e: int(e))
    sementes = sorted({x['semente'] for x in linhas}, key=lambda s: int(s))
    pilotos = sorted({x.get('piloto', '?') for x in linhas})
    cont, _ = np.histogram(np.clip(d, -1.0, 1.0), bins=FAIXAS)
    perto = int(np.sum(np.abs(d) < LIMIAR_RETA))
    esq, dir_ = int(np.sum(d >= LIMIAR_RETA)), int(np.sum(d <= -LIMIAR_RETA))
    t = ['# Dataset `%s`' % nome, '',
         '> Relatorio do `histograma.py`: o que ele achou no `acoes.csv`. Nao diz se o',
         '> dataset serve, nao valida a entrega e nao substitui o enunciado.', '',
         '| | |', '|---|---|',
         '| quadros | %d |' % len(d),
         '| episodios | %d (sementes %s) |' % (len(eps), ', '.join(sementes)),
         '| piloto | %s |' % ', '.join(pilotos),
         '| direcao: media, desvio | %.3f, %.3f |' % (d.mean(), d.std()),
         '| direcao: min, max | %.3f, %.3f |' % (d.min(), d.max()),
         '| abs(direcao) < %.2f | %d quadros (%.0f%%) |' % (LIMIAR_RETA, perto,
                                                           100.0 * perto / len(d)),
         '| esquerda (>= %.2f) / direita (<= -%.2f) | %d / %d |' % (LIMIAR_RETA, LIMIAR_RETA,
                                                                    esq, dir_),
         '', 'Direcao em faixas de 0,02 (+1 = volante todo a esquerda; as pontas juntam',
         'tudo abaixo de -0,2 e acima de +0,2):', '', '```']
    maior = max(cont.max(), 1)
    for a, b, c in zip(FAIXAS[:-1], FAIXAS[1:], cont):
        t.append('[%+.2f, %+.2f) %5d %s' % (a, min(b, 1.0), c,
                                             '#' * int(round(50.0 * c / maior))))
    t.append('```')
    t.append('')
    t.append('Por episodio:')
    t.append('')
    t.append('| episodio | semente | quadros | abs(direcao) < %.2f |' % LIMIAR_RETA)
    t.append('|---|---|---|---|')
    for e in eps:
        de = np.array([float(x['direcao']) for x in linhas if x['episodio'] == e])
        s = next(x['semente'] for x in linhas if x['episodio'] == e)
        t.append('| %s | %s | %d | %.0f%% |' % (e, s, len(de),
                                                100.0 * np.mean(np.abs(de) < LIMIAR_RETA)))
    t.append('')
    t.append('O que isto NAO significa: uma tabela sem nada estranho e "o script nao achou')
    t.append('mais nada para contar", nao "dataset pronto". Se a direcao de verdade das')
    t.append('curvas esta la, so a sua pista e o comportamento do modelo dizem.')
    return '\n'.join(t), d, cont


def desenhar(d, cont, nome, caminho):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('olhe: sem matplotlib neste Python; o PNG foi pulado (o .md tem o histograma)')
        return
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=110)
    centros = np.clip((FAIXAS[:-1] + FAIXAS[1:]) / 2.0, -0.21, 0.21)
    ax.bar(centros, cont, width=0.018, color='#14213D')
    ax.axvspan(-LIMIAR_RETA, LIMIAR_RETA, color='#FCA311', alpha=0.35, zorder=0,
               label='abs(direcao) < %.2f: %.0f%%' % (LIMIAR_RETA,
                                                     100.0 * np.mean(np.abs(d) < LIMIAR_RETA)))
    ax.set_xlim(-0.23, 0.23)
    ax.set_xlabel('direcao (+1 = esquerda); as barras das pontas juntam |direcao| > 0,2')
    ax.set_ylabel('quadros')
    ax.set_title('%s -- %d quadros' % (nome, len(d)), fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis='y')
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)
    print('achei %d quadros; grafico em %s' % (len(d), caminho))


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--pasta', required=True)
    p.add_argument('--md', help='grava o relatorio em Markdown (ex.: dataset.md)')
    p.add_argument('--png', help='grava o grafico (precisa de matplotlib)')
    args = p.parse_args(argv)
    nome = pathlib.Path(args.pasta).resolve().name
    texto, d, cont = resumo(ler(args.pasta), nome)
    print(texto)
    if args.md:
        pathlib.Path(args.md).write_text(texto + '\n')
    if args.png:
        desenhar(d, cont, nome, args.png)
    return 0


if __name__ == '__main__':
    sys.exit(principal())
