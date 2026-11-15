#!/usr/bin/env python3
"""A REGUA: a mesma medida para qualquer controlador -- PID, BC ou uma constante.

    PY="$PB_DIR/.venv-metadrive/bin/python"
    $PY avaliar.py --controlador pid --saida resultados/pid
    $PY avaliar.py --controlador constante --direcao 0.0 --saida resultados/constante
    xvfb-run -a -s "-screen 0 1280x1024x24" $PY avaliar.py --controlador bc \
        --modelo modelo/pesos.npz --saida resultados/bc            # (sem xvfb no WSLg)

Roda N episodios (10) com sementes FIXAS (100 a 109), no MESMO mapa e na
mesma configuracao, e mede por episodio:

    concluiu      1 se o MetaDrive disse arrive_dest no ultimo passo
    colidiu       1 se bateu: crash_vehicle, crash_object, crash_building ou
                  crash_human. NAO inclui sair da pista (coluna propria)
    saiu_da_pista 1 se o MetaDrive disse out_of_road: fora de qualquer faixa,
                  OU sobre a linha continua (amarela ou branca da borda), OU
                  na calcada -- e a regra de _is_out_of_road() do
                  metadrive_env.py, com on_continuous_line_done=True (padrao)
    vel_media     media de carro.speed_km_h em todos os passos, em km/h
    passos        passos de 0,1 s simulados ate o fim
    recompensa    soma da recompensa do MetaDrive (aprox. metros andados na
                  rota + 0,1 x fracao da velocidade maxima; +10 ao chegar,
                  -5 ao sair ou bater)
    fracao_rota   info['route_completion'] no ultimo passo (0 a 1; ~0,99 ao chegar)
    erro_lat_medio_m, erro_lat_max_m   |desvio| do centro da faixa de
                  referencia (a do pid.py), medido do ESTADO, para os dois
    var_direcao   media de |direcao(t) - direcao(t-1)|: o volante batendo de
                  um lado para o outro. O carro pode chegar com o volante em
                  serra -- e essa serra vira o rotulo do dataset
    motivo        a primeira chave verdadeira entre arrive_dest, crash_*,
                  out_of_road e max_step
    tempo_parede_s

Um episodio termina no primeiro desses eventos (o MetaDrive encerra em
qualquer batida ou saida) ou em HORIZONTE passos.

SEM TRAFEGO, de proposito: traffic_density = 0 e accident_prob = 0. O que se
compara e a DIRECAO -- os dois controladores usam o mesmo acelerador
proporcional, que nao freia para o carro da frente. Com trafego, a coluna
`colidiu` mediria a falta de um controle longitudinal, que nenhum dos dois
tem, e nao a direcao. --trafego existe para quem quiser ver isso acontecer.
Por isso `colidiu` deve dar 0 aqui; ela fica na tabela porque o enunciado a
pede e porque com --trafego ela deixa de ser zero.
"""
import argparse
import csv
import math
import os
import pathlib
import sys
import time

import pid as piloto_pid

# ------------------------------------------------------------------------------
# O CENARIO -- o mesmo para coletar, treinar e medir. Mude aqui, e so aqui.
# ------------------------------------------------------------------------------
# S reta, C curva (raio e angulo sorteados pela semente). Sem cruzamento: no
# cruzamento a rota escolhe virar ou seguir, e uma camera sozinha nao sabe qual
# das duas a rota quer -- o BC precisaria de um comando de navegacao a mais.
MAPA = 'SCSCS'
FAIXAS = 3                       # o padrao do MetaDrive; o carro nasce na do meio
SEMENTES_AVALIACAO = 100         # avaliar usa 100..109; coletar.py usa 0, 1, 2...
TRAFEGO = 0.0
HORIZONTE = 1000                 # passos (100 s simulados); a rota leva 334 a 611
CAMERA = (160, 120)              # largura x altura da camera do BC (e do dataset)
# O EMPURRAO (--empurrao V): do passo 40 ao 49 (4 a 5 s, ainda na primeira
# reta) o volante e FORCADO a V, qualquer que seja o controlador. Com V = 0,06
# o PID sai 1,4 m do centro e volta -- e nenhum quadro do dataset do PID esta
# a mais de 0,47 m do centro. Mede se o controlador sabe VOLTAR.
EMPURRAO_INICIO, EMPURRAO_PASSOS = 40, 10

COLUNAS = ['episodio', 'semente', 'concluiu', 'colidiu', 'vel_media', 'passos',
           'recompensa', 'fracao_rota', 'saiu_da_pista', 'motivo',
           'erro_lat_medio_m', 'erro_lat_max_m', 'var_direcao', 'tempo_parede_s']

BATIDAS = ('crash_vehicle', 'crash_object', 'crash_building', 'crash_human')


def config_cenario(semente_inicial, n_cenarios, camera=None, trafego=TRAFEGO, **extra):
    """O dicionario de configuracao do MetaDriveEnv. camera=(L, A) liga a imagem."""
    cfg = dict(
        use_render=False,
        map=MAPA,
        map_config=dict(lane_num=FAIXAS),
        start_seed=semente_inicial,
        num_scenarios=n_cenarios,       # reset(seed=) so aceita [start_seed, +n)
        traffic_density=trafego,
        accident_prob=0.0,
        random_spawn_lane_index=False,  # sempre a mesma faixa de partida...
        agent_configs={'default_agent': dict(
            spawn_lane_index=('>', '>>', piloto_pid.FAIXA_ALVO))},  # ...a do meio
        horizon=HORIZONTE,
        log_level=50,
    )
    if camera:
        from metadrive.component.sensors.rgb_camera import RGBCamera
        largura, altura = camera
        cfg.update(
            image_observation=True,     # obs = {"image": (A, L, 3, 1), "state": ...}
            norm_pixel=False,           # uint8 0..255
            stack_size=1,
            sensors={'rgb_camera': (RGBCamera, largura, altura)},
            vehicle_config={'image_source': 'rgb_camera'},
            interface_panel=[],
            window_size=(largura, altura),
        )
    cfg.update(extra)
    return cfg


def exigir_tela():
    """O MetaDrive 0.4.3 so abre o buffer da camera com um servidor X."""
    if os.environ.get('DISPLAY'):
        return
    sys.exit('ERRO: nao ha DISPLAY, e este controlador precisa da camera. No WSL2,\n'
             'confira o WSLg (echo $DISPLAY deve dar :0). Sem X, rode por baixo do Xvfb:\n'
             '  xvfb-run -a -s "-screen 0 1280x1024x24" ' + ' '.join(sys.argv))


def motivo(info):
    for chave in ('arrive_dest',) + BATIDAS + ('out_of_road', 'max_step'):
        if info.get(chave):
            return chave
    return 'desconhecido'


def rodar(controlador, episodios=10, semente_inicial=SEMENTES_AVALIACAO,
          vel_alvo=piloto_pid.VEL_ALVO_KMH, trafego=TRAFEGO, falar=True, horizonte=HORIZONTE,
          empurrao=0.0, parcial=None, trajetoria=None):
    """Roda os episodios e devolve uma lista de dicionarios, um por episodio."""
    from metadrive.envs.metadrive_env import MetaDriveEnv
    camera = CAMERA if controlador.precisa_imagem else None
    if camera:
        exigir_tela()
    env = MetaDriveEnv(config_cenario(semente_inicial, episodios, camera, trafego,
                                      horizon=horizonte))
    linhas, passos = [], []
    try:
        for ep in range(episodios):
            semente = semente_inicial + ep
            obs, info = env.reset(seed=semente)
            controlador.reiniciar()
            carro = env.agent
            t0 = time.time()
            n, soma_r, soma_v, soma_e, max_e = 0, 0.0, 0.0, 0.0, 0.0
            soma_dd, anterior = 0.0, None
            while True:
                acao = controlador.agir(env, obs)
                if empurrao and EMPURRAO_INICIO <= n < EMPURRAO_INICIO + EMPURRAO_PASSOS:
                    acao = [empurrao, acao[1]]
                if anterior is not None:
                    soma_dd += abs(acao[0] - anterior)
                anterior = acao[0]
                obs, r, term, trunc, info = env.step(acao)
                n += 1
                soma_r += r
                soma_v += carro.speed_km_h
                desvio, rumo = piloto_pid.erros_da_faixa(carro)
                if trajetoria:
                    passos.append((ep, semente, n, round(desvio, 3), round(rumo, 4),
                                   round(acao[0], 4), round(carro.speed_km_h, 1)))
                soma_e += abs(desvio)
                max_e = max(max_e, abs(desvio))
                if falar and n % 100 == 0 and controlador.precisa_imagem:
                    print('    ep %d passo %d (%.1f passos/s)' % (ep, n, n / (time.time() - t0)),
                          flush=True)
                if term or trunc:
                    break
            linha = dict(
                episodio=ep, semente=semente,
                concluiu=int(bool(info.get('arrive_dest'))),
                colidiu=int(any(info.get(k) for k in BATIDAS)),
                vel_media=round(soma_v / n, 2), passos=n, recompensa=round(soma_r, 2),
                fracao_rota=round(float(info.get('route_completion', 0.0)), 3),
                saiu_da_pista=int(bool(info.get('out_of_road'))),
                motivo=motivo(info),
                erro_lat_medio_m=round(soma_e / n, 3), erro_lat_max_m=round(max_e, 3),
                var_direcao=round(soma_dd / max(1, n - 1), 4),
                tempo_parede_s=round(time.time() - t0, 1))
            linhas.append(linha)
            if parcial:      # um episodio com camera leva minutos: grava a cada um
                gravar_csv(linhas, parcial)
            if trajetoria:
                with open(trajetoria, 'w', newline='') as f:
                    w = csv.writer(f, lineterminator='\n')
                    w.writerow(('episodio', 'semente', 'passo', 'desvio_m', 'rumo_rad',
                                'direcao', 'vel_kmh'))
                    w.writerows(passos)
            if falar:
                print('  ep %2d semente %d: %-12s passos %4d  rota %.3f  vel %5.1f km/h  '
                      'erro lat medio %.2f m  (%.1f s)'
                      % (ep, semente, linha['motivo'], n, linha['fracao_rota'],
                         linha['vel_media'], linha['erro_lat_medio_m'],
                         linha['tempo_parede_s']), flush=True)
    finally:
        env.close()
    return linhas


def media_desvio(valores):
    """(media, desvio-padrao AMOSTRAL); desvio 0 com um valor so."""
    n = len(valores)
    m = sum(valores) / n
    if n < 2:
        return m, 0.0
    return m, math.sqrt(sum((v - m) ** 2 for v in valores) / (n - 1))


def texto_resumo(linhas, nome):
    """A tabela de resumo em Markdown: contagens e media +- desvio."""
    n = len(linhas)
    t = ['**%s** -- %d episodios, sementes %d a %d' % (
        nome, n, linhas[0]['semente'], linhas[-1]['semente']), '',
        '| medida | valor |', '|---|---|']
    for col in ('concluiu', 'colidiu', 'saiu_da_pista'):
        k = sum(x[col] for x in linhas)
        t.append('| %s | %d de %d |' % (col, k, n))
    for col, fmt in (('vel_media', '%.1f'), ('passos', '%.0f'), ('recompensa', '%.1f'),
                     ('fracao_rota', '%.3f'), ('erro_lat_medio_m', '%.3f'),
                     ('erro_lat_max_m', '%.3f'), ('var_direcao', '%.3f')):
        m, s = media_desvio([float(x[col]) for x in linhas])
        t.append(('| %s | ' + fmt + ' +- ' + fmt + ' |') % (col, m, s))
    t.append('')
    t.append('media +- desvio-padrao amostral (n-1) sobre os episodios')
    return '\n'.join(t)


def cabecalho_curto():
    return ('%-36s %8s %6s %6s %13s %12s %14s %8s'
            % ('controlador', 'concluiu', 'saiu', 'bateu', 'vel km/h', 'rota', 'erro lat m',
               'var dir'))


def linha_curta(nome, linhas):
    n = len(linhas)
    v = media_desvio([x['vel_media'] for x in linhas])
    r = media_desvio([x['fracao_rota'] for x in linhas])
    e = media_desvio([x['erro_lat_medio_m'] for x in linhas])
    dd = media_desvio([x['var_direcao'] for x in linhas])
    return ('%-36s %4d/%-3d %3d/%-2d %3d/%-2d %5.1f +- %4.1f %5.3f+-%5.3f %6.3f+-%6.3f %8.3f'
            % (nome[:36], sum(x['concluiu'] for x in linhas), n,
               sum(x['saiu_da_pista'] for x in linhas), n, sum(x['colidiu'] for x in linhas), n,
               v[0], v[1], r[0], r[1], e[0], e[1], dd[0]))


def gravar_csv(linhas, caminho):
    caminho = pathlib.Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator='\n')
        w.writeheader()
        w.writerows(linhas)


def gravar(linhas, base, resumo):
    """BASE.csv (um episodio por linha) e BASE-resumo.md."""
    gravar_csv(linhas, str(base) + '.csv')
    pathlib.Path(str(base) + '-resumo.md').write_text(resumo + '\n')
    print('gravei %s.csv e %s-resumo.md' % (base, base))


class Constante:
    """A linha de base mais burra: volante parado num valor so (a media do dataset)."""

    precisa_imagem = False

    def __init__(self, direcao, vel_alvo):
        self.d, self.vel_alvo = direcao, vel_alvo
        self.nome = 'constante direcao=%g' % direcao

    def reiniciar(self):
        pass

    def agir(self, env, obs):
        return [self.d, piloto_pid.acelerador(env.agent.speed_km_h, self.vel_alvo)]


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--controlador', choices=('pid', 'bc', 'constante'), default='pid')
    p.add_argument('--episodios', type=int, default=10, help='(10)')
    p.add_argument('--semente-inicial', type=int, default=SEMENTES_AVALIACAO,
                   help='(%d) -- a mesma para todos os controladores' % SEMENTES_AVALIACAO)
    p.add_argument('--vel', type=float, default=piloto_pid.VEL_ALVO_KMH,
                   help='velocidade-alvo km/h (%g)' % piloto_pid.VEL_ALVO_KMH)
    p.add_argument('--trafego', type=float, default=TRAFEGO, help='(%g) -- leia o topo' % TRAFEGO)
    p.add_argument('--modelo', help='bc: o pesos.npz que o treinar_bc.py exporta')
    p.add_argument('--direcao', type=float, default=0.0, help='constante: o valor (0.0)')
    p.add_argument('--inverter-canais', action='store_true',
                   help='bc: entrega RGB a uma rede treinada em BGR (a armadilha)')
    p.add_argument('--sem-normalizar', action='store_true',
                   help='bc: esquece o /255 que o treino fez (a outra armadilha)')
    p.add_argument('--empurrao', type=float, default=0.0,
                   help='forca o volante a este valor do passo %d ao %d (0 = nao)'
                   % (EMPURRAO_INICIO, EMPURRAO_INICIO + EMPURRAO_PASSOS - 1))
    p.add_argument('--trajetoria', help='grava um CSV com o desvio e a direcao de CADA passo')
    p.add_argument('--horizonte', type=int, default=HORIZONTE,
                   help='passos maximos por episodio (%d)' % HORIZONTE)
    p.add_argument('--saida', help='grava SAIDA.csv e SAIDA-resumo.md')
    args = p.parse_args(argv)

    if args.controlador == 'pid':
        ctl = piloto_pid.PilotoPID(vel_alvo=args.vel)
    elif args.controlador == 'constante':
        ctl = Constante(args.direcao, args.vel)
    else:
        if not args.modelo:
            p.error('--controlador bc pede --modelo CAMINHO/pesos.npz')
        import dirigir_bc
        ctl = dirigir_bc.PilotoBC(args.modelo, args.vel, args.inverter_canais,
                                  args.sem_normalizar)
    try:
        import metadrive  # noqa: F401
    except ImportError:
        sys.exit('ERRO: metadrive nao instalado neste Python (%s).\n'
                 'Rode com o do venv: "$PB_DIR/.venv-metadrive/bin/python"' % sys.executable)
    linhas = rodar(ctl, args.episodios, args.semente_inicial, args.vel, args.trafego,
                   horizonte=args.horizonte, empurrao=args.empurrao,
                   parcial=(args.saida + '.csv') if args.saida else None,
                   trajetoria=args.trajetoria)
    texto = texto_resumo(linhas, '%s, alvo %g km/h, trafego %g%s' % (
        ctl.nome, args.vel, args.trafego,
        ', EMPURRAO %g nos passos %d-%d' % (args.empurrao, EMPURRAO_INICIO,
                                            EMPURRAO_INICIO + EMPURRAO_PASSOS - 1)
        if args.empurrao else ''))
    print()
    print(texto)
    if getattr(ctl, 'ms', None):
        print('inferencia da rede (NumPy): %.1f ms por quadro, media de %d quadros'
              % (sum(ctl.ms) / len(ctl.ms), len(ctl.ms)))
    if args.saida:
        gravar(linhas, args.saida, texto)
    return 0


if __name__ == '__main__':
    sys.exit(principal())
