# Exemplo — `aula17-metadrive`

**Aula 17 · Etapa 9.** O item 3 do TP4 pede o pipeline de faixas no MetaDrive — máscara HSV, Canny e Hough, sobreposto ao frame da câmera sintética — e termina assim: *"Implemente também detecção de formas geométricas (sinais de trânsito) com Hough Circle e Harris Corner."* O item 4 começa por *"Colete 500 frames rotulados do MetaDrive em 3 classes (via livre / obstáculo / cruzamento)."* As duas coisas começam no mesmo lugar — uma pasta de quadros PNG com uma tabela ao lado dizendo o que havia em cada um — e este exemplo é exatamente isso: o MetaDrive subindo sem janela, um motorista automático, os quadros e o `estado.csv` que vira o rótulo.

> ## Leia isto antes de qualquer coisa
>
> **A primeira execução do MetaDrive nesta disciplina** foi feita num container Linux sem GPU, com Python 3.10 instalado pelo `uv` e um servidor X virtual (Xvfb), e as saídas desta página saíram **de lá**. Em 09/11/2026 a mesma receita rodou também num WSL2 com Ubuntu 22.04 e WSLg (a máquina do professor), **sem Xvfb** e com a GPU: a captura foi umas **20 vezes mais rápida**, o `estado.csv` saiu igual, e as faixas **não** — a seção **"O que foi e o que não foi verificado"**, no fim, separa linha a linha o que foi visto onde.
>
> E dois achados que mudam o que o material das aulas anteriores dizia: o detector da Aula 13, **sem mudar nada**, encontra **zero** segmentos nos quadros do MetaDrive; e **não há placa nenhuma** na cena do MetaDrive. As duas coisas estão medidas abaixo.

```
aula17-metadrive/
├── capturar_frames.py   # sobe o MetaDrive sem tela, dirige sozinho, grava PNG + estado.csv
├── medir_faixas.py      # o faixas.py da Aula 13, sem mudar uma linha, com duas configuracoes
├── formas.py            # HoughCircles e cornerHarris -- e o que ha na cena para achar
├── testar.py            # 7 grupos; o setimo so roda se o MetaDrive estiver instalado
└── amostra/             # 12 dos 60 quadros da semente 7, o estado.csv inteiro e duas sobreposicoes
```

A arquitetura cabe em duas linhas, e o contrato entre elas é a pasta:

```
   venv do MetaDrive (Python 3.10)               python3 do sistema (apt)

   capturar_frames.py --frames 500  ------->  quadroNNN.png + estado.csv
                                                    |
                                                    +--> medir_faixas.py   (item 3, faixas)
                                                    +--> formas.py         (item 3, formas)
                                                    +--> a sua CNN         (item 4)
```

Só o `capturar_frames.py` precisa do MetaDrive. O resto lê PNG com o OpenCV do apt e roda em qualquer lugar — inclusive sobre a `amostra/` que vem no repositório, antes de você instalar qualquer coisa.

## Baixar

O `medir_faixas.py` importa o `faixas.py` da Aula 13 **pelo caminho**, sem copiá-lo, então as duas pastas descem juntas e lado a lado. Tudo pende do `git clone` pelo `&&`: se o clone falhar, nenhum `rm -rf` roda.

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y python3-numpy python3-opencv

mkdir -p "$PB_DIR" && cd /tmp && rm -rf pb-a17 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a17 && \
  rm -rf "$PB_DIR/aula17-metadrive" "$PB_DIR/aula13-veicular" && \
  cp -r pb-a17/exemplos/aula17-metadrive "$PB_DIR/" && \
  cp -r pb-a17/exemplos/aula13-veicular "$PB_DIR/"
```

## Instalar o MetaDrive

O MetaDrive vai num ambiente **próprio**, criado com `uv`, como todo ambiente Python desta disciplina: nunca `pip install` solto (cai em `--user` e reescreve o NumPy e o OpenCV que o ROS 2 usa), nunca `sudo pip`, nunca `python3 -m venv`. O ambiente fica em `$PB_DIR/.venv-metadrive`, **fora** da pasta do exemplo, de propósito: o bloco de download apaga e recria `aula17-metadrive/`, e um venv de 1 GB lá dentro iria junto.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
uv venv --python 3.10 --system-site-packages .venv-metadrive
uv pip install --python .venv-metadrive/bin/python "metadrive-simulator==0.4.3"
```

O `--python 3.10` não é enfeite. O MetaDrive 0.4.3 depende de `panda3d==1.10.13`, e esse Panda3D só tem wheel até o Python 3.11. Num Python 3.12 ou 3.13 o `uv` recusa com uma frase clara — `panda3d==1.10.13 has no wheels with a matching Python ABI tag (e.g., cp313)` — e foi exatamente o que aconteceu no container onde isto foi testado, que tinha 3.13 como padrão. No Ubuntu 22.04 o Python do sistema já é o 3.10, e a opção só confirma; se o seu WSL tiver outro, o `uv` baixa um 3.10 sozinho.

Nesta máquina a instalação levou **18 s** e resolveu `panda3d 1.10.13`, `gymnasium 1.4.0`, `numpy 2.2.6`, `opencv-python 5.0.0.93`, `pygame 2.6.1` e mais uns quarenta pacotes; o venv ficou com **843 MB**. Na **primeira** execução o MetaDrive baixa sozinho os *assets* (modelos, texturas, 168 MB) para dentro do próprio pacote — não precisa de `pull_asset`. Repare que o NumPy 2 e o OpenCV 5 ficam **dentro** do venv; o `python3` do sistema continua com os do apt, e é ele que roda o resto do exemplo.

Agora as duas conferências que o próprio pacote oferece. Rode-as de uma pasta que **não** tenha uma subpasta chamada `metadrive` — senão o `python -m metadrive...` importa a pasta em vez do pacote:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
"$PB_DIR/.venv-metadrive/bin/python" -m metadrive.examples.profile_metadrive
"$PB_DIR/.venv-metadrive/bin/python" -m metadrive.examples.verify_headless_installation --camera rgb
```

A primeira roda 10 000 passos de física **sem** imagem. Aqui ela terminou assim:

```
[INFO] MetaDrive version: 0.4.3
...
Finish 10000/10000 simulation steps. Time elapse: 40.8526. Average FPS: 491.9347, Average number of vehicles: 4.7913
Total Time Elapse: 40.853, average FPS: 491.932, average number of vehicles: 4.791.
```

A segunda é a que importa, porque liga a câmera. **Sem servidor X ela falha**, e com uma mensagem que não ajuda nada:

```
[INFO] Render Mode: offscreen
[INFO] Known Pipes: glxGraphicsPipe
  File ".../metadrive/third_party/simplepbr/__init__.py", line 287, in _setup_tonemapping
    self.tonemap_quad.set_shader(tonemap_shader)
AttributeError: 'NoneType' object has no attribute 'set_shader'
```

A leitura correta é: o Panda3D do MetaDrive 0.4.3 só conhece o `glxGraphicsPipe`, que precisa de um X mesmo para desenhar fora da tela; sem X o *buffer* não abre, o pós-processamento recebe `None`, e o erro aparece três camadas acima da causa. **No WSL2 com WSLg o `DISPLAY` já vale `:0`** e isso não deve acontecer. Num servidor sem tela — ou se o seu WSLg estiver desligado —, o remédio que funcionou aqui foi o Xvfb, um X que desenha na memória:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
sudo apt install -y xvfb
cd "$PB_DIR/aula17-metadrive"
xvfb-run -a -s "-screen 0 1280x1024x24" "$PB_DIR/.venv-metadrive/bin/python" -m metadrive.examples.verify_headless_installation --camera rgb
```

```
[INFO] Sensors: [lidar: Lidar(), side_detector: SideDetector(), lane_line_detector: LaneLineDetector(), rgb_camera: RGBCamera(256, 256)]
[INFO] Render Mode: offscreen
[WARNING] You are using too large buffer! The height is 256, and width is 256. ...
rgb_camera Test result:
Headless mode Offscreen render launched successfully!
images named 'rgb_camera_from_observation.png' and 'rgb_camera_from_buffer.png' are saved to .../site-packages/metadrive/examples.
```

Os dois PNG saem **dentro do pacote instalado**, não na pasta atual. O aviso de *buffer* grande é para quem treina aprendizado por reforço com milhões de quadros; para nós, 256×256 é pequeno.

Tentei também o caminho sem X nenhum — o pipe EGL do Panda3D (`load-display p3headlessgl` num `Config.prc` apontado por `PANDA_PRC_DIR`), com e sem `EGL_PLATFORM=surfaceless`, `LIBGL_ALWAYS_SOFTWARE=1` e as variáveis `MESA_GL_VERSION_OVERRIDE`. O Panda3D abre o `eglGraphicsBuffer`, e o MetaDrive cai **no mesmo** `set_shader`. Não insisti: o Xvfb resolve, e no WSL2 o WSLg já é o X.

## Capturar

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
"$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py --frames 60 --saida quadros
```

Se não houver `DISPLAY`, o script para **antes** de criar o ambiente e diz a linha do `xvfb-run` — em vez de deixar o `set_shader` aparecer. A saída, nesta máquina, foi:

```
forma da imagem : (240, 320, 3), uint8, canais BGR
quadros gravados: 60 em quadros (+ estado.csv)
tempo simulado  : 18.0 s (180 passos de 0.10 s)
tempo de parede : 164.2 s -> 0.37 quadros/s, 1.10 passos/s
```

**Como se pede a imagem.** A documentação do MetaDrive não diz; o código instalado diz (`metadrive/obs/image_obs.py`, `metadrive/component/sensors/base_camera.py` e `metadrive/tests/test_installation.py`). O mínimo que devolve um quadro como array é isto — rodado aqui, imprime `(240, 320, 3, 1)` para a observação e `(240, 320, 3) uint8` para o quadro:

```python
from metadrive.envs.metadrive_env import MetaDriveEnv
from metadrive.component.sensors.rgb_camera import RGBCamera

env = MetaDriveEnv(dict(
    use_render=False, image_observation=True, norm_pixel=False, stack_size=1,
    sensors={"rgb_camera": (RGBCamera, 320, 240)},          # (classe, LARGURA, ALTURA)
    vehicle_config={"image_source": "rgb_camera"},
    interface_panel=[], window_size=(320, 240),
    start_seed=7))                   # reset(seed=) so aceita sementes em [start_seed, +num_scenarios)
obs, _ = env.reset(seed=7)
obs, *_ = env.step([0.0, 0.0])
quadro = obs["image"][..., -1]       # (240, 320, 3) uint8, BGR -- direto no cv2.imwrite
env.close()
```

Quatro detalhes que cobram caro se errados. A observação é um **dicionário** `{"image", "state"}`, e a imagem tem **quatro** eixos — `(altura, largura, 3, pilha)` —, porque o MetaDrive empilha os últimos quadros para o aprendizado por reforço; com `stack_size=1` a pilha tem um só, e `[..., -1]` o tira. Sem `norm_pixel=False` a imagem vem em `float32` de 0 a 1, e o `cv2.imwrite` grava um PNG preto. A ordem dos canais é **BGR**, a mesma do OpenCV — o `get_image()` da câmera chama de `"bgr"` o que devolve sem inverter, e o teste de instalação grava o array direto com `cv2.imwrite`; o `testar.py` confere isso pelo céu, que sai azul no canal 0. E o esboço que estava no README da Aula 13, `obs['image'][..., ::-1]`, inverte o eixo da **pilha**, não o dos canais: com pilha de 3 ele devolve um array `(H, W, 3, 3)` que nenhum detector aceita.

**Quem dirige é o `IDMPolicy` do próprio MetaDrive** (`agent_policy=IDMPolicy`): segue a faixa, freia atrás de quem está na frente e troca de faixa sozinho. A ação `[0, 0]` que o script passa ao `step` é ignorada. Com ele a trajetória depende só da semente, e o `testar.py` prova: duas capturas com a mesma semente dão o **mesmo `estado.csv`** e, nesta máquina, PNG idênticos byte a byte.

**O mapa é fixo** — `SXSTSC`: reta, cruzamento de quatro vias, reta, cruzamento em T, reta, curva. Com mapa sorteado, muita semente não passa por cruzamento nenhum nos primeiros quinhentos quadros, e a classe "cruzamento" do item 4 fica vazia. Com `--passo 3` (um quadro a cada 0,3 s simulado, o padrão), a semente 7 chega ao primeiro cruzamento no quadro 55.

**O terreno é obrigatório**, e isto é contraintuitivo. Com `show_terrain=False` o passo fica 2,3× mais rápido (2,5 contra 1,1 passos por segundo), e o asfalto sai **branco e liso**: as faixas pintadas fazem parte da textura do chão. A opção `--sem-terreno` existe para quem quiser quadros para a CNN e não para as faixas.

**O `estado.csv`** tem uma linha por quadro, e as colunas são a base do rótulo semiautomático do item 4:

| coluna | o que é | de onde vem |
|---|---|---|
| `indice`, `arquivo`, `passo`, `t_s` | qual quadro, e em que instante simulado | o laço do script; `t_s = passo × 0,02 s × 5` |
| `x_m`, `y_m`, `vel_kmh`, `rumo_rad` | onde o carro estava, a que velocidade, para onde apontava | `env.agent.position`, `.speed_km_h`, `.heading_theta` |
| `bloco` | a letra do bloco do mapa em que a faixa atual **termina** | o nome do nó do grafo de vias: `2X0_0_` é o bloco 2, tipo X |
| `em_cruzamento` | 1 se o bloco é X, T ou O | `bloco` |
| `veiculo_a_frente`, `dist_a_frente_m`, `objeto_a_frente` | o objeto mais próximo num corredor de 30 m × 3,5 m à frente, e a classe dele | geometria sobre `env.engine.get_objects()`, sem olhar a imagem |
| `rotulo_sugerido` | `cruzamento`, `obstaculo` (algo a menos de 20 m) ou `via_livre` | a regra `rotulo()`, com os limiares no topo do script |

O rótulo é **sugerido**, não verdade. A aproximação de um cruzamento já conta como cruzamento (é o bloco em que a faixa termina), e um carro na faixa ao lado, a 15 m, que aparece no meio do quadro, **não** conta como obstáculo. Os 60 quadros da semente 7 saíram com 54 `via_livre`, 6 `cruzamento` e **nenhum** `obstaculo` — o IDM mantém distância do carro da frente. Para o item 4, olhe os quadros, corrija o que discordar e diga no relatório quantas linhas você corrigiu.

## Medir as faixas

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
python3 ../aula13-veicular/faixas.py --pasta amostra
python3 medir_faixas.py --pasta amostra --sobreposicao amostra/figuras/faixas-sobreposicao.png --quadro 4
```

A primeira linha é o detector da Aula 13 **como ele é**, e o resultado é a aula: **0 segmentos Hough em todos os 60 quadros**. Não é defeito do Hough. São três coisas, todas medidas nos pixels:

1. **A tinta do MetaDrive é escura.** A pintura branca chega no máximo a V = 149 no HSV, e o limiar da Aula 13 é `branco_v_min = 150`. Um ponto de diferença, e a máscara branca fica vazia.
2. **A faixa amarela central tem 1 pixel de largura** a 320×240 (2 px a 640×480), e a abertura morfológica 3×3 da etapa de cor apaga tudo que tem menos de 3 px. A linha está lá — `H = 27, S = 255, V = 149`, dentro de todos os limiares — e some na limpeza de sal e pimenta.
3. **O contraste dela no cinza é de uns 30 níveis** contra o asfalto, pouco para `Canny(50, 150)`.

O `medir_faixas.py` roda o mesmo `detectar_faixas()` uma segunda vez com a configuração **ajustada**, declarada no topo do arquivo antes de medir: amplia o quadro 3× por vizinho mais próximo (a linha passa a ter 3 px e sobrevive à abertura), `branco_v_min = 130`, `amarelo_v_min = 70`, `canny = (20, 60)`. Nos 12 quadros da amostra:

```
quadro          PADRAO (A13)    AJUSTADA
quadro000.png     0 seg  . .     14 seg  E D
quadro005.png     0 seg  . .     13 seg  E D
quadro010.png     0 seg  . .     14 seg  E D
quadro015.png     0 seg  . .     18 seg  E D
quadro020.png     0 seg  . .     14 seg  E D
quadro025.png     0 seg  . .     16 seg  E D
quadro030.png     0 seg  . .     16 seg  E D
quadro035.png     0 seg  . .     17 seg  E D
quadro040.png     0 seg  . .     16 seg  E D
quadro045.png     0 seg  . .     16 seg  E D
quadro050.png     0 seg  . .     11 seg  E D
quadro055.png     0 seg  . .      0 seg  . .
PADRAO  : 12 quadros | segmentos Hough por quadro min 0, mediana 0, max 0 | esq 0, dir 0, ambas 0
AJUSTADA: 12 quadros | segmentos Hough por quadro min 0, mediana 16, max 18 | esq 11, dir 11, ambas 11
```

Nos 60 quadros completos a ajustada acha as duas faixas em **51**, a esquerda em 52 e a direita em 51, com mediana de 15 segmentos por quadro. Os quadros sem faixa são os do cruzamento, no fim: dentro do cruzamento não há pintura, e o detector diz "não achei" em vez de inventar — que é o comportamento certo.

A esquerda do carro é a **linha amarela dupla** (a semente 7 dirige na faixa da esquerda) e a direita é a tracejada branca. A `faixas-sobreposicao.png` da amostra mostra as duas, com a área navegável pintada entre elas, no tamanho ampliado (960×720) — reduzida de volta, o texto do `desenhar()` da Aula 13 fica ilegível.

Continua valendo o que a Aula 13 disse: **sem verdade não há erro a medir**. A tabela diz quantas vezes cada faixa foi achada, não se ela foi achada no lugar certo. A medição continua com a cena sintética e o `avaliar_faixas.py`; o MetaDrive é a prova de que a pipeline sobrevive a uma imagem que você não desenhou — e, como se viu, ela só sobrevive depois de ajustada.

## As formas

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
python3 formas.py --pasta amostra --sobreposicao amostra/figuras/formas-sobreposicao.png --quadro 8
python3 formas.py --pasta amostra --param2 15
```

**O MetaDrive não tem placa de trânsito.** Nenhuma classe de placa existe no pacote instalado. O mapa procedural também não tem semáforo — há um modelo de semáforo nos *assets*, mas só o `ScenarioEnv`, que reproduz cenários reais do Waymo e do nuScenes, o usa. O que existe na cena do `MetaDriveEnv` é isto, contado num episódio da semente 7: 24 cones (`TrafficCone`), um triângulo de advertência (`TrafficWarning`), uma barreira (`TrafficBarrier`) e veículos de cinco tamanhos — com `accident_prob=1.0`, que é o padrão do `capturar_frames.py` justamente para os cones aparecerem.

O script diz isso na primeira linha da saída, e o resultado bate:

```
cena: o MetaDrive (mapa procedural) NAO TEM PLACA nem semaforo; ha cones, triangulos, barreiras e veiculos.
quadro          circulos   circ. no ceu  cantos cantos na pista
quadro000.png          0              0      90              68
quadro005.png          0              0     126             108
quadro010.png          0              0     136             113
quadro015.png          0              0     100              82
quadro020.png          0              0      85              66
quadro025.png          0              0     123              98
quadro030.png          0              0     131             104
quadro035.png          0              0     132             113
quadro040.png          0              0     101              65
quadro045.png          0              0     112              87
quadro050.png          0              0      59              43
quadro055.png          0              0     146              45
total: 12 quadros, 0 circulos (0 acima do horizonte, falsos por construcao), cantos por quadro min 59, mediana 123, max 146
PLACA: nenhuma -- o MetaDrive nao tem placa; nenhum circulo acima e placa.
```

**Hough Circle: zero, e é o número certo.** Com `param2 = 30` (votos mínimos), nenhum círculo nos 60 quadros. Baixando para 20 aparecem 16 círculos em 15 quadros, 12 deles **acima do horizonte** — nuvem; com 15, são 151, 89 no céu. Todo círculo que aparece é falso positivo, e a coluna "no céu" existe para medir isso sem precisar de verdade nenhuma: acima do horizonte não há nada redondo nesta cena. Para provar que o detector funciona quando há o que achar, o `testar.py` desenha uma placa redonda num fundo cinza e exige um círculo no centro certo, com o raio certo.

**Harris: muitos cantos, e isso não prova nada sozinho.** O limiar é **relativo** ao maior valor do quadro (1%), e limiar relativo garante canto em qualquer imagem — até numa parede lisa, o maior valor passa. Os cantos que importam estão na sobreposição: as quinas do caminhão, a base dos cones, a ponta de cada tracejado da faixa. Cada aglomerado do mapa do Harris conta uma vez (componente conexo), senão um canto viraria nove pixels. O teste desenha um quadrado preto e exige exatamente 4.

O que dizer no relatório do item 3: *a cena não tem placa; o Hough Circle não achou círculo (e os que acha com limiar baixo estão no céu); o Harris acha os cantos dos objetos que existem — veículos e cones.* Isso é resposta honesta ao enunciado. Inventar uma placa não é.

## O que foi e o que não foi verificado

Esta seção existe porque a diferença importa, e porque material de aula que finge ter sido testado custa caro na hora da entrega.

**Rodou neste container** — Ubuntu sem GPU, 2 núcleos, Python 3.10.20 instalado pelo `uv` (o padrão da máquina era 3.13, recusado pelo `panda3d`), Mesa 25.2 com `llvmpipe` (renderização por software), Xvfb já instalado:

a instalação de `metadrive-simulator==0.4.3` com `uv pip install --python`, em 18 s; o download automático dos *assets* na primeira execução; o `profile_metadrive` (491,9 FPS de física, sem imagem); o `verify_headless_installation --camera rgb` **por baixo do `xvfb-run`**, e a falha literal sem ele; a falha do caminho EGL; o `capturar_frames.py` gravando 60 quadros (240, 320, 3) uint8 BGR em 164 s de parede, a 1,1 passos por segundo com terreno; a captura de 6 quadros a 640×480 (0,9 passos por segundo); o determinismo do `estado.csv` e dos PNG com a mesma semente; o `faixas.py` da Aula 13 dando 0 segmentos e o `medir_faixas.py` dando as duas faixas em 51 de 60; o `formas.py` com 0 círculos e 30 a 180 cantos por quadro; o `testar.py` com os sete grupos, inclusive a captura de verdade do grupo 7 (36 s); e os três conferidores do repositório.

**Rodou num WSL2, em 09/11/2026** — Ubuntu 22.04, WSLg, a GPU do Windows, **sem Xvfb**, a receita desta página:

- a **velocidade**: 20 quadros a 6,88 quadros/s (o processo inteiro, com a carga do MetaDrive, em 23 s) e 60 quadros a 8,83 quadros/s. Contra 0,37 quadros/s no container, 500 quadros passam de uns 23 minutos para 1 a 1,5 minuto. A diferença é a renderização: GPU contra Mesa `llvmpipe` (software) por baixo do Xvfb. **O seu número depende de qual dos dois você tem** — meça com os 20 primeiros quadros antes de planejar os 500;
- o **`estado.csv` da semente 7**, colunas 1 a 9, saiu **idêntico** ao da `amostra/` (o `diff` não acusou nada): o determinismo do estado entre duas máquinas foi visto uma vez;
- as **faixas**, e aqui a máquina mudou o resultado. Sobre a `amostra/` (quadros do container), o `faixas.py` e o `medir_faixas.py` deram o mesmo que aqui. Sobre os 60 quadros capturados **com GPU**, o mesmo código deu `PADRAO: esq 0, dir 51, ambas 0` (mediana de 4 segmentos) e `AJUSTADA: esq 52, dir 57, ambas 52` (mediana de 20). Com GPU a tracejada branca da direita passa no limiar da Aula 13 em 51 de 60 quadros, e a amarela dupla da esquerda em nenhum. É o caso "funciona na minha máquina" com números: o limiar é da fonte de imagem, e a renderização faz parte da fonte. **Meça os seus quadros**, não confie nos daqui.

**Não rodou em lugar nenhum, e é o que você vai encontrar:**

o MetaDrive **no WSL2 de outra máquina**, sem GPU utilizável pelo WSLg, ou com o WSLg desligado. Se o `verify_headless_installation` falhar com o `set_shader`, o `xvfb-run` deste README é o plano B, e ele roda em CPU — a velocidade passa a ser a do container.

o **Python 3.10 do Ubuntu** com `--system-site-packages`. Aqui o 3.10 era do `uv` e não tinha pacote de sistema nenhum para herdar. No seu, o venv enxerga o NumPy 1.21 e o OpenCV 4.5 do apt, e o `uv` instala o NumPy 2.2 e o OpenCV 5.0 **por cima, dentro do venv**. Deve funcionar — o venv tem precedência. No WSL2 de 09/11 a receita funcionou, mas não se anotou se o `uv` usou o 3.10 do Ubuntu ou baixou o dele.

o **clone do GitHub** (`git clone https://github.com/metadriverse/metadrive.git && pip install -e .`), que a documentação recomenda. O pin `0.4.3` do PyPI funcionou de primeira, e por isso o clone não foi tentado.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `panda3d==1.10.13 has no wheels with a matching Python ABI tag` | o venv foi criado com Python 3.12 ou 3.13: apague o `.venv-metadrive` e recrie com `uv venv --python 3.10 --system-site-packages` |
| `AttributeError: 'NoneType' object has no attribute 'set_shader'` | não há servidor X: `echo $DISPLAY` vazio. No WSL2, confira o WSLg; senão, `xvfb-run -a -s "-screen 0 1280x1024x24"` na frente do comando |
| `ERRO: nao ha DISPLAY` | é o `capturar_frames.py` antecipando a linha de cima, com a solução na mensagem |
| `No module named metadrive` rodando `python -m metadrive...` | você está numa pasta com uma subpasta `metadrive` (o clone do GitHub, por exemplo), ou usou o `python3` do sistema em vez do do venv |
| `metadrive nao instalado neste Python` | rodou `python3 capturar_frames.py`; é `"$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py` |
| o asfalto saiu branco, sem faixa | `--sem-terreno`: as faixas são textura do chão |
| o PNG saiu preto | `norm_pixel` ficou `True` e a imagem veio em float 0–1; o `capturar_frames.py` já passa `False` |
| `AssertionError: scenario_index (seed) should be in [0:1)` | `env.reset(seed=N)` sem `start_seed=N` na configuração: o ambiente só aceita sementes no intervalo dele |
| o PNG saiu com o céu laranja | alguém inverteu os canais: a observação já é BGR, grave direto |
| `faixas.py --pasta` dá 0 segmentos em tudo | é o esperado com a configuração da Aula 13 — use o `medir_faixas.py` e leia a seção das faixas |
| `nao achei .../aula13-veicular/faixas.py` | a pasta da Aula 13 não está ao lado desta: refaça o bloco de download, ou passe `--faixas CAMINHO` |
| o episódio termina antes dos N quadros | o carro bateu ou saiu da pista (`crash_vehicle`, `out_of_road`); o script avisa e grava o que tinha. Troque a `--semente` |
| a captura é lentíssima | renderização por software (Xvfb + llvmpipe): ~1 passo por segundo, 0,37 quadros/s; com a GPU pelo WSLg foram 7 a 9 quadros/s. Reduza `--largura/--altura` só se não for medir faixa |
| `You are using too large buffer!` | aviso para RL com milhões de quadros; ignore |

## Como adequar ao seu projeto

**Gere os 500 quadros do item 4 em várias sementes, não numa só.** Uma semente é uma estrada: 500 quadros dela são 500 vistas do mesmo trecho, e a CNN aprende o trecho. Rode o `capturar_frames.py` com cinco sementes e `--frames 100` cada, em pastas separadas, e junte os CSV. O mapa `SXSTSC` tem dois cruzamentos (o X e o T); com 100 quadros a `--passo 3` a semente 7 chega ao primeiro no quadro 55 — confira no CSV quantos quadros de cruzamento cada semente rendeu, porque a rota que o IDM escolhe dentro do cruzamento muda com a semente.

**Equilibre as classes antes de treinar.** Com o IDM dirigindo, `obstaculo` quase não aparece — ele mantém distância de quem está na frente. Para ter a classe, aumente `--trafego` (0,3 a 0,5) e `--acidentes`, ou reduza o `LIMIAR_OBSTACULO_M` no topo do script e diga no relatório que reduziu. A regra que não muda é a da Aula 9: os limiares vão para o topo do arquivo **antes** de você ver o resultado.

**Revise o rótulo sugerido, e conte as correções.** O `rotulo_sugerido` é geometria, não visão: ele não sabe se o carro da frente estava escondido atrás de uma curva, e chama de cruzamento os metros finais antes dele. Uma planilha com uma coluna `rotulo_final` ao lado e o número de linhas alteradas é a evidência de rotulagem que o item 4 pede.

**Ajuste o detector de faixa na sua câmera, não na minha.** A configuração ajustada do `medir_faixas.py` foi escolhida em 320×240 com renderização por software. Se você capturar a 640×480 ou com GPU, rode a configuração padrão primeiro, olhe a máscara de cor (o `faixas.py --quadro ... --etapas DIR` da Aula 13 grava as quatro etapas) e só então mexa nos números.

**Se quiser uma forma de verdade para o Hough Circle**, ponha-a na cena. A saída honesta é a do teste: um círculo desenhado sobre um quadro real do MetaDrive, em posição conhecida, mede se o detector acha o que existe. A saída desonesta é baixar o `param2` até aparecer alguma coisa.

## O que cada arquivo faz

| Arquivo | Papel | Precisa do MetaDrive? |
|---|---|---|
| `capturar_frames.py` | sobe o `MetaDriveEnv` sem janela com a câmera RGB como observação, dirige com o `IDMPolicy` e grava `quadroNNN.png` + `estado.csv` com o rótulo sugerido. `--frames`, `--saida`, `--semente`, `--passo`, `--largura`, `--altura`, `--mapa`, `--trafego`, `--acidentes`, `--sem-terreno` | **sim** (o venv) |
| `medir_faixas.py` | importa o `faixas.py` da Aula 13 pelo caminho e roda `detectar_faixas()` com a configuração padrão e com a ajustada; tabela por quadro e sobreposição. `--pasta`, `--sobreposicao`, `--quadro`, `--faixas` | não |
| `formas.py` | `HoughCircles` e `cornerHarris` com os parâmetros no topo; círculos acima do horizonte, cantos na pista, e a frase sobre a ausência de placa. `--pasta`, `--sobreposicao`, `--quadro`, `--param2` | não |
| `testar.py` | 7 grupos: o CSV, os PNG, as funções puras, as formas (com placa e quadrado desenhados), as faixas, a higiene dos `.py` e — se achar o venv — a captura de 3 quadros duas vezes. Termina em `todos os testes passaram.` e sai com 0 ou 1 | só o grupo 7 |
| `amostra/quadroNNN.png` | 12 dos 60 quadros da semente 7, um a cada 1,5 s simulado; o `quadro055` já é o cruzamento | — |
| `amostra/estado.csv` | as 60 linhas da captura inteira; o `testar.py` confere a regra do rótulo em todas | — |
| `amostra/figuras/faixas-sobreposicao.png` | o `quadro020` com as duas faixas da configuração ajustada, a 960×720 | — |
| `amostra/figuras/formas-sobreposicao.png` | o `quadro040` com os cantos Harris em vermelho, a linha do horizonte e nenhum círculo | — |

## Conferir antes de confiar

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
python3 testar.py
```

Sem o venv, os seis primeiros grupos rodam em meio segundo e o sétimo diz `[pulado]`. Com o venv em `$PB_DIR/.venv-metadrive`, ele é achado sozinho e o grupo 7 captura 3 quadros duas vezes — uns 40 s com renderização por software.

## Licença

MIT, como todo o diretório `exemplos/`.
