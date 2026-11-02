# Aula 16 — A clínica do Nav2, e a sessão que se reproduz sem o robô

**Terça, 03/11/2026 · sala SJ205 · Etapa 8 (26/10–07/11)**

[:material-file-pdf-box: Slides da Aula 16 (PDF)](apresentacao-aula16.pdf){ .md-button .md-button--primary }
[:material-stethoscope: Diagnóstico do Nav2](../../exemplos/aula16-clinica/index.md){ .md-button }
[:material-chart-timeline-variant: Árvore e sessão gravada](../../exemplos/aula16-arvore-bag/index.md){ .md-button }

## Cenas dos últimos episódios

**Na Aula 15** o Nav2 subiu com o mapa de vocês e o AMCL convergiu depois do *2D Pose Estimate*. Antes disso, a tabela do filtro de partículas mostrou os três cenários terminando com a nuvem entre 6,3 e 7,8 cm — e um deles a **5,92 m** da verdade, com o rumo invertido. A frase que ficou foi essa: **concordância interna não é evidência**.

E a aula começou com um defeito do próprio material: `rviz:=true` na linha de comando, e o RViz2 não abria. O `launch_arguments` de um `IncludeLaunchDescription` não é escopado, e o `'rviz': 'false'` que o launch passava ao mundo da Aula 11 apagava o valor digitado. **Catorze processos no ar, nenhuma mensagem de erro, e o botão que faltava era o que fazia a aula acontecer.**

Hoje a aula tem duas metades e as duas descendem daquilo. A primeira é fazer o Nav2 **navegar** na máquina de cada um — o G4.1 vence **amanhã, 04/11**, e o G4.2 na segunda, **09/11**. A segunda é começar o item 2, que é onde a navegação deixa de depender de você estar na frente dela.

## A ideia da aula em uma frase

**Um sistema que só funciona com você na frente dele não está entregue.** É isso que o item 2 do TP4 cobra quando pede uma árvore de comportamento *e* uma sessão gravada que se reproduz offline: a árvore decide sem você, e o bag prova sem você. O resto da aula é consequência disso.

## A ordem de hoje, e o que cede se o tempo apertar

| Bloco | O que você sai com | Vence em |
|---|---|---|
| 1. A clínica — pôr o Nav2 para navegar | um goal cumprido sem intervenção, com o print | **04/11** |
| 2. A rota de três pontos e os costmaps | o `rota.py` com os seus pontos e os dois costmaps explicados | 09/11 |
| 3. A árvore: o que o Humble tem, e o que não tem | a decisão de qual caminho você vai seguir | 12/11 |
| 4. A sessão gravada e a figura | o bag, o CSV e o gráfico da trajetória | 15/11 |

Se o tempo apertar, **o bloco 4 cede** — ele é o que está mais longe (15/11) e é o mais autocontido desta página. O que não cede é o bloco 1: ele vence amanhã.

## Preparar o terminal e pegar o material

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
mkdir -p "$PB_WS/src"

# a cópia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x), e o
# colcon passa a compilar a versão velha sem dizer nada. A guarda é o próprio
# encadeamento com &&: se o clone falhar, nada é apagado. (Comentário DENTRO de
# uma cadeia `&& \` a quebraria — por isso ele está aqui em cima.)
cd /tmp && rm -rf pb-a16 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a16 && \
  rm -rf "$PB_DIR/aula16-clinica" "$PB_DIR/aula16-arvore-bag" && \
  cp -r pb-a16/exemplos/aula16-clinica "$PB_DIR/" && \
  cp -r pb-a16/exemplos/aula16-arvore-bag "$PB_DIR/"
```

Nenhum dos dois precisa de `colcon build` para a parte de hoje: o diagnóstico é Python puro, e a régua da sessão também. O pacote ROS 2 do segundo exemplo entra depois, quando você for gravar o seu bag.

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Num terminal novo, três coisas se perdem juntas e só a primeira avisa:

    ```bash
    export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
    export PB_DIR="$HOME/projeto-pb-$PB_USER" && export PB_WS="$PB_DIR/ros2_ws"
    source /opt/ros/humble/setup.bash
    source "$PB_WS/install/setup.bash"
    ```

---

## Bloco 1 — A clínica: onde olhar, em dez segundos

Com o seu Nav2 no ar, num terminal ao lado:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-clinica"
python3 diagnosticar_nav2.py
python3 diagnosticar_nav2.py --rapido      # só o ambiente, os nós, o ciclo de vida e o /cmd_vel
```

Ele percorre dez verificações na ordem em que compensa olhar — ambiente, nós no ar, ciclo de vida, TF, pose inicial, `/cmd_vel`, a cadeia até o `/cmd_vel_nav`, os servidores de ação, os costmaps e o mapa — e devolve **uma lista de lugares para olhar**, cada um com a próxima ação numa linha.

!!! danger "Ele não corrige, não valida e não antecipa nota"
    `achei` não quer dizer certo. `nao achei` não quer dizer errado. Nos dois casos quer dizer: **vá olhar isso.**

    E o que ele marca com `olhe` é o que mais pesa, porque nenhum comando alcança: se o robô **realmente anda**, se o mapa publicado é **do seu cenário**, se a **rota faz sentido** na sua planta. Isso é o que o G4.1 e o G4.2 avaliam — e é leitura minha, não saída de script. Sair daqui com a lista vazia não é ter terminado: é ter esgotado o que um script enxerga.

### Os quatro casos que respondem por quase tudo

| O que você vê | O que é, e o que fazer |
|---|---|
| o gerenciador parado em `Configuring`, calado | um nome na lista do gerenciador sem nó correspondente no ar. O diagnóstico aponta **o primeiro nó inativo**: é ali que ele parou, e os de baixo são consequência |
| `bt_navigator` ativo, mas nada acontece com o goal | falta `map → odom`: **o AMCL não recebeu a pose inicial**. No Humble ele só publica depois dela (`if (!initial_pose_is_known_) return;`) |
| o robô anda truncado, ou anda sozinho | `/cmd_vel` com **dois publicadores**. Não dá erro: o robô obedece ao último que falou. O diagnóstico nomeia os dois |
| o robô não anda e ninguém reclama | a cadeia do `/cmd_vel`: o `controller_server` fala em `/cmd_vel_nav` e, sem o `velocity_smoother` ou com os remapeamentos desfeitos, ninguém ouve |

**Nenhum dos quatro produz mensagem de erro.** É a mesma família do `rviz:=true` da semana passada, e é por isso que a primeira coisa a fazer não é ler o log: é perguntar ao sistema o que ele tem.

---

## Bloco 2 — O goal de amanhã, e a rota de segunda

O **G4.1 vence amanhã** e pede uma coisa só: o robô indo até **um** goal, sem intervenção, com vídeo curto. Pelo RViz2 é o **2D Goal Pose** (publica em `/goal_pose`); por código é o `rota.py` da Aula 15, com um ponto só:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 run aula15_nav2 rota --ros-args -p rota:="[9.0, 2.0, 1.57]"
```

O **G4.2 vence na segunda** e sobe a aposta: **três waypoints ou mais**, e os dois costmaps **explicados**. A rota inteira é o `rota.py` com os seus pontos; a explicação é dois parágrafos, e eles valem metade do item:

> O costmap **global** é o mapa inteiro com a inflação, e é sobre ele que o NavFn planeja. O **local** é uma janela rolante de poucos metros, reconstruída a partir do laser a cada ciclo, e é sobre ela que o DWB escolhe a próxima velocidade.

Quem escrever isso com os números do **seu** YAML — tamanho da janela, resolução, `robot_radius`, `inflation_radius` — entrega o item bem feito sem escrever uma linha de código a mais.

!!! warning "Objetivo recusado não é objetivo que falhou"
    Ponto em célula ocupada, ou a menos de `robot_radius` de uma parede, faz o servidor **recusar** o goal: ele nem tenta. Escolha os pontos olhando o **costmap global** no RViz2, não o mapa cru — e lembre que `robot_radius` decide se a passagem abre, enquanto `inflation_radius` decide só o quanto ela custa.

---

## Bloco 3 — A árvore, e o que o Humble não tem

O `bt_navigator` executa um **XML**, e os prontos estão em `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/`. O exemplo desta aula traz dois: a árvore oficial `navigate_to_pose_w_replanning_and_recovery.xml` copiada e **comentada bloco a bloco**, e uma variante com a espera de 2 s no ramo de recuperação.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ls /opt/ros/humble/share/nav2_bt_navigator/behavior_trees/
cd "$PB_DIR/aula16-arvore-bag" && ls arvores/
```

!!! danger "Não existe, no Humble, um nó de árvore que meça distância a obstáculo"
    Essa é a informação que decide o item 2, e ela foi conferida na lista oficial de nós registrados (`nav2_behavior_tree/nav2_tree_nodes.xml`): há condições para bateria baixa, para objetivo trocado, para caminho inválido, para tempo decorrido — **e nenhuma para "obstáculo a menos de 0,5 m"**.

    Ou seja: a árvore sozinha **não cumpre** o enunciado. O que ela faz é decidir o que acontece quando alguém lhe diz que há um obstáculo. Quem diz é você, por um dos dois caminhos:

    - **o caminho completo**, um nó de condição próprio em C++ registrado como plugin do `nav2_behavior_tree`, composto na árvore com o `Wait` de 2 s dentro de um `ReactiveFallback`;
    - **o caminho de cliente**, o `vigia.py` do exemplo: ele assina o `/scan`, cancela o goal quando a distância mínima cai abaixo de 0,5 m, espera 2 s e **reenvia o mesmo objetivo**. É a Aula 8 outra vez — cancelamento de ação —, e roda sem compilar C++.

    **Os dois passam.** O que não passa é não dizer qual você usou, e por quê. Traga a sua escolha: a aula de 10/11 é sobre ela.

Duas armadilhas que custam tempo e não dizem o nome:

O `wait_duration` do nó `Wait` é um **inteiro**. Escrever `2.0` ali não é "dois segundos com casa decimal": é um valor que a árvore recusa a carregar, e o `bt_navigator` falha ao ativar — sem apontar a linha.

E **comentário de XML não pode conter dois traços seguidos**. Toda opção do ROS 2 começa com dois traços, então colar um `ros2 run ... --ros-args` dentro de um `<!-- -->` faz o parser recusar **o arquivo inteiro**, com uma mensagem que não menciona traços. É por isso que, nas duas árvores do exemplo, os comandos ficam fora dos comentários.

---

## Bloco 4 — A sessão gravada, e a figura que ela produz

O item 2 termina pedindo o que é, na prática, a parte mais fácil de provar: **a sessão gravada e reproduzida offline, com o gráfico da trajetória**. O caminho é curto e não depende de biblioteca nova:

```
ros2 bag record  ──►  bag  ──►  ros2 bag play --clock  ──►  gravar_pose  ──►  CSV  ──►  figura
```

E o exemplo permite fazer **a régua antes do robô**: ele gera uma sessão sintética, determinística, com dois eventos de obstáculo, e mede.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 simular_sessao.py                      # gera sessao.csv
python3 medir_sessao.py                        # a tabela
python3 plotar_trajetoria.py --saida trajetoria.png
```

```
DISTANCIA PERCORRIDA -- tres contas, tres numeros
  integral de |cmd_v| dt      :  25.52 m   <- o que foi mandado andar
  soma dos passos do /odom    :  26.29 m   <- +3.0% (a deriva de escala)
  soma dos passos do /amcl    :  49.03 m   <- +92.1%: o tremor virou caminho

INTERRUPCOES -- 2 evento(s); o portao viu no minimo 0.402 m
  #  t disp (s)  /scan (m)  parado (s)  espera (s)  2 s cumpridos
  1      12.30      0.402        2.00        2.00            sim
  2      51.80      0.406        2.10        2.10            sim
```

Três leituras, e a primeira é a que mais vale:

**A trajetória do `/amcl_pose` tem 49 m, e o robô andou 25.** Não é defeito do AMCL: é a conta que está errada. Somar a distância entre poses sucessivas de uma estimativa que treme soma também o tremor, e 92% de inflação sai de um ruído de poucos centímetros. **Quem citar "distância percorrida" no relatório a partir do `/amcl_pose` está citando ruído** — e esta é a terceira vez no semestre que uma métrica mede o instrumento em vez do mundo.

**O vão entre as duas trajetórias é 0,75 m, e ele tem nome.** Não é "erro do AMCL": é exatamente o que a transformada `map → odom` corrige, a deriva acumulada da odometria. Escreva assim no relatório; é a diferença entre descrever uma figura e explicá-la.

**As duas esperas duram 2,00 s e 2,10 s.** São diferentes de propósito: uma tolerância que nunca é exercitada não prova nada. A régua declara `2,00 s ± 0,25 s` **antes** de medir — como na Aula 9, e pelo mesmo motivo.

!!! tip "O `/tf_static` é publicado uma vez, e é o que mais falta no bag"
    Ele sai com durabilidade *transient local* no instante em que o sistema sobe. Fora da lista do `record`, a sua reprodução é um laser flutuando sem corpo — e você só descobre **depois**, quando não há mais como regravar a sessão.

    ```bash
    ros2 bag record -o sessao-tp4 /odom /amcl_pose /scan /cmd_vel /tf /tf_static
    ```

    Grave também o que a **sua** análise precisa reproduzir, e diga no relatório o que ficou de fora e por quê. O enunciado diz "a sessão inteira"; a lista acima é o mínimo que sustenta o gráfico.

---

## A tarefa da semana

**O que fazer.** Um goal cumprido sem intervenção (amanhã), uma rota de três pontos com os costmaps explicados (segunda), e a escolha de caminho para a interrupção de 0,5 m, trazida por escrito.

**O que usar.** O `diagnosticar_nav2.py` quando travar; o `rota.py` da Aula 15 com os seus pontos; o `aula16-arvore-bag` para a árvore e para a régua da sessão.

**Como adequar ao seu projeto.** Os pontos da rota saem do **seu** mapa, escolhidos sobre o costmap global. A árvore que você copiar vai para o **seu** pacote, e o caminho apontado no `behavior_tree` tem de existir na máquina que roda o `bt_navigator` — aponte para dentro do `share` do pacote instalado, não para a pasta de fontes.

**Como saber que terminou.** O diagnóstico sem pendências, e estas três:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 action list | grep navigate            # navigate_to_pose
ros2 topic info /cmd_vel --verbose          # 1 publicador
ros2 run tf2_ros tf2_echo map odom          # NÃO identidade
```

E a evidência commitada: o vídeo curto do goal em `docs/evidencias/tp4/goal-unico.mp4` (ou o link, testado numa janela anônima).

## Desafio — medir a sua própria sessão antes de ter uma

Opcional, e responde-se medindo.

Rode `python3 medir_sessao.py` no CSV sintético e leia a tabela inteira. Depois **mude uma coisa só** e meça de novo: `--sem-eventos`, ou uma espera de 1,2 s, ou outra semente. A pergunta é: **qual coluna da tabela denuncia a mudança, e qual fica igual?**

Quem souber responder isso já sabe o que procurar no próprio bag na semana que vem — e é exatamente o que separa quem entrega a figura de quem entrega a figura explicada.

## Para a próxima aula — 10/11

**A sua escolha de caminho para a interrupção**, funcionando ou travada, dá no mesmo: a aula é sobre ela. Quem for de C++ traz o plugin compilando; quem for de cliente traz o `vigia` rodando. E tragam o **bag** da sessão: a partir dele, a análise offline é o que fecha o item 2.

Começa também o relógio dos itens 3 e 4 — MetaDrive em 17/11, CNN em 19/11. **Os 500 frames rotulados são a parte que não comprime.**
