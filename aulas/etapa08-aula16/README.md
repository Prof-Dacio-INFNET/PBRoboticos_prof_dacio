# Aula 16 — O caminho até o Nav2 navegar, e a sessão que se reproduz sem o robô

**Terça, 03/11/2026 · sala SJ205 · Etapa 8 (26/10–07/11)**

[:material-file-pdf-box: Slides da Aula 16 (PDF)](apresentacao-aula16.pdf){ .md-button .md-button--primary }
[:material-stethoscope: Diagnóstico do Nav2](../../exemplos/aula16-clinica/index.md){ .md-button }
[:material-chart-timeline-variant: Árvore e sessão gravada](../../exemplos/aula16-arvore-bag/index.md){ .md-button }

!!! info "Como esta página funciona"
    Em sala eu **demonstrei** o caminho no meu ambiente, e vocês observaram. **O que é para rodar no seu ambiente está na [tarefa da semana](#a-tarefa-da-semana)**, como uma sequência ordenada para fazer em casa, no seu ritmo — é lá que a aula acontece para cada um.

    As seções dos blocos 1 a 4 descrevem **o que foi mostrado e o que observar**: elas servem para reconhecer, na sua tela, o que apareceu na minha. Cada bloco se sustenta sozinho e diz o que pressupõe; dá para ler fora de ordem.

## Cenas dos últimos episódios

**Na Aula 15** o Nav2 subiu com o mapa de vocês e o AMCL convergiu depois do *2D Pose Estimate*. Antes disso, a tabela do filtro de partículas mostrou os três cenários terminando com a nuvem entre 6,3 e 7,8 cm — e um deles a **5,92 m** da verdade, com o rumo invertido. A frase que ficou foi essa: **concordância interna não é evidência**.

E a aula começou com um defeito do próprio material: `rviz:=true` na linha de comando, e o RViz2 não abria. O `launch_arguments` de um `IncludeLaunchDescription` não é escopado, e o `'rviz': 'false'` que o launch passava ao mundo da Aula 11 apagava o valor digitado. **Catorze processos no ar, nenhuma mensagem de erro, e o botão que faltava era o que fazia a aula acontecer.**

Hoje a aula tem duas metades, e as duas descendem daquilo. A primeira é o **caminho até o Nav2 navegar**: o sistema saudável, o diagnóstico, e os três defeitos mudos que mais aparecem. A segunda é começar o item 2 do TP4, que é onde a navegação deixa de depender de você estar na frente dela.

## A ideia da aula em uma frase

**Um sistema que só funciona com você na frente dele não está entregue.** É isso que o item 2 do TP4 cobra quando pede uma árvore de comportamento *e* uma sessão gravada que se reproduz offline: a árvore decide sem você, e o bag prova sem você. O resto da aula é consequência disso.

## O que você sai sabendo hoje, e o que isso vale no seu projeto

| A capacidade | No seu projeto |
|---|---|
| descobrir, em dez segundos, por que o seu Nav2 não está navegando | você deixa de depender de mim para destravar — e trava menos |
| mandar o robô até um objetivo e **provar que ele chegou** | é a primeira vez que o seu sistema faz algo de ponta a ponta sozinho |
| escolher, e saber dizer, **onde mora a decisão** de interromper | é arquitetura, e é o que você defende na arguição |
| medir uma sessão gravada com o robô desligado | a demonstração do fim do semestre deixa de depender de sorte |

## O que foi demonstrado, onde está na tarefa, e quando vence

As datas estão nesta tabela e em [Gates de cada TP](../../recursos/gates-tps.md) — elas são **referência para consultar**, não o assunto da aula.

| Bloco demonstrado | O que você faz em casa | Gate | Vence em |
|---|---|---|---|
| 1. O caminho para navegar | [passos 1 a 4](#passo-1-preparar-os-terminais) da tarefa: o diagnóstico, os casos, o goal e o vídeo de 20 s | G4.1 | **04/11** |
| 2. A rota e os costmaps | [passo 5](#passo-5-a-rota-de-tres-pontos-e-os-dois-paragrafos-dos-costmaps): três pontos do seu mapa e os dois parágrafos | G4.2 | 09/11 |
| 3. A árvore | [passo 6](#passo-6-a-escolha-do-caminho-da-interrupcao-por-escrito): a escolha do caminho, por escrito, trazida à próxima aula | G4.3 | 10/11 (aula) · 12/11 (gate) |
| 4. A sessão gravada | o [desafio](#desafio-medir-a-sua-propria-sessao-antes-de-ter-uma), e o seu bag quando a interrupção existir | G4.4 | 15/11 |
| depois desta etapa | os itens 3 e 4 do TP4: MetaDrive e a CNN | G4.5 · G4.6 | 17/11 · 19/11 |

Se o tempo apertou em sala, **o bloco 4 cedeu** — ele é o que vence mais tarde e o mais autocontido desta página. O que não cede é o bloco 1: é o que vence primeiro.

## Pegar o material

Este é o bloco que abre o seu trabalho em casa. Ele define as três variáveis da disciplina e copia os dois exemplos para dentro do seu projeto.

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

Nenhum dos dois precisa de `colcon build` para esta semana: o diagnóstico é Python puro, e a régua da sessão também. O pacote ROS 2 do segundo exemplo entra depois, quando você for gravar o seu bag.

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Um bloco que começa com ela supõe que o mesmo terminal já rodou um bloco que define as variáveis; um terminal novo começa sempre pelas três variáveis e pelas duas linhas de `source`, como no [passo 1](#passo-1-preparar-os-terminais) da tarefa.

---

## Bloco 1 — O caminho para navegar, demonstrado

**Pressupõe:** o Nav2 da Aula 15 compilado no seu workspace. **Para fazer: passos 1 a 4 da [tarefa](#a-tarefa-da-semana).**

### O sistema saudável, e o que ele mostra

Foi o percurso inteiro, na ordem em que vocês vão fazê-lo. No **Terminal A**, o sistema com o RViz2 (`ros2 launch aula15_nav2 nav2.launch.py rviz:=true`). No RViz2, o *2D Pose Estimate* na posição do robô — e a nuvem de partículas fechando em volta dele. Depois o *2D Goal Pose* num ponto livre: o plano global desenhado até o alvo, a janela do costmap local acompanhando o robô, e o robô **chegando**. E o vídeo de 20 s, gravado com o celular apontado para a tela, na frente de vocês: é isso que o vídeo precisa ter — o robô saindo e chegando. Print de plano desenhado é planejamento, não navegação.

### O diagnóstico no sistema saudável

Com o sistema no ar, no **Terminal B**, o `diagnosticar_nav2.py`. Ele percorre dez verificações na ordem em que compensa olhar — ambiente, nós no ar, ciclo de vida, TF, pose inicial, `/cmd_vel`, a cadeia até o `/cmd_vel_nav`, os servidores de ação, os costmaps e o mapa — e devolve **uma lista de lugares para olhar**, cada um com a próxima ação. No sistema saudável a lista sai vazia, e a linha do `/cmd_vel` é a que mais merece ser lida:

```text
6. O /cmd_vel -- publicador que nao e' do Nav2 e' defeito, e nao da erro
  achei      /cmd_vel so' com os publicadores do Nav2    velocity_smoother + behavior_server x5, como esperado
  achei      /cmd_vel tem assinante                      mundo
[...]
Nao sobrou nada para olhar do que este script alcanca.
Isso NAO quer dizer que o Nav2 esta pronto, e nao quer dizer que o G4.1 fecha.
Quer dizer que esgotei o que um script enxerga [...]
```

**Seis publicadores em `/cmd_vel`, e os seis são legítimos.** O `velocity_smoother` é quem leva o goal até o robô; o `behavior_server` aparece **uma vez por comportamento** — *spin*, *backup*, *drive_on_heading*, *assisted_teleop*, *wait* —, e cada um só fala durante uma recuperação. A quantidade de `behavior_server` muda com os plugins do seu `nav2.yaml`. A regra, então, não é por contagem: **publicador que não é do Nav2 é defeito** — qualquer nome além de `velocity_smoother` e `behavior_server`.

!!! danger "Ele não corrige, não valida e não antecipa nota"
    `achei` não quer dizer certo. `nao achei` não quer dizer errado. Nos dois casos quer dizer: **vá olhar isso.**

    E o que ele marca com `olhe` é o que mais pesa, porque nenhum comando alcança: se o robô **realmente anda**, se o mapa publicado é **do seu cenário**, se a **rota faz sentido** na sua planta, se o relatório responde ao que foi pedido. Isso é o que o G4.1 e o G4.2 avaliam — e é leitura minha, não saída de script. Sair com a lista vazia não é ter terminado: é ter esgotado o que um script enxerga.

### Os três casos, e o mesmo gesto para os três

Cada caso foi demonstrado do mesmo jeito: **quebrar → rodar o diagnóstico → ler a primeira linha de "Onde olhar" → corrigir → rodar de novo.** O que importa observar não é o defeito; é que a primeira linha da lista aponta para ele, mesmo quando a tela do launch fala de outra coisa.

**Caso 1 — ninguém deu a pose inicial.** O sistema subiu sem o clique no *2D Pose Estimate*. No terminal do launch, o `planner_server` repete *Timed out waiting for transform from base_footprint to map*, e o gerenciador de navegação para nele. A mensagem fala de transformada; a causa é um clique que faltou. A primeira linha de "Onde olhar":

```text
   1. aresta map -> odom
      quem publica essa aresta e' o AMCL, e no Humble ele nao publica NADA
      antes da pose inicial (`if (!initial_pose_is_known_) return;`): clique o
      2D Pose Estimate no RViz2, ou suba o launch com
      `pose_inicial_auto:=true`. [...]
```

Sem a aresta `map → odom` o quadro `map` não existe, e por isso ela vem **antes** de qualquer nó inativo na lista: o nó parado é eco dela.

**Caso 2 — um publicador intruso em `/cmd_vel`.** Com o sistema saudável, num **Terminal C**, `ros2 run aula11_mundo piloto` — o piloto reativo da Aula 11. Não aparece erro em lugar nenhum: o robô obedece ao último que falou, e o sintoma é andar truncado, ou andar sozinho. O `ros2 topic info /cmd_vel --verbose` mostra sete blocos de publicador; o diagnóstico separa o que é do Nav2 do que não é e **nomeia o intruso**:

```text
  nao achei  /cmd_vel so' com os publicadores do Nav2    intruso: piloto
```

A correção é derrubar o intruso (`Ctrl+C` no Terminal C), e não mexer em nenhum dos seis do Nav2.

**Caso 3 — o gerenciador parado.** O sistema subiu com `autostart:=false`: os nós estão no ar, mas nenhum foi ativado. A seção 3 do diagnóstico mostra os nove nós em `unconfigured [1]`, e a lista final tem **um** item — o primeiro nó inativo na ordem de subida, que é onde o gerenciador parou. O resto vem agrupado numa linha, como consequência:

```text
   1. ativo: map_server
      este e' o primeiro da ordem de subida que nao esta ativo: o gerenciador
      parou AQUI -- ou alguem o desativou a mao. [...]
      (e mais 8 nos inativos por consequencia: amcl, controller_server,
      smoother_server, planner_server, behavior_server, bt_navigator,
      waypoint_follower, velocity_smoother; e, pelo mesmo ciclo de vida
      parado, a aresta map -> odom e o /cmd_vel sem velocity_smoother --
      resolva o primeiro e rode de novo)
```

Compare com o caso 1: lá a aresta `map → odom` é a **raiz**; aqui ela é **consequência**, porque o AMCL nem ativou. O diagnóstico só manda dar a pose inicial quando o AMCL está ativo — e é essa diferença que diz por onde começar.

**Nenhum dos três produz mensagem de erro.** É a mesma família do `rviz:=true` da semana passada, e é por isso que a primeira coisa a fazer não é ler o log: é perguntar ao sistema o que ele tem. Há um quarto caso frequente — a cadeia do `/cmd_vel_nav` quebrada — que não foi demonstrado; ele está na tarefa, no [passo 3](#passo-3-os-tres-casos-e-o-quarto), com o caminho escrito.

---

## Bloco 2 — A rota e os costmaps, demonstrados

**Pressupõe:** o bloco 1 — o sistema no ar e a pose inicial dada. **Para fazer: [passo 5](#passo-5-a-rota-de-tres-pontos-e-os-dois-paragrafos-dos-costmaps) da tarefa.**

O que foi mostrado: o `rota.py` da Aula 15 **sem argumento nenhum**, percorrendo os cinco pontos da rota padrão sem ninguém clicando; no RViz2, o display de cada costmap **ligado e desligado**, um de cada vez, para a diferença ficar visível — o global cobre o mapa inteiro, o local é a janela que segue o robô; e os quatro números do YAML lidos do sistema no ar, com `ros2 param get`: a largura e a resolução do costmap local, o `robot_radius` e o `inflation_radius` do global.

A explicação dos dois costmaps é metade do G4.2, e cabe em duas frases:

> O costmap **global** é o mapa inteiro com a inflação, e é sobre ele que o NavFn planeja. O **local** é uma janela rolante de poucos metros, reconstruída a partir do laser a cada ciclo, e é sobre ela que o DWB escolhe a próxima velocidade.

Quem escrever isso com os números do **seu** YAML entrega o item bem feito sem escrever uma linha de código a mais.

!!! warning "Objetivo recusado não é objetivo que falhou"
    No fim do bloco eu cliquei um goal **colado numa parede**, de propósito. O servidor **recusou**: nem tentou planejar, e o robô não se mexeu. Ponto em célula ocupada, ou a menos de `robot_radius` de uma parede, tem esse efeito. Escolha os pontos olhando o **costmap global** no RViz2, não o mapa cru — e lembre que `robot_radius` decide se a passagem abre, enquanto `inflation_radius` decide só o quanto ela custa.

---

## Bloco 3 — A árvore, e o que o Humble não tem

**Pressupõe:** nada no ar — é leitura de arquivo. **Para fazer: [passo 6](#passo-6-a-escolha-do-caminho-da-interrupcao-por-escrito) da tarefa.**

O `bt_navigator` executa um **XML**, e os prontos estão em `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/`. O exemplo desta aula traz dois: a árvore oficial `navigate_to_pose_w_replanning_and_recovery.xml` copiada e **comentada bloco a bloco** (`padrao_comentada.xml`), e uma variante com a espera de 2 s no ramo de recuperação (`com_espera.xml`). Em sala eu abri a comentada e li: é um arquivo de texto, e dá para ler.

Depois, o `grep` que decide o item 2, na lista oficial de nós registrados:

```bash
# ── qualquer terminal: é só leitura de arquivo ──
grep -i "Condition" /opt/ros/humble/share/nav2_behavior_tree/nav2_tree_nodes.xml | head -20
```

!!! danger "Não existe, no Humble, um nó de árvore que meça distância a obstáculo"
    Há condições para bateria baixa, para objetivo trocado, para caminho inválido, para tempo decorrido — **e nenhuma para "obstáculo a menos de 0,5 m"**.

    Ou seja: a árvore sozinha **não cumpre** o enunciado. O que ela faz é decidir o que acontece quando alguém lhe diz que há um obstáculo. Quem diz é você, por um dos dois caminhos:

    - **o caminho completo**, um nó de condição próprio em C++ registrado como plugin do `nav2_behavior_tree`, composto na árvore com o `Wait` de 2 s dentro de um `ReactiveFallback`;
    - **o caminho de cliente**, o `vigia.py` do exemplo: ele assina o `/scan`, cancela o goal quando a distância mínima cai abaixo de 0,5 m, espera 2 s e **reenvia o mesmo objetivo**. É a Aula 8 outra vez — cancelamento de ação —, e roda sem compilar C++.

    **Os dois passam.** O que não passa é não dizer qual você usou, e por quê.

Duas armadilhas que custam tempo e não dizem o nome:

O `wait_duration` do nó `Wait` é um **inteiro**. Escrever `2.0` ali não é "dois segundos com casa decimal": é um valor que a árvore recusa a carregar, e o `bt_navigator` falha ao ativar — sem apontar a linha.

E **comentário de XML não pode conter dois traços seguidos**. Toda opção do ROS 2 começa com dois traços, então colar um `ros2 run ... --ros-args` dentro de um `<!-- -->` faz o parser recusar **o arquivo inteiro**, com uma mensagem que não menciona traços. É por isso que, nas duas árvores do exemplo, os comandos ficam fora dos comentários.

---

## Bloco 4 — A sessão gravada, e a figura que ela produz

**Pressupõe:** para a régua, nada no ar; para gravar, o sistema do bloco 1. **Para fazer: o [desafio](#desafio-medir-a-sua-propria-sessao-antes-de-ter-uma), e o seu bag quando a interrupção existir.**

O item 2 termina pedindo o que é, na prática, a parte mais fácil de provar: **a sessão gravada e reproduzida offline, com o gráfico da trajetória**. O caminho é curto e não depende de biblioteca nova:

```
ros2 bag record  ──►  bag  ──►  ros2 bag play --clock  ──►  gravar_pose  ──►  CSV  ──►  figura
```

Em sala foram vinte segundos gravados ao vivo com o robô andando, o `ros2 bag info` da gravação — com o `/tf_static` aparecendo com **uma** mensagem só —, e o `ros2 bag play` tocando de volta com o sistema desligado. A linha de gravação, para quando for a sua vez:

```bash
# ── Terminal C, novo, com o sistema do Terminal A no ar e um goal andando ──
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
mkdir -p "$PB_DIR/bags" && cd "$PB_DIR/bags"
ros2 bag record -o sessao-tp4 /odom /amcl_pose /scan /cmd_vel /tf /tf_static
```

!!! tip "O `/tf_static` é publicado uma vez, e é o que mais falta no bag"
    Ele sai com durabilidade *transient local* no instante em que o sistema sobe. Fora da lista do `record`, a sua reprodução é um laser flutuando sem corpo — e você só descobre **depois**, quando não há mais como regravar a sessão. Grave também o que a **sua** análise precisa reproduzir, e diga no relatório o que ficou de fora e por quê.

Depois, **a régua antes do robô**: o exemplo gera uma sessão sintética, determinística, com dois eventos de obstáculo, e mede. Não precisa de ROS 2 no ar:

```bash
# ── qualquer terminal, depois do bloco "Pegar o material" ──
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

---

## A tarefa da semana

**É aqui que a aula acontece para você.** Os sete passos abaixo são o que eu demonstrei, na ordem em que compensa fazer, para rodar no seu ambiente e no seu ritmo. Cada passo diz o que pressupõe, o que observar e o que fazer quando o observado não bater.

| | |
|---|---|
| **O que fazer** | o robô indo até um objetivo sozinho, com o vídeo de 20 s; uma rota de três pontos do seu mapa, com os dois costmaps explicados; e a escolha do caminho da interrupção de 0,5 m, por escrito |
| **O que usar** | o `nav2.launch.py` da Aula 15, o `diagnosticar_nav2.py` (em `aula16-clinica`), o `rota.py` da Aula 15 e as árvores de `aula16-arvore-bag` |
| **Como adequar ao seu projeto** | os pontos saem do **seu** mapa, escolhidos sobre o costmap global; os números dos parágrafos saem do **seu** YAML; a árvore que você copiar vai para o **seu** pacote, e o caminho apontado tem de existir no `share` instalado, não na pasta de fontes |
| **Como saber que terminou** | o [passo 7](#passo-7-como-saber-que-terminou) |

São três terminais, sempre com o mesmo nome: **A — o sistema** (o launch ocupa o terminal), **B — o diagnóstico e os comandos**, e **C — o intruso**, só no caso 2. Todo terminal novo começa pelas três variáveis e pelas duas linhas de `source`.

### Passo 1 — Preparar os terminais

**Pressupõe:** o material baixado ([Pegar o material](#pegar-o-material)) e o Nav2 da Aula 15 no seu workspace.

**Terminal A — o sistema.** Terminal novo, nada precisa estar no ar:

```bash
# ── Terminal A: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 pkg list | grep -c aula15_nav2        # tem de ser 1
ros2 pkg list | grep -c aula11_mundo       # tem de ser 1
```

Se alguma das duas devolveu `0`, o pacote não está **compilado** neste workspace — e aí é `colcon build`, não `source`. No mesmo Terminal A:

```bash
# ── Terminal A, só se uma das contagens acima deu 0 ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && colcon build --symlink-install \
  --packages-select aula11_mundo aula15_nav2 && source install/setup.bash
```

!!! warning "`Package 'aula15_nav2' not found: searching: ['/opt/ros/humble']`"
    Não quer dizer que o pacote não existe: a lista entre colchetes mostra **onde ele procurou**, e nela só aparece o `/opt/ros/humble`. Falta a segunda linha de `source`, a do seu workspace — neste terminal.

### Passo 2 — O sistema no ar, e o diagnóstico lido

**Pressupõe:** o passo 1. **Observe:** a lista final, e a linha do `/cmd_vel`.

**Terminal A — o sistema.** O launch ocupa o terminal até você derrubá-lo com `Ctrl+C`:

```bash
# ── Terminal A (o do passo 1, já com o source) ──
ros2 launch aula15_nav2 nav2.launch.py rviz:=true
```

Com o RViz2 aberto e o mapa na tela, clique o **2D Pose Estimate** na posição do robô e arraste na direção em que ele olha. A nuvem de partículas tem de se concentrar em volta dele.

**Terminal B — o diagnóstico.** Terminal novo, com o Terminal A no ar:

```bash
# ── Terminal B: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
cd "$PB_DIR/aula16-clinica" && python3 diagnosticar_nav2.py
```

Se a sua máquina é lenta (WSL2 cheio, notebook com pouca memória) e várias linhas saem como `olhe` por falta de resposta, dê mais paciência a cada comando. No mesmo Terminal B:

```bash
# ── Terminal B, só se a máquina é lenta ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-clinica" && python3 diagnosticar_nav2.py --timeout 10
```

**O que você tem de ver**, com o sistema saudável: a linha `/cmd_vel so' com os publicadores do Nav2` como `achei`, com `velocity_smoother + behavior_server x5, como esperado` (o número de `behavior_server` pode ser outro, se o seu `nav2.yaml` tem outros comportamentos), e no fim `Nao sobrou nada para olhar do que este script alcanca` — seguido do parágrafo que diz o que isso **não** significa. Leia esse parágrafo: ele é a parte que vale nota.

**Se a lista não saiu vazia:** leia **a primeira linha** de *Onde olhar* e vá ao passo 3. As outras linhas costumam ser eco da primeira; resolva a primeira e rode de novo.

### Passo 3 — Os três casos, e o quarto

**Pressupõe:** o passo 2, com a lista de *Onde olhar* na tela. Procure abaixo o caso cuja **primeira linha** bate com a sua. Depois de corrigir, rode o diagnóstico de novo no Terminal B — a correção só vale quando a linha some:

```bash
# ── Terminal B, depois de cada correção ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-clinica" && python3 diagnosticar_nav2.py
```

#### Caso 1 — a primeira linha é `aresta map -> odom`

**O que você vê.** No Terminal A, o `planner_server` repetindo *Timed out waiting for transform from base_footprint to map*, e o gerenciador de navegação parado nele. Na lista, `aresta map -> odom` em primeiro, às vezes com um nó inativo logo abaixo.

**O que é.** Ninguém deu a pose inicial. Quem publica `map → odom` é o AMCL, e no Humble ele não publica nada antes da pose (`if (!initial_pose_is_known_) return;`). Sem essa aresta o quadro `map` não existe, e o planejador não tem onde planejar. O nó parado é consequência.

**O que fazer.** Clique o **2D Pose Estimate** no RViz2 e rode o diagnóstico de novo. Se preferir que a pose venha sozinha a cada subida, derrube o Terminal A com `Ctrl+C` e suba de novo com a pose de largada do launch:

```bash
# ── Terminal A, depois do Ctrl+C ──
ros2 launch aula15_nav2 nav2.launch.py rviz:=true pose_inicial_auto:=true
```

#### Caso 2 — a primeira linha é `/cmd_vel so' com os publicadores do Nav2`

**O que você vê.** O robô anda truncado, ou anda sozinho, e nenhum nó reclama. Na lista, a linha do `/cmd_vel` como `nao achei`, com o nome de fora: `intruso: piloto`, ou outro.

**O que é.** Um publicador que não é do Nav2 está falando em `/cmd_vel`, e o robô obedece ao último que falou. Os do Nav2 são o `velocity_smoother` e o `behavior_server` — este repetido, um por comportamento; **qualquer outro nome é intruso**. Para ver a lista inteira com os seus olhos, no Terminal B:

```bash
# ── Terminal B ──
ros2 topic info /cmd_vel --verbose | grep "Node name"
```

**O que fazer.** Derrube o intruso, e só ele. O `piloto` da Aula 11 sai com `Ctrl+C` no terminal em que você rodou `ros2 run aula11_mundo piloto`; se ele veio de um launch do mundo, suba esse launch com `piloto:=false`. Um `teleop_twist_keyboard` esquecido sai com `Ctrl+C`. Se aparecer `velocity_smoother x2`, são dois Nav2 no ar: um launch antigo num terminal esquecido.

!!! tip "Para reconhecer o caso, provoque-o (opcional)"
    Foi assim que ele foi demonstrado. Com o sistema saudável no ar, abra um **Terminal C — o intruso**, rode o bloco abaixo, rode o diagnóstico no Terminal B e procure `intruso: piloto`. Depois derrube o Terminal C com `Ctrl+C` e rode o diagnóstico de novo.

    ```bash
    # ── Terminal C: uma vez por terminal ──────────────────
    export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
    export PB_DIR="$HOME/projeto-pb-$PB_USER"
    export PB_WS="$PB_DIR/ros2_ws"
    source /opt/ros/humble/setup.bash
    source "$PB_WS/install/setup.bash"
    ros2 run aula11_mundo piloto
    ```

#### Caso 3 — a primeira linha é `ativo: <um nó>`, com a linha agrupada embaixo

**O que você vê.** O Nav2 "subiu", mas o RViz2 não aceita goal e nada se mexe. Na seção 3 do diagnóstico, vários nós como `nao achei`; na lista final, **um** item — o primeiro nó inativo na ordem de subida — e, embaixo dele, a linha `(e mais N nos inativos por consequencia: ...)`.

**O que é.** O gerenciador de ciclo de vida ativa um nó por vez e **parou ali**. Os de baixo estão inativos por consequência; consertar os de baixo é consertar o lugar errado. As causas comuns: o launch subiu com `autostart:=false`; um nome na lista `node_names` do gerenciador sem nó correspondente no ar; ou um parâmetro que o nó recusou ao configurar.

**O que fazer.** Comece pelo nó da primeira linha. Leia o terminal do launch (Terminal A) procurando o `lifecycle_manager`: ele nomeia o nó em que travou. Se você subiu com `autostart:=false`, derrube com `Ctrl+C` e suba sem ele, como no passo 2. Se não foi isso, a própria linha do diagnóstico traz o comando para tentar a configuração à mão (`ros2 lifecycle set /<nó> configure`) e ver o erro que o gerenciador engoliu.

!!! note "Por que a aresta `map -> odom` aparece aqui como consequência"
    No caso 1 ela é a raiz: o AMCL está ativo e só falta a pose. No caso 3 o AMCL nem ativou, e mandar dar a pose seria apontar para o lugar errado. É por isso que o diagnóstico a põe na linha agrupada.

#### O quarto caso — o robô não anda e ninguém reclama (não demonstrado)

**O que você vê.** O goal é aceito, o plano aparece no RViz2, e o robô fica parado. Na lista, `ativo: velocity_smoother` como primeira linha, ou `/cmd_vel_nav ligado nas duas pontas` como `nao achei`.

**O que é.** A cadeia do `/cmd_vel` está quebrada: o `controller_server` fala em `/cmd_vel_nav`, e quem repassa ao `/cmd_vel` é o `velocity_smoother`. Sem ele ativo — ou com ele fora do launch e os remapeamentos ainda no lugar —, ninguém ouve o controlador.

**O que fazer.** Confira as duas pontas do `/cmd_vel_nav` e o estado do suavizador, no Terminal B:

```bash
# ── Terminal B ──
ros2 topic info /cmd_vel_nav --verbose | grep -E "Node name|Endpoint type"
ros2 lifecycle get /velocity_smoother        # tem de ser active [3]
```

Se ele está no ar mas não ativo, ative-o e rode o diagnóstico de novo. No Terminal B:

```bash
# ── Terminal B, só se o velocity_smoother não estava active [3] ──
ros2 lifecycle set /velocity_smoother activate
```

Se ele **não aparece** como assinante do `/cmd_vel_nav`, o defeito está no seu launch: o `velocity_smoother` saiu da lista de nós, ou saiu com os remapeamentos (`cmd_vel → cmd_vel_nav` no controlador, `cmd_vel_smoothed → cmd_vel` no suavizador) ainda no lugar. Compare com o `nav2.launch.py` da Aula 15.

### Passo 4 — O goal, e o vídeo de 20 s

**Pressupõe:** o passo 2 com a lista vazia — o sistema no ar e a pose dada. **Observe:** o robô saindo e chegando, não o plano.

Pelo RViz2: o **2D Goal Pose** num ponto livre do **seu** mapa (ele publica em `/goal_pose`). Por código, o `rota.py` da Aula 15 com um ponto só — `[x, y, yaw]`, troque pelos números de um ponto do seu mapa. No Terminal B:

```bash
# ── Terminal B, com o Terminal A no ar e a pose dada ──
ros2 run aula15_nav2 rota --ros-args -p rota:="[9.0, 2.0, 1.57]"
```

Enquanto o robô anda, grave **20 segundos** com o celular apontado para a tela: o robô saindo e chegando, com o plano global e o costmap local visíveis no RViz2. Não precisa ser bonito; precisa existir. O vídeo vai para `docs/evidencias/tp4/goal-unico.mp4` no seu repositório — ou, se for grande, um link público ou não listado, **testado numa janela anônima**.

**Se o goal for recusado:** o ponto está em célula ocupada ou colado numa parede — escolha outro, olhando o costmap global (passo 5). **Se o robô não sair do lugar:** volte ao diagnóstico (passo 2); o quarto caso do passo 3 é o mais provável.

### Passo 5 — A rota de três pontos, e os dois parágrafos dos costmaps

**Pressupõe:** o passo 4. **Observe:** a rota inteira cumprida, e os quatro números do seu YAML.

Escolha três pontos olhando o **costmap global** no RViz2 — longe das paredes infladas — e anote `x`, `y` e o rumo de cada um. A rota é uma lista achatada, três números por ponto. O exemplo abaixo usa três pontos da rota padrão do mundo da Aula 11; troque pelos seus. No Terminal B:

```bash
# ── Terminal B, com o Terminal A no ar e a pose dada ──
ros2 run aula15_nav2 rota --ros-args -p rota:="[2.0, 4.0, 0.0, 6.1, 4.0, 0.0, 9.0, 2.2, -1.57]"
```

A evidência do G4.2 é o status da ação ao fim de cada ponto, que o `rota.py` imprime, mais os prints dos dois costmaps. Para os prints, no RViz2, ligue e desligue o display de cada costmap, um de cada vez.

Depois, os quatro números que entram nos parágrafos. Com o sistema no ar, no Terminal B:

```bash
# ── Terminal B, com o Terminal A no ar ──
ros2 param get /local_costmap/local_costmap width
ros2 param get /local_costmap/local_costmap resolution
ros2 param get /global_costmap/global_costmap robot_radius
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
```

Escreva os dois parágrafos com esses números: o **global** é o mapa inteiro com a inflação, e é sobre ele que o NavFn planeja; o **local** é a janela rolante de tantos metros, na resolução tal, reconstruída do laser, e é sobre ela que o DWB escolhe a próxima velocidade. E diga, com o seu `robot_radius`, se as passagens mais estreitas do seu mapa abrem ou não.

### Passo 6 — A escolha do caminho da interrupção, por escrito

**Pressupõe:** nada no ar. **Observe:** a lista de condições do Humble.

Leia as duas árvores do exemplo e confira, você mesmo, a lista de condições. Em qualquer terminal:

```bash
# ── qualquer terminal ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag" && ls arvores/
grep -i "Condition" /opt/ros/humble/share/nav2_behavior_tree/nav2_tree_nodes.xml | head -20
```

Depois escreva, em três frases, no rascunho do seu relatório do TP4: **qual caminho** você vai seguir (o completo, em C++, ou o de cliente, com o `vigia.py`); **por quê**; e **onde mora a decisão** de interromper — na árvore ou no seu nó. Traga isso para a próxima aula: ela é sobre essa escolha.

### Passo 7 — Como saber que terminou

Com o sistema no ar e a pose dada, no Terminal B:

```bash
# ── Terminal B, com o Terminal A no ar e a pose dada ──
ros2 action list | grep navigate               # navigate_to_pose
ros2 topic info /cmd_vel --verbose | grep "Node name"   # só velocity_smoother e behavior_server
```

E a aresta `map → odom`, que tem de existir e **não** ser identidade. O `tf2_echo` não termina sozinho: leia uma ou duas linhas de `Translation` e saia com `Ctrl+C`. No Terminal B:

```bash
# ── Terminal B; saia com Ctrl+C ──
ros2 run tf2_ros tf2_echo map odom
```

Você terminou quando tem, nesta ordem:

1. o diagnóstico sem pendências — e o parágrafo do que ele **não** alcança lido;
2. o `/cmd_vel` só com `velocity_smoother` e `behavior_server`;
3. o vídeo de 20 s do goal commitado em `docs/evidencias/tp4/goal-unico.mp4`, ou o link testado numa janela anônima;
4. a rota de três pontos cumprida, com o status de cada ponto e os prints dos dois costmaps;
5. os dois parágrafos dos costmaps, com os números do **seu** YAML;
6. as três frases da escolha do caminho da interrupção.

Travou num passo e o observado não bate com nada desta página? Poste no fórum do Moodle a saída do diagnóstico (`python3 diagnosticar_nav2.py --sem-cor | tee diag.txt` gera o texto) e o passo em que você está.

## Desafio — medir a sua própria sessão antes de ter uma

Opcional, e responde-se medindo. **Pressupõe:** o material baixado; nada no ar.

Rode a régua no CSV sintético (bloco 4) e leia a tabela inteira. Depois **mude uma coisa só** e meça de novo. Por exemplo, sem os eventos de obstáculo, num arquivo à parte:

```bash
# ── qualquer terminal ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 simular_sessao.py --sem-eventos --saida sem-eventos.csv
python3 medir_sessao.py sem-eventos.csv
```

Outras mudanças de uma coisa só: uma espera de 1,2 s (`--espera 1.2`), ou outra semente (`--semente`). A pergunta é: **qual coluna da tabela denuncia a mudança, e qual fica igual?**

Quem souber responder isso já sabe o que procurar no próprio bag — e é exatamente o que separa quem entrega a figura de quem entrega a figura explicada.

## Para a próxima aula

**A sua escolha de caminho para a interrupção**, funcionando ou travada, dá no mesmo: a aula é sobre ela. Quem for de C++ traz o plugin compilando; quem for de cliente traz o `vigia` rodando. E, quando a interrupção existir, o **bag** da sessão: a partir dele, a análise offline é o que fecha o item 2.

Começa também o relógio dos itens 3 e 4 — as datas estão na [tabela](#o-que-foi-demonstrado-onde-esta-na-tarefa-e-quando-vence) e em [Gates de cada TP](../../recursos/gates-tps.md). **Os 500 frames rotulados são a parte que não comprime**: comece a salvar frames esta semana.
