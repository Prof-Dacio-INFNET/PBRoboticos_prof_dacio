# Exemplo — `gpu-cpu`

> **Apoio, não veredito.** O `medir_dispositivo.py` mede e relata o que achou nesta máquina (`achei` / `nao achei` / `olhe`). Ele **não** valida a instalação, **não** diz que dispositivo usar, **não** antecipa nota e **não** substitui o enunciado nem o tutorial [CPU ou GPU: os dois caminhos](../../tutoriais/gpu-cpu.md), que é onde as receitas estão.

**Etapa 9 · Aulas 17 e 18.** Um script que roda com o Python de **qualquer** venv do curso — o do PPO, o da CNN, um venv novo com GPU — e cronometra, na CPU e (se houver) na GPU, três cargas parecidas com as do curso. Serve para trocar "a GPU deve ajudar" por um número da **sua** máquina.

```
gpu-cpu/
├── medir_dispositivo.py   # detecta torch e/ou TensorFlow; cronometra CPU x GPU; achei / nao achei / olhe
└── testar.py              # 5 grupos; os de GPU com dubles (nao precisa de GPU)
```

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

mkdir -p "$PB_DIR" && cd /tmp && rm -rf pb-gpu && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-gpu && \
  rm -rf "$PB_DIR/gpu-cpu" && \
  cp -r pb-gpu/exemplos/gpu-cpu "$PB_DIR/"
```

Não há venv próprio: o script usa o venv que você já tem.

## Medir

Cada linha num venv diferente; rode as que existirem na sua máquina (as de `-gpu` são as do tutorial):

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/gpu-cpu"
"$PB_DIR/.venv-rl/bin/python" medir_dispositivo.py
```

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/gpu-cpu"
test -x "$PB_DIR/.venv-rl-gpu/bin/python" && "$PB_DIR/.venv-rl-gpu/bin/python" medir_dispositivo.py
test -x "$PB_DIR/.venv-cnn-gpu/bin/python" && "$PB_DIR/.venv-cnn-gpu/bin/python" medir_dispositivo.py
```

Opções: `--grande` acrescenta uma CNN de 224×224 com 64/128/256 filtros (a carga em que a GPU costuma pagar; ela **não** existe no curso e leva uns 3 s por lote numa CPU de 2 núcleos); `--so-cpu` não toca na GPU; `--biblioteca torch|tensorflow` mede só uma; `--repeticoes` e `--aquecimento` mudam quantos lotes contam e quantos são descartados; `--sem-determinismo` tira o `enable_op_determinism` que os scripts do curso usam; `--sem-captura` deixa o log do TensorFlow sair direto no terminal (use se o processo morrer sem mensagem).

## O que ele mede

| carga | o que é | parecida com |
|---|---|---|
| `mlp-passo` | MLP 25 → 256 → 256 → 5, lote 1, só a ida | o PPO escolhendo **uma** ação a cada passo do simulador |
| `mlp-treino` | a mesma MLP, lote 64, ida + volta + Adam | a atualização do PPO (`LOTE = 64` do `treinar_ppo.py`) |
| `cnn-treino` | 3 blocos Conv3×3 (16/32/64) + BN + ReLU + MaxPool, densa 64, dropout 0,5, imagens 128×96, lote 32 | o `treinar.py` da `aula17-cnn` e, menor, o `treinar_bc.py` |
| `cnn-grande` | só com `--grande` | um treino de visão maior, fora do curso |

Os dados são aleatórios: o que se mede é o tempo da conta, não a qualidade. Cada carga roda 3 lotes de aquecimento, descartados (na GPU, o primeiro lote inclui compilação e cópia), e 20 cronometrados; a tabela traz a **mediana** em milissegundos por lote. `razao = cpu / gpu`: acima de 1 a GPU levou menos tempo por lote, abaixo de 1, mais.

## Uma saída real, sem GPU

No container onde o material foi escrito (Linux, 2 núcleos, sem GPU), com o venv do PPO (`torch 2.14.1+cpu`):

```
[torch 2.14.1+cpu] cuda no pacote: nenhum; torch.cuda.is_available(): False
  medindo em cpu ...
    mlp-passo   0.04 ms/lote
    mlp-treino  0.93 ms/lote
    cnn-treino  124.2 ms/lote

=== mediana de 20 lotes (depois de 3 de aquecimento) ===
biblioteca | carga      | cpu (ms/lote) | gpu (ms/lote) | razao
-----------+------------+---------------+---------------+------
torch      | mlp-passo  | 0.04          | sem GPU       | -
torch      | mlp-treino | 0.93          | sem GPU       | -
torch      | cnn-treino | 124.2         | sem GPU       | -

nao achei: nvidia-smi (nvidia-smi nao existe neste sistema)
achei: torch 2.14.1+cpu (CUDA no pacote: nenhum -- pacote so CPU), 2 thread(s) na CPU
nao achei: tensorflow neste Python (...)
```

Com o venv da CNN (`tensorflow-cpu 2.21.0`), a `cnn-treino` deu **97 a 100 ms** por lote, e a `cnn-grande` **2,9 s**. Duas leituras que esses números já permitem, sem GPU nenhuma:

- **A rede do PPO não é o gargalo.** `mlp-passo` = 0,04 ms; um passo do `highway-fast-v0` leva ~29 ms (35 passos/s, medido no `aula18-ppo`). Mesmo uma GPU que zerasse a conta da rede não mudaria o treino.
- **A CNN do curso é pequena.** ~100 ms por lote × 13 lotes por época × 20 épocas ≈ 26 s de conta, dentro dos 38–45 s medidos por rodada. A GPU pode encolher os 26 s; o resto continua.

Com GPU, a coluna `gpu (ms/lote)` ganha números e aparecem linhas `olhe:` dizendo onde a GPU levou mais ou menos tempo. Se a biblioteca não tiver código para a sua placa (o caso da série RTX 50 com torch antigo ou com o TensorFlow oficial), a coluna diz `erro` e a linha `olhe:` explica em uma frase, em vez de um traceback. **Nenhuma saída com GPU foi vista ainda** — este exemplo foi escrito numa máquina sem GPU.

## O que ele não alcança

O tempo do **seu** treino. Uma carga sintética não tem simulador, disco, leitura de imagens nem o Python em volta — e é isso que pesa nos treinos do curso. Uma razão de 5 na `cnn-treino` **não** quer dizer um treino 5 vezes mais rápido. O que vale para o relatório é o seu treino de verdade, medido nos dois dispositivos, com o dispositivo e a versão da biblioteca escritos ao lado do tempo.

Ele também não sabe se a sua instalação "está certa": ele sabe o que encontrou. Uma lista sem `olhe:` quer dizer "esgotei o que um script enxerga", não "está tudo pronto".

## Conferir antes de confiar

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/gpu-cpu"
python3 testar.py
```

Cinco grupos. Os quatro primeiros rodam com qualquer `python3`, sem torch nem TensorFlow: higiene dos `.py`; as funções puras (o diagnóstico de cada mensagem literal — `sm_120 is not compatible`, `no kernel image`, `CUDA_ERROR_INVALID_PTX`, driver velho —, a tabela, a mediana, o vocabulário `achei` / `nao achei` / `olhe`); e **dublês** de torch e de TensorFlow que fingem uma RTX 5050 diante de um torch sem `sm_120` e de um TensorFlow que dá `CUDA_ERROR_INVALID_PTX`, conferindo que o script inteiro termina com relato e **sem traceback**. O quinto roda o script de verdade em cada Python que você passar com `--python` (pode repetir). Aqui: 50 conferências com os dois venvs de CPU, uns 11 s (44 sem `--python`, menos de 1 s). Termina em `todos os testes passaram.`

## Licença

MIT, como todo o `exemplos/` (ver `exemplos/LICENSE`).
