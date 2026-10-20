# Exemplo — `aula13-instancia`

**Aula 13 · Etapa 7.** Da máscara à instância: a segmentação por cor da Aula 3 diz **onde** há objeto, não **quantos**. Quando duas peças se encostam, a componente conexa funde as duas numa instância só — e não dá erro nenhum: devolve uma contagem plausível. Este exemplo torna isso **mensurável**, e cobre o gate **G3.4** do TP3.

```
aula13-instancia/
├── cena.py             # gera cena/ com 12 quadros + verdade POR INSTÂNCIA
├── instancia.py        # carregador: reexporta o algoritmo que mora no pacote
├── avaliar.py          # a régua — conta, casa por IoU, acusa fusão e divisão
├── testar.py           # defeitos sintéticos conhecidos, para confiar na régua
└── aula13_instancia/   # o pacote ROS 2 (é a evolução do aula03-visao)
    ├── aula13_instancia/instancia.py   # ← o algoritmo mora AQUI, uma vez só
    ├── aula13_instancia/segmentador_instancia.py
    ├── aula13_instancia/publicador_cena.py
    ├── config/instancia.yaml
    ├── rviz/segmentacao.rviz          # display Image já em Best Effort
    └── launch/instancia.launch.py
```

O fluxo, offline e dentro do ROS 2, é o mesmo miolo:

```
                       ┌──────────────────────────────────┐
cena.py ──> cena/ ──>  │ instancia.py                     │
                       │   cor_conectada  (Aula 3)        │ ──> avaliar.py ──> tabela + figura
/camera/image_raw ──>  │   cor_watershed  (separa)        │
                       │   modelo         (YOLOv8-seg)    │ ──> /vision/segmented
                       └──────────────────────────────────┘      /vision/instancias
```

## O que o enunciado do TP3 pede, item 3

| O que o enunciado pede | O que o exemplo faz | O comando |
|---|---|---|
| aplicar **YOLO** em imagem ou vídeo do seu ambiente, para **segmentação por instância** | o detector `modelo` é um adaptador para o `ultralytics` YOLOv8-seg e obedece ao mesmo contrato dos outros dois — entra como mais uma linha da tabela, não como ato de fé | `ros2 launch aula13_instancia instancia.launch.py metodo:=modelo` (com o venv — [duas formas](#rodar-o-modelo-dentro-do-ros-2)) |
| máscaras coloridas **por classe**, com **transparência 0,5**, sobrepostas ao frame | `sobrepor_classes`: uma cor por classe, mistura 0,5 **só onde há máscara**, contorno sólido por instância e o nome da classe com fundo atrás. É o padrão `saida: classe_alpha` | `ros2 launch aula13_instancia instancia.launch.py` |
| publicar em **`/vision/segmented`** para ver no **RViz2** | o tópico é o mesmo de sempre; o pacote traz um `rviz/segmentacao.rviz` com o display `Image` apontado e já em **Best Effort** | `ros2 launch aula13_instancia instancia.launch.py rviz:=true` |

**O padrão mudou.** Até esta versão, `/vision/segmented` saía sempre com uma cor por **instância**; agora sai com a cor por **classe** e transparência, porque é isso que o enunciado pede. A figura antiga continua a uma palavra de distância — `saida:=instancia` — e continua sendo a que mostra a fusão da Aula 13 na tela. São duas perguntas diferentes, e o nó agora responde às duas:

| `saida` | a cor diz | serve para |
|---|---|---|
| `classe_alpha` (padrão) | **de que tipo** é o objeto | a entrega do TP3: classe + transparência sobre o frame |
| `instancia` | **qual** objeto é | ver a fusão: duas peças encostadas de uma cor só |
| `mascara` | de que tipo, sem o frame | conferir a máscara quando o fundo polui a vista |

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y python3-opencv python3-numpy

cd /tmp && rm -rf pb-a13 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a13 && \
  # a copia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x),
  # e o colcon passa a compilar a versao velha sem dizer nada
  rm -rf "$PB_DIR/aula13-instancia" "$PB_WS/src/aula13_instancia" && \
  cp -r pb-a13/exemplos/aula13-instancia "$PB_DIR/" && \
  cp -r pb-a13/exemplos/aula13-instancia/aula13_instancia "$PB_WS/src/"
```

Nada de `pip`. O único detector que precisaria dele é opcional e está explicado mais abaixo.

## Medir, sem ROS 2 e sem câmera

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
python3 cena.py
python3 avaliar.py
```

O `cena.py` desenha 12 quadros com **10 peças cada**, das quais **7 estão encostadas em alguma outra**, e grava a verdade duas vezes: um `verdade.json` com classe, centroide, área e bbox, e um `rotulosNNN.png` em que **cada pixel carrega o id inteiro da sua instância**. É a representação mais simples que permite IoU por instância — sem polígono, sem RLE, e conferível a olho: abra o PNG de rótulos e você está olhando para a própria verdade.

## O resultado, e o que ele conta

```
detector         verdades previstas casadas erro cont. IoU medio fusoes divisoes  classe ms/quadro
---------------- -------- --------- ------- ---------- --------- ------ --------  ------ ---------
cor_conectada         120        72      48      40.0%      0.86     48        0  100.0%     16.04
cor_watershed         120       120     120       0.0%      0.94      0        0  100.0%     29.96
modelo                120        17       4      85.8%      0.89     15        0    0.0%    148.25
```

Tudo é **determinístico** menos a coluna de tempo — rodando de novo, sai idêntico. O tempo é da sua máquina; o que viaja é a razão entre os dois (~2×).

Quatro leituras, e a terceira é a que vale a aula.

**O erro não dá erro.** O `cor_conectada` não levanta exceção, não loga aviso, não devolve `None`. Ele devolve **72** onde havia 120, com toda a convicção, e um `/vision/contagem` publicando um número plausível. Num robô que conta frutos colhidos, isso é uma subcontagem de 40% que ninguém percebe até alguém conferir a mão.

**A máscara era a mesma.** Os dois detectores partem do mesmo `cv2.inRange` e da mesma morfologia. O que mudou foi a **leitura** da máscara: `connectedComponentsWithStats` responde "quantas manchas", e a pergunta era "quantos objetos". As 48 fusões são exatamente os 12 quadros × (1 + 1 + 2) grupos colados.

**IoU médio alto pode ser a pior notícia da tabela.** O `cor_conectada` marca **0,86** — ótimo, até você ler a coluna ao lado: **48 casadas de 120**. O IoU médio só fala dos pares que casaram; ele não sabe nada de quem ficou de fora, e por isso ele nunca viaja sozinho. Um detector que acha uma peça só, perfeitamente, marca IoU 1,00.

**Separar custa, e dá para dizer quanto.** O watershed custa ~2× o tempo e devolve máscaras um pouco menores (IoU 0,94 contra 0,97 que o conectado tira nas peças soltas), porque a linha de água consome ~1 px do perímetro de cada instância. Quem decide se vale é o domínio: para contar peças, vale sempre; para medir área de uma peça isolada, talvez não.

## Ver **onde** errou

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
python3 avaliar.py --imagem dif-instancia.png
python3 avaliar.py --imagem dif-quadro5.png --quadro 5
```

Uma linha por detector, verdade e previsão lado a lado. Verde onde casou, **vermelho onde fundiu**, âmbar onde dividiu, cinza no que sobrou de um lado só — com a legenda embutida, para a figura ir ao relatório do TP3 sozinha.

O par vermelho no painel do `cor_conectada` é o argumento inteiro da aula numa imagem: duas peças, uma cor. **O número diz quanto; a figura diz onde.**

## O que a cena tem de propósito

| Grupo | O que é | O que ele quebra |
|---|---|---|
| 3 peças soltas | círculo e retângulos separados | nada; é a linha de base — todo detector acerta |
| 2 pares colados | círculo+círculo e retângulo+retângulo | `connectedComponents` conta 1 onde há 2 |
| 1 trio colado | corrente de três círculos | conta 1 onde há 3 — e registra **2** fusões |

As peças encostadas se sobrepõem poucos pixels: o gargalo que sobra tem ~18 px, **grosso o bastante para sobreviver à abertura morfológica** (senão o problema sumiria sozinho e a aula não teria assunto) e **fino o bastante para a transformada de distância enxergar dois núcleos**.

## Onde o watershed **não** serve

Vale dizer isto em sala, porque é o tipo de limite que o aluno descobre sozinho, no TP3, no pior dia: o método depende de existir um **gargalo**. Duas peças retangulares encostadas **face contra face** não têm gargalo nenhum — a transformada de distância não tem vale, e **nenhum** valor de `fracao_semente` separa as duas. É por isso que, na cena, o par de retângulos se encosta pelo **canto**.

Quando o seu domínio tem contato face a face (caixas numa esteira, livros numa pilha), o caminho não é ajustar a fração: é mudar de evidência — profundidade, borda, ou um modelo treinado nas suas peças.

## O terceiro detector: um modelo pré-treinado

O `modelo` é um adaptador para o `ultralytics` YOLOv8-seg e obedece ao **mesmo contrato** dos outros dois. Ele é opcional em tempo de execução: sem o pacote instalado, `avaliar.py` pula a linha e diz exatamente o que fazer — nunca `sudo pip`, que reescreve a biblioteca que os nós ROS 2 usam.

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"

command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
uv venv --system-site-packages .venv-yolo
uv pip install --python .venv-yolo/bin/python ultralytics
.venv-yolo/bin/python avaliar.py            # agora com a linha do modelo
```

!!! danger "Nunca `pip install` fora do ambiente — é o que quebra o ROS 2"
    Repare que a receita acima **não ativa nada**: o `uv pip install --python` diz onde instalar, então não existe "esqueci de ativar". Essa é a razão de ser da regra.

    Um `pip install` sem ambiente ativo cai em `--user` e instala **numpy 2, opencv-python 5 e setuptools 84** em `~/.local`, por cima do que o ROS 2 usa. O estrago não se parece com a causa: `colcon build` falha com `option --uninstall not recognized`, o `cv_bridge` morre com `_ARRAY_API not found` ou `KeyError: 16`, e código que funcionava passa a dar `TypeError` porque o OpenCV 5 mudou retornos. O [cheatsheet de OpenCV](../../cheatsheets/opencv.md) já descreve esse par.

    Se acontecer, o desfazer é uma linha, e nada se perde:

    ```bash
    mv ~/.local/lib/python3.10/site-packages ~/.local/lib/python3.10/site-packages.guardado
    ```

    E o venv só nasce se o `python3.10-venv` estiver instalado; sem ele, o comando falha e é fácil "resolver" rodando o `pip` solto — que é exatamente a armadilha.

Medido nesta cena, o resultado é mais duro do que se espera de um modelo moderno:

```
modelo                120        17       4      85.8%      0.89     15        0    0.0%    148.25
```

**Dezessete instâncias onde havia 120, zero por cento de acerto de classe, cinco vezes mais lento — e o segundo melhor IoU médio da tabela.** Essa última parte não é ironia: as quatro instâncias que ele casou, casou bem, e o IoU médio só sabe falar delas. É a demonstração mais limpa do que esta aula inteira persegue — **o maior IoU da tabela pode ser do pior detector**.

E aqui está a parte honesta, que vale documentar porque o aluno vai cair nela: **o modelo não conhece as classes do seu domínio**. Ele conhece as 80 do COCO — pessoa, carro, cachorro. "Peça vermelha" não está lá. Então ele tende a achar as instâncias certas (inclusive as encostadas, que é onde o clássico falha) e **errar a classe**, enquanto o método clássico **acerta a classe e erra a separação**. Por isso a classe sai prefixada com `coco:` e o acerto de classe despenca na tabela: o número torna a conversa concreta.

O híbrido costuma ser a resposta certa no TP3 — o modelo acha a instância, a cor vota a classe dentro da máscara. São três linhas, e já estão escritas: `cfg['classe_por_cor'] = True`.

### Rodar o `modelo` dentro do ROS 2

Aqui mora um atrito real, e ele não é do exemplo: o `ultralytics` vive no venv, e os nós ROS 2 rodam com o **python do sistema** — o do `/usr/bin/python3`. Instalar no venv não muda nada para o nó. Por isso o venv da disciplina nasce com `--system-site-packages`: ele **enxerga** o `rclpy`, o `cv_bridge` e o OpenCV do apt, e o caminho inverso (o nó enxergar o venv) é o que as duas receitas abaixo resolvem.

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
uv venv --system-site-packages .venv-yolo
uv pip install --python .venv-yolo/bin/python ultralytics
```

**A) Emprestando o `site-packages` do venv ao `ros2 launch`.** Continua tudo igual — `ros2 launch`, `ros2 run`, `ros2 param` —, só que o python do sistema passa a achar o `ultralytics`:

```bash
PYTHONPATH="$PWD/.venv-yolo/lib/python3.10/site-packages:$PYTHONPATH" \
  ros2 launch aula13_instancia instancia.launch.py metodo:=modelo
```

**B) Rodando o executável instalado com o python do venv.** Sem `ros2 run` no meio: o `colcon` instala o nó como um script, e qualquer python que enxergue o `rclpy` pode executá-lo. Como o venv foi criado com `--system-site-packages`, ele enxerga:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
.venv-yolo/bin/python "$PB_WS/install/aula13_instancia/lib/aula13_instancia/segmentador_instancia" \
  --ros-args -p metodo:=modelo
```

A (A) é a que mantém o launch inteiro de pé e costuma ser a escolha no TP3; a (B) é a que dá o diagnóstico mais limpo quando a (A) não funciona, porque não há `PYTHONPATH` nenhum para desconfiar. Se a versão do python do seu venv não for `python3.10`, o caminho da (A) muda junto — confira com `ls .venv-yolo/lib/`.

!!! warning "Estas duas linhas não foram executadas aqui"
    O exemplo foi montado num ambiente **sem ROS 2**, então as duas receitas acima **não** foram testadas — nem elas, nem o `rviz:=true`, nem o `.rviz`. O que está testado, e roda em qualquer máquina com OpenCV e NumPy do apt, é a parte sem ROS 2: `cena.py`, `avaliar.py` e os oito grupos do `testar.py`, inclusive a sobreposição por classe. **Confira as duas na sua máquina** antes de depender delas na véspera da entrega.

## Rodar dentro do ROS 2 (o gate G3.4)

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && colcon build --symlink-install --packages-select aula13_instancia && \
  source install/setup.bash
```

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
ros2 launch aula13_instancia instancia.launch.py \
  pasta:="$PB_DIR/aula13-instancia/cena" rviz:=true
ros2 launch aula13_instancia instancia.launch.py \
  pasta:="$PB_DIR/aula13-instancia/cena" metodo:=cor_watershed saida:=instancia
```

Em outro terminal:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source "$PB_WS/install/setup.bash"
ros2 topic echo /vision/instancias --once
ros2 param set /segmentador_instancia saida instancia      # troca a figura em voo
ros2 run rqt_image_view rqt_image_view /vision/segmented   # alternativa ao RViz2
```

O `/vision/segmented` publica, por padrão, as máscaras coloridas **por classe** com transparência 0,5 sobre o frame — o que o item 3 do enunciado pede. Com `saida:=instancia` ele volta a publicar uma cor por **instância**, que é a figura da Aula 13: duas peças vermelhas encostadas pintadas de uma cor só é um erro que se vê na tela, antes de qualquer métrica. Repare que, na saída por classe, essa fusão **volta a ficar escondida** — a cor diz a classe, e a classe das duas é a mesma. É por isso que a sobreposição desenha o **contorno de cada instância** por cima: sem ele, duas peças da mesma classe viram uma mancha única.

### Ver no RViz2

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source "$PB_WS/install/setup.bash"
rviz2 -d "$PB_WS/install/aula13_instancia/share/aula13_instancia/rviz/segmentacao.rviz"
```

Ou na mão, que é o que o enunciado cobra saber fazer: **Add** → **By display type** → **Image** → em `Topic`, `/vision/segmented`. (O display **Camera** também mostra imagem, mas exige `camera_info` e um frame na TF; este exemplo não publica nenhum dos dois, então use o **Image**.)

!!! danger "QoS: a imagem não aparece e **não há erro**"
    Este nó publica imagem como dado de sensor, com **`BEST_EFFORT`**. Um display que peça `RELIABLE` — que é o padrão do RViz2 — simplesmente **não recebe nada**: o painel fica cinza, o `ros2 topic hz` mostra o tópico publicando normalmente, e **não aparece mensagem de erro em lugar nenhum**. QoS incompatível não dá erro, dá silêncio.

    No display `Image`, abra `Topic` e ponha **Reliability Policy: Best Effort**. O `rviz/segmentacao.rviz` deste pacote já vem assim — e é por isso que ele existe.

    Para confirmar de qual lado está o problema, antes de mexer em qualquer coisa:

    ```bash
    ros2 topic hz /vision/segmented      # publica? então o problema é do assinante
    ros2 topic info /vision/segmented --verbose    # mostra o QoS dos dois lados
    ```

Mais duas coisas que o RViz2 faz e assustam sem motivo: ele avisa **`Fixed Frame [camera] does not exist`**, porque este exemplo publica imagem mas não publica TF — o display `Image` não transforma nada, e a imagem aparece do mesmo jeito; e o painel só acorda quando chega o **primeiro** quadro, então com `fps:=1.0` a espera é de um segundo, não um defeito.

Suba com `cor_conectada`, conte as cores; suba com `cor_watershed`, conte de novo. **A contagem que aparece no tópico tem de bater com a coluna `previstas` da tabela** — são os mesmos quadros e o mesmo código. Quando não bate, o problema está na fronteira ROS 2 (QoS, parâmetro, encoding), não no algoritmo, e isso já é meio diagnóstico pronto.

!!! note "Uma implementação, dois usos"
    O algoritmo mora em `aula13_instancia/aula13_instancia/instancia.py`, dentro do pacote — tem de morar lá, porque depois do `colcon build` o nó só enxerga o que está dentro dele. O `instancia.py` da raiz é um carregador que reexporta o mesmo módulo, e é por isso que `avaliar.py` mede **o código que vai rodar**. Duas cópias divergiriam num limiar por volta da terceira semana, e a medida deixaria de valer para o nó sem ninguém perceber.

## O que cada arquivo faz

| Arquivo | Papel |
|---|---|
| `cena.py` | desenha `cena/` com verdade por instância; `--quadros`, `--semente`, `--pasta` |
| `instancia.py` (raiz) | carregador de 3 linhas: acha o pacote e reexporta os detectores |
| `aula13_instancia/.../instancia.py` | **o algoritmo**: `cor_conectada`, `cor_watershed`, `modelo`, `detectar` — e as duas figuras, `sobrepor_classes` (por classe, com alpha) e `pintar_instancias` (por instância) |
| `avaliar.py` | a régua: casamento por IoU, erro de contagem, fusões, divisões, `--imagem` |
| `testar.py` | confere a régua com defeitos que você mesmo injetou |
| `.../segmentador_instancia.py` | o nó do gate G3.4: `/vision/segmented` + `/vision/instancias`; `saida` escolhe a figura |
| `.../publicador_cena.py` | publica `cena/` em `/camera/image_raw` — launch sobe sem câmera |
| `.../ponte.py` | `cv_bridge` quando funciona, conversão manual quando não (igual à Aula 3) |
| `config/instancia.yaml` | método, **`saida`**, **`alpha`**, faixas HSV por classe, área mínima |
| `rviz/segmentacao.rviz` | display `Image` em `/vision/segmented`, já em **Best Effort** |
| `launch/instancia.launch.py` | sobe os dois nós; aceita `metodo:=`, `saida:=`, `alpha:=`, `rviz:=true` |

## Conferir a régua antes de confiar nela

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
python3 testar.py
```

Oito grupos, todos com a resposta sabida de antemão: peças separadas, peças coladas, IoU comparado, um detector que **super-segmenta de propósito** (para provar que a régua acusa divisão, e não só fusão), a figura que muda quando o resultado muda, a cena ausente, o modelo ausente — e a sobreposição por classe. Termina em `todos os testes passaram.` e sai com código 0 ou 1 — dá para pendurar no CI do seu repositório.

O oitavo grupo mede o que o item 3 do enunciado afirma, e mede como afirmação verificável, não como impressão de tela: a imagem sai do **tamanho do frame**; **fora** da máscara o pixel é o original **byte a byte** (só o rótulo escreve por cima, porque é anotação); **dentro** da máscara todo pixel mudou, e mudou na proporção exata de `alpha` — `0,5 × frame + 0,5 × cor da classe`, conferido pixel a pixel; e duas instâncias **da mesma classe encostadas**, que sem contorno são uma mancha de uma cor só, ficam separadas pela linha do contorno.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `nao achei a verdade da cena` | rode `python3 cena.py` antes — a mensagem traz o comando |
| `nao achei o pacote aula13_instancia` | rode de dentro do material, ou copie o pacote para `$PB_WS/src` |
| `No module named 'cv2'` | `sudo apt install python3-opencv python3-numpy` |
| as duas linhas da tabela dão o mesmo número | a cena não tem peça encostada; confira o `--semente` e o `COLADO` |
| `cor_watershed` conta **mais** do que existe | `fracao_semente` alto demais: o núcleo de uma peça virou dois |
| `cor_watershed` conta **igual** ao conectado | `fracao_semente` baixo demais, ou não há gargalo (contato face a face) |
| máscara vazia, zero instâncias | faixa HSV chutada; meça com o `amostrar_hsv` da Aula 3 |
| `/vision/instancias` não publica | nada em `/camera/image_raw`: confira `pasta:=` no launch |
| o nó vê menos instâncias que a tabela | QoS: o `rqt` pede RELIABLE e o nó publica BEST_EFFORT |
| o RViz2 não mostra a imagem **e não dá erro** | o display `Image` está em RELIABLE; ponha **Best Effort** (ou use `rviz:=true`) |
| `Fixed Frame [camera] does not exist` no RViz2 | o exemplo não publica TF; o display `Image` não transforma nada e a imagem aparece mesmo assim |
| a saída ficou com uma cor por instância | `saida` está em `instancia`; o padrão do TP3 é `classe_alpha` |
| o log avisa `saida='...' nao existe` | valor fora de `classe_alpha \| instancia \| mascara`; o nó cai no padrão e segue |
| peça vermelha fica **cinza** na sobreposição | é a mistura a 50% com a cor complementar da camada; fixe a cor da classe em `CORES_CLASSE` |
| `ultralytics` instalado e o nó não acha | o nó roda com o python do sistema; veja as duas receitas em *Rodar o `modelo` dentro do ROS 2* |
| `Wrong parameter type` ao lançar | argumento de launch chega como texto; use `ParameterValue` (já está no launch) |
| `KeyError: 16` na primeira imagem | `cv_bridge` quebrado; o `ponte.py` cai sozinho no plano B e diz o motivo no log |

## Como adequar ao seu projeto

**Troque as classes de cor pelas do seu domínio.** Tudo que o detector sabe sobre cor está em seis inteiros por classe, no `config/instancia.yaml` — e em nenhum outro lugar:

```yaml
classes: [amarelo, laranja]
faixa:
  amarelo: [20, 35, 20, 35, 110, 70]     # h1_min h1_max h2_min h2_max s_min v_min
  laranja: [8, 20, 8, 20, 140, 80]
```

Não chute esses números: meça com o `amostrar_hsv` da Aula 3, no **seu** objeto e com a **sua** iluminação. Classe nova é declarada em tempo de execução pelo nó, então não há código a mudar.

**Mande a figura do jeito que o seu relatório precisa.** `saida` e `alpha` são parâmetros, então nada disso é recompilação:

```bash
ros2 param set /segmentador_instancia saida classe_alpha
ros2 param set /segmentador_instancia alpha 0.35      # camada mais discreta
```

A cor de cada classe é estável (a mesma em toda execução, para duas capturas de tela serem comparáveis) e é escolhida a partir do **nome** da classe. Ela **não** copia a cor do objeto de propósito: misturar vermelho com vermelho a 50% devolve vermelho, e a máscara ficaria invisível exatamente onde precisa aparecer. Se quiser mandar na cor:

```python
from aula13_instancia import instancia
instancia.CORES_CLASSE['tomate_maduro'] = (40, 40, 210)      # BGR
```

**Troque o `Int32` pela sua `.msg`.** A contagem sai como `std_msgs/Int32` porque é o mínimo que o gate pede. O seu projeto provavelmente quer mais: id, classe, centroide e área de cada instância. O pacote de interfaces é o da Aula 6, e a troca é local — o `detectar()` já devolve exatamente esses campos:

```python
# no segmentador_instancia.py
from meu_projeto_interfaces.msg import Instancia, ListaInstancias

msg = ListaInstancias()
for i, inst in enumerate(instancias):
    x, y, w, h = inst['bbox']
    msg.itens.append(Instancia(id=i, classe=inst['classe'], area=inst['area'],
                               cx=inst['centroide'][0], cy=inst['centroide'][1],
                               x=x, y=y, largura=w, altura=h))
```

**Troque a cena sintética pela sua, quando tiver rótulo.** O `avaliar.py` não sabe de onde veio a verdade: ele lê `verdade.json` + `rotulosNNN.png`. Qualquer ferramenta de anotação que exporte máscara por instância serve — exporte nesse formato e a régua inteira continua valendo, inclusive a figura.

**Acrescente o seu detector.** Escreva uma função com a assinatura do contrato, registre no dicionário `DETECTORES`, e ela entra na tabela ao lado das outras. É assim que um modelo treinado nas suas peças deixa de ser ato de fé e vira uma linha comparável — que é o que o TP3 avalia: a métrica e a justificativa, não o modelo.

## Licença

MIT, como todo o diretório `exemplos/`.
