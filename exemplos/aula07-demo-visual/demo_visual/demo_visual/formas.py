"""Desenho e classificacao das formas dos marcadores.

Um modulo so, usado pelo gerador das folhas E pelo detector. Isso nao e
elegancia: e a garantia de que o que se imprime e exatamente o que se procura.
Quando o gerador e o detector tem cada um a sua ideia de "triangulo", a
demonstracao falha na sala e ninguem descobre por que.
"""
import math

# Cada marcador: (nome, n_vertices_esperado, servico que ele dispara)
MARCADORES = [
    ('triangulo', 3, '/robo/parar'),
    ('quadrado',  4, '/robo/seguir'),
    ('circulo',   0, '/robo/girar'),      # 0 = classificado por circularidade
    ('cruz',     12, '/robo/emergencia'),
]

NOMES = [m[0] for m in MARCADORES]
SERVICO_DE = {nome: srv for nome, _, srv in MARCADORES}


def pontos(nome, cx, cy, r):
    """Vertices da forma, em coordenadas de tela (y para baixo)."""
    if nome == 'triangulo':
        return [(cx + r * math.cos(a), cy + r * math.sin(a))
                for a in (-math.pi / 2, -math.pi / 2 + 2 * math.pi / 3,
                          -math.pi / 2 + 4 * math.pi / 3)]
    if nome == 'quadrado':
        l = r * 0.80
        return [(cx - l, cy - l), (cx + l, cy - l), (cx + l, cy + l), (cx - l, cy + l)]
    if nome == 'cruz':
        b = r * 0.34           # meia-largura do braco
        e = r * 0.92           # meia-extensao
        return [(cx - b, cy - e), (cx + b, cy - e), (cx + b, cy - b),
                (cx + e, cy - b), (cx + e, cy + b), (cx + b, cy + b),
                (cx + b, cy + e), (cx - b, cy + e), (cx - b, cy + b),
                (cx - e, cy + b), (cx - e, cy - b), (cx - b, cy - b)]
    if nome == 'circulo':
        return [(cx + r * math.cos(2 * math.pi * i / 64),
                 cy + r * math.sin(2 * math.pi * i / 64)) for i in range(64)]
    raise ValueError('forma desconhecida: %s' % nome)


def classificar(contorno, cv2):
    """Contorno -> nome do marcador, ou None.

    A regra e deliberadamente simples e explicavel no quadro:
    circularidade alta = circulo; senao, conta vertices depois de simplificar
    o contorno. Nada de aprendizado, nada de modelo -- e o ponto e esse: da
    para ir longe com geometria, e saber ate onde e o que separa engenharia
    de chute.
    """
    area = cv2.contourArea(contorno)
    perim = cv2.arcLength(contorno, True)
    if perim <= 0 or area <= 0:
        return None

    circularidade = 4 * math.pi * area / (perim * perim)
    if circularidade > 0.80:
        return 'circulo'

    # epsilon proporcional ao perimetro: simplifica o contorno ate sobrarem
    # so os vertices "de verdade", sem depender do tamanho na imagem
    aprox = cv2.approxPolyDP(contorno, 0.025 * perim, True)
    n = len(aprox)

    if n == 3:
        return 'triangulo'
    if n == 4:
        x, y, w, h = cv2.boundingRect(aprox)
        if 0.75 <= (w / float(h)) <= 1.33:
            return 'quadrado'
        return None
    if 10 <= n <= 14:
        # a cruz tem 12 vertices; a folga absorve ruido de borda
        return 'cruz'
    return None
