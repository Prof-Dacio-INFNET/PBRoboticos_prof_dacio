#!/usr/bin/env python3
"""Gera uma cena sintetica com verdade POR INSTANCIA conhecida.

    python3 cena.py                   # -> cena/ com 12 quadros + verdade.json
    python3 cena.py --quadros 4
    python3 cena.py --semente 7
    python3 cena.py --pasta /tmp/cena-teste

Nao precisa de camera e nao precisa de ROS 2: e Python, OpenCV e NumPy do apt.

POR QUE GERAR EM VEZ DE FILMAR: para medir "quantos objetos tem aqui" voce
precisa saber a resposta certa em cada quadro -- e, mais do que isso, precisa
saber QUAIS pixels sao de qual objeto. Rotular isso a mao e caro e chato;
desenhar a cena da o rotulo perfeito de graca. E a mesma escolha da Aula 9,
agora com a verdade uma casa mais fina: instancia, nao caixa.

A verdade sai em DOIS arquivos por quadro, de proposito:

    quadroNNN.png    a imagem que o detector ve
    rotulosNNN.png   a MESMA grade, com o id inteiro da instancia em cada
                     pixel (0 = fundo)

Com o PNG de rotulos, IoU por instancia e um bincount -- sem poligono e sem
RLE. E mais simples de escrever, mais simples de conferir a olho (abra o PNG e
ele e a propria verdade) e mais honesto: nao ha etapa de conversao onde esconder
um erro. O verdade.json guarda o resumo (classe, centroide, area, bbox) e
aponta para o par de arquivos.

O QUE A CENA TEM DE PROPOSITO
-----------------------------
Parte das pecas se ENCOSTA. Peca separada todo detector conta certo; e no
encostado que "uma mancha = um objeto" quebra. E quebra sem dar erro nenhum:
devolve uma contagem plausivel, so que menor. Por isso cada quadro tem tres
pecas soltas, dois PARES colados e um TRIO colado -- 10 instancias, das quais
7 estao encostadas em alguma outra.

DETERMINISTICO: a semente tem padrao fixo e o gerador e consumido sempre na
mesma ordem, para a turma inteira ver os mesmos numeros na mesma aula.
"""
import argparse
import json
import math
import pathlib

import cv2
import numpy as np

L, A = 640, 480            # tamanho do quadro
QUADROS = 12
SEMENTE = 13
R = 26                     # raio da peca redonda
RET = (54, 44)             # lados da peca retangular
COLADO = 1.88              # distancia entre centros, em raios. < 2 => encostam
PAR_RET = (42, 30)         # deslocamento do par de retangulos, nos eixos da peca
RUIDO = 4.0                # desvio do ruido gaussiano, em niveis de cinza
FUNDO = 232                # fundo claro: saturacao baixa, fora de toda faixa HSV

# Cores em BGR (e OpenCV). Sao as tres classes do dominio deste exemplo.
CLASSES = {
    'vermelho': (40, 40, 210),
    'azul': (200, 110, 40),
    'verde': (60, 180, 70),
}

# Receita fixa de cada quadro: tipo do grupo, classe e forma.
GRUPOS = (
    ('solta', 'vermelho', 'circulo'),
    ('par', 'azul', 'circulo'),
    ('solta', 'verde', 'retangulo'),
    ('trio', 'vermelho', 'circulo'),
    ('par', 'verde', 'retangulo'),
    ('solta', 'azul', 'retangulo'),
)
# Uma celula por grupo. Longe o bastante para que grupos VIZINHOS nunca se
# toquem: quem se encosta, se encosta porque foi desenhado para isso.
CELULAS = ((106, 120), (320, 120), (533, 120), (106, 360), (320, 360), (533, 360))


def _peca(classe, forma, centro, angulo=0.0):
    if forma == 'circulo':
        return {'classe': classe, 'forma': 'circulo', 'centro': centro, 'raio': R}
    return {'classe': classe, 'forma': 'retangulo', 'centro': centro,
            'tamanho': RET, 'angulo': angulo}


def _grupo(tipo, classe, forma, centro, angulo):
    """Monta as pecas de um grupo. 'par' e 'trio' saem ENCOSTADOS de proposito.

    A distancia entre centros e COLADO * R, menor que 2 * R: as pecas se
    sobrepoem alguns pixels e viram UMA componente conexa. O gargalo que sobra
    tem uns 25 px -- grosso o bastante para sobreviver a abertura morfologica,
    fino o bastante para a transformada de distancia enxergar dois nucleos.
    """
    cx, cy = centro
    ux, uy = math.cos(angulo), math.sin(angulo)
    d = COLADO * R
    if tipo == 'solta':
        return [_peca(classe, forma, (cx, cy), math.degrees(angulo))]
    if tipo == 'par' and forma == 'retangulo':
        # Dois retangulos encostados pelo CANTO. Face contra face nao serviria:
        # a sobreposicao seria larga como a peca, a transformada de distancia
        # nao teria vale nenhum e nenhuma fracao de semente separaria os dois.
        # Gargalo e condicao do metodo, nao detalhe da cena -- esta no README.
        dx, dy = PAR_RET
        ex = dx / 2 * ux - dy / 2 * uy
        ey = dx / 2 * uy + dy / 2 * ux
        graus = math.degrees(angulo)
        return [_peca(classe, forma, (cx - ex, cy - ey), graus),
                _peca(classe, forma, (cx + ex, cy + ey), graus)]
    if tipo == 'par':
        return [_peca(classe, forma, (cx - d / 2 * ux, cy - d / 2 * uy)),
                _peca(classe, forma, (cx + d / 2 * ux, cy + d / 2 * uy))]
    # Trio em corrente com uma DOBRA: assim nao ha juncao tripla no meio (que
    # abriria um buraco na mascara) e as pecas das pontas nao se tocam.
    vx, vy = math.cos(angulo + 0.52), math.sin(angulo + 0.52)
    pontos = [(-d * ux, -d * uy), (0.0, 0.0), (d * vx, d * vy)]
    mx = sum(p[0] for p in pontos) / 3.0
    my = sum(p[1] for p in pontos) / 3.0
    return [_peca(classe, forma, (cx + px - mx, cy + py - my))
            for px, py in pontos]


def pecas_do_quadro(k, rng):
    """A mesma receita em todo quadro; o que muda e o angulo e um tremor pequeno.

    O angulo gira com k para a cena nao ser 12 copias da mesma imagem, e o
    tremor sai do rng -- consumido sempre na MESMA ordem, que e o que mantem a
    cena deterministica.
    """
    pecas = []
    for i, (tipo, classe, forma) in enumerate(GRUPOS):
        cx, cy = CELULAS[i]
        jx, jy = rng.uniform(-10.0, 10.0, 2)
        ang = 0.4 * i + 0.26 * k + float(rng.uniform(-0.12, 0.12))
        pecas += _grupo(tipo, classe, forma, (cx + jx, cy + jy), ang)
    return pecas


def resumo(pecas, rotulos, area_min=200):
    """Mede cada instancia no ROTULO, nao no desenho: o que vale e o visivel.

    Se uma peca foi tapada por outra, a verdade dela e o pedaco que sobrou --
    porque e tudo o que qualquer detector poderia achar. Medir contra a forma
    inteira seria cobrar o detector por pixel que nao esta na imagem.
    """
    conta = np.bincount(rotulos.ravel(), minlength=len(pecas) + 1)
    saida = []
    for i, p in enumerate(pecas, start=1):
        area = int(conta[i])
        if area < area_min:
            continue                       # peca praticamente toda tapada
        ys, xs = np.nonzero(rotulos == i)
        x, y = int(xs.min()), int(ys.min())
        saida.append({'id': i, 'classe': p['classe'],
                      'centroide': [round(float(xs.mean()), 1),
                                    round(float(ys.mean()), 1)],
                      'area': area,
                      'bbox': [x, y, int(xs.max()) - x + 1, int(ys.max()) - y + 1]})
    return saida


def desenhar_pecas(pecas, largura=L, altura=A, rng=None, ruido=RUIDO):
    """Desenha as pecas e, na MESMA ordem, a grade de rotulos.

    A ordem importa: peca desenhada depois TAPA a de antes, na imagem e no
    rotulo. Os dois ficam consistentes por construcao.

    A imagem usa antialias na borda (fica parecida com foto); o rotulo, nao --
    id inteiro nao se mistura, 3 e 4 nao viram 3,5. Sobra uma discordancia de
    ~1 px na borda, que e justamente o tipo de erro que existe em dado real.
    """
    bgr = np.full((altura, largura, 3), FUNDO, np.uint8)
    rotulos = np.zeros((altura, largura), np.uint8)
    for i, p in enumerate(pecas, start=1):
        cor = CLASSES[p['classe']]
        if p['forma'] == 'circulo':
            centro = (int(round(p['centro'][0])), int(round(p['centro'][1])))
            cv2.circle(bgr, centro, p['raio'], cor, -1, cv2.LINE_AA)
            cv2.circle(rotulos, centro, p['raio'], int(i), -1)
        else:
            caixa = cv2.boxPoints(((float(p['centro'][0]), float(p['centro'][1])),
                                   (float(p['tamanho'][0]), float(p['tamanho'][1])),
                                   float(p['angulo'])))
            caixa = np.round(caixa).astype(np.int32)
            cv2.fillConvexPoly(bgr, caixa, cor, cv2.LINE_AA)
            cv2.fillConvexPoly(rotulos, caixa, int(i))
    if ruido and rng is not None:
        bgr = np.clip(bgr.astype(np.float32) + rng.normal(0.0, ruido, bgr.shape),
                      0, 255).astype(np.uint8)
    return bgr, rotulos, resumo(pecas, rotulos)


def contar_encostadas(rotulos):
    """Quantas instancias tocam alguma outra. Dilata cada id e ve quem aparece.

    Serve para o relatorio da cena: e esse numero que separa os detectores.
    """
    ids = [i for i in np.unique(rotulos) if i]
    nucleo = np.ones((3, 3), np.uint8)
    encostadas = 0
    for i in ids:
        vizinha = cv2.dilate((rotulos == i).astype(np.uint8), nucleo)
        outros = np.unique(rotulos[(vizinha > 0) & (rotulos != i)])
        if any(o for o in outros):
            encostadas += 1
    return encostadas


def gravar_cena(pasta, quadros, semente=SEMENTE):
    """Grava quadroNNN.png, rotulosNNN.png e verdade.json. Devolve o verdade."""
    pasta = pathlib.Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    lista = []
    for k, (bgr, rotulos, instancias) in enumerate(quadros):
        nome_img, nome_rot = 'quadro%03d.png' % k, 'rotulos%03d.png' % k
        cv2.imwrite(str(pasta / nome_img), bgr)
        cv2.imwrite(str(pasta / nome_rot), rotulos)
        lista.append({'indice': k, 'imagem': nome_img, 'rotulos': nome_rot,
                      'instancias': instancias})
    meta = {'largura': int(quadros[0][0].shape[1]),
            'altura': int(quadros[0][0].shape[0]),
            'semente': int(semente), 'quadros': len(quadros),
            'classes': list(CLASSES), 'lista': lista}
    (pasta / 'verdade.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    return pasta / 'verdade.json'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quadros', type=int, default=QUADROS, help='quantos quadros')
    ap.add_argument('--semente', type=int, default=SEMENTE,
                    help='semente do gerador (padrao fixo: a aula toda ve o mesmo)')
    ap.add_argument('--pasta', default='cena', help='pasta de saida (padrao: cena)')
    a = ap.parse_args()

    rng = np.random.default_rng(a.semente)
    quadros = [desenhar_pecas(pecas_do_quadro(k, rng), rng=rng)
               for k in range(a.quadros)]
    caminho = gravar_cena(a.pasta, quadros, a.semente)

    total = sum(len(q[2]) for q in quadros)
    encostadas = sum(contar_encostadas(q[1]) for q in quadros)
    por_classe = {}
    for _, _, instancias in quadros:
        for inst in instancias:
            por_classe[inst['classe']] = por_classe.get(inst['classe'], 0) + 1

    print('%s  %d quadros de %dx%d, semente %d'
          % (a.pasta, a.quadros, L, A, a.semente))
    print('  %d instancias no total  (%s)'
          % (total, ', '.join('%s %d' % (c, n) for c, n in sorted(por_classe.items()))))
    print('  %d delas ENCOSTADAS em alguma outra -- e aqui que a componente '
          'conexa funde' % encostadas)
    print('  verdade: %s  (+ rotulosNNN.png, um id inteiro por instancia)'
          % caminho.name)
    print('\nagora meca:  python3 avaliar.py')


if __name__ == '__main__':
    main()
