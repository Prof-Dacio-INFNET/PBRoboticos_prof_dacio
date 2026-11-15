#!/usr/bin/env python3
"""Grava o dataset do Behavioral Cloning: quadros da camera + a acao de direcao.

    PY="$PB_DIR/.venv-metadrive/bin/python"
    $PY coletar.py --piloto humano-terminal --quadros 1000 --saida dataset   # O DA ENTREGA
    $PY coletar.py --piloto humano-janela   --quadros 1000 --saida dataset   # idem, WASD na janela
    $PY coletar.py --piloto pid --quadros 1000 --saida dataset-pid           # o da AULA
    $PY coletar.py --piloto pid --ruido 0.2 --quadros 1000 --saida dataset-pid-ruido

O ENUNCIADO PEDE PILOTAGEM HUMANA. O modo `pid` existe para a aula mostrar a
mecanica (e para este exemplo ser verificavel numa maquina sem teclado nem
tela); o dataset que vai para a entrega e o de um dos modos `humano-*`.

Escreve, em --saida:

    quadro00000.png ...    a camera do carro, 160x120, BGR (como o MetaDrive entrega)
    acoes.csv              uma linha por quadro, com as colunas abaixo

    indice, arquivo, episodio, semente, passo
    direcao            o ROTULO: a direcao que o piloto QUIS dar naquele quadro
    direcao_aplicada   a que foi de fato aplicada ao carro (difere de `direcao`
                       so com --ruido)
    acelerador         o que foi aplicado
    desvio_m, rumo_rad, vel_kmh   o estado (pid.erros_da_faixa), para conferencia
    piloto

O par e (quadro ANTES do passo, acao daquele passo): a imagem que o piloto
via quando decidiu. Gravar a imagem DEPOIS do passo desalinha tudo de um quadro.

OS PILOTOS
  pid              o pid.py dirige. Sem ruido, ele nunca sai do centro -- e o
                   dataset nunca mostra como voltar para ele (leia o README).
  pid --ruido S    o carro recebe direcao = pid + perturbacao (um passeio
                   aleatorio que volta a zero, de escala S), mas o ROTULO
                   gravado e o que o PID mandaria. O dataset passa a ter
                   quadros fora do centro com a correcao certa.
  humano-terminal  voce dirige pelas teclas do TERMINAL de onde rodou o script
                   (o foco tem de estar nele); a janela do MetaDrive so mostra.
                       a / seta esq.   volante +0,02 para a esquerda
                       d / seta dir.   volante +0,02 para a direita
                       s / espaco      volante no centro
                       w / x           velocidade-alvo +5 / -5 km/h
                       q / Ctrl+C      grava e sai
                   O acelerador e o mesmo controle do pid.py: voce so dirige.
  humano-janela    o teclado do PROPRIO MetaDrive (manual_control=True): W A S D
                   com o foco na janela dele. Grava info['steering'], o volante
                   que o MetaDrive aplicou. NAO VERIFICADO (leia o README).

Os episodios usam as sementes 0, 1, 2... (a regua usa 100 a 109: o BC e medido
em estradas que ele nunca viu).
"""
import argparse
import csv
import os
import pathlib
import random
import sys
import time

import avaliar
import pid as piloto_pid

COLUNAS = ['indice', 'arquivo', 'episodio', 'semente', 'passo', 'direcao',
           'direcao_aplicada', 'acelerador', 'desvio_m', 'rumo_rad', 'vel_kmh', 'piloto']

PASSO_VOLANTE = 0.02     # cada toque de a/d: a curva deste mapa pede 0,06 a 0,08
PASSO_VEL = 5.0          # cada toque de w/x
RUIDO_THETA = 0.1        # quanto a perturbacao volta para zero por passo (0..1)
JANELA = (480, 360)      # a janela que o humano ve (a camera gravada continua 160x120)


class Teclado:
    """Le teclas do terminal sem esperar Enter (termios), sem bloquear (select).

    Fora de um terminal (stdin redirecionado) ou no Windows, nao le nada.
    """

    def __init__(self):
        self.fd, self.antigo, self.resto = None, None, b''

    def __enter__(self):
        try:
            import termios
        except ImportError:
            return self
        if not sys.stdin.isatty():
            return self
        self.fd = sys.stdin.fileno()
        self.antigo = termios.tcgetattr(self.fd)
        novo = termios.tcgetattr(self.fd)
        novo[3] &= ~(termios.ICANON | termios.ECHO)
        novo[6][termios.VMIN], novo[6][termios.VTIME] = 1, 0
        termios.tcsetattr(self.fd, termios.TCSANOW, novo)
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.antigo)

    def ler(self):
        """Lista de simbolos das teclas que chegaram desde a ultima leitura."""
        if self.fd is None:
            return []
        import select
        dados = self.resto
        while select.select([self.fd], [], [], 0)[0]:
            bloco = os.read(self.fd, 64)
            if not bloco:
                break
            dados += bloco
        simbolos, self.resto = decodificar(dados)
        return simbolos


SETAS = {b'\x1b[D': 'esq', b'\x1b[C': 'dir', b'\x1bOD': 'esq', b'\x1bOC': 'dir',
         b'\x1b[A': 'mais', b'\x1b[B': 'menos'}
LETRAS = {b'a': 'esq', b'd': 'dir', b's': 'centro', b' ': 'centro', b'w': 'mais',
          b'x': 'menos', b'q': 'sai', b'\x03': 'sai'}


def decodificar(dados):
    """Bytes do terminal -> (simbolos, bytes de uma sequencia de escape incompleta)."""
    out, i = [], 0
    while i < len(dados):
        if dados[i:i + 1] == b'\x1b':
            seq = dados[i:i + 3]
            if len(seq) < 3:
                return out, dados[i:]          # o resto da seta chega na proxima leitura
            if seq in SETAS:
                out.append(SETAS[seq])
            i += 3
            continue
        c = dados[i:i + 1].lower()
        if c in LETRAS:
            out.append(LETRAS[c])
        i += 1
    return out, b''


def aplicar_teclas(simbolos, volante, vel_alvo):
    """(volante, vel_alvo, sair) depois das teclas. Volante +1 = esquerda."""
    sair = False
    for s in simbolos:
        if s == 'esq':
            volante += PASSO_VOLANTE
        elif s == 'dir':
            volante -= PASSO_VOLANTE
        elif s == 'centro':
            volante = 0.0
        elif s == 'mais':
            vel_alvo += PASSO_VEL
        elif s == 'menos':
            vel_alvo = max(0.0, vel_alvo - PASSO_VEL)
        elif s == 'sai':
            sair = True
    return max(-1.0, min(1.0, round(volante, 3))), vel_alvo, sair


class Perturbacao:
    """Passeio aleatorio que volta a zero (Ornstein-Uhlenbeck discreto).

    Ruido branco a 10 Hz o carro filtra e quase nao sai do centro; este anda
    para um lado por alguns segundos e volta, como um motorista distraido.
    """

    def __init__(self, escala, semente):
        self.escala, self.x = escala, 0.0
        self.rng = random.Random(semente)

    def __call__(self):
        self.x += -RUIDO_THETA * self.x + self.escala * 0.45 * self.rng.gauss(0.0, 1.0)
        return self.x


def coletar(args):
    import cv2
    from metadrive.envs.metadrive_env import MetaDriveEnv

    humano = args.piloto.startswith('humano')
    extra = {}
    if humano:
        extra.update(use_render=True, window_size=JANELA, interface_panel=['dashboard'])
    if args.piloto == 'humano-janela':
        extra.update(manual_control=True, controller='keyboard')
    saida = pathlib.Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    n_ep_max = 1000
    cfg = avaliar.config_cenario(args.semente_inicial, n_ep_max, avaliar.CAMERA, **extra)
    env = MetaDriveEnv(cfg)
    pid = piloto_pid.PilotoPID(vel_alvo=args.vel)
    gravados, ep, t0, passos_total = 0, 0, time.time(), 0
    vel_alvo = args.vel
    sair = False
    caminho_csv = saida / 'acoes.csv'
    with open(caminho_csv, 'w', newline='') as arq, Teclado() as teclado:
        w = csv.writer(arq, lineterminator='\n')
        w.writerow(COLUNAS)
        while gravados < args.quadros and not sair:
            semente = args.semente_inicial + ep
            obs, info = env.reset(seed=semente)
            pid.reiniciar()
            pert = Perturbacao(args.ruido, semente)
            carro = env.agent
            volante, passo, no_ep = 0.0, 0, 0
            while True:
                t_passo = time.time()
                quadro = obs['image'][..., -1]           # BGR, a imagem ANTES da acao
                desvio, rumo = piloto_pid.erros_da_faixa(carro)
                if args.piloto == 'pid':
                    rotulo = pid.direcao(carro)
                    aplicada = max(-1.0, min(1.0, rotulo + (pert() if args.ruido else 0.0)))
                    acel = piloto_pid.acelerador(carro.speed_km_h, vel_alvo)
                elif args.piloto == 'humano-terminal':
                    volante, vel_alvo, sair = aplicar_teclas(teclado.ler(), volante, vel_alvo)
                    rotulo = aplicada = volante
                    acel = piloto_pid.acelerador(carro.speed_km_h, vel_alvo)
                else:
                    rotulo = aplicada = acel = None     # o MetaDrive le o teclado no step
                obs, _, term, trunc, info = env.step([aplicada or 0.0, acel or 0.0])
                if rotulo is None:                      # humano-janela: o que foi aplicado
                    rotulo = aplicada = float(info.get('steering', 0.0))
                    acel = float(info.get('acceleration', 0.0))
                if passo % args.passo == 0:
                    nome = 'quadro%05d.png' % gravados
                    cv2.imwrite(str(saida / nome), quadro)
                    w.writerow([gravados, nome, ep, semente, passo, '%.4f' % rotulo,
                                '%.4f' % aplicada, '%.3f' % acel, '%.3f' % desvio,
                                '%.4f' % rumo, '%.1f' % carro.speed_km_h, args.piloto])
                    gravados += 1
                    no_ep += 1
                passo += 1
                passos_total += 1
                if humano and gravados % 20 == 0:
                    print('\r  quadros %4d  volante %+.2f  alvo %3.0f km/h  vel %5.1f  '
                          'desvio %+.2f m '
                          % (gravados, rotulo, vel_alvo, carro.speed_km_h, desvio), end='',
                          flush=True)
                if args.tempo_real:                     # nao mais rapido que 0,1 s por passo
                    folga = piloto_pid.DT_S - (time.time() - t_passo)
                    if folga > 0:
                        time.sleep(folga)
                if (term or trunc or sair or gravados >= args.quadros
                        or (args.max_por_episodio and no_ep >= args.max_por_episodio)):
                    break
            fim = avaliar.motivo(info) if (term or trunc) else 'corte'
            print('%sepisodio %d (semente %d): %d quadros, %d passos, fim: %s'
                  % ('\n' if humano else '', ep, semente, no_ep, passo, fim), flush=True)
            ep += 1
    env.close()
    gasto = time.time() - t0
    print('quadros gravados: %d em %s (+ acoes.csv), %d episodios' % (gravados, saida, ep))
    print('tempo de parede : %.0f s -> %.2f quadros/s, %.2f passos/s'
          % (gasto, gravados / gasto, passos_total / gasto))
    return gravados


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--piloto', required=True,
                   choices=('humano-terminal', 'humano-janela', 'pid'))
    p.add_argument('--quadros', type=int, default=1000, help='(1000)')
    p.add_argument('--saida', default='dataset', help='(dataset)')
    p.add_argument('--passo', type=int, default=2,
                   help='grava 1 quadro a cada N passos de 0,1 s (2): vizinhos a 0,1 s sao '
                   'quase iguais')
    p.add_argument('--semente-inicial', type=int, default=0, help='(0)')
    p.add_argument('--max-por-episodio', type=int, default=0,
                   help='corta o episodio depois de N quadros (0 = ate o fim)')
    p.add_argument('--vel', type=float, default=piloto_pid.VEL_ALVO_KMH,
                   help='velocidade-alvo km/h (%g)' % piloto_pid.VEL_ALVO_KMH)
    p.add_argument('--ruido', type=float, default=0.0,
                   help='so --piloto pid: escala da perturbacao aplicada (0 = sem)')
    p.add_argument('--tempo-real', action='store_true',
                   help='segura cada passo em >= 0,1 s (o padrao nos modos humano-*)')
    args = p.parse_args(argv)
    if args.ruido and args.piloto != 'pid':
        p.error('--ruido so vale com --piloto pid')
    if args.piloto.startswith('humano'):
        args.tempo_real = True
        if args.piloto == 'humano-terminal' and not sys.stdin.isatty():
            p.error('humano-terminal precisa de um terminal (stdin nao e um tty)')
    if not os.environ.get('DISPLAY'):
        sys.exit('ERRO: nao ha DISPLAY. O MetaDrive 0.4.3 precisa de um servidor X para a\n'
                 'camera. No WSL2, confira o WSLg (echo $DISPLAY deve dar :0). Sem X:\n'
                 '  xvfb-run -a -s "-screen 0 1280x1024x24" ' + ' '.join(sys.argv))
    try:
        import metadrive  # noqa: F401
    except ImportError:
        sys.exit('ERRO: metadrive nao instalado neste Python (%s).\n'
                 'Rode com o do venv: "$PB_DIR/.venv-metadrive/bin/python"' % sys.executable)
    return 0 if coletar(args) == args.quadros else 1


if __name__ == '__main__':
    sys.exit(principal())
