#!/usr/bin/env python3
"""Desenha a figura que o item 2 do TP4 pede, a partir do CSV da sessao.

    python3 plotar_trajetoria.py                       # le sessao.csv
    python3 plotar_trajetoria.py sessao.csv --saida trajetoria.png
    python3 plotar_trajetoria.py --so-trajetoria       # so' o painel de cima

FERRAMENTA DE DESENHO: **matplotlib**, com o backend `Agg` (sem tela). Foi a
escolha porque ela esta no apt do Ubuntu 22.04 (`python3-matplotlib`), nao
precisa de servidor X e sai com eixos e legenda prontos para o relatorio. Se
`import matplotlib` falhar, a mensagem diz o comando do apt e o script sai --
nao ha desenho de reserva, de proposito: duas implementacoes de figura e'
duas coisas para manter e uma para esquecer de conferir.

O QUE A FIGURA MOSTRA, e por que sao duas trajetorias no mesmo eixo:

    O enunciado pede "grafico da trajetoria". A trajetoria de QUEM? O bag tem
    duas, e elas NAO coincidem:

      /odom       o que as rodas acham que andaram. Erra por escala e o erro
                  se ACUMULA -- a curva vai se descolando da outra.
      /amcl_pose  o que o AMCL conclui olhando o /scan contra o mapa. Nao
                  acumula: ele reamarra a estimativa ao mapa a cada varredura.

    A DISTANCIA ENTRE AS DUAS CURVAS e' a deriva que o AMCL corrigiu -- e e'
    exatamente a transformada `map -> odom` que ele publica. Plotar so' uma
    das duas joga fora a melhor informacao do bag. Os tracinhos cinza que
    costuram as curvas de tantos em tantos segundos existem para esse vao ser
    visto crescendo, e nao apenas existir.

    O painel de baixo e' o que prova o comportamento do gate G4.3: a menor
    distancia do /scan furando o limiar de 0,5 m, e o `cmd_v` indo a zero e
    ficando zero por 2 s. Sem ele, a figura mostra onde o robo andou e nao
    mostra que ele PAROU -- que e' a metade do item 2.
"""
import argparse
import csv
import math
import sys

# Backend sem tela ANTES de importar o pyplot: no WSL2 sem servidor X o
# backend padrao tenta abrir janela e estoura. `Agg` escreve arquivo e pronto.
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit('este script desenha com matplotlib, e ela nao esta instalada:\n'
             '  sudo apt install -y python3-matplotlib\n'
             'pacote do apt, nunca pip -- pip reescreve o numpy do ROS 2.')

SALA = (12.0, 8.0)        # m, so' para desenhar a caixa de referencia
LIMIAR_OBSTACULO = 0.5    # m, o limiar do enunciado, desenhado como linha
COSTURA_S = 6.0           # s entre os tracinhos que ligam as duas curvas
TETO_SCAN = 3.0           # m: o /scan e' saturado aqui so' PARA DESENHAR. A
#                           figura existe para mostrar o portao de 0,5 m; com
#                           o eixo indo ate 6 m o furo do limiar vira um risco
#                           de dois pixels. O CSV continua com o valor cheio.

# Cores escolhidas para sobreviver a impressao em preto e branco: as duas
# curvas diferem tambem em TRACO (cheio x tracejado) e em espessura, nao so'
# em cor. Relatorio impresso em laser e' o destino provavel desta figura.
COR_ODOM = '#d1620a'
COR_AMCL = '#1f4e9c'
COR_EVENTO = '#b00020'


def ler_csv(caminho):
    """Le o CSV da sessao. Numeros viram float, `estado` fica texto."""
    with open(caminho, newline='', encoding='utf-8') as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        sys.exit('o CSV %s nao tem nenhuma linha de dados' % caminho)
    faltando = [c for c in ('t', 'odom_x', 'odom_y', 'amcl_x', 'amcl_y',
                            'dist_min_scan', 'cmd_v', 'estado')
                if c not in linhas[0]]
    if faltando:
        sys.exit('o CSV %s nao tem as colunas %s -- ele foi gerado pelo '
                 'simular_sessao.py ou pelo gravar_pose.py?'
                 % (caminho, ', '.join(faltando)))
    saida = []
    for r in linhas:
        d = {'estado': r['estado']}
        for k, v in r.items():
            if k != 'estado':
                d[k] = float(v)
        saida.append(d)
    return saida


def interrupcoes(linhas):
    """Os indices em que o estado VIRA `interrompido`.

    So' a transicao conta, nao cada amostra do estado: o evento e' o instante
    em que o portao disparou, e ele dura varias amostras. Contar amostras
    daria "6 interrupcoes" onde houve 2 -- e' o mesmo erro de quem conta
    mensagem em vez de contar evento.
    """
    marcos = []
    anterior = None
    for i, r in enumerate(linhas):
        if r['estado'] == 'interrompido' and anterior != 'interrompido':
            marcos.append(i)
        anterior = r['estado']
    return marcos


def desenhar(linhas, caminho, so_trajetoria=False, titulo=None):
    """Monta a figura e grava. Devolve o caminho gravado."""
    t = [r['t'] for r in linhas]
    marcos = interrupcoes(linhas)

    if so_trajetoria:
        fig, ax = plt.subplots(figsize=(8.4, 5.8))
        eixos_tempo = []
    else:
        fig, (ax, ax2) = plt.subplots(
            2, 1, figsize=(8.4, 8.6), gridspec_kw={'height_ratios': [3, 2]})
        eixos_tempo = [ax2]

    # ---------------------------------------------------- painel da trajetoria
    ax.add_patch(plt.Rectangle((0, 0), SALA[0], SALA[1], fill=False,
                               edgecolor='#999999', linewidth=1.2, zorder=1))
    ax.plot([r['odom_x'] for r in linhas], [r['odom_y'] for r in linhas],
            color=COR_ODOM, linewidth=2.4, linestyle='--', zorder=3,
            label='/odom  (as rodas: erro de escala, acumula)')
    ax.plot([r['amcl_x'] for r in linhas], [r['amcl_y'] for r in linhas],
            color=COR_AMCL, linewidth=1.6, zorder=4,
            label='/amcl_pose  (o mapa: reamarra, nao acumula)')

    # As costuras: o vao entre as duas curvas, medido de COSTURA_S em COSTURA_S.
    passo = max(1, int(round(COSTURA_S / max(1e-9, t[1] - t[0]))))
    for r in linhas[::passo]:
        ax.plot([r['odom_x'], r['amcl_x']], [r['odom_y'], r['amcl_y']],
                color='#8a8a8a', linewidth=0.8, zorder=2)
    fim = linhas[-1]
    vao = math.hypot(fim['odom_x'] - fim['amcl_x'], fim['odom_y'] - fim['amcl_y'])
    ax.annotate('o laco nao fecha para a odometria:\nvao final de %.2f m' % vao,
                xy=((fim['odom_x'] + fim['amcl_x']) / 2.0,
                    (fim['odom_y'] + fim['amcl_y']) / 2.0),
                xytext=(-28, -62), textcoords='offset points', fontsize=9,
                color='#444444',
                arrowprops=dict(arrowstyle='->', color='#555555', linewidth=0.9))

    ax.plot([linhas[0]['amcl_x']], [linhas[0]['amcl_y']], marker='o',
            markersize=8, color='#222222', zorder=5, label='largada')
    for k, i in enumerate(marcos, start=1):
        r = linhas[i]
        ax.plot([r['amcl_x']], [r['amcl_y']], marker='X', markersize=12,
                color=COR_EVENTO, zorder=6,
                label='obstaculo < %.1f m: cancela, espera, retoma'
                      % LIMIAR_OBSTACULO if k == 1 else None)
        ax.annotate(' %d ' % k, xy=(r['amcl_x'], r['amcl_y']),
                    xytext=(9, 9), textcoords='offset points',
                    fontsize=11, color=COR_EVENTO, weight='bold')

    ax.set_xlim(-0.4, SALA[0] + 0.4)
    ax.set_ylim(-0.4, SALA[1] + 0.4)
    ax.set_aspect('equal')
    ax.set_xlabel('x no quadro map (m)')
    ax.set_ylabel('y no quadro map (m)')
    ax.set_title(titulo or 'Sessao do TP4 item 2: trajetoria e interrupcoes',
                 fontsize=12)
    ax.grid(True, color='#e4e4e4', linewidth=0.7)
    ax.legend(loc='lower left', fontsize=8.5, framealpha=0.95)

    # -------------------------------------------------------- painel do tempo
    if eixos_tempo:
        ax2 = eixos_tempo[0]
        ax2.plot(t, [min(r['dist_min_scan'], TETO_SCAN) for r in linhas],
                 color='#2a7f5f', linewidth=1.4,
                 label='menor distancia do /scan (m, saturada em %.0f m)'
                       % TETO_SCAN)
        ax2.axhline(LIMIAR_OBSTACULO, color=COR_EVENTO, linewidth=1.2,
                    linestyle=':', label='limiar do TP4: %.1f m'
                                         % LIMIAR_OBSTACULO)
        ax2.plot(t, [r['cmd_v'] for r in linhas], color='#5a4fcf',
                 linewidth=1.4, label='cmd_v do /cmd_vel (m/s)')
        # `cmd_w` esta aqui para que ninguem confunda CURVA com PARADA: nos
        # trechos de giro o cmd_v tambem e' zero. Parado e' quando os DOIS
        # sao zero -- e e' assim que a regua conta o tempo de parada.
        ax2.plot(t, [abs(r['cmd_w']) for r in linhas], color='#9a9a2f',
                 linewidth=1.1, linestyle='-.',
                 label='|cmd_w| do /cmd_vel (rad/s)')
        # As faixas sombreadas sao as esperas: e' nelas que o cmd_v fica zero.
        inicio = None
        primeira = True
        for i, r in enumerate(linhas):
            parado = r['estado'] in ('esperando',)
            if parado and inicio is None:
                inicio = r['t']
            elif not parado and inicio is not None:
                ax2.axvspan(inicio, linhas[i - 1]['t'] + (t[1] - t[0]),
                            color=COR_EVENTO, alpha=0.13,
                            label='estado = esperando' if primeira else None)
                primeira = False
                inicio = None
        ax2.set_xlabel('t (s) desde a primeira mensagem do bag')
        ax2.set_ylabel('m  /  m/s')
        ax2.set_ylim(-0.15, TETO_SCAN + 1.15)
        ax2.grid(True, color='#e4e4e4', linewidth=0.7)
        ax2.legend(loc='upper center', fontsize=8.5, ncol=2, framealpha=0.95)

    fig.tight_layout()
    fig.savefig(caminho, dpi=140)
    plt.close(fig)
    return caminho


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv', nargs='?', default='sessao.csv',
                    help='o CSV da sessao (padrao sessao.csv)')
    ap.add_argument('--saida', default='trajetoria.png', metavar='ARQ.png',
                    help='onde gravar a figura (padrao trajetoria.png)')
    ap.add_argument('--so-trajetoria', action='store_true', dest='so_trajetoria',
                    help='apenas o painel da trajetoria, sem o painel do tempo')
    ap.add_argument('--titulo', default=None, help='titulo do painel de cima')
    a = ap.parse_args()

    linhas = ler_csv(a.csv)
    saida = desenhar(linhas, a.saida, a.so_trajetoria, a.titulo)
    marcos = interrupcoes(linhas)
    print('csv     : %s  (%d amostras, %.1f s)'
          % (a.csv, len(linhas), linhas[-1]['t']))
    print('eventos : %d interrupcao(oes) marcada(s) na figura' % len(marcos))
    print('figura  : %s' % saida)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
