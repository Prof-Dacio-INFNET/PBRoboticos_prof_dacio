#!/usr/bin/env python3
"""Sobe o MetaDrive sem janela, dirige sozinho e grava N quadros da camera RGB.

    python capturar_frames.py                          # 60 quadros em ./quadros
    python capturar_frames.py --frames 500 --saida dataset --semente 3
    python capturar_frames.py --frames 3 --passo 1 --saida /tmp/q   # o teste rapido

Escreve, na pasta de --saida:

    quadro000.png ... quadroNNN.png   a camera sintetica, 8 bits, 3 canais
    estado.csv                        uma linha por quadro: onde o carro estava,
                                      a que velocidade, para onde apontava, o
                                      que havia a frente e se estava num
                                      cruzamento -- a base do rotulo
                                      semiautomatico do item 4 do TP4

QUEM DIRIGE e o IDMPolicy do proprio MetaDrive: segue a faixa, freia atras do
carro da frente e troca de faixa sozinho. Nao e o seu controlador; e o motorista
que gera os dados. Com ele a trajetoria depende so da semente, e o mesmo
comando gera o mesmo conjunto na sua maquina e na do colega.

A IMAGEM sai da observacao do ambiente (image_observation=True), que entrega um
dicionario {"image": (H, W, 3, pilha), "state": (19,)}. Com norm_pixel=False a
imagem e uint8 em [0, 255]; com stack_size=1 a pilha tem um quadro so. E a
ordem dos canais e BGR -- a mesma do OpenCV --, entao o cv2.imwrite grava o
array sem conversao nenhuma. Quem for mostrar com matplotlib inverte: [..., ::-1].

SEM TELA: o MetaDrive 0.4.3 abre um buffer OpenGL fora da tela, mas pede um
servidor X para isso (o pipe que ele carrega e o glxGraphicsPipe do Panda3D).
No WSL2 com WSLg o DISPLAY ja existe e basta rodar. Num servidor sem X,
rode por baixo do xvfb-run (veja o README). Sem DISPLAY nenhum o erro do
MetaDrive e enganoso -- "'NoneType' object has no attribute 'set_shader'" --,
por isso este script confere o DISPLAY antes e para com a frase certa.
"""
import argparse
import csv
import math
import os
import re
import sys
import time

# --- parametros da rotulagem semiautomatica, declarados ANTES de capturar ---
# Corredor a frente do carro, no referencial do proprio carro: um objeto conta
# como "a frente" se estiver entre 0 e ALCANCE_M para a frente e a menos de
# MEIA_LARGURA_M para o lado. 1,75 m e meia faixa de 3,5 m.
ALCANCE_M = 30.0
MEIA_LARGURA_M = 1.75
# Abaixo desta distancia a linha sai com rotulo_sugerido = obstaculo.
LIMIAR_OBSTACULO_M = 20.0
# Letras de bloco do mapa procedural que sao cruzamento: X (quatro vias),
# T (tres vias) e O (rotatoria). Ver metadrive/component/pgblock/.
BLOCOS_CRUZAMENTO = ("X", "T", "O")
# O mapa: uma letra por bloco. S reta, X cruzamento, T, C curva.
# Fixo de proposito: com mapa sorteado, metade das sementes nao tem cruzamento.
MAPA_PADRAO = "SXSTSC"

COLUNAS = [
    "indice", "arquivo", "passo", "t_s", "x_m", "y_m", "vel_kmh", "rumo_rad",
    "bloco", "em_cruzamento", "veiculo_a_frente", "dist_a_frente_m",
    "objeto_a_frente", "rotulo_sugerido",
]

_BLOCO = re.compile(r"^-?\d+([A-Za-z$])")


def bloco_da_faixa(indice_faixa):
    """Devolve a letra do bloco em que a faixa atual TERMINA, ou "" se nao achar.

    O MetaDrive nomeia os nos do grafo de vias como "2X0_0_": numero do bloco,
    letra do tipo, e o resto e interno. A faixa (inicio, fim, i) pertence ao
    bloco do no 'fim' -- e e por isso que a aproximacao de um cruzamento ja
    conta como cruzamento. Os nos do primeiro bloco sao ">", ">>", ">>>".
    """
    if not indice_faixa:
        return ""
    fim = indice_faixa[1]
    achado = _BLOCO.match(fim)
    return achado.group(1) if achado else "I"


def o_que_esta_a_frente(carro, objetos):
    """Procura o objeto mais proximo no corredor a frente do carro.

    Usa so geometria: posicao do objeto no referencial do carro. Nao olha a
    imagem. Devolve (distancia em m ou None, nome da classe ou "").
    """
    cx, cy = carro.position
    rumo = carro.heading_theta
    c, s = math.cos(rumo), math.sin(rumo)
    melhor, nome = None, ""
    for obj in objetos:
        if obj is carro:
            continue
        ox, oy = obj.position
        dx, dy = ox - cx, oy - cy
        frente = dx * c + dy * s
        lado = -dx * s + dy * c
        if 0.0 < frente <= ALCANCE_M and abs(lado) <= MEIA_LARGURA_M:
            if melhor is None or frente < melhor:
                melhor, nome = frente, type(obj).__name__
    return melhor, nome


def rotulo(em_cruzamento, dist):
    """A regra do rotulo sugerido. Cruzamento ganha de obstaculo de proposito:
    no cruzamento quase sempre ha carro parado a frente, e a classe rara e ela.
    """
    if em_cruzamento:
        return "cruzamento"
    if dist is not None and dist <= LIMIAR_OBSTACULO_M:
        return "obstaculo"
    return "via_livre"


def tem_tela():
    """O Panda3D do MetaDrive 0.4.3 so abre o buffer fora da tela com um X."""
    return bool(os.environ.get("DISPLAY"))


def montar_ambiente(args):
    """Cria o MetaDriveEnv com a camera RGB como observacao.

    Os imports ficam aqui dentro para o --help funcionar sem o MetaDrive.
    """
    from metadrive.component.sensors.rgb_camera import RGBCamera
    from metadrive.envs.metadrive_env import MetaDriveEnv
    from metadrive.policy.idm_policy import IDMPolicy

    config = dict(
        use_render=False,            # sem janela: o render vai para um buffer
        image_observation=True,      # a observacao passa a ter a imagem
        norm_pixel=False,            # uint8 0..255, nao float 0..1
        stack_size=1,                # um quadro por observacao, sem pilha
        sensors={"rgb_camera": (RGBCamera, args.largura, args.altura)},
        vehicle_config={"image_source": "rgb_camera"},
        interface_panel=[],          # sem painel: nao ha tela para ele
        window_size=(args.largura, args.altura),
        map=args.mapa,
        start_seed=args.semente,
        num_scenarios=1,
        traffic_density=args.trafego,
        accident_prob=args.acidentes,  # cones, triangulos e carro quebrado
        agent_policy=IDMPolicy,      # o motorista: segue a faixa sozinho
        # SEM o terreno o asfalto sai BRANCO e LISO: as faixas pintadas fazem
        # parte da textura do chao. Para o item 3 ele e obrigatorio.
        show_terrain=not args.sem_terreno,
        log_level=50,
    )
    return MetaDriveEnv(config)


def capturar(args):
    """Roda o episodio e grava os quadros. Devolve o numero de quadros gravados."""
    import cv2

    os.makedirs(args.saida, exist_ok=True)
    env = montar_ambiente(args)
    gravados = 0
    try:
        obs, _ = env.reset(seed=args.semente)
        dt = env.config["physics_world_step_size"] * env.config["decision_repeat"]
        carro = env.agent
        inicio = time.time()
        caminho_csv = os.path.join(args.saida, "estado.csv")
        with open(caminho_csv, "w", newline="") as arq:
            escritor = csv.writer(arq)
            escritor.writerow(COLUNAS)
            passo = 0
            while gravados < args.frames:
                # Avanca --passo passos entre um quadro e outro: quadros
                # vizinhos a 0,1 s sao quase iguais e nao ensinam nada a CNN.
                fim = False
                for _ in range(args.passo):
                    obs, _, term, trunc, info = env.step([0.0, 0.0])
                    passo += 1
                    if term or trunc:
                        fim = True
                        break
                img = obs["image"][..., -1]          # (H, W, 3) uint8 BGR
                nome = "quadro%03d.png" % gravados
                cv2.imwrite(os.path.join(args.saida, nome), img)
                objetos = env.engine.get_objects().values()
                dist, tipo = o_que_esta_a_frente(carro, objetos)
                bloco = bloco_da_faixa(carro.lane_index)
                cruz = bloco in BLOCOS_CRUZAMENTO
                veic = tipo.endswith("Vehicle")
                x, y = carro.position
                escritor.writerow([
                    gravados, nome, passo, "%.2f" % (passo * dt), "%.2f" % x, "%.2f" % y,
                    "%.1f" % carro.speed_km_h, "%.3f" % carro.heading_theta,
                    bloco, int(cruz), int(veic),
                    "" if dist is None else "%.1f" % dist, tipo, rotulo(cruz, dist),
                ])
                gravados += 1
                if fim:
                    print("AVISO: o episodio terminou no passo %d (%s); gravei %d quadros."
                          % (passo, _motivo(info), gravados))
                    break
        gasto = time.time() - inicio
        print("forma da imagem : %s, %s, canais BGR" % (img.shape, img.dtype))
        print("quadros gravados: %d em %s (+ estado.csv)" % (gravados, args.saida))
        print("tempo simulado  : %.1f s (%d passos de %.2f s)" % (passo * dt, passo, dt))
        print("tempo de parede : %.1f s -> %.2f quadros/s, %.2f passos/s"
              % (gasto, gravados / gasto, passo / gasto))
    finally:
        env.close()
    return gravados


def _motivo(info):
    """Traduz o dicionario de fim de episodio para uma palavra."""
    for chave in ("crash_vehicle", "crash_object", "out_of_road", "arrive_dest", "max_step"):
        if info.get(chave):
            return chave
    return "desconhecido"


def principal(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", type=int, default=60, help="quantos quadros gravar (60)")
    p.add_argument("--saida", default="quadros", help="pasta de saida (quadros)")
    p.add_argument("--semente", type=int, default=7, help="semente do cenario (7)")
    p.add_argument("--passo", type=int, default=3,
                   help="passos de 0,1 s entre dois quadros (3 -> um quadro a cada 0,3 s)")
    p.add_argument("--largura", type=int, default=320, help="largura da camera (320)")
    p.add_argument("--altura", type=int, default=240, help="altura da camera (240)")
    p.add_argument("--mapa", default=MAPA_PADRAO, help="blocos do mapa (%s)" % MAPA_PADRAO)
    p.add_argument("--trafego", type=float, default=0.15, help="densidade de trafego (0.15)")
    p.add_argument("--acidentes", type=float, default=1.0,
                   help="probabilidade de cena de acidente com cones por bloco (1.0)")
    p.add_argument("--sem-terreno", action="store_true",
                   help="desliga o chao texturizado: 2,3x mais rapido, mas SEM faixa pintada")
    args = p.parse_args(argv)
    if args.frames < 1 or args.passo < 1:
        p.error("--frames e --passo precisam ser >= 1")
    if not tem_tela():
        print("ERRO: nao ha DISPLAY. O MetaDrive 0.4.3 precisa de um servidor X mesmo\n"
              "sem janela. No WSL2, confira o WSLg (echo $DISPLAY deve dar :0).\n"
              "Sem X, rode por baixo do Xvfb:\n"
              "  xvfb-run -a -s \"-screen 0 1280x1024x24\" python capturar_frames.py ...",
              file=sys.stderr)
        return 2
    try:
        import metadrive  # noqa: F401
    except ImportError:
        print("ERRO: metadrive nao instalado neste Python (%s).\n"
              "Rode com o Python do venv: $PB_DIR/.venv-metadrive/bin/python" % sys.executable,
              file=sys.stderr)
        return 2
    return 0 if capturar(args) == args.frames else 1


if __name__ == "__main__":
    sys.exit(principal())
