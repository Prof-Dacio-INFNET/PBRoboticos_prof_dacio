#!/usr/bin/env python3
"""Confere a cena e o detector antes de voce confiar no numero que eles dao.

    python3 testar.py

Nao precisa de ROS 2, nem de MetaDrive, nem da cena previamente gerada: ele
monta a sua propria, pequena, numa pasta temporaria.

Os seis grupos nao conferem se o detector e bom. Conferem se ele falha ONDE a
aula diz que ele falha -- porque e isso que a aula afirma, e afirmacao sem
teste e slide. Em particular, o grupo 2 nao se contenta com "a taxa caiu": ele
exige que a queda apareca na ETAPA DE COR e nao na de reta.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import cv2

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from avaliar_faixas import medir                                      # noqa: E402
from faixas import cfg_padrao, detectar_faixas                        # noqa: E402

QUADROS = 8                  # poucos: o teste tem de rodar em segundos
ERRO_ANG_MAX = 1.0           # graus, no `limpo`. Limiar declarado ANTES de rodar.
ERRO_BASE_MAX = 3.0          # pixels, no `limpo`
falhas = []


def conferir(nome, ok, detalhe=''):
    print(f'  {"ok  " if ok else "FALHA"}  {nome}{"  - " + detalhe if detalhe else ""}')
    if not ok:
        falhas.append(nome)


def gerar(destino, *extra):
    """Roda o cena_estrada.py como o aluno roda: pelo terminal."""
    r = subprocess.run([sys.executable, str(AQUI / 'cena_estrada.py'),
                        '--saida', str(destino), '--quadros', str(QUADROS), *extra],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('cena_estrada.py falhou:\n' + r.stdout + r.stderr)
    return json.loads((pathlib.Path(destino) / 'verdade.json').read_text(encoding='utf-8'))


tmp = pathlib.Path(tempfile.mkdtemp())
cena = tmp / 'estrada'
verdade = gerar(cena)
cfg = cfg_padrao()
m = {c: medir(cena, c, verdade['condicoes'][c], cfg) for c in verdade['condicoes']}

print('1. no `limpo` a pipeline classica acerta, e com erro pequeno')
conferir('achou as duas em >= 95% dos quadros', m['limpo']['ambas'] >= 95.0,
         f"{m['limpo']['ambas']:.1f}%")
conferir(f'erro angular <= {ERRO_ANG_MAX} grau', m['limpo']['erro_ang'] <= ERRO_ANG_MAX,
         f"{m['limpo']['erro_ang']:.2f} graus")
conferir(f'erro na base <= {ERRO_BASE_MAX} px', m['limpo']['erro_base'] <= ERRO_BASE_MAX,
         f"{m['limpo']['erro_base']:.2f} px")

print('2. em `apagada` a taxa cai, e cai na etapa de COR -- nao na de reta')
conferir('achou as duas despenca', m['apagada']['ambas'] < 20.0,
         f"{m['limpo']['ambas']:.0f}% -> {m['apagada']['ambas']:.0f}%")
conferir('mascara do lado esquerdo quase desaparece',
         m['apagada']['cor_esq'] < 0.20 * m['limpo']['cor_esq'],
         f"{m['limpo']['cor_esq']:.0f} -> {m['apagada']['cor_esq']:.0f} px")
conferir('mascara do lado direito continua inteira',
         m['apagada']['cor_dir'] > 0.80 * m['limpo']['cor_dir'],
         f"{m['limpo']['cor_dir']:.0f} -> {m['apagada']['cor_dir']:.0f} px")
conferir('a faixa direita continua sendo achada', m['apagada']['dir'] >= 95.0,
         f"{m['apagada']['dir']:.1f}%")
conferir('nao e a etapa de reta: os segmentos que sobraram ajustam bem',
         m['apagada']['erro_ang'] <= ERRO_ANG_MAX,
         f"erro da faixa direita sozinha {m['apagada']['erro_ang']:.2f} graus")

print('3. em `sombra` o Hough recebe segmentos espurios que nao existiam no `limpo`')
conferir('mais espurios que no limpo', m['sombra']['espurios'] > m['limpo']['espurios'],
         f"{m['limpo']['espurios']:.0f} -> {m['sombra']['espurios']:.0f} por quadro")
conferir('e eles entram nos grupos', m['sombra']['esp_grupo'] >= 1.0,
         f"{m['sombra']['esp_grupo']:.0f} por quadro")
conferir('o erro angular sobe por causa disso',
         m['sombra']['erro_ang'] > 4.0 * m['limpo']['erro_ang'],
         f"{m['limpo']['erro_ang']:.2f} -> {m['sombra']['erro_ang']:.2f} graus")

print('4. em `noite` a cor passa e a BORDA morre -- a outra etapa, o outro sintoma')
conferir('mascara de cor sobrevive', m['noite']['cor'] > 0.80 * m['limpo']['cor'],
         f"{m['limpo']['cor']:.0f} -> {m['noite']['cor']:.0f} px")
conferir('pixels de borda despencam', m['noite']['borda'] < 0.20 * m['limpo']['borda'],
         f"{m['limpo']['borda']:.0f} -> {m['noite']['borda']:.0f} px")

print('5. a regiao de interesse realmente corta: sem ela entram retas do ceu')
y_hor = verdade['y_horizonte']
quadro = cv2.imread(str(cena / verdade['condicoes']['limpo'][0]['arquivo']))
conferir('o quadro de teste foi lido', quadro is not None)


def acima_do_horizonte(res):
    """Quantos segmentos do Hough tem o meio acima da linha do horizonte."""
    return sum(1 for x1, y1, x2, y2 in res['diag']['segmentos'] if (y1 + y2) / 2 < y_hor)


com = detectar_faixas(quadro, cfg_padrao())
sem = detectar_faixas(quadro, cfg_padrao(roi=None))
conferir('com ROI: nenhum segmento acima do horizonte', acima_do_horizonte(com) == 0,
         f'{acima_do_horizonte(com)} segmento(s)')
conferir('sem ROI: aparecem segmentos acima do horizonte', acima_do_horizonte(sem) > 0,
         f'{acima_do_horizonte(sem)} segmento(s) (telhado e estai)')
v0 = verdade['condicoes']['limpo'][0]
if com['faixa_esq'] and sem['faixa_esq']:
    erro_com = abs(com['faixa_esq']['angulo'] - v0['faixa_esq']['angulo'])
    erro_sem = abs(sem['faixa_esq']['angulo'] - v0['faixa_esq']['angulo'])
    conferir('e o angulo da faixa esquerda piora sem a ROI', erro_sem > erro_com + 2.0,
             f'{erro_com:.2f} -> {erro_sem:.2f} graus')
else:
    conferir('e o angulo da faixa esquerda piora sem a ROI', False, 'faixa nao achada')

print('6. --etapas gera os quatro arquivos de evidencia do gate G3.5')
saida = tmp / 'etapas'
r = subprocess.run([sys.executable, str(AQUI / 'faixas.py'),
                    '--quadro', str(cena / verdade['condicoes']['sombra'][0]['arquivo']),
                    '--etapas', str(saida)], capture_output=True, text=True)
conferir('faixas.py --etapas saiu com 0', r.returncode == 0, r.stderr.strip()[:70])
for nome in ('1-cor.png', '2-borda.png', '3-reta.png', '4-final.png'):
    arq = saida / nome
    conferir(f'{nome} existe e nao esta vazio', arq.is_file() and arq.stat().st_size > 1000,
             f'{arq.stat().st_size} bytes' if arq.is_file() else 'ausente')

print('7. a cena e deterministica: mesma semente, mesmos bytes')
a = gerar(tmp / 'rep-a', '--condicao', 'limpo')
b = gerar(tmp / 'rep-b', '--condicao', 'limpo')
conferir('o JSON da verdade e identico',
         json.dumps(a['condicoes'], sort_keys=True) == json.dumps(b['condicoes'], sort_keys=True))
png_a = (tmp / 'rep-a' / 'limpo' / 'quadro000.png').read_bytes()
png_b = (tmp / 'rep-b' / 'limpo' / 'quadro000.png').read_bytes()
conferir('o PNG do quadro 0 e identico byte a byte', png_a == png_b,
         f'{len(png_a)} bytes')
c = gerar(tmp / 'rep-c', '--condicao', 'limpo', '--semente', '99')
conferir('semente diferente muda a cena',
         (tmp / 'rep-c' / 'limpo' / 'quadro000.png').read_bytes() != png_a)
conferir('mas nao muda a verdade (o ruido nao mexe na geometria)',
         json.dumps(c['condicoes'], sort_keys=True) == json.dumps(a['condicoes'], sort_keys=True))

print()
if falhas:
    print(f'{len(falhas)} FALHA(S): ' + '; '.join(falhas))
    raise SystemExit(1)
print('todos os testes passaram.')
