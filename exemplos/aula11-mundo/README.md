# Aula 11 — Mundo mínimo: `/scan`, `/odom` e a árvore de TF do TP3

Este pacote faz o papel que o Gazebo faria no TP3, e faz a versão mínima de
propósito: **sem física, sem render e sem janela**. O que ele entrega são as
mesmas interfaces — e é das interfaces que o seu sistema depende, não do
simulador.

Com ele você fecha o **G3.0** (um comando sobe o sistema inteiro) e o **G3.2**
(árvore `map → odom → base_link → sensores`) sem depender da pilha gráfica, e
chega no Gazebo com o esqueleto já pronto.

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

cd /tmp && rm -rf pb-aula11 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-aula11 && \
  # a copia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x),
  # e o colcon passa a compilar a versao velha sem dizer nada
  rm -rf "$PB_WS/src/aula11_mundo" && \
  cp -r pb-aula11/exemplos/aula11-mundo/aula11_mundo "$PB_WS/src/" && \
  cd "$PB_WS" && colcon build --packages-select aula11_mundo && \
  source install/setup.bash
```

Tudo o que não é ROS 2 roda sem compilar nada:

```bash
cd /tmp/pb-aula11/exemplos/aula11-mundo
python3 testar.py                    # 8 verificações do mundo
python3 simular.py --segundos 90     # gera simulacao.png
```

## Rodar

```bash
ros2 launch aula11_mundo mundo.launch.py
ros2 launch aula11_mundo mundo.launch.py deriva:=0.0     # odometria perfeita
ros2 launch aula11_mundo mundo.launch.py modelo:=false   # sem o URDF da Aula 9
ros2 launch aula11_mundo mundo.launch.py rviz:=true
```

!!! tip "Se o RViz2 abrir só com o Grid, não é defeito do sistema"
    É ausência de **displays**. O `rviz2` sem `-d` abre vazio: quadro fixo `map`, status
    `Ok`, e nada desenhado — parece que nada subiu, mas o que falta é a configuração.

    O launch passa `-d rviz/mundo.rviz`, que já traz LaserScan, Odometry, RobotModel, TF e o
    mundo real. Se você abrir o `rviz2` na mão, passe o arquivo:

    ```bash
    rviz2 -d $(ros2 pkg prefix aula11_mundo)/share/aula11_mundo/rviz/mundo.rviz
    ```

## O que tem dentro

| Arquivo | Papel |
|---|---|
| `aula11_mundo/mapa.py` | a grade de ocupação e o laser que a enxerga — numpy puro |
| `aula11_mundo/nucleo.py` | a lógica do robô, **sem ROS 2**: integração, deriva e decisão |
| `aula11_mundo/mundo.py` | o nó: publica `/scan`, `/odom`, `/deriva` e a TF `odom → base_footprint` |
| `aula11_mundo/piloto.py` | o nó que dirige — reativo, sem mapa e sem destino |
| `aula11_mundo/simular.py` | roda tudo offline e desenha as duas trajetórias |
| `launch/mundo.launch.py` | sobe o sistema inteiro, no formato que o G3.0 cobra |
| `rviz/mundo.rviz` | os displays já montados — sem isto o RViz2 abre só com o Grid |
| `config/mundo.yaml` | parâmetros, com o curinga `/**` da Aula 10 |
| `simular.py` · `testar.py` | rodam da pasta do exemplo, sem ROS 2 e sem compilar |

O `nucleo.py` existir separado não é organização: é o mesmo contrato do detector
da Aula 10. A lógica não sabe em que sistema roda, então o que você depura
offline é literalmente o que vai para o nó.

## A árvore de TF, e quem publica cada aresta

É esta a árvore que o **G3.2** pede, e saber quem publica cada aresta é metade
do gate:

```
map ──────────► odom ──────────► base_footprint ──► (URDF) ──► camera_link
 │               │                    │
 │               │                    └──► laser_frame
 │               │
 │               └── o nó `mundo`, integrando a odometria (com deriva)
 └── ESTE LAUNCH, como identidade fixa — é um PLACEHOLDER
```

No TP3 quem publica `map → odom` é o **SLAM Toolbox**, e a identidade vira
correção. É literalmente esse o trabalho dele.

## O exercício: ver a deriva aparecer

```bash
ros2 launch aula11_mundo mundo.launch.py
ros2 topic echo /deriva          # noutro terminal
```

O número cresce. Ele é a distância entre onde o robô **está** e onde a
odometria **acha** que ele está.

Agora desligue a deriva e compare:

```bash
ros2 launch aula11_mundo mundo.launch.py deriva:=0.0
```

Offline, a mesma coisa sai em figura — a linha cinza é a verdade, a vermelha é a
odometria:

```bash
python3 simular.py --deriva 3 --saida com-deriva.png
python3 simular.py --deriva 0 --saida sem-deriva.png
```

### Por que isso não se resolve medindo mais vezes

A odometria aqui não erra por **ruído**: erra por **viés**. O modelo aplica um
erro de escala de 3% — o erro de quem mediu o raio da roda com régua.

Ruído se cancela: some com a média, e medir mais vezes ajuda. Viés não. Ele tem
sinal constante, entra na integral toda vez com o mesmo sinal, e **cresce com a
distância percorrida**. Rodar mais tempo piora.

É por isso que nenhum filtro sobre `/odom` resolve, e é por isso que o SLAM
precisa de uma referência **externa** que não se mexe: as paredes.

### O mundo real desenhado, e por que ele está ali

O nó publica também `/mundo_real`, um `OccupancyGrid` com as paredes de verdade, no
quadro `map`. **O robô não tem acesso a isso** — se tivesse, não precisaria de SLAM.

Ele existe só para você enxergar a deriva: as paredes ficam paradas em `map`, enquanto o
laser, desenhado a partir da odometria, escorrega para fora delas. Sem as paredes na tela,
"o laser desliza" é uma frase; com elas, é uma coisa que você vê acontecer.

Quando o SLAM entrar, no TP3, ele vai construir o próprio mapa a partir do `/scan` — e a
diferença entre esse mapa e este aqui é exatamente o que ele ainda não sabe.

### Um detalhe que vale medir

Na corrida padrão (`--deriva 3 --segundos 90`, 28,4 m percorridos), o erro de
posição **sobe e desce** — 0,19 m, depois 0,15 m, depois 0,95 m, terminando em
0,57 m — enquanto o erro angular sobe sem parar até 13,6°.

A posição oscila porque um giro pode reaproximar as duas poses por acaso. Quem
olhar só o número final conclui que a deriva foi menor do que ela chegou a ser.

É a mesma lição da Aula 9, noutro assunto: **o agregado esconde onde falhou.**
O número final é uma medida honesta de uma coisa que não é a que interessa.

## Se você quiser Gazebo

Vá em frente — este pacote não te impede, ele te adianta. Troque o nó `mundo`
por um Gazebo publicando `/scan` e `/odom` nos mesmos tópicos, e **todo o resto
do seu sistema continua valendo**: o launch, os frames, o SLAM, o Nav2.

Essa é a razão de existir deste exemplo. O simulador é um detalhe de
implementação atrás de uma interface — e trocar o miolo sem trocar o contrato é
o mesmo movimento da Aula 6, da Aula 9 e da Aula 10.

O passo a passo está em [Gazebo para o TP3](../../tutoriais/gazebo-para-o-tp3.md):
qual versão (Fortress, não Harmonic), como montar a ponte, e quando parar.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package 'aula11_mundo' not found` | terminal sem `source install/setup.bash` |
| `No module named 'numpy'` | `sudo apt install python3-numpy` — nunca pip no python do sistema |
| `package 'meu_robo_description' not found` | suba com `modelo:=false` |
| `/deriva` sempre 0 | subiu com `deriva:=0.0`, ou o robô não está andando |
| o robô não anda | o `piloto` não subiu, ou `/scan` não está chegando: `ros2 topic hz /scan` |
| `view_frames` mostra duas árvores | faltou o `static_transform_publisher` de `map → odom` |
| RViz2 vazio | o G3.2 não depende dele — use `view_frames` e `tf2_echo` |
| o laser desliza para fora das paredes no RViz2 | **é o ponto da aula**: `map → odom` é identidade e a odometria derivou |
