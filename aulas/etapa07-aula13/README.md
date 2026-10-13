# Aula 13 — Achar não é acertar

**Terça, 13/10/2026 · sala SJ205 · Etapa 7 (12/10–24/10)**

[:material-file-pdf-box: Slides da Aula 13 (PDF)](apresentacao-aula13.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula13-instancia`](../../exemplos/aula13-instancia/index.md){ .md-button }
[:material-code-tags: Exemplo `aula13-veicular`](../../exemplos/aula13-veicular/index.md){ .md-button }

## Cenas dos últimos episódios

**Na Aula 12** o `slam_toolbox` assumiu a aresta `map → odom`, vocês viram a correção crescer junto com a deriva e com o sinal trocado, salvaram o mapa com o launch ainda no ar e o mediram contra o cenário — cobertura e concordância, separadas de propósito. O bloco sobre navegação era o de folga declarado e cedeu pela segunda vez; ele volta hoje, no fim, e é de novo o que cede.

Quatro peças antigas voltam, e a segunda é a que a aula inteira cobra:

| De onde vem | O que era | Onde entra hoje |
|---|---|---|
| **Aula 3** — segmentação HSV | a máscara que diz onde há objeto | hoje ela continua certa e deixa de bastar |
| **Aula 9** — a régua declarada antes | medir em vez de achar que está bom | hoje a régua ganha uma coluna, e é ela que denuncia o resto |
| **Aula 10** — o contrato do detector | mesma assinatura, miolos trocáveis | três detectores de instância, intercambiáveis no mesmo arnês |
| **Aula 12** — medir contra a verdade | o mundo sintético tem verdade; o real não | hoje a verdade é pixel a pixel, e vale para imagem |

## A ideia da aula em uma frase

**Achar não é acertar — e a média não conta quem ficou de fora.**

Dois números dos exemplos de hoje bastam para provar as duas metades da frase:

- a segmentação por cor marca **IoU médio 0,86**, que é ótimo, com **48 instâncias casadas de 120**. O número alto é o retrato de quem sobrou;
- o detector de faixas acha **as duas faixas em 100% dos quadros com sombra**, e erra **49 pixels** na base da imagem. Achou as duas. Achou errado.

Nenhum dos dois levanta exceção, loga aviso ou devolve `None`. É a mesma família do YAML lido e descartado em silêncio, do `view_frames` que gera PDF vazio e dos dois publicadores da mesma aresta: **o erro não se apresenta como erro**. A diferença é que hoje ele se esconde *dentro da métrica* — que era justamente o instrumento que deveria encontrá-lo.

## Por que a aula está nesta ordem

Ordenada por **custo de perda**. O que vence antes vem primeiro; o bloco de folga vem por último e fica declarado de antemão.

| Bloco | O que você sai sabendo fazer | Prazo | Se faltar tempo |
|---|---|---|---|
| 1. Da máscara à instância | separar objetos que se encostam, e saber quando não dá | **18/10** | não pode cair |
| 2. A régua que acusa a fusão | medir instância: contagem, IoU, fusão e divisão | **18/10** | não pode cair |
| 3. Percepção veicular | rodar cor → borda → reta e dizer **qual etapa** quebrou | **20/10** | não pode cair |
| 4. O que a navegação acrescenta | dizer o que falta a um robô que só reage | 30/10 | **é o que cede** |

!!! danger "O mapa do TP3 vence quinta, 15/10"
    O **G3.3** — mapa persistido do seu cenário, o par `mapa.pgm` + `mapa.yaml` — vence **depois de amanhã**, e é pré-requisito do TP4 inteiro. Se ele ainda não está no repositório, resolva isso antes da tarefa de hoje: o caminho inteiro está na [página da Aula 12](../etapa06-aula12/index.md), e o `comparar_mapas.py` ficou na raiz do seu workspace de propósito, para sobreviver ao reboot.

## Objetivos

Ao final da aula você deve conseguir explicar por que uma máscara correta pode produzir uma contagem errada sem gerar erro nenhum; separar instâncias que se encostam com transformada de distância e watershed, e dizer em que situação esse método não tem o que fazer; medir uma segmentação por instância com quatro números em vez de um, sabendo o que cada um esconde; rodar a cadeia cor → borda → reta sobre uma cena de estrada e **atribuir a falha a uma etapa**, com evidência; e publicar a sua segmentação por instância em `/vision/segmented`, que é o que o TP3 cobra.

## Baixar o material desta aula

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

# 1) o que a aula usa — tudo do apt, nada de pip
sudo apt install -y python3-opencv python3-numpy python3-yaml
sudo apt install -y ros-humble-cv-bridge ros-humble-rqt-image-view

# 2) baixar o material (pode repetir sempre — o rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 3) os dois exemplos vão para DENTRO do seu projeto, não para /tmp:
#    a tarefa da semana é feita depois da aula, e /tmp some no reboot
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula13-instancia "$PB_DIR/"
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula13-veicular  "$PB_DIR/"

# 4) e o pacote ROS 2 vai para o workspace
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula13-instancia/aula13_instancia "$PB_WS/src/"
cd "$PB_WS" && colcon build --symlink-install --packages-select aula13_instancia
source install/setup.bash
```

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Abriu um terminal novo? Elas se perderam — e sem essa linha, `cd "$PB_DIR/aula13-instancia"` viraria `cd /aula13-instancia`, que falha dizendo outra coisa.

## Parte 1 — Da máscara à instância

A segmentação da Aula 3 responde **onde há objeto**. A pergunta do TP3 é outra: **quantos objetos há, e qual é cada um**. Entre as duas existe um passo que parece trivial e não é.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
python3 cena.py
python3 avaliar.py
```

A cena tem 12 quadros com 10 peças cada, e **7 delas encostam em alguma outra** — de propósito. O que sai:

```
detector         verdades previstas casadas erro cont. IoU medio fusoes divisoes  classe ms/quadro
cor_conectada         120        72      48      40.0%      0.86     48        0  100.0%     16.04
cor_watershed         120       120     120       0.0%      0.94      0        0  100.0%     29.96
```

**A máscara era a mesma nos dois.** Os dois partem do mesmo `cv2.inRange` e da mesma morfologia. O que mudou foi a **leitura** dela: `connectedComponentsWithStats` responde "quantas manchas existem", e a pergunta era "quantos objetos existem". Onde duas peças se tocam, há uma mancha e dois objetos.

E repare no que o primeiro detector faz quando erra: ele devolve **72** onde havia 120, com toda a convicção, e publica um número plausível. Num robô que conta frutos colhidos, é uma subcontagem de 40% que ninguém percebe até alguém conferir a mão.

### Separar o que se encosta

O `cor_watershed` usa a mesma máscara e acrescenta duas ideias:

1. a **transformada de distância** (`cv2.distanceTransform`) transforma a mancha num relevo: quanto mais longe da borda, mais alto. Dois objetos colados viram dois picos com um vale no meio;
2. os picos viram sementes, e o **watershed** (`cv2.watershed`) inunda o relevo a partir delas até as águas se encontrarem — e a linha onde se encontram é o corte.

!!! warning "Onde o watershed não serve, e vale saber hoje e não no dia da entrega"
    O método depende de existir **gargalo**. Duas peças retangulares encostadas **face contra face** não têm vale nenhum na transformada de distância, e **nenhum** valor de limiar separa as duas. Se o seu domínio tem contato face a face — caixas numa esteira, livros numa pilha —, o caminho não é ajustar o parâmetro: é mudar de evidência (profundidade, borda, ou um modelo treinado nas suas peças). O exemplo tem uma seção sobre isso.

## Parte 2 — A régua que acusa a fusão

Na Aula 9 a lição foi declarar a medida antes de olhar o resultado. Hoje ela ganha um capítulo: **uma medida só também mente**, e a que mente melhor é a média.

| O número | O que ele responde | O que ele esconde |
|---|---|---|
| erro de contagem | quantos objetos a mais ou a menos | nada sobre *quais*, nem sobre a forma |
| IoU médio dos casados | quão bem as instâncias encontradas se encaixam | **tudo** sobre as que não foram encontradas |
| fusões | quantas verdades caíram numa previsão só | o caso espelho |
| divisões | quantas previsões partiram uma verdade só | o caso espelho |

O `cor_conectada` marca IoU **0,86** — e a coluna ao lado diz **48 casadas de 120**. O IoU médio só fala dos pares que casaram; ele não sabe nada de quem ficou de fora. Um detector que achasse **uma** peça, perfeitamente, marcaria IoU 1,00.

E o terceiro detector, que é um modelo pré-treinado, leva o argumento ao extremo:

```
detector             verdades previstas casadas erro cont. IoU medio classe  ms/quadro
cor_conectada             120        72      48      40.0%      0.86 100.0%      16.0
cor_watershed             120       120     120       0.0%      0.94 100.0%      30.3
modelo (YOLOv8-seg)       120        17       4      85.8%      0.89   0.0%     148.2
```

**O maior IoU depois do watershed é do pior detector da tabela.** O modelo achou 17 instâncias onde havia 120, acertou **zero por cento** das classes — ele conhece as classes do COCO, não "peça vermelha do seu projeto" — e custa cinco vezes mais caro por quadro. E ainda assim marca 0,89, porque as quatro instâncias que ele casou, casou bem.

**É por isso que esse número nunca viaja sozinho.** Escreva isso no relatório do TP3 ao lado de qualquer média que você publicar.

### Ver onde errou, e não só quanto

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia"
python3 avaliar.py --imagem "$PB_DIR/docs/evidencias/tp3/instancia.png"
```

Uma linha por detector, verdade e previsão lado a lado: verde onde casou, **vermelho onde fundiu**, âmbar onde dividiu, com a legenda embutida na figura. O par vermelho no painel do `cor_conectada` é o argumento da aula inteira numa imagem — duas peças, uma cor. **O número diz quanto; a figura diz onde.**

### O mesmo miolo, agora publicando em `/vision/segmented`

O gate **G3.4** pede segmentação por instância publicando no tópico, com as classes do seu domínio. É o mesmo código que você acabou de medir:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && source install/setup.bash
ros2 launch aula13_instancia instancia.launch.py metodo:=cor_watershed
```

Em outro terminal:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && source install/setup.bash
ros2 topic echo /vision/instancias --once          # a contagem
ros2 run rqt_image_view rqt_image_view             # escolha /vision/segmented
```

A imagem publicada é colorida **por instância**, não por classe: duas peças vermelhas vizinhas saem em cores diferentes. É assim que se vê, olhando, que a separação aconteceu.

!!! tip "O algoritmo mora dentro do pacote, e isso não é detalhe"
    `avaliar.py` mede exatamente o módulo que o nó importa. Duas cópias divergiriam num limiar por volta da terceira semana, e a medida deixaria de valer para o nó **sem ninguém perceber** — que é o defeito que esta aula inteira persegue.

## Parte 3 — Percepção veicular, sem instalar simulador

O gate **G3.5** pede o módulo de percepção veicular rodando e documentado. A cadeia clássica tem três etapas, e **cada uma falha de um jeito diferente** — saber qual delas quebrou é a diferença entre consertar e chutar.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 cena_estrada.py
python3 avaliar_faixas.py
```

Cinco condições, 24 quadros cada, com a geometria das faixas conhecida:

| Condição | Achou as duas | Erro angular | Erro na base | Qual etapa quebrou |
|---|---|---|---|---|
| limpo | 100% | 0,15° | 0,8 px | — (linha de base) |
| sombra | **100%** | 5,8° | **49,6 px** | **reta**: a máscara inchou de 3.134 para 20.204 px e segmentos que não são faixa entraram nos grupos |
| apagada | 0% | — | — | **cor**: a máscara do lado esquerdo foi de 1.649 px para **zero** |
| noite | 0% | — | — | **borda**: a máscara passou (3.260 px) e o Canny devolveu **0 px** |
| faixa dupla | 100% | 0,15° | 0,8 px | nenhuma — 7 segmentos espúrios oferecidos, 7 recusados |

Três leituras que valem o bloco:

**`apagada` e `noite` dão o mesmo 0% por motivos opostos.** Uma morre na primeira etapa, a outra na segunda. Com um número só — "detectou ou não" — as duas são indistinguíveis, e você passaria a tarde mexendo no parâmetro errado. É para isso que existe a segunda tabela do avaliador, a de etapas.

**`sombra` é o pior caso, e é o que marca 100%.** O limite da sombra é uma reta longa, forte e inclinada; o agrupamento é por **sinal** da inclinação; então o segmento da sombra entra no grupo da esquerda mesmo estando do lado direito do quadro, e o ajuste ponderado por comprimento obedece. Detecção perfeita, 49 pixels de erro. *Achar não é acertar.*

**Defesa custa, e dá para ver a conta.** Na condição de faixa dupla, o Hough ofereceu 7 segmentos espúrios e o filtro de inclinação (20°–78°) recusou todos. A defesa que *não* está implementada — exigir que o segmento esteja do lado do quadro correspondente ao grupo — é exatamente a que resolveria a sombra. Fica para vocês.

### As quatro figuras que são a evidência do G3.5

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
mkdir -p "$PB_DIR/docs/evidencias/tp3/veicular"
python3 faixas.py --quadro estrada/sombra/quadro006.png \
  --etapas "$PB_DIR/docs/evidencias/tp3/veicular"
python3 avaliar_faixas.py --imagem "$PB_DIR/docs/evidencias/tp3/veicular/painel.png"
```

Saem `1-cor.png`, `2-borda.png`, `3-reta.png` e `4-final.png`. São elas que mostram, em vez de afirmar, onde a cadeia se perdeu — e é isso que o `veicular.md` do TP3 tem de conter.

!!! warning "Não existe almoço grátis, e dá para medir o preço"
    Baixar o Canny para `--canny 10 30` recupera a condição `noite` de 0% para 100% — e **arruína** a sombra: o erro angular vai de 3,9° para 23,4°, e os espúrios de 4 para 43. Não é um ajuste melhor; é outro compromisso. Diga no relatório **qual** você escolheu e **por quê**, e o que perdeu em troca.

### Trocar a fonte por MetaDrive é opcional, e custa a verdade

O contrato do exemplo é uma função que entrega quadros BGR. Trocar a cena sintética pelo MetaDrive não muda nada daí para a frente — mas a verdade geométrica some junto, e com ela todas as colunas de erro. É por isso que a **medição fica na cena sintética** e o simulador, quando entrar, entra para a demonstração.

## Parte 4 — O que a navegação acrescenta

*(É o bloco que ficou da Aula 12, e é o que cede de novo se o tempo apertar.)*

O `piloto.py` do mundo mínimo é o navegador mais burro que funciona: anda reto, gira quando fecha na frente. Trinta linhas, e explora o mundo inteiro.

Agora que existe mapa, a lista do que falta a ele fica concreta:

| O piloto não sabe | O Nav2 acrescenta | Já existe? |
|---|---|---|
| onde está | localização contra o mapa | **o mapa é do TP3** |
| para onde vai | um objetivo, enviado como ação | as ações são da Aula 8 |
| o que há além do que o laser vê | custos global e local, construídos do mapa | **o mapa é do TP3** |
| o que fazer quando trava | comportamentos de recuperação | ainda não |

**O objetivo do Nav2 é uma ação**, com feedback periódico e cancelamento — exatamente as da Aula 8. Navegação não é assunto novo; é a montagem de peças que já estão no lugar. O TP4 começa em 30/10, e é onde isso vira entrega.

## Tarefa da semana

### O que fazer

Duas coisas, e as duas vão para o repositório como evidência do TP3:

1. **Segmentação por instância do seu domínio**, publicando em `/vision/segmented`, com a contagem publicada e **medida** — erro de contagem, IoU médio, fusões e divisões, contra uma verdade que você construiu.
2. **O módulo veicular rodando**, com as quatro figuras das etapas e um parágrafo dizendo, para a condição em que ele falhou, **qual etapa** quebrou e como você sabe disso.

### O que usar

| Para | Use |
|---|---|
| separar o que se encosta | `instancia.py`, função `cor_watershed` |
| medir a instância | `avaliar.py`, e a figura do `--imagem` |
| publicar no tópico | o nó `segmentador_instancia` e o `config/instancia.yaml` |
| a cadeia veicular | `faixas.py --etapas`, e o `avaliar_faixas.py` |
| escrever a evidência | `docs/evidencias/tp3/veicular.md` |

### Como adequar ao seu projeto

**As classes são as suas.** Troque as três faixas HSV do `instancia.yaml` pelas cores do seu domínio e o `Int32` da contagem pela sua `.msg` da Aula 6 — quem entrega contagem de peça genérica está entregando o meu exemplo, não o projeto dele.

**A verdade é sua, e é o trabalho de verdade.** Para medir, você precisa de pelo menos **dez quadros com verdade**: ou gerando a cena como o `cena.py` faz, ou rotulando à mão dez imagens reais do seu cenário. Dez é pouco e é honesto; zero não é medida nenhuma.

**A região de interesse é sua.** No módulo veicular, o trapézio que corta o céu depende do ângulo da sua câmera. Quem tem robô terrestre pode apontar a mesma cadeia para uma linha no chão — é o mesmo problema com outra escala.

### Como saber que terminou

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-instancia" && python3 avaliar.py      # a tabela, com o SEU cenário
cd "$PB_WS" && source install/setup.bash
ros2 launch aula13_instancia instancia.launch.py &       # deixe subir
sleep 10
ros2 topic echo /vision/instancias --once                # a contagem, publicando

cd "$PB_DIR/aula13-veicular"
python3 avaliar_faixas.py                                # as cinco condições
```

Guarde a tabela, a figura do `--imagem` e as quatro etapas em `docs/evidencias/tp3/`. **Quem rodou e não guardou fez o trabalho e não provou.**

## Desafio — o modelo pré-treinado vale a pena no seu domínio?

O `avaliar.py` tem um terceiro detector, `modelo`, que é um adaptador para o YOLOv8-seg e obedece ao **mesmo contrato** dos outros dois. Na cena do exemplo ele já foi medido — 85,8% de erro de contagem, 0% de acerto de classe, 148 ms por quadro — mas a pergunta que interessa é sobre **o seu** domínio. Instale num venv (nunca `sudo pip`, que reescreve a biblioteca que os nós ROS 2 usam), rode sobre o seu cenário, e responda com número:

- ele acha as instâncias que o watershed não acha — por exemplo, as encostadas face a face?
- e **acerta a classe**? Ele conhece as classes do COCO, não "peça vermelha do meu projeto". O que acontece com a coluna de classe?
- quanto custa por quadro, comparado aos 16 ms e 30 ms dos clássicos?
- e a pergunta que interessa: **para o seu domínio, qual dos três você entregaria, e o que você perde na escolha?**

Não há resposta única, e há respostas erradas: qualquer uma sem número é uma delas.

```bash
# ── herda as variáveis do bloco de download ──
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

## Para a próxima aula — 20/10

**Aterrissagem do TP3.** É o último encontro antes da entrega de **sexta, 23/10**: clínica dos gates que ainda estiverem abertos, leitura do que o relatório precisa conter, e fechamento das evidências. Chegue com o mapa salvo, a instância publicando e as figuras do veicular — a clínica é para o que não fechou, não para começar.
