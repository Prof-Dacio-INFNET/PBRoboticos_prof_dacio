---
titulo: "CPU ou GPU: os dois caminhos"
tipo: ambiente
etapa: 9
alvo: "Ubuntu 22.04 (jammy) sobre WSL2 ou nativo · torch e TensorFlow em venvs do uv"
opcional: true
---

# CPU ou GPU: os dois caminhos

> **A regra do curso: tudo roda em CPU, a GPU é opcional, e nenhum TP exige GPU.** Todos os números publicados nos exemplos saíram de CPU (e, quando aparecem números da máquina do professor, a página diz qual foi o dispositivo). Se o seu notebook tem uma placa NVIDIA, este guia mostra como usá-la **sem quebrar o ambiente que já funciona** — e, antes disso, onde ela ajuda e onde não ajuda nas cargas desta disciplina.

**Para quem é.** Para quem tem GPU NVIDIA e quer saber se vale a pena; para quem não tem e quer saber se está perdendo alguma coisa (resposta curta: nas cargas do curso, quase nada); e para quem tem uma placa da **série RTX 50** (5050, 5060, 5070, 5080, 5090), que é o caso com mais armadilha — ela tem [uma seção própria](#serie-rtx-50-a-armadilha-da-arquitetura-nova).

**O que este guia não é.** Não é um guia de CUDA. Nada aqui instala o *CUDA Toolkit* do sistema: o torch e o TensorFlow trazem as bibliotecas CUDA deles dentro do venv, e o que o sistema precisa é só do **driver**.

## Onde a GPU ajuda e onde não ajuda, nas cargas do curso

Os números abaixo são os **medidos** nos exemplos; nenhum é promessa de ganho. "Container" é a máquina onde o material foi escrito (Linux, 2 núcleos, **sem GPU**); "professor" é um notebook com WSL2.

| carga do curso | onde o tempo vai | o que foi medido | a GPU muda alguma coisa? |
|---|---|---|---|
| **Câmera do MetaDrive** (Aulas 17 e 18: capturar quadros, gravar o dataset do BC, o BC dirigindo) | desenhar a imagem (OpenGL) | container, renderização por software: **0,37 a 0,5 quadro/s**; professor, WSL2 com WSLg: **6,9 a 8,8 quadros/s** na captura da Aula 17 e **14,7 quadros/s** gravando o dataset da Aula 18 | **Sim, e muito** — e isso **não precisa de CUDA**: no WSL2 o desenho vai para a placa de vídeo pelo WSLg sozinho. A [seção do render](#render-o-metadrive-ja-usa-a-gpu-sem-cuda) mostra como conferir qual placa está desenhando |
| **PPO com `MlpPolicy`** (Aula 18, `aula18-ppo`) | o simulador `highway-fast-v0`, que é Python puro | container: **28 passos/s** no treino, **35 passos/s** só o simulador; professor: **50 a 58 passos/s** (CPU). A rede escolhendo **uma** ação leva **0,04 ms** na CPU do container (`medir_dispositivo.py`), contra **~29 ms** de cada passo do simulador | **Não.** A rede é ~0,1% do passo; não há o que acelerar. A documentação do Stable Baselines3 diz: *"PPO is meant to be run primarily on the CPU, especially when you are not using a CNN"*, e a própria biblioteca avisa, ao receber `device="cuda"` com `MlpPolicy`, que *"the training might take longer than on CPU"* |
| **CNN da Aula 17** (`aula17-cnn`, 500 imagens 128×96, 20 épocas) | as convoluções e o Python em volta | container: **38 a 45 s por rodada**; um lote de 32 levou **~100 a 124 ms** na CPU (`medir_dispositivo.py`), ou seja ~30 s das 20 épocas são conta | **Pouco, em tempo absoluto.** A conta é a parte que a GPU acelera, mas o total já é de um minuto. Ganho não medido aqui |
| **BC da Aula 18** (`aula18-pid-bc`, `treinar_bc.py`) | idem, com imagens menores (80×35) | professor, CPU: **42 a 46 s** | idem |
| **YOLO** (Aula 13, `ultralytics`) e treinos maiores do seu projeto | convoluções grandes | uma CNN de 224×224 com 64/128/256 filtros (`medir_dispositivo.py --grande`) levou **2,9 s por lote** na CPU do container | **É aqui que a GPU paga.** Nenhuma medida em GPU foi feita para este material |

!!! warning "A mesma semente não dá a mesma tabela em outro dispositivo"
    Isso já foi medido duas vezes neste curso, **sem** GPU nenhuma no meio: na Aula 18, o BC treinado no notebook do professor variou na terceira casa entre duas execuções (no container, era idêntico byte a byte), e o BC treinado com os quadros desenhados pela placa de vídeo **dirigiu diferente** (10 de 10 contra 8 de 10). Trocar CPU por GPU, ou trocar o adaptador que desenha a câmera, muda os números. **Treine e meça no mesmo dispositivo, e escreva no relatório qual foi** — dispositivo, versão da biblioteca e tempo.

## Tenho GPU NVIDIA? Três comandos

No **PowerShell do Windows** (só para WSL2):

```powershell
nvidia-smi
wsl --version
```

No **terminal do Ubuntu** (WSL2 ou nativo):

```bash
nvidia-smi
```

```bash
ls /usr/lib/wsl/lib 2>/dev/null | grep -i -E "cuda|nvidia" || echo "nao achei /usr/lib/wsl/lib com bibliotecas NVIDIA (normal em Ubuntu nativo)"
```

O que pode aparecer:

| no Ubuntu, o `nvidia-smi`... | quer dizer | caminho |
|---|---|---|
| mostra a tabela com o nome da placa, `Driver Version` e `CUDA Version` | o driver está pronto. No WSL2, o número é o do driver **do Windows** | pode seguir para o [caminho GPU](#caminho-gpu-cada-biblioteca-num-venv-novo) |
| `command not found`, no WSL2, mas `ls /usr/lib/wsl/lib` lista `libcuda.so` e `nvidia-smi` | o driver está lá; o `PATH` é que não inclui a pasta | rode `/usr/lib/wsl/lib/nvidia-smi` |
| `command not found`, no WSL2, e a pasta não tem nada da NVIDIA | o Windows não tem driver NVIDIA, ou a placa não é NVIDIA | instale o driver **no Windows** (abaixo) e rode `wsl --shutdown` |
| `NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver`, em Ubuntu **nativo** | não há driver carregado | [Ubuntu nativo](#ubuntu-nativo) |
| `command not found` e o notebook não tem NVIDIA | AMD, Intel ou só vídeo integrado | [fique no CPU](#sem-gpu-nvidia-amd-ou-intel) — e o render do WSLg continua usando a sua placa |

!!! danger "No WSL2, nunca instale driver NVIDIA dentro do Ubuntu"
    O driver é **um só, o do Windows**. A documentação da NVIDIA é literal: *"Do not install any driver within the WSL environment"* e *"you must not install any NVIDIA Linux GPU driver within WSL"* — nada de `nvidia-driver-*`, `cuda-drivers` ou `nvidia-open` com `apt` dentro do WSL. O WSL expõe o driver do Windows como `libcuda.so` em `/usr/lib/wsl/lib`, e um driver Linux instalado por cima quebra esse arranjo. O driver do Windows vem do site da NVIDIA ou do aplicativo da NVIDIA; depois de atualizar, `wsl --shutdown` no PowerShell e abra o Ubuntu de novo.

## Caminho CPU (o padrão do curso)

É o que os exemplos já ensinam, e é a **referência** de todos os números publicados. Não há nada a mudar:

| venv | receita | o detalhe que garante o CPU |
|---|---|---|
| `$PB_DIR/.venv-rl` (PPO) | [`aula18-ppo`](../exemplos/aula18-ppo/index.md#o-ambiente-uv-python-310-e-o-torch-so-cpu) | `--torch-backend cpu`: sem ele, o torch do PyPI no Linux vem com CUDA (uns 3 GB a mais, que não ajudam aqui) |
| `$PB_DIR/.venv-cnn` (CNN e BC) | [`aula17-cnn`](../exemplos/aula17-cnn/index.md#o-ambiente-a-unica-excecao-ao-system-site-packages) | `tensorflow-cpu` no lugar de `tensorflow` |
| `$PB_DIR/.venv-metadrive` | [`aula17-metadrive`](../exemplos/aula17-metadrive/index.md) | nenhum: o render usa a placa de vídeo pelo WSLg, sem CUDA |

Se o seu notebook tem GPU e você quer ter certeza de que um treino com TensorFlow está na CPU, esconda a GPU na linha do comando: `CUDA_VISIBLE_DEVICES="" "$PB_DIR/.venv-cnn-gpu/bin/python" treinar.py ...`. O `treinar.py` e o `treinar_bc.py` imprimem, logo no começo, a linha `dispositivos:` — com a GPU escondida ela diz só `CPU`. No PPO o padrão já é a CPU (`--dispositivo cpu`).

## Caminho GPU: cada biblioteca num venv novo

**A regra deste caminho: o venv de CPU que funciona não é tocado.** Tudo vai em venvs **novos**, com outro nome — `.venv-rl-gpu`, `.venv-cnn-gpu` —, e o de CPU continua sendo a referência. Se um treino longo está rodando no `.venv-rl`, ele continua rodando: nada abaixo mexe nele.

Todos os blocos abaixo são **idempotentes**: colar duas vezes não recria nada (`test -x ... ||` só cria o venv se ele ainda não existe).

### Antes: o `uv` precisa conhecer os índices novos

Terminal do Ubuntu:

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
uv self update
uv pip install --help | grep -o "cu130" | head -1
```

**Tem de aparecer** `cu130` na última linha. Se não aparecer, o `uv` é antigo demais e o `self update` não funcionou (comum quando o `uv` veio de outro instalador): reinstale pelo `curl` da quarta linha.

### PyTorch com GPU — `.venv-rl-gpu`

**Qual torch.** As placas da série RTX 50 têm a arquitetura **`sm_120`**, que só existe nos pacotes do torch compilados com **CUDA 12.8 ou mais novo**, a partir do torch 2.7. O PyTorch não publica mais o índice `cu128` para versões novas: em 17/11/2026, para o Python 3.10 do curso, o índice `cu128` para no torch **2.11.0**, o `cu129` no **2.13.0**, e o **`cu130`** (o CUDA 13.0, o mesmo do torch do PyPI desde o 2.11) tem o **2.14.1** — a mesma versão do `2.14.1+cpu` do `.venv-rl`. O `cu126` também tem o 2.14.1, mas **não** tem a `sm_120`: numa RTX 50 ele instala sem erro e falha na primeira conta. Por isso a linha abaixo diz `cu130` explicitamente, em vez de `auto`.

**O driver.** O `cu130` pede driver da família **580 ou mais novo** (no WSL2, o número que o `nvidia-smi` mostra é o do Windows). Se o seu for mais antigo, atualize o driver; se não puder, troque `cu130` por `cu129` na linha e anote no relatório (torch 2.13.0).

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
test -x "$PB_DIR/.venv-rl-gpu/bin/python" || uv venv --python 3.10 "$PB_DIR/.venv-rl-gpu"
uv pip install --python "$PB_DIR/.venv-rl-gpu/bin/python" --torch-backend cu130 stable-baselines3 highway-env gymnasium matplotlib
```

O download é grande: o `uv pip install --dry-run` com `cu130` lista o `torch 2.14.1+cu130`, o `triton` e **15 pacotes `nvidia-*`** (CUDA 13, cuDNN 9) — da ordem de 3 GB, a mesma ordem medida no `aula18-ppo` para o torch com CUDA (não baixei aqui). Se a instalação parar no meio, Ctrl+C e repita a linha.

**Por que não `--torch-backend auto`.** O `auto` existe e escolhe o índice pelo driver que ele encontrar: o `uv` procura em `/sys/module/nvidia/version`, depois em `/proc/driver/nvidia/version`, depois roda o `nvidia-smi`. No WSL2 os dois primeiros não existem, e se o `nvidia-smi` não estiver no `PATH` o `auto` **cai para o CPU sem avisar**. Escrever `cu130` faz a linha dizer o que instala.

**Conferir** — no mesmo terminal:

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
"$PB_DIR/.venv-rl-gpu/bin/python" - <<'EOF'
import torch
print("torch", torch.__version__, "| CUDA no pacote:", torch.version.cuda)
if not torch.cuda.is_available():
    print("PARE: torch.cuda.is_available() deu False -- veja o socorro do tutorial")
    raise SystemExit(1)
nome = torch.cuda.get_device_name(0)
sm = "sm_%d%d" % torch.cuda.get_device_capability(0)
arqs = torch.cuda.get_arch_list()
print("GPU:", nome, "|", sm, "| arquiteturas deste torch:", " ".join(arqs))
if sm not in arqs:
    print("PARE:", sm, "nao esta na lista -- este torch nao serve para esta GPU")
    raise SystemExit(1)
a = torch.randn(2048, 2048, device="cuda")
print("achei: conta feita na GPU, soma = %.1f" % float((a @ a).sum()))
EOF
```

**Tem de aparecer**, nesta ordem: `torch 2.14.1+cu130 | CUDA no pacote: 13.0`; a linha `GPU:` com o nome da sua placa, a arquitetura (`sm_120` numa RTX 50; `sm_86`, `sm_89` etc. nas anteriores) e uma lista de arquiteturas que **contém** a sua; e a linha `achei: conta feita na GPU`. Se aparecer `PARE:`, não siga: a [tabela de socorro](#socorro-rapido) tem a mensagem.

**Usar no PPO** — só para medir, já que o treino do curso é em CPU. O `treinar_ppo.py` aceita `--dispositivo cpu|cuda|auto` (padrão `cpu`) e diz no cabeçalho qual dispositivo ficou em uso. Com `cuda`, o Stable Baselines3 imprime um aviso dizendo que o PPO com `MlpPolicy` foi feito para a CPU — é esperado, não é erro. A [seção de medida](#meca-antes-de-acreditar) tem o comando que compara os dois.

### TensorFlow com GPU — `.venv-cnn-gpu`, e por que é incerto

**O estado em novembro de 2026.** O TensorFlow publicado é o **2.21.0**, e o `tensorflow[and-cuda]` traz as bibliotecas **CUDA 12** dele (o `uv` resolve hoje cuDNN 9 e o CUDA 12.9 do pip). Para as placas **até a série RTX 40**, é o caminho documentado e deve funcionar. Para a **série RTX 50**, **não há suporte oficial confirmado**: os relatos públicos (a issue [#89272](https://github.com/tensorflow/tensorflow/issues/89272) do TensorFlow, aberta com uma RTX 5090 no WSL2 e com comentários até 2026; um tópico do fórum da NVIDIA com uma RTX 5060 Ti e o TensorFlow 2.20) mostram o aviso `TensorFlow was not built with CUDA kernel binaries compatible with compute capability 12.0` seguido de `CUDA_ERROR_INVALID_PTX` no primeiro treino. Houve quem fizesse funcionar com `tf-nightly` e quem precisasse compilar o TensorFlow da fonte. **Não dá para dizer daqui se funciona na sua placa** — o teste abaixo decide em um minuto.

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
test -x "$PB_DIR/.venv-cnn-gpu/bin/python" || uv venv --python 3.10 "$PB_DIR/.venv-cnn-gpu"
uv pip install --python "$PB_DIR/.venv-cnn-gpu/bin/python" "tensorflow[and-cuda]" opencv-python-headless matplotlib scikit-learn
```

Como o `.venv-cnn`, este venv nasce **sem** `--system-site-packages` (a [`aula17-cnn`](../exemplos/aula17-cnn/index.md#o-ambiente-a-unica-excecao-ao-system-site-packages) explica por quê), e leva `tensorflow` — **nunca** junto com o `tensorflow-cpu` no mesmo venv.

**O teste que decide** — uma rede com convolução, BatchNormalization, MaxPool e Dropout (foi no Dropout que o relato da RTX 5060 Ti quebrou), com o mesmo `enable_op_determinism` dos scripts do curso:

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
TF_CPP_MIN_LOG_LEVEL=1 "$PB_DIR/.venv-cnn-gpu/bin/python" - <<'EOF'
import time
import tensorflow as tf
import keras
gpus = tf.config.list_physical_devices("GPU")
print("tensorflow", tf.__version__, "| keras", keras.__version__, "| GPUs:", gpus)
if not gpus:
    print("PARE: o TensorFlow nao enxerga GPU -- veja o socorro do tutorial")
    raise SystemExit(1)
tf.config.experimental.enable_op_determinism()
keras.utils.set_random_seed(0)
L = keras.layers
with tf.device("/GPU:0"):
    m = keras.Sequential([keras.Input((96, 128, 3)), L.Conv2D(16, 3, use_bias=False),
                          L.BatchNormalization(), L.Activation("relu"), L.MaxPooling2D(),
                          L.Flatten(), L.Dropout(0.5), L.Dense(3, activation="softmax")])
    m.compile("adam", "sparse_categorical_crossentropy")
    x = tf.random.uniform((64, 96, 128, 3))
    y = tf.zeros((64,), dtype="int32")
    t0 = time.time()
    m.fit(x, y, batch_size=32, epochs=3, verbose=2)
print("achei: 3 epocas terminaram em %.1f s; pesos em %s" % (time.time() - t0,
                                                           m.weights[0].value.device))
EOF
```

As duas saídas possíveis:

- **Funcionou:** a linha `GPUs: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]`, três linhas `Epoch` e `achei: 3 epocas terminaram em ... s; pesos em .../device:GPU:0`. O aviso `compute capability 12.0 ... jit-compiled from PTX` pode aparecer antes, e a primeira época pode demorar (é a compilação); se terminou, terminou. Use o `.venv-cnn-gpu` no lugar do `.venv-cnn` nos comandos dos exemplos e **meça** antes de trocar de vez.
- **Não funcionou:** `GPUs: []` e `PARE:`, ou um erro com `CUDA_ERROR_INVALID_PTX`, `JIT compilation failed`, `no kernel image` ou `ptxas`. Siga o plano B. Se ficar mais de 5 minutos parado na primeira época, Ctrl+C e plano B também.

**Plano B, o mais simples: continue no `.venv-cnn`.** As CNNs do curso treinam em um minuto na CPU (tabela do começo). Nada no TP depende de GPU.

**Plano B com GPU: o Keras com o torch por baixo** (`KERAS_BACKEND=torch`). O Keras 3 roda sobre o TensorFlow, o JAX ou o torch, e o torch tem a `sm_120`. Os scripts do curso usam o `tf.data` do TensorFlow para alimentar o treino, então o venv leva o `tensorflow-cpu` (só para os dados) **e** o torch `cu130` (para a conta):

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
test -x "$PB_DIR/.venv-cnn-torch/bin/python" || uv venv --python 3.10 "$PB_DIR/.venv-cnn-torch"
uv pip install --python "$PB_DIR/.venv-cnn-torch/bin/python" --torch-backend cu130 torch tensorflow-cpu opencv-python-headless matplotlib scikit-learn
```

E cada comando de treino ganha a variável na frente, por exemplo, na `aula17-cnn`:

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
KERAS_BACKEND=torch "$PB_DIR/.venv-cnn-torch/bin/python" treinar.py --pasta sintetico --saida resultado-torch
```

**Tem de aparecer**, no começo, a linha `keras 3.12.4 com backend torch: torch 2.14.1+cu130, GPU <nome da placa>`. **O que foi verificado aqui, sem GPU:** com o torch **de CPU** no lugar do `cu130`, o `treinar.py` da `aula17-cnn` rodou inteiro com `KERAS_BACKEND=torch`, e o `treinar_bc.py` da `aula18-pid-bc` também — e o `pesos.npz` que ele exporta bateu com o NumPy do `rede.py` (diferença de 4·10⁻⁹). **A tabela não foi a mesma** do backend TensorFlow (acurácia de validação 0,98 e 0,95 contra 0,98 e 0,93; 50 s e 91 s por rodada contra 39 s e 43 s): outro backend é outra conta, e o relatório diz qual foi usado. Com a GPU de verdade, este caminho **não** foi executado.

### Render: o MetaDrive já usa a GPU, sem CUDA

No WSL2, o WSLg desenha as janelas e as câmeras do MetaDrive pela placa de vídeo do Windows (o OpenGL vira Direct3D 12 pelo Mesa). É isso que deu 7 a 15 quadros/s no notebook do professor, contra 0,4 por software. Em notebook com **duas** placas — a integrada (Intel ou AMD) e a NVIDIA —, o Mesa escolhe a **integrada** por padrão, para poupar bateria (a documentação do WSLg diz isso). Para ver qual está desenhando:

```bash
sudo apt install -y mesa-utils
glxinfo -B | grep -E "OpenGL renderer|Device"
```

| `OpenGL renderer string:` | quer dizer |
|---|---|
| `D3D12 (NVIDIA GeForce ...)` | a NVIDIA está desenhando |
| `D3D12 (Intel(R) ...)` ou `D3D12 (AMD Radeon(TM) ...)` | a integrada está desenhando: a variável abaixo pode mudar isso |
| `llvmpipe (LLVM ...)` | renderização por **software**: o WSLg não está usando placa nenhuma (é o 0,4 quadro/s) |

Para pedir a NVIDIA, a variável `MESA_D3D12_DEFAULT_ADAPTER_NAME` recebe um pedaço do nome da placa. Confira **antes** de deixá-la fixa:

```bash
MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA glxinfo -B | grep "OpenGL renderer"
```

Se agora aparecer `D3D12 (NVIDIA ...)`, **meça** a câmera com e sem a variável, com o mesmo comando, antes de concluir alguma coisa — a integrada pode ser rápida o bastante:

```bash
# ── herda as variáveis do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
"$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py --frames 20 --saida /tmp/render-padrao | grep "tempo de parede"
MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA "$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py --frames 20 --saida /tmp/render-nvidia | grep "tempo de parede"
```

Cada linha termina em `-> N quadros/s`. **Só se a segunda for claramente maior**, deixe a variável no `~/.bashrc` (o `grep -q` impede de escrever duas vezes):

```bash
grep -q MESA_D3D12_DEFAULT_ADAPTER_NAME ~/.bashrc || echo 'export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA' >> ~/.bashrc
```

!!! warning "Trocou a placa que desenha? Regrave o dataset"
    O adaptador muda os pixels (é a mesma lição do aviso do começo). Um BC treinado com quadros desenhados pela integrada e avaliado com a NVIDIA desenhando está sendo avaliado em outra fonte de imagem. Escolha o adaptador **antes** de gravar o dataset do TP5 e não troque mais.

### YOLO (Aula 13)

O `ultralytics` usa a GPU sozinho quando o torch a enxerga, e aceita `device="cpu"` ou `device=0` para escolher. O venv `.venv-yolo` da [`aula13-instancia`](../exemplos/aula13-instancia/index.md) é instalado sem `--torch-backend`, o que traz o torch do PyPI — com CUDA 13.0 no Linux. Numa placa com driver 580 ou mais novo ele já serve para a GPU; num notebook sem NVIDIA, a mesma linha com `--torch-backend cpu` evita uns 3 GB de download. Confira o dispositivo com o bloco de conferência do torch acima, trocando `.venv-rl-gpu` por `.venv-yolo`.

## Meça antes de acreditar

O exemplo [`gpu-cpu`](../exemplos/gpu-cpu/index.md) tem o `medir_dispositivo.py`, que roda com o Python de **qualquer** venv, descobre o que está instalado (torch, TensorFlow ou os dois), e cronometra na CPU e, se houver, na GPU, três cargas parecidas com as do curso: a rede do PPO escolhendo **uma** ação (`mlp-passo`), a mesma rede numa atualização com lote de 64 (`mlp-treino`) e a CNN das Aulas 17 e 18 num lote de 32 imagens 128×96 (`cnn-treino`). Ele **relata, não recomenda**: termina em linhas `achei`, `nao achei` e `olhe`, e explica o erro da série RTX 50 em uma frase em vez de um traceback. O README do exemplo tem os comandos e uma saída real.

Como ler a tabela: `razao = cpu / gpu`. Acima de 1, a GPU levou menos tempo **por lote**; abaixo de 1, mais. Uma razão alta no `cnn-treino` **não** quer dizer que o treino inteiro fica tantas vezes mais rápido — carregar imagens, o Python em volta e (no PPO) o simulador continuam na CPU.

**No relatório**, ao lado de cada tempo de treino e de cada tabela: o dispositivo (CPU ou o nome da GPU), a versão da biblioteca (`torch 2.14.1+cpu`, `tensorflow 2.21.0`) e o tempo de parede. Os scripts do curso imprimem as três coisas no começo da execução.

## Série RTX 50: a armadilha da arquitetura nova

!!! warning "RTX 5050, 5060, 5070, 5080, 5090 (arquitetura Blackwell, `sm_120`)"
    - **torch:** só pacotes com CUDA 12.8 ou mais novo, torch 2.7 em diante. Use `--torch-backend cu130` (driver 580+) ou `cu129`. **Nunca `cu126` ou mais antigo**: instala sem erro e falha na primeira conta com `NVIDIA GeForce RTX 50xx with CUDA capability sm_120 is not compatible with the current PyTorch installation` e depois `CUDA error: no kernel image is available for execution on the device`. A conferência da seção do torch pega isso antes (a `sm_120` tem de estar na lista).
    - **TensorFlow:** sem suporte oficial confirmado. O teste da seção do TensorFlow decide em um minuto; se falhar, plano B.
    - **Render:** nada especial — o WSLg desenha com qualquer placa que o driver do Windows conheça.
    - **Driver:** no WSL2, o do Windows, atualizado. Uma placa nova com driver antigo é a primeira suspeita de qualquer erro.

## Ubuntu nativo

Em Ubuntu instalado direto no notebook (sem WSL), o driver **é** do Linux e vem do `apt`. O caminho mais curto é deixar o Ubuntu escolher a versão recomendada para a placa:

```bash
sudo ubuntu-drivers list
sudo ubuntu-drivers install
```

Reinicie o computador e confira com `nvidia-smi`. Duas observações, **não verificadas** neste material: com *Secure Boot* ligado, o Ubuntu pede uma senha na instalação e uma confirmação azul (*MOK*) no primeiro boot — sem ela, o driver não carrega; e as placas da série RTX 50 só funcionam com a variante **aberta** do driver (pacotes `nvidia-driver-5xx-open`), que o `ubuntu-drivers` deve escolher sozinho. **Não instale o CUDA Toolkit do sistema**: o torch e o TensorFlow trazem o CUDA deles no venv, e um CUDA do sistema só acrescenta uma segunda versão para confundir. Do `nvidia-smi` em diante, os venvs e as conferências são os mesmos deste guia.

## Sem GPU NVIDIA, AMD ou Intel

**Fique no CPU** — é o caminho do curso e o de todos os números publicados. O render do MetaDrive pelo WSLg continua usando a sua placa, seja ela qual for. Para um treino **maior** que os do curso (um YOLO treinado no seu dataset, por exemplo), o Google Colab oferece GPU no navegador; nesse caso, o relatório diz que o treino foi lá, com a GPU e as versões que o Colab mostrou (`!nvidia-smi`, `torch.__version__`), porque o modelo treinado lá foi treinado em outra máquina e outra versão — e a tabela de avaliação se faz na **sua** máquina, com o seu simulador.

## Socorro rápido

| mensagem ou sintoma | causa provável | o que fazer |
|---|---|---|
| `NVIDIA GeForce RTX 50xx ... with CUDA capability sm_120 is not compatible with the current PyTorch installation` | torch de índice antigo (`cu126` ou anterior) | venv novo com `--torch-backend cu130` |
| `CUDA error: no kernel image is available for execution on the device` | idem, ou TensorFlow sem a `sm_120` | torch: `cu130`; TensorFlow: plano B |
| `torch.cuda.is_available()` dá `False` e o `torch.__version__` termina em `+cpu` | instalou com `--torch-backend cpu` ou o `auto` não achou o `nvidia-smi` | refaça a linha com `--torch-backend cu130` |
| `The NVIDIA driver on your system is too old` | driver mais velho que o CUDA do pacote | WSL2: atualize o driver **no Windows** e `wsl --shutdown`; ou use `cu129` |
| `unexpected argument '--torch-backend'` ou `invalid value 'cu130'` | `uv` antigo | `uv self update` |
| `CUDA_ERROR_INVALID_PTX`, `JIT compilation failed`, `ptxas` no TensorFlow | TensorFlow sem suporte à sua placa | plano B |
| `GPUs: []` no TensorFlow com `nvidia-smi` funcionando | instalou `tensorflow-cpu`, ou os dois pacotes no mesmo venv | venv novo só com `tensorflow[and-cuda]` |
| `Could not find cuda drivers on your machine, GPU will not be used` | o TensorFlow não achou o `libcuda.so` | WSL2: `ls /usr/lib/wsl/lib` tem de listar o `libcuda.so`; senão, driver do Windows |
| `You are trying to run PPO on the GPU, but it is primarily intended to run on the CPU` | aviso do Stable Baselines3 com `--dispositivo cuda` | não é erro; é a recomendação da biblioteca |
| `glxinfo -B` mostra `llvmpipe` no WSL2 | o WSLg está desenhando por software | `wsl --update` e `wsl --shutdown` no PowerShell; driver do Windows atualizado |
| a captura do MetaDrive ficou mais lenta com `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` | acontece: a integrada pode ser mais rápida para imagens pequenas | tire a variável do `~/.bashrc` |

## O que foi e o que NÃO foi verificado

**Nenhum comando de GPU deste guia foi executado onde ele foi escrito** — uma máquina Linux de 2 núcleos **sem GPU**. Tudo o que é de GPU saiu da documentação citada abaixo e da leitura dos índices de pacotes, e a primeira execução será a do professor, num notebook com RTX 5050 no WSL2.

**Rodou aqui, em CPU:** o `medir_dispositivo.py` com o torch `2.14.1+cpu` e com o `tensorflow-cpu 2.21.0` (os números de CPU da tabela do começo), e o `testar.py` dele, que simula com dublês a GPU `sm_120` diante de um torch sem `sm_120` e o `CUDA_ERROR_INVALID_PTX` do TensorFlow; o `uv pip install --dry-run` com `--torch-backend cu130` (resolve `torch 2.14.1+cu130`, `triton` e 15 pacotes `nvidia-*`) e com `tensorflow[and-cuda]` (resolve o TensorFlow 2.21.0 com as bibliotecas CUDA 12.9 do pip); a lista do que cada índice do PyTorch tem para o Python 3.10, em 17/11/2026; os dois blocos de conferência (torch e TensorFlow) no caminho sem GPU, que param em `PARE:`, e o resto deles em CPU; o `KERAS_BACKEND=torch` com o torch de CPU nos dois scripts de treino; o `--dispositivo` do `treinar_ppo.py`, com o padrão `cpu` dando pesos idênticos aos da versão anterior.

**Não rodou em lugar nenhum ainda:** o torch `cu130` numa GPU; o TensorFlow com GPU, em qualquer placa; o `KERAS_BACKEND=torch` com GPU; o `glxinfo` e a variável `MESA_D3D12_DEFAULT_ADAPTER_NAME` em notebook com duas placas; o driver em Ubuntu nativo; o Colab. Quando a primeira execução acontecer, esta seção recebe o que se viu.

**Fontes** (consultadas em 17/11/2026):

- NVIDIA, *CUDA on WSL User Guide*: <https://docs.nvidia.com/cuda/wsl-user-guide/index.html>
- NVIDIA, *CUDA Toolkit Release Notes* (driver por versão do CUDA; 13.x pede 580+): <https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html>
- Microsoft, *Enable NVIDIA CUDA on WSL*: <https://learn.microsoft.com/en-us/windows/wsl/tutorials/gpu-compute>
- uv, *Using uv with PyTorch* (`--torch-backend`): <https://docs.astral.sh/uv/guides/integration/pytorch/> e a detecção do driver no código do `uv`: <https://github.com/astral-sh/uv/blob/main/crates/uv-torch/src/nvidia.rs>
- PyTorch, *Introducing CUDA 13.2 and Deprecating CUDA 12.8 (Release 2.12)* (Blackwell 12.0 nos pacotes CUDA 13): <https://dev-discuss.pytorch.org/t/introducing-cuda-13-2-and-deprecating-cuda-12-8-release-2-12/3337>
- PyTorch, *Transitioning PyPI CUDA wheels to CUDA 13.0 (Release 2.11)*: <https://dev-discuss.pytorch.org/t/transitioning-pypi-cuda-wheels-to-cuda-13-0-as-the-stable-release-2-11/3325>
- Fórum do PyTorch, *RTX 5050 (sm_120) Support*: <https://discuss.pytorch.org/t/rtx-5050-sm-120-support-timeline-when-in-stable-pytorch/224288>
- Índice de pacotes do PyTorch (`cu130`): <https://download.pytorch.org/whl/cu130/torch/>
- TensorFlow, *Install TensorFlow with pip*: <https://www.tensorflow.org/install/pip>
- TensorFlow, issue #89272 *TensorFlow on RTX 5090*: <https://github.com/tensorflow/tensorflow/issues/89272>
- Fórum da NVIDIA, TensorFlow com RTX 5060 Ti: <https://forums.developer.nvidia.com/t/how-can-i-use-my-rtx-5060ti-to-training-model-by-using-tensorflow/350054>
- Keras 3, backends: <https://keras.io/getting_started/>
- Stable Baselines3, PPO: <https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html> e a issue citada pelo aviso: <https://github.com/DLR-RM/stable-baselines3/issues/1245>
- WSLg, *GPU selection in WSLg*: <https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg>
- Ultralytics, argumento `device`: <https://docs.ultralytics.com/usage/cfg/>
