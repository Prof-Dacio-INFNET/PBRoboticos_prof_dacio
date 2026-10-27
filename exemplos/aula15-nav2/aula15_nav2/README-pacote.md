# `aula15_nav2` — o Nav2 sobre o mundo da Aula 11

Na Aula 12 o `slam_toolbox` **construía** o mapa e publicava `map → odom`. Aqui
o mapa já existe, e a aresta `map → odom` passa a ser publicada pelo **AMCL**:
mesma aresta, problema diferente — não é mais "que mapa é este?", é "onde eu
estou dentro dele?".

> ## Leia isto antes de qualquer coisa
>
> **Este pacote foi escrito numa máquina sem ROS 2** — sem `colcon build` e sem
> `ros2 launch`. A primeira execução foi na noite de **26/10**, e está relatada
> na seção **"O que foi e o que não foi verificado"**, no fim desta página:
> o que subiu, o que não subiu, e o defeito que ela encontrou. Leia essa seção
> antes de concluir que o erro é seu.

## O que o launch sobe

| # | Nó | Papel |
|---|---|---|
| 1 | `mundo` (Aula 11) | o simulador: `/scan`, `/odom`, `odom → base_footprint`. Sobe com `map_odom:=false` e `piloto:=false` |
| 2 | `map_server` | lê o `mapa.yaml` e publica `/map` |
| 3 | `amcl` | publica `map → odom`, calculado a partir do `/scan` |
| 4 | `lifecycle_manager_localization` | ativa os dois acima |
| 5 | `controller_server` (DWB), `smoother_server`, `planner_server` (NavFn), `behavior_server`, `waypoint_follower`, `velocity_smoother` | o Nav2 propriamente dito |
| 6 | `lifecycle_manager_navigation` | ativa os seis acima |
| 7 | `rviz2` | só com `rviz:=true` |

A árvore de TF que resulta:

```
map -> odom                     o AMCL, corrigindo a deriva
odom -> base_footprint          o nó `mundo` (com deriva, de propósito)
base_footprint -> laser_frame   transformada estática
base_footprint -> ...           o robot_state_publisher, com modelo:=true
```

A cadeia do `/cmd_vel`, que é a parte que mais confunde:

```
controller_server  publica cmd_vel, remapeado para /cmd_vel_nav
velocity_smoother  ouve /cmd_vel_nav, publica /cmd_vel
nó `mundo`         ouve /cmd_vel
```

Os dois remapeamentos são os mesmos do `navigation_launch.py` oficial do Humble.
Se você tirar o `velocity_smoother` sem desfazê-los, o `controller_server` fica
falando em `/cmd_vel_nav` e ninguém ouve: o robô não anda e nenhum nó reclama.

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

# Pacote ROS é por apt, nunca por pip. O navigation2 traz os servidores; o
# nav2-bringup traz os plugins de RViz2, inclusive o da nuvem de partículas.
sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup

mkdir -p "$PB_WS/src" && cd /tmp && rm -rf pb-a15 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a15 && \
  # a cópia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x),
  # e o colcon passa a compilar a versão velha sem dizer nada
  test -d \ && rm -rf "$PB_WS/src/aula15_nav2" "$PB_WS/src/aula11_mundo" && \
  cp -r pb-a15/exemplos/aula15-nav2/aula15_nav2 "$PB_WS/src/" && \
  cp -r pb-a15/exemplos/aula11-mundo/aula11_mundo "$PB_WS/src/" && \
  cd "$PB_WS" && colcon build --packages-select aula11_mundo aula15_nav2 && \
  source install/setup.bash
```

## Rodar

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula15_nav2 nav2.launch.py rviz:=true
```

Da primeira vez, **com o RViz2 aberto**, a sequência é esta — e não dá para
pular o passo 1:

1. **"2D Pose Estimate"** na barra de ferramentas. Clique na posição de largada
   do robô — `(2, 4)` neste mundo, a sala oeste — e **arraste** na direção em
   que ele aponta antes de soltar. A nuvem verde de partículas nasce aí.
2. Veja a nuvem se fechar enquanto o robô ainda está parado (às vezes basta um
   `/scan`; às vezes precisa de movimento).
3. **"2D Goal Pose"**. Clique um destino do outro lado da porta, na sala leste.
4. O caminho azul (`/plan`) aparece, o vermelho (`/local_plan`) sai do robô, e
   ele anda.

Outros argumentos — `--show-args` lista todos com descrição:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula15_nav2 nav2.launch.py --show-args
ros2 launch aula15_nav2 nav2.launch.py mapa:="$PB_DIR/maps/mapa.yaml"  # o SEU mapa
ros2 launch aula15_nav2 nav2.launch.py pose_inicial_auto:=true         # sem clicar
ros2 launch aula15_nav2 nav2.launch.py deriva:=6.0                     # erro maior
ros2 launch aula15_nav2 nav2.launch.py modelo:=false                   # sem o URDF
```

## A pose inicial é manual de propósito

O padrão é `pose_inicial_auto:=false`: o AMCL sobe **esperando**, e quem dá a
pose é você, com o mouse.

Isso é escolha pedagógica, não esquecimento. **Pose inicial errada é o erro
clássico do G4.0**, e o sintoma é cruel: o sistema todo sobe saudável, a nuvem
converge, o planejador planeja — e o robô dirige contra uma parede que, no mapa
dele, não existe. Vale fazer o gesto com a mão pelo menos uma vez, e vale
**errar de propósito** uma vez: clique a pose inicial na sala errada e veja o
que acontece. É o experimento mais útil desta aula.

Depois de ter feito o gesto, `pose_inicial_auto:=true` entrega a pose de largada
`(2,0 ; 4,0 ; 0,0)` direto pelo parâmetro `set_initial_pose` do AMCL — serve
para repetir um teste sem reclicar e para rodar em máquina sem tela.

## Como saber que o AMCL convergiu

Quatro sinais, do mais barato ao mais conclusivo:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 topic echo /amcl_pose --once          # a covariância da pose estimada
ros2 run tf2_ros tf2_echo map odom         # a correção que o AMCL está aplicando
ros2 topic echo /deriva                    # o erro que ela deveria estar corrigindo
```

1. **A nuvem.** No RViz2, as setas verdes encolhem de uma mancha larga para um
   tufo do tamanho do robô. Nuvem larga = incerteza alta; nuvem que não fecha =
   o robô ainda não viu o bastante, ou a pose inicial está errada.
2. **A covariância.** Em `/amcl_pose`, os elementos 0, 7 e 35 da `covariance`
   (x, y e yaw) caem e estabilizam. Décimos de m² é incerteza grande;
   centésimos é convergido.
3. **O laser contra o mapa.** Os pontos âmbar do `/scan` caem **em cima** das
   paredes do mapa. Laser deslocado de forma consistente é pose errada; laser
   tremendo é árvore de TF quebrada, não localização ruim.
4. **A conta fechando.** `tf2_echo map odom` é o erro acumulado da odometria com
   o sinal trocado, e `/deriva` é esse mesmo erro medido pelo simulador. Os dois
   números andam juntos — é a mesma comprovação da Aula 12, agora com AMCL em
   vez de SLAM.

**Nuvem colapsada não é prova de nada.** Um AMCL com `alpha1..alpha5` baixos
produz nuvem apertadíssima em cima da pose errada, com cara de perfeição. É por
isso que os `alpha` deste pacote ficaram no padrão generoso do Nav2, e o
comentário no YAML explica.

## As cinco linhas que você troca no seu projeto

Todo o resto do `config/nav2.yaml` é o `nav2_params.yaml` do Humble com os
valores ajustados a este mundo — e **cada divergência em relação ao oficial está
marcada no arquivo** com `(oficial: X)`, para você poder desfazer qualquer
escolha nossa em um minuto. O que você precisa acertar são estas cinco, marcadas
no YAML com `# TROQUE 1:` a `# TROQUE 5:`:

| # | Linha | Onde aparece | O que acontece se estiver errada |
|---|---|---|---|
| 1 | `base_frame_id` / `robot_base_frame`: `base_footprint` | `amcl`, `bt_navigator`, `behavior_server`, os dois costmaps (5 lugares) | o padrão do Nav2 é `base_link`. Com a raiz errada, tudo sobe limpo e nada localiza |
| 2 | `scan_topic` / `topic` da fonte de sensor: `scan` e `/scan` | `amcl`, `obstacle_layer` dos dois costmaps | costmap vazio: o DWB dirige achando tudo livre |
| 3 | velocidades máximas: `0.35 m/s` e `0.9 rad/s` | DWB (`max_vel_x`, `max_vel_theta`, `max_speed_xy`), `velocity_smoother`, `behavior_server` | alto demais, o robô entra na parede antes de vê-la; baixo demais, o progress checker declara travamento |
| 4 | `robot_radius`: `0.20` | os dois costmaps | grande demais, não passa na porta de 1,2 m; pequeno demais, raspa a parede |
| 5 | `use_sim_time`: `false` | **todos os 13 nós** do YAML | o mais caro de todos: com `true` e sem Gazebo, os nós sobem, ficam `ACTIVE` e **nunca processam nada**, sem um único erro na tela |

A quinta merece um parágrafo. O `nav2_params.yaml` oficial vem com
`use_sim_time: True` porque supõe Gazebo. Este mundo não tem Gazebo e ninguém
publica `/clock` — por isso aqui é `false` em todos os nós, inclusive nos dois
auxiliares do `bt_navigator` e dentro dos dois costmaps. **No TP4, se você
entrar com Gazebo, volta a ser `true` — e tem de ser `true` em todos os lugares
ao mesmo tempo.** Metade `true` e metade `false` é o defeito mais difícil de
achar desta etapa.

Na segunda rodada, quando o sistema já andar, vale olhar também `resolution`
(tem de ser igual à do seu mapa) e `inflation_radius` (a conta da porta está
comentada no YAML).

## O mapa embutido

```
maps/mapa.pgm      240 x 160 células, 0,05 m — PGM binário P5
maps/mapa.yaml     resolution 0.05, origin [0, 0, 0], negate 0
maps/gerar_mapa.py o script que gerou os dois, a partir da grade da Aula 11
```

O mapa **não foi desenhado à mão**: saiu da mesma classe `Mundo` que o simulador
usa para gerar o `/scan`. Ele existe para o exemplo andar no primeiro
`ros2 launch`, antes de você ter mapa próprio. Depois, troque pelo seu —
`mapa:=` — e é esse gesto que o G4.0 cobra.

Para regerar ou conferir (não precisa de ROS 2, só de `numpy`):

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS/src/aula15_nav2/maps"
python3 gerar_mapa.py --conferir
```

Ele relê o PGM, desfaz o flip de linhas e compara célula a célula com a grade de
origem. Na preparação deste material o resultado foi **38400/38400 células
(100,0000%)**, 4300 paredes de cada lado e nenhuma célula ambígua.

## O piloto reativo não sobe — e por que isso é um argumento, não um parâmetro

O `mundo.launch.py` da Aula 11 sobe dois nós, e o segundo é o `piloto` reativo —
que publica `/cmd_vel`. O Nav2 também publica `/cmd_vel`. **Dois publicadores no
mesmo tópico não dão erro**: dão um robô que obedece ao último que falou, 5 vezes
por segundo cada. É o mesmo tipo de defeito do `map_odom:=false` da Aula 12, uma
camada acima: lá eram dois publicadores da mesma aresta de TF, aqui são dois
publicadores do mesmo comando de velocidade. Nenhum dos dois reclama.

Por isso o launch inclui o mundo com `piloto:=false`, e a conferência é uma linha:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 topic info /cmd_vel --verbose     # espere 1 publicador: velocity_smoother
```

Se aparecerem **dois**, o `piloto:=false` não chegou — quase sempre porque o
`aula11_mundo` compilado é anterior ao argumento. O diagnóstico é o de sempre:

```bash
ros2 launch aula11_mundo mundo.launch.py --show-args   # tem de listar `piloto`
```

A versão primeira deste pacote resolvia isto por parâmetro — subia o piloto e o
calava com velocidade zero — e isso **estava errado**, por um motivo que vale a
aula: calar por parâmetro deixa o nó publicando (parada, 20 vezes por segundo),
e o robô anda truncado sem que nada no sistema esteja em erro. A correção certa
é não subir o nó. Quando a escolha é *existir ou não existir*, ela é argumento
de launch; parâmetro é para ajustar o que existe.

Vale reler o docstring do `piloto.py` da Aula 11, onde as quatro faltas dele
estão listadas. Cada uma virou um pedaço deste pacote: `amcl` (não sabia onde
estava), `bt_navigator` (não sabia para onde ia), `planner_server` (não
planejava rota) e `behavior_server` (não se recuperava).

## O nó `rota` — o item 1 do TP4 em 150 linhas

O enunciado do TP4 pede, no item 1, *"um nó Python enviando goals sequenciais ao
Nav2, definindo uma rota de patrulha ou inspeção"*. É o `rota.py` deste pacote, e
ele é pequeno por um motivo que vale dizer em voz alta: **o Nav2 é um servidor de
ação**, e vocês escreveram cliente de ação em setembro, nas Aulas 7 e 8.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 run aula15_nav2 rota                              # a rota padrão, uma volta
ros2 run aula15_nav2 rota --ros-args -p voltas:=0      # patrulha sem fim
ros2 run aula15_nav2 rota --ros-args \
  -p rota:="[2.0, 4.0, 0.0, 9.0, 2.0, 1.57]"           # a sua rota
```

A rota é um parâmetro **achatado** — `[x, y, yaw, x, y, yaw, ...]` — porque
parâmetro do ROS 2 não aceita lista de listas. O nó recusa uma lista cujo tamanho
não seja múltiplo de 3, dizendo quantos números recebeu.

Três coisas nele merecem leitura antes de copiar para o seu projeto:

| Linha | Por que ela está escrita assim |
|---|---|
| `alvo.header.frame_id = quadro` (`map`) | o objetivo é um lugar **no mapa**. Mandar o mesmo goal em `base_link` pede "ande 2 m para a frente e 4 m para a esquerda" — e o Nav2 obedece, sem reclamar |
| `status == GoalStatus.STATUS_SUCCEEDED` | no Humble o `result` do `navigate_to_pose` é um `std_msgs/Empty`: **não há código de erro para ler**. Quem escrever `resultado.result.error_code` escreve código de uma versão posterior |
| `rclpy.spin_until_future_complete` no `main` | bloquear é de propósito, e só é legítimo **fora** de callback. Dentro de um callback, o executor esperaria por si mesmo: nada acontece e nada reclama — o mesmo cuidado da Aula 8 |

Existem três ações para isto, e o enunciado aceita qualquer uma:
`navigate_to_pose` (uma pose), `follow_waypoints` (a lista inteira, com
`missed_waypoints` no resultado) e `navigate_through_poses` (a lista como um
plano único, com `number_of_poses_remaining` no feedback). Este nó usa a primeira
em sequência porque é a única em que **você vê**, no seu código, o goal ser
aceito, o feedback chegar e o status voltar — uma vez por ponto. As outras duas
escondem justamente a parte que o TP4 manda explicar.

## QoS no RViz2 — a armadilha que não avisa

O `rviz/nav2.rviz` já vem com cada display casado com o seu publicador, e isso
não é detalhe decorativo:

| Tópico | Política | Por quê |
|---|---|---|
| `/particle_cloud` | **Best Effort**, Volatile | o AMCL publica com `SensorDataQoS`, que é Best Effort. Um display em Reliable fica **em branco**, sem erro e sem aviso — e você conclui que o AMCL não está publicando |
| `/map`, costmaps | Reliable, **Transient Local** | mapa é dado de estado: o publicador guarda a última cópia para quem chega depois. Em Volatile você só vê o mapa se o RViz2 subir **antes** do `map_server` |
| `/scan` | Reliable, Volatile | o nó `mundo` publica com o QoS padrão do `rclpy`, que é Reliable |

A regra: um display pode pedir **menos** garantia que o publicador (Best Effort
contra Reliable funciona), nunca **mais**. Quem reclama da incompatibilidade é o
publicador, no log; o RViz2 não reclama de nada.

O display de `Image` vem **desligado** — este mundo não tem câmera. Ficou no
arquivo como lembrete da Aula 13, já em Best Effort.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package 'nav2_bringup' not found` | falta `sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup` |
| tudo sobe e para em "Configuring" | um nome em `node_names` do `lifecycle_manager` não corresponde a nó no ar |
| os nós ficam `ACTIVE` e nada acontece | `use_sim_time: true` sem Gazebo: ninguém publica `/clock` |
| o Nav2 sobe e morre uns segundos depois | `bond_timeout` curto numa máquina lenta — está em 10 s neste pacote |
| a nuvem de partículas não aparece | display em Reliable contra o Best Effort do AMCL, ou `nav2_rviz_plugins` ausente |
| a nuvem aparece e não fecha | pose inicial errada, ou o robô ainda não viu geometria suficiente |
| o laser treme na tela | dois publicadores de `map → odom` — esqueceu o `map_odom:=false` |
| `view_frames` mostra duas árvores | a mesma coisa |
| o mapa não aparece no RViz2 | `map_subscribe_transient_local` ou a Durability do display |
| `No valid path could be found` | objetivo em célula ocupada ou inflada — a `tolerance` do NavFn é 0,5 m |
| o robô gira no lugar e não sai | costmap local vazio (tópico do `/scan` errado), ou objetivo inalcançável |
| o robô não anda e nenhum nó reclama | a cadeia do `/cmd_vel`: confira `ros2 topic hz /cmd_vel_nav` e `/cmd_vel` |
| `rota` diz que o servidor não apareceu | o `bt_navigator` não está **ativo**: `ros2 lifecycle get /bt_navigator`. Sem pose inicial não há `map → odom`, e ele fica esperando a TF |
| `rota`: goal **RECUSADO** | o servidor nem tentou — objetivo fora do mapa ou em célula ocupada/inflada. A mensagem útil sai no terminal do `planner_server` |
| o robô anda truncado, e `/cmd_vel` tem 2 publicadores | o `piloto:=false` não chegou: o `aula11_mundo` compilado é anterior ao argumento — `--show-args` confirma |
| `Transform from base_footprint to odom was unavailable` | `transform_tolerance` apertado numa máquina lenta |
| o mapa parece espelhado em y | o `flipud` do PGM — `python3 gerar_mapa.py --conferir` |

## O que foi e o que não foi verificado

Esta seção existe porque a diferença importa, e porque material de aula que
finge ter sido testado custa caro na hora da entrega.

**Foi verificado, nesta máquina:**

- `ast.parse` em todos os `.py` do pacote — passou;
- `yaml.safe_load` no `config/nav2.yaml`, `maps/mapa.yaml` e `rviz/nav2.rviz` —
  todos carregam;
- `package.xml` como XML bem-formado;
- `use_sim_time` presente e `false` em **todos os 13** blocos de nó do
  `nav2.yaml`, conferido percorrendo a árvore carregada;
- o par `mapa.pgm` + `mapa.yaml` relido e comparado com a grade da Aula 11:
  **100,0000%**, 38400/38400 células, nenhuma ambígua. Orientação conferida por
  amostragem: o círculo em `(3,6 ; 6,0)` e o retângulo em `(2,7 ; 2,2)` caem nas
  linhas certas do PGM, a porta em `(6,1 ; 4,0)` está livre, as linhas do topo e
  da base são parede;
- nenhuma linha acima de 99 caracteres nos `.py`, nenhum byte não-ASCII neles;
- os nomes de nó, executável, pacote, parâmetro e plugin foram lidos na **fonte
  do Humble**, não de memória — as URLs estão abaixo.

**A primeira execução, em 26/10 — o que ela provou e o que ela achou:**

- `colcon build` passou, e `ros2 launch aula15_nav2 nav2.launch.py rviz:=true`
  subiu os **catorze processos**;
- o `map_server` leu o par do mapa (`240 X 160 map @ 0.05 m/cell`) e o AMCL o
  recebeu (`Received a 240 X 160 map`);
- o gerenciador de localização ativou `map_server` e `amcl`, com bond;
- o `controller_server` e o `smoother_server` ativaram; o `local_costmap`
  esperou o quadro `odom` e seguiu assim que o nó `mundo` começou a publicar;
- **o RViz2 não abriu**, e isso era um defeito deste launch: `launch_arguments`
  de um `IncludeLaunchDescription` não são escopadas, e o `'rviz': 'false'`
  passado ao mundo da Aula 11 apagava o `rviz:=true` da linha de comando. Está
  corrigido em duas camadas (`GroupAction` escopado e o nome `rviz_nav2`), e as
  duas foram exercitadas contra a biblioteca `launch` do branch `humble`, cada
  uma sozinha. Nasceu daí o `tools/conferir-launch.py`;
- sem RViz2 não houve *2D Pose Estimate*, logo sem `map → odom`, logo o
  `global_costmap` ficou em `Invalid frame ID "map"` e o `planner_server` não
  ativou. **Esse comportamento é correto** — é o Nav2 esperando a pose inicial.

**Continua NÃO verificado:**

- o Nav2 **navegando**: nenhum goal foi enviado, nenhuma rota foi planejada;
- o AMCL nunca localizou neste mapa; **não sabemos quanto tempo a nuvem leva
  para fechar**, nem se os `alpha` escolhidos bastam para a deriva de 3%;
- o NavFn nunca planejou uma rota, e o DWB nunca atravessou a porta de 1,2 m com
  `inflation_radius: 0.35` — a aritmética da porta está no YAML, a travessia
  não foi observada;
- o `rviz/nav2.rviz` nunca foi aberto num RViz2: ele carrega como YAML, e os
  nomes de classe foram conferidos na fonte, mas nenhum display foi visto
  desenhando;
- `maps/gerar_mapa.py` rodou e foi conferido; o `map_server` lendo o arquivo que
  ele produziu, **não**;
- o `piloto:=false` chegando ao `mundo.launch.py` — o argumento existe e o
  `testar.py` da Aula 11 passa, mas nenhum `ros2 launch` foi executado;
- o `rota.py` **nunca enviou um goal**. Os nomes de campo e de status foram lidos
  no `nav2_msgs/action/NavigateToPose.action` do Humble e no `action_msgs`, e o
  arquivo passa no `ast.parse` — nada além disso.

**Dois defeitos da Aula 11 que este pacote encontrou, e que foram corrigidos
lá:** o `mundo.launch.py` não tinha como desligar o piloto reativo (agora tem,
`piloto:=false`), e o nó `mundo` media o `/scan` a partir do **centro** do robô
enquanto o publicava no quadro `laser_frame`, 0,10 m à frente — um viés
sistemático de 10 cm entre onde o feixe foi medido e onde o ROS 2 achava que
tinha sido. Agora o nó mede a partir de `pose_do_laser()`, e o mesmo
`laser_x:=` alimenta a medição e a transformada estática. **Nenhuma das duas
correções foi exercitada com o Nav2 no ar.** Se a nuvem do AMCL fechar com um
deslocamento constante, a primeira pergunta é se o `aula11_mundo` compilado já é
a versão de hoje.

**As fontes do Humble que foram lidas** (branch `humble`, não `main` — os nomes
de parâmetro mudaram entre versões):

- `nav2_bringup/params/nav2_params.yaml` — a base de todo o `config/nav2.yaml`
- `nav2_bringup/launch/localization_launch.py` e `navigation_launch.py` — nomes
  de nó e executável, listas do `lifecycle_manager`, os remapeamentos do `cmd_vel`
- `nav2_bringup/rviz/nav2_default_view.rviz` — classes de display e QoS
- `nav2_amcl/src/amcl_node.cpp` — `set_initial_pose`, `initial_pose.*`, o QoS do
  `/particle_cloud`, o tratamento de `inf` e dos limites de alcance
- `nav2_costmap_2d/plugins/obstacle_layer.cpp` — `inf_is_valid` e os padrões das
  fontes de observação
- `nav2_lifecycle_manager/src/lifecycle_manager.cpp` — `bond_timeout`, `autostart`
- `nav2_map_server/src/map_server/map_server.cpp` — `yaml_filename`, `topic_name`,
  `frame_id`
- `nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml`
  — a árvore padrão, para saber quais servidores precisam estar de pé
- `rviz_default_plugins/plugins_description.xml` — os nomes `SetInitialPose` e
  `SetGoal`

Todos em `https://github.com/ros-navigation/navigation2/tree/humble` e
`https://github.com/ros2/rviz/tree/humble`.

## O que tem dentro

| Arquivo | Papel |
|---|---|
| `launch/nav2.launch.py` | inclui o mundo com `map_odom:=false` e `piloto:=false`, e sobe os nove nós do Nav2 |
| `config/nav2.yaml` | parâmetros do Nav2 — as cinco linhas que importam estão marcadas `# TROQUE` |
| `maps/mapa.pgm`, `maps/mapa.yaml` | o mapa pronto, gerado da grade da Aula 11 |
| `maps/gerar_mapa.py` | gera e confere o par acima, sem ROS 2 |
| `rviz/nav2.rviz` | nuvem de partículas, dois costmaps, planos — com o QoS resolvido |
| `aula15_nav2/rota.py` | cliente da ação `navigate_to_pose`: percorre uma rota de poses, uma por vez — o item 1 do TP4 |
