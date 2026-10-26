# Exemplo — `aula15-nav2`

**Aula 15 · Etapa 8.** O gate **G4.0** do TP4 pede que *"o Nav2 suba com o mapa do TP3 e localize (AMCL convergindo)"*, provado com um print do RViz2 em que a nuvem de partículas está concentrada. O problema é que **"está concentrada" se avalia por impressão** — e esta disciplina passou o semestre trocando impressão por número. Este exemplo torna a convergência do AMCL **mensurável**, e faz isso **sem ROS 2**: um filtro de partículas honesto, em NumPy, rodando sobre o mapa da Aula 11, que é ao mesmo tempo o mapa conhecido e a **verdade**.

A frase que o exemplo existe para derrubar é esta: *a nuvem concentrou, logo o robô está localizado.* Não é. A nuvem concentrar prova **confiança**, não **acerto** — e o exemplo mede as duas coisas lado a lado.

```
aula15-nav2/
├── localizacao.py      # o filtro: Particulas, Mcl (mover, pesar, reamostrar)
├── simular_loc.py      # roda o filtro contra a verdade, percurso fixo, CSV
├── avaliar_loc.py      # a régua: tabela dos 3 cenários + o painel das nuvens
├── testar.py           # 7 grupos com a resposta sabida de antemão
└── aula15_nav2/        # o pacote ROS 2 desta aula — launch do Nav2, params do
                        # AMCL, o mapa e a config do RViz2 (ver README-pacote.md)
```

O núcleo offline e a camada ROS 2 respondem à mesma pergunta por dois caminhos:

```
                        ┌────────────────────────────────────────┐
Mundo (Aula 11) ──────► │ localizacao.py                         │
  mapa conhecido        │   espalhar_uniforme / espalhar_ao_redor│
  + VERDADE             │   mover()      ← odometria com deriva  │ ──► avaliar_loc.py
                        │   pesar()      ← /scan da pose real    │     tabela + figura
odometria com deriva ─► │   reamostrar() ← quando N_ef < N/2     │
/scan da pose real ───► │   estimativa() → pose + DISPERSÃO      │
                        └────────────────────────────────────────┘

mapa do TP3 (.pgm) ───► AMCL do Nav2 ───► /particle_cloud ───► print do RViz2
```

O print do RViz2 mostra a nuvem. **Só a nuvem.** A coluna `erro pos` da tabela é o que ele não tem, e é a razão de este exemplo existir.

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y python3-numpy python3-opencv

cd /tmp && rm -rf pb-a15 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a15 && \
  # a cópia antiga sai antes: cp -r sobre pasta existente ANINHA (src/x/x),
  # e o colcon passa a compilar a versão velha sem dizer nada
  rm -rf "$PB_DIR/aula15-nav2" "$PB_WS/src/aula15_nav2" && \
  cp -r pb-a15/exemplos/aula15-nav2 "$PB_DIR/" && \
  cp -r pb-a15/exemplos/aula15-nav2/aula15_nav2 "$PB_WS/src/"
```

O núcleo offline precisa do **mapa da Aula 11** — ele é o mapa *e* é a verdade. Se você ainda não tem o `aula11-mundo` baixado ao lado, o script diz exatamente o que fazer e sai; não há `ImportError` de três linhas aqui.

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
rm -rf "$PB_DIR/aula11-mundo" && cp -r /tmp/pb-a15/exemplos/aula11-mundo "$PB_DIR/"
```

Nada de `pip`. Nada que precise de ROS 2 para rodar as três primeiras seções.

## Medir, sem ROS 2 e sem Nav2

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 simular_loc.py                       # os três cenários, resumo de cada um
python3 avaliar_loc.py                       # a tabela comparada
python3 avaliar_loc.py --imagem nuvem.png    # + a figura do relatório
```

O robô percorre **sempre o mesmo caminho**: 13 trechos de velocidade constante, ~26,9 m em 95,9 s, saindo de (2, 4) na sala 1, atravessando a porta, dando a volta pela sala 2 e voltando pela porta. É um percurso **fixo**, e não o `piloto.py` reativo da Aula 11, de propósito: o resultado precisa ser o mesmo na sua máquina e na minha, senão a tabela não pode ser citada em sala. Com um piloto reativo, mexer no filtro mudaria a trajetória, e ninguém saberia se o número mudou por causa do filtro ou por causa do caminho.

## O resultado, e o que ele conta

```
mapa         : .../aula11-mundo/aula11_mundo
percurso     : fixo, 13 trechos, ~26.9 m em 95.9 s -- igual em toda maquina
partida      : verdade em (2.0, 4.0); a pose ERRADA informada e (9.8, 4.0)
nuvem        : 1200 particulas, 30 feixes por particula, semente 42
convergencia : raio da nuvem < 0.30 m E desvio angular < 15.0 graus,
               mantidos por 10 atualizacoes seguidas do filtro
acerto       : erro de posicao final < 0.50 m contra a verdade
odometria    : deriva de 3.0% -- sozinha, erraria 0.72 m no fim do laco

cenario     t conv (s) erro pos (m) erro ang (g)  nuvem (m)  nuvem (g)  N ef min  N ef fim  convergiu para
-------     ---------- ------------ ------------  ---------  ---------  --------  --------  --------------
uniforme           3.0         0.02          0.4      0.066        1.7      11.8     614.9  lugar certo
aproximada         0.6         0.02          0.5      0.063        1.6      63.0     624.3  lugar certo
errada             0.6         5.92        179.7      0.078        2.2     114.5     449.8  lugar ERRADO
```

Tudo é **determinístico**: com a semente 42, rodando de novo sai idêntico. O `testar.py` confere isso bit a bit.

**A métrica foi declarada antes**, como na Aula 9, e ela aparece impressa na própria saída: convergiu = a nuvem fica com raio abaixo de 30 cm **e** desvio angular abaixo de 15°, e **assim permanece por 10 atualizações seguidas**. Um instante isolado de dispersão baixa não é convergência, é sorte — e o grupo 7 do `testar.py` prova que a régua recusa uma nuvem que pisca.

Quatro leituras, e a terceira é a que vale a aula.

**O erro não dá erro.** No cenário `errada`, a pose inicial informada ao filtro está em (9,8, 4,0), na outra sala — é o aluno clicando o *2D Pose Estimate* no lugar errado. O filtro não levanta exceção, não emite aviso, não acusa nada. Ele converge em **0,6 s**, mais rápido que o cenário `uniforme`, deixa a nuvem com **7,8 cm de raio** e publica uma pose com **5,92 m de erro e 180° de rumo invertido**. No RViz2, isso é um print perfeito de nuvem concentrada.

**A nuvem mais concentrada pode ser a do robô mais perdido.** É a tese da Aula 13 voltando de outra roupa: lá, o maior IoU médio da tabela era do pior detector; aqui, a nuvem mais confiante é a mais errada. Qualquer métrica que mede **o que o algoritmo acha de si mesmo** se deixa enganar da mesma maneira. A cura é sempre a mesma: medir contra a verdade.

**Olhe a coluna `N ef min`.** Ela é o diagnóstico mais interessante da tabela. No cenário `uniforme`, o N efetivo chega a **11,8** de 1200 — o filtro passa por uma crise: as hipóteses competem, quase todas morrem, a reamostragem renova a nuvem. No cenário `errada`, o mínimo é **114,5**: o filtro **nunca teve dúvida**. E é coerente — todas as partículas concordam entre si, porque todas estão igualmente erradas. *Concordância interna não é evidência.*

**A localização ganha da odometria por 30×.** Sozinha, a odometria com 3% de deriva termina o laço com **0,72 m** de erro. O filtro termina com **0,02 m**. É isso que o AMCL compra: ele não corrige a odometria, ele a **amarra ao mapa** — que é literalmente o que a transformada `map → odom` significa.

### Convergir no lugar errado sem ninguém clicar em nada

O mundo da Aula 11 tem uma propriedade que ninguém projetou e que é a melhor aula do exemplo: ele é **quase simétrico por rotação de 180° em torno de (6, 4)**. As duas salas têm quase a mesma largura, e o obstáculo da sala 1 em (2,7, 2,2) cai quase exatamente sobre o da sala 2 em (9,1, 5,5) quando você gira o mapa meia volta. A única coisa que distingue as duas metades é o cilindro de 35 cm em (3,6, 6,0).

Por isso a localização global é **cara ou sorte**:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 avaliar_loc.py uniforme --particulas 400 --segundos 20
```

```
uniforme           8.4         8.48        178.1      0.223       11.8      13.5     400.0  lugar ERRADO
```

Com 400 partículas e 20 s de percurso, a nuvem trava na **sala gêmea** e o robô fica 8,48 m fora, com 178° de erro de rumo. Com 1200 partículas e o laço inteiro, ela acha o lugar certo. Nenhum dos dois é bug: é o que a simetria do mapa faz com um filtro que não tem nenhuma informação a priori. **É exatamente por isso que o gate G4.0 pede o clique no 2D Pose Estimate** — e por que `set_initial_pose` existe no AMCL.

Se o seu ambiente do TP3 tem corredores iguais, salas espelhadas ou um hall sem móveis, espere o mesmo. A resposta não é mais partículas; é dar a pose inicial, ou mapear algo que quebre a simetria.

## Ver **onde** a nuvem concentrou

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 avaliar_loc.py --imagem nuvem.png
python3 avaliar_loc.py --imagem colapso.png --momentos 6 --segundos 20
```

Uma linha por cenário, três momentos por linha (início, meio, fim) sobre o mesmo mapa, **com legenda embutida** — a figura vai ao relatório do TP4 sozinha, ao lado do print do RViz2. Cada partícula é um ponto, e uma amostra delas leva um risco mostrando o **rumo**, porque a dispersão de θ é metade do problema e o ponto a esconde.

Na linha `errada`, o círculo escuro (a verdade) e a cruz vermelha (a estimativa) ficam em **salas diferentes** — e a nuvem em volta da cruz é do tamanho de uma moeda. **O número diz quanto; a figura diz onde.**

Com `--momentos 6` você vê o colapso acontecer: as 1200 hipóteses espalhadas pelo mapa inteiro viram uma mancha em dois ou três ciclos do filtro.

## Como isto se liga ao AMCL do Nav2

Cada peça do filtro tem um parâmetro correspondente no `amcl` do Nav2. Esta tabela é o motivo de o exemplo ser um filtro de verdade e não uma animação: mexer aqui e mexer lá tem o mesmo efeito.

| Peça aqui | Parâmetro do AMCL | O que acontece quando você mexe |
|---|---|---|
| `Particulas.espalhar_ao_redor` | `set_initial_pose`, `initial_pose.x/.y/.yaw` — e o botão **2D Pose Estimate** do RViz2 | é a diferença entre os cenários `aproximada` e `errada`. **O parâmetro mais perigoso da lista**: ninguém valida se o palpite está certo |
| `Particulas.espalhar_uniforme` | o que o AMCL faz quando `set_initial_pose: false` (e o serviço `/reinitialize_global_localization`) | localização global. Num mapa simétrico, é cara ou coroa — veja a seção acima |
| `--particulas` (nuvem de tamanho fixo) | `min_particles` / `max_particles` | mais partículas = mais hipóteses sobrevivendo à primeira rodada = mais chance de a certa estar entre elas. Custa CPU linearmente (grupo 3 do `testar.py` mede os dois lados) |
| `feixes_usados` / `--feixes` | `max_beams` (no ROS 1 chamava-se `laser_max_beams`) | menos feixes = nuvem mais gorda e erro médio maior; mais feixes = mais CPU por partícula. Com 5 feixes o erro médio **triplica** (grupo 4) |
| o portão de `Mcl.atualizar` | `update_min_d` / `update_min_a` | o filtro só roda depois de 20 cm ou 0,2 rad de movimento. Reamostrar com o robô parado destrói diversidade sem acrescentar informação: a nuvem encolhe por falta de dado, não por ganho de certeza |
| `Mcl.reamostrar` + limiar de N efetivo | `resample_interval` | com que frequência a nuvem é renovada. Reamostrar sempre empobrece; reamostrar nunca deixa quase todo o peso numa partícula só |
| `ALFA_PADRAO` (alpha1..alpha4) | `alpha1` … `alpha5`, com `robot_model_type: DifferentialMotionModel` | o ruído do modelo de movimento. **Alpha pequeno demais é a causa nº 1 de AMCL que "perde" o robô**: a nuvem não se abre o suficiente para a hipótese certa continuar viva |
| `sigma_z`, `z_hit`, `z_rand` | `sigma_hit`, `z_hit`, `z_rand`, `z_max`, `z_short`, `laser_model_type` | o modelo de observação. O `z_rand` é o que impede que **um** feixe absurdo (uma pessoa passando, algo que não está no mapa) zere o peso de uma partícula que está certa |
| `estimativa()` → dispersão | a covariância do `/amcl_pose` e o `/particle_cloud` que o RViz2 desenha | é o mesmo número. A diferença é que aqui ele vem acompanhado do erro contra a verdade |
| **não existe aqui** | `recovery_alpha_slow` / `recovery_alpha_fast` | é a recuperação do AMCL: quando o peso médio despenca, ele injeta partículas aleatórias. **Vem desligada por padrão (0.0)** — e é por isso que o cenário `errada` não se salva sozinho no Nav2 também |
| `EXPOENTE_PESO` | **não existe no AMCL** | veja abaixo; é a honestidade que falta ao AMCL |

### O parágrafo mais importante do `localizacao.py`

Os feixes do laser **não são independentes**: a parede que o feixe 7 vê é a mesma que o feixe 8 vê. Multiplicar 30 verossimilhanças como se fossem 30 medidas independentes conta a mesma evidência trinta vezes — e o efeito é brutal. Com expoente 1,0, o N efetivo desta nuvem cai de **1200 para 1 no primeiro ciclo**: uma partícula sobrevive, as outras 1199 viram cópias dela, e o filtro deixou de ser Monte Carlo. Virou um palpite com nuvem de enfeite.

Por isso o `localizacao.py` eleva a verossimilhança a `EXPOENTE_PESO = 0.15`, e declara o número no topo do arquivo. **O AMCL não tem esse expoente** — e é uma das razões de ele ser mais confiante do que deveria. O jeito dele de conseguir o mesmo efeito é indireto: menos feixes (`max_beams`) e `sigma_hit` maior. Se o seu AMCL está sempre certíssimo de si e ocasionalmente certíssimo e errado, é disto que se trata.

Para ver o efeito com os seus próprios olhos, edite o `EXPOENTE_PESO` para `1.0` e rode `python3 avaliar_loc.py` de novo: a coluna `N ef min` cai para perto de 1 e o cenário `uniforme` passa a depender da sorte da semente.

## O que cada arquivo faz

| Arquivo | Papel |
|---|---|
| `localizacao.py` | o filtro: `Particulas` (poses N×3 + pesos), `Mcl` (`mover`, `pesar`, `reamostrar`, `estimativa`), o lançamento de raios vetorizado `lancar_lote`, e **os limiares da régua declarados no topo**. Rodado direto, confere o lançamento de raios contra o `Mundo.medir` da Aula 11 |
| `simular_loc.py` | pilota o percurso fixo, alimenta o filtro com odometria **derivada** e `/scan` da pose verdadeira, grava uma linha por varredura. `--particulas`, `--feixes`, `--inicial`, `--deriva`, `--semente`, `--segundos`, `--ruido-laser`, `--saida` |
| `avaliar_loc.py` | a régua: roda os três cenários, imprime a tabela com os limiares declarados, e desenha o painel com `--imagem` / `--momentos` |
| `testar.py` | 7 grupos com a resposta sabida de antemão; termina em `todos os testes passaram.` e sai com código 0 ou 1 |
| `aula15_nav2/` | o pacote ROS 2 desta aula: `launch/nav2.launch.py`, `config/nav2.yaml` com os `params` do AMCL que a tabela acima referencia, o mapa, `rviz/nav2.rviz` e o nó `rota` — cliente da ação `navigate_to_pose` que cumpre uma rota de poses, que é o item 1 do TP4. Tem README próprio (`README-pacote.md`) |

### O CSV, para quando a tabela não basta

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 simular_loc.py --saida loc.csv        # gera loc-uniforme.csv, loc-aproximada.csv, loc-errada.csv
```

Uma linha por varredura do laser, com `t`, `atualizou`, `reamostrou`, a pose verdadeira, a estimada, `erro_pos`, `erro_ang`, as três dispersões, `raio_nuvem` e `n_efetivo`. É o arquivo para plotar o erro ao longo do tempo no relatório — e para ver, com os próprios olhos, que entre duas atualizações do filtro **nada muda**, porque o portão `update_min_d` segurou.

## Conferir a régua antes de confiar nela

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula15-nav2"
python3 testar.py
```

Sete grupos, cerca de 20 segundos, todos com a resposta sabida de antemão:

1. **o mapa e o lançamento de raios** — a versão vetorizada concorda com o `Mundo.medir` da Aula 11 dentro de um passo da marcha, inclusive sobre o que está fora de alcance;
2. **pose inicial errada** — a nuvem concentra igual (7,3 cm contra 6,1 cm da pose certa) e mesmo assim termina 6,2 m fora; a régua acusa `lugar ERRADO`. **É o grupo que sustenta a aula**: se ele falhar um dia, o argumento caiu;
3. **mais partículas** — com palpite inicial largo e 8 feixes, 900 partículas erram 0,029 m onde 60 erram 0,163 m, e custam 0,91 s contra 0,15 s. Os dois números aparecem;
4. **menos feixes** — com 5 feixes o erro médio é 0,042 m contra 0,016 m com 30, e a nuvem engorda de 5,6 cm para 12,3 cm. Em troca, custa 6× menos tempo;
5. **a reamostragem dispara** — o N efetivo cai a 31 de 600 em algum momento, a reamostragem roda, e um teste unitário prova que ela copia quem tem peso, descarta quem não tem e devolve os pesos a 1/N;
6. **determinismo** — duas corridas com a semente 7 dão a mesma série bit a bit; com a semente 8, muda;
7. **a régua em si** — nuvem sempre gorda nunca converge, nuvem que **pisca** não conta, e o instante devolvido é o primeiro da sequência estável.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `nao achei o mapa (o pacote aula11_mundo)` | baixe o `aula11-mundo` ao lado, ou copie-o para `$PB_WS/src`; a mensagem traz as três saídas |
| `No module named 'numpy'` | `sudo apt install python3-numpy python3-opencv` |
| `--imagem` falha com `No module named 'cv2'` | idem; o `cv2` só é usado para desenhar, nunca para medir |
| a tabela sai, mas os três cenários dão o mesmo número | você mudou a `POSE_ERRADA` para perto da verdadeira, ou `--semente`; o veredito avisa |
| `uniforme` converge para o lugar errado | é esperado em mapa simétrico — veja a seção da sala gêmea. Suba `--particulas` ou dê a pose inicial |
| o filtro leva uma eternidade | o custo é `particulas × feixes × ciclos`; baixe `--particulas` ou `--feixes` antes de baixar `--segundos` |
| no Nav2 real, o AMCL "perde" o robô numa curva | `alpha1`/`alpha2` baixos demais: a nuvem não abre o suficiente para a hipótese certa sobreviver ao giro |
| no Nav2 real, `/particle_cloud` não aparece no RViz2 | o tópico é `BEST_EFFORT`; ponha o display **PoseArray** em Best Effort (a mesma armadilha de QoS da Aula 13) |
| no Nav2 real, a nuvem nunca encolhe | o AMCL não está recebendo `/scan`, ou o `base_frame_id`/`odom_frame_id` não batem com a sua TF |
| no Nav2 real, a nuvem encolhe e a pose fica parada | `update_min_d` alto demais para o seu percurso: o filtro não está atualizando |

## Como adequar ao seu projeto

**Troque o mundo pelo seu mapa.** O filtro só pede três coisas de um mapa: `grade` (booleana), `res` e os tamanhos `nx`/`ny`. Qualquer `.pgm` do `map_saver_cli` vira isso em quatro linhas — e o `comparar_mapas.py` da Aula 12 já tem o leitor de PGM pronto para copiar. Feito isso, a régua inteira continua valendo sobre o **seu** mapa do TP3.

**Troque o percurso fixo pelo rosbag da sua coleta.** O `simular_loc.py` alimenta o filtro com `(odom, angulos, leituras)` por varredura. Se você gravou um bag com `/odom` e `/scan`, o laço é o mesmo: leia o bag em vez de integrar o percurso. Perde-se a verdade — e com ela a coluna `erro pos`, que é justamente o que só existe em simulação.

**Meça o seu AMCL com estes mesmos números.** No robô, `/amcl_pose` traz a covariância: a raiz de `covariance[0]` e `covariance[7]` são os desvios em x e y, e o `raio_nuvem` é a mesma `hypot` dos dois. Assine `/amcl_pose`, registre `hypot` e o tempo, e você tem a coluna `t conv` do seu robô — com o mesmo limiar declarado, em vez de "parece que concentrou".

**Declare o seu limiar antes de rodar.** Os valores aqui (30 cm de raio, 15° de desvio, 10 atualizações seguidas, 50 cm para "lugar certo") estão no topo do `localizacao.py` e são chutes razoáveis para um robô de 20 cm de raio num mundo de 12 × 8 m. **Os seus serão outros.** O que não muda é a regra da Aula 9: escolha o limiar **antes** de ver o resultado, porque limiar escolhido depois é o que faz o seu filtro parecer bom.

## Licença

MIT, como todo o diretório `exemplos/`.
