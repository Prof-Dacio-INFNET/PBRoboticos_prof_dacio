#!/usr/bin/env python3
"""Curvas de acuracia e de perda das duas rodadas, no mesmo eixo.

    VENV=../.venv-cnn/bin/python
    $VENV curvas.py --pasta resultado --saida curvas.png

Le PASTA/historico_sem.json e PASTA/historico_com.json (o treinar.py os
grava) e desenha dois paineis lado a lado: acuracia e perda. Em cada painel
estao as QUATRO curvas -- treino e validacao, sem e com augmentation --,
porque e a comparacao entre elas que o enunciado pede: "curvas de acuracia e
perda com e sem augmentation".

A cor diz a rodada (azul = sem, laranja = com); o traco diz o conjunto
(tracejado = treino, cheio = validacao). Assim a figura le em duas perguntas:
"as duas cores se separam?" (o augmentation mudou algo) e "o tracejado se
afasta do cheio?" (a rede decorou o treino).

Uma nota sobre a curva de treino da rodada COM: ela e medida sobre imagens
AUMENTADAS, que sao mais dificeis que as originais. Por isso ela costuma ficar
abaixo da de treino da rodada SEM, e isso nao quer dizer que a rede aprendeu
menos. A comparacao honesta entre as rodadas e a da validacao, que e a mesma
para as duas e nunca passa pelo augmentation.

matplotlib com backend Agg: nao precisa de tela, roda no WSL2 sem WSLg.
"""
import argparse
import json
import pathlib
import sys

COR = {'sem': '#2a78d6', 'com': '#eb6834'}     # azul e laranja, nesta ordem, sempre
ROTULO = {'sem': 'sem augmentation', 'com': 'com augmentation'}


def ler(pasta, nome):
    """O historico de uma rodada, ou para com a frase que diz de onde ele vem."""
    caminho = pathlib.Path(pasta) / f'historico_{nome}.json'
    if not caminho.exists():
        sys.exit(f'nao achei {caminho}: rode antes o treinar.py --saida {pasta}')
    with open(caminho) as f:
        h = json.load(f)
    faltam = {'accuracy', 'val_accuracy', 'loss', 'val_loss'} - set(h)
    if faltam:
        sys.exit(f'{caminho}: faltam as chaves {sorted(faltam)}')
    return h


def desenhar(historicos, saida, titulo=None):
    """Grava a figura; devolve o caminho."""
    try:
        import matplotlib
    except ImportError:
        sys.exit('sem matplotlib neste Python: use o do venv (README, "O ambiente")')
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    fig, eixos = plt.subplots(1, 2, figsize=(10, 4), dpi=120)
    for ax, chave, nome_eixo in ((eixos[0], 'accuracy', 'acuracia'),
                                 (eixos[1], 'loss', 'perda (entropia cruzada)')):
        for rodada, h in historicos.items():
            ep = range(1, len(h[chave]) + 1)
            ax.plot(ep, h[chave], color=COR[rodada], linestyle='--', linewidth=1.5,
                    label=f'{ROTULO[rodada]} - treino')
            ax.plot(ep, h['val_' + chave], color=COR[rodada], linestyle='-', linewidth=2,
                    marker='o', markersize=3, label=f'{ROTULO[rodada]} - validacao')
        ax.set_xlabel('epoca')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylabel(nome_eixo)
        ax.grid(True, color='#dddddd', linewidth=0.6)
        for lado in ('top', 'right'):
            ax.spines[lado].set_visible(False)
    eixos[0].set_ylim(0.0, 1.02)
    # a perda da validacao nas primeiras epocas, com BatchNormalization, pode
    # ir a dezenas e achatar o resto da curva; o eixo para no 95o percentil
    todas = [v for h in historicos.values() for k in ('loss', 'val_loss') for v in h[k]]
    todas.sort()
    teto = todas[min(len(todas) - 1, int(0.95 * len(todas)))]
    eixos[1].set_ylim(0.0, max(0.5, teto * 1.1))
    eixos[0].legend(fontsize=8, loc='lower right', frameon=False)
    if titulo:
        fig.suptitle(titulo, fontsize=10)
    fig.tight_layout()
    fig.savefig(saida)
    plt.close(fig)
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pasta', default='resultado',
                    help='onde estao os historico_*.json (padrao resultado)')
    ap.add_argument('--saida', default='curvas.png', help='PNG de saida (padrao curvas.png)')
    ap.add_argument('--titulo', help='titulo da figura (opcional)')
    a = ap.parse_args()
    hs = {nome: ler(a.pasta, nome) for nome in ('sem', 'com')}
    desenhar(hs, a.saida, a.titulo)
    for nome, h in hs.items():
        print(f'{ROTULO[nome]:<17}: {len(h["accuracy"])} epocas, acc_val final '
              f'{h["val_accuracy"][-1]:.3f}, perda_val final {h["val_loss"][-1]:.3f}')
    print(f'figura: {a.saida}')


if __name__ == '__main__':
    main()
