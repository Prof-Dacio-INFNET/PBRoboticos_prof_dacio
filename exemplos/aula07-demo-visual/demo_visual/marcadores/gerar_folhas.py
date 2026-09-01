#!/usr/bin/env python3
"""Gera as folhas A4 dos marcadores, para imprimir e distribuir.

    python3 marcadores/gerar_folhas.py            # -> marcadores/marcadores-aula07.pdf

As formas vem de demo_visual/formas.py, o MESMO modulo que o detector usa.
Isso nao e elegancia: e a garantia de que o que se imprime e exatamente o que
se procura. Gerador e detector com ideias diferentes de "triangulo" produzem
uma demonstracao que falha em sala sem ninguem descobrir por que.

Precisa de reportlab:  uv pip install reportlab   (dentro de um venv!)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from demo_visual.formas import MARCADORES, pontos

W, H = A4
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'marcadores-aula07.pdf')
c = canvas.Canvas(SAIDA, pagesize=A4)


def rodape(titulo, sub):
    c.setFont('Helvetica-Bold', 15); c.setFillColor(black)
    c.drawCentredString(W / 2, 74, titulo)
    c.setFont('Helvetica', 10.5); c.setFillColor(HexColor('#666666'))
    c.drawCentredString(W / 2, 54, sub)
    c.setFont('Helvetica', 8); c.setFillColor(HexColor('#999999'))
    c.drawCentredString(W / 2, 32, 'PB Sistemas Robóticos · INFNET · Aula 7')


# folha 0: alvo vermelho do Demo 1
c.setFillColor(HexColor('#D71313'))
c.circle(W / 2, H / 2 + 40, 165, fill=1, stroke=0)
rodape('ALVO VERMELHO', 'Demo 1 — segure e mova; as setas dizem para onde a câmera iria')
c.showPage()

# folhas dos marcadores do Demo 2
cx, cy, r = W / 2, H / 2 + 40, 200
for nome, _, servico in MARCADORES:
    c.setFillColor(black)
    p = c.beginPath()
    pts = [(x, H - y) for x, y in pontos(nome, cx, cy, r)]   # y do PDF cresce para cima
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    rodape(nome.upper(), 'Levante esta folha para a câmera  →  chama o serviço %s' % servico)
    c.showPage()

c.save()
print('gerado: %s  (%d folhas)' % (SAIDA, 1 + len(MARCADORES)))
