#!/usr/bin/env python3
"""A regua da sessao: os numeros que o relatorio do TP4 item 2 cita.

    python3 medir_sessao.py                 # le sessao.csv
    python3 medir_sessao.py sessao.csv
    python3 medir_sessao.py limpa.csv       # uma sessao sem nenhum evento

Le o CSV e nada mais: funciona igual sobre o CSV do `simular_sessao.py` e
sobre o CSV que o `gravar_pose.py` tira do SEU bag. E' de proposito que ele
nao importa nem o simulador nem o plotador -- a regua tem de poder ser
copiada sozinha para o seu projeto.

A DISCIPLINA DA AULA 9, de novo: os limiares estao declarados LOGO ABAIXO,
antes de qualquer conta. Limiar escolhido depois de ver o resultado e' o que
faz qualquer entrega parecer boa.

O QUE ELE MEDE, e por que cada coisa:

  distancia percorrida   tres numeros, nao um -- e a diferenca entre eles e' a
                         aula. Veja o comentario de `comprimento`.
  vao odom x amcl        a distancia entre as duas estimativas. NAO e' "erro":
                         o bag nao tem verdade. E' a deriva que o AMCL
                         corrigiu, que e' a transformada `map -> odom`.
  interrupcoes           quantas vezes o portao disparou. Conta EVENTO, nao
                         amostra: um evento dura dezenas de linhas do CSV.
  parado / espera        quanto tempo o robo ficou com os dois comandos em
                         zero, e quanto durou o estado `esperando`. Sao
                         numeros diferentes, e o TP4 cobra o segundo.
  reincidencia           dois disparos no MESMO lugar sao o sintoma de que o
                         obstaculo era parede, e nao pessoa. Veja o README.
"""
import argparse
import csv
import math
import sys

# ------------------------------------------------- LIMIARES, declarados antes
# Os dois primeiros nao sao escolha nossa: estao no enunciado do TP4, em
# metros e em segundos.
LIMIAR_OBSTACULO_M = 0.50
ESPERA_ALVO_S = 2.00

# Estes tres sao escolha nossa, e cada um tem uma razao:
#
# A tolerancia existe porque a espera no robo NUNCA sai 2,000 s. O no `Wait`
# do Nav2 recebe `wait_duration` INTEIRO e e' tiqueteado pela arvore a 10 Hz
# (`bt_loop_duration` do bt_navigator), e o bag so' tem as mensagens que
# passaram pela rede. Exigir 2,000 s seria reprovar um sistema correto.
TOL_ESPERA_S = 0.25

# Abaixo disto, em m/s e em rad/s, o robo esta PARADO. Nao se compara com
# zero exato: o `velocity_smoother` do Nav2 publica rampas, e a ultima
# amostra antes da parada vem com uns poucos mm/s.
LIMIAR_PARADO = 0.005

# Dois disparos a menos disto um do outro sao, muito provavelmente, o MESMO
# obstaculo -- e obstaculo que nao sai do lugar nao se resolve esperando.
RAIO_REINCIDENCIA_M = 0.60

# Quantos eventos a sessao do exemplo tem. No SEU bag sera outro numero: o
# enunciado nao pede um numero de interrupcoes, pede que elas FUNCIONEM.
EVENTOS_ESPERADOS = 2

COLUNAS = ('t', 'odom_x', 'odom_y', 'odom_yaw', 'amcl_x', 'amcl_y',
           'amcl_yaw', 'dist_min_scan', 'cmd_v', 'cmd_w', 'estado')


def ler_csv(caminho):
    """Le o CSV da sessao e confere o contrato das colunas."""
    try:
        with open(caminho, newline='', encoding='utf-8') as f:
            linhas = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit('nao achei %s. Gere a sessao antes:\n'
                 '  python3 simular_sessao.py --saida %s' % (caminho, caminho))
    if not linhas:
        sys.exit('o CSV %s nao tem nenhuma linha de dados' % caminho)
    faltando = [c for c in COLUNAS if c not in linhas[0]]
    if faltando:
        sys.exit('faltam no %s as colunas: %s' % (caminho, ', '.join(faltando)))
    saida = []
    for r in linhas:
        d = {'estado': r['estado']}
        for k in COLUNAS:
            if k != 'estado':
                d[k] = float(r[k])
        saida.append(d)
    return saida


def comprimento(linhas, px, py):
    """Soma dos deslocamentos entre amostras consecutivas.

    CUIDADO, e e' o numero mais traicoeiro desta regua: somar deslocamentos
    de uma serie RUIDOSA conta o ruido como caminho andado. O /amcl_pose
    treme alguns centimetros entre varreduras; com amostras de 0,1 s, o passo
    verdadeiro e' da ordem de 3,5 cm e o tremor e' da mesma ordem -- entao a
    soma vem inflada, as vezes ao DOBRO. Isso nao e' defeito do AMCL: e'
    defeito da conta. A distancia honesta sai da odometria (que e' suave,
    ainda que com escala errada) ou da integral de |cmd_v|.
    """
    total = 0.0
    for a, b in zip(linhas, linhas[1:]):
        total += math.hypot(b[px] - a[px], b[py] - a[py])
    return total


def distancia_por_comando(linhas):
    """A integral de |cmd_v| dt: quanto o robo foi MANDADO andar."""
    total = 0.0
    for a, b in zip(linhas, linhas[1:]):
        total += abs(a['cmd_v']) * (b['t'] - a['t'])
    return total


def vao(r):
    """Distancia entre a pose do /odom e a do /amcl_pose numa amostra."""
    return math.hypot(r['odom_x'] - r['amcl_x'], r['odom_y'] - r['amcl_y'])


def blocos(linhas, estado):
    """Faixas [i, j) de amostras consecutivas num mesmo estado."""
    saida = []
    ini = None
    for i, r in enumerate(linhas):
        if r['estado'] == estado and ini is None:
            ini = i
        elif r['estado'] != estado and ini is not None:
            saida.append((ini, i))
            ini = None
    if ini is not None:
        saida.append((ini, len(linhas)))
    return saida


def eventos(linhas, dt):
    """Um registro por interrupcao: quando disparou, quanto parou, onde.

    Um evento comeca quando o estado VIRA `interrompido` e termina quando ele
    volta a `navegando`. Entre os dois cabem `interrompido`, `esperando` e
    `retomando` -- e a espera que o TP4 cobra e' o bloco `esperando`, nao o
    evento inteiro.
    """
    saida = []
    i = 0
    while i < len(linhas):
        if linhas[i]['estado'] != 'interrompido' or (
                i > 0 and linhas[i - 1]['estado'] == 'interrompido'):
            i += 1
            continue
        j = i
        while j < len(linhas) and linhas[j]['estado'] != 'navegando':
            j += 1
        faixa = linhas[i:j]
        espera = [r for r in faixa if r['estado'] == 'esperando']
        parado = max((len(b) for b in blocos_parado(faixa)), default=0)
        saida.append({
            'i': i, 'j': j,
            't': linhas[i]['t'],
            'scan': min(r['dist_min_scan'] for r in faixa),
            'x': linhas[i]['amcl_x'], 'y': linhas[i]['amcl_y'],
            'espera_s': len(espera) * dt,
            'parado_s': parado * dt,
            'evento_s': len(faixa) * dt,
        })
        i = j
    return saida


def blocos_parado(faixa):
    """Faixas de amostras com os DOIS comandos abaixo de LIMIAR_PARADO.

    Os dois: num trecho de giro o `cmd_v` tambem e' zero, e quem olha so'
    para ele conta cada curva como uma parada.
    """
    saida, ini = [], None
    for i, r in enumerate(faixa):
        parado = (abs(r['cmd_v']) < LIMIAR_PARADO
                  and abs(r['cmd_w']) < LIMIAR_PARADO)
        if parado and ini is None:
            ini = i
        elif not parado and ini is not None:
            saida.append(list(range(ini, i)))
            ini = None
    if ini is not None:
        saida.append(list(range(ini, len(faixa))))
    return saida


def medir(linhas):
    """Devolve o dicionario com tudo o que a tabela imprime."""
    passos = [b['t'] - a['t'] for a, b in zip(linhas, linhas[1:])]
    dt = sorted(passos)[len(passos) // 2] if passos else 0.1
    evs = eventos(linhas, dt)

    reincidentes = []
    for a, b in zip(evs, evs[1:]):
        if math.hypot(b['x'] - a['x'], b['y'] - a['y']) < RAIO_REINCIDENCIA_M:
            reincidentes.append((a['t'], b['t']))

    i_max = max(range(len(linhas)), key=lambda i: vao(linhas[i]))
    fora = [e for e in evs if abs(e['espera_s'] - ESPERA_ALVO_S) > TOL_ESPERA_S]

    return {
        'amostras': len(linhas), 'dt': dt, 'duracao': linhas[-1]['t'],
        'hz': 1.0 / dt if dt else float('nan'),
        'dist_odom': comprimento(linhas, 'odom_x', 'odom_y'),
        'dist_amcl': comprimento(linhas, 'amcl_x', 'amcl_y'),
        'dist_cmd': distancia_por_comando(linhas),
        'vao_final': vao(linhas[-1]),
        'vao_max': vao(linhas[i_max]), 't_vao_max': linhas[i_max]['t'],
        'scan_min': min(r['dist_min_scan'] for r in linhas),
        'eventos': evs, 'fora_da_espera': fora, 'reincidentes': reincidentes,
        'parado_total_s': sum(len(b) for b in blocos_parado(linhas)) * dt,
        'estados': sorted({r['estado'] for r in linhas}),
    }


def imprimir(m, caminho):
    print('arquivo       : %s' % caminho)
    print('amostras      : %d linhas, %.1f Hz, %.1f s de sessao'
          % (m['amostras'], m['hz'], m['duracao']))
    print('estados vistos: %s' % ', '.join(m['estados']))
    print()
    print('LIMIARES (declarados no topo do medir_sessao.py, antes de medir)')
    print('  obstaculo   : %.2f m          espera alvo : %.2f s (+- %.2f s)'
          % (LIMIAR_OBSTACULO_M, ESPERA_ALVO_S, TOL_ESPERA_S))
    print('  parado      : |v| < %.3f m/s E |w| < %.3f rad/s'
          % (LIMIAR_PARADO, LIMIAR_PARADO))
    print('  reincidente : dois disparos a menos de %.2f m um do outro'
          % RAIO_REINCIDENCIA_M)
    print()
    print('DISTANCIA PERCORRIDA -- tres contas, tres numeros')
    print('  integral de |cmd_v| dt      : %6.2f m   <- o que foi mandado andar'
          % m['dist_cmd'])
    print('  soma dos passos do /odom    : %6.2f m   <- %+.1f%% (a deriva de '
          'escala)' % (m['dist_odom'],
                       100.0 * (m['dist_odom'] / max(m['dist_cmd'], 1e-9) - 1)))
    print('  soma dos passos do /amcl    : %6.2f m   <- %+.1f%%: o tremor do '
          'AMCL virou caminho' % (m['dist_amcl'],
                                  100.0 * (m['dist_amcl']
                                           / max(m['dist_cmd'], 1e-9) - 1)))
    print('  cite a PRIMEIRA ou a segunda. A terceira e armadilha de conta, '
          'nao distancia.')
    print()
    print('ODOMETRIA x AMCL -- o vao entre as duas trajetorias')
    print('  vao final   : %.2f m' % m['vao_final'])
    print('  vao maximo  : %.2f m, em t = %.1f s' % (m['vao_max'],
                                                     m['t_vao_max']))
    print('  nao chame isto de erro: o bag nao tem verdade. E a deriva que o')
    print('  AMCL corrigiu -- a mesma coisa que a transformada map -> odom.')
    print()
    print('INTERRUPCOES -- %d evento(s); o portao viu no minimo %.3f m'
          % (len(m['eventos']), m['scan_min']))
    if m['eventos']:
        print('  #  t disp (s)  /scan (m)  parado (s)  espera (s)  evento (s)'
              '  2 s cumpridos  onde (x, y)')
        for k, e in enumerate(m['eventos'], start=1):
            ok = abs(e['espera_s'] - ESPERA_ALVO_S) <= TOL_ESPERA_S
            print('  %d  %9.2f  %9.3f  %10.2f  %10.2f  %10.2f  %13s  '
                  '(%.2f, %.2f)'
                  % (k, e['t'], e['scan'], e['parado_s'], e['espera_s'],
                     e['evento_s'], 'sim' if ok else 'NAO', e['x'], e['y']))
        print('  tempo parado na sessao inteira: %.2f s' % m['parado_total_s'])
    else:
        print('  nenhuma. Ou nada entrou na frente do robo, ou o vigia nao '
              'estava no ar.')
    print()
    print('VEREDITO')
    for linha in veredito(m):
        print('  %s' % linha)


def veredito(m):
    """As frases que o aluno copia para o relatorio -- ou que o reprovam."""
    saida = []
    n = len(m['eventos'])
    if n == 0:
        saida.append('NAO ha evento de obstaculo nesta sessao: o item 2 pede '
                     'pelo menos um.')
    elif n != EVENTOS_ESPERADOS:
        saida.append('%d evento(s) -- a sessao de referencia tem %d. Nao e '
                     'erro, so nao e a mesma sessao.' % (n, EVENTOS_ESPERADOS))
    else:
        saida.append('%d evento(s) de obstaculo, como esperado.' % n)

    if n and m['scan_min'] >= LIMIAR_OBSTACULO_M:
        saida.append('ATENCAO: houve interrupcao, mas o /scan nunca ficou '
                     'abaixo de %.2f m. O que disparou nao foi o portao.'
                     % LIMIAR_OBSTACULO_M)
    if m['fora_da_espera']:
        saida.append('ESPERA FORA DO ALVO em %d evento(s): %s. O TP4 pede '
                     '%.1f s.'
                     % (len(m['fora_da_espera']),
                        ', '.join('%.2f s' % e['espera_s']
                                  for e in m['fora_da_espera']),
                        ESPERA_ALVO_S))
    elif n:
        saida.append('todas as esperas dentro de %.2f s +- %.2f s.'
                     % (ESPERA_ALVO_S, TOL_ESPERA_S))
    if m['reincidentes']:
        saida.append('REINCIDENCIA: dois disparos no mesmo lugar (t = %s). '
                     'Obstaculo que nao anda nao se resolve esperando -- veja '
                     'o README.'
                     % '; '.join('%.1f s e %.1f s' % p
                                 for p in m['reincidentes']))
    if n == EVENTOS_ESPERADOS and not m['fora_da_espera'] \
            and not m['reincidentes'] and m['scan_min'] < LIMIAR_OBSTACULO_M:
        saida.append('a sessao sustenta o item 2: interrompeu abaixo de '
                     '%.2f m, esperou %.1f s, retomou e terminou.'
                     % (LIMIAR_OBSTACULO_M, ESPERA_ALVO_S))
    return saida


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv', nargs='?', default='sessao.csv',
                    help='o CSV da sessao (padrao sessao.csv)')
    a = ap.parse_args()
    linhas = ler_csv(a.csv)
    imprimir(medir(linhas), a.csv)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
