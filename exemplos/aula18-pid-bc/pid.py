#!/usr/bin/env python3
"""O controlador PID de direcao (simple-pid) que mantem o carro no centro da faixa.

    PY="$PB_DIR/.venv-metadrive/bin/python"
    $PY pid.py                                   # os ganhos do topo, 10 episodios
    $PY pid.py --kp 0.05 0.5 3                   # varre o Kp: lento x agressivo
    $PY pid.py --kp 0.2 0.5 1 --olhar 0          # sem o termo de rumo: oscila e sai
    $PY pid.py --kd 0 0.1 0.3                    # o Kd que serrilha o volante
    $PY pid.py --vel 40 60 80                    # a velocidade em que o ganho deixa de servir
    $PY pid.py --sem-dt                          # a armadilha do relogio do simple-pid

O PID NAO OLHA A IMAGEM. Ele le o ESTADO do simulador -- onde o carro esta em
relacao a faixa -- e e por isso que ele e a linha de base: e o que um
controlador classico faz quando a percepcao e perfeita. A rede do
Behavioral Cloning so tem a imagem.

DE ONDE VEM CADA NUMERO (MetaDrive 0.4.3, conferido no codigo instalado):

    carro.navigation.current_ref_lanes   as faixas da via em que a ROTA esta
                                         agora (lista; 3 faixas neste mapa)
    faixa.local_coordinates(posicao)     (longitudinal, lateral) do carro no
                                         referencial da faixa, em metros;
                                         lateral > 0 e o carro A DIREITA do
                                         centro (medido: direcao +0,3 leva a
                                         lateral para negativo)
    faixa.heading_theta_at(longitudinal) o rumo da faixa naquele ponto (rad)
    carro.heading_theta                  o rumo do carro (rad, anti-horario)
    carro.speed_km_h                     a velocidade (km/h)

E o mesmo caminho que o IDMPolicy do proprio MetaDrive usa no
steering_control() (policy/idm_policy.py), com dois PID somados; aqui e um
PID so, sobre um erro que junta os dois:

    desvio  = -lateral                   m, positivo = carro a ESQUERDA do centro
    rumo    = rumo_carro - rumo_faixa    rad, positivo = apontando para a esquerda
    medida  = desvio + OLHAR_M * sin(rumo)

`medida` e onde o carro estara, de lado, daqui a OLHAR_M metros se nao
virar: o desvio de um ponto a frente. Sem o termo de rumo (--olhar 0), o PID
so ve o desvio de agora e descobre que passou do centro tarde demais -- e
oscila. A acao do MetaDrive e [direcao, acelerador], as duas em [-1, 1];
direcao +1 e o volante todo para a ESQUERDA (40 graus nas rodas).

O ACELERADOR nao e o assunto: e um controle proporcional simples para manter
a velocidade-alvo, o MESMO para o PID e para o BC. Assim a comparacao mede so
a direcao.
"""
import argparse
import math
import sys

# ------------------------------------------------------------------------------
# GANHOS -- declarados antes de medir, com o porque.
# ------------------------------------------------------------------------------
# Kp: 1 m de erro a frente pede 0,5 de volante (20 graus nas rodas). A
# varredura do README mostra o lento (Kp pequeno) e o agressivo (Kp grande).
KP = 0.5
# Ki: zero. Neste mapa nao ha vento nem inclinacao lateral para o integral
# corrigir, e o termo de rumo (OLHAR_M) ja tira o erro de regime da curva. O
# integral so acrescentaria sobressinal. Para ver: --ki 0.1.
KI = 0.0
# Kd: ZERO, e esta e a decisao que mais custou. O termo de rumo (OLHAR_M) ja
# e o amortecimento: ele enxerga o carro virando antes do desvio crescer. Com
# Kd = 0,3 os 10 episodios concluem igual, mas o volante passa a bater de um
# lado para o outro a cada passo (variacao media de 0,40 por passo, contra
# 0,01 com Kd = 0): a derivada da medida a 0,1 s amplifica a propria resposta
# do carro. A regua nao acusa -- o carro chega --, mas o ROTULO do dataset vira
# serra, e a rede do BC so aprende a media. Para ver: --kd 0.3.
KD = 0.0
# Distancia do ponto a frente, em metros. 5 m e uns 0,45 s a 40 km/h.
OLHAR_M = 5.0
# Velocidade-alvo e o ganho do acelerador (proporcional): 10 km/h abaixo do
# alvo pede acelerador 1,0. Com isso a media fica uns 6 km/h abaixo do alvo:
# o episodio comeca parado, e o proporcional puro tem erro de regime.
VEL_ALVO_KMH = 40.0
K_VEL = 0.1
# Passo de controle do MetaDrive: physics_world_step_size 0,02 s x
# decision_repeat 5 = 0,1 s simulado por env.step(). E esse dt que o PID
# precisa receber -- nao o tempo do relogio (veja --sem-dt).
DT_S = 0.1
# A faixa que o PID segue: 0, 1 ou 2 das 3 do mapa. A do meio, onde o carro nasce.
FAIXA_ALVO = 1


def ajustar_angulo(a):
    """Leva um angulo para (-pi, pi]: a diferenca entre 179 e -179 graus e 2 graus."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def faixa_de_referencia(carro, indice=FAIXA_ALVO):
    """A faixa da ROTA em que o carro deveria estar (a de indice FAIXA_ALVO)."""
    faixas = carro.navigation.current_ref_lanes
    return faixas[min(indice, len(faixas) - 1)]


def erros_da_faixa(carro, indice=FAIXA_ALVO):
    """(desvio_m, rumo_rad) do carro em relacao a faixa de referencia.

    desvio > 0: o carro esta a esquerda do centro; rumo > 0: aponta para a
    esquerda da faixa. As duas medidas saem do estado do simulador, nao da
    imagem.
    """
    faixa = faixa_de_referencia(carro, indice)
    lon, lat = faixa.local_coordinates(carro.position)
    rumo = ajustar_angulo(carro.heading_theta - faixa.heading_theta_at(lon))
    return -float(lat), float(rumo)


def medida_a_frente(desvio, rumo, olhar=OLHAR_M):
    """O desvio de um ponto OLHAR metros a frente, se o carro seguir reto."""
    return desvio + olhar * math.sin(rumo)


def acelerador(vel_kmh, alvo_kmh=VEL_ALVO_KMH, k=K_VEL):
    """Proporcional, saturado em [-1, 1]. Negativo e freio."""
    return max(-1.0, min(1.0, k * (alvo_kmh - vel_kmh)))


class PilotoPID:
    """O controlador. Interface comum da regua (avaliar.py):

        reiniciar()          no comeco de cada episodio
        agir(env, obs)  ->   [direcao, acelerador]

    precisa_imagem = False: a regua nao liga a camera para ele.
    """

    precisa_imagem = False

    def __init__(self, kp=KP, ki=KI, kd=KD, olhar=OLHAR_M, vel_alvo=VEL_ALVO_KMH,
                 com_dt=True):
        from simple_pid import PID  # aqui: o testar.py importa este arquivo sem o simple-pid
        self.olhar = olhar
        self.vel_alvo = vel_alvo
        self.com_dt = com_dt
        self.nome = 'pid kp=%g ki=%g kd=%g olhar=%g' % (kp, ki, kd, olhar)
        # setpoint 0: o alvo e desvio zero. output_limits: o volante do MetaDrive.
        # sample_time: o padrao (0,01 s) e de RELOGIO DE PAREDE -- so pesa sem dt=.
        self.pid = PID(kp, ki, kd, setpoint=0.0, output_limits=(-1.0, 1.0))
        self.ultima = (0.0, 0.0, 0.0)

    def reiniciar(self):
        # sem isto, o integral e a ultima medida do episodio anterior entram no novo
        self.pid.reset()

    def direcao(self, carro):
        desvio, rumo = erros_da_faixa(carro)
        medida = medida_a_frente(desvio, rumo, self.olhar)
        if self.com_dt:
            d = self.pid(medida, dt=DT_S)
        else:
            # A ARMADILHA: sem dt, o simple-pid usa time.monotonic(). Sem camera
            # o MetaDrive roda centenas de passos por segundo de parede, e cada
            # chamada chega antes do sample_time de 0,01 s -- o PID devolve a
            # saida ANTERIOR, congelada. Com camera, 1 passo por segundo de
            # parede vira dt = 1 s, e o derivativo fica 10x menor que o pensado.
            d = self.pid(medida)
        self.ultima = (desvio, rumo, d)
        return float(d)

    def agir(self, env, obs):
        carro = env.agent
        return [self.direcao(carro), acelerador(carro.speed_km_h, self.vel_alvo)]


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--kp', type=float, nargs='+', default=[KP], help='um ou varios (%g)' % KP)
    p.add_argument('--ki', type=float, default=KI, help='(%g)' % KI)
    p.add_argument('--kd', type=float, nargs='+', default=[KD], help='um ou varios (%g)' % KD)
    p.add_argument('--olhar', type=float, default=OLHAR_M,
                   help='metros do ponto a frente; 0 = so o desvio de agora (%g)' % OLHAR_M)
    p.add_argument('--vel', type=float, nargs='+', default=[VEL_ALVO_KMH],
                   help='velocidade-alvo em km/h, uma ou varias (%g)' % VEL_ALVO_KMH)
    p.add_argument('--sem-dt', action='store_true',
                   help='chama o PID sem dt= (relogio de parede): a armadilha')
    p.add_argument('--episodios', type=int, default=10, help='(10)')
    p.add_argument('--saida', default=None,
                   help='CSV por episodio (so com UM kp e UMA vel); grava tambem SAIDA-resumo.md')
    args = p.parse_args(argv)

    import avaliar
    combinacoes = [(kp, kd, v) for v in args.vel for kd in args.kd for kp in args.kp]
    varredura = len(combinacoes) > 1
    if varredura and args.saida:
        p.error('--saida so com um --kp, um --kd e uma --vel')
    resumos = []
    for kp, kd, vel in combinacoes:
        piloto = PilotoPID(kp, args.ki, kd, args.olhar, vel, com_dt=not args.sem_dt)
        linhas = avaliar.rodar(piloto, args.episodios, vel_alvo=vel, falar=not varredura)
        resumos.append((piloto.nome.replace('pid ', '') + ' v=%g' % vel, linhas))
        if not varredura:
            texto = avaliar.texto_resumo(linhas, piloto.nome + ', alvo %g km/h' % vel)
            print(texto)
            if args.saida:
                avaliar.gravar(linhas, args.saida, texto)
    if varredura:
        print(avaliar.cabecalho_curto())
        for nome, linhas in resumos:
            print(avaliar.linha_curta(nome, linhas))
    return 0


if __name__ == '__main__':
    sys.exit(principal())
