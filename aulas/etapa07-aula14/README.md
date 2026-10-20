# Aula 14 — Aterrissagem do TP3: o enunciado, item por item

**Terça, 20/10/2026 · sala SJ205 · Etapa 7 (12/10–24/10)**

[:material-file-pdf-box: Slides da Aula 14 (PDF)](apresentacao-aula14.pdf){ .md-button .md-button--primary }
[:material-clipboard-text-search: Roteiro de revisão](../../exemplos/tp3/revisar-entrega/index.md){ .md-button }
[:material-code-tags: Exemplo `aula13-instancia`](../../exemplos/aula13-instancia/index.md){ .md-button }

## Cenas dos últimos episódios

**Na Aula 13** a máscara virou instância: `connectedComponents` devolveu 72 objetos onde havia 120 — 40% de erro de contagem, sem erro nenhum — e o watershed devolveu 120. Depois a régua mostrou que **IoU médio 0,86 com 48 casadas de 120** é um número bonito de uma medida quebrada, e que o maior IoU da tabela podia ser do pior detector. O bloco de percepção veicular não saiu; ele entra hoje, no formato que o enunciado pede, que é diferente do que estava previsto.

**Hoje é a última aula antes da entrega de sexta, 23/10.** Não há conteúdo novo: há o enunciado do TP3 lido linha a linha, com demonstração de cada item funcionando, e a lista do que o avaliador procura em cada um.

## A ideia da aula em uma frase

**O enunciado é a rubrica.** Cada verbo dele — *desenvolva*, *execute*, *documente*, *capture*, *explique*, *publique*, *relacione* — é um item que alguém vai procurar no seu repositório na sexta à noite. O que não estiver provado por arquivo, print ou comando não conta, por mais que tenha funcionado na sua máquina.

## Os quatro itens, e o que cada um cobra

| Item do enunciado | O verbo que pega | Gate | Prova no repositório |
|---|---|---|---|
| 1. Launch principal | **execute com um único comando** | G3.0, G3.1 | `launch/bringup.launch.py` + captura de tela |
| 2. TFs e SLAM | **capture** o TF tree e **explique** cada frame | G3.2, G3.3 | `frames.pdf` + `maps/` + parágrafos no relatório |
| 3. Segmentação semântica | **publique** em `/vision/segmented` | G3.4 | print do RViz2 + o nó no repositório |
| 4. Arquitetura veicular | **relacione** com o seu projeto | G3.5 | `docs/evidencias/tp3/veicular.md` |

## Preparar o terminal e pegar o conferidor

Hoje você trabalha **no seu projeto**, não num exemplo. Este bloco define as variáveis e traz a única coisa nova da aula: o conferidor da entrega.

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

cd /tmp && rm -rf pb-a14 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a14

# a copia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x),
# e o colcon passa a compilar a versao velha sem dizer nada
rm -rf "$PB_DIR/aula13-instancia" "$PB_WS/src/aula13_instancia"
cp pb-a14/exemplos/tp3/revisar-entrega/revisar_tp3.py "$PB_DIR/"
cp -r pb-a14/exemplos/aula13-instancia "$PB_DIR/"
cp -r pb-a14/exemplos/aula13-instancia/aula13_instancia "$PB_WS/src/"
cd "$PB_WS" && colcon build --symlink-install --packages-select aula13_instancia
source install/setup.bash
```

!!! warning "Você já tem a pasta da Aula 13 — e é por isso que o `rm -rf` está aí"
    `cp -r origem destino/` quando `destino/origem` **já existe** não substitui: ele copia **para dentro**, e você fica com `src/aula13_instancia/aula13_instancia`. O `colcon` continua compilando a versão antiga, o launch sobe, e os argumentos novos (`saida:=`, `rviz:=`) simplesmente **não existem** — sem erro nenhum. Para conferir qual versão está instalada:

    ```bash
    ros2 launch aula13_instancia instancia.launch.py --show-args
    ```

    Tem de listar `metodo`, `saida`, `alpha`, `rviz`, `pasta` e `fps`. Se listar menos, é a versão antiga.

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Abriu um terminal novo? Elas se perderam — e sem essa linha, `cd "$PB_DIR"` viraria `cd /`, que não falha dizendo o que faltou.

---

## Item 1 — O launch principal

> *Desenvolva o arquivo `bringup.launch.py` que inicialize em sequência: Gazebo com o mundo do projeto, Robot State Publisher com o URDF do robô, RViz2 com configuração salva (`.rviz`) e todos os nós de percepção dos TPs anteriores. Carregue todos os parâmetros via YAML. Execute com um único comando e documente com captura de tela.*

**O que o avaliador procura:** um arquivo só, que sobe tudo, com os parâmetros fora do código.

**Onde trava, e são sempre as mesmas três:**

**O `.rviz` que não está no repositório.** O launch aponta para `rviz/projeto.rviz`, funciona na sua máquina, e no clone do avaliador o RViz2 abre vazio — ou nem abre. Salve a configuração (`File → Save Config As`) **dentro do repositório** e commite.

**Os parâmetros ainda no código.** O enunciado diz "todos os parâmetros via YAML". Número cravado em `.py` é o que a Aula 10 chamou de YAML lido e descartado em silêncio: confira que o valor do arquivo **chega** ao nó.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 param get /seu_no seu_parametro      # tem de devolver o valor do YAML, não o do código
```

**Dois `bringup.launch.py` no repositório.** Um na raiz, outro numa pasta antiga. Nem você nem o avaliador sabem qual o `ros2 launch` vai pegar. Deixe um.

!!! danger "Use o Gazebo Fortress — e entenda por quê, porque a razão se repete"
    O enunciado cita **Harmonic**. **Para esta disciplina, a versão é o Fortress**, e isso vale como decisão de turma: ninguém perde ponto por entregar com ele.

    O motivo é **alinhamento de versões**. Cada distribuição do ROS 2 é construída e testada contra **uma** versão do Gazebo: o par do Humble é o **Fortress**, e é ele que vem de `ros-humble-ros-gz`, mantido e testado junto com a distribuição. O Harmonic com Humble existe, mas por pacotes **não oficiais** que **conflitam** com os `ros-humble-ros-gz*` já instalados — a própria documentação do Gazebo marca a combinação como *"possible, but use with caution"* e diz que **não a recomenda para iniciantes**.

    ```bash
    sudo apt install -y ros-humble-ros-gz      # o par do Humble; o comando é `ign gazebo`
    ```

    **Se você já tem Harmonic rodando**, siga com ele e escreva isso no relatório. O que não vale é trocar de versão a três dias da entrega: o conflito derruba o que funciona, e você passa a quinta-feira consertando ambiente em vez de escrevendo.

!!! warning "Alinhamento de versões — a mesma falha, em três lugares diferentes"
    Esta é a terceira vez no semestre que versões desalinhadas quebram alguma coisa **sem dizer que foi versão**:

    | O par que tem de bater | O que acontece quando não bate |
    |---|---|
    | ROS 2 Humble ↔ Gazebo **Fortress** | pacotes conflitantes, e o que já funcionava para de subir |
    | `cv_bridge` do apt ↔ **NumPy 1.x** e **OpenCV 4.5.4** | `_ARRAY_API not found`, `KeyError: 16`, nós morrendo na importação |
    | o código do exemplo ↔ a versão do OpenCV | `TypeError` em função que mudou de retorno entre a 4 e a 5 |

    A regra que sai disso, e que vale para o resto do curso: **o Python do sistema é território do `apt`**, e tudo o que não vier do apt vai para um ambiente `uv` com `--system-site-packages`. Quando algo quebrar de um jeito que não faz sentido, a primeira pergunta é *"o que mudou de versão aqui?"*.

**Como provar:** rode o comando único, tire o print com Gazebo (ou o seu simulador) e o RViz2 abertos, e salve em `docs/evidencias/tp3/bringup.png`.

---

## Item 2 — TFs e SLAM

> *Lance o SLAM Toolbox integrado ao ROS 2 e visualize no RViz2 o mapa sendo construído em tempo real, as TFs do robô (`base_link`, `odom`, `map`) e o scan com sensores simulados. Capture o TF tree completo com `ros2 run tf2_tools view_frames` e explique cada frame de referência no relatório.*

**O que o avaliador procura:** o `frames.pdf` com uma árvore só, e — isto é o que separa nota — **um parágrafo por frame**, dizendo quem o publica e o que ele significa.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/docs/evidencias/tp3" && ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo map odom        # a correção do SLAM, diferente de zero
```

**O que escrever sobre cada frame** — é literalmente o que o enunciado pede com a palavra *explique*:

| Frame | Quem publica | O que significa |
|---|---|---|
| `map` | o SLAM | o referencial fixo do mundo; não desliza, mas dá saltos quando o laço fecha |
| `odom` | quem integra a odometria | contínuo e suave, e **erra acumulando** — a deriva que vocês mediram |
| `base_link` | a cadeia do URDF | o corpo do robô; a raiz do seu modelo |
| `laser`, `camera`… | o `robot_state_publisher`, a partir do URDF | onde cada sensor está **em relação ao corpo** |

E a frase que vale a nota inteira do item: **`map → odom` é o erro acumulado da odometria com o sinal trocado** — por isso ele existe, e por isso quem publica é o SLAM, não você.

**Onde trava:** PDF vazio (o launch não estava rodando — TF é fluxo, não arquivo), duas árvores (um frame sem pai), dois `odom` (o placeholder não saiu: falta `map_odom:=false` ou equivalente), e o mapa salvo com o launch já fechado — o mapa vive na memória do nó.

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/maps" && cd "$PB_DIR/maps" && \
  ros2 run nav2_map_server map_saver_cli -f mapa     # COM o launch ainda no ar
```

---

## Item 3 — Segmentação semântica com YOLO

> *Aplique YOLO em imagens ou vídeo do ambiente do seu projeto para segmentação por instância. Exiba as máscaras coloridas por classe com transparência 0,5 sobrepostas ao frame. Publique a imagem segmentada em um tópico ROS 2 `/vision/segmented` para visualização no RViz2.*

São **três exigências separadas**, e a segunda é a que mais some na correção: máscaras **por classe**, com **alpha 0,5**, **sobrepostas ao frame** — não a máscara sozinha, não uma cor por objeto.

O exemplo da Aula 13 faz as três:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && source install/setup.bash
ros2 launch aula13_instancia instancia.launch.py saida:=classe_alpha alpha:=0.5
```

E, para rodar com o **YOLO** que o enunciado pede, o modelo vive num ambiente `uv` e o nó empresta o `site-packages` dele:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
uv venv --system-site-packages .venv-yolo
uv pip install --python .venv-yolo/bin/python ultralytics

PYTHONPATH="$PWD/.venv-yolo/lib/python3.10/site-packages:$PYTHONPATH" \
  ros2 launch aula13_instancia instancia.launch.py metodo:=modelo saida:=classe_alpha
```

O `--system-site-packages` é o que faz isso funcionar: o ambiente enxerga o `rclpy` do sistema, e o `PYTHONPATH` devolve o `ultralytics` ao nó. **Nunca** `pip install` sem ambiente — ele cai em `--user`, troca o NumPy e o OpenCV do sistema e derruba o `cv_bridge`.

**Ver no RViz2**, que é o que o enunciado pede (o `rqt_image_view` é atalho, não entrega):

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
rviz2 -d "$PB_WS/src/aula13_instancia/rviz/segmentacao.rviz"
```

!!! warning "A imagem não aparece no RViz2 e não há erro nenhum"
    É QoS. Tópico de imagem costuma ser publicado como **Best Effort**; se o display do RViz2 estiver em **Reliable**, os dois não se encontram e **nada é dito**. No display `Image`, abra `Topic → Reliability Policy` e ponha `Best Effort`. Confirme antes que há publicador: `ros2 topic hz /vision/segmented`.

**Como adequar ao seu projeto:** o YOLO pré-treinado conhece as 80 classes do COCO — não conhece "peça vermelha do meu projeto". Se o seu domínio não está no COCO, você tem três saídas defensáveis, e todas valem desde que **escritas**: usar as classes do COCO que existirem na sua cena; votar a classe pela cor dentro da máscara do modelo; ou usar o detector clássico e dizer, com a tabela da Aula 13, por que ele ganhou no seu caso.

---

## Item 4 — Arquitetura de percepção veicular

> *Identifique em um veículo real ou diagrama os protocolos CAN e Ethernet presentes, os tipos de sensores e descreva como cada um seria integrado ao pipeline ROS 2 do projeto. Relacione essa análise com as escolhas de sensores do seu próprio projeto.*

**Este item não tem código.** É texto, e é onde a maioria vai perder ponto por entregar três parágrafos genéricos de internet. O enunciado pede quatro coisas; entregue as quatro, nesta ordem, em `docs/evidencias/tp3/veicular.md`.

### 1. Os barramentos, e por que são dois

| | **CAN** | **Ethernet automotiva** |
|---|---|---|
| Para que serve | controle: powertrain, freios, portas, painel | dados: câmera, LiDAR, atualização de software |
| Mensagem | curta (8 bytes no CAN clássico; até 64 no CAN FD) | pacote grande, pilha IP completa |
| Quem fala quando | todos escutam; a prioridade está no identificador | comutada, ponto a ponto |
| Por que existe | previsível e barato, cabo de dois fios | banda que câmera e LiDAR exigem |
| Onde aparece | ECUs de chassi e corpo | 100BASE-T1 / 1000BASE-T1, um par trançado |

A frase que mostra que você entendeu: **o CAN é escolhido por previsibilidade, não por velocidade; a Ethernet entra onde a banda do sensor não cabe no CAN.** Uma câmera de 1080p não passa por um barramento de 8 bytes por mensagem — e um comando de freio não precisa de banda, precisa de chegar na hora.

### 2. Os sensores, por família

Câmera (imagem densa, barata, sofre com luz), LiDAR (geometria direta, cara, sofre com chuva e superfície espelhada), radar (velocidade radial direta, atravessa chuva, baixa resolução), ultrassom (centímetros, estacionamento), IMU (aceleração e giro a alta taxa, deriva), GNSS (posição absoluta, falha em túnel e entre prédios), e os encoders das rodas (a odometria que vocês já conhecem, e cuja deriva vocês mediram).

### 3. Como cada um entraria no seu pipeline ROS 2

É aqui que o item deixa de ser cópia. Para cada sensor, três linhas: **o driver, o tópico e o tipo de mensagem, e o que acontece com o tempo e a TF**.

| Sensor | Entra no ROS 2 como | Tópico e tipo | O cuidado |
|---|---|---|---|
| Câmera | driver USB/GigE → `image_transport` | `/camera/image_raw`, `sensor_msgs/Image` | QoS *sensor data*; comprimir antes de gravar bag |
| LiDAR | driver do fabricante | `/scan` (`LaserScan`) ou `/points` (`PointCloud2`) | TF do sensor ao `base_link` precisa estar certa |
| Radar | driver CAN → mensagens do domínio | tópico próprio, `.msg` do projeto | taxa baixa; cuidado ao casar com a câmera |
| IMU | driver serial/I²C | `/imu/data`, `sensor_msgs/Imu` | alta taxa; é o que suaviza a odometria |
| GNSS | driver NMEA | `/fix`, `sensor_msgs/NavSatFix` | referencial diferente do `map`: precisa de conversão |
| CAN do veículo | SocketCAN → `ros2_socketcan` | `/from_can_bus`, `can_msgs/Frame` | decodificar o quadro é trabalho seu, com o DBC |

E os dois cuidados que valem para todos: **carimbo de tempo** (sensores diferentes chegam em instantes diferentes; sem sincronização a fusão mistura passado com presente) e **TF** (cada sensor mede no referencial dele; sem a transformada, dois sensores apontam para coisas diferentes achando que apontam para a mesma).

### 4. Relacione com o SEU projeto

O último parágrafo é o que o enunciado cobra com a palavra *relacione*, e é o que não dá para copiar: **quais sensores o seu projeto usa, em que barramento cada um estaria num veículo real, e o que você teria de mudar no seu pipeline para que isso fosse verdade.** Três ou quatro frases honestas valem mais que duas páginas genéricas — inclusive dizer "o meu projeto é simulado e não tem barramento; se fosse embarcado, a câmera iria por Ethernet e os encoders por CAN" é uma resposta certa.

---

## Antes de postar: o roteiro de revisão

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR" && python3 revisar_tp3.py            # e, com o sistema no ar:
cd "$PB_DIR" && python3 revisar_tp3.py --ao-vivo
```

Ele percorre os quatro itens e a entrega e devolve **uma lista de lugares para olhar**, na ordem em que costuma compensar.

!!! danger "O roteiro não corrige, não valida e não garante nada"
    Ele **não é correção prévia**: não antecipa nota, não atesta que a entrega está pronta e não substitui a leitura do enunciado. **A referência é o enunciado do TP3, e a responsabilidade pela entrega é sua.**

    `achei` não quer dizer entregue certo. `não achei` não quer dizer entregue errado. Nos dois casos quer dizer: **vá olhar isso.**

    E o que ele marca com `olhe` é justamente o que mais pesa, porque nenhum comando alcança: se o launch **realmente sobe** o seu sistema, se o mapa é **do seu cenário**, se a explicação dos frames está correta, se a análise do item 4 fala do **seu** projeto. Isso é leitura — e quem lê sou eu.

    Sair daqui com a lista vazia não é ter terminado: é ter esgotado o que um script enxerga. O resto é reler o enunciado com o seu repositório aberto do lado.

## A entrega, na sexta 23/10

A ordem importa, e é a mesma dos TPs anteriores:

```bash
# ── herda as variáveis do bloco de preparação ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
git add -A && git commit -m "TP3: evidências e relatório"
git switch -c entrega-tp3 && git push -u origin entrega-tp3
git tag -a tp3 -m "entrega TP3" && git push origin tp3
```

Depois, **no Moodle**: o ZIP do código, o PDF do relatório e os links. A postagem no Moodle é a entrega oficial — sem ela não há nota, por mais completo que o repositório esteja. E o repositório é critério de avaliação, não anexo: histórico de commits, branch, tag e evidências commitadas.

!!! tip "Arquivo grande não vai para o Git"
    Vídeo, bag e peso de modelo vão para link público ou não listado, com o link no relatório e no README. Teste cada link numa janela anônima antes de postar: **se o avaliador não consegue abrir, não existe.**

## Para a próxima aula — 27/10

**Etapa 8 abre com navegação**, que ficou para trás três vezes e agora vira entrega: o Nav2 em cima do mapa que vocês salvaram, e o TP4 começando em 30/10. Chegue com o TP3 postado e a cabeça livre.
