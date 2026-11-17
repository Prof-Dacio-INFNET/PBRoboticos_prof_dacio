#!/usr/bin/env python3
"""Prova o que da para provar do medir_dispositivo.py -- inclusive sem GPU nenhuma.

    python3 testar.py                                              # grupos 1 a 4
    python3 testar.py --python "$PB_DIR/.venv-rl/bin/python" \
                      --python "$PB_DIR/.venv-cnn/bin/python"      # + grupo 5

Grupos:
    1. higiene dos .py: ast.parse, ASCII puro, linhas <= 99 colunas
    2. funcoes puras: diagnostico das mensagens literais (serie RTX 50, driver velho,
       PTX), razao, mediana, tabela, vocabulario (achei / nao achei / olhe)
    3. dubles do torch: GPU sm_120 com torch sem sm_120 (o aviso classico), GPU com
       sm_120 na lista, e o main inteiro com a GPU dando "no kernel image" -- tem de
       virar relato, nunca traceback
    4. dubles do TensorFlow: GPU visivel e CUDA_ERROR_INVALID_PTX no primeiro lote;
       e a captura do stderr do C++ (descritor 2)
    5. SO COM --python: o script de verdade, em CPU, em cada Python dado

Termina em "todos os testes passaram." e sai com 0, ou com 1 se algo falhou.
"""
import argparse
import ast
import contextlib
import io
import os
import pathlib
import subprocess
import sys
import types
import warnings

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.dont_write_bytecode = True

import medir_dispositivo as md  # noqa: E402

FALHAS = []

AVISO_SM120 = ("NVIDIA GeForce RTX 5050 Laptop GPU with CUDA capability sm_120 is not "
               "compatible with the current PyTorch installation.\nThe current PyTorch "
               "install supports CUDA capabilities sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90.")
ERRO_KERNEL = ("CUDA error: no kernel image is available for execution on the device\n"
               "CUDA kernel errors might be asynchronously reported at some other API call")
ERRO_PTX = ("'cuModuleLoadData(&module, data)' failed with 'CUDA_ERROR_INVALID_PTX'")
LOG_TF = ("2026-11-17 W external/xla/gpu: TensorFlow was not built with CUDA kernel "
          "binaries compatible with compute capability 12.0. CUDA kernels will be "
          "jit-compiled from PTX, which could take 30 minutes or longer.\n"
          "I tensorflow/core: outra linha qualquer\n")
PROIBIDAS = ("use gpu", "use a gpu", "aprovado", "reprovado", "[ok]", "falha:", "erro:")


def confere(cond, msg):
    print("  [%s] %s" % ("ok" if cond else "FALHOU", msg))
    if not cond:
        FALHAS.append(msg)


@contextlib.contextmanager
def modulos_falsos(**mods):
    """Poe modulos falsos em sys.modules e devolve o estado anterior no fim."""
    antes = {k: sys.modules.get(k) for k in mods}
    sys.modules.update(mods)
    try:
        yield
    finally:
        for k, v in antes.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def rodar_main(argv):
    """main() com a saida capturada; devolve (codigo, texto, excecao)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = md.main(argv)
        return rc, buf.getvalue(), None
    except Exception as e:  # noqa: BLE001
        return None, buf.getvalue(), e


def grupo1():
    print("1. higiene dos .py")
    for p in sorted(AQUI.glob("*.py")):
        bruto = p.read_bytes()
        try:
            ast.parse(bruto)
            ok_ast = True
        except SyntaxError:
            ok_ast = False
        ascii_ok = all(c < 128 for c in bruto)
        largas = [i + 1 for i, lin in enumerate(bruto.decode("utf-8").splitlines())
                  if len(lin) > 99]
        confere(ok_ast and ascii_ok and not largas,
                "%s: ast ok, ASCII puro, nenhuma linha > 99%s"
                % (p.name, "" if not largas else " (linhas %s)" % largas))


def grupo2():
    print("2. funcoes puras")
    d = md.diagnosticar(AVISO_SM120)
    confere(d is not None and "cu130" in d, "aviso sm_120 do torch -> manda reinstalar com cu130")
    d = md.diagnosticar(ERRO_KERNEL)
    confere(d is not None and "sm_120" in d, "'no kernel image' -> fala da arquitetura sm_120")
    d = md.diagnosticar(ERRO_PTX)
    confere(d is not None and "tensorflow-cpu" in d, "CUDA_ERROR_INVALID_PTX -> plano B")
    d = md.diagnosticar(LOG_TF)
    confere(d is not None and "PTX" in d, "log 'not built with ... 12.0' -> compilacao PTX")
    d = md.diagnosticar("The NVIDIA driver on your system is too old (found version 12020)")
    confere(d is not None and "WINDOWS" in d, "driver velho -> atualizar no Windows")
    confere(md.diagnosticar("CUDA out of memory. Tried to allocate") is not None,
            "out of memory reconhecido")
    confere(md.diagnosticar("ModuleNotFoundError: x") is None, "mensagem sem relacao -> None")
    confere(md.diagnosticar(None) is None, "None -> None")
    rel = md.linhas_relevantes(LOG_TF)
    confere(len(rel) == 1 and "12.0" in rel[0], "linhas_relevantes pega so a linha da GPU")
    confere(md.mediana_ms([0.001, 0.003, 0.002]) == 2.0, "mediana_ms([1,3,2] ms) = 2.0")
    confere(md.mediana_ms([]) is None, "mediana_ms([]) = None")
    confere(md.razao(10.0, 2.5) == 4.0, "razao(10, 2.5) = 4.0 (cpu/gpu)")
    confere(md.razao(10.0, None) is None and md.razao(None, 1.0) is None,
            "razao sem um dos lados = None")
    t = md.tabela([("torch", "mlp-passo", 0.04, None, "sem GPU"),
                   ("torch", "cnn-treino", 120.0, 12.0, None)])
    confere("cpu (ms/lote)" in t and "gpu (ms/lote)" in t and "razao" in t,
            "tabela tem as colunas carga | cpu | gpu | razao")
    confere("sem GPU" in t and "10.00" in t, "tabela: 'sem GPU' e a razao 10.00")
    obs = md.observacoes([("torch", "a", 1.0, 3.0, None), ("torch", "b", 30.0, 3.0, None),
                          ("torch", "c", 1.0, 1.05, None), ("torch", "d", 1.0, None, "x")])
    confere(len(obs) == 3 and all(o.startswith("olhe: ") for o in obs),
            "observacoes so com 'olhe:' (3 frases; a sem GPU nao gera frase)")
    confere("MAIS" in obs[0] and "MENOS" in obs[1] and "mesma faixa" in obs[2],
            "observacoes dizem MAIS / MENOS / mesma faixa")
    texto = " ".join(obs).lower() + md.CABECALHO.lower()
    confere(not any(p in texto for p in PROIBIDAS), "nenhuma frase de veredito")
    confere(md.e_wsl("Linux version 6.6.87.2-microsoft-standard-WSL2"), "e_wsl: WSL2 -> True")
    confere(not md.e_wsl("Linux version 6.8.0-49-generic"), "e_wsl: Ubuntu nativo -> False")


class _Cuda:
    def __init__(self, arqs, aviso=None, nome_falha=False):
        self.arqs, self.aviso, self.nome_falha = arqs, aviso, nome_falha

    def is_available(self):
        if self.aviso:
            warnings.warn(self.aviso, UserWarning)
        return True

    def get_device_name(self, i):
        if self.nome_falha:
            raise RuntimeError(ERRO_KERNEL)
        return "NVIDIA GeForce RTX 5050 Laptop GPU"

    def get_device_capability(self, i):
        return (12, 0)

    def get_arch_list(self):
        return list(self.arqs)

    def synchronize(self):
        pass


def torch_falso(arqs, aviso=None, nome_falha=False):
    t = types.ModuleType("torch")
    t.__version__ = "2.11.0+cu126"
    t.version = types.SimpleNamespace(cuda="12.6")
    t.cuda = _Cuda(arqs, aviso, nome_falha)
    t.get_num_threads = lambda: 2
    return t


ANTIGAS = ["sm_50", "sm_60", "sm_70", "sm_75", "sm_80", "sm_86", "sm_90"]


def grupo3():
    print("3. dubles do torch (sem GPU de verdade)")
    info = md.inspecionar_torch(torch_falso(ANTIGAS, aviso=AVISO_SM120))
    confere(info["disponivel"] and info["sm"] == "sm_120", "GPU vista como sm_120")
    confere(info["arquitetura_na_lista"] is False, "sm_120 fora da lista do torch cu126")
    confere(any("sm_120" in a for a in info["avisos"]), "o aviso classico foi capturado")
    info = md.inspecionar_torch(torch_falso(ANTIGAS + ["sm_100", "sm_120"]))
    confere(info["arquitetura_na_lista"] is True and not info["avisos"],
            "torch com sm_120 na lista: nada a apontar")
    info = md.inspecionar_torch(torch_falso(ANTIGAS, nome_falha=True))
    confere(any("no kernel image" in a for a in info["avisos"]),
            "erro ao pedir o nome da GPU vira aviso, nao excecao")

    ms, nota, msgs = md.medir_com_seguranca(lambda: [0.001, 0.002, 0.003], "x")
    confere(ms == 2.0 and nota is None, "medir_com_seguranca: tempos -> mediana")

    def explode():
        raise RuntimeError(ERRO_KERNEL)
    ms, nota, msgs = md.medir_com_seguranca(explode, "x")
    confere(ms is None and nota == "erro" and "no kernel image" in msgs[0],
            "medir_com_seguranca: RuntimeError vira (None, 'erro', mensagem)")

    # o main inteiro: CPU mede, GPU explode no primeiro lote
    original = md.cargas_torch

    def cargas(torch, disp, grande):
        def passo():
            if disp == "cuda":
                raise RuntimeError(ERRO_KERNEL)
        return [("mlp-passo", passo), ("cnn-treino", passo)]
    md.cargas_torch = cargas
    try:
        with modulos_falsos(torch=torch_falso(ANTIGAS, aviso=AVISO_SM120)):
            rc, saida, exc = rodar_main(["--biblioteca", "torch", "--repeticoes", "2",
                                         "--aquecimento", "0"])
    finally:
        md.cargas_torch = original
    confere(exc is None and rc == 0, "main com GPU quebrada termina sem traceback (rc 0)")
    confere("Traceback" not in saida, "nenhum Traceback na saida")
    confere("ERRO" in saida and "erro" in saida, "a tabela mostra a GPU como erro")
    confere("olhe: sm_120 NAO esta na lista" in saida, "relata sm_120 fora da lista")
    confere("cu130" in saida, "a saida diz o caminho (--torch-backend cu130)")
    confere("O que isto NAO significa" in saida, "termina dizendo o que nao significa")
    linhas_fim = [l for l in saida.splitlines() if l.startswith(("achei", "nao achei",
                                                                 "olhe"))]
    confere(len(linhas_fim) >= 4, "linhas finais em achei / nao achei / olhe (%d)"
            % len(linhas_fim))
    confere(not any(p in saida.lower() for p in PROIBIDAS), "nenhuma frase de veredito")


class _Device:
    atual = []

    def __init__(self, nome):
        self.nome = nome

    def __enter__(self):
        _Device.atual.append(self.nome)

    def __exit__(self, *a):
        _Device.atual.pop()


def tf_e_keras_falsos():
    tf = types.ModuleType("tensorflow")
    tf.__version__ = "2.21.0"
    gpu = types.SimpleNamespace(name="/physical_device:GPU:0")
    tf.config = types.SimpleNamespace(
        list_physical_devices=lambda tipo: [gpu],
        experimental=types.SimpleNamespace(enable_op_determinism=lambda: None))
    tf.sysconfig = types.SimpleNamespace(get_build_info=lambda: {"cuda_version": "12.5.1"})
    tf.device = _Device
    keras = types.ModuleType("keras")
    keras.__version__ = "3.12.4"
    keras.backend = types.SimpleNamespace(backend=lambda: "tensorflow")
    return tf, keras


def grupo4():
    print("4. dubles do TensorFlow (sem GPU de verdade)")
    original = md.cargas_tf

    def cargas(tf, keras, grande):
        def montar():
            if _Device.atual and "GPU" in _Device.atual[-1]:
                os.write(2, LOG_TF.encode())        # o C++ escreve no descritor 2
                raise RuntimeError("InternalError: " + ERRO_PTX)
            return lambda: None
        return [("cnn-treino", montar)]
    md.cargas_tf = cargas
    tf, keras = tf_e_keras_falsos()
    try:
        with modulos_falsos(tensorflow=tf, keras=keras):
            rc, saida, exc = rodar_main(["--biblioteca", "tensorflow", "--repeticoes", "2",
                                         "--aquecimento", "0"])
    finally:
        md.cargas_tf = original
    confere(exc is None and rc == 0, "main com INVALID_PTX termina sem traceback (rc 0)")
    confere("achei: 1 GPU(s) visivel(is) pelo TensorFlow" in saida, "relata a GPU visivel")
    confere("CUDA_ERROR_INVALID_PTX" in saida, "a mensagem literal aparece")
    confere("compute capability 12.0" in saida, "a linha do log C++ capturada aparece")
    confere("tensorflow-cpu" in saida, "a explicacao aponta o plano B")

    with md.capturar_stderr(True) as caixa:
        os.write(2, b"linha do C++\n")
    confere(caixa and "linha do C++" in caixa[0], "capturar_stderr pega o descritor 2")
    with md.capturar_stderr(False) as caixa:
        pass
    confere(caixa == [], "capturar_stderr(False) nao mexe em nada")


def grupo5(pythons):
    print("5. o script de verdade, em CPU")
    if not pythons:
        print("  [pulado] nenhum --python dado (ex.: --python \"$PB_DIR/.venv-rl/bin/python\")")
        return
    for py in pythons:
        r = subprocess.run([py, "-B", str(AQUI / "medir_dispositivo.py"), "--repeticoes", "3",
                            "--aquecimento", "1"], capture_output=True, text=True,
                           timeout=900)
        s = r.stdout
        confere(r.returncode == 0 and "Traceback" not in s + r.stderr,
                "%s: roda sem traceback" % py)
        confere("cpu (ms/lote)" in s and "cnn-treino" in s, "%s: tabela com cnn-treino" % py)
        confere("O que isto NAO significa" in s, "%s: termina com o que nao significa" % py)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--python", action="append", default=[],
                    help="um Python de venv com torch ou tensorflow (pode repetir)")
    a = ap.parse_args()
    grupo1()
    grupo2()
    grupo3()
    grupo4()
    grupo5(a.python)
    if FALHAS:
        print("\n%d conferencia(s) falharam." % len(FALHAS))
        return 1
    print("\ntodos os testes passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
