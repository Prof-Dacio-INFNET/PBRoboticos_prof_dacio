# Aula 12 — O SLAM paga a conta da deriva

**Terça, 06/10/2026 · sala SJ205 · Etapa 6 (28/09–10/10)**

[:material-file-pdf-box: Slides da Aula 12 (PDF)](apresentacao-aula12.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula12-slam`](../../exemplos/aula12-slam/index.md){ .md-button }
[:material-code-tags: Exemplo `aula11-mundo`](../../exemplos/aula11-mundo/index.md){ .md-button }

## Cenas dos últimos episódios

**Na Aula 11** vocês subiram o sistema inteiro com um comando, viram o YAML que é lido e descartado em silêncio, montaram o mundo mínimo publicando `/scan` e `/odom`, e mediram a deriva da odometria crescendo num número. O bloco sobre navegação era o de folga declarado e ficou para hoje — ele volta no fim, e cai melhor agora, com mapa na mão.

Três coisas de antes voltam, e a terceira é a que a aula inteira resolve:

| De onde vem | O que era | Onde entra hoje |
|---|---|---|
| **Aula 9** — ruído e viés | ruído se cancela com repetição; viés não | o SLAM é a resposta ao viés, e ela vem de fora |
| **Aula 11** — a árvore de TF | quatro arestas, cada uma com um dono | hoje **uma delas troca de dono** |
| **Aula 11** — a deriva medida | o erro entre onde o robô está e onde acha que está | hoje ele vira a correção que o SLAM publica |

A frase que ficou em aberto na semana passada: *"`map → odom` está, neste momento, mentindo"*. Hoje ela deixa de mentir.

## A ideia da aula em uma frase

**A aresta `map → odom` é o erro acumulado da odometria, com o sinal trocado.** Não é uma transformada qualquer: é exatamente o número que vocês mediram como `/deriva`, publicado por quem conseguiu descobri-lo olhando para fora.

E olhar para fora é o ponto. O robô não pode corrigir a odometria com mais odometria — já vimos por quê. O SLAM compara o `/scan` de agora com o mapa que vem construindo, reconhece onde já esteve, e daí deduz quanto errou.

## Por que a aula está nesta ordem

Ordenada por **custo de perda**. O que vence antes vem primeiro; o bloco de folga vem por último e fica declarado de antemão.

| Bloco | O que você sai sabendo fazer | Prazo da entrega | Se faltar tempo |
|---|---|---|---|
| 1. A árvore fecha? | provar que a sua árvore de transformadas está inteira | **sexta** | não pode cair |
| 2. O SLAM assume a aresta | trocar o placeholder por uma correção calculada | 15/10 | não pode cair |
| 3. Salvar e medir o mapa | guardar o mapa e dizer **quanto** ele acertou | 15/10 | não pode cair |
| 4. O que a navegação acrescenta | dizer o que falta a um robô que só reage | 30/10 | **volta na Aula 13** |

O bloco 1 não é revisão: é pré-requisito literal do bloco 2. **O SLAM não conserta TF errada** — ele é construído em cima dela, e com a árvore quebrada ele sobe sem reclamar e não produz mapa nenhum.

## Objetivos

Ao final da aula você deve conseguir provar que a sua árvore de transformadas está completa e sem aviso; ligar o `slam_toolbox` ao seu robô acertando as quatro linhas que importam; explicar por que o placeholder tem de sair quando o SLAM entra; salvar o mapa construído; e dizer, com um número, quanto esse mapa concorda com o mundo.

## Baixar o material desta aula

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

# 1) o SLAM e o utilitário que salva mapa
sudo apt install -y ros-humble-slam-toolbox ros-humble-nav2-map-server

# 2) baixar o material (pode repetir sempre — a linha do rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 3) os dois pacotes: o mundo da semana passada e o SLAM de hoje
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula11-mundo/aula11_mundo "$PB_WS/src/"
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula12-slam/aula12_slam   "$PB_WS/src/"

# 4) o comparador vai para a RAIZ do workspace, e não fica em /tmp:
#    a tarefa da semana é feita depois da aula, e /tmp some no reboot
cp /tmp/PBRoboticos_prof_dacio/exemplos/aula12-slam/comparar_mapas.py "$PB_WS/"

cd "$PB_WS"
colcon build --packages-select aula11_mundo aula12_slam
source install/setup.bash
```

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Abriu um terminal novo? Elas se perderam, e sem essa linha `"$PB_WS/install/setup.bash"` viraria `/install/setup.bash` — um erro que não diz o que faltou.

    Com ela, o shell para e nomeia a variável ausente. É a mesma ideia de verificar a afirmação em vez de deixar o silêncio passar por aprovação.

O comparador de mapas roda solto, sem compilar e sem ROS 2:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd /tmp/PBRoboticos_prof_dacio/exemplos/aula12-slam
python3 testar.py
```

## Parte 1 — A sua árvore fecha?

Antes de qualquer SLAM, a pergunta que decide o resto do dia. Suba o seu sistema e rode, com ele no ar:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && source install/setup.bash

ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo map base_footprint
```

O `frames.pdf` tem de mostrar **uma árvore só**, de `map` até os seus sensores, sem frames órfãos e sem dois `odom`.

| O que aparece | O que significa |
|---|---|
| PDF vazio | o launch não está rodando — TF é fluxo, não arquivo |
| duas árvores separadas | falta uma junta ligando as partes; procure o frame sem pai |
| dois `odom` | dois nós publicam a mesma aresta — tire um |
| `base_footprint` sem pai | falta o `odom → base_footprint`, que é quem integra a odometria |

!!! danger "Isto é pré-requisito, não revisão"
    O `slam_toolbox` lê a sua TF para saber onde o laser estava quando mediu. Com a árvore quebrada, ele **sobe sem reclamar** e simplesmente não produz mapa. Você passaria a aula olhando uma tela vazia e culpando o SLAM.

## Parte 2 — O SLAM assume a aresta

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula12_slam slam.launch.py
```

No RViz2, o mapa do SLAM cresce por cima do mundo real, que fica em cinza por baixo.

### A diferença estrutural é uma linha

O launch de hoje inclui o mundo da semana passada com **um argumento a mais**:

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(os.path.join(mundo_pkg, 'launch', 'mundo.launch.py')),
    launch_arguments={'map_odom': 'false',        # ← o placeholder sai
                      'deriva': deriva,
                      'rviz': 'false'}.items(),
),
```

O `static_transform_publisher` que publicava `map → odom` como identidade **tem de sair**. Dois publicadores da mesma aresta não geram erro: geram árvore quebrada, que é o defeito mais caro deste trabalho. Se você esquecer, o laser treme na tela e o `view_frames` mostra o estrago.

### As quatro linhas que ligam o SLAM ao seu robô

Todo o resto do `slam.yaml` é o padrão do `slam_toolbox` e serve como está:

```yaml
odom_frame: odom              # de onde vem a odometria
map_frame: map                # a aresta que ele vai PUBLICAR
base_frame: base_footprint    # a raiz do seu URDF
scan_topic: /scan             # o sensor
```

Errar `base_frame` é o modo mais comum de o SLAM subir calado e não entregar nada. Se o seu URDF tem outra raiz, é aqui que se diz.

### Ver a correção acontecer

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 run tf2_ros tf2_echo map odom        # a correção, crescendo
ros2 topic echo /deriva                   # o erro que ela está corrigindo
```

Os dois números andam juntos, e é esse o fecho da semana passada: **a correção é a deriva, com o sinal trocado**.

Quando o robô passa de novo por onde já esteve, o SLAM reconhece o lugar e a correção **dá um salto**. Isso é o fechamento de laço, e é o que a odometria sozinha nunca faz — porque ela não tem como saber que já esteve ali.

## Parte 3 — Salvar e medir o mapa

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/maps" && cd "$PB_DIR/maps" && \
  ros2 run nav2_map_server map_saver_cli -f mapa
```

Os três comandos estão encadeados de propósito: se o `mkdir` falhar, o `map_saver` **não roda**. Sem o encadeamento ele rodaria no diretório em que você estava, e o mapa apareceria num lugar que você não escolheu.

!!! danger "Nunca `sudo mkdir` numa pasta sua"
    Se o `mkdir` reclamar, o problema é a variável vazia — não a permissão. Resolver com `sudo` cria a pasta **pertencente ao root**, e aí o `map_saver`, que roda como você, não consegue escrever. O erro que aparece é `Magick: Unable to open file`, que não diz nada sobre permissão.

    Para desfazer: `sudo chown -R "$(id -u):$(id -g)" "$PB_DIR/maps"`.

Gera `mapa.pgm` + `mapa.yaml`, **com o launch ainda rodando**: o mapa vive na memória do nó, e o `map_saver_cli` pede uma cópia. Sem ninguém publicando, não há o que salvar.

### "Parece bom" não é resposta — de novo

Num robô real você não tem a verdade: só tem o mapa. Como o nosso mundo é sintético, a verdade existe, e dá para transformar impressão em número:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS"
python3 comparar_mapas.py "$PB_DIR/maps/mapa.yaml"
```

Ele reporta **cobertura** (quanto do mundo foi explorado) e **concordância** (quanto do que foi explorado bate), separadas de propósito: um mapa de 30% do mundo com 100% de concordância é um mapa certo e incompleto, que é um problema diferente de um mapa completo e torto.

### Ver onde o mapa errou, e não só quanto

O número diz **quanto**; a figura diz **onde** — e olhar para o lugar costuma explicar o número:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS"
python3 comparar_mapas.py "$PB_DIR/maps/mapa.yaml" --imagem "$PB_DIR/maps/diferenca.png"
```

Cada célula sai pintada pela categoria: **azul** onde o SLAM achou a parede, **âmbar** onde ele não viu, **vermelho** onde inventou parede que não existe, e **cinza** no que ficou inexplorado. A legenda vai dentro da imagem, então ela entra no relatório sozinha.

Uma deriva residual aparece como **dupla borda âmbar-e-vermelha** ao longo das paredes: o mapa inteiro deslocado alguns centímetros. Um fechamento de laço que não aconteceu aparece como um lado do cenário torto em relação ao outro. São assinaturas diferentes, e dá para distinguir olhando.

!!! warning "A origem do mapa não é a origem do mundo"
    O quadro `map` nasce **onde o robô começou**, não onde o mundo começa — aqui, em `(2, 4)`. Errar esse desconto faz um mapa correto parecer péssimo, e é a primeira coisa a conferir quando o número vier baixo.

Isto é a Aula 9 de novo, noutro objeto: **declarar a régua antes de olhar o resultado**, e desconfiar do agregado que esconde onde falhou.

### As quatro janelas que vale deixar abertas

O terminal prova; a tela convence. Com o sistema no ar, estas quatro mostram coisas diferentes ao mesmo tempo:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"

# 1. o mapa crescendo sobre o mundo real — já vem configurado no launch
ros2 launch aula12_slam slam.launch.py rviz:=true

# 2. o grafo: o slam_toolbox entrando entre o sensor e a TF
ros2 run rqt_graph rqt_graph

# 3. a deriva subindo, em gráfico e ao vivo
ros2 run rqt_plot rqt_plot /deriva/data

# 4. a correção que o SLAM publica, em número
ros2 run tf2_ros tf2_echo map odom
```

As janelas 3 e 4 lado a lado são a aula inteira numa tela: **a curva que sobe é o erro, e o número ao lado é a correção que o anula**.

!!! tip "A árvore de TF, ao vivo em vez de em PDF"
    O `view_frames` gera um PDF estático — bom como evidência, ruim para acompanhar. Para ver a árvore mudando, existe o `rqt_tf_tree`, e o nome da invocação mudou entre versões. Confira o que a **sua** instalação tem antes de decorar:

    ```bash
    ros2 pkg executables rqt_tf_tree      # diz o que existe no seu sistema
    ```

    Se não aparecer nada, `sudo apt install ros-humble-rqt-tf-tree`. É o mesmo hábito de sempre: verificar em vez de assumir.

## Parte 4 — O que a navegação acrescenta

O `piloto.py` do mundo mínimo é o navegador mais burro que funciona: anda reto, gira quando fecha na frente. Trinta linhas, e explora o mundo inteiro.

Agora que existe mapa, a lista do que falta a ele fica concreta:

| O piloto não sabe | O Nav2 acrescenta | Já existe? |
|---|---|---|
| onde está | localização contra o mapa | **o mapa é de hoje** |
| para onde vai | um objetivo, enviado como ação | as ações são da Aula 8 |
| o que há além do que o laser vê | custos global e local, construídos do mapa | **o mapa é de hoje** |
| o que fazer quando trava | comportamentos de recuperação | ainda não |

Duas das quatro linhas passaram a ser possíveis hoje. E a segunda fecha o semestre até aqui: **o objetivo do Nav2 é uma ação**, com feedback periódico e cancelamento — exatamente as da Aula 8. Navegação não é assunto novo; é a montagem de peças que já estão no lugar.

## Tarefa da semana

### O que fazer

Construir, salvar e **medir** o mapa do seu próprio cenário, com a correção `map → odom` vindo do SLAM e não de um placeholder.

Ao terminar, quatro coisas são verdade: o `view_frames` mostra uma árvore só com `map` no topo; o `tf2_echo map odom` devolve um valor que muda ao longo do tempo; existe um par `mapa.pgm` + `mapa.yaml` no seu repositório; e você tem um número dizendo o quanto esse mapa concorda com o cenário.

### O que usar

| Para | Use |
|---|---|
| ligar o SLAM | `aula12_slam/config/slam.yaml` — as quatro linhas do topo |
| tirar o placeholder | `map_odom:=false` ao incluir o mundo |
| salvar | `ros2 run nav2_map_server map_saver_cli -f mapa` |
| medir | `comparar_mapas.py` — ele fica na **raiz do workspace** (`$PB_WS`), não em `/tmp` |
| conferir a árvore antes | `view_frames` e `tf2_echo`, da Aula 11 |

### Como adequar ao seu projeto

**O cenário é o seu.** Se você editou o `mapa.py` para parecer com o ambiente do seu robô — corredores, fileiras, colunas —, é esse mundo que o SLAM vai mapear, e o comparador já usa a sua versão como verdade. Se você foi de Gazebo, o `/scan` vem de lá e o SLAM não percebe diferença: é a mesma interface.

**A métrica é sua decisão.** Qual concordância é suficiente para o seu projeto? Um robô que navega entre pontos nomeados tolera um mapa mais tosco que um que precisa encostar numa prateleira. Declare o número **antes** de rodar.

**O laço é o seu.** O fechamento de laço só acontece se o robô voltar por onde passou. Se o seu cenário é um corredor sem volta, ele nunca fecha — e isso é um achado sobre o seu projeto, não um defeito do SLAM. Escreva isso no relatório.

### Como saber que terminou

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula12_slam slam.launch.py &      # deixe explorar uns 2 minutos
sleep 120

ros2 run tf2_tools view_frames                        # uma árvore, map no topo
ros2 run tf2_ros tf2_echo map odom --once             # a correção, diferente de zero
mkdir -p "$PB_DIR/maps" && cd "$PB_DIR/maps" && \
  ros2 run nav2_map_server map_saver_cli -f mapa      # o par .pgm + .yaml

cd "$PB_WS"                                           # onde o comparador foi copiado
python3 comparar_mapas.py "$PB_DIR/maps/mapa.yaml" \
  --imagem "$PB_DIR/maps/diferenca.png"               # o número E a figura
```

Guarde as saídas em `docs/evidencias/tp3/`, junto do número do comparador e da figura da diferença.

!!! tip "Se o `comparar_mapas.py` não for encontrado"
    Ele foi copiado para a raiz do workspace no bloco de download justamente porque `/tmp` **não sobrevive ao reboot** — e esta tarefa é feita depois da aula. Se ainda assim ele reclamar que não achou o cenário, ele diz as três saídas possíveis na própria mensagem: rodar de dentro do material, copiá-lo para a raiz do workspace, ou sourcear o workspace.

## Desafio — quanto de mapa o fechamento de laço vale?

Opcional, para quem terminou. Ele se responde medindo.

O fechamento de laço é o mecanismo que distingue SLAM de odometria com desenho. A pergunta é: **quanto ele vale, em concordância de mapa?**

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
# Rode duas vezes, 3 minutos cada, salvando com nomes diferentes:
#   (a) deriva baixa  — a odometria quase não erra, o laço tem pouco a corrigir
#   (b) deriva alta   — a odometria erra muito, e o laço faz o trabalho pesado
ros2 launch aula12_slam slam.launch.py deriva:=1.0
ros2 launch aula12_slam slam.launch.py deriva:=8.0
```

Salve e compare os dois mapas. Depois responda, em `docs/evidencias/tp3/valor-do-laco.md`: a concordância caiu proporcionalmente à deriva, ou o SLAM absorveu o erro? Em que ponto ele deixa de dar conta? E o que isso diz sobre **quanto vale calibrar a odometria** de um robô que vai rodar SLAM de qualquer jeito?

A última pergunta é a interessante, e tem mais de uma resposta defensável.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package 'slam_toolbox' not found` | falta `sudo apt install ros-humble-slam-toolbox` |
| o mapa não aparece no RViz2 | `base_frame` errado no YAML, ou `/scan` sem publicar |
| `view_frames` mostra duas árvores | esqueceu o `map_odom:=false` |
| o laser treme na tela | a mesma coisa: duas fontes disputando `map → odom` |
| `view_frames` gera PDF vazio | o launch não está rodando |
| `map_saver_cli` não salva nada | o launch precisa estar no ar; o mapa vive na memória do nó |
| `Magick: Unable to open file (mapa.pgm)` | a pasta é de **root**: alguém criou com `sudo`. `sudo chown -R "$(id -u):$(id -g)" <pasta>` |
| `cannot create directory '/maps'` | `$PB_DIR` está vazio neste terminal — redefina as variáveis do bloco de download |
| `bash: /install/setup.bash: No such file...` | a mesma coisa: `$PB_WS` vazio virou caminho absoluto |
| o mapa fica torto e não corrige | o robô ainda não fechou laço — deixe explorar mais |
| concordância baixíssima | confira `--origem-robo` antes de culpar o SLAM |
| RViz2 abre vazio | abriu sem `-d`; o launch já passa a configuração |
| `No module named 'numpy'` | `sudo apt install python3-numpy` |

## Para a próxima aula (13/10)

**Percepção: segmentação por instância e o módulo veicular.** O mapa diz onde o robô está; a percepção diz o que há em volta. Chegue com o mapa salvo e medido — ele é a base das duas entregas seguintes.
