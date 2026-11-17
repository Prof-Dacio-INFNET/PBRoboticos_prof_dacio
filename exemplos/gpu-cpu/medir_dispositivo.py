#!/usr/bin/env python3
"""Mede, nesta maquina, quanto tempo cargas parecidas com as do curso levam na CPU e na GPU.

    "$PB_DIR/.venv-rl-gpu/bin/python"  medir_dispositivo.py     # o venv do torch com GPU
    "$PB_DIR/.venv-cnn-gpu/bin/python" medir_dispositivo.py     # o venv do TensorFlow com GPU
    "$PB_DIR/.venv-rl/bin/python"      medir_dispositivo.py     # o de CPU tambem serve

APOIO, NAO VEREDITO. O script relata o que achou (achei / nao achei / olhe). Ele nao
valida a instalacao, nao diz que dispositivo usar, nao antecipa nota e nao substitui
o enunciado. Uma carga sintetica nao e o seu treino: o seu treino tem simulador,
disco e Python em volta, e e isso que mais pesa.

Roda com o Python de QUALQUER venv: usa o torch se existir, o TensorFlow se existir,
os dois se existirem, e diz o que faltou. Cargas (todas com dados aleatorios):

    mlp-passo   MLP 25 -> 256 -> 256 -> 5, lote 1, so a ida: o PPO escolhendo UMA acao
                a cada passo do simulador (o caso da coleta)
    mlp-treino  a mesma MLP, lote 64, ida + volta + Adam: a atualizacao do PPO
    cnn-treino  3 blocos Conv3x3(16/32/64)-BN-ReLU-MaxPool, densa 64, dropout 0.5,
                imagens 128x96x3, lote 32, ida + volta + Adam: as CNNs das Aulas 17 e 18
    cnn-grande  (so com --grande) 64/128/256 filtros, 224x224, lote 32: uma carga do
                tamanho em que a GPU costuma pagar; NAO existe no curso

Cada carga roda --aquecimento lotes descartados (a primeira vez na GPU inclui
compilacao e copia) e depois --repeticoes lotes cronometrados; a tabela traz a
MEDIANA em milissegundos por lote. razao = cpu / gpu: acima de 1 a GPU levou menos
tempo por lote; abaixo de 1, mais.
"""
import argparse
import contextlib
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import warnings

CABECALHO = (
    "medir_dispositivo.py -- APOIO, NAO VEREDITO: relata o que mediu nesta maquina.\n"
    "Nao valida a instalacao, nao diz o que usar, nao substitui o enunciado.")

MLP_ENTRADA = 25      # a observacao do highway-fast-v0: 5 veiculos x 5 numeros
MLP_OCULTA = 256      # a rede do treinar_ppo.py: [256, 256]
MLP_SAIDA = 5         # as 5 acoes discretas do highway-env
MLP_LOTE = 64         # o LOTE do treinar_ppo.py
CNN_ALTURA, CNN_LARGURA = 96, 128   # o --tamanho padrao do aula17-cnn
CNN_FILTROS = (16, 32, 64)
CNN_DENSA = 64
CNN_LOTE = 32
CNN_CLASSES = 3
GRANDE_LADO = 224
GRANDE_FILTROS = (64, 128, 256)

# Mensagens literais conhecidas -> o que elas querem dizer. A ordem importa: a
# primeira que casar ganha. Tudo em minusculas (a comparacao e sem caixa).
DIAGNOSTICOS = (
    ("is not compatible with the current pytorch installation",
     "este torch nao traz codigo para a arquitetura desta GPU (na serie RTX 50 e a "
     "sm_120): o torch foi instalado de um indice antigo (cu126 ou anterior). "
     "Reinstale num venv novo com --torch-backend cu130"),
    ("no kernel image is available",
     "a biblioteca nao tem codigo compilado para a arquitetura desta GPU. Na serie "
     "RTX 50 (sm_120): torch de indice antigo (use --torch-backend cu130); no "
     "TensorFlow, os pacotes oficiais podem nao trazer a sm_120"),
    ("cuda_error_invalid_ptx",
     "o TensorFlow tentou compilar na hora (PTX) o codigo para esta GPU e o driver "
     "recusou. E o sintoma conhecido do TensorFlow oficial na serie RTX 50: fique no "
     "tensorflow-cpu (o padrao do curso) ou siga o plano B do tutorial"),
    ("not built with cuda kernel binaries compatible with compute capability",
     "o TensorFlow avisa que nao foi compilado para esta GPU e vai tentar compilar na "
     "hora (PTX). Pode funcionar devagar, pode demorar muito no primeiro lote, pode "
     "falhar com CUDA_ERROR_INVALID_PTX"),
    ("jit compilation failed",
     "a compilacao na hora (XLA/PTX) falhou para esta GPU: mesmo caso da serie RTX 50 "
     "sem suporte no TensorFlow instalado"),
    ("ptxas",
     "o compilador ptxas falhou: o ptxas que veio com o pacote nao conhece esta "
     "arquitetura de GPU"),
    ("driver version is insufficient",
     "o driver NVIDIA e mais velho que o CUDA destes pacotes. No WSL2 o driver e o do "
     "WINDOWS: atualize-o la (nunca instale driver NVIDIA dentro do WSL)"),
    ("nvidia driver on your system is too old",
     "o driver NVIDIA e mais velho que o CUDA deste torch. No WSL2 o driver e o do "
     "WINDOWS: atualize-o la; ou instale o torch de um indice mais antigo (cu129)"),
    ("cuda_error_no_device",
     "a biblioteca nao enxergou GPU nenhuma. No WSL2: confira nvidia-smi dentro do "
     "Ubuntu e o driver do Windows"),
    ("no deterministic",
     "o determinismo (enable_op_determinism, o mesmo dos scripts do curso) nao tem "
     "implementacao para alguma operacao nesta GPU"),
    ("out of memory",
     "a GPU ficou sem memoria: feche outros programas que usam a GPU ou rode com "
     "lote menor"),
)

TERMOS_DE_LOG = ("compute capability", "ptx", "cuda_error", "no kernel image",
                 "jit compilation", "ptxas", "driver version", "could not find cuda",
                 "cannot dlopen", "skipping registering gpu", "deterministic")


def diagnosticar(texto):
    """Mensagem de erro (ou log) -> explicacao em portugues, ou None. Funcao pura."""
    baixo = (texto or "").lower()
    for chave, explicacao in DIAGNOSTICOS:
        if chave in baixo:
            return explicacao
    return None


def linhas_relevantes(log, limite=8):
    """As linhas de um log do TensorFlow/CUDA que falam de GPU, arquitetura ou driver."""
    saida = []
    for linha in (log or "").splitlines():
        if any(t in linha.lower() for t in TERMOS_DE_LOG):
            saida.append(linha.strip()[:160])
    return saida[:limite]


def mediana_ms(tempos_s):
    """Lista de segundos -> mediana em milissegundos (None se a lista for vazia)."""
    if not tempos_s:
        return None
    return 1000.0 * statistics.median(tempos_s)


def razao(cpu_ms, gpu_ms):
    """cpu / gpu; None se faltar um dos dois."""
    if cpu_ms is None or gpu_ms is None or gpu_ms <= 0:
        return None
    return cpu_ms / gpu_ms


def fmt_ms(v):
    return "-" if v is None else ("%.2f" % v if v < 10 else "%.1f" % v)


def fmt_razao(r):
    return "-" if r is None else "%.2f" % r


def tabela(linhas):
    """[(biblioteca, carga, cpu_ms, gpu_ms, nota)] -> texto da tabela."""
    cab = ("biblioteca", "carga", "cpu (ms/lote)", "gpu (ms/lote)", "razao")
    corpo = []
    for bib, carga, cpu, gpu, nota in linhas:
        r = razao(cpu, gpu)
        g = fmt_ms(gpu) if gpu is not None else (nota or "-")
        corpo.append((bib, carga, fmt_ms(cpu), g, fmt_razao(r)))
    larg = [max(len(str(x[i])) for x in [cab] + corpo) for i in range(len(cab))]
    out = [" | ".join(str(c).ljust(larg[i]) for i, c in enumerate(cab))]
    out.append("-+-".join("-" * w for w in larg))
    for lin in corpo:
        out.append(" | ".join(str(c).ljust(larg[i]) for i, c in enumerate(lin)))
    return "\n".join(out)


def observacoes(linhas):
    """Frases factuais sobre a tabela: o que a medida mostrou, sem recomendar nada."""
    obs = []
    for bib, carga, cpu, gpu, _ in linhas:
        r = razao(cpu, gpu)
        if r is None:
            continue
        if r >= 1.2:
            obs.append("olhe: %s %s -- a GPU levou %.1fx MENOS tempo por lote que a CPU"
                       % (bib, carga, r))
        elif r <= 1 / 1.2:
            obs.append("olhe: %s %s -- a GPU levou %.1fx MAIS tempo por lote que a CPU"
                       % (bib, carga, 1 / r))
        else:
            obs.append("olhe: %s %s -- CPU e GPU ficaram na mesma faixa (razao %.2f)"
                       % (bib, carga, r))
    return obs


def e_wsl(texto_proc_version):
    """O conteudo de /proc/version diz que isto e um WSL? Funcao pura."""
    return "microsoft" in (texto_proc_version or "").lower()


def ler(caminho):
    try:
        with open(caminho) as arq:
            return arq.read()
    except OSError:
        return ""


def nvidia_smi():
    """(caminho, linha 'nome, driver, capacidade') ou (None, motivo)."""
    exe = shutil.which("nvidia-smi")
    if not exe and os.path.exists("/usr/lib/wsl/lib/nvidia-smi"):
        exe = "/usr/lib/wsl/lib/nvidia-smi"
    if not exe:
        return None, "nvidia-smi nao existe neste sistema"
    try:
        r = subprocess.run([exe, "--query-gpu=name,driver_version,compute_cap",
                            "--format=csv,noheader"], capture_output=True, text=True,
                           timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "nvidia-smi nao rodou: %s" % e
    if r.returncode != 0:
        return None, "nvidia-smi saiu com %d: %s" % (r.returncode,
                                                    (r.stderr or r.stdout).strip()[:120])
    return exe, r.stdout.strip()


@contextlib.contextmanager
def capturar_stderr(ativo=True):
    """Desvia o descritor 2 (onde o C++ do TensorFlow/CUDA escreve) para um arquivo.

    Entrega uma lista que, na saida, recebe o texto capturado. Sem isso as linhas
    que dizem 'compute capability 12.0' se perdem no meio de dezenas de outras.
    """
    caixa = []
    if not ativo:
        yield caixa
        return
    sys.stderr.flush()
    salvo = os.dup(2)
    tmp = tempfile.TemporaryFile(mode="w+b")
    os.dup2(tmp.fileno(), 2)
    try:
        yield caixa
    finally:
        sys.stderr.flush()
        os.dup2(salvo, 2)
        os.close(salvo)
        tmp.seek(0)
        caixa.append(tmp.read().decode("utf-8", "replace"))
        tmp.close()


def cronometrar(passo, sincronizar, aquecimento, repeticoes):
    """Roda passo() aquecimento+repeticoes vezes; devolve os tempos das repeticoes."""
    for _ in range(aquecimento):
        passo()
    sincronizar()
    tempos = []
    for _ in range(repeticoes):
        t0 = time.perf_counter()
        passo()
        sincronizar()
        tempos.append(time.perf_counter() - t0)
    return tempos


def medir_com_seguranca(medir, rotulo):
    """Chama medir(); devolve (ms, None) ou (None, nota) sem deixar o traceback subir.

    E aqui que o erro da serie RTX 50 vira uma frase em vez de 40 linhas de pilha.
    """
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        try:
            return mediana_ms(medir()), None, avisos_uteis(avisos)
        except Exception as e:  # noqa: BLE001  (qualquer erro da GPU vira relato)
            msg = "%s: %s" % (type(e).__name__, str(e).strip().splitlines()[0][:200]
                              if str(e).strip() else "")
            return None, "erro", [msg] + avisos_uteis(avisos)


def avisos_uteis(avisos):
    """Descarta os avisos de deprecacao (o NumPy 2 gera dezenas deles no Keras)."""
    return [str(a.message) for a in avisos
            if not issubclass(a.category, (DeprecationWarning, FutureWarning))]


# ---------------------------------------------------------------------------
# torch
# ---------------------------------------------------------------------------
def inspecionar_torch(torch):
    """O que o torch diz da GPU. Recebe o modulo (o testar.py passa um duble)."""
    info = {"versao": getattr(torch, "__version__", "?"),
            "cuda_compilado": getattr(getattr(torch, "version", None), "cuda", None),
            "disponivel": False, "nome": None, "capacidade": None, "arquiteturas": [],
            "arquitetura_na_lista": None, "avisos": []}
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        try:
            info["disponivel"] = bool(torch.cuda.is_available())
            if info["disponivel"]:
                info["nome"] = torch.cuda.get_device_name(0)
                info["capacidade"] = tuple(torch.cuda.get_device_capability(0))
                info["arquiteturas"] = list(torch.cuda.get_arch_list())
        except Exception as e:  # noqa: BLE001
            info["avisos"].append("%s: %s" % (type(e).__name__, e))
        info["avisos"] += avisos_uteis(avisos)
    if info["capacidade"]:
        maior, menor = info["capacidade"]
        alvo = "sm_%d%d" % (maior, menor)
        info["sm"] = alvo
        info["arquitetura_na_lista"] = alvo in info["arquiteturas"]
    return info


def cargas_torch(torch, dispositivo, grande):
    """{nome: funcao_passo} para o dispositivo dado ('cpu' ou 'cuda')."""
    nn = torch.nn
    torch.manual_seed(0)
    dev = torch.device(dispositivo)

    def mlp():
        return nn.Sequential(nn.Linear(MLP_ENTRADA, MLP_OCULTA), nn.Tanh(),
                             nn.Linear(MLP_OCULTA, MLP_OCULTA), nn.Tanh(),
                             nn.Linear(MLP_OCULTA, MLP_SAIDA)).to(dev)

    def cnn(filtros, altura, largura, classes):
        camadas, entra = [], 3
        for f in filtros:
            camadas += [nn.Conv2d(entra, f, 3, padding=1, bias=False), nn.BatchNorm2d(f),
                        nn.ReLU(), nn.MaxPool2d(2)]
            entra = f
        plano = entra * (altura // 8) * (largura // 8)
        camadas += [nn.Flatten(), nn.Linear(plano, CNN_DENSA), nn.ReLU(), nn.Dropout(0.5),
                     nn.Linear(CNN_DENSA, classes)]
        return nn.Sequential(*camadas).to(dev)

    def passo_treino(modelo, x, y):
        opt = torch.optim.Adam(modelo.parameters(), lr=1e-3)
        perda = nn.CrossEntropyLoss()

        def passo():
            opt.zero_grad(set_to_none=True)
            perda(modelo(x), y).backward()
            opt.step()
        return passo

    rede_passo = mlp()
    obs1 = torch.randn(1, MLP_ENTRADA, device=dev)

    def mlp_passo():
        with torch.no_grad():
            rede_passo(obs1).argmax(dim=1)

    x64 = torch.randn(MLP_LOTE, MLP_ENTRADA, device=dev)
    y64 = torch.randint(0, MLP_SAIDA, (MLP_LOTE,), device=dev)
    xi = torch.rand(CNN_LOTE, 3, CNN_ALTURA, CNN_LARGURA, device=dev)
    yi = torch.randint(0, CNN_CLASSES, (CNN_LOTE,), device=dev)
    cargas = [("mlp-passo", mlp_passo),
              ("mlp-treino", passo_treino(mlp(), x64, y64)),
              ("cnn-treino", passo_treino(cnn(CNN_FILTROS, CNN_ALTURA, CNN_LARGURA,
                                              CNN_CLASSES), xi, yi))]
    if grande:
        xg = torch.rand(CNN_LOTE, 3, GRANDE_LADO, GRANDE_LADO, device=dev)
        yg = torch.randint(0, 10, (CNN_LOTE,), device=dev)
        cargas.append(("cnn-grande", passo_treino(cnn(GRANDE_FILTROS, GRANDE_LADO,
                                                      GRANDE_LADO, 10), xg, yg)))
    return cargas


def medir_torch(args, linhas, achados):
    try:
        import torch
    except ImportError:
        achados.append("nao achei: torch neste Python (%s)" % sys.executable)
        return
    info = inspecionar_torch(torch)
    achados.append("achei: torch %s (CUDA no pacote: %s), %d thread(s) na CPU"
                   % (info["versao"], info["cuda_compilado"] or "nenhum -- pacote so CPU",
                      torch.get_num_threads()))
    print("\n[torch %s] cuda no pacote: %s; torch.cuda.is_available(): %s"
          % (info["versao"], info["cuda_compilado"] or "nenhum", info["disponivel"]))
    if info["disponivel"]:
        print("  GPU: %s, capacidade %s (%s)" % (info["nome"], info["capacidade"], info["sm"]))
        print("  arquiteturas deste torch: %s" % " ".join(info["arquiteturas"]))
        achados.append("achei: GPU %s (%s) vista pelo torch" % (info["nome"], info["sm"]))
        if not info["arquitetura_na_lista"]:
            achados.append("olhe: %s NAO esta na lista de arquiteturas deste torch (%s)"
                           % (info["sm"], " ".join(info["arquiteturas"])))
    elif info["cuda_compilado"]:
        achados.append("nao achei: GPU pelo torch (o pacote tem CUDA %s, mas "
                       "torch.cuda.is_available() deu False)" % info["cuda_compilado"])
    for aviso in info["avisos"]:
        print("  aviso do torch: %s" % aviso.strip().splitlines()[0][:200])
        d = diagnosticar(aviso)
        if d:
            achados.append("olhe: %s" % d)

    def sync_cpu():
        pass

    def sync_gpu():
        torch.cuda.synchronize()

    resultados = {}
    for disp, sync in (("cpu", sync_cpu), ("cuda", sync_gpu)):
        if disp == "cuda" and (not info["disponivel"] or args.so_cpu):
            continue
        print("  medindo em %s ..." % disp, flush=True)
        try:
            cargas = cargas_torch(torch, disp, args.grande)
        except Exception as e:  # noqa: BLE001
            nota = "%s: %s" % (type(e).__name__, str(e).strip().splitlines()[0][:200])
            print("    nao consegui montar as redes em %s: %s" % (disp, nota))
            d = diagnosticar(nota)
            achados.append("olhe: torch em %s -- %s" % (disp, d or nota))
            continue
        for nome, passo in cargas:
            ms, nota, msgs = medir_com_seguranca(
                lambda: cronometrar(passo, sync, args.aquecimento, args.repeticoes), nome)
            resultados[(disp, nome)] = (ms, nota)
            print("    %-11s %s" % (nome, fmt_ms(ms) + " ms/lote" if ms is not None
                                      else "ERRO"), flush=True)
            for m in msgs:
                print("      mensagem: %s" % m[:200])
                d = diagnosticar(m)
                if d:
                    achados.append("olhe: torch %s em %s -- %s" % (nome, disp, d))
    for nome in ("mlp-passo", "mlp-treino", "cnn-treino", "cnn-grande"):
        if ("cpu", nome) not in resultados:
            continue
        cpu = resultados[("cpu", nome)][0]
        gpu, nota = resultados.get(("cuda", nome), (None, "sem GPU"))
        linhas.append(("torch", nome, cpu, gpu, nota))


# ---------------------------------------------------------------------------
# TensorFlow / Keras
# ---------------------------------------------------------------------------
def cargas_tf(tf, keras, grande):
    """[(nome, construtor)] -- cada construtor devolve passo() no dispositivo corrente."""
    layers = keras.layers

    def mlp():
        e = keras.Input(shape=(MLP_ENTRADA,))
        x = layers.Dense(MLP_OCULTA, activation="tanh")(e)
        x = layers.Dense(MLP_OCULTA, activation="tanh")(x)
        return keras.Model(e, layers.Dense(MLP_SAIDA)(x))

    def cnn(filtros, altura, largura, classes):
        e = keras.Input(shape=(altura, largura, 3))
        x = e
        for f in filtros:
            x = layers.Conv2D(f, 3, padding="same", use_bias=False)(x)
            x = layers.BatchNormalization(momentum=0.9)(x)
            x = layers.Activation("relu")(x)
            x = layers.MaxPooling2D()(x)
        x = layers.Flatten()(x)
        x = layers.Dense(CNN_DENSA, activation="relu")(x)
        x = layers.Dropout(0.5, seed=0)(x)
        return keras.Model(e, layers.Dense(classes, activation="softmax")(x))

    import numpy as np
    rng = np.random.default_rng(0)

    def treino(construir, x, y, perda):
        def montar():
            keras.utils.set_random_seed(0)
            m = construir()
            m.compile(optimizer=keras.optimizers.Adam(1e-3), loss=perda)

            def passo():
                m.train_on_batch(x, y)
            return passo
        return montar

    def passo_mlp():
        keras.utils.set_random_seed(0)
        m = mlp()
        obs = tf.constant(rng.standard_normal((1, MLP_ENTRADA)).astype("float32"))

        def passo():
            m(obs, training=False).numpy()
        return passo

    x64 = rng.standard_normal((MLP_LOTE, MLP_ENTRADA)).astype("float32")
    y64 = rng.integers(0, MLP_SAIDA, MLP_LOTE)
    xi = rng.random((CNN_LOTE, CNN_ALTURA, CNN_LARGURA, 3)).astype("float32")
    yi = rng.integers(0, CNN_CLASSES, CNN_LOTE)
    perda = "sparse_categorical_crossentropy"
    cargas = [("mlp-passo", passo_mlp),
              ("mlp-treino", treino(mlp, x64, y64, keras.losses.SparseCategoricalCrossentropy(
                  from_logits=True))),
              ("cnn-treino", treino(lambda: cnn(CNN_FILTROS, CNN_ALTURA, CNN_LARGURA,
                                                CNN_CLASSES), xi, yi, perda))]
    if grande:
        xg = rng.random((CNN_LOTE, GRANDE_LADO, GRANDE_LADO, 3)).astype("float32")
        yg = rng.integers(0, 10, CNN_LOTE)
        cargas.append(("cnn-grande", treino(lambda: cnn(GRANDE_FILTROS, GRANDE_LADO,
                                                        GRANDE_LADO, 10), xg, yg, perda)))
    return cargas


def medir_tf(args, linhas, achados):
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")   # some o INFO, ficam os avisos
    with capturar_stderr(not args.sem_captura) as caixa:
        try:
            import tensorflow as tf
            import keras
            erro_import = None
        except ImportError as e:
            erro_import = e
        except Exception as e:  # noqa: BLE001  (TensorFlow quebrado tambem e relato)
            erro_import = e
        gpus = []
        if erro_import is None:
            try:
                gpus = tf.config.list_physical_devices("GPU")
            except Exception:  # noqa: BLE001
                gpus = []
    log_import = caixa[0] if caixa else ""
    if erro_import is not None:
        if isinstance(erro_import, ImportError) and "tensorflow" in str(erro_import):
            achados.append("nao achei: tensorflow neste Python (%s)" % sys.executable)
        else:
            achados.append("olhe: o tensorflow existe mas nao importou: %s" % erro_import)
        return
    backend = keras.backend.backend()
    print("\n[tensorflow %s, keras %s, backend %s] GPUs visiveis: %s"
          % (tf.__version__, keras.__version__, backend,
             ", ".join(g.name for g in gpus) or "nenhuma"))
    cuda_tf = tf.sysconfig.get_build_info().get("cuda_version", None)
    achados.append("achei: tensorflow %s (CUDA no pacote: %s), keras %s com backend %s"
                   % (tf.__version__, cuda_tf or "nenhum -- pacote so CPU",
                      keras.__version__, backend))
    if gpus:
        achados.append("achei: %d GPU(s) visivel(is) pelo TensorFlow" % len(gpus))
    elif cuda_tf:
        achados.append("nao achei: GPU pelo TensorFlow (o pacote tem CUDA %s)" % cuda_tf)
    for linha in linhas_relevantes(log_import):
        print("  log: %s" % linha)
    if backend != "tensorflow":
        achados.append("olhe: KERAS_BACKEND=%s; as cargas do TensorFlow foram puladas"
                       % backend)
        return
    if not args.sem_determinismo:
        # o mesmo que os scripts do curso fazem; na GPU algumas operacoes recusam
        tf.config.experimental.enable_op_determinism()
    dispositivos = [("cpu", "/CPU:0")]
    if gpus and not args.so_cpu:
        dispositivos.append(("gpu", "/GPU:0"))
    resultados = {}
    for rot, dev in dispositivos:
        print("  medindo em %s ...%s" % (rot, " (o primeiro lote na GPU pode demorar: "
                                               "compilacao)" if rot == "gpu" else ""),
              flush=True)
        for nome, montar in cargas_tf(tf, keras, args.grande):
            def medir():
                with tf.device(dev):
                    passo = montar()
                    return cronometrar(passo, lambda: None, args.aquecimento,
                                       args.repeticoes)
            with capturar_stderr(not args.sem_captura and rot == "gpu") as cx:
                ms, nota, msgs = medir_com_seguranca(medir, nome)
            log = cx[0] if cx else ""
            resultados[(rot, nome)] = (ms, nota)
            print("    %-11s %s" % (nome, fmt_ms(ms) + " ms/lote" if ms is not None
                                      else "ERRO"), flush=True)
            for m in msgs + linhas_relevantes(log):
                print("      mensagem: %s" % m[:200])
            d = diagnosticar("\n".join(msgs) + "\n" + log)
            if d:
                achados.append("olhe: tensorflow %s em %s -- %s" % (nome, rot, d))
    for nome in ("mlp-passo", "mlp-treino", "cnn-treino", "cnn-grande"):
        if ("cpu", nome) not in resultados:
            continue
        cpu = resultados[("cpu", nome)][0]
        gpu, nota = resultados.get(("gpu", nome), (None, "sem GPU"))
        linhas.append(("tensorflow", nome, cpu, gpu, nota))


def argumentos(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--biblioteca", choices=("auto", "torch", "tensorflow"), default="auto",
                   help="auto: mede o que estiver instalado neste Python")
    p.add_argument("--repeticoes", type=int, default=20, help="lotes cronometrados (20)")
    p.add_argument("--aquecimento", type=int, default=3, help="lotes descartados (3)")
    p.add_argument("--grande", action="store_true",
                   help="inclui a cnn-grande (224x224, 64/128/256): lenta na CPU")
    p.add_argument("--so-cpu", action="store_true", help="nao mede a GPU")
    p.add_argument("--sem-determinismo", action="store_true",
                   help="TensorFlow sem enable_op_determinism (os scripts do curso usam)")
    p.add_argument("--sem-captura", action="store_true",
                   help="nao desvia o stderr do TensorFlow (use se o processo morrer mudo)")
    return p.parse_args(argv)


def main(argv=None):
    a = argumentos(argv)
    print(CABECALHO)
    print("\nPython %s em %s" % (platform.python_version(), sys.executable))
    wsl = e_wsl(ler("/proc/version"))
    print("sistema: %s%s, %s nucleo(s) logicos"
          % (platform.system(), " (WSL)" if wsl else "", os.cpu_count()))
    achados = []
    exe, smi = nvidia_smi()
    if exe:
        print("nvidia-smi (%s): %s" % (exe, smi))
        achados.append("achei: nvidia-smi -> %s" % smi)
    else:
        print("nvidia-smi: %s" % smi)
        achados.append("nao achei: nvidia-smi (%s)" % smi)
    linhas = []
    if a.biblioteca in ("auto", "torch"):
        medir_torch(a, linhas, achados)
    if a.biblioteca in ("auto", "tensorflow"):
        medir_tf(a, linhas, achados)

    print("\n=== mediana de %d lotes (depois de %d de aquecimento) ===" % (a.repeticoes,
                                                                          a.aquecimento))
    if linhas:
        print(tabela(linhas))
        print("razao = cpu / gpu: acima de 1 a GPU levou menos tempo por lote; abaixo, mais.")
    else:
        print("(nada medido: nem torch nem tensorflow neste Python)")
    print("")
    for linha in achados + observacoes(linhas):
        print(linha)
    print("\nO que isto NAO significa: uma carga sintetica nao e o seu treino. No PPO o "
          "tempo\nesta no simulador (Python puro), nao na rede; nas CNNs do curso, em "
          "carregar\nimagens e no Python em volta. Meca o seu treino de verdade nos dois "
          "dispositivos\ne relate dispositivo e tempo no relatorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
