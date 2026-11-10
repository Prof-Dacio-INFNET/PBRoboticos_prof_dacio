#!/usr/bin/env python3
"""Gera a sessao que o `ros2 bag` da sua entrega vai conter -- sem ROS 2.

    python3 simular_sessao.py
    python3 simular_sessao.py --saida sessao.csv
    python3 simular_sessao.py --sem-eventos --saida limpa.csv
    python3 simular_sessao.py --espera 1.2 --saida espera-curta.csv
    python3 simular_sessao.py --como-vigia-real --saida real.csv

O QUE ELE E:

    O item 2 do TP4 pede quatro coisas de uma vez -- arvore de comportamento,
    portao de 0,5 m, espera de 2 s, bag reproduzivel com grafico da trajetoria.
    As tres ultimas sao ANALISE DE DADOS: elas se fazem sobre um CSV, e quem
    tem o CSV nao precisa de robo nenhum para fazer a conta. Este script
    produz um CSV com a mesma forma do que o `gravar_pose.py` tira do seu bag,
    para que a regua (`medir_sessao.py`) e o grafico (`plotar_trajetoria.py`)
    possam ser escritos, conferidos e CITADOS antes de o robo existir.

    Nao e um simulador de fisica e nao pretende ser: e um gerador de sessao
    sintetica, deterministico, com semente fixa. O percurso e fixo -- a mesma
    ideia do `simular_loc.py` da Aula 15, e pelo mesmo motivo: o numero que vai
    para a tabela da aula tem de sair igual na sua maquina e na minha.

O QUE O CSV TEM, e por que NAO tem a verdade:

    t, odom_x, odom_y, odom_yaw, amcl_x, amcl_y, amcl_yaw,
    dist_min_scan, cmd_v, cmd_w, estado

    Exatamente o que um bag de /odom, /amcl_pose, /scan, /cmd_vel e
    /estado_vigia entrega -- e NADA MAIS. A pose verdadeira existe aqui
    dentro (este script a integra), mas ela NAO vai para o arquivo, porque no
    bag do seu robo ela nao existe. E essa ausencia que explica por que a
    coluna da regua se chama "odom x amcl" e nao "erro": sem verdade, o que
    da' para medir e' a DISTANCIA ENTRE AS DUAS ESTIMATIVAS, que e' a deriva
    que o AMCL corrigiu. Quem quiser erro contra a verdade so' tem em
    simulacao, e o `testar.py` usa isso -- la' dentro, nunca no CSV.

A HISTORIA QUE A SESSAO CONTA, em quatro estados:

    navegando     o goal esta ativo, o robo segue a rota
    interrompido  o portao de 0,5 m disparou: cancel_goal_async enviado, o
                  robo freia (3 amostras, e a desaceleracao aparece em cmd_v)
    esperando     os 2 s de espera, com cmd_v e cmd_w em ZERO
    retomando     o MESMO objetivo foi reenviado, o robo acelera de volta

    COMO O VIGIA REAL GRAVA (`--como-vigia-real`): no robo, `interrompido`
    dura so' o tempo de o servidor aceitar o cancelamento (~2 ms no ensaio de
    09/11/2026) e `retomando` o de o goal novo ser aceito. A 10 Hz nenhum dos
    dois cai numa linha do CSV, e o temporizador de 2 s do vigia comeca no
    cancelamento: o robo FREIA dentro do `esperando`. Com a opcao, o CSV sai
    assim -- so' `navegando` e `esperando`, a frenagem dentro da espera e a
    aceleracao dentro do `navegando` --, que e' a sessao que a regua tem de
    acertar e que, ate 09/11, ela errava contando zero.

    Sao dois eventos, nos dois lugares declarados em ARCOS_EVENTO. O obstaculo
    e' uma PESSOA que entra na frente do robo e sai alguns segundos depois --
    e essa escolha e' a aula inteira. A espera de 2 s do enunciado so' faz
    sentido se o obstaculo for transitorio. Se for uma parede, esperar 2 s e
    retomar da um laco infinito: o robo para, espera, anda 20 cm, para de
    novo, para sempre. O README tem o paragrafo; o `medir_sessao.py` tem a
    coluna que acusa (reincidencia no mesmo lugar).
"""
import argparse
import csv
import math

import numpy as np

# --------------------------------------------------------------- a sessao
SEMENTE = 42               # fixa: dois `python3 simular_sessao.py` dao o mesmo CSV
DT = 0.1                   # s por amostra -> 10 Hz, a taxa do `gravar_pose.py`
SALA = (12.0, 8.0)         # m, a mesma caixa do mundo da Aula 11
POSE_INICIAL = (2.0, 4.0, 0.0)
ALCANCE_MAX = 6.0          # m, alcance do laser -- acima disso o /scan da inf

# Deriva da odometria: erro de ESCALA, nao de ruido. E' o `aplicar_deriva` da
# Aula 11 (v e w multiplicados por 1 + pct/100), que e' o erro de quem mediu o
# raio da roda com regua: pequeno, constante, e que NAO se cancela. Ele e' a
# razao de existir o AMCL, e e' a distancia entre as duas trajetorias do
# grafico do item 2.
DERIVA_PCT = 3.0

# O AMCL nao e' a verdade: ele e' uma estimativa boa. Estes dois numeros sao o
# quanto a pose do /amcl_pose balanca em volta da verdade -- ordem de grandeza
# do que se ve num AMCL convergido, com nuvem de poucos centimetros de raio.
RUIDO_AMCL = 0.025         # m, desvio-padrao em x e y
RUIDO_AMCL_ANG = 0.012     # rad, desvio-padrao em yaw
RUIDO_SCAN = 0.015         # m, ruido da menor distancia do /scan

# ------------------------------------------------- o portao e a espera
# O limiar do enunciado. Nao e' escolha nossa: esta no TP4, em metros.
LIMIAR_OBSTACULO = 0.5     # m
ESPERA_S = 2.0             # s, tambem do enunciado

# Atraso de tick: no robo, a espera NUNCA sai exatamente 2,000 s. O no `Wait`
# do Nav2 recebe `wait_duration` INTEIRO e e' tiqueteado pela arvore a 10 Hz
# (o `bt_loop_duration` do bt_navigator), entao a espera observada no bag vem
# 2,0 a 2,2 s. O segundo evento desta sessao leva este atraso de proposito,
# para que a regua tenha de usar a tolerancia dela em vez de comparar com 2,0
# exato -- regua que so' passa no caso perfeito nao e' regua.
ATRASO_TICK_S = 0.1

FREIO_S = 0.3              # s de desaceleracao antes de parar de vez
RETOMADA_S = 0.8           # s de aceleracao depois de reenviar o objetivo
REARME_S = 1.5             # s de carencia antes de o portao poder disparar de novo

# ----------------------------------------------------------- o obstaculo
RAIO_PESSOA = 0.18         # m, o raio do cilindro que o laser ve
DIST_PESSOA = 0.95         # m a frente do robo em que a pessoa aparece
DURACAO_PESSOA_S = 2.6     # s que ela fica ali antes de sair de cena
# Onde os dois eventos acontecem, em METROS PERCORRIDOS -- nao em segundos.
# Tem de ser em arco: a primeira parada atrasa o relogio, e um evento marcado
# em segundos sairia do lugar. Em arco, os dois caem sempre no mesmo ponto do
# percurso, com ou sem parada antes.
ARCOS_EVENTO = (4.0, 14.0)

# ------------------------------------------------------------- o percurso
# (v em m/s, w em rad/s, duracao em s). Retangulo dentro da sala, sem passar
# perto de parede: o portao de 0,5 m nao distingue parede de pessoa, e um
# percurso rente a parede dispararia o tempo todo. O `testar.py` confere a
# folga minima, em vez de confiar nesta aritmetica.
#
# A taxa de giro e' 0,60 rad/s e nao 0,50 por um motivo de FIGURA, nao de
# robo: no painel de baixo do `plotar_trajetoria.py` o |cmd_w| e o limiar de
# 0,5 m sao desenhados no mesmo eixo, e duas linhas em 0,50 no mesmo grafico
# sao duas linhas que ninguem consegue separar. Cada giro leva 2,62 s, que
# dao 1,572 rad -- 90,1 graus.
PERCURSO = (
    (0.35, 0.00, 14.0),    # leste, pelo meio da sala
    (0.00, 0.60, 2.62),    # vira para o norte
    (0.35, 0.00, 7.0),     # norte
    (0.00, -0.60, 2.62),   # vira para o leste
    (0.35, 0.00, 10.0),    # leste, pela metade de cima
    (0.00, -0.60, 2.62),   # vira para o sul
    (0.35, 0.00, 13.0),    # sul, pelo lado leste
    (0.00, -0.60, 2.62),   # vira para o oeste
    (0.35, 0.00, 12.0),    # oeste, pela metade de baixo
    (0.00, -0.60, 2.62),   # vira para o norte
    (0.35, 0.00, 6.0),     # norte, de volta a altura da largada
    (0.00, 0.60, 2.62),    # vira para o oeste
    (0.35, 0.00, 11.0),    # oeste, FECHANDO o laco em cima do trecho de ida
)
DURACAO_ROTA = sum(d for _, _, d in PERCURSO)

# A forma do CSV. E' contrato: o `plotar_trajetoria.py`, o `medir_sessao.py` e
# o `gravar_pose.py` do pacote ROS 2 escrevem e leem ESTES nomes, nesta ordem.
CAMPOS_CSV = ('t', 'odom_x', 'odom_y', 'odom_yaw', 'amcl_x', 'amcl_y',
              'amcl_yaw', 'dist_min_scan', 'cmd_v', 'cmd_w', 'estado')

ESTADOS = ('navegando', 'interrompido', 'esperando', 'retomando')


def normalizar(ang):
    """Traz o angulo para (-pi, pi]."""
    return math.atan2(math.sin(ang), math.cos(ang))


def passo_diferencial(pose, v, w, dt):
    """Um passo de um robo de tracao diferencial. O mesmo da Aula 11.

    Integracao de Euler: boa o suficiente com dt de 0,1 s e v de 0,35 m/s --
    o erro de discretizacao fica em milimetros, tres ordens de grandeza abaixo
    da deriva de 3% que este script quer mostrar.
    """
    x, y, th = pose
    return (x + v * math.cos(th) * dt,
            y + v * math.sin(th) * dt,
            normalizar(th + w * dt))


def aplicar_deriva(pose, v, w, dt, pct):
    """Integra a odometria com erro sistematico de ESCALA. Da Aula 11."""
    k = 1.0 + pct / 100.0
    return passo_diferencial(pose, v * k, w * k, dt)


def comando(t_rota):
    """(v, w) do percurso no instante `t_rota`. Depois do fim, parado.

    O argumento e' o tempo DE ROTA, nao o tempo de parede: ele congela
    enquanto o robo espera. E' assim no robo tambem -- o objetivo continua
    existindo, a arvore esta num no `Wait`, e o percurso retoma de onde parou.
    """
    for v, w, dur in PERCURSO:
        if t_rota < dur:
            return v, w
        t_rota -= dur
    return 0.0, 0.0


def folga_de_parede(x, y):
    """Distancia ate a parede mais proxima da sala. E' o piso do /scan."""
    return min(x, SALA[0] - x, y, SALA[1] - y)


def posicoes_das_pessoas(arcos=ARCOS_EVENTO, dt=DT):
    """Onde cada pessoa entra na frente do robo, em (x, y).

    Integra o percurso NOMINAL (sem nenhuma parada) so' para descobrir a pose
    do robo quando ele tiver andado `arco` metros, e poe a pessoa
    DIST_PESSOA metros a frente, na direcao em que ele aponta. Fazer isso por
    arco e nao por tempo e' o que mantem os dois eventos no mesmo lugar do
    percurso mesmo quando a primeira parada atrasa tudo o que vem depois.
    """
    pendentes = list(arcos)
    saida = []
    pose = tuple(POSE_INICIAL)
    arco = 0.0
    t = 0.0
    while pendentes and t < DURACAO_ROTA + 1.0:
        if arco >= pendentes[0]:
            x, y, th = pose
            saida.append((x + DIST_PESSOA * math.cos(th),
                          y + DIST_PESSOA * math.sin(th)))
            pendentes.pop(0)
            continue
        v, w = comando(t)
        pose = passo_diferencial(pose, v, w, dt)
        arco += abs(v) * dt
        t += dt
    return saida


def distancia_minima(pose, pessoa):
    """O que o /scan reportaria como menor distancia, agora.

    Duas contribuicoes: a parede mais proxima da sala (o piso, sempre
    presente) e, se houver pessoa em cena, a superficie do cilindro dela.
    Cortada no alcance do laser, porque parede a 9 m nao aparece num laser de
    6 m -- la' o /scan devolve inf, e `inf` tratado como numero e' a armadilha
    classica do `min(ranges)` (veja o docstring do `vigia.py`).
    """
    x, y, _ = pose
    d = folga_de_parede(x, y)
    if pessoa is not None:
        d = min(d, max(0.02, math.hypot(x - pessoa[0], y - pessoa[1])
                       - RAIO_PESSOA))
    return min(d, ALCANCE_MAX)


def simular(semente=SEMENTE, dt=DT, deriva_pct=DERIVA_PCT, espera_s=ESPERA_S,
            limiar=LIMIAR_OBSTACULO, com_eventos=True, atraso_tick=ATRASO_TICK_S,
            ruido_scan=RUIDO_SCAN, ruido_amcl=RUIDO_AMCL, como_vigia_real=False):
    """Roda a sessao inteira. Devolve (registros, resumo).

    Cada registro tem as 11 colunas do CSV **mais** tres que nao vao para o
    arquivo: `x_verdade`, `y_verdade`, `th_verdade`. Elas existem para o
    `testar.py` poder provar o que o CSV nao permite provar -- que o erro da
    odometria cresce e o do AMCL nao. No bag do seu robo elas nao existem, e e'
    por isso que elas param aqui.

    `como_vigia_real` muda so' o que vai para a coluna `estado` e quando a
    espera comeca a contar (veja o docstring do modulo): `interrompido` vira
    `esperando`, a espera total continua sendo a pedida, `retomando` vira
    `navegando`, e a carencia conta a partir da retomada, como no vigia.
    """
    rng = np.random.default_rng(semente)
    pessoas = posicoes_das_pessoas() if com_eventos else []

    verdade = tuple(POSE_INICIAL)
    odom = tuple(POSE_INICIAL)
    estado = 'navegando'
    passos_no_estado = 0          # quantos passos faltam para sair do estado
    t_rota = 0.0
    arco = 0.0
    rearme = 0                    # passos de carencia do portao
    proxima_pessoa = 0            # indice da proxima pessoa a entrar em cena
    pessoa_ativa = None
    pessoa_passos = 0
    eventos = []                  # (t do disparo, dist no disparo, espera pedida)

    registros = []
    n_max = int(round((DURACAO_ROTA + 60.0) / dt))
    for n in range(n_max):
        t = n * dt
        if t_rota >= DURACAO_ROTA:
            break

        # ---- quem entra e quem sai de cena, por arco percorrido ----------
        if (proxima_pessoa < len(pessoas) and arco >= ARCOS_EVENTO[proxima_pessoa]
                and pessoa_ativa is None):
            pessoa_ativa = pessoas[proxima_pessoa]
            pessoa_passos = int(round(DURACAO_PESSOA_S / dt))
            proxima_pessoa += 1
        if pessoa_ativa is not None:
            pessoa_passos -= 1
            if pessoa_passos <= 0:
                pessoa_ativa = None

        # ---- o sensor -----------------------------------------------------
        dist = distancia_minima(verdade, pessoa_ativa)
        if ruido_scan > 0.0:
            dist = max(0.02, dist + float(rng.normal(0.0, ruido_scan)))

        # ---- o portao, que e' a logica do `vigia.py` em cinco linhas ------
        if estado == 'navegando' and rearme <= 0 and dist < limiar:
            estado = 'interrompido'
            passos_no_estado = int(round(FREIO_S / dt))
            # A espera pedida ao no `Wait` e' sempre a mesma; o que varia e' o
            # atraso de tick que o segundo evento carrega (veja ATRASO_TICK_S).
            pedida = espera_s + atraso_tick * len(eventos)
            eventos.append((t, dist, pedida))
        rearme -= 1

        # ---- o fator que multiplica o comando no estado atual -------------
        # Em `navegando` vale 1; frear e retomar sao rampas lineares; em
        # `esperando` e' zero, e e' esse zero que a regua procura no CSV.
        if estado == 'interrompido':
            n_freio = int(round(FREIO_S / dt))
            fator = max(0.0, passos_no_estado - 1) / n_freio
            fator = max(fator, 1.0 / (n_freio + 1))   # nunca chega a zero aqui:
            #            o zero pertence a `esperando`, e misturar os dois faria
            #            a regua contar a frenagem como parte da espera.
        elif estado == 'esperando':
            fator = 0.0
        elif estado == 'retomando':
            n_ret = int(round(RETOMADA_S / dt))
            fator = 1.0 - max(0.0, passos_no_estado - 1) / (n_ret + 1)
        else:
            fator = 1.0

        v_nom, w_nom = comando(t_rota)
        v, w = v_nom * fator, w_nom * fator

        # ---- a pose: verdade, odometria (com deriva) e AMCL ---------------
        amcl = (verdade[0] + float(rng.normal(0.0, ruido_amcl)),
                verdade[1] + float(rng.normal(0.0, ruido_amcl)),
                normalizar(verdade[2] + float(rng.normal(0.0, RUIDO_AMCL_ANG))))

        rotulo = estado
        if como_vigia_real:
            rotulo = {'interrompido': 'esperando',
                      'retomando': 'navegando'}.get(estado, estado)
        registros.append({
            't': round(t, 4),
            'odom_x': odom[0], 'odom_y': odom[1], 'odom_yaw': odom[2],
            'amcl_x': amcl[0], 'amcl_y': amcl[1], 'amcl_yaw': amcl[2],
            'dist_min_scan': dist, 'cmd_v': v, 'cmd_w': w, 'estado': rotulo,
            'x_verdade': verdade[0], 'y_verdade': verdade[1],
            'th_verdade': verdade[2]})

        # ---- anda -----------------------------------------------------------
        verdade = passo_diferencial(verdade, v, w, dt)
        odom = aplicar_deriva(odom, v, w, dt, deriva_pct)
        arco += abs(v) * dt
        # O tempo de rota anda na MESMA proporcao do comando. Com isso o
        # percurso e' percorrido no mesmo arco, pare quantas vezes parar: o
        # ponto do percurso em que a pessoa aparece nao se mexe.
        t_rota += dt * fator

        # ---- a maquina de estados ------------------------------------------
        if estado != 'navegando':
            passos_no_estado -= 1
            if passos_no_estado <= 0:
                if estado == 'interrompido':
                    estado = 'esperando'
                    passos_no_estado = int(round(eventos[-1][2] / dt))
                    if como_vigia_real:
                        # o temporizador do vigia comecou no cancelamento:
                        # a frenagem ja comeu parte da espera
                        passos_no_estado -= int(round(FREIO_S / dt))
                elif estado == 'esperando':
                    estado = 'retomando'
                    passos_no_estado = int(round(RETOMADA_S / dt))
                else:
                    estado = 'navegando'
                    rearme = int(round(REARME_S / dt))
                    if como_vigia_real:
                        # no vigia a carencia comeca no reenvio do goal
                        rearme -= int(round(RETOMADA_S / dt))

    final = registros[-1]
    erro_odom = math.hypot(final['odom_x'] - final['x_verdade'],
                           final['odom_y'] - final['y_verdade'])
    erro_amcl = math.hypot(final['amcl_x'] - final['x_verdade'],
                           final['amcl_y'] - final['y_verdade'])
    resumo = {
        'semente': semente, 'dt': dt, 'linhas': len(registros),
        'duracao': final['t'], 'deriva_pct': deriva_pct, 'limiar': limiar,
        'espera_s': espera_s, 'eventos': len(eventos),
        'como_vigia_real': como_vigia_real,
        'arco': arco, 'erro_odom_final': erro_odom,
        'erro_amcl_final': erro_amcl,
        'folga_minima': min(folga_de_parede(r['x_verdade'], r['y_verdade'])
                            for r in registros),
        'pessoas': pessoas,
        'disparos': [(round(te, 2), round(de, 3), round(pe, 2))
                     for te, de, pe in eventos],
    }
    return registros, resumo


def gravar_csv(caminho, registros):
    """Grava SO' as 11 colunas do contrato. A verdade fica de fora."""
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        esc = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        esc.writeheader()
        for r in registros:
            esc.writerow({k: r[k] for k in CAMPOS_CSV})
    return caminho


def imprimir_resumo(r):
    print('semente       : %d  (fixa -- rodar de novo da o mesmo CSV)'
          % r['semente'])
    print('amostras      : %d linhas a %.1f Hz, %.1f s de sessao'
          % (r['linhas'], 1.0 / r['dt'], r['duracao']))
    print('percurso      : fixo, %d trechos, %.1f m andados'
          % (len(PERCURSO), r['arco']))
    print('folga minima  : %.2f m da parede mais proxima  (limiar do portao: '
          '%.2f m)' % (r['folga_minima'], r['limiar']))
    print('deriva        : %.1f%% de escala na odometria' % r['deriva_pct'])
    print('eventos       : %d disparos do portao de %.2f m' % (r['eventos'],
                                                              r['limiar']))
    for i, (te, de, pe) in enumerate(r['disparos'], start=1):
        print('  evento %d    : t = %6.2f s, /scan em %.3f m, espera pedida '
              '%.2f s' % (i, te, de, pe))
    print('odom x verdade: %.2f m no fim  (e o que o AMCL teve de corrigir)'
          % r['erro_odom_final'])
    print('amcl x verdade: %.2f m no fim  (nao esta no CSV: o bag nao tem '
          'verdade)' % r['erro_amcl_final'])


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--saida', default='sessao.csv', metavar='ARQ.csv',
                    help='onde gravar (padrao sessao.csv)')
    ap.add_argument('--semente', type=int, default=SEMENTE,
                    help='padrao %d, fixa' % SEMENTE)
    ap.add_argument('--deriva', type=float, default=DERIVA_PCT,
                    help='deriva de escala da odometria, em %%%% (padrao %.1f)'
                         % DERIVA_PCT)
    ap.add_argument('--espera', type=float, default=ESPERA_S,
                    help='espera pedida ao no Wait, em s (padrao %.1f)' % ESPERA_S)
    ap.add_argument('--limiar', type=float, default=LIMIAR_OBSTACULO,
                    help='portao de obstaculo, em m (padrao %.2f -- e o do TP4)'
                         % LIMIAR_OBSTACULO)
    ap.add_argument('--sem-eventos', action='store_true', dest='sem_eventos',
                    help='sessao sem nenhum obstaculo, para conferir a regua')
    ap.add_argument('--como-vigia-real', action='store_true',
                    dest='como_vigia_real',
                    help='coluna estado como o vigia real grava: so navegando '
                         'e esperando (interrompido e retomando duram ms)')
    a = ap.parse_args()

    registros, resumo = simular(
        semente=a.semente, deriva_pct=a.deriva, espera_s=a.espera,
        limiar=a.limiar, com_eventos=not a.sem_eventos,
        como_vigia_real=a.como_vigia_real)
    imprimir_resumo(resumo)
    print('csv           : %s  (%d linhas, %d colunas)'
          % (gravar_csv(a.saida, registros), len(registros), len(CAMPOS_CSV)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
