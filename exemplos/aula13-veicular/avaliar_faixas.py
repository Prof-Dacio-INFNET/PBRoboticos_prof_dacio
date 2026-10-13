#!/usr/bin/env python3
"""Mede o detector de faixa contra a verdade, condicao por condicao.

    python3 avaliar_faixas.py                        # a tabela
    python3 avaliar_faixas.py --imagem painel.png    # + o painel comparativo
    python3 avaliar_faixas.py --canny 15 45          # mexe na etapa 2 e ve o preco
    python3 avaliar_faixas.py --sem-roi              # idem, sem regiao de interesse

AS METRICAS, declaradas antes de rodar qualquer coisa:

    achou as duas   % dos quadros em que AS DUAS faixas foram devolvidas. Uma
                    faixa so nao serve para nada: sem as duas nao ha corredor,
                    e e o corredor que o controle consome.
    erro angular    media de |angulo detectado - angulo verdadeiro|, em graus,
                    sobre as faixas que foram achadas. So sobre as achadas, de
                    proposito: quem nao acha nao tem erro angular, tem ausencia,
                    e as duas coisas nao se somam na mesma coluna.
    erro na base    media de |x_base detectado - x_base verdadeiro|, em pixels,
                    na ULTIMA linha da imagem -- onde o carro esta agora.
    ms/quadro       mediana (um quadro lento isolado nao diz nada do detector).

DIZER QUE PIOROU NAO E DIAGNOSTICO. Por isso a segunda tabela nao mede o
resultado, mede as ETAPAS: quantos pixels sobraram depois da mascara HSV (e de
que lado), quantos pixels de borda o Canny devolveu, e quantos segmentos o
Hough montou. Cada condicao deixa uma assinatura diferente nesses tres numeros,
e e a assinatura que nomeia a etapa quebrada -- nao o palpite de quem olha.

A medicao SO existe porque a cena e sintetica. Trocando a fonte por MetaDrive,
as duas primeiras colunas desta tabela deixam de poder ser calculadas. Veja o
README: a fonte e trocavel, a regua nao viaja com ela.
"""
import argparse
import json
import pathlib
import statistics
import sys
import time

import cv2
import numpy as np

from faixas import _angulo, cfg_padrao, detectar_faixas

AMBAR, VERDE, VERMELHO = (20, 170, 250), (70, 220, 70), (48, 48, 235)
CINZA_ESC = (28, 28, 32)
ORDEM = ('limpo', 'sombra', 'apagada', 'noite', 'faixa_dupla')


def _txt(img, s, org, esc=0.44, cor=(245, 245, 245), esp=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, esc, (0, 0, 0), esp + 3, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, esc, cor, esp, cv2.LINE_AA)


def mediana(valores):
    return statistics.median(valores) if valores else float('nan')


def _num(v, formato):
    """Formata, mas escreve '--' quando nao ha numero: nan na tabela e ruido."""
    return '--'.rjust(len(formato % 0.0)) if v != v else formato % v


def espurios(segmentos, item, cfg, tol=10.0):
    """(espurios, espurios_que_entraram_num_grupo).

    Espurio aqui tem definicao, nao opiniao: segmento cujo angulo esta a mais de
    `tol` graus das DUAS faixas verdadeiras. So da para contar isto porque a cena
    e sintetica -- com MetaDrive esta coluna nao existe.

    A segunda metade do par e a que importa. Um espurio recusado pelo filtro de
    inclinacao e um susto; um espurio que entrou num grupo e um erro de angulo.
    """
    alvos = (item['faixa_esq']['angulo'], item['faixa_dir']['angulo'])
    total = dentro = 0
    for x1, y1, x2, y2 in segmentos:
        ang = _angulo(x1, y1, x2, y2)
        if any(abs(ang - alvo) <= tol for alvo in alvos):
            continue
        total += 1
        if cfg['incl_min'] <= abs(ang) <= cfg['incl_max']:
            dentro += 1
    return total, dentro


def medir(raiz, condicao, quadros, cfg):
    """Roda o detector em todos os quadros de uma condicao e resume."""
    achou_ambas = achou_esq = achou_dir = 0
    erros_ang, erros_base, tempos = [], [], []
    dgs, esp, esp_grupo = [], [], []
    for item in quadros:
        caminho = raiz / item['arquivo']
        bgr = cv2.imread(str(caminho))
        if bgr is None:
            raise SystemExit('nao consegui ler %s' % caminho)

        # ------- JANELA CRONOMETRADA: so o detector -------
        t0 = time.perf_counter()
        res = detectar_faixas(bgr, cfg)
        tempos.append((time.perf_counter() - t0) * 1000.0)
        # ------- fim da janela. Nada abaixo entra na conta. -------

        dgs.append(res['diag'])
        a_esp, a_grupo = espurios(res['diag']['segmentos'], item, cfg)
        esp.append(a_esp)
        esp_grupo.append(a_grupo)
        for chave in ('faixa_esq', 'faixa_dir'):
            faixa, verdade = res[chave], item[chave]
            if faixa is None:
                continue
            if chave == 'faixa_esq':
                achou_esq += 1
            else:
                achou_dir += 1
            erros_ang.append(abs(faixa['angulo'] - verdade['angulo']))
            erros_base.append(abs(faixa['x_base'] - verdade['x_base']))
        if res['faixa_esq'] is not None and res['faixa_dir'] is not None:
            achou_ambas += 1

    n = max(len(quadros), 1)
    return {
        'condicao': condicao,
        'n': len(quadros),
        'ambas': 100.0 * achou_ambas / n,
        'esq': 100.0 * achou_esq / n,
        'dir': 100.0 * achou_dir / n,
        'erro_ang': (sum(erros_ang) / len(erros_ang)) if erros_ang else float('nan'),
        'erro_base': (sum(erros_base) / len(erros_base)) if erros_base else float('nan'),
        'ms': mediana(tempos),
        'cor': mediana([d['pixels_cor'] for d in dgs]),
        'cor_esq': mediana([d['pixels_cor_esq'] for d in dgs]),
        'cor_dir': mediana([d['pixels_cor_dir'] for d in dgs]),
        'cor_longe': mediana([d['pixels_cor_longe'] for d in dgs]),
        'borda': mediana([d['pixels_borda'] for d in dgs]),
        'segmentos': mediana([d['n_segmentos'] for d in dgs]),
        'aceitos': mediana([d['n_esq'] + d['n_dir'] for d in dgs]),
        'espurios': mediana(esp),
        'esp_grupo': mediana(esp_grupo),
    }


def diagnosticar(base, m):
    """Nomeia a ETAPA que quebrou, comparando as assinaturas com a do `limpo`.

    A ordem das perguntas e deliberada: primeiro as que matam a entrada (cor),
    depois a que mata a medida de diferenca (borda), e so no fim a que entrega
    reta errada com entrada abundante (reta). Invertida, a primeira pergunta
    responderia tudo e nao explicaria nada.
    """
    if m['condicao'] == 'limpo':
        return 'linha de base'
    if m['cor_esq'] < 0.35 * base['cor_esq'] and m['cor_dir'] > 0.70 * base['cor_dir']:
        return ('COR: a mascara do lado esquerdo sumiu (%d -> %d px) e a do direito ficou '
                'intacta. O Hough nunca viu o que ajustar daquele lado.'
                % (base['cor_esq'], m['cor_esq']))
    if m['cor'] < 0.60 * base['cor'] and m['cor_longe'] < 0.25 * base['cor_longe']:
        return ('COR LONGE: so sobrou pintura perto do carro (%d -> %d px na metade de cima '
                'da ROI). A reta sai de um apoio curto e o angulo vira ruido.'
                % (base['cor_longe'], m['cor_longe']))
    if m['borda'] < 0.30 * base['borda']:
        return ('BORDA: a mascara passou (%d px, %.0f%% do limpo) e o Canny devolveu %d px. '
                'Contraste, nao cor: a diferenca pintura-asfalto ficou abaixo do limiar.'
                % (m['cor'], 100.0 * m['cor'] / max(base['cor'], 1), m['borda']))
    if m['esp_grupo'] > base['esp_grupo'] + 0.5:
        return ('RETA: a mascara inchou (%d -> %d px) e %d segmento(s) por quadro que nao sao '
                'de faixa nenhuma entraram nos grupos. O ajuste e correto; a entrada nao e.'
                % (base['cor'], m['cor'], m['esp_grupo']))
    return ('nenhuma: a pipeline aguentou. A mascara cresceu (%d -> %d px), o Hough devolveu '
            '%d espurio(s) e o filtro de inclinacao recusou todos.'
            % (base['cor'], m['cor'], m['espurios']))


def painel(raiz, medidas, verdade, cfg, caminho):
    """Um quadro por condicao, com a verdade em ambar e a deteccao em verde.

    Legenda embutida: a figura vai para o relatorio sozinha, sem depender de
    uma frase no corpo do texto que alguem vai esquecer de escrever.
    """
    cel_l, cel_a = 320, 240
    celulas = []
    for m in medidas:
        quadros = verdade['condicoes'][m['condicao']]
        item = quadros[len(quadros) // 2]
        bgr = cv2.imread(str(raiz / item['arquivo']))
        res = detectar_faixas(bgr, cfg)
        alt, larg = bgr.shape[:2]
        y_base, y_topo = alt - 1, int(0.57 * alt)
        img = bgr.copy()
        for chave in ('faixa_esq', 'faixa_dir'):
            v = item[chave]
            a = np.tan(np.radians(v['angulo']))
            dx = (y_topo - y_base) / a if abs(a) > 1e-6 else 0.0
            cv2.line(img, (int(v['x_base']), y_base), (int(v['x_base'] + dx), y_topo),
                     AMBAR, 4, cv2.LINE_AA)
            f = res[chave]
            if f is not None:
                cv2.line(img, (int(f['x_base']), y_base), (int(f['x_topo']), y_topo),
                         VERDE, 2, cv2.LINE_AA)
        cel = cv2.resize(img, (cel_l, cel_a), interpolation=cv2.INTER_AREA)
        cv2.rectangle(cel, (0, 0), (cel_l - 1, 52), CINZA_ESC, -1)
        _txt(cel, m['condicao'], (8, 20), 0.56)
        achou = '%.0f%% as duas' % m['ambas']
        erro = 'erro %.1f g' % m['erro_ang'] if m['erro_ang'] == m['erro_ang'] else 'sem erro'
        _txt(cel, '%s   %s' % (achou, erro), (8, 42), 0.42,
             VERDE if m['ambas'] > 90 and (m['erro_ang'] < 2.5) else VERMELHO)
        cv2.rectangle(cel, (0, 0), (cel_l - 1, cel_a - 1), (70, 70, 74), 1)
        celulas.append(cel)

    legenda = np.full((cel_a, cel_l, 3), 250, np.uint8)
    cv2.rectangle(legenda, (0, 0), (cel_l - 1, cel_a - 1), (70, 70, 74), 1)
    _txt(legenda, 'legenda', (12, 26), 0.56, (40, 40, 40))
    linhas = (((20, 170, 250), 'ambar: a faixa de verdade'),
              ((70, 180, 70), 'verde: a faixa que o detector ajustou'),
              (None, 'so o ambar visivel = nao achou'),
              (None, 'ambar e verde separados = achou torto'),
              (None, 'cena sintetica, %d quadros por condicao' % medidas[0]['n']),
              (None, 'HSV -> Canny -> HoughLinesP, cfg unica'))
    for i, (cor, texto) in enumerate(linhas):
        y = 58 + i * 28
        if cor is not None:
            cv2.line(legenda, (14, y - 5), (46, y - 5), cor, 4, cv2.LINE_AA)
        cv2.putText(legenda, texto, (56 if cor else 14, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.40, (45, 45, 45), 1, cv2.LINE_AA)

    while len(celulas) < 6:
        celulas.append(np.full((cel_a, cel_l, 3), 250, np.uint8))
    celulas[5] = legenda
    grade = np.vstack([np.hstack(celulas[:3]), np.hstack(celulas[3:6])])
    faixa = np.full((34, grade.shape[1], 3), 250, np.uint8)
    cv2.putText(faixa, 'deteccao de faixa: a mesma pipeline em cinco condicoes',
                (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (35, 35, 35), 1, cv2.LINE_AA)
    cv2.imwrite(caminho, np.vstack([faixa, grade]))
    return caminho


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cena', default='estrada', help='pasta da cena (padrao estrada)')
    ap.add_argument('--imagem', metavar='ARQ.png', help='painel comparando as condicoes')
    ap.add_argument('--canny', nargs=2, type=int, metavar=('BAIXO', 'ALTO'),
                    help='troca os limiares do Canny e mede de novo')
    ap.add_argument('--sem-roi', action='store_true', help='desliga a regiao de interesse')
    a = ap.parse_args()

    raiz = pathlib.Path(a.cena)
    arquivo = raiz / 'verdade.json'
    if not arquivo.is_file():
        print('nao achei a cena em %s.' % raiz, file=sys.stderr)
        print('gere antes:  python3 cena_estrada.py --saida %s' % raiz, file=sys.stderr)
        return 1
    verdade = json.loads(arquivo.read_text(encoding='utf-8'))

    cfg = cfg_padrao()
    if a.canny:
        cfg['canny'] = (a.canny[0], a.canny[1])
    if a.sem_roi:
        cfg['roi'] = None

    presentes = [c for c in ORDEM if c in verdade['condicoes']]
    if not presentes:
        print('o verdade.json nao tem nenhuma condicao conhecida.', file=sys.stderr)
        return 1
    medidas = [medir(raiz, c, verdade['condicoes'][c], cfg) for c in presentes]

    print('cena        : %s  (%d condicoes x %d quadros, semente %s)'
          % (raiz, len(medidas), medidas[0]['n'], verdade.get('semente')))
    for parte in verdade.get('convencao', '').split('; '):
        print('verdade     : %s' % parte)
    print('config      : Canny %s   ROI %s   inclinacao aceita %.0f-%.0f graus'
          % (tuple(cfg['canny']), 'trapezio' if cfg['roi'] else 'DESLIGADA',
             cfg['incl_min'], cfg['incl_max']))
    print()
    print('a regua')
    print('  %-12s %13s %10s %10s %13s %13s %8s'
          % ('condicao', 'achou as duas', 'achou esq', 'achou dir',
             'erro angular', 'erro na base', 'ms'))
    for m in medidas:
        print('  %-12s %12.1f%% %9.1f%% %9.1f%% %11s %11s %8.2f'
              % (m['condicao'], m['ambas'], m['esq'], m['dir'],
                 _num(m['erro_ang'], '%.2f g'), _num(m['erro_base'], '%.2f px'), m['ms']))
    print('  o erro e medido SO sobre as faixas achadas: em `apagada` ele e o erro da faixa')
    print('  direita sozinha, e por isso parece bom. A coluna que conta ali e `achou esq`.')
    print()
    print('por etapa (mediana por quadro, dentro da regiao de interesse)')
    print('  %-12s %8s %8s %8s %9s %10s %9s %11s'
          % ('condicao', 'px cor', 'cor esq', 'cor dir', 'px borda', 'segmentos',
             'espurios', 'nos grupos'))
    for m in medidas:
        print('  %-12s %8d %8d %8d %9d %10d %9d %11d'
              % (m['condicao'], m['cor'], m['cor_esq'], m['cor_dir'], m['borda'],
                 m['segmentos'], m['espurios'], m['esp_grupo']))
    print('  espurio = segmento a mais de 10 graus das DUAS faixas verdadeiras;')
    print('  `nos grupos` = os que ainda assim passaram no filtro de inclinacao.')
    print()
    base = medidas[0]
    print('qual etapa quebrou, e como se sabe')
    for m in medidas:
        print('  %-12s %s' % (m['condicao'], diagnosticar(base, m)))
    print()
    if a.imagem:
        print('painel      : %s' % painel(raiz, medidas, verdade, cfg, a.imagem))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
