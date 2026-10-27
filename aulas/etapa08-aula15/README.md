# Aula 15 — Navegação autônoma: o Nav2 em cima do seu mapa

**Terça, 27/10/2026 · sala SJ205 · Etapa 8 (26/10–07/11)**

[:material-file-pdf-box: Slides da Aula 15 (PDF)](apresentacao-aula15.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula15-nav2`](../../exemplos/aula15-nav2/index.md){ .md-button }
[:material-flag-checkered: Gates do TP4](../../recursos/gates-tps.md){ .md-button }

## Cenas dos últimos episódios

**Na Aula 14** o enunciado do TP3 foi lido item por item, com o roteiro de revisão rodando ao lado — e a entrega foi na sexta, 23/10. O que ficou dito ali vale para hoje em outra escala: **o enunciado é a rubrica**, e o TP4 tem quatro itens que nenhum script confere por você.

**As peças que a aula de hoje vai montar são todas suas.** Da **Aula 11** vem o mundo e a deriva: a odometria erra 3%, o erro só cresce, e `map → odom` era um `static_transform_publisher` mentiroso publicando identidade — hoje quem publica essa aresta é o AMCL, e ela deixa de ser mentira. Da **Aula 12** vem o mapa que vocês salvaram, o par `.pgm` + `.yaml`, que deixa de ser evidência de entrega e passa a ser **entrada**: é nele que o robô vai se achar. Da **Aula 9** vem a régua declarada antes de medir, senão ela se ajusta ao resultado. Da **Aula 13** vem a frase de que achar não é acertar — o maior IoU médio da tabela era do pior detector —, e hoje a mesma armadilha reaparece com outra roupa, que é a espinha da aula.

E das **Aulas 7 e 8** vem a peça que vocês não sabem que já têm: objetivo, feedback, resultado, cancelamento. **O Nav2 é um servidor de ação.** Quem entendeu aquelas duas aulas já sabe navegar, e só falta o nome do servidor.

## A ideia da aula em uma frase

**A nuvem concentrar prova confiança, não localização.** O gate de hoje pede um print do RViz2 com a nuvem de partículas concentrada — e esse print é exatamente o que **não** distingue um robô localizado de um robô 5,92 m fora do lugar, com o rumo invertido. Vamos medir a diferença antes de confiar na figura.

## A ordem de hoje, e o que cede se o tempo apertar

A aula está ordenada por **custo de perda**: o que vence antes vem primeiro.

| Bloco | O que você sai sabendo | Vence em |
|---|---|---|
| 1. A nuvem medida, sem ROS 2 | por que "concentrou" não é "achou", com número | — |
| 2. O Nav2 no ar, e a pose inicial | o Nav2 sobe com o seu mapa e o AMCL converge | **30/10** |
| 3. Um goal, e depois a rota | o robô vai sozinho até um objetivo, e depois até cinco | 04/11 e 09/11 |
| 4. O TP4, item por item | onde ter atenção nos quatro itens | 21/11 |

Se o tempo apertar, **o bloco que cede é o 4** — ele está escrito nesta página inteira, item por item, e dá para ler em casa. O que não cede é o bloco 2: ele vence na sexta.

## Instalar o Nav2 — antes de qualquer coisa

São uns 200 MB e dois minutos. Faça isso **agora**, no começo da aula, porque o resto do dia depende dele.

```bash
sudo apt update
sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup

# o bloco 1 roda sem ROS 2, mas precisa destes dois (o segundo so' para a figura)
sudo apt install -y python3-numpy python3-opencv

# conferir — as três linhas têm de responder
ros2 pkg list | grep -c '^nav2_'            # 20 ou mais
ros2 pkg executables nav2_amcl              # nav2_amcl amcl
ros2 pkg executables nav2_bt_navigator      # nav2_bt_navigator bt_navigator
```

!!! danger "Nav2 vem do apt, e da versão do Humble — isto não é preferência"
    `ros-humble-navigation2` é o Nav2 **construído e testado contra o Humble**. Não compile o Nav2 da fonte do `main` e não instale nada do Nav2 por pip: você vai arrastar uma versão cujos nomes de parâmetro mudaram, e **o sintoma não vai dizer que foi versão**. O que aparece é o gerenciador de ciclo de vida parado em `Configuring`, calado, para sempre.

    É a mesma regra do semestre, na terceira vez: **Humble pareia com Gazebo Fortress** (`ros-humble-ros-gz`, binário `ign gazebo`), o `cv_bridge` do apt pareia com **NumPy 1.x e OpenCV 4.5.4**, e o Nav2 pareia com o Humble. Diante de um erro que não faz sentido, a primeira pergunta é **"o que mudou de versão aqui?"**.

Os dois pacotes entram por motivos diferentes. O metapacote `navigation2` traz os servidores **e** o `nav2_rviz_plugins`, de onde vem o display da **nuvem de partículas** — a figura que o gate pede. Sem ele, o display não existe na lista do RViz2 e parece que o AMCL não está publicando. O `nav2_bringup` traz os launches e os YAMLs de referência, que são a fonte contra a qual este material foi escrito.

!!! tip "A nuvem só existe depois da pose inicial"
    No código do AMCL do Humble, a publicação da nuvem começa com `if (!initial_pose_is_known_) return;`. Antes do seu *2D Pose Estimate* o tópico `/particle_cloud` **não tem mensagem nenhuma** — não é display errado, não é QoS, não é o RViz2: é o AMCL esperando você.

## Preparar o terminal e pegar o material

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
mkdir -p "$PB_WS/src"

cd /tmp && rm -rf pb-a15 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a15

# o `test -d` nao e enfeite: sem ele, um clone que falha deixa o rm -rf rodar
# assim mesmo, e voce fica sem a versao nova E sem a antiga. Shell interativo
# nao tem `set -e`: linha que falha nao interrompe as de baixo.
#
# e o rm -rf tem de vir antes do cp -r: cp -r sobre pasta existente ANINHA
# (src/x/x), e o colcon passa a compilar a versao velha sem dizer nada
test -d pb-a15 && \
  rm -rf "$PB_DIR/aula15-nav2" "$PB_WS/src/aula15_nav2" "$PB_WS/src/aula11_mundo" && \
  cp -r pb-a15/exemplos/aula15-nav2 "$PB_DIR/" && \
  cp -r pb-a15/exemplos/aula15-nav2/aula15_nav2 "$PB_WS/src/" && \
  cp -r pb-a15/exemplos/aula11-mundo/aula11_mundo "$PB_WS/src/"
cd "$PB_WS" && colcon build --symlink-install \
  --packages-select aula11_mundo aula15_nav2
source install/setup.bash
```

!!! warning "O `aula11_mundo` é recopiado hoje, e é obrigatório"
    O mundo da Aula 11 mudou nesta semana, por causa desta aula, e ganhou **dois argumentos novos**:

    - `piloto:=false` — para o piloto reativo não disputar o `/cmd_vel` com o Nav2;
    - `laser_x:=0.10` — o mesmo número alimenta a medição do `/scan` e a transformada `base_footprint → laser_frame`. Antes, o feixe era medido no **centro** do robô e publicado num quadro 10 cm à frente: um viés sistemático que nenhum nó reclamava.

    Se você não recopiar, o Nav2 sobe com o piloto brigando pelo volante, e o sintoma é **robô andando truncado**, sem erro nenhum. Confira qual versão está instalada:

    ```bash
    ros2 launch aula11_mundo mundo.launch.py --show-args    # tem de listar `piloto` e `laser_x`
    ```

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Abriu um terminal novo? Elas se perderam — e sem essa linha, `cd "$PB_DIR"` viraria `cd /`, que não falha dizendo o que faltou.

    Num terminal novo, três coisas se perdem juntas, e só a primeira avisa:

    ```bash
    export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
    export PB_DIR="$HOME/projeto-pb-$PB_USER" && export PB_WS="$PB_DIR/ros2_ws"
    source /opt/ros/humble/setup.bash
    source "$PB_WS/install/setup.bash"
    ```

---

## Bloco 1 — A nuvem que concentrou no lugar errado

Isto roda **sem ROS 2 e sem Nav2**: é um filtro de partículas honesto em NumPy, sobre o mapa da Aula 11 — que serve ao mesmo tempo de mapa conhecido e de **verdade**. É por isso que ele pode medir o que o RViz2 não mostra.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 simular_loc.py          # os três cenários
python3 avaliar_loc.py          # a tabela comparada
```

```
cenario     t conv (s) erro pos (m) erro ang (g)  nuvem (m)  nuvem (g)  N ef min  convergiu para
-------     ---------- ------------ ------------  ---------  ---------  --------  --------------
uniforme           3.0         0.02          0.4      0.066        1.7      11.8  lugar certo
aproximada         0.6         0.02          0.5      0.063        1.6      63.0  lugar certo
errada             0.6         5.92        179.7      0.078        2.2     114.5  lugar ERRADO
```

**Leia a coluna da nuvem e a coluna do erro juntas.** Os três cenários terminam com a nuvem entre **6,3 e 7,8 cm** de raio. Nos três, um print do RViz2 mostraria a mesma coisa: uma manchinha concentrada, status `Ok`, nenhum aviso. E um deles está a **5,92 m** da verdade, com o rumo **180° invertido**.

O cenário `errada` é o aluno clicando o *2D Pose Estimate* na sala vizinha. O filtro não levanta exceção, não emite aviso, converge **mais rápido** que os outros dois — e a nuvem dele é a **mais concentrada da tabela**.

!!! quote "A frase da aula"
    **Concordância interna não é evidência.** Olhe o `N ef min`: no cenário `uniforme` o número efetivo de partículas despenca para **11,8** de 1200 — o filtro passa por uma crise, as hipóteses competem, quase todas morrem. No cenário `errada` ele nunca desce de **114,5**: o filtro **nunca teve dúvida**, porque todas as partículas estão igualmente erradas.

    É a Aula 13 de novo: o maior IoU médio era do pior detector. Qualquer métrica que mede **o que o algoritmo acha de si mesmo** se engana da mesma maneira. A cura também é a mesma: medir contra a verdade.

E a figura, que vai ao relatório ao lado do print do RViz2:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 avaliar_loc.py --imagem nuvem.png
python3 avaliar_loc.py --imagem colapso.png --momentos 6 --segundos 20
```

Na linha `errada`, o círculo da verdade e a cruz da estimativa caem em **salas diferentes**, e a nuvem em volta da cruz é do tamanho de uma moeda. **O número diz quanto; a figura diz onde.**

### O mapa simétrico, e por que o gate pede o clique

O mundo da Aula 11 é **quase simétrico por rotação de 180°** em torno de (6, 4) — ninguém projetou isso, e é a melhor aula do exemplo. Com poucas partículas e pouco percurso, a localização global trava na sala gêmea:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 avaliar_loc.py uniforme --particulas 400 --segundos 20
```

```
uniforme           8.4         8.48        178.1      0.223       11.8      13.5  lugar ERRADO
```

Não é bug: é o que a simetria do mapa faz com um filtro sem informação a priori. **É exatamente por isso que o `set_initial_pose` existe no AMCL, e por que o gate pede o clique no 2D Pose Estimate.** Se o cenário do seu TP3 tem corredores iguais, salas espelhadas ou um hall vazio, espere o mesmo — e a resposta não é mais partículas, é dar a pose inicial.

A [página do exemplo](../../exemplos/aula15-nav2/index.md) tem a tabela que liga **cada peça do filtro ao parâmetro correspondente do AMCL** — `alpha1..alpha5`, `max_beams`, `update_min_d`, `sigma_hit`, `z_rand`, `recovery_alpha_slow`. Quando o AMCL do seu projeto se comportar mal, é essa tabela que diz qual linha do YAML mexer, e o que esperar.

---

## Bloco 2 — O Nav2 no ar, e o gesto que decide

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula15_nav2 nav2.launch.py --show-args      # SEMPRE antes
ros2 launch aula15_nav2 nav2.launch.py rviz:=true
```

!!! danger "Este pacote subiu pela primeira vez na véspera — e achou um defeito"
    O `aula15_nav2` foi escrito contra a **fonte do Nav2 do Humble**: cada nome de nó, executável, parâmetro e plugin foi lido no repositório, e o `config/nav2.yaml` marca com `(oficial: X)` toda linha em que ele divergiu do `nav2_params.yaml` de referência. Mas ele foi escrito **sem ROS 2 na máquina**, e a primeira execução foi na noite de 26/10.

    Ela encontrou um defeito, e ele está contado abaixo porque é bom demais para jogar fora: o sistema subiu inteiro, fez exatamente o que foi mandado fazer, e **o RViz2 não abriu** — sem uma única mensagem de erro.

    O [README do pacote](../../exemplos/aula15-nav2/aula15_nav2/README-pacote.md) tem a lista do que foi e do que não foi verificado, atualizada depois dessa execução.

### O primeiro defeito deste pacote, achado na véspera

O comando era este, e a saída tinha **catorze** processos — o mundo da Aula 11 com os seus dois nós auxiliares (a TF estática do laser e o `robot_state_publisher`), o `map_server`, o `amcl`, os sete do Nav2 e os dois gerenciadores de ciclo de vida. **Nenhum deles era o `rviz2`:**

```bash
ros2 launch aula15_nav2 nav2.launch.py rviz:=true     # e o RViz2 nao abre
```

A causa está na biblioteca `launch`, não no Nav2: **`launch_arguments` de um `IncludeLaunchDescription` não são escopadas.** O include devolve um `SetLaunchConfiguration` por argumento, **no escopo de quem inclui**, e esse `Set` grava sem olhar o que já estava lá. Como este launch inclui o mundo da Aula 11 passando `'rviz': 'false'`, esse `false` **apagava o `rviz:=true` que você digitou** — e o nó do RViz2, avaliado depois, não subia.

E aí vem a cascata que você veria no terminal, toda ela consequência de um RViz2 que não abriu:

```
[amcl] AMCL cannot publish a pose or update the transform. Please set the initial pose...
[global_costmap] Timed out waiting for transform from base_footprint to map ...
                 Invalid frame ID "map" ... frame does not exist
```

Sem RViz2 não há como clicar o *2D Pose Estimate*; sem pose inicial o AMCL não publica `map → odom`; sem essa aresta **o quadro `map` não existe**, e o `planner_server` espera por ele para sempre. Três mensagens, nenhuma falando de argumento de launch.

!!! quote "Por que este defeito vale uma seção da página"
    Ele é a tese da disciplina em forma de bug: **o sistema fez exatamente o que foi mandado fazer, e ninguém mandou o que queria.** A correção tem duas camadas, e as duas foram exercitadas com a própria biblioteca `launch` do Humble, cada uma sozinha:

    1. o include vai dentro de um `GroupAction([...])`, que é `scoped=True` por padrão;
    2. o nó do RViz2 passa a depender de `rviz_nav2`, um nome que o launch incluído não conhece.

    E, pela regra da casa, **erro que reincide não se corrige relendo com mais cuidado**: nasceu o `tools/conferir-launch.py`, que percorre os `*.launch.py` do repositório e falha quando um include fixa, em constante, um argumento que o próprio arquivo declara. Ele achou o mesmo defeito no `aula12_slam` — cujo `rviz` tinha padrão `true`, ou seja, **o RViz2 daquela aula nunca subiu para ninguém**, e isso passou despercebido por três semanas.

**O `--show-args` primeiro, sempre.** `ros2 launch` aceita argumento desconhecido **calado** — `rviz:=true` num pacote que não declara `rviz` simplesmente não faz nada, e você fica procurando defeito no RViz2. Se a lista não trouxer `mapa`, `rviz`, `pose_inicial_auto` e `deriva`, o pacote compilado é outro (quase sempre o `cp -r` aninhado).

### As peças, e por que elas sobem em duas levas

| Ordem | Quem sobe | Papel |
|---|---|---|
| 1 | `mundo` (Aula 11), com `map_odom:=false` e `piloto:=false` | o simulador: `/scan`, `/odom`, `odom → base_footprint` |
| 2 | `map_server` | lê o `.yaml` do mapa e publica `/map` |
| 3 | `amcl` | **publica `map → odom`** — a aresta que na Aula 11 era mentira |
| 4 | `lifecycle_manager_localization` | ativa 2 e 3, nesta ordem |
| 5 | `controller_server` (DWB), `smoother_server`, `planner_server` (NavFn), `behavior_server`, `bt_navigator`, `waypoint_follower`, `velocity_smoother` | o Nav2 propriamente dito |
| 6 | `lifecycle_manager_navigation` | ativa os sete acima **nesta ordem** — é a ordem da lista `NOS_NAVEGACAO`, no launch |

**Nav2 é software de ciclo de vida.** Nenhum desses nós funciona só porque o processo está no ar: ele precisa ser configurado e ativado, e quem faz isso é o gerenciador. A consequência prática é o modo de falha mais caro do TP4:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 lifecycle get /amcl              # tem de dizer: active [3]
ros2 lifecycle get /bt_navigator      # idem
ros2 node list                        # quem está no ar
```

Se um nome na lista do gerenciador não corresponder a um nó realmente no ar, ele **fica esperando para sempre** — sem erro, sem aviso, parado em `Configuring`. É o jeito número um de perder uma hora.

### A cadeia do `/cmd_vel`, que é onde todo mundo tropeça

```
controller_server  publica cmd_vel  ── remapeado para ──►  /cmd_vel_nav
velocity_smoother  ouve /cmd_vel_nav  ── publica ──►  /cmd_vel
no `mundo`         ouve /cmd_vel
```

Os dois remapeamentos são os **mesmos do `navigation_launch.py` oficial**. Se você tirar o `velocity_smoother` sem desfazê-los, o `controller_server` fica falando em `/cmd_vel_nav`, ninguém ouve, **o robô não anda e nenhum nó reclama**.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 topic info /cmd_vel --verbose        # UM publicador: velocity_smoother
ros2 topic hz /cmd_vel_nav                # com goal ativo, tem de ter tráfego
```

**Dois publicadores em `/cmd_vel` não dão erro** — dão um robô que obedece ao último que falou. É a mesma família do defeito de `map → odom` da Aula 12, uma camada acima. Se aparecerem dois, o `piloto:=false` não chegou.

### O 2D Pose Estimate: o gesto mais importante da aula

O launch sobe com a pose inicial **manual**, de propósito. O AMCL espera, e quem dá a pose é você, com o botão **2D Pose Estimate** do RViz2: clique na posição e arraste na direção do rumo.

Faça esse gesto **com a mão, pelo menos uma vez**, olhando a nuvem: ela nasce onde você clicou e você vê ela fechar — ou não. Depois disso, para repetir um teste sem reclicar:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula15_nav2 nav2.launch.py rviz:=true pose_inicial_auto:=true
```

E para ver a convergência pelo lado dos números, não da figura:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 topic echo /amcl_pose --once         # a pose E a covariância
ros2 run tf2_ros tf2_echo map odom        # a correção que o AMCL está aplicando
```

!!! tip "A covariância do `/amcl_pose` é a sua nuvem, em número"
    O print mostra a nuvem; o `/amcl_pose` traz a **covariância** da mesma estimativa. É o número que o bloco 1 chama de "raio da nuvem" — e, como o bloco 1 mostrou, ele mede confiança, não acerto. Cite os dois no relatório: *"a nuvem fechou com covariância X, e eu confirmei a pose contra Y"* vale mais que qualquer figura.

    O `tf2_echo map odom` é o outro número honesto: ele é **o erro acumulado da odometria com o sinal trocado**. Com a deriva de 3% da Aula 11, essa translação cresce ao longo do laço — e é literalmente a conta que o AMCL está pagando.

### O que entra no relatório como evidência da localização

Print do RViz2 com a nuvem concentrada, **mais** uma frase dizendo como você sabe que ela concentrou no lugar certo. A frase é o que separa o item entregue do item bem feito, e ela não precisa ser sofisticada: *"a estimativa coincide com a parede que o robô estava encostando"*, ou *"o laser ficou alinhado com o mapa, sem deslizar"*, já é argumento.

---

## Bloco 3 — Um goal, e depois a rota

!!! warning "Daqui para frente, nada foi visto funcionando"
    O ensaio da véspera parou na localização: o launch sobe, o `map_server` lê o mapa, o AMCL ativa. **Nenhum goal foi enviado até agora** — o NavFn nunca planejou uma rota com este YAML, o DWB nunca atravessou a porta de 1,2 m e o `rota.py` nunca enviou um objetivo. A primeira execução é em sala, junto. Quem conseguir primeiro, diga em voz alta: vale para a turma.

O jeito mais rápido de mandar o primeiro objetivo é o **2D Goal Pose** do RViz2: clique, arraste o rumo, solte. Ele publica em `/goal_pose`, que o `bt_navigator` assina. O que **deve** aparecer é o plano global (NavFn) desenhado até o alvo, e o robô começando a andar, corrigindo com o costmap local (DWB).

Depois disso, o objetivo vira **código** — e aqui vocês já sabem fazer:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 action list | grep navigate                  # navigate_to_pose está aí
ros2 run aula15_nav2 rota                         # a rota padrão, uma volta
ros2 run aula15_nav2 rota --ros-args -p voltas:=0 # patrulha sem fim
```

**O Nav2 é um servidor de ação.** `navigate_to_pose` tem objetivo, feedback, resultado e cancelamento — os quatro motivos pelos quais ação existe, e o conteúdo das Aulas 7 e 8. O `rota.py` tem 227 linhas, das quais quase metade é comentário, e é o item 1 do TP4 inteiro.

Três coisas nele que valem ler antes de copiar para o seu projeto:

| O que está escrito | Por que |
|---|---|
| `header.frame_id = 'map'` | o objetivo é um lugar **no mapa**. O mesmo goal em `base_link` pede "ande 2 m para a frente e 4 m para a esquerda" — e o Nav2 obedece, sem reclamar |
| `status == GoalStatus.STATUS_SUCCEEDED` | no Humble o `result` do `navigate_to_pose` é um `std_msgs/Empty`: **não existe código de erro para ler**. Quem escrever `resultado.result.error_code` escreveu código de uma versão posterior |
| `spin_until_future_complete` no `main` | bloquear é intencional, e só é legítimo **fora** de callback. Dentro de um callback, o executor esperaria por si mesmo: nada acontece e nada reclama — o mesmo cuidado da Aula 8 |

E o campo que resolve metade do item 2 do TP4, de graça: o goal do `navigate_to_pose` tem um campo **`behavior_tree`** (string). Vazio, usa a árvore padrão; preenchido com o caminho de um XML, o `bt_navigator` usa **a sua árvore** naquele objetivo. No `rota.py` isso é o parâmetro `arvore:=`:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 run aula15_nav2 rota --ros-args -p arvore:=/caminho/da/sua_arvore.xml
```

### O desvio reativo que o item 1 pede

O enunciado fecha o item 1 com *"incluindo desvio reativo de obstáculos"*. No Nav2 isso não é um nó novo: é o **costmap local** alimentado pelo `/scan` e o **DWB** avaliando trajetórias contra ele a cada ciclo.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 param get /controller_server FollowPath.max_vel_x
ros2 param get /local_costmap/local_costmap inflation_layer.inflation_radius
```

Os dois costmaps que o item 1 manda configurar — e que o **gate G4.2** manda *explicar* — dividem o trabalho assim: o **global** é o mapa inteiro com a inflação, e é sobre ele que o NavFn planeja; o **local** é uma janela rolante de poucos metros, reconstruída a partir do laser, e é sobre ela que o DWB decide a próxima velocidade. Quem explicar essa divisão de trabalho com os números do seu YAML (tamanho da janela, resolução, raio de inflação) entrega o item **bem feito** em dois parágrafos.

!!! warning "A aritmética da porta, que vale para o seu cenário também"
    A porta do mundo tem 1,2 m e o robô tem 0,40 m de diâmetro. **São duas contas diferentes, e confundi-las é o erro.**

    A primeira é a que bloqueia: células a menos de `robot_radius` (0,20 m) de uma parede são **intransponíveis** — o planejador trata o robô como ponto, e esse raio já está embutido. Sobram `1,2 − 2 × 0,20 = 0,8 m` de passagem.

    A segunda é a que **encarece**: o `inflation_radius` (0,35 m) põe custo crescente em volta das paredes. Sobram `1,2 − 2 × 0,35 = 0,5 m` de corredor com custo **zero** no meio da porta — espaço confortável para o NavFn mirar.

    Suba a inflação para o valor oficial, 0,55 m, e a porta **não fecha**: sobram 0,1 m de custo zero, e o plano passa raspando ou escolhe outro caminho. Quem esperar `No valid path could be found` por causa da inflação procura no lugar errado — esse erro vem da primeira conta, não da segunda. **Nada disto foi observado**; faça a conta com a passagem mais estreita do seu mapa e depois confira na tela.

---

## O TP4, item por item — onde ter atenção

O TP4 vence em **21/11, até 12h**, e começa agora: o primeiro gate é **30/10**, nesta sexta. A tabela completa com datas e evidências está em [Gates de cada TP](../../recursos/gates-tps.md); aqui está o que cada item cobra e **onde ele costuma quebrar**.

| Item | O verbo que pega | O que prova no repositório |
|---|---|---|
| 1. Nav2 + nó de rota | **enviando goals sequenciais** | `launch/` + o nó + print dos costmaps + vídeo de 20 s |
| 2. Árvore de comportamento + bag | **interrompa**, **aguarde**, **retome** · **reproduzível** | XML da árvore + `bags/` + gráfico da trajetória |
| 3. Percepção veicular no MetaDrive | **sobreponha** ao frame | scripts + prints das três etapas |
| 4. CNN com e sem augmentation | **compare** as curvas | notebook executado + curvas + matriz de confusão |

### Item 1 — Nav2, costmaps, AMCL, planejador e a rota

**O que você já tem depois de hoje:** o sistema subindo e se localizando, mais o molde do YAML. O `nav2.yaml` deste pacote é o `nav2_params.yaml` oficial com **cinco decisões** marcadas `# TROQUE`, espalhadas por umas trinta linhas — são as que dependem do seu robô, do seu sensor e do seu simulador:

| | O que é | Onde aparece |
|---|---|---|
| **TROQUE 1** | `base_frame_id` / `robot_base_frame` — o quadro da base do **seu** URDF | 5 lugares |
| **TROQUE 2** | o tópico do laser (`scan_topic`, `topic:`) | 3 lugares |
| **TROQUE 3** | as velocidades máximas, casadas com o seu robô | 6 lugares |
| **TROQUE 4** | `robot_radius` — o raio do **seu** robô | 2 lugares (os dois costmaps) |
| **TROQUE 5** | `use_sim_time` | **13 lugares** |

!!! danger "O `use_sim_time` é o mais caro dos cinco, e o enunciado diz \"em Gazebo\""
    O YAML deste pacote está com `use_sim_time: false` nos treze nós porque o mundo da Aula 11 **não publica `/clock`**. Se o seu item 1 entrar com Gazebo de verdade, os treze viram `true` — **todos ao mesmo tempo**.

    Metade `true` e metade `false` é o defeito mais difícil de achar da etapa: os nós ficam `active`, ninguém reclama, e o sistema simplesmente não processa nada. E repare que o `use_sim_time` vai pelo YAML **e** pelos gerenciadores de ciclo de vida, que o recebem fora do arquivo.

E o mapa **não** se troca no YAML: o `yaml_filename` fica vazio de propósito, porque quem o preenche é o argumento `mapa:=` do launch. Caminho escrito ali é ignorado, sem aviso.

**Onde ele quebra:**

- **O mapa.** O enunciado diz "em Gazebo". A decisão da disciplina é a mesma do TP3: **Gazebo é o Fortress** (`ros-humble-ros-gz`, `ign gazebo`), e **o mundo mínimo da Aula 11 é aceito** desde que você diga isso no relatório, em uma frase. O que o item cobra é o sistema navegando com o **seu** mapa — e o mundo mínimo é um mundo. Não troque de simulador a três semanas da entrega: trocar versão às vésperas derruba o que funciona.
- **O `robot_radius` e o `inflation_radius`.** Se o robô do seu URDF tem outro tamanho, as duas mudam — e fazem coisas diferentes: o `robot_radius` decide se a passagem **abre ou fecha**, o `inflation_radius` decide o quanto ela **custa**. Faça as duas contas com a passagem mais estreita do seu mapa.
- **A pose inicial.** Metade dos "o Nav2 não navega" é AMCL sem pose inicial: o `bt_navigator` fica esperando a TF `map → odom` que ninguém publica. O bloco 2 desta página tem os três comandos que separam esse caso dos outros.
- **A rota.** Ponto em célula ocupada, ou a menos de `robot_radius` de uma parede, é **goal recusado** — não goal que falhou: o servidor nem tenta. Escolha os pontos olhando o costmap global no RViz2, não o mapa cru.

### Item 2 — A árvore de comportamento, e a gravação

São **duas entregas** no mesmo item, e a segunda é a que some: a árvore **e** a sessão gravada e reproduzível.

**A árvore.** O `bt_navigator` executa um XML, e os prontos estão em `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/`. Comece de `navigate_to_pose_w_replanning_and_recovery.xml`, copie para o **seu** pacote, e aponte para ele — pelo parâmetro `default_nav_through_poses_bt_xml` / `default_nav_to_pose_bt_xml` do `bt_navigator`, ou pelo campo `behavior_tree` do goal, que o `rota.py` já sabe preencher.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ls /opt/ros/humble/share/nav2_bt_navigator/behavior_trees/
ros2 param get /bt_navigator default_nav_to_pose_bt_xml     # com o Nav2 no ar
```

O comportamento pedido — *interromper abaixo de 0,5 m, aguardar 2 s, retomar o objetivo* — tem **dois caminhos defensáveis**, e o que não é defensável é não dizer qual você usou:

- **O caminho completo:** um nó de condição próprio (plugin C++ do `nav2_behavior_tree`) que lê o `/scan` e devolve `FAILURE` quando a distância mínima cai abaixo de 0,5 m, composto na árvore com o `Wait` de 2 s dentro de um `ReactiveFallback`. É o caminho que o enunciado descreve ao pé da letra, e é o mais caro: plugin novo, `CMakeLists`, registro do nó.
- **O caminho de cliente:** a árvore é a padrão (ou uma sua, com nós prontos), e a interrupção vive no **seu nó Python**: ele monitora o `/scan`, cancela o goal quando o obstáculo entra em 0,5 m, espera 2 s e reenvia o mesmo objetivo. Você já tem o cancelamento — é a Aula 8.

Nos dois casos o relatório tem de dizer **onde a decisão mora** e mostrar o comportamento acontecendo. Traga a sua escolha para a aula de 03/11; é o assunto do dia.

**A gravação.** O item pede gravar a sessão e **reproduzi-la offline** — "dá para rodar a análise com o robô desligado" é o critério:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/bags" && cd "$PB_DIR/bags"
ros2 bag record -o sessao-tp4 \
  /amcl_pose /odom /scan /cmd_vel /plan /tf /tf_static
# depois, com TUDO desligado:
ros2 bag info sessao-tp4
ros2 bag play sessao-tp4
```

!!! danger "Grave o `/tf_static`, ou a reprodução não serve para nada"
    O `/tf_static` é publicado **uma vez**, com QoS `transient local`, no instante em que o sistema sobe. Se ele não estiver na lista do `record`, a reprodução não tem as transformadas fixas do robô, e o que você vê é um laser flutuando sem corpo. É o erro mais comum do item, e ele só aparece **depois**, quando não há como regravar a sessão.

    Liste os tópicos explicitamente, como acima, em vez de `-a`: `-a` grava tudo, inclusive imagem, e um bag de 2 GB não vai para o Git nem para link.

    Mas leia o enunciado com cuidado: ele diz **"grave a sessão inteira"**. A lista acima é o mínimo para reproduzir a trajetória; se a sua análise offline precisa de `/particle_cloud`, `/local_plan`, `/behavior_tree_log` ou dos tópicos de visão do seu projeto, eles entram. A regra é essa: **grave tudo o que a sua análise precisa reproduzir, e diga no relatório o que você excluiu e por quê.** Se a sua versão do `ros2 bag record` aceitar `--exclude` (confira com `ros2 bag record --help`), `-a` menos as imagens é o melhor dos dois mundos.

**O gráfico da trajetória** é o que fecha o item, e o caminho garantido usa o que vocês já sabem: com o bag rodando (`ros2 bag play`), um nó seu assina `/amcl_pose` e escreve um CSV; o gráfico sai do CSV com matplotlib, sem ROS 2. Existe o caminho direto — ler o bag em Python com o `rosbag2_py` — e ele é mais elegante, mas **eu não o exercitei**: se for por ali, teste antes de depender dele na véspera.

Plote **duas** curvas no mesmo eixo: a do `/odom` e a do `/amcl_pose`. A distância entre elas é a deriva que o AMCL corrigiu, e é o gráfico mais eloquente que este TP permite — a Aula 11 inteira numa figura.

### Item 3 — MetaDrive: faixas e formas geométricas

O pipeline é **o mesmo da Aula 13**: máscara HSV, Canny, `HoughLinesP`, sobreposto ao frame. O que muda é a fonte da imagem — e é aí que está o trabalho.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/percepcao-veicular" && cd "$PB_DIR/percepcao-veicular"
uv venv --system-site-packages .venv-metadrive
uv pip install --python .venv-metadrive/bin/python "metadrive-simulator==0.4.3"

# a conferencia e do proprio pacote -- rode fora de pasta que tenha subpasta "metadrive"
.venv-metadrive/bin/python -m metadrive.pull_asset
.venv-metadrive/bin/python -m metadrive.examples.profile_metadrive
.venv-metadrive/bin/python -m metadrive.examples.verify_headless_installation --camera rgb
```

!!! warning "O que eu sei e o que eu não sei sobre o MetaDrive"
    A versão **0.4.3** é a última publicada no PyPI (dezembro de 2024) e aceita Python de 3.6 a 3.11 — o 3.10 do Ubuntu 22.04 está dentro. A documentação afirma que a versão atual **já suporta renderização sem tela**, e o `verify_headless_installation` existe para provar isso na sua máquina.

    **Eu não rodei o MetaDrive em máquina minha.** Os comandos acima são os da documentação oficial, não de uma execução minha. Quem rodar primeiro, diga em sala: isso vale para a turma inteira.

    Duas armadilhas documentadas: o `python -m metadrive...` **falha se o diretório atual tiver uma subpasta chamada `metadrive`**, e a documentação recomenda o clone em vez do PyPI. As duas se cruzam: se você for pelo plano B, clone **fora** da sua pasta de trabalho (`git clone ... "$PB_DIR/metadrive-fonte"`) e instale com `uv pip install --python .venv-metadrive/bin/python -e "$PB_DIR/metadrive-fonte"` — senão o `python -m` passa a falhar de dentro da pasta que você acabou de criar. É por isso que a pasta de trabalho acima **não** se chama `metadrive`.

**O ponto de atenção que vale mais que a instalação:** os itens 3 e 4 pedem **frames salvos em disco**, não um pipeline acoplado ao simulador. Grave as imagens uma vez, trabalhe sobre os arquivos, e o resto do TP não depende mais do MetaDrive subir. Quem acoplar o OpenCV ao laço do simulador vai depurar duas coisas ao mesmo tempo.

Se o MetaDrive não subir na sua máquina, existe **saída declarada**: o `cena_estrada.py` do exemplo [`aula13-veicular`](../../exemplos/aula13-veicular/index.md) gera cenas de estrada sintéticas em cinco condições, e o pipeline é o mesmo. Vale o item com um parágrafo dizendo o que você usou e por quê — e, aí, a discussão de falhas sai de graça, porque aquele exemplo já mede: faixa apagada derruba a detecção por cor a **0%**, e à noite o Canny devolve **zero** pixels de borda.

**As formas geométricas** (`cv2.HoughCircles` e `cv2.cornerHarris`) são a parte que mais gera texto vazio. Três conselhos concretos:

- **Confira o que existe na cena antes de prometer placa.** Se não houver placa no cenário, o item se cumpre sobre o que há — cones, veículos, a boca do cruzamento — e você **diz isso**. Detector que não tem o que detectar devolve zero, e zero com explicação é resultado; zero sem explicação é item faltando.
- **`HoughCircles` é o algoritmo mais sensível a parâmetro de todo o OpenCV.** `param2` alto demais: nenhum círculo. Baixo demais: círculos em todo lugar. Registre a faixa que você testou — é o "com discussão de falhas" que o **gate G4.5** cobra.
- **Harris devolve um mapa de resposta, não cantos.** Ele precisa de limiar e de supressão de vizinhança; quem plotar o mapa cru entrega uma imagem vermelha inteira.

### Item 4 — A CNN, com e sem augmentation

A exigência que decide o item não é a rede: é a **comparação**. Duas rodadas, mesma arquitetura, mesmas épocas — uma com augmentation e uma sem — e as curvas de acurácia e perda **no mesmo gráfico**.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/cnn" && cd "$PB_DIR/cnn"
uv venv .venv-cnn                 # SEM --system-site-packages: veja o aviso abaixo
uv pip install --python .venv-cnn/bin/python \
  tensorflow-cpu opencv-python-headless matplotlib scikit-learn
uv pip list --python .venv-cnn/bin/python | grep -i tensorflow   # anote a versao
```

**A versão que vier, anote no relatório.** É a regra de alinhamento do semestre aplicada ao seu caso: resultado de treino sem versão de framework declarada não é reprodutível.

!!! danger "Este é o único venv do semestre SEM `--system-site-packages`"
    A regra da disciplina é `uv venv --system-site-packages`, e ela existe para o ambiente continuar enxergando o `rclpy` e o `PyQt5` do sistema. **Aqui ela se inverte**, e vale entender por quê: o TensorFlow instala o NumPy dele *dentro* do venv, que tem precedência; com `--system-site-packages`, o `python3-opencv` do apt — compilado contra o NumPy 1.x — fica visível ao lado dele, e o primeiro `import cv2` para carregar os frames devolve `_ARRAY_API not found`. É o erro da Aula 13, dentro do ambiente criado para evitá-lo.

    Como este script **nunca** é um nó ROS 2, ele não precisa ver o `rclpy`: ambiente fechado, com o OpenCV vindo de dentro (`opencv-python-headless`). **Treine fora do ROS 2**, salve o modelo, e — se algum dia quiser inferência dentro de um nó — carregue o modelo num processo separado.

**Onde o item quebra, em ordem de frequência:**

- **Os 500 frames rotulados.** Esta é a parte caríssima, e ninguém a estima certo. 500 imagens em 3 classes (`via livre`, `obstáculo`, `cruzamento`) precisam ser **vistas uma a uma** por você. Salve os frames com nome que já carregue o rótulo (`livre_0001.png`), ou escreva um rotulador de dez linhas que mostra a imagem e espera uma tecla. Comece isso na **primeira** semana, não na última.
- **Classes desbalanceadas.** Se 400 frames são `via livre`, a rede acerta 80% prevendo sempre `via livre` — e a acurácia parece ótima. **O gate G4.6 pede matriz de confusão** (o enunciado não pede), e é ela que mostra a coluna vazia. Mesma lição da Aula 9: acurácia agregada esconde o caso que importa — e repare que a rubrica cobra mais que o enunciado, sempre.
- **Augmentation que estraga o rótulo.** O enunciado pede rotação ±15°, zoom 0,2 e **espelhamento horizontal**. Pense no espelhamento antes de ligá-lo: num problema de faixa, espelhar troca o lado da pista. Se isso muda o significado da sua classe, diga no relatório — perceber isso vale mais do que o número final.
- **Comparar duas rodadas que não são comparáveis.** Mesma semente, mesma divisão treino/validação, mesmas épocas. Senão a comparação não mede augmentation, mede sorte.

O `BatchNormalization` e o `Dropout(0.5)` são pedidos explicitamente: ponha, e escreva uma frase sobre o que cada um faz com as curvas. Quem olhar as duas curvas de validação e souber apontar onde a sem-augmentation começa a decorar o treino entregou o item **muito bem feito**.

---

## A tarefa da semana

**O que fazer.** O Nav2 subindo no **seu** projeto, com o **seu** mapa do TP3, o AMCL convergindo, e o robô cumprindo uma rota de três pontos do seu cenário.

**O que usar.** O `aula15_nav2` como molde: copie `launch/nav2.launch.py`, `config/nav2.yaml` e `rviz/nav2.rviz` para o seu pacote e percorra as cinco decisões marcadas `# TROQUE` (a tabela está no bloco 4 desta página). O mapa entra pelo argumento `mapa:=`, não pelo YAML; a pose inicial, pelo RViz2 ou por `pose_inicial_auto:=true`. O `rota.py` entra com os seus pontos.

**Como adequar ao seu projeto.** Três perguntas, nesta ordem: o mapa é do seu cenário? O raio do robô é o do seu URDF? As passagens do seu mapa abrem com a sua inflação? A terceira é a que trava gente, e a conta está no bloco 3 desta página.

**Como saber que terminou.** Rode as cinco linhas abaixo; as cinco têm de responder o que está escrito ao lado:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 lifecycle get /amcl                  # active [3]
ros2 lifecycle get /bt_navigator          # active [3]
ros2 topic info /cmd_vel --verbose        # 1 publicador
ros2 run tf2_ros tf2_echo map odom        # NAO identidade: o AMCL está corrigindo
ros2 action list | grep navigate          # navigate_to_pose
```

E a evidência que a sexta cobra: o print do RViz2 com a nuvem concentrada em `docs/evidencias/tp4/amcl.png`, **commitado**, mais a frase que diz como você sabe que ela concentrou no lugar certo.

## Desafio — medir a ambiguidade do seu mapa

Opcional, para quem terminou a tarefa, e responde-se **medindo**.

O mundo da Aula 11 é quase simétrico, e por isso a localização global dele é cara ou coroa. **O seu mapa também tem uma simetria** — corredores iguais, salas espelhadas, um hall sem móveis. A pergunta é: quanto ela custa?

Duas frentes, qualquer uma serve:

1. **No simulador medido**, varra o número de partículas e ache o ponto de virada: `python3 avaliar_loc.py uniforme --particulas N --segundos 20` para N em 200, 400, 800, 1200, 2000. Em que N ele passa a achar o lugar certo de forma consistente? E se você mudar a semente?
2. **No seu Nav2 real**, dê de propósito uma pose inicial errada — no lugar simétrico do seu mapa — e observe. A nuvem fecha? Em quantos segundos? Com que covariância? Compare com a pose inicial certa. **Se as duas covariâncias forem parecidas, você reproduziu a tabela do bloco 1 no seu próprio projeto** — e isso é um parágrafo de relatório que quase ninguém escreve.

Traga o número. Vale para a arguição e para o relatório do TP4.

## Para a próxima aula — 03/11

**Árvore de comportamento e a sessão gravada** (item 2): o XML, onde mora a decisão de interromper, e o bag que reproduz com o robô desligado. Chegue com o Nav2 navegando no seu projeto e com a sua escolha de caminho para a interrupção — a aula é sobre a sua escolha, não sobre a minha.

E comece a salvar os frames do MetaDrive **nesta semana**. Os 500 rótulos do item 4 são a parte que não comprime.
