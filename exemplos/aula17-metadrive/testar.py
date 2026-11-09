#!/usr/bin/env python3
"""Prova o que da para provar, com e sem o MetaDrive instalado.

    python3 testar.py                      # grupos 1 a 6; o 7 so se achar o MetaDrive
    python3 testar.py --python "$PB_DIR/.venv-metadrive/bin/python"   # forca o 7

Grupos:
    1. o estado.csv da amostra: colunas, 60 linhas, regra do rotulo coerente
    2. os PNG da amostra: forma (240, 320, 3), uint8, todos citados no CSV
    3. as funcoes puras do capturar_frames.py, com resposta sabida
    4. o formas.py: roda na amostra, e deterministico, ACHA circulo e canto
       quando eles existem (imagem desenhada), e nao acha circulo no MetaDrive
    5. o medir_faixas.py: a configuracao da Aula 13 da zero, a ajustada acha
    6. higiene: ast.parse, ASCII puro, linhas <= 99 colunas
    7. SO COM METADRIVE: captura 3 quadros duas vezes e confere que as duas
       capturas dao o mesmo CSV

Termina em "todos os testes passaram." e sai com 0, ou com 1 na primeira falha
de cada grupo contada no fim.
"""
import argparse
import ast
import csv
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
AMOSTRA = AQUI / "amostra"
sys.path.insert(0, str(AQUI))

import capturar_frames as cf  # noqa: E402  (nao importa o metadrive no topo)
import formas  # noqa: E402
import medir_faixas  # noqa: E402

FALHAS = []


def confere(cond, msg):
    print("  [%s] %s" % ("ok" if cond else "FALHOU", msg))
    if not cond:
        FALHAS.append(msg)


def ler_csv():
    with open(AMOSTRA / "estado.csv", newline="") as arq:
        leitor = csv.reader(arq)
        cab = next(leitor)
        return cab, [dict(zip(cab, lin)) for lin in leitor]


def grupo1():
    print("1. estado.csv da amostra")
    cab, linhas = ler_csv()
    confere(cab == cf.COLUNAS, "as %d colunas sao as do capturar_frames.COLUNAS" % len(cab))
    confere(len(linhas) == 60, "60 linhas (achei %d)" % len(linhas))
    confere([int(x["indice"]) for x in linhas] == list(range(len(linhas))),
            "indice vai de 0 a N-1 sem buraco")
    t = [float(x["t_s"]) for x in linhas]
    confere(all(b > a for a, b in zip(t, t[1:])), "o tempo cresce estritamente")
    confere(all(x["rotulo_sugerido"] in ("via_livre", "obstaculo", "cruzamento")
                for x in linhas), "rotulo_sugerido so tem as 3 classes do item 4")
    coerente = all(
        x["rotulo_sugerido"] == cf.rotulo(
            x["em_cruzamento"] == "1",
            float(x["dist_a_frente_m"]) if x["dist_a_frente_m"] else None)
        for x in linhas)
    confere(coerente, "rotulo_sugerido bate com a regra rotulo() linha a linha")
    confere(all((x["bloco"] in cf.BLOCOS_CRUZAMENTO) == (x["em_cruzamento"] == "1")
                for x in linhas), "em_cruzamento bate com a letra do bloco")
    n_cruz = sum(1 for x in linhas if x["rotulo_sugerido"] == "cruzamento")
    confere(n_cruz >= 1, "a semente 7 passa por um cruzamento (%d quadros)" % n_cruz)


def grupo2():
    print("2. PNG da amostra")
    _, linhas = ler_csv()
    citados = {x["arquivo"] for x in linhas}
    pngs = sorted(AMOSTRA.glob("quadro*.png"))
    confere(len(pngs) >= 10, "ha pelo menos 10 quadros na amostra (%d)" % len(pngs))
    formas_ok = True
    for p in pngs:
        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        formas_ok &= img is not None and img.shape == (240, 320, 3) and img.dtype == np.uint8
    confere(formas_ok, "todos os quadros sao (240, 320, 3) uint8")
    confere(all(p.name in citados for p in pngs), "todo PNG da amostra tem linha no CSV")
    # Ceu azul em cima, asfalto cinza embaixo: se o canal azul do ceu for maior
    # que o vermelho no ARQUIVO lido pelo cv2 (BGR), a ordem de canais esta certa.
    img = cv2.imread(str(pngs[0]))
    ceu = img[:40].reshape(-1, 3).mean(axis=0)
    confere(ceu[0] > ceu[2] + 20, "ceu azul no canal 0 do cv2: o arquivo foi gravado em BGR "
            "certo (B=%.0f R=%.0f)" % (ceu[0], ceu[2]))


class _Obj(object):
    def __init__(self, x, y, rumo=0.0):
        self.position = (x, y)
        self.heading_theta = rumo


class SVehicle(_Obj):
    pass


class TrafficCone(_Obj):
    pass


def grupo3():
    print("3. funcoes puras do capturar_frames.py")
    confere(cf.bloco_da_faixa((">", ">>", 0)) == "I", "no '>>' e o primeiro bloco: I")
    confere(cf.bloco_da_faixa(("1S0_0_", "2X0_0_", 0)) == "X", "fim '2X0_0_' -> X")
    confere(cf.bloco_da_faixa(("-3T0_1_", "-3T1_0_", 1)) == "T", "sinal negativo -> T")
    confere(cf.bloco_da_faixa(None) == "", "sem faixa -> vazio")
    carro = _Obj(0.0, 0.0, 0.0)
    obj = [carro, SVehicle(12.0, 0.5), TrafficCone(8.0, 3.0), SVehicle(-5.0, 0.0),
           SVehicle(45.0, 0.0)]
    d, tipo = cf.o_que_esta_a_frente(carro, obj)
    confere(d == 12.0 and tipo == "SVehicle",
            "a frente: carro a 12 m na faixa; cone a 3 m de lado e carro atras ignorados")
    carro_n = _Obj(0.0, 0.0, 1.5707963)
    d2, _ = cf.o_que_esta_a_frente(carro_n, [carro_n, TrafficCone(0.3, 9.0)])
    confere(d2 is not None and abs(d2 - 9.0) < 0.01, "o corredor gira com o rumo (90 graus)")
    confere(cf.rotulo(True, 5.0) == "cruzamento", "cruzamento ganha de obstaculo")
    confere(cf.rotulo(False, cf.LIMIAR_OBSTACULO_M) == "obstaculo", "no limiar e obstaculo")
    confere(cf.rotulo(False, None) == "via_livre", "nada a frente e via livre")


def grupo4():
    print("4. formas.py")
    a = formas.percorrer(AMOSTRA)
    b = formas.percorrer(AMOSTRA)
    confere(len(a) >= 10, "roda sobre a amostra (%d quadros)" % len(a))
    confere(a == b, "duas passadas dao exatamente o mesmo resultado")
    confere(sum(len(r["circulos"]) for _, r in a) == 0,
            "param2=30: nenhum circulo nos quadros do MetaDrive (nao ha placa)")
    confere(all(len(r["cantos"]) > 0 for _, r in a), "Harris marca cantos em todo quadro")
    # O detector funciona quando HA circulo: uma placa desenhada.
    img = np.full((240, 320, 3), 110, np.uint8)
    cv2.circle(img, (160, 100), 25, (40, 40, 220), -1)
    cv2.circle(img, (160, 100), 25, (250, 250, 250), 3)
    cs = formas.circulos(img)
    confere(len(cs) == 1 and abs(cs[0][0] - 160) <= 3 and abs(cs[0][2] - 25) <= 4,
            "placa redonda desenhada: 1 circulo em (160, 100), raio 25 (%s)" % cs)
    img2 = np.full((240, 320, 3), 200, np.uint8)
    cv2.rectangle(img2, (100, 60), (220, 180), (20, 20, 20), -1)
    ks = formas.cantos(img2)
    confere(len(ks) == 4, "quadrado preto desenhado: 4 cantos Harris (%d)" % len(ks))


def grupo5():
    print("5. medir_faixas.py")
    if not medir_faixas.AULA13_PADRAO.is_file():
        print("  [pulado] nao achei %s" % medir_faixas.AULA13_PADRAO)
        return
    F = medir_faixas.carregar_faixas(medir_faixas.AULA13_PADRAO)
    linhas = medir_faixas.medir(F, AMOSTRA)
    seg_p = sum(lin[1]["diag"]["n_segmentos"] for lin in linhas)
    ambas_a = sum(1 for lin in linhas if lin[2]["faixa_esq"] and lin[2]["faixa_dir"])
    confere(seg_p == 0, "configuracao da Aula 13, sem mudar nada: 0 segmentos no MetaDrive")
    confere(ambas_a >= len(linhas) - 2, "configuracao ajustada: as duas faixas em %d de %d"
            % (ambas_a, len(linhas)))


def grupo6():
    print("6. higiene dos .py")
    for p in sorted(AQUI.glob("*.py")):
        bruto = p.read_bytes()
        ok_ast = True
        try:
            ast.parse(bruto.decode("ascii", errors="replace"))
        except SyntaxError:
            ok_ast = False
        ascii_ok = all(c < 128 for c in bruto)
        largas = [i + 1 for i, lin in enumerate(bruto.decode("utf-8").splitlines())
                  if len(lin) > 99]
        confere(ok_ast and ascii_ok and not largas,
                "%s: ast ok, ASCII puro, nenhuma linha > 99%s"
                % (p.name, "" if not largas else " (linhas %s)" % largas))


def achar_python(pedido):
    """Um Python que importe metadrive: o pedido, este, ou o .venv-metadrive."""
    candidatos = [pedido, os.environ.get("METADRIVE_PYTHON"), sys.executable,
                  str(AQUI.parent / ".venv-metadrive" / "bin" / "python"),
                  str(AQUI / ".venv-metadrive" / "bin" / "python"),
                  str(pathlib.Path.cwd() / ".venv-metadrive" / "bin" / "python")]
    for c in candidatos:
        if not c or not os.path.exists(c):
            continue
        r = subprocess.run([c, "-c", "import metadrive"], capture_output=True)
        if r.returncode == 0:
            return c
    return None


def capturar_3(py, pasta):
    cmd = [py, str(AQUI / "capturar_frames.py"), "--frames", "3", "--passo", "1",
           "--saida", pasta]
    if not os.environ.get("DISPLAY"):
        if not shutil.which("xvfb-run"):
            return None
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24"] + cmd
    # cwd numa pasta temporaria: python -m/import falha se houver ./metadrive
    return subprocess.run(cmd, capture_output=True, text=True, cwd=tempfile.gettempdir())


def grupo7(pedido):
    print("7. captura de verdade (MetaDrive)")
    py = achar_python(pedido)
    if py is None:
        print("  [pulado] nenhum Python com metadrive (passe --python ou defina "
              "METADRIVE_PYTHON)")
        return
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        r1 = capturar_3(py, d1)
        if r1 is None:
            print("  [pulado] sem DISPLAY e sem xvfb-run")
            return
        confere(r1.returncode == 0, "capturar_frames.py --frames 3 sai com 0 (%s)"
                % (r1.stderr.strip().splitlines()[-1:] if r1.returncode else py))
        if r1.returncode:
            return
        pngs = sorted(pathlib.Path(d1).glob("quadro*.png"))
        confere(len(pngs) == 3, "3 PNG gravados")
        img = cv2.imread(str(pngs[0]), cv2.IMREAD_UNCHANGED)
        confere(img is not None and img.shape == (240, 320, 3), "forma (240, 320, 3)")
        with open(os.path.join(d1, "estado.csv")) as arq:
            linhas = list(csv.reader(arq))
        confere(linhas[0] == cf.COLUNAS and len(linhas) == 4, "CSV com cabecalho e 3 linhas")
        r2 = capturar_3(py, d2)
        csv1 = open(os.path.join(d1, "estado.csv")).read()
        csv2 = open(os.path.join(d2, "estado.csv")).read()
        confere(r2.returncode == 0 and csv1 == csv2,
                "mesma semente, mesmo estado.csv nas duas capturas")
        h1 = [hashlib.md5(p.read_bytes()).hexdigest() for p in pngs]
        h2 = [hashlib.md5(p.read_bytes()).hexdigest()
              for p in sorted(pathlib.Path(d2).glob("quadro*.png"))]
        print("  [info] PNG identicos byte a byte nas duas capturas: %s"
              % ("sim" if h1 == h2 else "NAO (o render nao e garantido deterministico)"))


def principal():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--python", help="Python do ambiente com o metadrive (grupo 7)")
    args = p.parse_args()
    grupo1()
    grupo2()
    grupo3()
    grupo4()
    grupo5()
    grupo6()
    grupo7(args.python)
    if FALHAS:
        print("%d falha(s)." % len(FALHAS))
        return 1
    print("todos os testes passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
