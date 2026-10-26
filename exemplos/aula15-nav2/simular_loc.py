#!/usr/bin/env python3
"""Roda o filtro de particulas contra a verdade, sem ROS 2 e sem Nav2.

Pilota o robo por um percurso FIXO pelo mundo da Aula 11, alimenta o filtro
com odometria que DERIVA (o `aplicar_deriva` da Aula 11) e com o /scan tirado
da pose verdadeira, e grava, a cada varredura: tempo, erro da estimativa
contra a verdade, dispersao da nuvem e N efetivo.

    python3 simular_loc.py
    python3 simular_loc.py --inicial errada
    python3 simular_loc.py --particulas 2000 --feixes 60 --saida loc.csv

O percurso e' fixo de proposito, e nao reativo como o `piloto.py` da Aula 11:
o resultado tem de ser o MESMO em todas as maquinas, para a tabela do
`avaliar_loc.py` poder ser citada em sala. Com o piloto reativo, uma mudanca
no filtro mudaria a trajetoria, e nao daria mais para saber se o numero
mudou por causa do filtro ou por causa do caminho.

Tres pontos de partida, e o terceiro e' o que ensina:

  uniforme    nenhum palpite -- particulas em todo o mapa livre. E' a
              localizacao global, e e' o que acontece quando ninguem clica em
              2D Pose Estimate.
  aproximada  gaussiana em volta da pose verdadeira. E' o clique certo.
  errada      gaussiana em volta de uma pose LONGE da verdade -- o espelho da
              pose real, na outra sala. E' o clique errado, o erro classico do
              aluno no RViz2, e o filtro nao tem como perceber.
"""
import argparse
import csv
import math

import numpy as np

from localizacao import (ALCANCE_MAX, ALFA_PADRAO, EXPOENTE_PESO, LIMIAR_ACERTO,
                         Mcl, Mundo, Particulas, erro_de_pose,
                         instante_convergencia, raio_nuvem, veredito)

# O `localizacao` ja' achou o pacote aula11_mundo e o pos no sys.path -- veja
# `achar_cenario()` la'. Por isso este import funciona sem PYTHONPATH nenhum.
from aula11_mundo.nucleo import aplicar_deriva, passo_diferencial            # noqa: E402

POSE_INICIAL = (2.0, 4.0, 0.0)     # a mesma da Aula 11 e do TP3
# A pose errada e' o espelho aproximado da verdadeira: outra sala, rumo
# oposto. Escolhida assim de proposito -- o erro que enfia o robo numa parede
# o filtro desfaz em tres ciclos; o erro que coloca o robo num lugar
# PARECIDO e' o que ele defende com conviccao ate o fim.
POSE_ERRADA = (9.8, 4.0, math.pi)

# Percurso fixo: (v em m/s, w em rad/s, segundos). Sala 1 -> porta -> sala 2,
# volta pela parede leste e retorna pela porta. ~27 m de laco fechado, que e'
# o cenario que o TP3 pede e o TP4 reusa.
PERCURSO = (
    (0.35, 0.00, 15.5),    # leste pela sala 1 e atravessa a porta
    (0.00, 0.50, 3.15),    # vira para o norte
    (0.35, 0.00, 8.0),     # norte pela sala 2
    (0.00, -0.50, 3.15),   # vira para o leste
    (0.35, 0.00, 9.5),     # leste, rente a parede norte
    (0.00, -0.50, 3.15),   # vira para o sul
    (0.35, 0.00, 15.0),    # sul, rente a parede leste
    (0.00, -0.50, 3.15),   # vira para o oeste
    (0.35, 0.00, 11.0),    # oeste pela parede sul da sala 2
    (0.00, -0.50, 3.15),   # vira para o norte
    (0.35, 0.00, 7.0),     # norte, de volta a altura da porta
    (0.00, 0.50, 3.15),    # vira para o oeste
    (0.35, 0.00, 11.0),    # oeste, de volta pela porta ate a sala 1
)
DURACAO_TOTAL = sum(s for _, _, s in PERCURSO)

CAMPOS_CSV = ('t', 'scan', 'atualizou', 'reamostrou', 'x_verdade', 'y_verdade',
              'th_verdade', 'x_est', 'y_est', 'th_est', 'erro_pos', 'erro_ang',
              'disp_x', 'disp_y', 'disp_th', 'raio_nuvem', 'n_efetivo')


def comando(t):
    """(v, w) do percurso fixo no instante t. Depois do fim, parado."""
    for v, w, dur in PERCURSO:
        if t < dur:
            return v, w
        t -= dur
    return 0.0, 0.0


def simular(particulas=1200, feixes=30, inicial='aproximada', deriva_pct=3.0,
            semente=42, segundos=None, dt=0.1, hz_laser=5.0, feixes_scan=180,
            fotos=3, quieto=True, alfa=ALFA_PADRAO, sigma=0.35,
            update_min_d=0.20, update_min_a=0.20, ruido_laser=0.02,
            expoente=EXPOENTE_PESO, sigma_z=0.20):
    """Roda um cenario inteiro. Devolve (mundo, registros, fotos, resumo).

    `registros` e' uma linha por varredura do laser; `fotos` sao retratos da
    nuvem em instantes igualmente espacados, para a figura do `avaliar_loc.py`.
    """
    segundos = DURACAO_TOTAL if segundos is None else float(segundos)
    rng = np.random.default_rng(semente)
    mundo = Mundo()
    angulos = np.linspace(-math.pi, math.pi, feixes_scan, endpoint=False)

    if inicial == 'uniforme':
        nuvem = Particulas.espalhar_uniforme(mundo, particulas, rng)
    elif inicial == 'aproximada':
        nuvem = Particulas.espalhar_ao_redor(POSE_INICIAL, particulas, rng, sigma)
    elif inicial == 'errada':
        nuvem = Particulas.espalhar_ao_redor(POSE_ERRADA, particulas, rng, sigma)
    else:
        raise ValueError('inicial desconhecida: %s' % inicial)

    mcl = Mcl(mundo, nuvem, rng, feixes_usados=feixes, alcance_max=ALCANCE_MAX,
              alfa=alfa, update_min_d=update_min_d, update_min_a=update_min_a,
              expoente=expoente, sigma_z=sigma_z)

    verdadeira = tuple(POSE_INICIAL)
    odom = tuple(POSE_INICIAL)
    passos_por_scan = max(1, int(round((1.0 / hz_laser) / dt)))
    n_passos = int(round(segundos / dt))
    quando_fotos = set(np.linspace(0, n_passos - 1, fotos).astype(int).tolist())

    registros, retratos = [], []
    n_scan = 0
    for n in range(n_passos):
        t = n * dt

        if n in quando_fotos:
            pose_est, disp = mcl.estimativa()
            retratos.append({'t': t, 'poses': mcl.particulas.poses.copy(),
                             'pesos': mcl.particulas.pesos.copy(),
                             'verdade': verdadeira, 'estimativa': pose_est,
                             'raio': raio_nuvem(disp)})

        if n % passos_por_scan == 0:
            leituras = mundo.medir(*verdadeira, angulos, alcance_max=ALCANCE_MAX)
            if ruido_laser > 0.0:
                # Laser perfeito e' mentira, e mentira generosa: ela faz o
                # filtro parecer melhor do que sera' no robo. 2 cm e' a ordem
                # de grandeza de um LIDAR de hobby.
                finito = np.isfinite(leituras)
                leituras = leituras.copy()
                leituras[finito] += rng.normal(0.0, ruido_laser, int(finito.sum()))
            mcl.atualizar(odom, angulos, leituras)
            pose_est, disp = mcl.estimativa()
            e_pos, e_ang = erro_de_pose(pose_est, verdadeira)
            registros.append({
                't': t, 'scan': n_scan, 'atualizou': mcl.atualizou,
                'reamostrou': mcl.reamostrou,
                'x_verdade': verdadeira[0], 'y_verdade': verdadeira[1],
                'th_verdade': verdadeira[2], 'x_est': pose_est[0],
                'y_est': pose_est[1], 'th_est': pose_est[2],
                'erro_pos': e_pos, 'erro_ang': e_ang,
                'disp_x': disp[0], 'disp_y': disp[1], 'disp_th': disp[2],
                'raio_nuvem': raio_nuvem(disp), 'n_efetivo': mcl.n_efetivo})
            n_scan += 1
            if not quieto and mcl.atualizou and n_scan % 20 == 1:
                print('  t=%6.2fs  erro %.2f m  nuvem %.2f m  N_ef %7.1f%s'
                      % (t, e_pos, raio_nuvem(disp), mcl.n_efetivo,
                         '  reamostrou' if mcl.reamostrou else ''))

        v, w = comando(t)
        verdadeira = passo_diferencial(verdadeira, v, w, dt)
        odom = aplicar_deriva(odom, v, w, dt, deriva_pct)

    final = registros[-1]
    t_conv = instante_convergencia(registros)
    resumo = {
        'inicial': inicial, 'particulas': particulas, 'feixes': feixes,
        'deriva_pct': deriva_pct, 'semente': semente, 'segundos': segundos,
        'ruido_laser': ruido_laser, 'expoente': expoente,
        'ciclos': mcl.ciclos, 'reamostragens': sum(1 for r in registros
                                                   if r['reamostrou']),
        't_conv': t_conv, 'erro_pos': final['erro_pos'],
        'erro_ang': final['erro_ang'], 'raio_final': final['raio_nuvem'],
        'disp_ang_final': math.degrees(final['disp_th']),
        'n_efetivo_final': final['n_efetivo'],
        'n_efetivo_min': min(r['n_efetivo'] for r in registros),
        'veredito': veredito(t_conv, final['erro_pos']),
        'erro_odom': math.hypot(odom[0] - verdadeira[0], odom[1] - verdadeira[1]),
    }
    return mundo, registros, retratos, resumo


def imprimir_resumo(r):
    print('cenario       : %s  (%d particulas, %d feixes, deriva %.1f%%, semente %d)'
          % (r['inicial'], r['particulas'], r['feixes'], r['deriva_pct'],
             r['semente']))
    print('ciclos        : %d atualizacoes do filtro, %d reamostragens'
          % (r['ciclos'], r['reamostragens']))
    print('convergiu em  : %s'
          % ('%.1f s' % r['t_conv'] if r['t_conv'] is not None else 'nunca'))
    print('erro final    : %.2f m de posicao, %.1f graus de angulo'
          % (r['erro_pos'], r['erro_ang']))
    print('nuvem final   : raio %.3f m, desvio angular %.1f graus'
          % (r['raio_final'], r['disp_ang_final']))
    print('N efetivo     : %.1f no fim, minimo de %.1f'
          % (r['n_efetivo_final'], r['n_efetivo_min']))
    print('odometria so  : erraria %.2f m (e o que o filtro teve de absorver)'
          % r['erro_odom'])
    print('veredito      : %s  (acerto = erro final < %.2f m)'
          % (r['veredito'], LIMIAR_ACERTO))


def gravar_csv(caminho, registros):
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        esc = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        esc.writeheader()
        for r in registros:
            esc.writerow({k: r[k] for k in CAMPOS_CSV})
    return caminho


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--particulas', type=int, default=1200,
                    help='tamanho da nuvem (padrao 1200)')
    ap.add_argument('--feixes', type=int, default=30,
                    help='feixes do /scan usados por particula (padrao 30)')
    ap.add_argument('--inicial', default=None,
                    choices=('uniforme', 'aproximada', 'errada'),
                    help='pose inicial informada ao filtro (padrao: roda os tres)')
    ap.add_argument('--deriva', type=float, default=3.0,
                    help='erro sistematico da odometria, em %% (padrao 3)')
    ap.add_argument('--semente', type=int, default=42, help='padrao 42, fixa')
    ap.add_argument('--segundos', type=float, default=DURACAO_TOTAL,
                    help='duracao do percurso (padrao %.0f, o laco completo)'
                         % DURACAO_TOTAL)
    ap.add_argument('--saida', metavar='ARQ.csv',
                    help='grava uma linha por varredura (um arquivo por cenario)')
    ap.add_argument('--ruido-laser', type=float, default=0.02, dest='ruido_laser',
                    help='desvio-padrao do ruido do /scan, em m (padrao 0,02)')
    ap.add_argument('--falante', action='store_true', help='imprime o andamento')
    a = ap.parse_args()

    cenarios = [a.inicial] if a.inicial else ['uniforme', 'aproximada', 'errada']
    for i, cen in enumerate(cenarios):
        if i:
            print()
        _, registros, _, resumo = simular(
            particulas=a.particulas, feixes=a.feixes, inicial=cen,
            deriva_pct=a.deriva, semente=a.semente, segundos=a.segundos,
            ruido_laser=a.ruido_laser, quieto=not a.falante)
        imprimir_resumo(resumo)
        if a.saida:
            alvo = a.saida if len(cenarios) == 1 else \
                a.saida.replace('.csv', '') + '-' + cen + '.csv'
            print('csv           : %s  (%d linhas)'
                  % (gravar_csv(alvo, registros), len(registros)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
