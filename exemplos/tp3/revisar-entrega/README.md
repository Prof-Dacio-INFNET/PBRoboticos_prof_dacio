# Revisar a entrega do TP3 — um roteiro, não um veredito

Um script que lê o **seu** repositório e aponta, item por item do enunciado,
**onde vale a pena olhar** antes de entregar. Ele faz a varredura mecânica que
ninguém faz na quinta-feira: cruzar o enunciado com o que está de fato no
repositório, linha por linha.

!!! danger "Isto não é correção, nem validação prévia"
    Ele **não corrige, não antecipa nota e não atesta que a sua entrega está
    pronta.** A referência é o **enunciado do TP3**, e a responsabilidade pela
    entrega é **sua** — antes e depois de rodar isto.

    `achei` não quer dizer entregue certo. `não achei` não quer dizer entregue
    errado. Nos dois casos quer dizer a mesma coisa: **vá olhar isso.**

### O que ele não consegue ver — e é o que mais pesa

Um comando consegue dizer que um arquivo existe, que um YAML parseia, que uma
tag está criada. Nenhum comando consegue dizer:

- se o seu launch **realmente sobe** o seu sistema, e não só menciona as coisas certas;
- se o mapa salvo é **do seu cenário**, e não o do exemplo;
- se a sua explicação dos frames **está correta**;
- se a análise do item 4 fala do **seu** projeto ou é texto genérico;
- se o que você escreveu **responde ao que foi pedido**.

Isso é leitura, e quem lê é o professor. No relatório do script esses pontos
aparecem como `olhe` — não porque falharam, mas porque estão fora do alcance
de qualquer verificação automática.

A entrega é **sexta, 23/10**. Rode isto hoje, não na sexta: o que ele aponta
costuma levar minutos para resolver, e nada leva minutos depois do prazo.

## Rodar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

cd /tmp && rm -rf pb-rev && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-rev && \
  cp pb-rev/exemplos/tp3/revisar-entrega/revisar_tp3.py "$PB_DIR/"
```

Só biblioteca padrão do Python: nada de `pip`, nada para compilar.

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
python3 revisar_tp3.py
```

Com o sistema no ar, em **outro** terminal (depois de `ros2 launch ... bringup.launch.py`),
ele confere também tópicos e TF:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source "$PB_WS/install/setup.bash"
cd "$PB_DIR"
python3 revisar_tp3.py --ao-vivo
```

E, para conferir um repositório que não é o diretório atual:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
python3 "$PB_DIR/revisar_tp3.py" --raiz "$PB_DIR"
```

**Código de saída:** `0` quando nada falta, `1` quando falta alguma coisa, `2`
quando a raiz passada não existe. Dá para encadear (`python3 revisar_tp3.py && git push`).

## Como ler a saída

Cada linha tem um dos três estados, e a diferença entre eles é a coisa mais
importante desta página:

| Marca | Significado | O que fazer |
|---|---|---|
| `achei` | o script **provou** o fato por comando | nada |
| `não achei` | o script provou que **não** está lá | resolver — entra na lista final |
| `olhe` | o script **não consegue** decidir | ler você mesmo; não conta para o código de saída |

No fim ele imprime **o que falta, na ordem em que compensa resolver** — launch
primeiro, git por último, porque o launch destrava todo o resto e o `git tag`
leva trinta segundos. É a mesma ordem que
[`recursos/gates-tps.md`](../../../recursos/gates-tps.md) recomenda: *comece
pelo launch, não pelo SLAM*.

## O que cada conferência significa

### Item 1 — Launch principal

| Conferência | Por que ela existe |
|---|---|
| existe **UM** `bringup.launch.py` | com dois, nem você nem o professor sabem qual o `ros2 launch` vai pegar |
| sintaxe válida (`ast.parse`) | launch que não parseia não sobe nada — e o erro do `ros2 launch` não aponta a linha |
| menciona Gazebo, `robot_state_publisher`, `rviz2` | reportados **separados**, porque "falta algo no launch" não ajuda; "falta o `robot_state_publisher`" ajuda |
| o `.rviz` citado existe no disco | o caso clássico: a configuração do RViz2 ficou só na sua máquina e o launch de quem clonou morre em `file not found` |
| o YAML de parâmetros citado existe no disco | o enunciado pede parâmetros via YAML; `mapa.yaml` não conta, ele é o G3.3 |
| existe URDF/xacro | é o que o `robot_state_publisher` carrega; sem ele não há TF do robô |

O launch é lido pela **árvore sintática**, sem comentários nem docstrings: um
docstring escrito *"falta subir o Gazebo"* não pode fazer o conferidor dizer que
o launch menciona Gazebo. Verificação que se engana com a sua própria anotação
não vale nada.

### Item 2 — TFs e SLAM

| Conferência | Por que ela existe |
|---|---|
| `docs/evidencias/tp3/frames.pdf` | é o **G3.2**, o gate de verdade deste TP: 90% dos problemas de SLAM são problemas de TF disfarçados |
| `slam_toolbox` referenciado em launch/config | o enunciado pede o SLAM Toolbox **integrado**, não rodado à mão num terminal esquecido |
| `maps/mapa.pgm` + `maps/mapa.yaml` | o par, no lugar certo — o `map_saver_cli` salva no diretório em que você estava |
| o `mapa.yaml` parseia e aponta para o PGM que existe | o erro silencioso: o `.yaml` de um salvamento e o `.pgm` de outro, ou um dos dois renomeado — o par quebra e o `map_server` não abre |

### Item 3 — Segmentação semântica

| Conferência | Por que ela existe |
|---|---|
| `/vision/segmented` aparece no código | é o nome que o enunciado **fixa**; publicar em `/segmentado` é publicar em lugar nenhum |
| imagem da segmentação em `docs/evidencias/tp3/` | sem o print, o trabalho existiu e não pôde ser avaliado |
| mistura com transparência | sempre `olhe` — o script acha indício de `addWeighted`/`alpha`, mas **cor por classe** e **0,5** você confere a olho |

### Item 4 — Arquitetura de percepção veicular

| Conferência | Por que ela existe |
|---|---|
| `docs/evidencias/tp3/veicular.md` existe | é o artefato do G3.5 |
| cita CAN, Ethernet e sensores | **lembrete, não nota**: ele só diz quais famílias de palavra-chave não apareceram, para você não descobrir na correção que esqueceu a Ethernet |
| relacionado às escolhas do seu projeto | sempre `olhe` — texto genérico de internet não pontua, e isso só a leitura pega |

### Entrega

| Conferência | Por que ela existe |
|---|---|
| relatório em `docs/` | é o documento que a rubrica lê |
| captura do launch rodando | o enunciado pede o comando único **documentado** com captura de tela |
| branch `entrega-tp3`, tag `tp3` | é literalmente o que o G3.6 verifica |
| nada pendente de commit | trabalho não commitado não existe para a correção |
| `maps/` e evidências **rastreados** pelo git | o erro clássico de entregar sem commitar: o arquivo está no seu disco, quem corrige faz `clone`, e não vê nada |

Se a pasta não for um repositório git, ele diz isso e segue — as quatro linhas
acima viram `olhe`.

### Ao vivo (`--ao-vivo`)

Quatro conferências, **todas tolerantes a falha**: `/vision/segmented` na lista
de tópicos (e com publisher ≥ 1), `/scan` publicando, a TF `map → odom`
existindo, e mais de um nó no ar. Toda uma delas que não dá para fazer vira `olhe`
com a causa provável, nunca um travamento: todo subprocesso tem timeout, e
`ros2 topic hz`, que não termina por conta própria, é lido pela saída parcial.

Sem ROS 2 instalado ou sem `source` do `setup.bash`, a seção inteira vira um `olhe`
que diz exatamente isso — rodar o script no Windows, fora do WSL2, não quebra
nada.

## Cada item do enunciado × o gate que ele fecha

| Item do enunciado | Gate | Evidência que fecha o gate | Data recomendada |
|---|---|---|---|
| 1. Launch principal: um comando sobe tudo | **G3.0** | `launch/bringup.launch.py` | 30/09 |
| 1. Mundo do projeto carregando com robô e câmera | **G3.1** | `worlds/`ou `models/` + print | 06/10 |
| 2. TFs: `map → odom → base_link → sensores`, sem warning | **G3.2** | `docs/evidencias/tp3/frames.pdf` | 10/10 |
| 2. SLAM Toolbox com mapa persistido | **G3.3** | `maps/mapa.pgm` + `maps/mapa.yaml` + print | 15/10 |
| 3. Segmentação por instância em `/vision/segmented` | **G3.4** | print em `docs/evidencias/tp3/` | 18/10 |
| 4. Arquitetura de percepção veicular | **G3.5** | `docs/evidencias/tp3/veicular.md` | 20/10 |
| Relatório, branch `entrega-tp3`, tag `tp3`, Moodle | **G3.6** | tag `tp3` + postagem | **23/10** |

A tabela completa, com a coluna "como provar" de cada gate, está em
[`recursos/gates-tps.md`](../../../recursos/gates-tps.md). Este script é um
atalho até ela, não um substituto: ele confere o que é verificável por comando,
e a régua da rubrica continua sendo a evidência commitada.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `existe UM bringup.launch.py: achei 2` | sobrou um `bringup.launch.py` numa pasta antiga — apague ou mova para fora do repositório |
| `.rviz referenciado existe no disco: citado e nao achado` | o `.rviz` está só na sua máquina: **File > Save Config As** dentro de `rviz/` e `git add` |
| `o launch nao cita nenhum .yaml de parametros` | os números estão no código; passe por `config/*.yaml` no `bringup` |
| `mapa.yaml aponta para o PGM: nao existe ao lado do yaml` | o par veio de salvamentos diferentes — salve os dois de novo com `map_saver_cli` |
| `mapa.yaml parseia: falta python3-yaml` | `sudo apt install python3-yaml` (ele degrada para uma leitura simples, mas confere menos) |
| `2 fora do git: maps/mapa.pgm, maps/mapa.yaml` | `git add maps docs/evidencias` — é o erro clássico de entregar sem commitar |
| `nenhuma imagem na pasta` | crie `docs/evidencias/tp3/` e salve os prints lá, com `seg`/`bringup` no nome |
| `nao achei o comando ros2` | falta `source "$PB_WS/install/setup.bash"` neste terminal |
| `/scan nao deu taxa em 10 s` | o Gazebo subiu mas o sensor não — confira o plugin do laser no URDF |
| `tf2_echo map odom nao devolveu transformada` | quem publica essa aresta é o SLAM; sem ele, só existe `odom → base_link` |

Veja também: [gates dos TPs](../../../recursos/gates-tps.md),
[aula 10 — bringup](../../aula10-bringup/index.md) e
[aula 12 — SLAM](../../aula12-slam/index.md).
