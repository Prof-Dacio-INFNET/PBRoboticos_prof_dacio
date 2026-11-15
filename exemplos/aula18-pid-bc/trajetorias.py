#!/usr/bin/env python3
"""Desenha o desvio lateral, passo a passo, de uma ou mais trajetorias do avaliar.py.

    python3 trajetorias.py --csv traj-pid.csv traj-bc.csv --nome PID BC --png desvio.png

Le os CSV que `avaliar.py --trajetoria ARQ` (ou `dirigir_bc.py --trajetoria`)
grava -- uma linha por passo: episodio, semente, passo, desvio_m, rumo_rad,
direcao, vel_kmh -- e desenha o desvio do centro da faixa de referencia contra
o tempo, do primeiro episodio de cada arquivo. As linhas tracejadas sao as
bordas da faixa do meio (+-1,75 m); a faixa vizinha tem o centro em +-3,5 m.
A faixa cinza e o empurrao do avaliar.py (passos 40 a 49), se houver.

So precisa de matplotlib (o do apt serve). Nao precisa do MetaDrive.
"""
import argparse
import csv
import sys

EMPURRAO = (40, 50)        # os passos do avaliar.EMPURRAO_INICIO, sem importar o avaliar
DT_S = 0.1
CORES = ('#14213D', '#FCA311', '#2a9d8f', '#e76f51')


def ler(caminho):
    with open(caminho, newline='') as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        sys.exit('%s esta vazio' % caminho)
    ep = linhas[0]['episodio']
    linhas = [x for x in linhas if x['episodio'] == ep]
    return ([int(x['passo']) * DT_S for x in linhas], [float(x['desvio_m']) for x in linhas],
            linhas[0]['semente'])


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--csv', nargs='+', required=True)
    p.add_argument('--nome', nargs='+', help='um rotulo por CSV')
    p.add_argument('--png', required=True)
    p.add_argument('--empurrao', action='store_true', help='marca a janela do empurrao')
    p.add_argument('--titulo', default='')
    args = p.parse_args(argv)
    nomes = args.nome or args.csv
    if len(nomes) != len(args.csv):
        p.error('um --nome para cada --csv')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=110)
    for y in (-1.75, 1.75):
        ax.axhline(y, color='#888888', ls='--', lw=1)
    for y in (-3.5, 3.5):
        ax.axhline(y, color='#bbbbbb', ls=':', lw=1)
    if args.empurrao:
        ax.axvspan(EMPURRAO[0] * DT_S, EMPURRAO[1] * DT_S, color='#cccccc', alpha=0.6,
                   label='empurrao')
    semente = ''
    for caminho, nome, cor in zip(args.csv, nomes, CORES):
        t, d, semente = ler(caminho)
        ax.plot(t, d, color=cor, lw=1.8, label=nome)
        print('achei %d passos em %s: desvio max %.2f m, final %.2f m'
              % (len(d), caminho, max(abs(v) for v in d), d[-1]))
    ax.set_xlabel('tempo simulado (s)')
    ax.set_ylabel('desvio do centro da faixa (m, + = esquerda)')
    ax.set_title(args.titulo or 'semente %s' % semente, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout()
    fig.savefig(args.png)
    plt.close(fig)
    print('grafico em %s' % args.png)
    return 0


if __name__ == '__main__':
    sys.exit(principal())
