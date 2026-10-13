#!/usr/bin/env python3
"""Detector de faixa em tres etapas isolaveis: cor -> borda -> reta.

    python3 faixas.py --quadro estrada/limpo/quadro000.png
    python3 faixas.py --quadro estrada/sombra/quadro000.png --etapas saida/
    python3 faixas.py --pasta estrada/noite          # a fonte inteira, sem medir

Com --etapas, grava os quatro arquivos que o gate G3.5 pede como evidencia:

    1-cor.png     a mascara HSV (branco em branco, amarelo em amarelo)
    2-borda.png   o Canny depois da mascara e depois da regiao de interesse
    3-reta.png    os segmentos do Hough, coloridos pelo grupo que receberam
    4-final.png   a cena com as duas faixas ajustadas

AS TRES ETAPAS, e por que elas ficam separadas:

    1. COR    mascara HSV. Pintura branca e pintura amarela ocupam faixas
              DIFERENTES do espaco HSV -- branco e "pouco saturado e claro",
              amarelo e "matiz 15-38 e saturado". Quem trata so o branco perde
              a dupla central, e quem junta as duas numa faixa larga aceita
              asfalto claro. Sao duas mascaras, unidas no fim.

    2. BORDA  Canny sobre o CINZA, nao sobre a mascara. A diferenca importa: o
              contorno da mascara e sempre uma borda forte (255 contra 0), e um
              Canny ali so redesenharia a etapa 1. No cinza, o Canny mede o que
              ele sabe medir -- DIFERENCA de brilho entre a pintura e o asfalto
              -- e isso e o que a condicao `noite` destroi. A mascara entra
              depois, dilatada, como filtro; e a regiao de interesse, um
              trapezio, entra por ultimo e explicitamente.

    3. RETA   HoughLinesP. Os segmentos sao agrupados pelo SINAL da inclinacao
              (negativa a esquerda, positiva a direita, em coordenadas de
              imagem) e filtrados por uma faixa de inclinacao: quase horizontal
              e horizonte, quase vertical e a dupla central. Cada grupo recebe
              um ajuste de minimos quadrados de x = a*y + b, ponderado pelo
              comprimento de cada segmento -- segmento longo pesa mais porque
              viu mais pintura.

Cada etapa falha de um jeito diferente, e `avaliar_faixas.py` mede isso. Nao
precisa de ROS 2 nem de simulador: e cv2 e numpy do apt.
"""
import argparse
import math
import pathlib

import cv2
import numpy as np

# A regiao de interesse em FRACOES do quadro, para nao depender do tamanho:
# base larga embaixo, estreita na altura em que a pista ja esta longe.
ROI_PADRAO = ((0.05, 1.00), (0.41, 0.57), (0.59, 0.57), (0.95, 1.00))

CFG_PADRAO = {
    # etapa 1 -- cor
    'branco_s_max': 55,          # pintura branca e POUCO saturada
    'branco_v_min': 150,         # ... e clara
    'amarelo_h': (15, 38),
    'amarelo_s_min': 70,
    'amarelo_v_min': 110,
    # etapa 2 -- borda
    'desfoque': 5,               # antes do Canny, sempre: ruido vira borda falsa
    'canny': (50, 150),
    'dilatacao_mascara': 5,      # a borda da pintura cai FORA da mascara por 1-2 px
    'roi': ROI_PADRAO,           # None = sem regiao de interesse (veja o testar.py)
    # etapa 3 -- reta
    'hough': {'rho': 1, 'threshold': 22, 'minLineLength': 26, 'maxLineGap': 90},
    'incl_min': 20.0,            # abaixo disto e horizonte, nao faixa
    'incl_max': 78.0,            # acima disto e a dupla central, nao faixa
    'min_segmentos': 2,          # uma faixa de um segmento so e chute
    'guardar_etapas': False,
}

VERDE, VERMELHO, AMBAR = (70, 220, 70), (48, 48, 235), (20, 170, 250)
CIANO, MAGENTA, CINZA = (235, 205, 60), (200, 70, 215), (130, 130, 135)


def fonte_pasta(pasta):
    """Entrega quadros BGR (H, W, 3) uint8, em ordem. E o contrato com a cena.

    O detector nao sabe de onde o quadro veio, e nao pode saber: e por isso que
    trocar a cena sintetica por MetaDrive (ou por um .mp4, ou por uma webcam) e
    escrever OUTRA funcao com esta assinatura, sem tocar em detectar_faixas().
    O que NAO viaja junto na troca e a verdade -- veja o README.
    """
    for caminho in sorted(pathlib.Path(pasta).glob('*.png')):
        bgr = cv2.imread(str(caminho))
        if bgr is not None:
            yield bgr


def cfg_padrao(**mudancas):
    """Copia da configuracao padrao com as mudancas aplicadas."""
    cfg = dict(CFG_PADRAO)
    cfg['hough'] = dict(CFG_PADRAO['hough'])
    cfg.update(mudancas)
    return cfg


def mascaras_cor(bgr, cfg):
    """Etapa 1. Devolve (mascara_branco, mascara_amarelo), ja sem sal e pimenta."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    branco = cv2.inRange(hsv,
                         np.array([0, 0, cfg['branco_v_min']], np.uint8),
                         np.array([180, cfg['branco_s_max'], 255], np.uint8))
    h0, h1 = cfg['amarelo_h']
    amarelo = cv2.inRange(hsv,
                          np.array([h0, cfg['amarelo_s_min'], cfg['amarelo_v_min']], np.uint8),
                          np.array([h1, 255, 255], np.uint8))
    nucleo = np.ones((3, 3), np.uint8)
    return (cv2.morphologyEx(branco, cv2.MORPH_OPEN, nucleo),
            cv2.morphologyEx(amarelo, cv2.MORPH_OPEN, nucleo))


def mascara_roi(alt, larg, cfg):
    """O trapezio da regiao de interesse, em pixels. None quando desligada."""
    if cfg.get('roi') is None:
        return None
    pts = np.array([[int(fx * larg), int(fy * alt) - 1] for fx, fy in cfg['roi']], np.int32)
    roi = np.zeros((alt, larg), np.uint8)
    cv2.fillPoly(roi, [pts], 255)
    return roi


def _angulo(x1, y1, x2, y2):
    """Angulo do segmento em graus, normalizado para (-90, 90]."""
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if ang <= -90.0:
        ang += 180.0
    elif ang > 90.0:
        ang -= 180.0
    return ang


def agrupar(segmentos, cfg):
    """Etapa 3a. Separa os segmentos em esquerda e direita pelo SINAL da inclinacao.

    Em coordenadas de imagem (y para baixo), a faixa esquerda sobe para a
    direita e tem inclinacao NEGATIVA; a direita, positiva. O filtro de
    inclinacao e o que impede o horizonte (quase 0 grau) e a dupla central
    (quase 90 graus) de entrarem nos grupos.
    """
    esq, dir_, fora = [], [], []
    for x1, y1, x2, y2 in segmentos:
        ang = _angulo(x1, y1, x2, y2)
        item = (x1, y1, x2, y2, ang)
        if not cfg['incl_min'] <= abs(ang) <= cfg['incl_max']:
            fora.append(item)
        elif ang < 0.0:
            esq.append(item)
        else:
            dir_.append(item)
    return esq, dir_, fora


def ajustar(grupo, cfg, y_base, y_topo):
    """Etapa 3b. Ajusta x = a*y + b por minimos quadrados ponderado por comprimento.

    Ajusta x em funcao de y, e nao o contrario, de proposito: faixa de rodagem
    e quase vertical na imagem, e y = f(x) explode justamente onde a faixa e
    mais confiavel. Ponderar pelo comprimento faz segmento longo pesar mais --
    ele viu mais pintura. Tambem e o que faz uma borda de sombra LONGA vencer a
    pintura curta na condicao `sombra`: o criterio e honesto, a entrada nao e.
    """
    if len(grupo) < cfg['min_segmentos']:
        return None
    ys, xs, ws = [], [], []
    for x1, y1, x2, y2, _ in grupo:
        comp = math.hypot(x2 - x1, y2 - y1)
        ys += [float(y1), float(y2)]
        xs += [float(x1), float(x2)]
        ws += [comp, comp]
    w = np.asarray(ws)
    y = np.asarray(ys)
    x = np.asarray(xs)
    soma = w.sum()
    if soma <= 0.0:
        return None
    my, mx = (w * y).sum() / soma, (w * x).sum() / soma
    syy = (w * (y - my) ** 2).sum()
    if syy < 1e-6:                       # todos os pontos na mesma linha: sem reta
        return None
    a = (w * (y - my) * (x - mx)).sum() / syy
    b = mx - a * my
    ang = _angulo(0.0, 0.0, a, 1.0)      # direcao (a, 1): x anda `a` quando y anda 1
    return {'a': a, 'b': b, 'angulo': ang, 'x_base': a * y_base + b,
            'x_topo': a * y_topo + b, 'n_seg': len(grupo),
            'comprimento': float(sum(math.hypot(s[2] - s[0], s[3] - s[1]) for s in grupo))}


def detectar_faixas(bgr, cfg=None):
    """Devolve {'faixa_esq': ..., 'faixa_dir': ..., 'etapas': {...}}.

    Cada faixa e None (nao achada) ou um dicionario com x_base, angulo, a, b e
    quantos segmentos a sustentam. 'diag' traz os contadores por etapa -- e com
    eles que se diz QUAL etapa quebrou, em vez de so dizer que o resultado
    piorou. 'etapas' so vem preenchido quando cfg['guardar_etapas'] e verdadeiro.
    """
    cfg = cfg_padrao() if cfg is None else cfg
    alt, larg = bgr.shape[:2]
    y_base = alt - 1

    # ---------------- etapa 1: cor ----------------
    m_branco, m_amarelo = mascaras_cor(bgr, cfg)
    cor = cv2.bitwise_or(m_branco, m_amarelo)

    roi = mascara_roi(alt, larg, cfg)
    roi_eff = roi if roi is not None else np.full((alt, larg), 255, np.uint8)
    y_topo = int(min(fy for _, fy in cfg['roi']) * alt) if cfg.get('roi') else 0

    # ---------------- etapa 2: borda ----------------
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    k = cfg['desfoque']
    suave = cv2.GaussianBlur(cinza, (k, k), 0) if k else cinza
    bordas = cv2.Canny(suave, cfg['canny'][0], cfg['canny'][1])
    d = cfg['dilatacao_mascara']
    perto = cv2.dilate(cor, np.ones((d, d), np.uint8)) if d else cor
    bordas = cv2.bitwise_and(bordas, perto)
    bordas = cv2.bitwise_and(bordas, roi_eff)

    # ---------------- etapa 3: reta ----------------
    h = cfg['hough']
    achados = cv2.HoughLinesP(bordas, h['rho'], math.pi / 180.0, h['threshold'],
                              minLineLength=h['minLineLength'],
                              maxLineGap=h['maxLineGap'])
    # O OpenCV 4 devolve (N, 1, 4) e o 5 devolve (N, 4). Normalizar aqui e' uma
    # linha; nao normalizar e' um TypeError no meio da aula, que foi o que
    # aconteceu quando um pip install trocou o OpenCV do sistema por baixo.
    segmentos = []
    if achados is not None:
        for linha in np.asarray(achados).reshape(-1, 4):
            segmentos.append(tuple(int(v) for v in linha))
    esq, dir_, fora = agrupar(segmentos, cfg)
    faixa_esq = ajustar(esq, cfg, y_base, y_topo)
    faixa_dir = ajustar(dir_, cfg, y_base, y_topo)

    cor_roi = cv2.bitwise_and(cor, roi_eff)
    meio = larg // 2
    longe = int(0.78 * alt)                   # metade de cima da regiao de interesse
    res = {
        'faixa_esq': faixa_esq,
        'faixa_dir': faixa_dir,
        'diag': {
            'pixels_cor': int(np.count_nonzero(cor_roi)),
            'pixels_cor_esq': int(np.count_nonzero(cor_roi[:, :meio])),
            'pixels_cor_dir': int(np.count_nonzero(cor_roi[:, meio:])),
            'pixels_cor_longe': int(np.count_nonzero(cor_roi[:longe])),
            'pixels_amarelo': int(np.count_nonzero(cv2.bitwise_and(m_amarelo, roi_eff))),
            'pixels_borda': int(np.count_nonzero(bordas)),
            'n_segmentos': len(segmentos),
            'n_esq': len(esq),
            'n_dir': len(dir_),
            'n_fora': len(fora),
            'segmentos': segmentos,
        },
        'etapas': {},
    }
    if cfg['guardar_etapas']:
        res['etapas'] = {
            'cor': img_cor(m_branco, m_amarelo, roi),
            'borda': img_borda(bordas, roi),
            'reta': img_reta(bgr, esq, dir_, fora),
            'final': desenhar(bgr, res, cfg),
        }
    return res


def _txt(img, s, org, esc=0.46, cor=(245, 245, 245), esp=1):
    """Texto com contorno preto. So ASCII: a fonte do OpenCV nao tem acento."""
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, esc, (0, 0, 0), esp + 3, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, esc, cor, esp, cv2.LINE_AA)


def _contorno_roi(img, roi):
    """Desenha o trapezio da regiao de interesse por cima, em ambar."""
    if roi is None:
        return
    cnts, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnts, -1, AMBAR, 1, cv2.LINE_AA)


def img_cor(m_branco, m_amarelo, roi):
    """Etapa 1 em imagem: branco onde a mascara de branco pegou, amarelo no amarelo.

    Os dois numeros sao diferentes de proposito. O do quadro inteiro mostra o
    tamanho do vazamento; o de dentro da ROI e o que as etapas seguintes vao
    consumir, e e ele que aparece na tabela do `avaliar_faixas.py`.
    """
    out = np.zeros((*m_branco.shape, 3), np.uint8)
    out[m_branco > 0] = (255, 255, 255)
    out[m_amarelo > 0] = (40, 190, 225)
    cor = cv2.bitwise_or(m_branco, m_amarelo)
    dentro = cor if roi is None else cv2.bitwise_and(cor, roi)
    _contorno_roi(out, roi)
    _txt(out, '1. cor: mascara HSV (branco + amarelo)', (10, 24), 0.52)
    _txt(out, 'quadro inteiro %d px   dentro da ROI %d px   amarelo %d px'
         % (int(np.count_nonzero(cor)), int(np.count_nonzero(dentro)),
            int(np.count_nonzero(m_amarelo))), (10, 46), 0.42, AMBAR)
    return out


def img_borda(bordas, roi):
    """Etapa 2 em imagem, com o trapezio da regiao de interesse desenhado."""
    out = cv2.cvtColor(bordas, cv2.COLOR_GRAY2BGR)
    _contorno_roi(out, roi)
    _txt(out, '2. borda: Canny no cinza, filtrado pela mascara e pela ROI', (10, 24), 0.52)
    _txt(out, 'px de borda %d   (ambar: a regiao de interesse)'
         % int(np.count_nonzero(bordas)), (10, 46), 0.44, AMBAR)
    return out


def img_reta(bgr, esq, dir_, fora):
    """Etapa 3 em imagem: cada segmento na cor do grupo que o recebeu."""
    out = (bgr * 0.35).astype(np.uint8)
    for grupo, cor in ((fora, CINZA), (esq, CIANO), (dir_, MAGENTA)):
        for x1, y1, x2, y2, _ in grupo:
            cv2.line(out, (x1, y1), (x2, y2), cor, 2, cv2.LINE_AA)
    _txt(out, '3. reta: segmentos do Hough, agrupados por inclinacao', (10, 24), 0.52)
    _txt(out, 'ciano esq %d   magenta dir %d   cinza recusados %d'
         % (len(esq), len(dir_), len(fora)), (10, 46), 0.44, (190, 190, 195))
    return out


def desenhar(bgr, res, cfg=None):
    """A cena com as faixas ajustadas e a area entre elas. E o 4-final.png."""
    cfg = cfg_padrao() if cfg is None else cfg
    out = bgr.copy()
    alt, larg = out.shape[:2]
    y_base = alt - 1
    y_topo = int(min(fy for _, fy in cfg['roi']) * alt) if cfg.get('roi') else int(0.57 * alt)
    e, d = res['faixa_esq'], res['faixa_dir']

    if e and d:                                   # area navegavel, so com as duas
        capa = out.copy()
        quad = np.array([[int(e['x_base']), y_base], [int(e['x_topo']), y_topo],
                         [int(d['x_topo']), y_topo], [int(d['x_base']), y_base]], np.int32)
        cv2.fillPoly(capa, [quad], (90, 180, 90))
        out = cv2.addWeighted(out, 0.82, capa, 0.18, 0)

    # Os rotulos ficam nos CANTOS, nao ao lado da reta: duas faixas que se
    # aproximam no horizonte escreveriam um texto em cima do outro.
    for faixa, rotulo, x_rot in ((e, 'esq', 10), (d, 'dir', larg - 156)):
        if faixa is None:
            continue
        cv2.line(out, (int(faixa['x_base']), y_base), (int(faixa['x_topo']), y_topo),
                 VERDE, 3, cv2.LINE_AA)
        _txt(out, '%s %+.1f graus' % (rotulo, faixa['angulo']),
             (x_rot, y_topo - 10), 0.46, VERDE)

    faltando = [r for f, r in ((e, 'esquerda'), (d, 'direita')) if f is None]
    _txt(out, '4. final: faixas ajustadas', (10, 24), 0.52)
    if faltando:
        _txt(out, 'NAO ACHOU: faixa ' + ' e faixa '.join(faltando), (10, 46), 0.48, VERMELHO)
    else:
        _txt(out, 'x_base  esq %.1f   dir %.1f' % (e['x_base'], d['x_base']),
             (10, 46), 0.44, VERDE)
    return out


def percorrer(pasta, sem_roi=False):
    """Roda a pipeline sobre uma fonte inteira e resume. Sem verdade, sem erro.

    E o que sobra quando a cena nao e sua: da para dizer se o detector devolve
    faixa e com que cara, nao da para dizer se ela esta no lugar certo. E
    exatamente o que acontece ao trocar a fonte por MetaDrive.
    """
    cfg = cfg_padrao(roi=None) if sem_roi else cfg_padrao()
    n = ambas = 0
    for n, bgr in enumerate(fonte_pasta(pasta), start=1):
        res = detectar_faixas(bgr, cfg)
        e, d = res['faixa_esq'], res['faixa_dir']
        ambas += 1 if e and d else 0
        print('  quadro %3d  esq %s  dir %s  (%d segmentos)'
              % (n, '%+7.2f g' % e['angulo'] if e else '     --',
                 '%+7.2f g' % d['angulo'] if d else '     --',
                 res['diag']['n_segmentos']))
    if n == 0:
        print('nenhum PNG em %s' % pasta)
        return 1
    print('%d quadros, as duas faixas em %d (%.1f%%). Sem verdade nao ha erro a medir:'
          % (n, ambas, 100.0 * ambas / n))
    print('para medir, use uma cena com verdade e o avaliar_faixas.py.')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--quadro', help='PNG de um quadro da cena')
    g.add_argument('--pasta', metavar='DIR',
                   help='roda sobre TODOS os PNG da pasta, via fonte_pasta(). '
                        'Nao mede nada: so diz se a pipeline sobrevive a cena')
    ap.add_argument('--etapas', metavar='DIR',
                    help='grava 1-cor.png, 2-borda.png, 3-reta.png e 4-final.png')
    ap.add_argument('--sem-roi', action='store_true',
                    help='desliga a regiao de interesse (para ver o que ela cortava)')
    a = ap.parse_args()

    if a.pasta:
        if a.etapas:
            print('--etapas e por quadro: use --quadro. Rodando so a passagem pela pasta.')
        return percorrer(a.pasta, a.sem_roi)

    bgr = cv2.imread(a.quadro)
    if bgr is None:
        raise SystemExit('nao consegui ler %s\n'
                         'gere a cena antes:  python3 cena_estrada.py' % a.quadro)

    cfg = cfg_padrao(guardar_etapas=bool(a.etapas))
    if a.sem_roi:
        cfg['roi'] = None
    res = detectar_faixas(bgr, cfg)

    print('quadro      : %s' % a.quadro)
    for rotulo, faixa in (('faixa_esq', res['faixa_esq']), ('faixa_dir', res['faixa_dir'])):
        if faixa is None:
            print('%-12s: NAO ACHADA' % rotulo)
        else:
            print('%-12s: x_base %7.2f   angulo %+7.2f   %d segmento(s)'
                  % (rotulo, faixa['x_base'], faixa['angulo'], faixa['n_seg']))
    dg = res['diag']
    print('etapa 1 cor : %6d px na ROI  (esq %d / dir %d / longe %d / amarelo %d)'
          % (dg['pixels_cor'], dg['pixels_cor_esq'], dg['pixels_cor_dir'],
             dg['pixels_cor_longe'], dg['pixels_amarelo']))
    print('etapa 2 bord: %6d px de borda' % dg['pixels_borda'])
    print('etapa 3 reta: %3d segmentos -> %d esq + %d dir, %d recusados por inclinacao'
          % (dg['n_segmentos'], dg['n_esq'], dg['n_dir'], dg['n_fora']))

    if a.etapas:
        destino = pathlib.Path(a.etapas)
        destino.mkdir(parents=True, exist_ok=True)
        for nome, img in (('1-cor', res['etapas']['cor']), ('2-borda', res['etapas']['borda']),
                          ('3-reta', res['etapas']['reta']), ('4-final', res['etapas']['final'])):
            cv2.imwrite(str(destino / (nome + '.png')), img)
            print('evidencia   : %s' % (destino / (nome + '.png')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
