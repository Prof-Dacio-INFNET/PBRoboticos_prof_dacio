# Aula 10 — Bringup: um comando sobe o sistema inteiro

Este pacote é o ensaio do **G3.0** do TP3 (`bringup.launch.py` subindo o sistema
todo) e a ferramenta que fecha o **G2.5** do TP2 (parametrização em YAML que
realmente chega ao nó).

Ele sobe um sistema pequeno mas completo — dois nós próprios, o modelo do robô
da Aula 9 e um arquivo de parâmetros — e **não precisa de câmera nem de
hardware**.

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

cd /tmp && rm -rf pb-aula10 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-aula10 && \
  # a copia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x),
  # e o colcon passa a compilar a versao velha sem dizer nada
  rm -rf "$PB_WS/src/aula10_bringup" && \
  cp -r pb-aula10/exemplos/aula10-bringup/aula10_bringup "$PB_WS/src/" && \
  cd "$PB_WS" && colcon build --packages-select aula10_bringup && \
  source install/setup.bash
```

O `conferir-params.py` roda solto, sem compilar nada:

```bash
python3 /tmp/pb-aula10/exemplos/aula10-bringup/conferir-params.py --help
```

## Rodar

```bash
ros2 launch aula10_bringup bringup.launch.py
```

Se você ainda não compilou o `meu_robo_description` da Aula 9, suba sem o modelo:

```bash
ros2 launch aula10_bringup bringup.launch.py modelo:=false
```

## O que tem dentro

| Arquivo | Papel |
|---|---|
| `launch/bringup.launch.py` | compõe o sistema: inclui a percepção e sobe o modelo do robô |
| `launch/percepcao.launch.py` | o subsistema, feito para ser incluído |
| `config/sistema.yaml` | parâmetros que **chegam** (usa o curinga `/**`) |
| `config/sistema-armadilha.yaml` | parâmetros que **não chegam** — é o exercício |
| `aula10_bringup/detector.py` | publica achados sintéticos; imprime os parâmetros que recebeu |
| `aula10_bringup/supervisor.py` | mede a taxa recebida e diz se o sistema está vivo |
| `conferir-params.py` | confere o YAML contra os nomes reais dos nós, sem ROS 2 |

## As três verificações

**Um launch que sobe sem erro não é um launch que funciona.** Subir é o que o
launch faz; funcionar é outra afirmação, e ela precisa de prova. São três:

```bash
ros2 launch aula10_bringup bringup.launch.py --show-args   # 1. o que dá para configurar
ros2 node list                                             # 2. quem realmente subiu
ros2 param dump /percepcao/detector                        # 3. com que valores
```

A terceira é a que quase ninguém faz, e é a que pega o erro desta aula.

## O exercício: o YAML que ninguém lê

Suba o sistema com o arquivo defeituoso:

```bash
ros2 launch aula10_bringup bringup.launch.py \
  params:=$(ros2 pkg prefix aula10_bringup)/share/aula10_bringup/config/sistema-armadilha.yaml
```

O `sistema-armadilha.yaml` pede `taxa_hz: 9.0` e `classe: NUNCA_APARECE`. Agora
olhe o que o nó diz que recebeu, no próprio log de subida, e confirme:

```bash
ros2 param get /percepcao/detector taxa_hz     # 2.0 — o padrão do código
ros2 param get /percepcao/detector classe      # objeto — o padrão do código
```

**Nenhum erro foi impresso em lugar nenhum.** O launch subiu, os nós subiram, o
arquivo foi lido, e os valores foram descartados em silêncio.

A causa: a chave do YAML é `detector:`, que significa o nó `/detector`, na raiz.
O launch empurrou o nó para `/percepcao/detector`. Os nomes não casam, e a regra
do ROS 2 é ignorar o que não casa — sem avisar.

O `conferir-params.py` diz isso antes de você perder a tarde:

```bash
ros2 node list | python3 conferir-params.py \
  $(ros2 pkg prefix aula10_bringup)/share/aula10_bringup/config/sistema-armadilha.yaml -
```

As duas curas são trocar a chave por `/percepcao/detector:` ou usar `/**:`.
Prefira o curinga: ele sobrevive à mudança de namespace, e mudar namespace é
exatamente o que você vai fazer quando o sistema crescer.

## Sobre ordem: nada espera nada

Repare na subida. O `supervisor` quase sempre nasce antes do `detector` e passa
alguns segundos avisando que não recebeu dado — e então se recupera sozinho.

Isso é o comportamento correto. Em ROS 2 o grafo é **descoberto**, não montado
em ordem: o launch dispara todos os processos e segue em frente. Um nó que só
funciona se subir depois de outro vai quebrar no dia em que a máquina estiver
mais lenta, e esse dia sempre chega — costuma ser o da apresentação.

A regra prática: **o nó tolera a ausência do outro**. Se você acha que precisa
de ordem de subida, quase sempre precisa de um nó mais tolerante.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package 'aula10_bringup' not found` | terminal sem `source install/setup.bash` |
| `package 'meu_robo_description' not found` | suba com `modelo:=false`, ou compile o pacote da Aula 9 |
| o YAML não muda nada | a chave não casa com o nome do nó — rode o `conferir-params.py` |
| `ros2 param get` diz `Node not found` | nome errado; use o que o `ros2 node list` imprime |
| supervisor só reclama, nunca recebe | o detector morreu; olhe o log dele, ou `ros2 topic list` |
| `libexec directory ... does not exist` | `setup.cfg` com o nome antigo do pacote |
