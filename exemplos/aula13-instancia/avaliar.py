#!/usr/bin/env python3
"""A regua da Aula 13: mede CONTAGEM e SEPARACAO, nao "parece bom".

    python3 avaliar.py                                  # todos os detectores
    python3 avaliar.py cor_watershed                    # um so
    python3 avaliar.py --iou 0.7                        # casamento mais exigente
    python3 avaliar.py --imagem dif-instancia.png       # + a figura do quadro 0
    python3 avaliar.py --imagem dif.png --quadro 5      # outro quadro

A METRICA, declarada ANTES de olhar qualquer resultado -- que e a disciplina
da Aula 9, e continua valendo aqui:

  casamento      cada instancia prevista casa com no maximo uma instancia
                 verdadeira, pelo maior IoU, de forma gulosa, com IoU >= 0,5
                 (o --iou muda o limiar).
  erro de
  contagem (%)   soma |previstas - verdades| de cada quadro, dividida pelo
                 total de verdades. Zero quer dizer "contou certo".
  IoU medio      media do IoU dos pares CASADOS. Diz a qualidade da mascara de
                 quem foi encontrado -- nao diz nada sobre quem foi perdido,
                 e por isso ele nunca viaja sozinho.
  fusoes         uma previsao que cobre k verdades (>= 50% da area de cada uma)
                 conta k-1 fusoes. Duas pecas encostadas viradas uma previsao
                 = 1 fusao. E o modo de falha desta aula.
  divisoes       o espelho: uma verdade partida em k previsoes (cada uma com
                 >= 50% da propria area dentro dela) conta k-1 divisoes.
  acerto classe  entre os pares casados, quantos acertaram a classe.
  ms/quadro      mediana do tempo so do detector. Mediana, e nao media, porque
                 um quadro lento isolado (o sistema resolveu fazer outra coisa)
                 desloca a media e nao diz nada sobre o detector.

Por que contagem E fusao, e nao so contagem: um detector que funde duas pecas e
inventa uma mancha de ruido conta 2 e acerta a contagem -- errando tudo. O par
(contagem, fusao) nao se deixa enganar por compensacao.

Como na Aula 9, nada de desenho entra na janela cronometrada: o custo de
observar nao pode entrar na medida do que se observa.
"""
import argparse
import json
import pathlib
import statistics
import sys
import time

import cv2
import numpy as np

from instancia import CONFIG_PADRAO, DETECTORES, INSTRUCAO_MODELO, PALETA, modelo_disponivel

VERDE, VERMELHO, AMARELO, FIM = '\033[32m', '\033[31m', '\033[33m', '\033[0m'

# Cores da figura (BGR). Mesma linguagem do comparar_mapas.py da Aula 12.
COR_OK = (90, 190, 90)
COR_FUSAO = (60, 60, 220)
COR_DIVISAO = (17, 163, 252)
COR_SOBRA = (150, 150, 150)
COR_FUNDO_TITULO = (40, 40, 44)

FMT_CAB = '%-15s %8s %9s %7s %10s %9s %6s %8s %7s %9s'
FMT_LIN = '%-15s %8d %9d %7d %9.1f%% %9.2f %6d %8d %6.1f%% %9.2f'
COLUNAS = ('detector', 'verdades', 'previstas', 'casadas', 'erro cont.',
           'IoU medio', 'fusoes', 'divisoes', 'classe', 'ms/quadro')


def carregar_cena(pasta):
    """Le verdade.json. Se nao existir, diz o comando que a gera e sai."""
    pasta = pathlib.Path(pasta)
    arq = pasta / 'verdade.json'
    if not arq.is_file():
        print('nao achei a verdade da cena em %s' % arq, file=sys.stderr)
        print('gere a cena antes -- e ela e deterministica, pode repetir:',
              file=sys.stderr)
        print('    python3 cena.py --pasta %s' % pasta, file=sys.stderr)
        return None
    meta = json.loads(arq.read_text(encoding='utf-8'))
    meta['pasta'] = pasta
    return meta


def ler_quadro(cena, k):
    """Devolve (bgr, rotulos, instancias) do quadro k."""
    quadro = cena['lista'][k]
    pasta = pathlib.Path(cena['pasta'])
    bgr = cv2.imread(str(pasta / quadro['imagem']), cv2.IMREAD_COLOR)
    rot = cv2.imread(str(pasta / quadro['rotulos']), cv2.IMREAD_UNCHANGED)
    if bgr is None or rot is None:
        raise SystemExit('quadro %d incompleto em %s -- rode python3 cena.py de novo'
                         % (k, pasta))
    if rot.ndim != 2:
        rot = rot[:, :, 0]
    return bgr, rot, quadro['instancias']


def analisar(previstas, rotulos, instancias, limiar):
    """Casa previsao com verdade e classifica cada erro. E o coracao da regua.

    O IoU sai de um bincount: para cada previsao, contar os rotulos que caem
    dentro da mascara da de uma vez a intersecao com TODAS as verdades. Nao ha
    poligono, nao ha RLE, nao ha conversao onde esconder um erro.
    """
    ids = [int(i['id']) for i in instancias]
    nmax = int(rotulos.max()) if rotulos.size else 0
    conta_v = np.bincount(rotulos.ravel(), minlength=nmax + 1)
    area_v = {i: float(conta_v[i]) if i < len(conta_v) else 0.0 for i in ids}
    classe_v = {int(i['id']): i['classe'] for i in instancias}

    area_p, inter = [], {}
    for p, inst in enumerate(previstas):
        m = inst['mascara'] > 0
        area_p.append(float(np.count_nonzero(m)))
        conta = np.bincount(rotulos[m].ravel(), minlength=nmax + 1)
        for i in ids:
            if i < len(conta) and conta[i] > 0:
                inter[(p, i)] = float(conta[i])

    iou = {}
    for (p, i), n in inter.items():
        uniao = area_p[p] + area_v[i] - n
        if uniao > 0:
            iou[(p, i)] = n / uniao

    # Casamento GULOSO: o melhor IoU leva, e os dois saem do sorteio. Guloso
    # nao e otimo, mas e explicavel em uma frase -- e numa regua de aula isso
    # vale mais do que meio ponto de IoU.
    casados, usados_p, usados_v = [], set(), set()
    for (p, i), v in sorted(iou.items(), key=lambda kv: (-kv[1], kv[0])):
        if v < limiar or p in usados_p or i in usados_v:
            continue
        casados.append((p, i, v))
        usados_p.add(p)
        usados_v.add(i)

    cobertas = {p: [i for i in ids
                    if area_v[i] > 0 and inter.get((p, i), 0.0) >= 0.5 * area_v[i]]
                for p in range(len(previstas))}
    partes = {i: [p for p in range(len(previstas))
                  if area_p[p] > 0 and inter.get((p, i), 0.0) >= 0.5 * area_p[p]]
              for i in ids}
    return {'ids': ids, 'area_v': area_v, 'classe_v': classe_v, 'iou': iou,
            'casados': casados, 'cobertas': cobertas, 'partes': partes,
            'fusoes': sum(max(0, len(v) - 1) for v in cobertas.values()),
            'divisoes': sum(max(0, len(v) - 1) for v in partes.values())}


def medir(nome, fn, cena, limiar, cfg):
    """Roda o detector na cena inteira e devolve o dicionario de metricas."""
    bgr0, _, _ = ler_quadro(cena, 0)
    for _ in range(3):
        fn(bgr0, cfg)             # aquece: o primeiro medido nao paga sozinho
                                  # o custo de alocar buffer e esquentar cache
    tot = {'verdades': 0, 'previstas': 0, 'desvio': 0, 'fusoes': 0, 'divisoes': 0,
           'casados': 0, 'classe_ok': 0, 'soma_iou': 0.0}
    tempos = []
    for k in range(len(cena['lista'])):
        bgr, rot, instancias = ler_quadro(cena, k)
        # ---------- JANELA CRONOMETRADA: so o detector ----------
        t0 = time.perf_counter()
        previstas = fn(bgr, cfg)
        tempos.append((time.perf_counter() - t0) * 1000.0)
        # ---------- fim da janela. Nada abaixo entra na conta. ----------
        a = analisar(previstas, rot, instancias, limiar)
        tot['verdades'] += len(instancias)
        tot['previstas'] += len(previstas)
        tot['desvio'] += abs(len(previstas) - len(instancias))
        tot['fusoes'] += a['fusoes']
        tot['divisoes'] += a['divisoes']
        for p, i, v in a['casados']:
            tot['casados'] += 1
            tot['soma_iou'] += v
            if previstas[p]['classe'] == a['classe_v'][i]:
                tot['classe_ok'] += 1
    tot['nome'] = nome
    tot['erro_contagem'] = 100.0 * tot['desvio'] / max(tot['verdades'], 1)
    tot['iou_medio'] = tot['soma_iou'] / max(tot['casados'], 1)
    tot['acerto_classe'] = 100.0 * tot['classe_ok'] / max(tot['casados'], 1)
    tot['ms'] = statistics.median(tempos)
    return tot


def _painel(bgr, pintura, titulo):
    """Um painel: a imagem bem lavada por baixo e as mascaras por cima.

    A imagem fica visivel de proposito -- o aluno precisa ver as pecas para
    entender o que a cor esta dizendo sobre elas.
    """
    cinza = cv2.cvtColor(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    base = (cinza.astype(np.float32) * 0.28 + 255.0 * 0.72).astype(np.uint8)
    camada = np.zeros_like(base)
    marcados = np.zeros(base.shape[:2], bool)
    for mascara, cor in pintura:
        m = mascara > 0
        camada[m] = cor
        marcados |= m
    saida = base.copy()
    saida[marcados] = cv2.addWeighted(base, 0.25, camada, 0.75, 0)[marcados]
    for mascara, cor in pintura:
        contornos, _ = cv2.findContours((mascara > 0).astype(np.uint8),
                                        cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(saida, contornos, -1, (30, 30, 30), 1)
    faixa = np.full((26, saida.shape[1], 3), COR_FUNDO_TITULO, np.uint8)
    cv2.putText(faixa, titulo, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                (240, 240, 240), 1, cv2.LINE_AA)
    return np.vstack([faixa, saida])


def _legenda(largura, texto_rodape):
    itens = ((COR_OK, 'instancia casada (IoU acima do limiar)'),
             (COR_FUSAO, 'FUSAO: uma previsao cobrindo duas ou mais verdades'),
             (COR_DIVISAO, 'DIVISAO: uma verdade partida em duas previsoes'),
             (COR_SOBRA, 'sem casamento (sobrou de um lado so)'))
    alto = 26 * len(itens) + 24 + 18 * len(texto_rodape)
    faixa = np.full((alto, largura, 3), 255, np.uint8)
    for i, (cor, texto) in enumerate(itens):
        y = 10 + i * 26
        cv2.rectangle(faixa, (10, y), (30, y + 16), cor, -1)
        cv2.rectangle(faixa, (10, y), (30, y + 16), (90, 90, 90), 1)
        cv2.putText(faixa, texto, (40, y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.44,
                    (40, 40, 40), 1, cv2.LINE_AA)
    for j, linha in enumerate(texto_rodape):
        cv2.putText(faixa, linha, (10, 26 * len(itens) + 16 + j * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1, cv2.LINE_AA)
    return faixa


def desenhar_comparacao(cena, k, nomes, caminho, limiar, cfg):
    """Verdade e previsao lado a lado, uma linha por detector.

    O numero diz QUANTO; a figura diz ONDE. Com legenda embutida, para a figura
    ir ao relatorio do TP3 sozinha -- a mesma regra da Aula 12.
    """
    bgr, rot, instancias = ler_quadro(cena, k)
    verdade = [((rot == int(i['id'])).astype(np.uint8) * 255,
                PALETA[(int(i['id']) - 1) % len(PALETA)]) for i in instancias]
    painel_v = _painel(bgr, verdade,
                       'verdade  -  %d instancias  (quadro %d)' % (len(instancias), k))
    linhas, rodape = [], []
    for nome in nomes:
        previstas = DETECTORES[nome](bgr, cfg)
        a = analisar(previstas, rot, instancias, limiar)
        casados_p = {p for p, _, _ in a['casados']}
        divididas = {p for i in a['ids'] for p in a['partes'][i]
                     if len(a['partes'][i]) > 1}
        pintura = []
        for p, inst in enumerate(previstas):
            if len(a['cobertas'][p]) > 1:
                cor = COR_FUSAO
            elif p in divididas:
                cor = COR_DIVISAO
            elif p in casados_p:
                cor = COR_OK
            else:
                cor = COR_SOBRA
            pintura.append((inst['mascara'], cor))
        titulo = ('%s  -  %d instancias, %d fusoes, %d divisoes'
                  % (nome, len(previstas), a['fusoes'], a['divisoes']))
        separador = np.full((painel_v.shape[0], 6, 3), 255, np.uint8)
        linhas.append(np.hstack([painel_v, separador, _painel(bgr, pintura, titulo)]))
        rodape.append('%s: %d previstas para %d verdades, %d casadas'
                      % (nome, len(previstas), len(instancias), len(a['casados'])))
    corpo = np.vstack(linhas)
    rodape.append('limiar de casamento: IoU >= %.2f' % limiar)
    cv2.imwrite(str(caminho), np.vstack([corpo, _legenda(corpo.shape[1], rodape)]))
    return caminho


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('detectores', nargs='*', default=[],
                    help='quais medir (padrao: todos)')
    ap.add_argument('--pasta', default='cena', help='pasta da cena (padrao: cena)')
    ap.add_argument('--iou', type=float, default=0.5,
                    help='limiar de casamento por instancia (padrao 0,5)')
    ap.add_argument('--imagem', metavar='ARQ.png',
                    help='desenha verdade x previsao, pintando fusao e divisao')
    ap.add_argument('--quadro', type=int, default=0, help='qual quadro desenhar')
    ap.add_argument('--area-min', type=float, default=None,
                    help='area minima da instancia, em px2')
    a = ap.parse_args()

    cena = carregar_cena(a.pasta)
    if cena is None:
        return 1

    cfg = dict(CONFIG_PADRAO)
    if a.area_min is not None:
        cfg['area_min'] = a.area_min

    alvos = a.detectores or list(DETECTORES)
    for nome in alvos:
        if nome not in DETECTORES:
            print('detector desconhecido: %s (tenho: %s)'
                  % (nome, ', '.join(DETECTORES)), file=sys.stderr)
            return 1

    print('cena        : %s  (%d quadros de %dx%d, semente %d)'
          % (a.pasta, cena['quadros'], cena['largura'], cena['altura'],
             cena['semente']))
    print('verdade     : %d instancias rotuladas pixel a pixel'
          % sum(len(q['instancias']) for q in cena['lista']))
    print('casamento   : guloso por IoU, limiar %.2f' % a.iou)
    print()
    print(FMT_CAB % COLUNAS)
    print(FMT_CAB % tuple('-' * len(c) for c in COLUNAS))

    medidas, pulados = [], []
    for nome in alvos:
        if nome == 'modelo':
            ok, motivo = modelo_disponivel(cfg)
            if not ok:
                pulados.append((nome, motivo))
                print('%-15s  pulado -- %s' % (nome, motivo.splitlines()[0]))
                continue
        m = medir(nome, DETECTORES[nome], cena, a.iou, cfg)
        medidas.append(m)
        print(FMT_LIN % (m['nome'], m['verdades'], m['previstas'], m['casados'],
                         m['erro_contagem'], m['iou_medio'], m['fusoes'],
                         m['divisoes'], m['acerto_classe'], m['ms']))
    print()
    print('fusao = uma previsao cobrindo k verdades conta k-1  |  divisao = o espelho')
    print('IoU medio e dos pares CASADOS -- leia a coluna `casadas` ao lado dele: '
          'ele nao')
    print('sabe nada de quem ficou de fora, e e assim que um numero alto esconde '
          'uma perda.')

    if pulados:
        print()
        for nome, _ in pulados:
            print('%s nao foi medido.' % nome)
        print('  ' + INSTRUCAO_MODELO)

    if a.imagem:
        nomes = [m['nome'] for m in medidas]
        k = max(0, min(a.quadro, len(cena['lista']) - 1))
        print()
        print('figura      : %s  (quadro %d)'
              % (desenhar_comparacao(cena, k, nomes, a.imagem, a.iou, cfg), k))

    if len(medidas) > 1:
        print()
        melhor = min(medidas, key=lambda m: (m['erro_contagem'], -m['iou_medio']))
        pior = max(medidas, key=lambda m: (m['erro_contagem'], -m['iou_medio']))
        if pior['fusoes'] > melhor['fusoes']:
            cor = VERDE if melhor['erro_contagem'] < 5.0 else AMARELO
            print('Veredito: %s%s erra %.1f%% da contagem com %d fusoes; '
                  '%s erra %.1f%% com %d%s'
                  % (cor, pior['nome'], pior['erro_contagem'], pior['fusoes'],
                     melhor['nome'], melhor['erro_contagem'], melhor['fusoes'], FIM))
            print('          A mascara era a MESMA. O que mudou foi a leitura dela.')
        else:
            print('%sVeredito: os detectores nao se separaram nesta cena -- '
                  'confira se as pecas estao se encostando%s' % (VERMELHO, FIM))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
