#!/usr/bin/env python3
"""Localizacao por filtro de particulas (MCL) sobre o mapa conhecido da Aula 11.

Sem ROS 2, sem Nav2, sem AMCL: numpy puro. Existe para trocar a frase "a nuvem
concentrou" -- que e' impressao -- por tres numeros que o aluno pode citar no
relatorio do TP4: a dispersao da nuvem, o N efetivo e o erro contra a verdade.

O mapa e' o `Mundo` da Aula 11, e aqui ele e' duas coisas ao mesmo tempo: o
mapa que o filtro conhece (o papel do mapa do TP3) e a VERDADE contra a qual
se mede. Num robo real essas duas coisas nao coexistem -- voce tem o mapa e
nao tem a verdade --, e e' exatamente por isso que, no RViz2, "a nuvem
concentrou" e' tudo o que da' para dizer. Aqui a verdade existe, e e' ela que
torna o gate G4.0 mensuravel.

As quatro pecas do MCL, cada uma com o nome do parametro do AMCL ao lado:

  amostragem inicial    espalhar_uniforme  localizacao global (sem palpite)
                        espalhar_ao_redor  o "2D Pose Estimate" do RViz2,
                                           que no Nav2 e' `set_initial_pose`
  modelo de movimento   Particulas.mover   alpha1..alpha4 do AMCL
  modelo de observacao  Mcl.pesar          `max_beams`, `laser_sigma_hit`,
                                           `z_hit`, `z_rand`
  reamostragem          Mcl.reamostrar     `resample_interval`

    python3 localizacao.py      # confere o lancamento de raios e sai
"""
import math
import os
import pathlib
import sys

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent


def achar_cenario() -> str:
    """Acha o pacote aula11_mundo, que e' o MAPA e e' a VERDADE desta aula.

    Mesma busca do `comparar_mapas.py` da Aula 12, pelo mesmo motivo: este
    script roda durante a semana, fora da aula, quando a copia do material em
    /tmp ja' sumiu no reboot. Procure em mais de um lugar e, se nao achar,
    diga o que fazer -- um ImportError de tres linhas nao ensina nada.
    """
    candidatos = [
        AQUI.parent / 'aula11-mundo' / 'aula11_mundo',   # rodando de dentro do material
        AQUI / 'src' / 'aula11_mundo',                   # copiado para a raiz do workspace
    ]
    if os.environ.get('PB_WS'):
        candidatos.append(pathlib.Path(os.environ['PB_WS']) / 'src' / 'aula11_mundo')
    for c in candidatos:
        if (c / 'aula11_mundo' / 'mapa.py').is_file():
            sys.path.insert(0, str(c))
            return str(c)
    try:                                                 # workspace sourceado
        import aula11_mundo.mapa                         # noqa: F401
        return 'pacote aula11_mundo instalado (workspace sourceado)'
    except ImportError:
        sys.exit(
            'nao achei o mapa (o pacote aula11_mundo). Ele e o mapa E a verdade:\n'
            'sem ele nao da para localizar nada nem medir nada. Tres saidas:\n'
            '  1) rode de dentro do material, onde aula11-mundo fica ao lado;\n'
            '  2) copie o pacote para a raiz do seu workspace, em src/aula11_mundo;\n'
            '  3) ou sourceie o workspace:  source "$PB_WS/install/setup.bash"')


ONDE_CENARIO = achar_cenario()
from aula11_mundo.mapa import Mundo                                   # noqa: E402

# ---------------------------------------------------------------- parametros

ALCANCE_MAX = 6.0          # m, o mesmo alcance do laser da Aula 11
PASSO_RAIO = 0.05          # m por amostra na marcha do raio (= 1 celula do mapa)

# Ruido do modelo de movimento. Sao os alpha1..alpha4 do AMCL, com o mesmo
# significado: quanto de incerteza cada parcela do deslocamento injeta.
ALFA_PADRAO = (0.20,       # alpha1: ruido de GIRO por radiano girado
               0.15,       # alpha2: ruido de GIRO por metro andado
               0.20,       # alpha3: ruido de AVANCO por metro andado
               0.05)       # alpha4: ruido de AVANCO por radiano girado

# Piso de ruido: depois de reamostrar, N particulas podem virar N copias
# IDENTICAS de uma so. O piso garante que a nuvem sempre tenha de onde
# recuperar. O AMCL nao tem este piso -- ele depende do movimento para
# espalhar, e e' por isso que um robo parado la' nunca melhora a estimativa.
PISO_RUIDO_TRANS = 0.006   # m
PISO_RUIDO_ROT = 0.004     # rad

# Expoente da verossimilhanca (a "tempera"). Os feixes NAO sao independentes:
# a parede que o feixe 7 ve e a mesma que o feixe 8 ve. Multiplicar 30
# gaussianas como se fossem 30 medidas independentes conta a mesma evidencia
# trinta vezes, e o efeito e' brutal -- com expoente 1,0 o N efetivo desta
# nuvem cai de 1200 para 1 no PRIMEIRO ciclo. Uma particula sobrevive, as
# outras 1199 sao copias dela, e o filtro deixou de ser Monte Carlo: virou um
# palpite com nuvem de enfeite.
#
# O AMCL nao tem este expoente, e e' por isso que ele e' mais confiante do que
# deveria. O jeito dele de conseguir o mesmo efeito e' indireto: menos feixes
# (`max_beams`) e `sigma_hit` maior. Aqui o parametro fica explicito para a
# aula poder mexer nele e ver o N efetivo responder.
EXPOENTE_PESO = 0.15

# ------------------------------------------------- criterio de CONVERGENCIA
# Declarado AQUI, antes de rodar qualquer coisa -- a disciplina da Aula 9.
# Convergiu = a nuvem esta concentrada E assim permanece. Um instante isolado
# de dispersao baixa nao e' convergencia, e' sorte.
LIMIAR_DISPERSAO = 0.30    # m, raio da nuvem = hypot(desvio_x, desvio_y)
LIMIAR_DISP_ANG = 15.0     # graus, desvio-padrao circular de theta
PASSOS_ESTAVEIS = 10       # atualizacoes seguidas abaixo dos DOIS limiares
LIMIAR_ACERTO = 0.50       # m, erro final que separa lugar certo de lugar errado


def normalizar(ang):
    """Traz o angulo para (-pi, pi]. Funciona em escalar e em array."""
    return np.arctan2(np.sin(ang), np.cos(ang))


def lancar_lote(mundo, poses, angulos, alcance_max=ALCANCE_MAX, passo=PASSO_RAIO,
                bloco=256):
    """Distancia ate a primeira parede, para MUITAS poses de uma vez. (N, B).

    E' o `Mundo.medir` da Aula 11 -- a mesma marcha amostrada, a mesma grade,
    o mesmo argmax pegando o primeiro True -- generalizado de uma pose para N.
    Tinha de ser vetorizado: pesar 1200 particulas com 30 feixes e' 1200
    chamadas de `medir` por ciclo, e o filtro deixaria de rodar em tempo de
    aula. O `testar.py` confere que as duas versoes concordam.

    `passo` e' 0,05 m aqui (uma celula do mapa) contra 0,02 m do `medir`: a
    leitura pode sair ate' um passo -- 5 cm -- acima da do `medir`, que e' um
    quarto do `sigma_z` do modelo de observacao, e portanto irrelevante para o
    peso. As paredes tem 20 cm, entao nenhum feixe atravessa parede por causa
    do passo maior. O grupo 1 do `testar.py` confere os dois limites.
    """
    poses = np.asarray(poses, dtype=np.float64).reshape(-1, 3)
    ang = np.asarray(angulos, dtype=np.float64).ravel()
    d = np.arange(passo, alcance_max + passo, passo)
    saida = np.empty((len(poses), len(ang)), dtype=np.float64)
    for ini in range(0, len(poses), bloco):
        p = poses[ini:ini + bloco]
        a = p[:, 2][:, None] + ang[None, :]                     # (n, B)
        xs = p[:, 0][:, None, None] + np.cos(a)[:, :, None] * d  # (n, B, D)
        ys = p[:, 1][:, None, None] + np.sin(a)[:, :, None] * d
        j = (xs / mundo.res).astype(np.int32)
        i = (ys / mundo.res).astype(np.int32)
        fora = (i < 0) | (i >= mundo.ny) | (j < 0) | (j >= mundo.nx)
        np.clip(i, 0, mundo.ny - 1, out=i)
        np.clip(j, 0, mundo.nx - 1, out=j)
        bateu = mundo.grade[i, j] | fora
        tem = bateu.any(axis=2)
        primeiro = bateu.argmax(axis=2)             # argmax pega o 1o True
        saida[ini:ini + bloco] = np.where(tem, d[primeiro], np.inf)
    return saida


class Particulas:
    """A nuvem: N poses (x, y, theta) e N pesos que somam 1.

    Uma particula e' uma hipotese inteira sobre onde o robo esta. A nuvem e' a
    distribuicao de probabilidade -- e e' por isso que ela pode ter duas
    manchas: duas hipoteses incompativeis e igualmente plausiveis, coisa que
    uma pose unica com covariancia nao sabe representar.
    """

    def __init__(self, poses, pesos=None):
        self.poses = np.asarray(poses, dtype=np.float64).reshape(-1, 3).copy()
        n = len(self.poses)
        if pesos is None:
            self.pesos = np.full(n, 1.0 / n)
        else:
            w = np.asarray(pesos, dtype=np.float64).ravel().copy()
            self.pesos = w / w.sum()

    def __len__(self):
        return len(self.poses)

    # ------------------------------------------------- amostragem inicial
    @classmethod
    def espalhar_uniforme(cls, mundo, n, rng):
        """Nenhum palpite: particulas sorteadas em qualquer celula LIVRE.

        E' a localizacao global, o caso em que o robo "nao sabe onde esta". No
        Nav2 e' o que acontece se voce nunca clicar em 2D Pose Estimate e o
        `set_initial_pose` estiver desligado.
        """
        livres = np.argwhere(~mundo.grade)                      # (M, 2) -> (i, j)
        escolhidas = rng.integers(0, len(livres), size=n)
        i = livres[escolhidas, 0]
        j = livres[escolhidas, 1]
        x = (j + rng.random(n)) * mundo.res                     # sorteia dentro da celula
        y = (i + rng.random(n)) * mundo.res
        th = rng.uniform(-math.pi, math.pi, n)
        return cls(np.column_stack([x, y, th]))

    @classmethod
    def espalhar_ao_redor(cls, pose, n, rng, sigma=0.35, sigma_ang=0.20):
        """Uma gaussiana em volta de uma pose informada.

        E' literalmente o 2D Pose Estimate do RViz2: a seta que voce arrasta
        da' a media, e a incerteza do seu clique da' o sigma. Se a seta
        apontar para o lugar errado, a nuvem nasce errada -- e o filtro NAO
        tem como saber disso (veja o cenario `errada` do `avaliar_loc.py`).
        """
        x, y, th = pose
        return cls(np.column_stack([
            x + rng.normal(0.0, sigma, n),
            y + rng.normal(0.0, sigma, n),
            normalizar(th + rng.normal(0.0, sigma_ang, n))]))

    # -------------------------------------------------- modelo de movimento
    def mover(self, rot1, trans, rot2, rng, alfa=ALFA_PADRAO):
        """Aplica o deslocamento da odometria a CADA particula, com ruido.

        O deslocamento vem decomposto em tres partes, como no modelo de
        odometria do AMCL: gira para a direcao do movimento (rot1), anda
        (trans), gira para a pose final (rot2). Cada parte recebe ruido
        proprio, e os quatro coeficientes sao os alpha1..alpha4.

        O ruido NAO e' enfeite: ele e' o que impede o colapso prematuro. Sem
        ele, as N particulas andam todas igual, a nuvem nunca se abre, a
        reamostragem come a diversidade em poucos ciclos e o filtro fica
        preso na primeira hipotese que parecer boa -- confiante e errado.
        """
        n = len(self.poses)
        a1, a2, a3, a4 = alfa
        sd_rot1 = a1 * abs(rot1) + a2 * abs(trans) + PISO_RUIDO_ROT
        sd_rot2 = a1 * abs(rot2) + a2 * abs(trans) + PISO_RUIDO_ROT
        sd_tr = a3 * abs(trans) + a4 * (abs(rot1) + abs(rot2)) + PISO_RUIDO_TRANS

        r1 = rot1 + rng.normal(0.0, sd_rot1, n)
        tr = trans + rng.normal(0.0, sd_tr, n)
        r2 = rot2 + rng.normal(0.0, sd_rot2, n)

        rumo = self.poses[:, 2] + r1
        self.poses[:, 0] += tr * np.cos(rumo)
        self.poses[:, 1] += tr * np.sin(rumo)
        self.poses[:, 2] = normalizar(rumo + r2)

    # ------------------------------------------------------------ estimativa
    def n_efetivo(self) -> float:
        """N efetivo (Kong, Liu & Wong):  N_ef = 1 / soma(w_i^2).

        Com os pesos normalizados, ele vale N quando todos os pesos sao iguais
        (nenhuma particula manda mais que as outras) e vale 1 quando um peso
        sozinho leva tudo. E' quantas particulas AINDA ESTAO VALENDO ALGO --
        pode haver 2000 na tela e N efetivo 3, e e' esse o momento em que a
        nuvem para de representar a incerteza e passa a representar um palpite.
        """
        return float(1.0 / np.sum(self.pesos ** 2))

    def estimativa(self):
        """Devolve (pose_media, dispersao).

        A media de theta e' CIRCULAR -- media aritmetica de -179 e +179 da' 0,
        que e' o oposto do certo. A dispersao angular sai do comprimento do
        vetor resultante R: desvio = sqrt(-2 ln R), que e' o desvio-padrao
        circular. R perto de 1 e' nuvem alinhada; R perto de 0 e' nuvem
        apontando para todo lado.
        """
        w = self.pesos
        x = float(w @ self.poses[:, 0])
        y = float(w @ self.poses[:, 1])
        c = float(w @ np.cos(self.poses[:, 2]))
        s = float(w @ np.sin(self.poses[:, 2]))
        th = math.atan2(s, c)
        sx = math.sqrt(max(0.0, float(w @ (self.poses[:, 0] - x) ** 2)))
        sy = math.sqrt(max(0.0, float(w @ (self.poses[:, 1] - y) ** 2)))
        r = min(1.0, max(math.hypot(c, s), 1e-12))
        sth = math.sqrt(max(0.0, -2.0 * math.log(r)))
        return (x, y, th), (sx, sy, sth)


def raio_nuvem(dispersao) -> float:
    """Um numero so para "o tamanho da nuvem": hypot(desvio_x, desvio_y)."""
    return math.hypot(dispersao[0], dispersao[1])


class Mcl:
    """O filtro: move, pesa, reamostra. Um ciclo por varredura do laser.

    Todo parametro aqui tem par no AMCL do Nav2, e o README faz a tabela.
    """

    def __init__(self, mundo, particulas, rng, feixes_usados=30, sigma_z=0.20,
                 z_hit=0.80, z_rand=0.20, alcance_max=ALCANCE_MAX,
                 alfa=ALFA_PADRAO, update_min_d=0.20, update_min_a=0.20,
                 fracao_n_efetivo=0.5, intervalo_reamostragem=1,
                 expoente=EXPOENTE_PESO):
        self.mundo = mundo
        self.particulas = particulas
        self.rng = rng
        self.feixes_usados = int(feixes_usados)
        self.sigma_z = float(sigma_z)
        self.z_hit = float(z_hit)
        self.z_rand = float(z_rand)
        self.alcance_max = float(alcance_max)
        self.alfa = tuple(alfa)
        self.update_min_d = float(update_min_d)
        self.update_min_a = float(update_min_a)
        self.expoente = float(expoente)
        self.limiar_n_efetivo = float(fracao_n_efetivo) * len(particulas)
        self.intervalo_reamostragem = int(intervalo_reamostragem)

        self.odom_ant = None
        self.desde_reamostragem = 0
        self.n_efetivo = float(len(particulas))
        self.atualizou = False
        self.reamostrou = False
        self.ciclos = 0            # quantas vezes o par (pesar, reamostrar) rodou

    # ------------------------------------------------------------- um ciclo
    def atualizar(self, odom, angulos, leituras):
        """Um ciclo do filtro, com o mesmo portao do AMCL.

        Devolve True se o ciclo completo rodou (movimento + peso), False se o
        robo nao andou o suficiente desde a ultima vez. Esse portao e' o
        `update_min_d` / `update_min_a`: reamostrar com o robo parado destroi
        diversidade sem acrescentar informacao nenhuma -- a nuvem encolhe por
        falta de dado, nao por ganho de certeza, e isso se chama colapso.
        """
        self.atualizou = False
        self.reamostrou = False

        if self.odom_ant is None:
            self.odom_ant = tuple(float(v) for v in odom)
            return False

        dx = odom[0] - self.odom_ant[0]
        dy = odom[1] - self.odom_ant[1]
        dth = float(normalizar(odom[2] - self.odom_ant[2]))
        trans = math.hypot(dx, dy)
        if trans < self.update_min_d and abs(dth) < self.update_min_a:
            return False

        # Decomposicao gira-anda-gira. Com trans ~ 0 o atan2 nao diz nada
        # (direcao de um deslocamento nulo), entao o giro no lugar vai inteiro
        # para rot2 -- senao o ruido de rot1 entra duas vezes.
        if trans < 1e-6:
            rot1, rot2 = 0.0, dth
        else:
            rot1 = float(normalizar(math.atan2(dy, dx) - self.odom_ant[2]))
            rot2 = float(normalizar(dth - rot1))

        self.particulas.mover(rot1, trans, rot2, self.rng, self.alfa)
        self.pesar(angulos, leituras)
        self.desde_reamostragem += 1
        self.n_efetivo = self.particulas.n_efetivo()

        if (self.n_efetivo < self.limiar_n_efetivo
                and self.desde_reamostragem >= self.intervalo_reamostragem):
            self.reamostrar()
            self.reamostrou = True
            self.desde_reamostragem = 0

        self.odom_ant = tuple(float(v) for v in odom)
        self.atualizou = True
        self.ciclos += 1
        return True

    # ------------------------------------------------ modelo de observacao
    def indices_feixes(self, total):
        """Quais feixes do /scan entram na conta -- o `max_beams` do AMCL.

        Subconjunto espalhado por todo o leque, nunca um trecho contiguo: 30
        feixes vizinhos olham para a mesma parede e contam a mesma coisa 30
        vezes, o que infla a confianca sem acrescentar informacao.
        """
        k = min(self.feixes_usados, total)
        return np.linspace(0, total, k, endpoint=False).astype(np.int64)

    def pesar(self, angulos, leituras):
        """Pontua cada particula pela diferenca entre o /scan real e o esperado.

        Para cada particula, lanca os feixes escolhidos contra o mapa
        CONHECIDO e compara com o que o laser realmente mediu. Cada feixe
        contribui com uma mistura de dois termos -- os mesmos do AMCL:

            p = z_hit * gaussiana(erro, sigma_z)  +  z_rand / alcance_max

        O segundo termo e' o que salva o filtro: sem ele, UM feixe absurdo
        (uma pessoa passando na frente, algo que nao esta no mapa) zera o peso
        de uma particula que esta certa, e o filtro mata a hipotese boa. Com
        ele, o pior que um feixe faz e' nao ajudar.

        A conta anda em log: 30 feixes multiplicados dao numeros que o float64
        arredonda para zero, e uma nuvem de pesos todos zero nao se normaliza.
        A soma dos logs ainda e' multiplicada por `self.expoente` -- veja o
        comentario de EXPOENTE_PESO no topo, que e' o paragrafo mais importante
        deste arquivo.
        """
        idx = self.indices_feixes(len(angulos))
        ang = np.asarray(angulos, dtype=np.float64)[idx]
        z = np.asarray(leituras, dtype=np.float64)[idx]
        # inf = "nao achei parede". Vira alcance maximo nos DOIS lados da
        # comparacao, senao a conta estoura e a hipotese e' descartada por um
        # detalhe de representacao.
        z = np.where(np.isfinite(z), np.minimum(z, self.alcance_max), self.alcance_max)

        esperado = lancar_lote(self.mundo, self.particulas.poses, ang,
                               self.alcance_max, PASSO_RAIO)
        esperado = np.where(np.isfinite(esperado), esperado, self.alcance_max)

        erro = esperado - z[None, :]
        p = (self.z_hit * np.exp(-0.5 * (erro / self.sigma_z) ** 2)
             + self.z_rand / self.alcance_max)
        log_w = np.log(p).sum(axis=1) * self.expoente
        log_w -= log_w.max()                        # so' a razao entre pesos importa
        w = np.exp(log_w) * self.particulas.pesos   # posterior = anterior x verossimilhanca
        soma = float(w.sum())
        if not np.isfinite(soma) or soma <= 0.0:
            # Todas as hipoteses impossiveis. Nao invente uma: empate, e deixe
            # o movimento espalhar a nuvem ate alguma voltar a fazer sentido.
            w = np.full(len(w), 1.0 / len(w))
            soma = 1.0
        self.particulas.pesos = w / soma

    # ---------------------------------------------------------- reamostragem
    def reamostrar(self):
        """Reamostragem SISTEMATICA: um sorteio so', N cortes igualmente espacados.

        Pensa na soma acumulada dos pesos como uma regua de 0 a 1, em que cada
        particula ocupa um pedaco do tamanho do seu peso. Sorteia-se UM numero
        em [0, 1/N) e marcam-se N cortes de 1/N em 1/N. Quem ocupa o pedaco de
        cada corte entra na nuvem nova -- peso grande ocupa muitos cortes e e'
        copiado varias vezes; peso minusculo some.

        Um sorteio em vez de N (como seria no multinomial) reduz a variancia da
        reamostragem, e e' o metodo que o AMCL usa. Depois do corte os pesos
        voltam todos a 1/N: a informacao ja' esta na POSICAO das copias.
        """
        n = len(self.particulas)
        acum = np.cumsum(self.particulas.pesos)
        acum[-1] = 1.0                              # fecha erro de arredondamento
        cortes = (self.rng.random() + np.arange(n)) / n
        idx = np.searchsorted(acum, cortes, side='left')
        np.clip(idx, 0, n - 1, out=idx)
        self.particulas.poses = self.particulas.poses[idx].copy()
        self.particulas.pesos = np.full(n, 1.0 / n)

    def estimativa(self):
        return self.particulas.estimativa()


# ------------------------------------------------------------------- a regua

def erro_de_pose(estimada, verdadeira):
    """(erro de posicao em m, erro de angulo em graus) contra a verdade."""
    ex = estimada[0] - verdadeira[0]
    ey = estimada[1] - verdadeira[1]
    ea = float(normalizar(estimada[2] - verdadeira[2]))
    return math.hypot(ex, ey), abs(math.degrees(ea))


def instante_convergencia(registros, limiar=LIMIAR_DISPERSAO,
                          limiar_ang=LIMIAR_DISP_ANG, estaveis=PASSOS_ESTAVEIS):
    """Quando a nuvem convergiu, pelo criterio declarado no topo do modulo.

    Recebe a lista de registros do `simular_loc.py` e devolve o tempo (s) do
    PRIMEIRO instante a partir do qual a nuvem fica concentrada e assim
    permanece por `estaveis` atualizacoes seguidas. None se nunca.

    Contam apenas os registros em que o filtro realmente atualizou: com o robo
    parado a dispersao fica congelada, e congelado nao e' convergido.
    """
    passos = [r for r in registros if r['atualizou']]
    bons = [(r['t'], raio_nuvem((r['disp_x'], r['disp_y'], r['disp_th'])) < limiar
             and math.degrees(r['disp_th']) < limiar_ang) for r in passos]
    seguidos = 0
    inicio = None
    for t, ok in bons:
        if ok:
            if seguidos == 0:
                inicio = t
            seguidos += 1
            if seguidos >= estaveis:
                return inicio
        else:
            seguidos = 0
            inicio = None
    return None


def veredito(t_conv, erro_pos, limiar_acerto=LIMIAR_ACERTO):
    """Convergir nao e' acertar -- a tese da Aula 13 reaparecendo na Aula 15."""
    if t_conv is None:
        return 'NAO convergiu'
    return 'lugar certo' if erro_pos < limiar_acerto else 'lugar ERRADO'


if __name__ == '__main__':
    mundo = Mundo()
    angs = np.linspace(-math.pi, math.pi, 30, endpoint=False)
    poses = np.array([[2.0, 4.0, 0.0], [9.0, 2.0, 1.0], [4.0, 6.5, -2.0]])
    lote = lancar_lote(mundo, poses, angs)
    uma = np.array([mundo.medir(*p, angs, alcance_max=ALCANCE_MAX) for p in poses])
    finito = np.isfinite(lote) & np.isfinite(uma)
    print('mapa (= verdade): %s' % ONDE_CENARIO)
    print('grade           : %d x %d celulas de %.2f m' % (mundo.nx, mundo.ny, mundo.res))
    print('feixes por pose : %d, alcance %.1f m' % (len(angs), ALCANCE_MAX))
    print('lote x medir    : maior diferenca %.3f m em %d feixes finitos'
          % (float(np.abs(lote[finito] - uma[finito]).max()), int(finito.sum())))
    print('inf de acordo   : %s'
          % (np.array_equal(np.isfinite(lote), np.isfinite(uma))))
    print()
    print('convergencia    : raio da nuvem < %.2f m E desvio angular < %.1f graus,'
          % (LIMIAR_DISPERSAO, LIMIAR_DISP_ANG))
    print('                  mantidos por %d atualizacoes seguidas' % PASSOS_ESTAVEIS)
    print('acerto          : erro de posicao final < %.2f m contra a verdade'
          % LIMIAR_ACERTO)
