#!/usr/bin/env python3
"""Gera quadros de estrada em perspectiva COM a verdade das duas faixas.

    python3 cena_estrada.py                       # todas as condicoes
    python3 cena_estrada.py --condicao sombra     # so uma, sem apagar as outras
    python3 cena_estrada.py --saida /tmp/estrada --semente 7

Escreve estrada/<condicao>/quadroNNN.png e estrada/verdade.json.

POR QUE SINTETICO, E NAO METADRIVE: para medir um detector de faixa voce precisa
saber ONDE a faixa esta em cada quadro. O MetaDrive entrega quadros convincentes
e nenhuma verdade utilizavel em coordenadas de imagem -- e cobra meia aula de
instalacao antes da primeira linha de percepcao. Aqui a cena e desenhada, entao
a verdade sai exata e de graca. Trocar a fonte depois e trocar UMA funcao (veja
o README); o que se perde na troca e justamente a verdade, e e por isso que a
MEDICAO fica com a cena sintetica mesmo depois de o MetaDrive entrar.

A VERDADE, por quadro e por faixa (coordenadas de imagem, y cresce para baixo):

    x_base   x onde a reta da faixa cruza a ULTIMA linha da imagem (y = 479)
    angulo   graus, atan2(dy, dx) normalizado para (-90, 90]

Escolhi estes dois porque os dois erros ficam legiveis sem conta nenhuma:
"errou 2,1 graus e 7 pixels na base do quadro" e uma frase que cabe no relatorio.
Em (rho, theta) o mesmo erro sai em unidades que ninguem julga de olho. A faixa
esquerda tem angulo NEGATIVO e a direita POSITIVO -- e esse sinal e exatamente o
que o detector usa para separar os segmentos do Hough em dois grupos.

As retas sao RETAS, nao curvas: o modelo que o Hough ajusta e uma reta, e uma
cena curva mediria o erro do modelo em vez do erro da pipeline. Curva e o
proximo passo, e o README diz onde ele entra.

AS CONDICOES, uma pasta cada, escolhidas para quebrar ETAPAS DIFERENTES:

    limpo        linha de base: pintura clara sobre asfalto escuro
    sombra       sombra diagonal e o auto-exposure abrindo por causa dela
    apagada      pintura do lado esquerdo desbotada (22% de opacidade)
    noite        contraste baixo: camera com ganho no maximo, preto levantado
    faixa_dupla  dupla amarela ao centro -- a condicao que a pipeline AGUENTA

Determinismo: o ruido vem de um gerador semeado por (semente, condicao, quadro).
Mesma semente, mesmos PNG e mesmo JSON, byte a byte.
"""
import argparse
import json
import math
import pathlib

import cv2
import numpy as np

L, A = 640, 480               # largura e altura do quadro
Y_HOR = 200                   # linha do horizonte, em pixels
Y_BASE = A - 1                # ultima linha da imagem: onde x_base e medido
N_QUADROS = 24
SEMENTE_PADRAO = 7

CONDICOES = ('limpo', 'sombra', 'apagada', 'noite', 'faixa_dupla')

# BGR. O ceu e claro e POUCO saturado de proposito: assim ele entra na mesma
# faixa HSV da pintura branca, e a regiao de interesse passa a ter trabalho.
CEU = (172, 182, 186)
ASFALTO = (58, 60, 62)
ACOSTAMENTO = (44, 54, 46)
PINTURA = (238, 240, 240)
AMARELO = (40, 190, 225)
ESTRUTURA = (62, 66, 70)

SOMBRA_GANHO = 2.70           # o auto-exposure abre porque a sombra domina
SOMBRA_FATOR = 0.38           # quanto a sombra escurece o que ela cobre
SOMBRA_ANGULO = -40.0         # graus: longe dos -54 da faixa esquerda, de proposito
APAGADA_ALFA = 0.22
NOITE_GANHO, NOITE_PRETO = 0.1477, 132.9

CONVENCAO = ('x_base: x da reta da faixa em y=479; '
             'angulo: graus de atan2(dy, dx) em (-90, 90]; '
             'faixa esquerda negativa, faixa direita positiva')


def geometria(k):
    """Ponto de fuga e x das duas faixas na base, no quadro k.

    O carro anda para os lados e a pista muda de largura: sem isso a verdade
    seria constante e um detector que devolvesse sempre o mesmo numero passaria.
    """
    desvio = 34.0 * math.sin(k / 5.0)
    largura = 206.0 + 16.0 * math.sin(k / 8.0 + 0.7)
    vx = L / 2.0 + 0.35 * desvio
    vy = Y_HOR + 2.0 * math.sin(k / 6.0)
    return vx, vy, L / 2.0 + desvio - largura, L / 2.0 + desvio + largura


def angulo_faixa(x_base, vx, vy):
    """Angulo em graus da reta (x_base, Y_BASE) -> (vx, vy), em (-90, 90]."""
    ang = math.degrees(math.atan2(vy - Y_BASE, vx - x_base))
    if ang <= -90.0:
        ang += 180.0
    elif ang > 90.0:
        ang -= 180.0
    return ang


def _poligono_faixa(x_base, vx, vy, largura_base, largura_topo=2.0):
    """Faixa pintada como poligono: estreita no horizonte, larga na base."""
    y_topo = Y_HOR + 6.0
    esquerda, direita = [], []
    for i in range(25):
        t = i / 24.0
        y = y_topo + t * (Y_BASE - y_topo)
        x = vx + (y - vy) / (Y_BASE - vy) * (x_base - vx)
        meia = (largura_topo + t * (largura_base - largura_topo)) / 2.0
        esquerda.append((x - meia, y))
        direita.append((x + meia, y))
    return np.array(esquerda + direita[::-1], np.int32)


def _pintar(img, poligono, cor, alpha=1.0):
    """Mistura `cor` dentro do poligono, com borda suavizada.

    O alpha existe por causa da condicao `apagada`: pintura desbotada nao e
    pintura ausente -- ela continua la, mais escura, e e isso que engana quem
    confia num limiar fixo de brilho.
    """
    capa = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(capa, [poligono], 255, cv2.LINE_AA)
    peso = (capa.astype(np.float32) / 255.0 * float(alpha))[:, :, None]
    alvo = np.array(cor, np.float32).reshape(1, 1, 3)
    img[:] = np.clip(img.astype(np.float32) * (1.0 - peso) + alvo * peso,
                     0, 255).astype(np.uint8)


def _fundo(img, vx, vy, xe, xd):
    """Ceu, acostamento, pista em perspectiva e a linha do horizonte."""
    img[:Y_HOR] = CEU
    img[Y_HOR:] = ACOSTAMENTO
    pista = np.array([[int(xe - 64), A], [int(vx - 10), int(vy)],
                      [int(vx + 10), int(vy)], [int(xd + 64), A]], np.int32)
    cv2.fillPoly(img, [pista], ASFALTO, cv2.LINE_AA)
    cv2.line(img, (0, Y_HOR), (L, Y_HOR), (120, 126, 128), 1, cv2.LINE_AA)


def _acima_do_horizonte(img):
    """Um telhado inclinado e um poste com estai. ACIMA do horizonte, de proposito.

    As duas estruturas sao escuras contra um ceu claro e pouco saturado: o ceu
    entra na mascara de branco, o contorno delas entra no Canny, e o Hough acha
    retas de -32 e +49 graus -- dentro da faixa de inclinacao que o detector
    aceita. Com a regiao de interesse, nada disso aparece. Sem ela, essas retas
    entram no mesmo grupo das faixas e puxam o ajuste. O `testar.py` confere.
    """
    telhado = np.array([[52, Y_HOR], [196, Y_HOR],
                        [196, Y_HOR - 96], [52, Y_HOR - 6]], np.int32)
    cv2.fillPoly(img, [telhado], ESTRUTURA, cv2.LINE_AA)
    cv2.line(img, (540, Y_HOR), (540, Y_HOR - 72), ESTRUTURA, 3, cv2.LINE_AA)
    cv2.line(img, (540, Y_HOR - 70), (596, Y_HOR - 6), ESTRUTURA, 2, cv2.LINE_AA)


def _sombra(img):
    """Sombra diagonal -- e o que ela faz com o auto-exposure da camera.

    A sombra sozinha nao engana o Canny; ela engana o CONTROLE DE EXPOSICAO.
    Com uma faixa escura ocupando um terco do quadro, o ganho sobe, a pintura
    estoura no branco e o asfalto iluminado SUBE PARA DENTRO da faixa HSV que
    devia ser so da pintura. A partir dai a mascara e a pista inteira, o limite
    da sombra passa a ser uma reta longa e forte, e o Hough a recebe como se
    fosse faixa. E o modo de falha classico de limiar fixo em estrada clara.
    """
    img[:] = np.clip(img.astype(np.float32) * SOMBRA_GANHO, 0, 255).astype(np.uint8)
    ys, xs = np.mgrid[0:A, 0:L].astype(np.float32)
    fi = math.radians(SOMBRA_ANGULO)
    dist = (xs - L / 2.0) * (-math.sin(fi)) + (ys - 380.0) * math.cos(fi)
    fator = np.where(np.abs(dist) < 92.0, SOMBRA_FATOR, 1.0).astype(np.float32)
    img[:] = np.clip(img.astype(np.float32) * fator[:, :, None],
                     0, 255).astype(np.uint8)


def _noite(img):
    """Contraste baixo: ganho no maximo e preto levantado pela nevoa.

    Repare no que esta transformacao NAO faz: ela nao apaga a pintura. A
    pintura continua mais clara que o asfalto e continua passando no limiar de
    brilho da etapa de cor. O que ela destroi e a DIFERENCA entre as duas --
    e diferenca e a unica coisa que o Canny sabe medir.
    """
    img[:] = np.clip(img.astype(np.float32) * NOITE_GANHO + NOITE_PRETO,
                     0, 255).astype(np.uint8)


def _ruido(img, rng, sigma):
    """Ruido de luminancia, igual nos tres canais: nao mexe na saturacao."""
    r = rng.normal(0.0, sigma, img.shape[:2]).astype(np.float32)
    img[:] = np.clip(img.astype(np.float32) + r[:, :, None], 0, 255).astype(np.uint8)


def quadro(k, condicao, rng, ruido=1.0):
    """Monta um quadro e devolve (imagem BGR, verdade do quadro)."""
    vx, vy, xe, xd = geometria(k)
    img = np.zeros((A, L, 3), np.uint8)
    _fundo(img, vx, vy, xe, xd)
    _acima_do_horizonte(img)

    alfa_esq = APAGADA_ALFA if condicao == 'apagada' else 1.0
    _pintar(img, _poligono_faixa(xe, vx, vy, 9.0), PINTURA, alfa_esq)
    _pintar(img, _poligono_faixa(xd, vx, vy, 9.0), PINTURA, 1.0)
    if condicao == 'faixa_dupla':
        centro = (xe + xd) / 2.0
        for deslocamento in (-10.0, 10.0):
            _pintar(img, _poligono_faixa(centro + deslocamento, vx, vy, 7.0), AMARELO)

    if condicao == 'sombra':
        _sombra(img)
    elif condicao == 'noite':
        _noite(img)
    _ruido(img, rng, (3.5 if condicao == 'noite' else 2.5) * ruido)

    verdade = {
        'quadro': k,
        'faixa_esq': {'x_base': round(xe, 2), 'angulo': round(angulo_faixa(xe, vx, vy), 2)},
        'faixa_dir': {'x_base': round(xd, 2), 'angulo': round(angulo_faixa(xd, vx, vy), 2)},
        'ponto_fuga': [round(vx, 2), round(vy, 2)],
    }
    return img, verdade


def gerar(raiz, condicao, quadros, semente, ruido=1.0):
    """Escreve os PNG de uma condicao e devolve a lista de verdades."""
    pasta = raiz / condicao
    pasta.mkdir(parents=True, exist_ok=True)
    idx = CONDICOES.index(condicao)
    lista = []
    for k in range(quadros):
        rng = np.random.default_rng(semente * 1000003 + idx * 1009 + k)
        img, verdade = quadro(k, condicao, rng, ruido)
        nome = 'quadro%03d.png' % k
        if not cv2.imwrite(str(pasta / nome), img):
            raise SystemExit('nao consegui escrever %s' % (pasta / nome))
        verdade['arquivo'] = '%s/%s' % (condicao, nome)
        lista.append(verdade)
    return lista


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--condicao', default='todas', choices=('todas',) + CONDICOES,
                    help='qual condicao gerar (padrao: todas)')
    ap.add_argument('--quadros', type=int, default=N_QUADROS,
                    help='quadros por condicao (padrao %d)' % N_QUADROS)
    ap.add_argument('--saida', default='estrada', help='pasta de saida (padrao estrada)')
    ap.add_argument('--semente', type=int, default=SEMENTE_PADRAO,
                    help='semente do ruido (padrao %d)' % SEMENTE_PADRAO)
    ap.add_argument('--ruido', type=float, default=1.0,
                    help='multiplica o ruido do sensor (1.0 = padrao; tente 3 na noite)')
    a = ap.parse_args()

    raiz = pathlib.Path(a.saida)
    raiz.mkdir(parents=True, exist_ok=True)
    arquivo = raiz / 'verdade.json'

    verdade = {'semente': a.semente, 'tamanho': [L, A], 'y_base': Y_BASE,
               'y_horizonte': Y_HOR, 'quadros_por_condicao': a.quadros,
               'ruido': a.ruido, 'convencao': CONVENCAO, 'condicoes': {}}

    # Gerar UMA condicao nao pode apagar a verdade das outras: quem esta
    # experimentando sombra nao quer regerar as cinco pastas a cada tentativa.
    if arquivo.is_file() and a.condicao != 'todas':
        try:
            antigo = json.loads(arquivo.read_text(encoding='utf-8'))
            if antigo.get('semente') == a.semente:
                verdade['condicoes'] = antigo.get('condicoes', {})
        except (ValueError, OSError):
            pass

    alvos = CONDICOES if a.condicao == 'todas' else (a.condicao,)
    for condicao in alvos:
        verdade['condicoes'][condicao] = gerar(raiz, condicao, a.quadros,
                                               a.semente, a.ruido)
        print('%-12s %3d quadros em %s' % (condicao, a.quadros, raiz / condicao))

    arquivo.write_text(json.dumps(verdade, indent=1, sort_keys=True) + '\n',
                       encoding='utf-8')
    print('verdade      %s  (%s)' % (arquivo, CONVENCAO.split(';')[0]))
    print('semente %d: rodar de novo da os mesmos bytes.' % a.semente)


if __name__ == '__main__':
    main()
