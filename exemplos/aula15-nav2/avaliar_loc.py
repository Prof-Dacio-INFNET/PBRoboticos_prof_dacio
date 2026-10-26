#!/usr/bin/env python3
"""A regua da convergencia do AMCL: tempo, erro, dispersao -- e lugar certo ou errado.

    python3 avaliar_loc.py
    python3 avaliar_loc.py --particulas 2000 --feixes 60
    python3 avaliar_loc.py --imagem nuvem.png

O gate G4.0 do TP4 pede "Nav2 sobe com o mapa do TP3 e localiza (AMCL
convergindo)", provado com um print do RViz2 em que a nuvem de particulas
esta concentrada. O problema e' que "esta concentrada" se avalia por
impressao, e esta disciplina passou o semestre trocando impressao por numero.

Entao: quatro numeros por cenario, e o quarto e' o que importa.

  tempo ate convergir  o primeiro instante a partir do qual a nuvem fica
                       concentrada e ASSIM PERMANECE por PASSOS_ESTAVEIS
                       atualizacoes seguidas do filtro. Um instante isolado de
                       dispersao baixa nao e' convergencia, e' sorte.
  erro final           distancia e angulo entre a pose estimada e a pose
                       VERDADEIRA. Existe aqui porque o mundo e' sintetico; no
                       seu robo nao existe, e e' por isso que esta regua tem de
                       ser rodada offline antes de confiar no print da tela.
  dispersao final      o tamanho da nuvem: raio = hypot(desvio_x, desvio_y) e o
                       desvio-padrao circular de theta. E' o que o print do
                       RViz2 mostra -- e e' SO' isso que ele mostra.
  convergiu para       certo ou ERRADO, comparando erro final com o limiar
                       declarado. E' a coluna que o print do RViz2 nao tem.

Convergir nao e' acertar. Essa e' a tese da Aula 13 (o IoU medio mais alto
podia ser do pior detector) voltando na Aula 15 com outra roupa: a nuvem mais
concentrada pode ser a do robo mais perdido.
"""
import argparse
import math

import numpy as np

from localizacao import (LIMIAR_ACERTO, LIMIAR_DISPERSAO, LIMIAR_DISP_ANG,
                         ONDE_CENARIO, PASSOS_ESTAVEIS)
from simular_loc import (DURACAO_TOTAL, PERCURSO, POSE_ERRADA, POSE_INICIAL,
                         simular)

VERDE, VERMELHO, AMARELO, FIM = '\033[32m', '\033[31m', '\033[33m', '\033[0m'

CENARIOS = ('uniforme', 'aproximada', 'errada')
EXPLICACAO = {
    'uniforme': 'nenhum palpite: particulas em todo o mapa livre',
    'aproximada': 'o 2D Pose Estimate no lugar certo',
    'errada': 'o 2D Pose Estimate na outra sala (o erro classico)',
}

# Cores da figura, em BGR. Mesma linguagem das Aulas 11, 12 e 13.
COR_PAREDE = (61, 33, 20)        # NAVY
COR_LIVRE = (245, 245, 245)
COR_PARTICULA = (196, 126, 48)   # azul-aco: uma hipotese
COR_RUMO = (225, 185, 140)       # o rumo de cada particula, mais claro
COR_VERDADE = (40, 40, 40)       # a pose verdadeira (so existe no simulador)
COR_ESTIMATIVA = (60, 60, 220)   # a estimativa do filtro (vermelho, como a
                                 # odometria da Aula 11: e' o que o robo acha)
COR_TITULO = (40, 40, 44)

FMT_CAB = '%-11s %10s %12s %12s %10s %10s %9s %9s  %s'
FMT_LIN = '%-11s %10s %12.2f %12.1f %10.3f %10.1f %9.1f %9.1f  %s'
COLUNAS = ('cenario', 't conv (s)', 'erro pos (m)', 'erro ang (g)',
           'nuvem (m)', 'nuvem (g)', 'N ef min', 'N ef fim', 'convergiu para')


def _px(mundo, altura_img, x, y, escala):
    """Ponto do mundo -> pixel. y cresce para cima no mundo, para baixo na imagem."""
    k = escala / mundo.res
    return int(round(x * k)), int(round(altura_img - y * k))


def _base_mapa(mundo, escala):
    """O mapa como fundo. E' o MESMO mapa que o filtro conhece."""
    img = np.full((mundo.ny, mundo.nx, 3), COR_LIVRE, np.uint8)
    img[mundo.grade] = COR_PAREDE
    img = np.flipud(img).copy()
    return np.repeat(np.repeat(img, escala, axis=0), escala, axis=1)


def _painel(mundo, foto, titulo, escala=2, rumos=160):
    """Um retrato da nuvem sobre o mapa, com faixa de titulo."""
    import cv2
    img = _base_mapa(mundo, escala)
    alt = img.shape[0]
    poses = foto['poses']

    # O rumo de uma amostra das particulas: sem isto, a figura mostra a
    # dispersao em x e y e esconde a de theta -- que e' metade do problema.
    passo = max(1, len(poses) // rumos)
    for x, y, th in poses[::passo]:
        a = _px(mundo, alt, x, y, escala)
        b = _px(mundo, alt, x + 0.22 * math.cos(th), y + 0.22 * math.sin(th), escala)
        cv2.line(img, a, b, COR_RUMO, 1, cv2.LINE_AA)
    for x, y, _ in poses:
        cv2.circle(img, _px(mundo, alt, x, y, escala), 1, COR_PARTICULA, -1)

    vx, vy, vth = foto['verdade']
    ex, ey, eth = foto['estimativa']
    cv2.circle(img, _px(mundo, alt, vx, vy, escala), 6, COR_VERDADE, -1)
    cv2.line(img, _px(mundo, alt, vx, vy, escala),
             _px(mundo, alt, vx + 0.5 * math.cos(vth), vy + 0.5 * math.sin(vth), escala),
             (255, 255, 255), 2, cv2.LINE_AA)
    cx, cy = _px(mundo, alt, ex, ey, escala)
    cv2.line(img, (cx - 8, cy), (cx + 8, cy), COR_ESTIMATIVA, 2, cv2.LINE_AA)
    cv2.line(img, (cx, cy - 8), (cx, cy + 8), COR_ESTIMATIVA, 2, cv2.LINE_AA)

    faixa = np.full((24, img.shape[1], 3), COR_TITULO, np.uint8)
    cv2.putText(faixa, titulo, (8, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (240, 240, 240), 1, cv2.LINE_AA)
    return np.vstack([faixa, img])


def _legenda(largura, rodape):
    import cv2
    itens = ((COR_PARTICULA, 'nuvem de particulas: um ponto = uma hipotese inteira de pose'),
             (COR_RUMO, 'o rumo de cada hipotese (a dispersao de theta, que o ponto esconde)'),
             (COR_VERDADE, 'pose VERDADEIRA -- so existe no simulador; no seu robo, nao'),
             (COR_ESTIMATIVA, 'estimativa do filtro: a media da nuvem (o que o robo acha)'))
    alto = 26 * len(itens) + 22 + 18 * len(rodape)
    faixa = np.full((alto, largura, 3), 255, np.uint8)
    for i, (cor, texto) in enumerate(itens):
        y = 10 + i * 26
        cv2.rectangle(faixa, (10, y), (30, y + 16), cor, -1)
        cv2.rectangle(faixa, (10, y), (30, y + 16), (90, 90, 90), 1)
        cv2.putText(faixa, texto, (40, y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.44,
                    (40, 40, 40), 1, cv2.LINE_AA)
    for j, linha in enumerate(rodape):
        cv2.putText(faixa, linha, (10, 26 * len(itens) + 14 + j * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1, cv2.LINE_AA)
    return faixa


def desenhar_nuvens(mundo, corridas, caminho, escala=2):
    """Painel: uma linha por cenario, tres momentos por linha, legenda embutida.

    E' a figura que vai ao relatorio do TP4 AO LADO do print do RViz2 -- e que
    diz o que o print nao diz: se a nuvem concentrou no lugar certo.
    """
    import cv2
    linhas, rodape = [], []
    for cen, (_, resumo, fotos) in corridas.items():
        celulas = []
        for k, foto in enumerate(fotos):
            quando = (('inicio', 'meio', 'fim')[k] if len(fotos) == 3
                      else '%d/%d' % (k + 1, len(fotos)))
            erro = math.hypot(foto['estimativa'][0] - foto['verdade'][0],
                              foto['estimativa'][1] - foto['verdade'][1])
            titulo = ('%s / %s  t=%.0fs  nuvem %.2f m  erro %.2f m'
                      % (cen, quando, foto['t'], foto['raio'], erro))
            celulas.append(_painel(mundo, foto, titulo, escala))
        sep = np.full((celulas[0].shape[0], 6, 3), 255, np.uint8)
        junto = [celulas[0]]
        for c in celulas[1:]:
            junto += [sep, c]
        linhas.append(np.hstack(junto))
        rodape.append('%-11s %s -- convergiu em %s, erro final %.2f m: %s'
                      % (cen, EXPLICACAO[cen],
                         ('%.1f s' % resumo['t_conv']) if resumo['t_conv'] is not None
                         else 'nunca',
                         resumo['erro_pos'], resumo['veredito']))
    corpo = np.vstack([np.vstack([ln, np.full((6, ln.shape[1], 3), 255, np.uint8)])
                       for ln in linhas])
    rodape.append('convergencia: raio da nuvem < %.2f m E desvio angular < %.1f graus, '
                  'por %d atualizacoes seguidas'
                  % (LIMIAR_DISPERSAO, LIMIAR_DISP_ANG, PASSOS_ESTAVEIS))
    rodape.append('acerto: erro de posicao final < %.2f m contra a verdade'
                  % LIMIAR_ACERTO)
    cv2.imwrite(str(caminho), np.vstack([corpo, _legenda(corpo.shape[1], rodape)]))
    return caminho


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cenarios', nargs='*', default=[],
                    help='quais medir (padrao: os tres)')
    ap.add_argument('--particulas', type=int, default=1200)
    ap.add_argument('--feixes', type=int, default=30,
                    help='feixes do /scan usados por particula (padrao 30 de 180)')
    ap.add_argument('--deriva', type=float, default=3.0,
                    help='erro sistematico da odometria, em %% (padrao 3)')
    ap.add_argument('--semente', type=int, default=42)
    ap.add_argument('--segundos', type=float, default=DURACAO_TOTAL)
    ap.add_argument('--imagem', metavar='ARQ.png',
                    help='painel com a nuvem em tres momentos, por cenario')
    ap.add_argument('--momentos', type=int, default=3,
                    help='quantos retratos por cenario na figura (padrao 3: '
                         'inicio, meio, fim). Suba para ver o colapso da nuvem')
    a = ap.parse_args()

    alvos = a.cenarios or list(CENARIOS)
    for c in alvos:
        if c not in CENARIOS:
            print('cenario desconhecido: %s (tenho: %s)' % (c, ', '.join(CENARIOS)))
            return 1

    caminho_m = 0.35 * sum(s for v, _, s in PERCURSO if v > 0 and s)
    print('mapa         : %s' % ONDE_CENARIO)
    print('percurso     : fixo, %d trechos, ~%.1f m em %.1f s -- igual em toda maquina'
          % (len(PERCURSO), caminho_m, a.segundos))
    print('partida      : verdade em (%.1f, %.1f); a pose ERRADA informada e (%.1f, %.1f)'
          % (POSE_INICIAL[0], POSE_INICIAL[1], POSE_ERRADA[0], POSE_ERRADA[1]))
    print('nuvem        : %d particulas, %d feixes por particula, semente %d'
          % (a.particulas, a.feixes, a.semente))
    print('convergencia : raio da nuvem < %.2f m E desvio angular < %.1f graus,'
          % (LIMIAR_DISPERSAO, LIMIAR_DISP_ANG))
    print('               mantidos por %d atualizacoes seguidas do filtro'
          % PASSOS_ESTAVEIS)
    print('acerto       : erro de posicao final < %.2f m contra a verdade'
          % LIMIAR_ACERTO)

    mundo, corridas = None, {}
    for cen in alvos:
        mundo, registros, fotos, resumo = simular(
            particulas=a.particulas, feixes=a.feixes, inicial=cen,
            deriva_pct=a.deriva, semente=a.semente, segundos=a.segundos,
            fotos=max(2, a.momentos))
        corridas[cen] = (registros, resumo, fotos)

    qualquer = next(iter(corridas.values()))[1]
    print('odometria    : deriva de %.1f%% -- sozinha, erraria %.2f m no fim do laco'
          % (a.deriva, qualquer['erro_odom']))
    print()
    print(FMT_CAB % COLUNAS)
    print(FMT_CAB % tuple('-' * len(c) for c in COLUNAS))
    for cen in alvos:
        r = corridas[cen][1]
        print(FMT_LIN % (cen,
                         '%.1f' % r['t_conv'] if r['t_conv'] is not None else 'nunca',
                         r['erro_pos'], r['erro_ang'], r['raio_final'],
                         r['disp_ang_final'], r['n_efetivo_min'],
                         r['n_efetivo_final'], r['veredito']))
    print()
    for cen in alvos:
        r = corridas[cen][1]
        print('%-11s %-48s %d ciclos, %d reamostragens'
              % (cen, EXPLICACAO[cen], r['ciclos'], r['reamostragens']))

    if a.imagem:
        print()
        print('figura       : %s' % desenhar_nuvens(mundo, corridas, a.imagem))

    print()
    if 'errada' in corridas and 'aproximada' in corridas:
        ok = corridas['aproximada'][1]
        mal = corridas['errada'][1]
        if mal['erro_pos'] > 1.0 and mal['raio_final'] < LIMIAR_DISPERSAO:
            print('Veredito: %sas duas nuvens concentraram -- %.0f cm e %.0f cm de raio --, '
                  'e uma delas%s' % (VERMELHO, 100 * ok['raio_final'],
                                     100 * mal['raio_final'], FIM))
            print('          %sesta %.1f m fora do lugar, com %.0f graus de erro de rumo.%s'
                  % (VERMELHO, mal['erro_pos'], mal['erro_ang'], FIM))
            print('          O print do RViz2 nao distingue as duas. A coluna '
                  '`erro pos` distingue.')
            print('          "A nuvem concentrou" prova CONFIANCA, nao localizacao.')
        else:
            print('%sVeredito: os cenarios nao se separaram -- o exemplo existe para '
                  'esse contraste.%s' % (AMARELO, FIM))
            print('          Confira --semente, --particulas e a POSE_ERRADA do '
                  'simular_loc.py.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
