# Exemplo — `aula17-cnn`

**Aula 17 · Etapa 9.** O item 4 do TP4 diz, no enunciado: *"Colete 500 frames rotulados do MetaDrive em 3 classes (via livre / obstáculo / cruzamento). Treine uma CNN com TensorFlow/Keras usando data augmentation (rotação ±15°, zoom 0,2, flip horizontal), BatchNormalization e Dropout(0,5). Plote as curvas de accuracy e loss com e sem augmentation e relate a melhoria de generalização."* O gate **G4.6** acrescenta a **matriz de confusão**. Este exemplo percorre esse enunciado de ponta a ponta: um ambiente Python que roda TensorFlow ao lado do ROS 2 sem quebrá-lo, a rotulagem dos quadros do MetaDrive, a mesma rede treinada duas vezes, as curvas no mesmo eixo e a matriz.

> ## Leia isto antes de qualquer coisa
>
> **Os números desta página saíram de imagens SINTÉTICAS**, desenhadas pelo `gerar_sintetico.py` sobre a estrada da Aula 13 — não do MetaDrive. Capturar 500 quadros do MetaDrive leva uns 23 minutos com renderização por software, e, com o piloto automático dirigindo, a classe `obstaculo` sai **vazia**: 0 em 60 na amostra da `aula17-metadrive`. Com o sintético, a aula tem números medidos hoje, sobre três classes que existem. **O seu relatório usa os quadros do MetaDrive**, não estes; o caminho está na seção **"O fluxo com o MetaDrive"**.
>
> O que rodou e o que não rodou está separado, linha a linha, em **"O que foi e o que não foi verificado"**, no fim.

```
aula17-cnn/
├── gerar_sintetico.py   # 500 imagens rotuladas, 3 classes, deterministicas -- SINTETICAS
├── rotular.py           # le o estado.csv do MetaDrive, propoe o rotulo, voce revisa no teclado
├── treinar.py           # a MESMA CNN treinada sem e com augmentation; matriz de confusao
├── curvas.py            # acuracia e perda, treino e validacao, as duas rodadas no mesmo eixo
├── testar.py            # 7 grupos; prova o que da sem treinar de verdade
└── amostra/             # so figuras e tabelas das rodadas medidas (nenhum modelo, nenhuma imagem)
```

O contrato entre as peças é uma pasta com PNG e um `rotulos.csv` (`arquivo,classe`). Quem treina não sabe de onde as imagens vieram:

```
   venv do MetaDrive                python3 do sistema (apt)          venv da CNN (.venv-cnn)

   capturar_frames.py  ------->  quadroNNN.png + estado.csv
                                          |
                                     rotular.py  ------->  rotulos.csv  --+
                                                                          |
                                   gerar_sintetico.py  ->  rotulos.csv  --+--> treinar.py --> curvas.py
                                                                                   |
                                                                  historico_*.json, matriz_*.png, tabela.txt
```

São **três Pythons**, e cada um tem um motivo: o MetaDrive precisa do venv dele (Panda3D), a janela de revisão precisa do OpenCV do apt (que abre janela), e o TensorFlow precisa de um venv que **não enxergue** os pacotes do sistema. O terceiro é a exceção da disciplina, e a seção do ambiente explica por quê.

## Baixar

O `gerar_sintetico.py` importa o `cena_estrada.py` da Aula 13 **pelo caminho**, e o fluxo real começa no `capturar_frames.py` da `aula17-metadrive`; as três pastas descem juntas e lado a lado. Tudo pende do `git clone` pelo `&&`: se o clone falhar, nenhum `rm -rf` roda.

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y python3-numpy python3-opencv

mkdir -p "$PB_DIR" && cd /tmp && rm -rf pb-a17c && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a17c && \
  rm -rf "$PB_DIR/aula17-cnn" "$PB_DIR/aula17-metadrive" "$PB_DIR/aula13-veicular" && \
  cp -r pb-a17c/exemplos/aula17-cnn "$PB_DIR/" && \
  cp -r pb-a17c/exemplos/aula17-metadrive "$PB_DIR/" && \
  cp -r pb-a17c/exemplos/aula13-veicular "$PB_DIR/"
```

## O ambiente — a única exceção ao `--system-site-packages`

Em toda a disciplina o ambiente Python se cria com `uv venv --system-site-packages`: o venv enxerga o NumPy 1.21 e o OpenCV 4.5 do apt, que são os que o `cv_bridge` do ROS 2 aceita, e só o que falta é instalado por cima. **Aqui não.** O venv da CNN nasce **sem** essa opção:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
uv venv --python 3.10 .venv-cnn
uv pip install --python .venv-cnn/bin/python tensorflow-cpu opencv-python-headless matplotlib scikit-learn
```

**Por quê.** O TensorFlow 2.21 traz o NumPy **2** dele. Num venv que enxerga o sistema, todo pacote que **não** estiver dentro do venv é buscado no `/usr/lib/python3/dist-packages` — e o `python3-opencv` e o `python3-matplotlib` de lá foram compilados contra o NumPy **1.x**. Basta um deles ficar de fora da linha do `uv pip install` (ou um `import` de algo que só existe no apt) para o `import` cair na versão do sistema, que, ao lado do NumPy 2, morre com `ImportError: numpy.core.multiarray failed to import` precedido de `_ARRAY_API not found` — uma frase que não menciona versão nenhuma. **Sem** `--system-site-packages`, o mesmo esquecimento dá `No module named cv2`, que nomeia a causa. A regra continua valendo para tudo o que fala com o ROS 2; esta é a exceção porque **este venv nunca importa ROS 2**: ele lê PNG e CSV e grava PNG, JSON e `.keras`.

Os outros três detalhes da linha, cada um com motivo:

- **`tensorflow-cpu`**, não `tensorflow`: a CNN deste tamanho treina em menos de um minuto na CPU, e o pacote completo traz o suporte a CUDA, maior e inútil num WSL2 sem GPU configurada.
- **`opencv-python-headless`**: o OpenCV sem janela. A janela de revisão do `rotular.py` roda com o `python3` **do sistema**, cujo OpenCV do apt abre janela pelo WSLg. Os dois OpenCV nunca se encontram, porque estão em Pythons diferentes.
- **O venv fica em `$PB_DIR/.venv-cnn`**, fora da pasta do exemplo, pelo mesmo motivo do venv do MetaDrive: o bloco de download apaga e recria `aula17-cnn/`, e um venv de 1,9 GB iria junto.

Nesta máquina o `uv` resolveu 47 pacotes. As versões que importam:

| pacote | versão |
|---|---|
| Python | 3.10.20 (baixado pelo `uv`) |
| tensorflow-cpu | 2.21.0 |
| keras | 3.12.4 |
| numpy | 2.2.6 |
| opencv-python-headless | 5.0.0.93 (`cv2.__version__` = 5.0.0) |
| matplotlib | 3.10.9 |
| scikit-learn | 1.7.2 |

A primeira tentativa de instalação ficou **dez minutos parada** baixando o `tensorflow-cpu` (261 MB) e foi interrompida; a segunda, idêntica, terminou em **11 s**. Se a sua parar, interrompa com Ctrl+C e repita a linha — o `uv` aproveita o que já baixou.

Confira antes de seguir:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
"$PB_DIR/.venv-cnn/bin/python" -c "import tensorflow as tf, keras, numpy, cv2; print(tf.__version__, keras.__version__, numpy.__version__, cv2.__version__)"
```

Antes da linha de versões aparecem umas cinco linhas de `oneDNN custom operations are on` e `This TensorFlow binary is optimized to use available CPU instructions`. São informação, não erro; os scripts deste exemplo as silenciam.

## Conferir antes de confiar

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" testar.py
```

Sete grupos, 121 conferências, uns 65 s neste container — quase todo o tempo é o TensorFlow subindo três vezes, e uns segundos são as três revisões do `rotular.py` dirigidas por um pseudoterminal. O teste não prova que a rede aprende; prova que as peças estão no lugar: o sintético é determinístico byte a byte, o CSV tem as colunas, o `rotular.py` traduz os códigos de tecla do GTK, do Qt e do Windows, retoma só o que foi revisado e revisa pelo terminal (sem janela: a janela não é testada aqui), as duas rodadas começam com **os mesmos pesos** (os 19 tensores do núcleo, um a um), o `treinar.py --epocas 1` gera todos os arquivos com a matriz 3×3, ele não quebra nos 12 quadros reais da amostra do MetaDrive (onde uma classe tem um exemplo só e outra não tem nenhum), e o `curvas.py` grava um PNG de verdade. Termina em `todos os testes passaram.`

## Medir no sintético

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" gerar_sintetico.py --saida sintetico
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta sintetico --saida resultado
"$PB_DIR/.venv-cnn/bin/python" curvas.py --pasta resultado --saida resultado/curvas.png
```

**As imagens.** 500, de 128×96 (a razão 4:3 dos quadros do MetaDrive), 167 / 167 / 166 por classe, semente 7. `via_livre` é a pista com as faixas; `obstaculo` tem um veículo ou cones **na faixa do carro**, a uma distância sorteada; `cruzamento` tem uma via transversal e a linha de parada. Em 35% das de `via_livre` e `cruzamento` há um carro **na faixa vizinha** — é a mesma regra do `estado.csv` do MetaDrive (só conta o que está no corredor à frente), e sem ele "tem um retângulo escuro na imagem" separaria as classes sozinho. Metade das imagens tem a faixa dupla amarela, sempre **à esquerda** do carro. O brilho varia de 0,65 a 1,30.

**A rede.** Três blocos `Conv2D → BatchNormalization → ReLU → MaxPooling` (16, 32 e 64 filtros), `Flatten`, `Dense(64)`, `Dropout(0.5)`, `Dense(3, softmax)`. Adam a 0,001, lote 32, 20 épocas, 80/20 estratificado com semente 7. Os hiperparâmetros estão no topo do `treinar.py`, declarados antes de qualquer resultado. A rodada `com` acrescenta, **antes** da rede, `RandomRotation(15/360)` — o Keras recebe a rotação em **fração de volta**, e `RandomRotation(15)` giraria até 15 voltas —, `RandomZoom(0.2)` e `RandomFlip('horizontal')`.

### A tabela medida

Treinado numa CPU de 2 núcleos, 89 s de parede para as duas rodadas (38,7 s a `sem`, 43,2 s a `com`, o resto é carregar o TensorFlow e as imagens):

```
dados   : sintetico -- 500 imagens, via_livre 167, obstaculo 167, cruzamento 166
divisao : 400 treino / 100 validacao, semente 7; 20 epocas, lote 32, entrada 128x96, BN momentum 0.9
linha de base: responder SEMPRE "via_livre" acerta 0.330 da validacao

rodada  acc_val  perda_val  acc_treino  melhor_acc_val(ep)  pior recall          acc_val_pert   tempo
sem       0.980      0.046       0.913       0.990 (10)     obstaculo   0.941         0.910    38.7 s
com       0.930      0.387       0.678       1.000 (19)     via_livre   0.788         0.940    43.2 s
diferenca (com - sem) na acc_val final: -0.050; na acc_val_pert: +0.030
acc_val_pert = a MESMA validacao passada uma vez (semente fixa) por rotacao, zoom e flip

recall por classe   via_li  obstac  cruzam
  sem                1.000   0.941   1.000
  com                0.788   1.000   1.000

matriz sem (linha = verdade, coluna = previsto, via_livre / obstaculo / cruzamento)
  via_livre      33     0     0
  obstaculo       2    32     0
  cruzamento      0     0    33
matriz com (linha = verdade, coluna = previsto, via_livre / obstaculo / cruzamento)
  via_livre      26     7     0
  obstaculo       0    34     0
  cruzamento      0     0    33
```

Rodei duas vezes, em processos separados: os mesmos números, casa por casa. É o `enable_op_determinism()` do TensorFlow mais a semente em tudo — **na mesma máquina**. Em outra CPU muda mais que a terceira casa: no WSL2 do professor, em 09/11/2026, a mesma semente deu `sem` 0,980 e `com` **0,850** na validação limpa (aqui, 0,930), e 0,880 contra 0,940 na perturbada. O sinal das duas diferenças é o mesmo nas duas máquinas — o augmentation perde na validação limpa e ganha na perturbada —; o tamanho, não. Leia o sinal, e relate os **seus** números.

A figura das curvas é a `amostra/curvas.png` desta pasta: acurácia e perda, treino tracejado e validação cheia, a rodada `sem` em azul e a `com` em laranja, no mesmo eixo.

Quatro leituras.

**O augmentation não melhorou a acurácia de validação — piorou 5 pontos.** E isso não é defeito. A validação sintética não tem nenhuma imagem girada, ampliada ou espelhada: ela mede a tarefa como ela é, e a tarefa aqui é fácil. A rodada `com` paga o preço do augmentation — aprende mais devagar, as curvas laranjas sobem dez épocas depois das azuis — sem ter onde cobrar o benefício. Em 20 épocas ela ainda está subindo e oscila: 1,000 na época 19, 0,930 na 20. A última época sozinha é um número frágil, e a tabela traz a melhor ao lado por isso.

**A coluna `acc_val_pert` pergunta o que o augmentation promete.** São as **mesmas** 100 imagens de validação passadas **uma** vez, com semente fixa, pelas mesmas três camadas — uma câmera torta, um zoom e um espelho, o tipo de variação que só a rodada `com` viu no treino (com outros sorteios). Ali a ordem se inverte: 0,910 sem, 0,940 com. São **três imagens em cem**. É a direção que a teoria prevê, mas três imagens não sustentam uma conclusão, e é exatamente isso que se escreve no relatório.

**A curva de treino da rodada `com` fica abaixo da de validação** — 0,678 contra 0,930. Ela é medida sobre imagens **aumentadas**, mais difíceis que as originais, e com o Dropout ligado. Validação acima do treino não é vazamento; é o que acontece quando o treino é mais difícil de propósito.

**A matriz diz o que a acurácia esconde.** As duas rodadas acertam todos os cruzamentos. A `sem` erra dois obstáculos chamando-os de via livre — o erro perigoso. A `com` erra no sentido contrário: sete vias livres viram obstáculo — o erro chato, o carro que freia à toa. Mesma ordem de grandeza na acurácia, comportamentos opostos no carro. O G4.6 pede a matriz por isso.

As figuras estão em `amostra/`: `curvas.png`, `matriz_sem.png`, `matriz_com.png` e `exemplos_augmentation.png` (uma imagem por classe e quatro versões aumentadas — olhe-a antes de confiar no augmentation).

### O caso desequilibrado: "acerta 90% respondendo sempre via livre"

A amostra do MetaDrive saiu com 54 `via_livre`, 0 `obstaculo` e 6 `cruzamento`. Na ordem das classes do enunciado — `via_livre:obstaculo:cruzamento` — isso é `54:0:6` (e **não** `54:6:0`, que daria seis obstáculos):

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" gerar_sintetico.py --proporcao 54:0:6 --saida desequilibrado
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta desequilibrado --saida resultado-deseq
```

São 450 / 0 / 50, e a linha de base passa a ser **0,900**: uma "rede" que nem olha a imagem e responde sempre `via_livre` acerta 90 em 100. A rede deste exemplo, nesse conjunto, faz 1,000 nas duas rodadas — o cruzamento sintético é fácil demais (`amostra/desequilibrado/`). O número que a aula precisa aparece de dois outros jeitos, ambos medidos:

**1. A rede quebrada que reporta 90%.** Com a BatchNormalization no momentum padrão do Keras (a quarta armadilha, logo abaixo), a mesma rede no mesmo conjunto termina assim (`amostra/desequilibrado-bn-0.99/`):

```
linha de base: responder SEMPRE "via_livre" acerta 0.900 da validacao
rodada  acc_val  perda_val  acc_treino  melhor_acc_val(ep)  pior recall          acc_val_pert   tempo
sem       0.900      0.829       1.000       0.900 ( 1)     cruzamento  0.000         0.900    37.5 s
matriz sem (linha = verdade, coluna = previsto, via_livre / obstaculo / cruzamento)
  via_livre      90     0     0
  obstaculo       0     0     0
  cruzamento     10     0     0
```

Acurácia de validação 0,900, de treino 1,000 — e a rede **nunca** disse `cruzamento`. Quem olhar só a acurácia entrega isso como resultado. A coluna da matriz é a única coisa da tabela que denuncia.

**2. A classe que não existe no treino.** A rede **sadia** treinada no `54:0:6` — 100% na validação dela — foi posta diante dos 167 obstáculos do conjunto equilibrado. A rodada `sem` chamou **157** de `via_livre` e 10 de `cruzamento`; a `com`, 143 e 24. **Zero** de `obstaculo`: ela não tem como responder uma classe que nunca viu, e a validação dela não tem como mostrar isso, porque também não tem obstáculo. A linha `obstaculo` da matriz sai vazia e o recall sai `n/a`. Isso foi medido com um trecho de seis linhas que carrega o `modelo_sem.keras` e o `modelo_com.keras`; não está num script.

## As armadilhas que o enunciado não avisa

**1. Desbalanceamento: a acurácia alta da rede que responde sempre a mesma coisa.** Com o piloto IDM do MetaDrive, `obstaculo` quase não aparece e `via_livre` domina. A acurácia, então, mede a proporção das classes antes de medir a rede. Três defesas, e as três vão para o relatório: a **linha de base** (a acurácia de quem responde sempre a classe mais comum — o `treinar.py` a imprime), a **matriz de confusão** com o **recall por classe** (o `treinar.py` imprime o pior), e **equilibrar a captura** — mais tráfego e mais acidentes no `capturar_frames.py`, várias sementes — em vez de equilibrar a conta.

**2. O augmentation pode trocar o significado da imagem.** O flip horizontal leva a faixa dupla amarela da esquerda para a direita: a rede passa metade do treino vendo uma estrada de mão inglesa, que não existe nem no Brasil nem no MetaDrive. Para as três classes do item 4 o rótulo sobrevive ao flip — um obstáculo espelhado continua à frente. Mas se a sua rede responder **lado** (obstáculo à esquerda ou à direita, ângulo de esterço, faixa ocupada), o flip **troca a resposta certa** e o rótulo teria de ser trocado junto. Há uma segunda, mais discreta: o `fill_mode='reflect'` da rotação e do zoom preenche os cantos espelhando a imagem, e espelhar uma estrada **inventa faixas** nas bordas — está em `amostra/exemplos_augmentation.png`. A regra: olhe as imagens aumentadas antes de treinar com elas.

**3. A comparação só vale com a mesma semente, a mesma divisão e as mesmas épocas.** Com 100 imagens de validação, cada imagem vale 1 ponto, e a diferença entre as rodadas foi de 5 pontos na validação e 3 na perturbada. Duas rodadas com sementes diferentes variam isso só pela sorte da inicialização e da ordem dos lotes. O `treinar.py` divide **uma** vez e grava a divisão em `divisao.csv`, constrói o núcleo das duas redes com a mesma semente (o `testar.py` confere peso a peso) e embaralha os lotes com a mesma semente. A única diferença entre as duas rodadas são as três camadas de augmentation.

**4. BatchNormalization com poucos dados: o treino acerta e a validação responde uma classe só.** Esta não estava no plano, e foi o primeiro resultado da primeira rodada. Com o padrão do Keras, `BatchNormalization(momentum=0.99)`, a rodada `sem` do conjunto equilibrado chegou a 0,913 no treino e ficou em **0,330** na validação desde a época 4 — tudo `via_livre` (`amostra/bn-0.99/`). A causa: no treino a BN normaliza com a média e a variância **do lote**; na inferência, com as **médias móveis**. Com 400 imagens em lotes de 32 são 13 passos por época, 260 em 20 épocas, e 0,99²⁶⁰ ≈ 0,07: 7% da variância móvel ainda é o valor inicial, 1,0, muito maior que a variância de verdade. O mesmo modelo salvo, avaliado com `training=True`, acerta **0,90** da validação; com `training=False`, 0,33. Com `momentum=0.9`, 0,9²⁶⁰ ≈ 10⁻¹², e a validação vai a 0,98. As acurácias de **treino** das duas configurações são idênticas época a época — o momentum só mexe nas médias móveis — e é isso que torna o diagnóstico limpo:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta sintetico --bn-momento 0.99 --saida resultado-bn099
"$PB_DIR/.venv-cnn/bin/python" curvas.py --pasta resultado-bn099 --saida resultado-bn099/curvas.png
```

Se a sua curva de validação ficar colada num valor igual a 1/3 (ou à fração da classe mais comum) enquanto a de treino sobe, é isto.

## O fluxo com o MetaDrive

Quatro passos, três Pythons, um terminal por bloco. Os blocos rodam em sequência, cada um depois de o anterior terminar.

**Terminal A — capturar.** Precisa do venv do MetaDrive (`aula17-metadrive`, seção "Instalar o MetaDrive"). Cinco sementes de 100 quadros, em pastas separadas: uma semente é uma estrada, e 500 quadros dela são 500 vistas do mesmo trecho. Uns 23 minutos com renderização por software. Se o `obstaculo` sair vazio, aumente `--trafego` e `--acidentes` (o README da `aula17-metadrive` explica) e diga no relatório o que mudou:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
for s in 7 8 9 10 11; do "$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py --frames 100 --semente "$s" --saida "quadros-s$s"; done
```

**Terminal B — rotular.** Com o `python3` **do sistema**, porque a janela precisa do OpenCV do apt. Uma pasta de cada vez; feche com `q` e ele grava, e se reabrir na mesma pasta continua do primeiro quadro que você ainda não revisou:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
python3 rotular.py --pasta ../aula17-metadrive/quadros-s7
```

A janela mostra o quadro ampliado 2×, a sugestão do `estado.csv` e o rótulo atual (verde se igual à sugestão, laranja se você mudou). **1 / 2 / 3** escolhem `via_livre` / `obstaculo` / `cruzamento` e avançam; **Enter** (ou espaço) aceita o que está mostrado; **setas** (ou **a** / **d**) andam sem mudar; **s** grava; **q**, **Esc** ou **Ctrl+C** gravam e saem. Maiúsculas (CapsLock) e o teclado numérico também valem.

**As teclas valem na janela ou no terminal** de onde você chamou o script — a primeira linha impressa diz isso. Clicar na janela não é obrigatório: se o foco ficou no terminal, é ali que as teclas são lidas, e nada é ecoado nem sobra para o shell depois. A cada passo o terminal mostra uma linha como `  7/20 quadro018.png -> obstaculo (sugerido via_livre)`, e assim há retorno mesmo com a janela escondida atrás de outra. Se uma tecla não fizer nada, o terminal imprime `tecla sem funcao: codigo N (0xHEX)`: anote esse código e mande junto com a descrição do problema — é o que diz qual tecla o seu OpenCV está entregando.

O `rotulos.csv` sai com quatro colunas, `arquivo,classe,sugerido,revisado`. `revisado` é 1 só nos quadros em que você apertou 1/2/3 ou Enter; nos outros, a `classe` é a sugestão que ninguém olhou. Na volta, só as linhas com `revisado=1` contam como revisadas; um `rotulos.csv` gravado pela versão anterior do script, sem essa coluna, é lido como "nada revisado", com aviso (e, se ele tiver alguma `classe` diferente da sugestão, é copiado antes para `rotulos.antigo.csv`). No fim o script imprime quantos quadros você revisou e **quantos diferem da sugestão** — esse é o número que vai para o relatório. O `treinar.py` lê só `arquivo` e `classe`.

Se a janela não abrir ou não responder (o WSLg falhou em sala, por exemplo), o `--sem-janela` faz a mesma revisão só pelo terminal, sem `imshow`: a cada passo imprime o arquivo, a sugestão e o rótulo atual. Abra o PNG num visualizador ao lado, se precisar ver o quadro:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
python3 rotular.py --pasta ../aula17-metadrive/quadros-s7 --sem-janela
```

Sem tela (num servidor, ou se o WSLg estiver desligado), há o `--so-sugestao`, que grava a sugestão sem abrir janela — e diz, na saída, que ninguém olhou:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
python3 rotular.py --pasta ../aula17-metadrive/quadros-s7 --so-sugestao
```

**Por que a revisão é obrigatória, e por que não rotular com a própria rede.** A sugestão é geometria sobre o estado do simulador, não visão: chama de cruzamento os metros *antes* do cruzamento, não vê se o carro da frente estava escondido por uma curva, ignora o carro da faixa vizinha que ocupa o meio da imagem. Se ninguém olhou, a rede aprende a regra do script, e a acurácia mede quanto ela imita o script. E a tentação seguinte — revisar 60, treinar, e deixar a rede rotular os outros 440 — é circular: o rótulo é a resposta contra a qual a rede é **medida**. Se quem escreve a resposta é a rede, a matriz de confusão mede quanto a rede concorda consigo mesma.

**Terminal C — treinar e desenhar.** O `--pasta` aceita várias pastas; cada uma tem o seu `rotulos.csv`, e a divisão treino/validação é feita sobre o conjunto inteiro:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta ../aula17-metadrive/quadros-s7 ../aula17-metadrive/quadros-s8 ../aula17-metadrive/quadros-s9 ../aula17-metadrive/quadros-s10 ../aula17-metadrive/quadros-s11 --saida resultado-metadrive
"$PB_DIR/.venv-cnn/bin/python" curvas.py --pasta resultado-metadrive --saida resultado-metadrive/curvas.png
```

Os quadros de 320×240 são reduzidos para 128×96 na leitura (`--tamanho` muda isso). Leia a tabela de cima para baixo: primeiro a contagem por classe e a linha de base, depois a acurácia, e por último — mas com mais peso — o pior recall e a matriz.

## O que foi e o que não foi verificado

**Rodou neste container** — Linux sem GPU, 2 núcleos, Python 3.10.20 instalado pelo `uv`, as versões da tabela do ambiente:

a criação do venv **sem** `--system-site-packages` e a instalação com `uv pip install --python` (11 s na segunda tentativa; a primeira travou no download e foi interrompida aos 10 min); o `gerar_sintetico.py` com 500 imagens equilibradas e com `54:0:6`, e o determinismo byte a byte; o `treinar.py` em quatro configurações de 20 épocas — equilibrado e `54:0:6`, cada um com momentum 0,9 e 0,99 —, uns 90 s de parede cada; a reprodução, em outro processo, da mesma tabela equilibrada; o modelo da rodada quebrada avaliado com `training=True` e `False`; a avaliação dos modelos do `54:0:6` sobre os 167 obstáculos; o `curvas.py`; o `rotular.py --so-sugestao` sobre os 12 quadros reais da `aula17-metadrive/amostra`, e o `treinar.py --epocas 1` sobre eles; o laço da janela do `rotular.py` sob Xvfb, com o OpenCV 5.0 (backend Qt) do Python do container, recebendo teclas de verdade por XTest na janela (2, seta direita, Enter, q) e, ao mesmo tempo, pelo terminal (3, seta esquerda), gravando exatamente o CSV esperado; a tradução dos códigos de tecla do GTK, do Qt e do Windows (com NumLock, CapsLock e teclado numérico) como função pura; a revisão pelo terminal (`--sem-janela`) dirigida por um pseudoterminal, com 1, setas, 2, 3, Esc e Ctrl+C, conferindo o `rotulos.csv`, a retomada pela coluna `revisado` e que o terminal volta ao estado de antes; o `testar.py` (121 conferências, uns 65 s); e os conferidores `conferir-caminhos.py` e `conferir-comandos.py` do repositório.

**Não rodou, e é o que você vai encontrar:**

a CNN sobre **quadros do MetaDrive de verdade** além dos 12 da amostra — e esses 12 só com uma época, para provar que o caminho não quebra. Nenhum número desta página vale para o MetaDrive. As imagens do MetaDrive têm céu com nuvens, terreno, faixas finas e escuras; a rede pode precisar de mais épocas, de mais resolução ou de outra coisa, e o seu relatório é o primeiro lugar onde isso vai ser medido.

o venv **no WSL2 com Ubuntu 22.04**. Aqui o 3.10 era do `uv`; no seu, o `uv venv --python 3.10` deve achar o Python do sistema, e o `uv` deve resolver as mesmas versões. É a expectativa, não o experimento.

o **`_ARRAY_API not found`** descrito na seção do ambiente. O container não tinha `python3-opencv` do apt para Python 3.10, e o erro não foi reproduzido aqui; o argumento é o mesmo que a disciplina já mediu com o `cv_bridge`.

o `rotular.py` com **o OpenCV do apt (4.5.4, backend GTK) e o WSLg**. No primeiro ensaio no WSL2, as teclas apertadas na janela não chegaram ao programa; a hipótese é que o GTK entrega o código com os bits dos modificadores (NumLock soma 0x100000: a tecla `1` chega como 1048625), e o script agora descarta esses bits — mas isso não foi conferido numa janela GTK. Também não foi conferido se esse OpenCV diz quando a janela é fechada no X (se não disser, o script avisa e você sai com **q**). Se alguma tecla não responder na janela, ela continua valendo no terminal, e a linha `tecla sem funcao: codigo N` diz o código que chegou.

a velocidade do treino **no seu notebook**. Aqui foram 38–45 s por rodada de 20 épocas em 2 núcleos.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `_ARRAY_API not found` seguido de `numpy.core.multiarray failed to import` | o venv enxerga o sistema e um pacote compilado contra NumPy 1.x (o `cv2` ou o `matplotlib` do apt) foi importado ao lado do NumPy 2 do TensorFlow. Apague o `.venv-cnn` e recrie **sem** `--system-site-packages` |
| `Could not find cuda drivers on your machine, GPU will not be used` | aviso inofensivo do TensorFlow ao não achar GPU; o treino roda na CPU. Não apareceu aqui, com o `tensorflow-cpu` |
| `oneDNN custom operations are on` / `This TensorFlow binary is optimized to use...` | informação do TensorFlow ao subir; ignore |
| `NodeDef mentions attribute use_unbounded_threadpool which is not in the op definition` | linha de log do TensorFlow 2.21 no `tf.data`, sem efeito; ignore |
| `triggered tf.function retracing` | aviso do Keras ao chamar `predict` em arrays de tamanhos diferentes no fim do treino; ignore |
| `No module named cv2` ou `No module named tensorflow` | rodou com `python3` em vez de `"$PB_DIR/.venv-cnn/bin/python"`, ou faltou o pacote na linha do `uv pip install` |
| `este OpenCV nao abre janela (e o headless do venv?)` | rodou o `rotular.py` com o Python do venv; é com o `python3` do sistema. Sem tela, use `--so-sugestao` |
| a janela do `rotular.py` não abre no WSL2 | o WSLg está desligado (`echo $DISPLAY` vazio); use `--sem-janela` e revise pelo terminal, olhando os PNG num visualizador |
| as teclas aparecem no terminal (`^[[C`, `1`) e o `rotular.py` não reage | versão antiga do script, que só lia a janela: atualize. A atual lê as teclas também no terminal |
| `tecla sem funcao: codigo N (0xHEX)` | a tecla chegou, mas com um código que o script não conhece; ela segue valendo no terminal. Mande o código |
| ``aviso: ... nao tem a coluna `revisado` `` | `rotulos.csv` da versão anterior: nada conta como revisado e a revisão recomeça do primeiro quadro |
| `nao achei .../aula13-veicular/cena_estrada.py` | a pasta da Aula 13 não está ao lado desta: refaça o bloco de download |
| validação colada em 0,33 (ou na fração da classe mais comum) com treino subindo | BatchNormalization com momentum alto para o tamanho do conjunto: a armadilha 4. O padrão do `treinar.py` é 0,9 |
| `aviso: alguma classe tem 1 exemplo so -- divisao sem estratificar` | uma classe tem um único quadro; a validação pode sair sem ela. Capture mais |
| recall `n/a` e uma linha de zeros na matriz | a classe não está na validação — e, se também não está no treino, a rede nunca vai respondê-la |
| a curva de treino `com` abaixo da de validação | esperado: o treino é medido sobre imagens aumentadas e com Dropout ligado |
| `--proporcao 54:6:0` deu seis obstáculos | a ordem é a do enunciado, `via_livre:obstaculo:cruzamento`; a amostra do MetaDrive é `54:0:6` |

## Como adequar ao seu projeto

**Rotule primeiro, treine depois, e conte as correções.** O número de linhas em que `classe` difere de `sugerido` no `rotulos.csv` é a evidência de rotulagem que o item 4 pede. Zero correções em 500 quadros é suspeito, não é mérito.

**Mude um hiperparâmetro de cada vez, e antes de olhar a validação.** Se a rede não aprender nos quadros do MetaDrive, a ordem razoável é: mais épocas (`--epocas 40`), depois mais resolução (`--tamanho 160x120`), depois a arquitetura no topo do `treinar.py`. Escreva no relatório o que mudou e por quê, e use a **mesma** semente nas duas rodadas que vai comparar.

**Se o `obstaculo` continuar raro, não treine assim mesmo.** O caminho honesto é capturar mais (tráfego, acidentes, sementes). O caminho de conta — `class_weight` no `fit`, ou repetir os exemplos raros — existe e funciona, mas não cria o que a câmera não viu: 6 obstáculos repetidos 50 vezes são 6 obstáculos.

**O modelo `.keras` não roda dentro de um nó ROS 2 com este venv.** O venv não tem `rclpy` nem `cv_bridge`, e não deve ter. Se um dia o classificador for para o robô, isso é outra conversa — de versão, de NumPy e de ambiente —, e não faz parte do item 4.

## O que cada arquivo faz

| Arquivo | Papel | Roda com |
|---|---|---|
| `gerar_sintetico.py` | desenha N imagens das três classes sobre a estrada do `cena_estrada.py` (importado pelo caminho) e grava `imgNNNN.png` + `rotulos.csv`. `--n`, `--proporcao`, `--saida`, `--semente`, `--tamanho` | venv da CNN (ou qualquer Python com OpenCV) |
| `rotular.py` | lê o `estado.csv` do `capturar_frames.py`, propõe o `rotulo_sugerido` e abre a revisão por teclado (na janela ou no terminal); grava `arquivo,classe,sugerido,revisado`. `--pasta`, `--saida`, `--sem-janela`, `--so-sugestao` | `python3` do sistema |
| `treinar.py` | divide uma vez, treina o mesmo núcleo sem e com `RandomRotation`/`RandomZoom`/`RandomFlip`, e grava históricos, modelos, matrizes, `divisao.csv`, `tabela.txt` e `exemplos_augmentation.png`. `--pasta` (uma ou várias), `--rotulos`, `--saida`, `--epocas`, `--semente`, `--tamanho`, `--lote`, `--bn-momento` | venv da CNN |
| `curvas.py` | acurácia e perda, treino (tracejado) e validação (cheio), sem (azul) e com (laranja) augmentation, no mesmo eixo. `--pasta`, `--saida`, `--titulo` | venv da CNN |
| `testar.py` | 7 grupos: higiene dos `.py`, o sintético, o `rotular.py`, a mesma inicialização, o treino de 1 época em duas pastas, o treino sobre a amostra real, as curvas. Sai com 0 ou 1 | venv da CNN |
| `amostra/tabela.txt`, `curvas.png`, `matriz_sem.png`, `matriz_com.png` (+ `.csv`) | a rodada equilibrada de 20 épocas desta página | — |
| `amostra/exemplos_augmentation.png` | uma imagem por classe e quatro versões aumentadas: a faixa amarela indo para a direita, as faixas inventadas nos cantos | — |
| `amostra/desequilibrado/` | a rodada `54:0:6` com a rede sadia (1,000 nas duas) | — |
| `amostra/desequilibrado-bn-0.99/` | a rodada `54:0:6` com a rede quebrada: 0,900 respondendo sempre `via_livre` | — |
| `amostra/bn-0.99/` | a rodada equilibrada com `momentum=0.99`: treino 0,913, validação 0,330 | — |

Nenhum modelo `.keras` e nenhuma das 500 imagens estão no repositório: os dois se refazem em menos de dois minutos com os comandos acima, e são idênticos aos daqui.

## Licença

MIT, como todo o diretório `exemplos/`.
