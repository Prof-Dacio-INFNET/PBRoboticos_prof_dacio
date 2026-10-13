# Exemplo — `aula13-veicular`

**Aula 13 · Percepção veicular.** A pipeline clássica de faixa — **HSV + Canny + Hough** — sobre uma cena de estrada com verdade conhecida, com as três etapas isoláveis e uma régua que diz **qual delas quebrou**, não só que o resultado piorou. Cobre o gate **G3.5** do TP3 e prepara o **G4.5** do TP4.

```
aula13-veicular/
├── cena_estrada.py      # gera estrada/<condicao>/quadroNNN.png + estrada/verdade.json
├── faixas.py            # o detector: cor -> borda -> reta, com as etapas guardáveis
├── avaliar_faixas.py    # a régua: mede contra a verdade, condição por condição
└── testar.py            # confere que ele falha ONDE a aula diz que falha
```

Python puro: `cv2` e `numpy` do apt. **Não precisa de ROS 2, não precisa de MetaDrive, não precisa de GPU.**

## Rodar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y python3-opencv python3-numpy

# 1) baixar o material (pode repetir sempre -- o rm evita o erro de pasta ja existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar para dentro do SEU projeto
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula13-veicular \
      "$PB_DIR/"

# 3) gerar a cena e medir
cd "$PB_DIR/aula13-veicular"
python3 cena_estrada.py
python3 avaliar_faixas.py
```

Uns 8 segundos no total: 120 quadros desenhados, 120 medidos.

!!! warning "A pasta `estrada/` tem ~53 MB — não commite"
    PNG com ruído de sensor não comprime, e são 120 deles. A cena é **regenerável e determinística**: ponha `estrada/` no `.gitignore` do seu projeto e commite só as quatro imagens de evidência e o painel. Quem commitar a pasta inteira vai descobrir isso no `git push`.

## O fluxo

```
cena  ──►  cor  ──►  borda  ──►  reta  ──►  faixas
PNG       HSV       Canny      HoughLinesP   (x_base, ângulo)
          branco    no cinza,  agrupadas      por faixa
          + amarelo filtrado   por sinal da
                    pela       inclinação
                    máscara
                    e pela ROI
```

As três etapas são **isoláveis de propósito**: cada uma falha de um jeito diferente, e esse é o conteúdo da aula. Uma pipeline que só devolve o resultado final transforma quatro modos de falha distintos num único "não funcionou".

## O resultado

```
a regua
  condicao     achou as duas  achou esq  achou dir  erro angular  erro na base       ms
  limpo               100.0%     100.0%     100.0%      0.15 g     0.79 px     5.40
  sombra              100.0%     100.0%     100.0%      5.78 g    49.55 px     5.57
  apagada               0.0%       0.0%     100.0%      0.13 g     0.63 px     5.53
  noite                 0.0%       0.0%       0.0%          --          --     5.00
  faixa_dupla         100.0%     100.0%     100.0%      0.15 g     0.81 px     6.27

por etapa (mediana por quadro, dentro da regiao de interesse)
  condicao       px cor  cor esq  cor dir  px borda  segmentos  espurios  nos grupos
  limpo            3134     1649     1580      1341         11         0           0
  sombra          20204     6370    15164      1285         11         4           4
  apagada          1577        0     1577       675          5         0           0
  noite            3260     1710     1643         0          0         0           0
  faixa_dupla      5872     1769     4004      2171         18         7           0
```

Os números de posição e de contagem são **determinísticos** — rodando de novo, saem idênticos. O `ms` é da sua máquina; o que viaja é a razão entre condições, não o valor absoluto.

### A segunda tabela é a que vale a aula

A primeira tabela diz **quanto** piorou. Só a segunda diz **onde**. Repare que as quatro condições deixam quatro assinaturas diferentes nos mesmos três contadores:

| Condição | O que a cena tem | O que acontece nos contadores | Etapa que quebrou |
|---|---|---|---|
| `limpo` | pintura clara sobre asfalto escuro | 3134 px de máscara, 1341 px de borda, 11 segmentos | — é a linha de base |
| `sombra` | sombra diagonal, e o *auto-exposure* abrindo por causa dela | máscara **incha de 3134 para 20204 px**; 4 segmentos por quadro que não são de faixa nenhuma **entram nos grupos** | **reta** — o ajuste está certo, a entrada é que não é |
| `apagada` | pintura esquerda desbotada (22% de opacidade) | `cor esq` vai de **1649 para 0 px**; `cor dir` fica intacta em 1577 | **cor** — e de um lado só |
| `noite` | contraste baixo: ganho no máximo, preto levantado | máscara **sobrevive** (3260 px, 104% do limpo) e o Canny devolve **0 px** | **borda** — contraste, não cor |
| `faixa_dupla` | dupla amarela ao centro | máscara cresce para 5872 px, Hough devolve 7 espúrios, **nenhum entra nos grupos** | nenhuma — a pipeline aguentou |

**`apagada` e `noite` dão o mesmo resultado final — 0% — por motivos opostos.** Em `apagada` a máscara some de um lado e o Hough nunca recebe o que ajustar. Em `noite` a máscara passa inteira e é o Canny que não acha diferença nenhuma para medir. Quem olha só a primeira tabela conclui "o detector não funciona no escuro nem com pintura ruim" e vai consertar a coisa errada em pelo menos um dos dois casos.

É a mesma disciplina do banco de provas da [Aula 9](../aula09-metrica/index.md): **modo de falha é o que você precisa saber; média é só um resumo.** A diferença é que aqui o modo de falha é localizado por etapa, com contador.

### Achar não é acertar

Olhe a linha da `sombra`: **100% de detecção e 49,55 px de erro na base.** O detector devolveu duas faixas em todos os quadros, com a maior confiança do mundo, e elas estão quase meio metro fora do lugar na escala da cena.

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 faixas.py --quadro estrada/sombra/quadro006.png --etapas /tmp/etapas-sombra
```

O `3-reta.png` mostra o mecanismo: o limite da sombra corre a **−40°**, a faixa esquerda verdadeira corre a **−54°**, e o agrupamento separa os segmentos pelo **sinal** da inclinação. Negativo é negativo: o limite da sombra entra no grupo da esquerda **mesmo estando do lado direito do quadro**, é mais longo que a pintura que sobrou, e o ajuste ponderado por comprimento faz exatamente o que foi mandado fazer — dá mais peso a quem viu mais pixels.

!!! warning "Um detector que não sabe dizer 'não sei' é pior que um que erra"
    Para o controle, 100% com 49 px de erro é pior que 0% honesto: no segundo caso o sistema freia ou devolve o volante; no primeiro ele esterça com convicção para fora da pista.

    No seu projeto, isso vira um requisito concreto: **publique uma medida de confiança junto com a faixa** — número de segmentos, comprimento total, dispersão do ajuste — e deixe o consumidor decidir o que fazer com ela. O `faixas.py` já devolve `n_seg` e `comprimento` em cada faixa justamente para isso.

## A evidência do gate G3.5

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
mkdir -p "$PB_DIR/docs/evidencias/tp3/veicular"
python3 faixas.py --quadro estrada/limpo/quadro000.png \
                  --etapas "$PB_DIR/docs/evidencias/tp3/veicular"
```

Saem quatro arquivos, e eles são exatamente o que o gate pede:

| Arquivo | O que mostra | O que ele prova |
|---|---|---|
| `1-cor.png` | a máscara HSV, branco em branco e amarelo em amarelo | que a etapa de cor roda, e **quanto dela é vazamento** — o rótulo traz os pixels do quadro inteiro e os de dentro da ROI |
| `2-borda.png` | o Canny já filtrado pela máscara e pela ROI, com o trapézio em âmbar | que a região de interesse está aplicada, e onde |
| `3-reta.png` | os segmentos do Hough, ciano na esquerda, magenta na direita, cinza nos recusados | como o agrupamento decidiu — é aqui que se vê o segmento espúrio entrando |
| `4-final.png` | a cena com as duas faixas ajustadas e o ângulo de cada uma | o resultado que o nó publicaria |

Rode o mesmo comando apontando para `estrada/sombra/quadro006.png` e guarde os dois conjuntos: **o par limpo/sombra é a discussão de falhas do G4.5 inteira, em quatro imagens.**

## O painel comparativo

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 avaliar_faixas.py --imagem "$PB_DIR/docs/evidencias/tp3/veicular/painel.png"
```

Um quadro por condição, **âmbar na faixa de verdade e verde na faixa detectada**, com a legenda embutida — a figura vai para o relatório sozinha. Âmbar sozinho significa que não achou; âmbar e verde separados significam que achou torto. É a mesma ideia da figura de diferença da [Aula 12](../aula12-slam/index.md): um número diz *quanto*, a figura diz *onde*.

## Não existe almoço grátis

A `noite` morre no Canny. A correção óbvia é baixar os limiares — e o exemplo deixa você fazer isso sem editar nada:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 avaliar_faixas.py --canny 10 30
```

Na cena padrão, a `noite` vai de **0% para 100%** com erro de 0,16° e nada mais piora. Parece almoço grátis. Não é: a cena padrão tem ruído de sensor baixo. Suba o ruído para o nível de uma câmera barata à noite e rode os dois de novo:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 cena_estrada.py --ruido 3
python3 avaliar_faixas.py                 # Canny padrão
python3 avaliar_faixas.py --canny 10 30   # Canny baixo
```

| Com ruído 3× | `noite` acha as duas | `sombra` erro angular | espúrios na `sombra` (nos grupos) |
|---|---|---|---|
| Canny (50, 150) | 0,0% | 3,90° | 4 (4) |
| Canny (10, 30) | **100,0%** | **23,42°** | **43 (21)** |

Baixar o limiar comprou a noite e vendeu a sombra: o erro angular na sombra ficou **seis vezes maior**, porque o Canny passou a enxergar textura de asfalto e ruído como borda, e o Hough montou 43 segmentos por quadro que não são de faixa nenhuma.

!!! tip "A regra geral, que vale para o seu projeto"
    **Todo parâmetro que você afrouxa para resolver uma condição piora outra.** Isso não é defeito do Canny; é o que *limiar* significa. A saída não é achar o número mágico — é medir as duas condições ao mesmo tempo e declarar qual delas o seu projeto escolhe atender.

    Se o seu sistema roda de dia, otimize para a sombra e documente que a noite está fora de escopo. Se roda à noite, o contrário. O que não vale é ajustar olhando uma condição só e chamar de "funcionou".

## O que cada arquivo faz

| Arquivo | Papel |
|---|---|
| `cena_estrada.py` | desenha as cinco condições e grava a verdade das duas faixas por quadro |
| `faixas.py` | o detector em três etapas; também é CLI (`--quadro`, `--pasta`, `--etapas`, `--sem-roi`) |
| `avaliar_faixas.py` | mede contra a verdade, nomeia a etapa quebrada, desenha o painel |
| `testar.py` | sete grupos de teste: confere que cada condição falha onde a aula diz |

### A verdade, e por que esses dois números

O `estrada/verdade.json` traz, por quadro e por faixa:

```json
{
 "arquivo": "limpo/quadro000.png",
 "quadro": 0,
 "faixa_esq": { "x_base": 103.69, "angulo": -52.21 },
 "faixa_dir": { "x_base": 536.31, "angulo":  52.21 },
 "ponto_fuga": [320.0, 200.0]
}
```

`x_base` é onde a reta da faixa cruza a **última linha da imagem** — onde o carro está agora. `angulo` é `atan2(dy, dx)` em graus, normalizado para `(-90, 90]`. Escolhi esses dois porque o erro fica legível sem conta nenhuma: *"errou 2,1 graus e 7 pixels na base do quadro"* é uma frase que cabe no relatório e que qualquer pessoa julga de olho. O mesmo erro em `(rho, theta)` sai em unidades que ninguém consegue avaliar lendo.

O sinal do ângulo não é decoração: **faixa esquerda é negativa, direita é positiva**, e é exatamente esse sinal que o detector usa para separar os segmentos em dois grupos.

### Por que a cena é desenhada

Pelo mesmo motivo da Aula 9: para medir percepção você precisa saber a resposta certa em cada quadro, e rotular vídeo de estrada à mão é caro e chato. Desenhando a cena, a verdade sai exata e de graça — inclusive os contadores por etapa, inclusive a coluna `espurios`, que só existe porque dá para perguntar *"esse segmento está a mais de 10° das duas faixas verdadeiras?"*.

Isso **não substitui dado real.** Substitui a falta dele no dia em que você precisa validar o seu *método*. As faixas são retas, não curvas, de propósito: o modelo que o Hough ajusta é uma reta, e medir numa cena curva mediria o erro do modelo misturado com o erro da pipeline. Curva é o passo seguinte, e ele começa trocando o ajuste de reta por um ajuste polinomial de segundo grau sobre os mesmos segmentos.

## Como adequar ao seu projeto

Três coisas mudam, e todas estão no `CFG_PADRAO` do `faixas.py` — você não precisa editar função nenhuma:

**A cor da pintura.** `branco_s_max` / `branco_v_min` para pintura clara, `amarelo_h` / `amarelo_s_min` / `amarelo_v_min` para a amarela. São faixas HSV *diferentes* porque branco e amarelo são coisas diferentes no espaço HSV: branco é "pouco saturado e claro" (matiz nenhum), amarelo é "matiz entre 15 e 38 e saturado". Quem junta as duas numa faixa larga aceita asfalto claro junto.

**A região de interesse.** `roi` é uma tupla de quatro pares em **frações** do quadro, não em pixels — assim ela sobrevive a uma troca de resolução. Câmera mais alta, mais inclinada ou com outra lente pede outro trapézio. Para ver o que ela está cortando, rode com `--sem-roi`: o exemplo põe um telhado inclinado e um poste acima do horizonte de propósito, e sem a ROI eles entram nos grupos e estragam o ângulo em **17 graus**.

**O critério de agrupamento.** Hoje é o sinal da inclinação mais uma faixa aceita de 20° a 78°. O mínimo recusa o horizonte; o máximo recusa a dupla central — e é por isso que a condição `faixa_dupla` passa ilesa, com 7 espúrios oferecidos e nenhum aceito. A defesa que falta, e que a condição `sombra` cobra, é **exigir que o segmento esteja do lado do quadro que corresponde ao seu grupo**: três linhas em `agrupar()`, e vale a pena você escrevê-las e medir o quanto elas compram.

!!! tip "Robô terrestre: é a mesma pipeline"
    Quem está na trilha R e não tem carro aponta esse mesmo código para uma **linha de fita no chão**. Muda a cor no `CFG_PADRAO`, muda o trapézio (a câmera do robô olha mais para baixo), e o agrupamento vira "um grupo só" — uma linha, não duas. O resto — Canny, Hough, ajuste ponderado, os contadores por etapa — fica igual, e a régua também: basta gerar a cena com uma faixa só.

## Trocar a fonte por MetaDrive (opcional)

O contrato entre a cena e o detector é **uma função que entrega quadros BGR**. Ele existe de verdade, em `faixas.py`:

```python
def fonte_pasta(pasta):
    """Entrega quadros BGR (H, W, 3) uint8, em ordem. E o contrato com a cena."""
    for caminho in sorted(pathlib.Path(pasta).glob('*.png')):
        bgr = cv2.imread(str(caminho))
        if bgr is not None:
            yield bgr
```

É ela que o `faixas.py --pasta DIR` consome. Trocá-la por MetaDrive é escrever outra com a mesma assinatura — `detectar_faixas()` não muda uma linha:

```python
# esboco -- NAO e necessario para nenhum gate; so instale se quiser
def fonte_metadrive(passos=200):
    from metadrive.envs import MetaDriveEnv          # pip, dentro de um venv
    env = MetaDriveEnv({'use_render': False, 'image_observation': True})
    env.reset()
    for _ in range(passos):
        obs, *_ = env.step([0.0, 0.5])
        yield obs['image'][..., ::-1]                # RGB -> BGR
    env.close()
```

Instalar é `uv venv --system-site-packages` e `pip install metadrive-simulator` **dentro do venv**, nunca no python do sistema e nunca dentro de um nó ROS 2 — a regra da disciplina não muda aqui. São uns 2 GB e alguns minutos; por isso ele é opcional e por isso a aula não espera por ele.

Para sentir como é rodar sem verdade antes de instalar coisa nenhuma, aponte o `--pasta` para qualquer pasta de PNG:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 faixas.py --pasta estrada/noite
```

Ele imprime o ângulo de cada faixa por quadro e **nenhuma coluna de erro** — porque não há com o que comparar. É literalmente a tela que você vai ver com o MetaDrive.

!!! warning "O que se perde na troca — e é o principal"
    **A verdade.** O MetaDrive sabe onde as faixas estão no mundo dele, mas não entrega os parâmetros delas em coordenadas da sua imagem, e sem isso as colunas `erro angular`, `erro na base` e `espurios` **deixam de poder ser calculadas**. Sobra "parece bom".

    Por isso a divisão de trabalho é esta, e ela é deliberada: **a medição fica com a cena sintética; o MetaDrive entra como confirmação visual de que a pipeline sobrevive a uma imagem que você não desenhou.** É o mesmo movimento do mundo mínimo da [Aula 11](../aula11-mundo/index.md) — o simulador atrás de uma interface, e o caminho sem simulador sempre funcionando.

    O gate **G4.5** pede a pipeline sobre a cena do MetaDrive. Este exemplo entrega tudo menos a fonte: quando o MetaDrive entrar, o `faixas.py` roda inalterado, e o `avaliar_faixas.py` continua medindo na cena sintética, que é onde a medição ainda significa alguma coisa.

## Conferir antes de confiar

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula13-veicular"
python3 testar.py
```

Sete grupos, uns 5 segundos, cena própria numa pasta temporária. Eles não conferem se o detector é bom — conferem se ele **falha onde a aula diz que falha**, que é o que a aula afirma. O grupo 2 é o exemplar: não se contenta com "a taxa caiu", exige que a queda apareça nos pixels da **etapa de cor** e que o lado direito continue intacto. Afirmação de slide sem teste é só afirmação de slide.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `nao achei a cena em estrada` | rode `python3 cena_estrada.py` antes — a mensagem já traz o comando |
| `No module named 'cv2'` | `sudo apt install python3-opencv` |
| `No module named 'numpy'` | `sudo apt install python3-numpy` |
| `cd: $PB_DIR/aula13-veicular: No such file` | `$PB_DIR` está vazio neste terminal — redefina as variáveis do bloco do topo |
| as duas faixas vêm `NAO ACHADA` em tudo | confira a ordem dos canais: o OpenCV lê **BGR**, não RGB |
| o detector acha faixa no céu | a ROI está desligada ou o trapézio não cobre a sua câmera |
| `erro na base` grande com 100% de detecção | é a `sombra`, e é o ponto da aula — abra o `3-reta.png` |
| tudo some quando troco a resolução | a ROI é em frações; conferir se você não a converteu para pixels |

## Licença

MIT, como todo o diretório `exemplos/`.
