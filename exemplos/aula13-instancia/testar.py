#!/usr/bin/env python3
"""Confere a regua e os detectores com defeitos SINTETICOS conhecidos.

    python3 testar.py

Nao precisa de ROS 2, nao precisa da cena gravada: cada teste desenha a sua
propria cena minima, com a resposta certa sabida de antemao. Se o avaliador
acerta numa cena cujo erro voce mesmo injetou, ele serve para medir detector
de verdade -- e e esse o raciocinio que vale levar para o TP3.

O teste 2 e o coracao: ele PROVA, em cinco linhas, o que a aula afirma -- duas
pecas encostadas viram uma instancia so no `cor_conectada`, e continuam duas no
`cor_watershed`. Se um dia esse teste falhar, a aula perdeu o argumento.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

import cv2
import numpy as np

from cena import desenhar_pecas, gravar_cena
from instancia import (CONFIG_PADRAO, DETECTORES, cor_da_classe,
                       instancia_de_mascara, modelo_disponivel, sobrepor_classes)
from avaliar import analisar

AQUI = pathlib.Path(__file__).resolve().parent
falhas = []


def conferir(nome, ok, detalhe=''):
    print('  %s  %s%s' % ('ok  ' if ok else 'FALHA', nome,
                          '  -- ' + detalhe if detalhe else ''))
    if not ok:
        falhas.append(nome)


def circulo(classe, centro, raio=26):
    return {'classe': classe, 'forma': 'circulo', 'centro': centro, 'raio': raio}


def retangulo(classe, centro, angulo=0.0, tamanho=(54, 44)):
    return {'classe': classe, 'forma': 'retangulo', 'centro': centro,
            'tamanho': tamanho, 'angulo': angulo}


def cena_de(pecas, largura=320, altura=240):
    """Uma cena de um quadro so, sem ruido: o teste nao precisa de sorte."""
    return desenhar_pecas(pecas, largura, altura, rng=None, ruido=0.0)


def rodar(*args, cwd=AQUI):
    r = subprocess.run([sys.executable, str(AQUI / 'avaliar.py'), *args],
                       capture_output=True, text=True, cwd=str(cwd))
    return r.stdout + r.stderr, r.returncode


def metricas(pecas, metodo, largura=320, altura=240, limiar=0.5):
    """Roda um detector numa cena montada aqui e devolve as contas do avaliador."""
    bgr, rotulos, instancias = cena_de(pecas, largura, altura)
    previstas = DETECTORES[metodo](bgr, CONFIG_PADRAO)
    a = analisar(previstas, rotulos, instancias, limiar)
    iou = [v for _, _, v in a['casados']]
    return {'verdades': len(instancias), 'previstas': len(previstas),
            'fusoes': a['fusoes'], 'divisoes': a['divisoes'],
            'casados': len(a['casados']),
            'iou': sum(iou) / len(iou) if iou else 0.0,
            'classes': [p['classe'] for p in previstas]}


SEPARADAS = [circulo('vermelho', (70, 70)), circulo('azul', (240, 70)),
             retangulo('verde', (150, 180), 20.0)]
# 1,88 raios entre centros: encostam de verdade, e o gargalo que sobra
# sobrevive a abertura morfologica. E a mesma distancia do cena.py.
COLADAS = [circulo('azul', (136, 120)), circulo('azul', (136 + 49, 120))]

print('1. pecas SEPARADAS: os dois detectores classicos contam certo')
for metodo in ('cor_conectada', 'cor_watershed'):
    m = metricas(SEPARADAS, metodo)
    conferir('%s conta 3' % metodo, m['previstas'] == 3,
             '%d previstas, %d casadas' % (m['previstas'], m['casados']))
    conferir('%s casa as 3 com IoU alto' % metodo,
             m['casados'] == 3 and m['iou'] >= 0.85, 'IoU %.2f' % m['iou'])
    conferir('%s nao inventa fusao nem divisao' % metodo,
             m['fusoes'] == 0 and m['divisoes'] == 0)
    conferir('%s acerta as classes' % metodo,
             sorted(m['classes']) == ['azul', 'verde', 'vermelho'],
             ', '.join(sorted(m['classes'])))

print('2. duas pecas ENCOSTADAS: e aqui que os dois se separam')
conectada = metricas(COLADAS, 'cor_conectada')
watershed = metricas(COLADAS, 'cor_watershed')
conferir('cor_conectada conta 1 onde ha 2', conectada['previstas'] == 1,
         '%d previstas para 2 verdades' % conectada['previstas'])
conferir('cor_conectada registra 1 fusao', conectada['fusoes'] == 1,
         '%d fusoes' % conectada['fusoes'])
conferir('cor_watershed conta 2', watershed['previstas'] == 2,
         '%d previstas' % watershed['previstas'])
conferir('cor_watershed nao registra fusao', watershed['fusoes'] == 0)
conferir('e nenhum dos dois levanta excecao', True, 'o erro nao da erro')

print('3. IoU medio: separar tambem melhora a mascara de quem foi achado')
conferir('IoU do watershed >= IoU do conectado',
         watershed['iou'] >= conectada['iou'],
         'conectada %.2f (%d casadas), watershed %.2f (%d casadas)'
         % (conectada['iou'], conectada['casados'],
            watershed['iou'], watershed['casados']))

print('4. o avaliador acusa DIVISAO quando o detector super-segmenta')


def picotador(bgr, cfg=None):
    """Detector de mentira: parte cada instancia do watershed ao meio.

    E o espelho do erro da aula -- em vez de fundir, divide. Serve para provar
    que a regua enxerga os dois lados, e nao so o que a aula quer mostrar.
    """
    saida = []
    for inst in DETECTORES['cor_watershed'](bgr, cfg):
        x, y, w, h = inst['bbox']
        for metade in (0, 1):
            corte = np.zeros_like(inst['mascara'])
            a, b = (x, x + w // 2) if metade == 0 else (x + w // 2, x + w)
            corte[:, a:b] = 255
            pedaco = np.bitwise_and(inst['mascara'], corte)
            if int(np.count_nonzero(pedaco)) < 50:
                continue
            novo = dict(inst)
            novo['mascara'] = pedaco
            saida.append(novo)
    return saida


bgr, rotulos, instancias = cena_de(SEPARADAS)
a = analisar(picotador(bgr, CONFIG_PADRAO), rotulos, instancias, 0.5)
conferir('acusa 3 divisoes (uma por peca partida)', a['divisoes'] == 3,
         '%d divisoes, %d fusoes' % (a['divisoes'], a['fusoes']))
conferir('nao confunde divisao com fusao', a['fusoes'] == 0)

print('5. a figura sai, e MUDA quando o resultado muda')
tmp = pathlib.Path(tempfile.mkdtemp())
pasta_colada, pasta_solta = tmp / 'colada', tmp / 'solta'
gravar_cena(pasta_colada, [cena_de(COLADAS)])
gravar_cena(pasta_solta, [cena_de(SEPARADAS)])
fig_colada, fig_solta = tmp / 'dif-colada.png', tmp / 'dif-solta.png'
saida_c, rc_c = rodar('--pasta', str(pasta_colada), '--imagem', str(fig_colada))
saida_s, rc_s = rodar('--pasta', str(pasta_solta), '--imagem', str(fig_solta))
conferir('gera as duas figuras', fig_colada.is_file() and fig_solta.is_file())
if fig_colada.is_file() and fig_solta.is_file():
    conferir('cena colada e cena solta dao figuras diferentes',
             fig_colada.read_bytes() != fig_solta.read_bytes(),
             '%d x %d bytes' % (os.path.getsize(fig_colada),
                                os.path.getsize(fig_solta)))
conferir('a tabela sai nas duas e o processo termina bem',
         rc_c == 0 and rc_s == 0 and 'cor_watershed' in saida_c)
conferir('a cena colada mostra fusao na tabela',
         ' 1 ' in saida_c or 'fusoes' in saida_c)

print('6. cena ausente: o avaliador tem de ensinar, nao estourar')
saida_v, rc_v = rodar('--pasta', str(tmp / 'nao-existe'))
conferir('sai com codigo diferente de zero', rc_v != 0, 'codigo %d' % rc_v)
conferir('diz o comando que gera a cena', 'python3 cena.py' in saida_v)

print('7. o detector `modelo` ausente NAO derruba o avaliador')
ok_modelo, motivo = modelo_disponivel(CONFIG_PADRAO)
conferir('modelo_disponivel devolve (ok, motivo) sem levantar',
         isinstance(ok_modelo, bool) and isinstance(motivo, str),
         'disponivel=%s' % ok_modelo)
saida_m, rc_m = rodar('--pasta', str(pasta_solta))
conferir('avaliar.py termina com codigo 0 mesmo assim', rc_m == 0)
if ok_modelo:
    conferir('com ultralytics instalado, o modelo aparece na tabela',
             'modelo' in saida_m)
else:
    conferir('sem ultralytics, a linha e pulada com explicacao',
             'pulado' in saida_m and 'venv' in saida_m)
    conferir('e os outros dois continuam medidos',
             'cor_conectada' in saida_m and 'cor_watershed' in saida_m)
saida_so, rc_so = rodar('modelo', '--pasta', str(pasta_solta))
conferir('pedir so o modelo tambem nao estoura', rc_so == 0)

print('8. sobreposicao POR CLASSE (o item 3 do enunciado do TP3)')
ALPHA = 0.5
quadro8, _, _ = cena_de(SEPARADAS)
inst8 = DETECTORES['cor_conectada'](quadro8, CONFIG_PADRAO)
sobre8 = sobrepor_classes(quadro8, inst8, ALPHA)
conferir('sai do tamanho e do tipo do frame',
         sobre8.shape == quadro8.shape and sobre8.dtype == quadro8.dtype,
         '%s %s' % (sobre8.shape, sobre8.dtype))

uniao8 = np.zeros(quadro8.shape[:2], bool)
for inst in inst8:
    uniao8 |= inst['mascara'] > 0
# Os rotulos pintam FORA da mascara de proposito -- sao anotacao, nao camada.
# A caixa de texto nasce no canto da bbox e sobe, entao mora dentro da bbox
# alargada; e esse o unico lugar fora da mascara onde a figura pode mexer.
anota8 = np.zeros_like(uniao8)
for inst in inst8:
    x, y, w, h = inst['bbox']
    anota8[max(0, y - 30):y + h, max(0, x - 4):x + max(w, 140)] = True
fora8 = (~uniao8) & (~anota8)
conferir('fora da mascara (e do rotulo) o pixel e o ORIGINAL, byte a byte',
         np.array_equal(sobre8[fora8], quadro8[fora8]),
         '%d px conferidos' % int(fora8.sum()))
mudou8 = np.any(sobre8 != quadro8, axis=2)
conferir('dentro da mascara, todo pixel mudou',
         bool(mudou8[uniao8].all()),
         '%d de %d px' % (int(mudou8[uniao8].sum()), int(uniao8.sum())))

# A transparencia e literalmente a do enunciado: 0,5 do frame + 0,5 da cor da
# classe. O contorno vai solido por cima da borda, entao a conta se confere no
# INTERIOR da mascara (erodido), que e onde a mistura manda.
inst_um = inst8[0]
nucleo8 = cv2.erode((inst_um['mascara'] > 0).astype(np.uint8), np.ones((7, 7), np.uint8))
dentro8 = nucleo8 > 0
esperado8 = ((1.0 - ALPHA) * quadro8[dentro8].astype(float)
             + ALPHA * np.array(cor_da_classe(inst_um['classe']), float))
erro8 = float(np.abs(sobre8[dentro8].astype(float) - esperado8).max()) if dentro8.any() else 9.0
conferir('a mistura e exatamente alpha=%.1f sobre o frame' % ALPHA, erro8 <= 1.0,
         'maior desvio %.1f nivel(is) em %d px' % (erro8, int(dentro8.sum())))

classes8 = {inst['classe'] for inst in inst8}
cores8 = {tuple(cor_da_classe(c)) for c in classes8}
conferir('uma cor por CLASSE, e classes diferentes com cores diferentes',
         len(cores8) == len(classes8) == 3, ', '.join(sorted(classes8)))
conferir('a cor da classe nao muda de execucao para execucao',
         cor_da_classe('vermelho') == cor_da_classe('vermelho')
         and cor_da_classe('vermelho') != cor_da_classe('azul'))

# Duas instancias ADJACENTES e da MESMA classe, montadas a mao: dividem a
# fronteira em x=120, sem 1 px de folga. E o caso que a cor por classe esconde
# -- a mesma fusao da Aula 13, voltando pela porta da frente.
fundo_par = np.full((120, 240, 3), 200, np.uint8)
m_a, m_b = (np.zeros((120, 240), np.uint8) for _ in range(2))
m_a[30:90, 40:120] = 255
m_b[30:90, 120:200] = 255
par = [instancia_de_mascara(m_a, 'azul'), instancia_de_mascara(m_b, 'azul')]
uniao_par = (m_a > 0) | (m_b > 0)
sem_borda = sobrepor_classes(fundo_par, par, ALPHA, contorno=False)
com_borda = sobrepor_classes(fundo_par, par, ALPHA, contorno=True)
cores_sem = np.unique(sem_borda[uniao_par].reshape(-1, 3), axis=0)
juncao = np.zeros_like(uniao_par)
juncao[30:90, 117:123] = True
linha = int(np.any(com_borda != sem_borda, axis=2)[juncao].sum())
conferir('sem contorno, duas pecas da mesma classe sao UMA mancha so',
         len(cores_sem) == 1, '%d cor(es) na uniao das duas' % len(cores_sem))
conferir('com contorno, a juncao das duas fica visivel', linha >= 60,
         '%d px de linha na faixa de encontro' % linha)
conferir('e o contorno nao vaza para fora da mascara',
         np.array_equal(com_borda[~uniao_par], sem_borda[~uniao_par]))

print()
if falhas:
    print('%d FALHA(S): %s' % (len(falhas), '; '.join(falhas)))
    raise SystemExit(1)
print('todos os testes passaram.')
