# Aula 12 — O SLAM assume a aresta `map → odom`

Na Aula 11 a aresta `map → odom` era uma identidade fixa — um placeholder que
mentia, e por isso o laser escorregava para fora das paredes. Aqui ela passa a
ser **calculada**, pelo `slam_toolbox`, a partir do `/scan`.

A diferença estrutural entre os dois launches é **uma linha**: o mundo sobe com
`map_odom:=false`, o placeholder sai, e quem publica a aresta passa a ser o SLAM.

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y ros-humble-slam-toolbox ros-humble-nav2-map-server

cd /tmp && rm -rf pb-a12 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a12 && \
  cp -r pb-a12/exemplos/aula12-slam/aula12_slam "$PB_WS/src/" && \
  cp -r pb-a12/exemplos/aula11-mundo/aula11_mundo "$PB_WS/src/" && \
  cp pb-a12/exemplos/aula12-slam/comparar_mapas.py "$PB_WS/" && \
  cd "$PB_WS" && colcon build --packages-select aula11_mundo aula12_slam && \
  source install/setup.bash
```

## Rodar

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula12_slam slam.launch.py
ros2 launch aula12_slam slam.launch.py deriva:=6.0    # erro maior, correção maior
ros2 launch aula12_slam slam.launch.py rviz:=false
```

No RViz2 você vê o mapa do SLAM crescendo por cima do mundo real, que fica em
cinza por baixo. Onde os dois coincidem, o SLAM acertou.

## O que tem dentro

| Arquivo | Papel |
|---|---|
| `launch/slam.launch.py` | inclui o mundo com `map_odom:=false` e sobe o `slam_toolbox` |
| `config/slam.yaml` | parâmetros do SLAM — as quatro linhas que importam estão no topo |
| `rviz/slam.rviz` | mapa do SLAM por cima, mundo real por baixo |
| `comparar_mapas.py` | mede o mapa construído contra a verdade, sem ROS 2 |
| `testar.py` | confere o comparador com mapas sintéticos de defeito conhecido |

## As quatro linhas que ligam o SLAM ao seu robô

Todo o resto do `slam.yaml` é o padrão do `slam_toolbox` e serve como está. O que
você precisa acertar são estas:

```yaml
odom_frame: odom              # de onde vem a odometria
map_frame: map                # a aresta que ele vai PUBLICAR
base_frame: base_footprint    # a raiz do seu URDF
scan_topic: /scan             # o sensor
```

Se o seu URDF tem outra raiz, é aqui que se diz. Errar `base_frame` é o modo mais
comum de o SLAM subir sem reclamar e não produzir mapa nenhum.

## Ver a correção acontecer

A aresta `map → odom` **é** o erro acumulado da odometria, com o sinal trocado.
Na Aula 11 medimos esse erro como `/deriva`; agora dá para ver o SLAM pagando a
conta:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 run tf2_ros tf2_echo map odom        # a correção, crescendo
ros2 topic echo /deriva                   # o erro que ela está corrigindo
```

Os dois números andam juntos. Quando o robô fecha um laço — passa de novo por
onde já esteve —, o SLAM reconhece o lugar e a correção dá um salto. É o
**fechamento de laço**, e é o que a odometria sozinha nunca consegue fazer.

## Salvar o mapa

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/maps" && cd "$PB_DIR/maps" && \
  ros2 run nav2_map_server map_saver_cli -f mapa
```

Encadeado de propósito: se o `mkdir` falhar, o `map_saver` não roda — senão ele salvaria no diretório em que você estava. E **não resolva um `mkdir` que falhou com `sudo`**: a pasta fica de root, o `map_saver` roda como você, e o erro que aparece é `Magick: Unable to open file`, que não diz nada sobre permissão.

Gera o par `mapa.pgm` + `mapa.yaml`. **Com o launch ainda rodando** — o mapa vive
na memória do nó, e `map_saver_cli` pede uma cópia dele; sem ninguém publicando,
não há o que salvar.

## Medir o mapa: o que normalmente não dá para fazer

Num robô real você não tem a verdade — só tem o mapa, e "parece bom" é tudo o que
dá para dizer. Como o nosso mundo é sintético, a verdade existe:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS"
python3 comparar_mapas.py "$PB_DIR/maps/mapa.yaml"
```

Ele reporta cobertura (quanto do mundo foi explorado), concordância (quanto do que
foi explorado bate), paredes encontradas, perdidas e fantasmas.

Com `--imagem`, ele também **desenha onde** errou:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS"
python3 comparar_mapas.py "$PB_DIR/maps/mapa.yaml" --imagem "$PB_DIR/maps/diferenca.png"
```

Azul onde achou a parede, âmbar onde não viu, vermelho onde inventou, cinza no
inexplorado — com a legenda embutida, para a figura ir ao relatório sozinha.

Deriva residual aparece como dupla borda âmbar-e-vermelha ao longo das paredes;
laço não fechado aparece como um lado do cenário torto em relação ao outro.

!!! warning "A origem do mapa não é a origem do mundo"
    O quadro `map` do SLAM nasce **onde o robô começou**, não onde o mundo começa.
    No nosso mundo o robô parte de `(2, 4)`, e é esse o desconto entre os dois
    sistemas — o padrão do `--origem-robo`.

    Errar isso faz um mapa correto parecer péssimo. É a primeira coisa a conferir
    quando o número vier baixo.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package 'slam_toolbox' not found` | falta `sudo apt install ros-humble-slam-toolbox` |
| o mapa não aparece | `base_frame` errado no YAML, ou `/scan` não está publicando |
| `view_frames` mostra duas árvores | esqueceu o `map_odom:=false` — dois publicadores da mesma aresta |
| o laser treme na tela | a mesma coisa: duas fontes disputando `map → odom` |
| `map_saver_cli` não salva nada | o launch tem de estar rodando; o mapa vive na memória do nó |
| `Magick: Unable to open file (mapa.pgm)` | a pasta é de **root**: alguém criou com `sudo`. `sudo chown -R "$(id -u):$(id -g)" <pasta>` |
| `cannot create directory '/maps'` | `$PB_DIR` está vazio neste terminal — redefina as variáveis do bloco de download |
| `bash: /install/setup.bash: No such file...` | a mesma coisa: `$PB_WS` vazio virou caminho absoluto |
| o mapa fica torto e não corrige | o robô não fechou laço ainda — deixe explorar mais |
| concordância baixíssima | confira `--origem-robo` antes de culpar o SLAM |
| `No module named 'numpy'` | `sudo apt install python3-numpy` |
