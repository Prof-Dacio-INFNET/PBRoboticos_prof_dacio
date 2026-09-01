"""Percepcao e desenho do Demo 1 -- SEM rclpy dentro.

Modulo puro de proposito: o que nao depende de ROS pode ser testado com uma
imagem e um print, sem subir grafo nenhum. E o mesmo motivo pelo qual o
teste_offline.py existe -- quando a aula trava, o plano B tem que rodar.
"""
import cv2
import numpy as np

# Vermelho ocupa as DUAS pontas do circulo de matiz (0-10 e 170-180).
# Uma faixa so pega metade do vermelho, e o sintoma e "as vezes detecta".
FAIXAS = (((0, 120, 70), (10, 255, 255)),
          ((170, 120, 70), (180, 255, 255)))

VERDE, AMARELO, VERMELHO, BRANCO = (60, 220, 60), (0, 200, 255), (40, 40, 230), (245, 245, 245)


def achar_alvo(bgr, area_min=800):
    """Maior mancha vermelha da cena -> (contorno, area). Sem alvo -> (None, 0)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mascara = None
    for baixo, alto in FAIXAS:
        m = cv2.inRange(hsv, np.array(baixo, np.uint8), np.array(alto, np.uint8))
        mascara = m if mascara is None else cv2.bitwise_or(mascara, m)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    melhor, melhor_area = None, 0.0
    for c in contornos:
        a = cv2.contourArea(c)
        if a >= area_min and a > melhor_area:
            melhor, melhor_area = c, a
    return melhor, melhor_area


def decidir(ex, ey, ea, tol=0.15):
    """Uma acao por vez, e isso e decisao de projeto, nao preguica.

    Robo que corrige tudo ao mesmo tempo fica confuso de assistir e dificil de
    depurar. Centralizar primeiro, aproximar depois, e a ordem que a turma
    consegue acompanhar com os olhos -- e a que um controlador real usa quando
    os eixos nao sao independentes.
    """
    if abs(ex) > tol:
        return ('direita', 'alvo a direita do centro') if ex > 0 else \
               ('esquerda', 'alvo a esquerda do centro')
    if abs(ey) > tol:
        return ('baixo', 'alvo abaixo do centro') if ey > 0 else \
               ('cima', 'alvo acima do centro')
    if ea < -tol:
        return 'frente', 'centralizado, mas longe'
    if ea > tol:
        return 'tras', 'centralizado, mas perto demais'
    return 'parado', 'alvo centralizado na distancia certa'


def _texto(img, txt, org, esc, cor, esp=2):
    cv2.putText(img, txt, org, cv2.FONT_HERSHEY_SIMPLEX, esc, (0, 0, 0), esp + 5, cv2.LINE_AA)
    cv2.putText(img, txt, org, cv2.FONT_HERSHEY_SIMPLEX, esc, cor, esp, cv2.LINE_AA)


def desenhar_seta(img, acao):
    h, w = img.shape[:2]
    cx, cy, L = w // 2, h // 2, min(w, h) // 4
    de_para = {
        'esquerda': ((cx + L // 2, cy), (cx - L, cy)),
        'direita':  ((cx - L // 2, cy), (cx + L, cy)),
        'cima':     ((cx, cy + L // 2), (cx, cy - L)),
        'baixo':    ((cx, cy - L // 2), (cx, cy + L)),
    }
    if acao in de_para:
        p0, p1 = de_para[acao]
        cv2.arrowedLine(img, p0, p1, (0, 0, 0), 24, cv2.LINE_AA, tipLength=0.42)
        cv2.arrowedLine(img, p0, p1, AMARELO, 12, cv2.LINE_AA, tipLength=0.42)
    elif acao == 'frente':
        cv2.circle(img, (cx, cy), L, (0, 0, 0), 22, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), L, AMARELO, 10, cv2.LINE_AA)
        _texto(img, 'APROXIMAR', (cx - 132, cy + L + 46), 1.0, AMARELO)
    elif acao == 'tras':
        cv2.circle(img, (cx, cy), L // 2, (0, 0, 0), 22, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), L // 2, AMARELO, 10, cv2.LINE_AA)
        _texto(img, 'AFASTAR', (cx - 108, cy + L + 46), 1.0, AMARELO)


def desenhar_hud(img, acao, motivo, ex, ey, ea, area, tol=0.15):
    h, w = img.shape[:2]
    cv2.drawMarker(img, (w // 2, h // 2), BRANCO, cv2.MARKER_CROSS, 34, 2)
    dx, dy = int(tol * w / 2), int(tol * h / 2)
    cv2.rectangle(img, (w // 2 - dx, h // 2 - dy), (w // 2 + dx, h // 2 + dy), (170, 170, 170), 1)

    cv2.rectangle(img, (0, 0), (w, 48), (25, 25, 25), -1)
    cor = VERDE if acao == 'parado' else (VERMELHO if acao == 'procurando' else AMARELO)
    cv2.putText(img, 'COMANDO: %s' % acao.upper(), (12, 33),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, cor, 2, cv2.LINE_AA)
    cv2.putText(img, motivo, (340, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.48, BRANCO, 1, cv2.LINE_AA)

    cv2.rectangle(img, (0, h - 30), (w, h), (25, 25, 25), -1)
    cv2.putText(img, 'erro_x=%+.2f   erro_y=%+.2f   erro_area=%+.2f   area=%d px'
                % (ex, ey, ea, int(area)), (12, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, BRANCO, 1, cv2.LINE_AA)


def processar(frame, area_min=800, tol=0.15, area_alvo=0.06):
    """Quadro cru -> (quadro anotado, acao, motivo, ex, ey, ea, area, centro)."""
    h, w = frame.shape[:2]
    contorno, area = achar_alvo(frame, area_min)
    if contorno is None:
        acao, motivo, ex, ey, ea, centro = 'procurando', 'nenhum alvo vermelho na cena', 0.0, 0.0, 0.0, None
    else:
        m = cv2.moments(contorno)
        centro = (int(m['m10'] / m['m00']), int(m['m01'] / m['m00']))
        ex = (centro[0] - w / 2) / (w / 2)
        ey = (centro[1] - h / 2) / (h / 2)
        alvo = area_alvo * w * h
        ea = (area - alvo) / alvo
        acao, motivo = decidir(ex, ey, ea, tol)
        cv2.drawContours(frame, [contorno], -1, VERDE, 3)
        cv2.circle(frame, centro, 7, VERDE, -1)
        cv2.line(frame, (w // 2, h // 2), centro, VERDE, 2)
    desenhar_seta(frame, acao)
    desenhar_hud(frame, acao, motivo, ex, ey, ea, area, tol)
    return frame, acao, motivo, ex, ey, ea, area, centro
