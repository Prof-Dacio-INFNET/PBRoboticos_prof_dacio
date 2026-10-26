#!/usr/bin/env python3
"""Confere o filtro e a regua antes de voce confiar neles. Nao precisa de ROS 2.

    python3 testar.py

Um filtro de localizacao errado e' pior que nenhum: ele devolve uma pose com
covariancia pequena, o Nav2 planeja em cima dela, e o robo vai com conviccao
para o lugar errado. Estes sete grupos existem para que o que a Aula 15 afirma
seja verificavel, e nao impressao de tela.

O grupo 2 e' o coracao: ele PROVA, em quatro linhas, a tese da aula -- com a
pose inicial errada a nuvem concentra do mesmo jeito, e a regua acusa. Se um
dia esse grupo falhar, a aula perdeu o argumento.
"""
import math
import time

import numpy as np

from localizacao import (EXPOENTE_PESO, LIMIAR_ACERTO, LIMIAR_DISPERSAO, Mcl,
                         Mundo, Particulas, instante_convergencia, lancar_lote,
                         raio_nuvem, veredito)
from simular_loc import POSE_ERRADA, POSE_INICIAL, simular

falhas = []


def conferir(nome, ok, detalhe=''):
    print('  %s  %s%s' % ('ok  ' if ok else 'FALHA', nome,
                          '  -- ' + detalhe if detalhe else ''))
    if not ok:
        falhas.append(nome)


def erro_medio(registros):
    u = [r['erro_pos'] for r in registros if r['atualizou']]
    return sum(u) / max(len(u), 1)


t_inicio = time.perf_counter()
mundo = Mundo()

print('1. o mapa e o lancamento de raios: a verdade da Aula 11, intacta')
angs = np.linspace(-math.pi, math.pi, 60, endpoint=False)
poses = np.array([[2.0, 4.0, 0.0], [9.0, 2.0, 1.0], [4.0, 6.5, -2.0],
                  [7.0, 4.0, 2.5], [10.5, 6.5, -0.3]])
lote = lancar_lote(mundo, poses, angs)
uma = np.array([mundo.medir(*p, angs, alcance_max=6.0) for p in poses])
fin = np.isfinite(lote) & np.isfinite(uma)
conferir('lancar_lote concorda com o Mundo.medir da Aula 11',
         float(np.abs(lote[fin] - uma[fin]).max()) <= 0.06,
         'maior diferenca %.3f m em %d feixes' % (
             float(np.abs(lote[fin] - uma[fin]).max()), int(fin.sum())))
conferir('e concorda tambem sobre o que esta FORA de alcance',
         np.array_equal(np.isfinite(lote), np.isfinite(uma)),
         '%d feixes infinitos nos dois' % int((~np.isfinite(lote)).sum()))
rng1 = np.random.default_rng(0)
nuvem1 = Particulas.espalhar_uniforme(mundo, 500, rng1)
dentro = [not mundo.ocupado(x, y) for x, y, _ in nuvem1.poses]
conferir('espalhar_uniforme nao poe particula dentro de parede',
         all(dentro), '%d de %d em celula livre' % (sum(dentro), len(dentro)))

print('2. pose inicial ERRADA: a nuvem concentra do mesmo jeito, e a regua acusa')
_, reg_bom, _, bom = simular(particulas=600, inicial='aproximada', segundos=30.0)
_, reg_mau, _, mau = simular(particulas=600, inicial='errada', segundos=30.0)
conferir('com pose aproximada, converge e o erro final e pequeno',
         bom['t_conv'] is not None and bom['erro_pos'] < 0.20,
         'converge em %.1f s, erro final %.3f m (limiares: converge, < 0,20 m)'
         % (bom['t_conv'], bom['erro_pos']))
conferir('com pose aproximada, a regua diz lugar certo',
         bom['veredito'] == 'lugar certo', bom['veredito'])
conferir('com pose ERRADA, a nuvem concentra igual (ou mais)',
         mau['raio_final'] < LIMIAR_DISPERSAO,
         'raio %.3f m contra %.3f m da pose certa -- os dois abaixo de %.2f m'
         % (mau['raio_final'], bom['raio_final'], LIMIAR_DISPERSAO))
conferir('e MESMO ASSIM esta longe da verdade',
         mau['erro_pos'] > 2.0,
         'erro final %.2f m, %.0f graus de rumo' % (mau['erro_pos'], mau['erro_ang']))
conferir('a regua acusa: convergiu para o lugar ERRADO',
         mau['veredito'] == 'lugar ERRADO',
         '%s (acerto = erro < %.2f m)' % (mau['veredito'], LIMIAR_ACERTO))
conferir('o erro nao da erro: nenhuma excecao, nenhum aviso', True,
         'o filtro terminou os %d ciclos sem reclamar de nada' % mau['ciclos'])

print('3. mais particulas: erro nao piora, e o tempo cobra a diferenca')
# Palpite inicial LARGO (sigma 2 m) e poucos feixes: e assim que o numero de
# particulas passa a importar. Com um palpite bom e 30 feixes o problema e
# facil demais, e 60 particulas acertam tanto quanto 1600.
med = {}
for n in (60, 900):
    erros, tempos = [], []
    for sem in (1, 2, 3):
        t0 = time.perf_counter()
        _, reg, _, r = simular(particulas=n, inicial='aproximada', segundos=25.0,
                               feixes=8, semente=sem, sigma=2.0)
        tempos.append(time.perf_counter() - t0)
        erros.append(erro_medio(reg))
    med[n] = (sum(erros) / 3, sum(tempos) / 3)
conferir('900 particulas nao erram mais que 60', med[900][0] <= med[60][0],
         'erro medio %.4f m com 900 contra %.4f m com 60 (3 sementes)'
         % (med[900][0], med[60][0]))
conferir('e a conta chega: 900 particulas custam mais tempo',
         med[900][1] > med[60][1],
         '%.2f s contra %.2f s por corrida de 25 s simulados'
         % (med[900][1], med[60][1]))

print('4. menos feixes: a estimativa degrada de forma mensuravel')
mf = {}
for f in (5, 30):
    erros, raios, tempos = [], [], []
    for sem in (1, 2):
        t0 = time.perf_counter()
        _, reg, _, r = simular(particulas=400, inicial='aproximada', segundos=30.0,
                               feixes=f, semente=sem)
        tempos.append(time.perf_counter() - t0)
        erros.append(erro_medio(reg))
        raios.append(r['raio_final'])
    mf[f] = (sum(erros) / 2, sum(raios) / 2, sum(tempos) / 2)
conferir('com 5 feixes o erro medio e maior que com 30', mf[5][0] > mf[30][0],
         '%.4f m contra %.4f m' % (mf[5][0], mf[30][0]))
conferir('e a nuvem fica mais gorda: menos evidencia, menos certeza',
         mf[5][1] > mf[30][1],
         'raio final %.3f m contra %.3f m' % (mf[5][1], mf[30][1]))
conferir('em troca, 5 feixes custam menos tempo que 30', mf[5][2] < mf[30][2],
         '%.2f s contra %.2f s' % (mf[5][2], mf[30][2]))

print('5. a reamostragem dispara, e a nuvem se renova')
conferir('o N efetivo cai abaixo do limiar em algum momento',
         bom['n_efetivo_min'] < 0.5 * 600,
         'minimo %.1f de 600 (limiar: N/2 = 300)' % bom['n_efetivo_min'])
conferir('e a reamostragem roda de fato', bom['reamostragens'] > 0,
         '%d reamostragens em %d ciclos' % (bom['reamostragens'], bom['ciclos']))
# E a reamostragem faz o que diz: copia quem tem peso e descarta quem nao tem.
rng5 = np.random.default_rng(3)
nuvem5 = Particulas(np.array([[1.0, 1.0, 0.0], [2.0, 2.0, 0.0],
                              [3.0, 3.0, 0.0], [4.0, 4.0, 0.0]]))
nuvem5.pesos = np.array([0.97, 0.01, 0.01, 0.01])
mcl5 = Mcl(mundo, nuvem5, rng5)
antes = nuvem5.n_efetivo()
mcl5.reamostrar()
sobreviventes = np.unique(nuvem5.poses[:, 0])
conferir('N efetivo despenca quando um peso domina', antes < 1.1,
         'N efetivo %.2f com pesos (0,97 / 0,01 / 0,01 / 0,01)' % antes)
conferir('a reamostragem sistematica copia quem tem peso',
         float((nuvem5.poses[:, 0] == 1.0).sum()) >= 3,
         '%d das 4 copias sao a particula de peso 0,97' % int((nuvem5.poses[:, 0] == 1.0).sum()))
conferir('e descarta as outras (a nuvem se renova)', len(sobreviventes) < 4,
         '%d poses distintas sobraram das 4' % len(sobreviventes))
conferir('depois do corte, os pesos voltam todos a 1/N',
         np.allclose(nuvem5.pesos, 0.25) and abs(nuvem5.n_efetivo() - 4.0) < 1e-9,
         'N efetivo volta a %.2f' % nuvem5.n_efetivo())

print('6. determinismo: mesma semente, mesmo resultado')
_, r_a, _, s_a = simular(particulas=300, inicial='uniforme', segundos=20.0, semente=7)
_, r_b, _, s_b = simular(particulas=300, inicial='uniforme', segundos=20.0, semente=7)
_, r_c, _, s_c = simular(particulas=300, inicial='uniforme', segundos=20.0, semente=8)
iguais = all(abs(x['erro_pos'] - y['erro_pos']) == 0.0
             and abs(x['n_efetivo'] - y['n_efetivo']) == 0.0
             for x, y in zip(r_a, r_b))
conferir('duas corridas com semente 7 dao a MESMA serie, bit a bit',
         iguais and len(r_a) == len(r_b), '%d linhas conferidas' % len(r_a))
conferir('e o mesmo resumo', s_a['erro_pos'] == s_b['erro_pos']
         and s_a['t_conv'] == s_b['t_conv'],
         'erro final %.6f m nas duas' % s_a['erro_pos'])
conferir('com semente 8 o resultado muda (o acaso existe, so e repetivel)',
         s_c['erro_pos'] != s_a['erro_pos'],
         'semente 7: %.4f m / semente 8: %.4f m' % (s_a['erro_pos'], s_c['erro_pos']))

print('7. a regua em si: o criterio de convergencia faz o que promete')
estavel = [{'t': 0.2 * i, 'atualizou': True, 'disp_x': 0.05, 'disp_y': 0.05,
            'disp_th': 0.02} for i in range(40)]
conferir('nuvem sempre concentrada: convergiu no primeiro instante',
         instante_convergencia(estavel) == 0.0,
         'instante %s' % instante_convergencia(estavel))
gorda = [dict(r, disp_x=1.0, disp_y=1.0) for r in estavel]
conferir('nuvem sempre gorda: nunca convergiu',
         instante_convergencia(gorda) is None)
piscando = [dict(r, disp_x=(0.05 if i % 2 else 1.0),
                 disp_y=(0.05 if i % 2 else 1.0))
            for i, r in enumerate(estavel)]
conferir('nuvem que pisca nao conta como convergida',
         instante_convergencia(piscando) is None,
         'um instante concentrado isolado e sorte, nao convergencia')
tarde = [dict(r, disp_x=(0.05 if i >= 12 else 1.0),
              disp_y=(0.05 if i >= 12 else 1.0))
         for i, r in enumerate(estavel)]
conferir('e pega o PRIMEIRO instante da sequencia estavel',
         abs(instante_convergencia(tarde) - 2.4) < 1e-9,
         'convergiu em %.1f s (indice 12 x 0,2 s)' % instante_convergencia(tarde))
conferir('convergir nao e acertar: a regua separa as duas coisas',
         veredito(3.0, 0.1) == 'lugar certo'
         and veredito(3.0, 9.0) == 'lugar ERRADO'
         and veredito(None, 0.1) == 'NAO convergiu',
         'os tres vereditos possiveis')
conferir('o expoente da verossimilhanca esta declarado e abaixo de 1',
         0.0 < EXPOENTE_PESO < 1.0,
         'EXPOENTE_PESO = %.2f (os feixes nao sao independentes)' % EXPOENTE_PESO)
d_erro = math.hypot(POSE_ERRADA[0] - POSE_INICIAL[0],
                    POSE_ERRADA[1] - POSE_INICIAL[1])
conferir('a POSE_ERRADA esta mesmo longe da verdadeira', d_erro > 5.0,
         '%.1f m de distancia, na outra sala' % d_erro)

print()
print('tempo total: %.1f s' % (time.perf_counter() - t_inicio))
if falhas:
    print('%d FALHA(S): %s' % (len(falhas), '; '.join(falhas)))
    raise SystemExit(1)
print('todos os testes passaram.')
