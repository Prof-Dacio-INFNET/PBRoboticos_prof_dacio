# Exemplo — `aula16-arvore-bag`

**Aula 16 · Etapa 8.** O item 2 do TP4 diz, no enunciado: *"Crie uma behavior tree que interrompa a navegação quando o sensor detectar obstáculo a menos de 0,5 m, aguarde 2 s e retome o goal. Grave toda a sessão de navegação com ros2 bag record e reproduza offline para validar o comportamento. Inclua gráfico da trajetória."* Três das coisas que ele pede — o portão de 0,5 m, a espera de 2 s e o gráfico — se **provam sobre um CSV**, e quem tem o CSV não precisa de robô nenhum para fazer a conta. É nisso que este exemplo aposta: a régua primeiro, o robô depois.

> ## Leia isto antes de qualquer coisa
>
> **A camada ROS 2 deste exemplo rodou pela primeira vez em 09/11/2026**, numa máquina com Humble e o Nav2 da Aula 15: `colcon build`, o `vigia` cancelando e retomando um goal, `ros2 bag record`/`play` e o `gravar_pose` tirando o CSV do bag. **As árvores XML continuam sem ter sido carregadas num `bt_navigator`.** E o ensaio achou um defeito na régua, já corrigido: ela contava **0** interrupções numa sessão que teve **1**. A seção **"O que foi e o que não foi verificado"**, no fim desta página, separa o que foi visto rodando do que não foi — inclusive o que mudou **depois** do ensaio.
>
> **A camada offline roda aqui, sem ROS 2.** O `testar.py` tem 10 grupos e 68 conferências, leva cerca de 1 s e passa. Os números citados aqui saíram dele e do `medir_sessao.py`.

```
aula16-arvore-bag/
├── simular_sessao.py      # gera a sessao sintetica: o CSV que um bag teria
├── plotar_trajetoria.py   # a figura do item 2: /odom e /amcl_pose no mesmo eixo
├── medir_sessao.py        # a regua: a tabela de numeros do relatorio
├── testar.py              # 10 grupos com a resposta sabida de antemao
├── arvores/
│   ├── padrao_comentada.xml   # a arvore oficial do Humble, comentada bloco a bloco
│   └── com_espera.xml         # a variante com a espera de 2 s, so com nos prontos
└── aula16_arvore/         # o pacote ROS 2 -- rodou em 09/11/2026 (ver aviso acima)
    ├── aula16_arvore/vigia.py        # o portao de 0,5 m: cancela, espera, reenvia
    ├── aula16_arvore/gravar_pose.py  # o bag virando o CSV que a regua le
    ├── aula16_arvore/varredura.py    # a menor distancia do /scan, feita direito
    └── launch/analise.launch.py      # sobe so o gravar_pose, ao lado do bag play
```

As duas camadas se encontram **no CSV**, e essa é a arquitetura inteira do exemplo:

```
   OFFLINE (roda aqui, hoje)                   ROS 2 (roda no seu robo, depois)

   simular_sessao.py                           ros2 bag record /odom /amcl_pose
     percurso fixo, semente 42                   /scan /cmd_vel /estado_vigia
     dois obstaculos a < 0,5 m                              |
     deriva de 3% na odometria                              v
            |                                   ros2 bag play --clock
            v                                              |
      +----------------+                                   v
      |   sessao.csv   | <---------------------  gravar_pose.py (assina os 5)
      +----------------+
        t, odom_*, amcl_*, dist_min_scan, cmd_v, cmd_w, estado
            |
            +--> medir_sessao.py     a tabela de numeros (G4.3 e G4.4)
            +--> plotar_trajetoria.py  a figura (o "grafico da trajetoria")
```

O CSV é o **contrato**, e ele tem exatamente o que um bag tem: nada de verdade, nada de pose perfeita. É por isso que a coluna da régua se chama *vão odom × amcl* e não *erro* — no bag do seu robô não existe contra o que medir erro. A verdade existe dentro do `simular_sessao.py`, e ela não sai de lá: só o `testar.py` a usa, para provar o que o CSV sozinho não permite provar.

## Baixar

Tudo o que a camada offline precisa vem do apt. Nada de `pip`: `pip install` solto cai em `--user` e reescreve o NumPy e o setuptools que o ROS 2 usa, e os sintomas aparecem três dias depois, no `colcon`. Se um dia você precisar mesmo de um ambiente isolado nesta disciplina, a ferramenta é o `uv` (`uv venv --system-site-packages`), nunca o `python3 -m venv`.

A cópia antiga sai antes de a nova entrar: `cp -r` sobre pasta existente **aninha** (`src/x/x`), e o `colcon` passa a compilar a versão velha sem dizer nada. E repare que tudo pende do `git clone` pelo `&&`: se o clone falhar — caminho do Windows num shell do WSL, rede fora —, o `rm -rf` **não roda**. Em shell interativo não há `set -e`, e uma linha que falha não interrompe as de baixo.

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

sudo apt install -y python3-numpy python3-matplotlib

mkdir -p "$PB_WS/src" && cd /tmp && rm -rf pb-a16 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a16 && \
  rm -rf "$PB_DIR/aula16-arvore-bag" "$PB_WS/src/aula16_arvore" && \
  cp -r pb-a16/exemplos/aula16-arvore-bag "$PB_DIR/" && \
  cp -r pb-a16/exemplos/aula16-arvore-bag/aula16_arvore "$PB_WS/src/" && \
  cp -r pb-a16/exemplos/aula16-arvore-bag/arvores "$PB_WS/src/aula16_arvore/"
```

A última linha não é decoração. As árvores moram em `arvores/`, um nível acima do pacote, porque são material de leitura tanto quanto código — mas o `bt_navigator` lê o XML **em tempo de execução**, e o caminho que você vai passar a ele tem de ser o do arquivo *instalado*. Por isso elas são copiadas para dentro do pacote antes do `colcon build`, e o `setup.py` **para com uma mensagem** se não as encontrar, em vez de instalar um pacote sem árvore nenhuma e deixar o erro aparecer meia hora depois, no `bt_navigator`, como um `Error loading XML file`.

## Medir, sem ROS 2, sem Nav2 e sem bag

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 simular_sessao.py                      # gera sessao.csv
python3 medir_sessao.py                        # a tabela de numeros
python3 plotar_trajetoria.py --saida trajetoria.png
python3 simular_sessao.py --como-vigia-real --saida real.csv
python3 medir_sessao.py real.csv               # a mesma sessao, como o bag grava
```

O percurso é **fixo** — 13 trechos, 25,5 m, 93,7 s — e a semente é 42. É de propósito, e é a mesma decisão do `simular_loc.py` da Aula 15: o número que vai para a tabela da aula tem de sair igual na sua máquina e na minha. Com um piloto reativo, mexer na régua mudaria a trajetória, e ninguém saberia se o número mudou por causa da régua ou por causa do caminho.

A odometria deriva **3%** contra a verdade — o `aplicar_deriva` da Aula 11, que é o erro de quem mediu o raio da roda com régua: pequeno, constante, e que não se cancela. O `/amcl_pose` treme uns 2,5 cm em volta da verdade e não acumula. Essas duas frases são o gráfico inteiro.

O obstáculo é uma **pessoa que entra na frente do robô e sai alguns segundos depois**. Essa escolha é a aula: a espera de 2 s do enunciado só faz sentido se o obstáculo for transitório. Volte a esse ponto na seção da armadilha, mais abaixo.

## O resultado, e o que ele conta

```
amostras      : 938 linhas, 10.0 Hz, 93.7 s de sessao
estados vistos: esperando, interrompido, navegando, retomando

LIMIARES (declarados no topo do medir_sessao.py, antes de medir)
  obstaculo   : 0.50 m          espera alvo : 2.00 s (+- 0.25 s)
  parado      : |v| < 0.005 m/s E |w| < 0.005 rad/s
  reincidente : dois disparos a menos de 0.60 m um do outro
  carencia    : 1.5 s depois de cada evento, portao desarmado

DISTANCIA PERCORRIDA -- tres contas, tres numeros
  integral de |cmd_v| dt      :  25.52 m   <- o que foi mandado andar
  soma dos passos do /odom    :  26.29 m   <- +3.0% (a deriva de escala)
  soma dos passos do /amcl    :  49.03 m   <- +92.1%: o tremor do AMCL virou caminho

ODOMETRIA x AMCL -- o vao entre as duas trajetorias
  vao final   : 0.75 m
  vao maximo  : 0.78 m, em t = 93.6 s

MENOR DISTANCIA DO /scan (setor frontal) -- dois numeros
  na sessao inteira       : 0.402 m, em t = 12.6 s (estado esperando, robo parado)
  com o portao armado     : 0.504 m, em t = 51.7 s
  "armado" = navegando, robo andando, fora da carencia. So o
  segundo numero o vigia comparou com o limiar; o primeiro pode
  cair parado no destino, na espera ou na carencia.

INTERRUPCOES -- 2 evento(s)
  #  t disp (s)  /scan (m)  parado (s)  espera (s)  evento (s)  2 s cumpridos  onde (x, y)
  1      12.30      0.402        2.00        2.00        3.10            sim  (6.32, 3.99)
  2      51.80      0.406        2.10        2.10        3.20            sim  (10.53, 3.03)
  tempo parado na sessao inteira: 4.10 s

VEREDITO
  2 evento(s) de obstaculo, como esperado.
  todas as esperas dentro de 2.00 s +- 0.25 s.
  a sessao sustenta o item 2: interrompeu abaixo de 0.50 m, esperou 2.0 s, retomou e terminou.
```

Cinco leituras, e a primeira é a que mais vale a aula.

**A distância percorrida tem três respostas, e uma delas é mentira.** Somar os deslocamentos entre amostras consecutivas do `/amcl_pose` dá **49,03 m** onde o robô andou 25,52 m. Não é defeito do AMCL: é defeito da conta. A 10 Hz, o passo verdadeiro é de 3,5 cm e o tremor do AMCL é da mesma ordem de grandeza — então a soma conta o ruído como caminho, e **infla 92%**. Quem escrever "o robô percorreu 49 m" no relatório escreveu um número que não existe. A distância honesta sai da odometria (suave, ainda que com escala errada) ou da integral de `|cmd_v| dt`. É a lição da Aula 9 numa roupa nova: *antes de citar um número, pergunte que conta o produziu.*

**O vão de 0,75 m é a transformada `map → odom`, e não um erro.** As duas curvas da figura saem do mesmo ponto e terminam a 75 cm uma da outra. Esse vão é exatamente o que o AMCL corrigiu ao longo da sessão — é o mesmo número que o `tf2_echo map odom` imprimiria no fim. Chamá-lo de "erro do AMCL" inverte o sinal da frase: o erro é da odometria, e o AMCL é quem o apaga. No `testar.py`, o grupo 5 confere que esse vão de 0,75 m bate com os 0,739 m de erro real da odometria contra a verdade — com 1 cm de folga, porque o AMCL também tem seu próprio tremor.

**As duas esperas não são iguais, e isso é o que torna a régua uma régua.** A primeira dá 2,00 s e a segunda, 2,10 s. O atraso é posto de propósito no simulador, porque no robô a espera **nunca** sai 2,000 s: o nó `Wait` do Nav2 recebe `wait_duration` **inteiro** e é tiqueteado pela árvore a 10 Hz, e o bag só tem as mensagens que passaram pela rede. Uma régua que só aprova o caso perfeito reprovaria um sistema correto — por isso a tolerância de ±0,25 s está declarada no topo do `medir_sessao.py`, antes de qualquer conta, como manda a Aula 9. O grupo 4 do `testar.py` prova os dois lados: 2,00 e 2,10 passam, e uma sessão que espera 1,2 s é reprovada com a frase `ESPERA FORA DO ALVO`.

**O menor `/scan` da sessão não é o que o portão viu.** A régua imprime dois números: o mínimo da sessão inteira e o mínimo com o portão **armado** — `navegando`, robô andando, fora da carência de 1,5 s depois de cada evento. O `vigia` só compara o `/scan` com o limiar no segundo caso: parado no destino depois do sucesso, dentro da espera ou na carência ele não olha. Por isso o mínimo da sessão pode ficar **abaixo** do limiar sem nenhuma contradição — no ensaio de 09/11 ele foi 0,480 m numa execução com limiar de 0,75 m que interrompeu uma vez só. O que seria defeito é o segundo número abaixo do limiar sem evento logo depois, e a régua avisa esse caso com uma linha `olhe:`.

**Parado é quando os DOIS comandos são zero.** Nos trechos de giro o `cmd_v` também é zero, e quem contar só ele conta cada curva como uma parada — nesta sessão, 15,7 s de giro virariam 15,7 s de "robô parado esperando obstáculo". A régua exige `|v| < 0,005` **e** `|w| < 0,005`, e por isso o total de parada da sessão é 4,10 s, que é exatamente 2,00 + 2,10.

### O que é um evento, e por que a régua errou no primeiro ensaio

O `vigia` passa por quatro estados — `navegando → interrompido → esperando → retomando → navegando` —, mas no robô **dois deles duram milissegundos**: o `interrompido` vai do pedido de cancelamento até o servidor aceitá-lo (2 ms no ensaio de 09/11) e o `retomando` vai do reenvio até o goal novo ser aceito. A 10 Hz, nenhuma linha do CSV cai neles: o CSV de um bag real tem `navegando` e `esperando`, e mais nada. A régua contava evento só quando o estado **virava** `interrompido`, o simulador fazia o `interrompido` durar 0,3 s, os testes passavam — e o primeiro bag real, com uma interrupção de verdade, saiu com **0 eventos**.

Agora um evento é um **bloco de linhas consecutivas fora de `navegando` que contenha `interrompido` ou `esperando`**, e começa na primeira linha do bloco. O `esperando` dura 2 s e não escapa da amostragem. Três consequências:

- **a espera medida tem erro de uma amostra.** Um intervalo de 2,0 s cobre 19, 20 ou 21 linhas a 10 Hz — ±0,1 s. A tolerância de ±0,25 s cobre isso com folga, e por isso não mudou.
- **o tempo parado é menor que a espera no robô real.** O temporizador de 2 s começa no cancelamento, e o robô freia **dentro** dele. Na sessão `--como-vigia-real` do simulador: espera de 2,00 s, parado de 1,70 s.
- **o começo da sessão não vira evento falso.** O `vigia` começa em `navegando`, ainda sem goal, e o `gravar_pose` grava `navegando` enquanto não ouviu o `vigia`. Se o CSV já **começa** dentro de um bloco `esperando` — o `ros2 bag record` ligado no meio de uma espera —, esse bloco é avisado e não é contado: a espera dele sairia curta e reprovaria uma sessão correta.

Desde o ensaio, o `vigia` também publica o `/estado_vigia` **na hora de cada transição**, além dos 10 Hz — o bag passa a guardar os quatro estados, cada um com o carimbo de quando aconteceu. O CSV continua quase sem `interrompido`, porque o `gravar_pose` guarda só o último estado ouvido; a régua não depende disso.

O `simular_sessao.py --como-vigia-real` gera a sessão exatamente assim, e o grupo 9 do `testar.py` mede com ela: os eventos contados, a espera na tolerância, a figura com as mesmas marcas, um ensaio em miniatura com 25 s de `navegando` parado no começo e o robô parado perto da parede no fim, e um CSV que começa no meio de uma espera.

### Medir com outro limiar

O enunciado pede 0,5 m, e a régua mede com 0,50 m. Mas no mundo da Aula 11 **nada chega a 0,5 m na rota** de um goal comum, e o ensaio de 09/11 foi feito com `-p limiar_m:=0.75` para o portão ter o que disparar. Medida com 0,50 m, essa sessão sai com `ATENCAO: ... o /scan nao ficou abaixo de 0.50 m` em cada evento — verdadeiro e inútil. Meça com o **mesmo** limiar com que o `vigia` rodou:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 medir_sessao.py sessao.csv --limiar 0.75
python3 plotar_trajetoria.py sessao.csv --limiar 0.75 --saida trajetoria.png
```

O limiar sai na linha `obstaculo` de LIMIARES, marcado `(--limiar)`, e o veredito ganha **uma** linha: `olhe: o TP4 pede 0.50 m; esta sessao foi medida com --limiar 0.75 m`. No relatório, diga o mesmo: o comportamento foi demonstrado com outro limiar, e por quê. A figura desenha a linha do limiar no valor passado e diz na legenda que o TP4 pede 0,5 m.

### A figura

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 plotar_trajetoria.py --saida trajetoria.png
python3 plotar_trajetoria.py --so-trajetoria --saida so-traj.png
```

**A ferramenta de desenho é o matplotlib**, com o backend `Agg` (sem tela) — escolhida porque está no apt do Ubuntu 22.04 (`python3-matplotlib`), não precisa de servidor X no WSL2 e sai com eixos e legenda prontos para o relatório. Não há desenho de reserva em OpenCV nem em SVG, de propósito: duas implementações de figura são duas coisas para manter e uma para esquecer de conferir. Se o `import` falhar, o script diz a linha do apt e sai.

O painel de cima é o que o enunciado pede: `/odom` e `/amcl_pose` **no mesmo eixo**, com os dois pontos de interrupção marcados com um X e numerados. As marcas são os eventos da régua, pela **mesma função** (`medir_sessao.eventos`) — por isso o `plotar_trajetoria.py` precisa do `medir_sessao.py` ao lado. No ensaio de 09/11 eram duas contagens em dois arquivos, e as duas diziam 0. Os tracinhos cinzentos costuram as duas curvas de 6 em 6 segundos, para o vão ser visto **crescendo** e não apenas existindo — e, como o percurso fecha um laço, a curva da odometria termina visivelmente fora do ponto de partida. É a figura clássica do "o laço não fecha para a odometria", de graça.

O painel de baixo é o que prova o **G4.3**: a menor distância do `/scan` furando a linha de 0,5 m, o `cmd_v` indo a zero e ficando zero por 2 s, e a faixa sombreada marcando o estado `esperando`. O `|cmd_w|` está lá por um motivo só: para ninguém confundir curva com parada. Sem esse painel, a figura mostra onde o robô andou e não mostra que ele **parou** — que é metade do item 2.

## A árvore de comportamento, e o que ela não sabe fazer

Em `arvores/` há dois XML, e a diferença entre eles cabe em dois atributos.

O `padrao_comentada.xml` é a árvore oficial do Humble — `navigate_to_pose_w_replanning_and_recovery.xml`, instalada em `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/` — copiada sem mudar nada e **comentada bloco a bloco**. Ela já está rodando no seu robô: é o valor padrão de `default_nav_to_pose_bt_xml`, e todo goal que você mandou na Aula 15 foi executado por ela. O item 2 do TP4 pede que você **crie** a árvore. A deste exemplo, o `com_espera.xml`, é um ponto de partida: você a adapta e a entrega, junto com o nó que mede a distância — e o relatório explica por que, no Humble, a decisão ficou dividida entre os dois. Para adaptar, primeiro é preciso saber ler a oficial.

Confira que a cópia não envelheceu em relação ao seu Humble — um `diff` não serve, porque os comentários estariam em todas as linhas; o que serve é comparar a **árvore**, que é o que o `bt_navigator` lê:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag/arvores"
OFICIAL=/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml
python3 -c "import xml.etree.ElementTree as E,sys; f=lambda p: E.tostring(E.parse(p).getroot()); print('IGUAIS' if f(sys.argv[1])==f(sys.argv[2]) else 'DIFERENTES')" "$OFICIAL" padrao_comentada.xml
```

O `testar.py` já roda essa mesma comparação contra uma cópia do XML oficial embutida nele, e por isso ela falha sem precisar de ROS 2 nenhum se alguém mexer na árvore sem querer.

O `com_espera.xml` muda **duas** coisas: o `<Wait wait_duration="5"/>` vira `<Wait wait_duration="2"/>`, e sobe de terceira para **primeira** entrada do `RoundRobin`. A segunda mudança é a que importa. O `RoundRobin` tenta uma recuperação por vez, em rodízio; na árvore oficial a ordem é limpar costmaps → girar → esperar → recuar, e a espera só chega na terceira falha. Com ela na frente, a primeira reação do Nav2 a uma navegação que falhou passa a ser *parar 2 s e tentar o objetivo de novo* — porque o `RecoveryNode` de cima retenta o ramo de navegação assim que o ramo de recuperação devolve `SUCCESS`. "Aguarde 2 s e retome o objetivo" é literalmente isso, com nós prontos do Humble, sem C++ e sem recompilar nada.

Para apontar a sua árvore há três caminhos, e os três recebem o **caminho instalado** (`install/.../share/aula16_arvore/arvores/com_espera.xml`), nunca o da pasta de fontes: o parâmetro `arvore` do nó `vigia` deste pacote, o parâmetro `arvore` do nó `rota` da Aula 15 — que preenche o campo `behavior_tree` do goal, uma pose por vez — ou o parâmetro `default_nav_to_pose_bt_xml` do `bt_navigator`, que vale para todos os goals, inclusive os do botão *2D Goal Pose* do RViz2.

### O que esta árvore **não** faz, e tem de estar no relatório

**Ela não sabe medir 0,5 m.** Nenhum nó de condição do `nav2_behavior_tree` do Humble lê distância a obstáculo. A lista inteira de condições é `GoalReached`, `IsStuck`, `TransformAvailable`, `GoalUpdated`, `GlobalUpdatedGoal`, `IsBatteryLow`, `IsBatteryCharging`, `DistanceTraveled`, `TimeExpired`, `PathExpiringTimer`, `InitialPoseReceived` e `IsPathValid` — e a única com "distância" no nome mede quanto o **robô** andou, não quanto falta para bater em alguma coisa. O `testar.py` confere essa ausência explicitamente, no grupo 8, para que a afirmação não seja de memória.

Então quando essa espera dispara? Quando a navegação **falha**: `FollowPath` devolvendo `FAILURE` (o DWB descartou todas as trajetórias, ou o progress checker declarou travamento) ou `ComputePathToPose` devolvendo `FAILURE`. Um obstáculo a 0,5 m normalmente produz uma dessas falhas — mas *normalmente* não é *quando a distância for menor que 0,5 m*, e a diferença é a frase que separa um relatório honesto de um relatório que passa:

> esta árvore reage à **consequência** (a navegação falhou); o item 2 pede reação à **causa** (o sensor viu menos de 0,5 m).

Fechar essa lacuna tem dois caminhos. O primeiro é um nó de condição em **C++** — assina o `/scan`, devolve `SUCCESS` abaixo do limiar, vira plugin, entra em `bt_navigator.plugin_lib_names`, e a árvore ganha um `ReactiveSequence` com ele no topo do ramo de navegação. É o caminho certo para produção, e custa um pacote `ament_cmake`, um `pluginlib` e um `colcon build` que falha de três jeitos antes de passar. O segundo é o `vigia.py` deste pacote, e é o que o exemplo escolheu.

## A camada ROS 2 — o caminho do bag até o CSV

**O que segue rodou em 09/11/2026**, com as ressalvas da seção de verificação: o `vigia` com `limiar_m:=0.75` cancelou o goal a 0,70 m, esperou 2 s e retomou; o bag foi gravado e tocado; o `gravar_pose` tirou dele o CSV. Os nomes de ação, campo, status e QoS foram lidos na fonte do Humble (as URLs estão na seção de verificação).

### `vigia.py` — o portão de 0,5 m pelo lado do cliente

O Nav2 não é uma biblioteca que você chama: é um servidor de ação que você contrata. Cancelar e reenviar são operações **públicas** dessa ação — então dá para implementar o item 2 inteiro sem o Nav2 saber que o `vigia` existe. Ele assina o `/scan`, e quando a menor distância do setor frontal cai abaixo de 0,5 m ele chama `cancel_goal_async()`, espera 2 s e manda o **mesmo** goal de novo.

A diferença honesta em relação ao caminho da árvore, para o relatório: a árvore reage dentro de um tick (o `bt_loop_duration` é 10 ms no Humble); o `vigia` reage no próximo `/scan`, que a 5 Hz é até 200 ms depois. Para um robô a 0,35 m/s isso são 7 cm. Para um robô a 1,5 m/s seriam 30 cm, e aí o caminho de cliente não serve mais.

Este nó é o contraponto do `rota.py` da Aula 15, e os dois juntos ensinam a mesma regra pelos dois lados. No `rota.py`, `rclpy.spin_until_future_complete` é **legítimo**, porque a espera acontece no `main`, fora de qualquer callback. Aqui ele seria **fatal**: todo o trabalho do `vigia` acontece dentro de callbacks, e chamar `spin_until_future_complete` dentro de um callback trava o nó para sempre — o executor só processa a próxima coisa quando o callback atual retorna, e o callback está esperando o executor processar a próxima coisa. O executor fica esperando por si mesmo, e o sintoma é o pior possível: nada acontece e nada reclama. O jeito certo é `futuro.add_done_callback(...)`, que retorna na hora, e uma máquina de estados que avança de callback em callback. O docstring do arquivo tem o parágrafo inteiro, mais duas armadilhas de rclpy que valem leitura: por que esta máquina de estados **não** precisa de trava (e passaria a precisar com um `MultiThreadedExecutor`), e como se faz um temporizador de uma vez só numa biblioteca em que `create_timer` é sempre periódico.

O `vigia` publica dois tópicos que existem **para o bag**: `/estado_vigia` (`navegando`, `interrompido`, `esperando`, `retomando` — os mesmos nomes do simulador), a 10 Hz **e** em cada transição, e `/dist_min`, a 10 Hz. Sem eles, o bag registra o que o robô fez e não registra **por quê**, e a figura do item 2 fica sem como marcar as interrupções. No CSV, `interrompido` e `retomando` quase nunca aparecem, porque duram milissegundos — veja "O que é um evento", acima.

O log de uma execução que interrompe uma vez, do ensaio de 09/11 com `-p limiar_m:=0.75`:

```
[WARN] [vigia]: obstaculo a 0.70 m (< 0.75 m): cancelando o objetivo
[INFO] [vigia]: cancelamento aceito (1 goal em cancelamento); esperando 2.0 s
[INFO] [vigia]: goal cancelado (pelo vigia)
[INFO] [vigia]: espera cumprida; retomando o MESMO objetivo
[INFO] [vigia]: enviando objetivo (9.00, 2.20, -1.57)
...
[INFO] [vigia]: objetivo cumprido. 1 interrupcao(oes) no caminho.
```

Repare nos carimbos do log original: o cancelamento foi aceito **1,8 ms** depois do pedido, e a espera cumprida saiu 2,001 s depois da aceitação. Esse 1,8 ms é o `interrompido` inteiro.

### Gravar e reproduzir

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && colcon build --packages-select aula16_arvore && source install/setup.bash
ros2 bag record -o sessao-tp4 /odom /amcl_pose /scan /cmd_vel /estado_vigia /dist_min /tf /tf_static
```

Grave **tópicos nomeados, não `-a`**. Com `-a` vêm os costmaps inteiros a 1 Hz e o bag de uma sessão de 90 s passa de um gigabyte — e um bag que não cabe no repositório do aluno não é um bag entregável. Os dois últimos da lista não são opcionais: sem `/tf` e `/tf_static` o RViz2 não desenha nada na reprodução, e é a reclamação número um de quem grava bag pela primeira vez.

Depois, em **dois terminais**, com o robô desligado:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source "$PB_WS/install/setup.bash"
ros2 launch aula16_arvore analise.launch.py saida:=sessao.csv
```

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source "$PB_WS/install/setup.bash"
ros2 bag info sessao-tp4
ros2 bag play sessao-tp4 --clock
```

Quando o bag acabar, `Ctrl-C` no primeiro terminal — o CSV já está completo, porque o `gravar_pose` dá *flush* a cada linha. E então a análise é a mesma de sempre, sobre o mesmo CSV:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 medir_sessao.py sessao.csv
python3 plotar_trajetoria.py sessao.csv --saida trajetoria.png
```

Se o `vigia` rodou com outro `limiar_m`, acrescente o mesmo `--limiar` às duas linhas — veja "Medir com outro limiar", acima.

**Este é o argumento do gate G4.4, e vale uma frase em sala:** do lado do assinante, o bag é *indistinguível* do robô. Se o seu código funcionou com o robô no ar, ele funciona com o bag tocando — e é por isso que o `gravar_pose.py` é o caminho garantido, e não o `rosbag2_py`. Ler o arquivo direto em Python também funciona, e custa serialização, tipo por tópico e um erro de versão de armazenamento que consome uma tarde.

O preço é um só, e é o `use_sim_time`. O `ros2 bag play --clock` publica o relógio do bag em `/clock`; um nó com `use_sim_time:=true` usa esse relógio, e sem ele usa o relógio de parede. Por isso o `analise.launch.py` vem com `use_sim_time:=true` **por padrão** — o contrário do resto do material, onde ele é `false` porque não há Gazebo. Se você tocar o bag **sem** `--clock`, passe `use_sim_time:=false`, senão o nó espera um `/clock` que nunca chega e **não grava nada**, sem uma linha de erro. E se tocar em `--rate 2.0` sem `--clock`, a sua sessão de 90 s vira um CSV de 45 s e a régua vai dizer que a espera durou 1 s.

### A armadilha do `min(msg.ranges)`

O `varredura.py` existe para que o `vigia` e o `gravar_pose` usem **a mesma conta**: se elas divergirem num detalhe, o gráfico do relatório mostra uma distância e o robô reage a outra, e ninguém consegue explicar a figura. E a conta não é `min(msg.ranges)`, por três motivos. Um feixe que não achou nada devolve `inf` — ou `nan`, a depender do driver —, e `min` com `nan` no meio devolve lixo, porque toda comparação com `nan` é falsa e o resultado passa a depender da ordem da lista. Muito driver real devolve **0.0** para feixe inválido (reflexo ruim, superfície preta), e aí `min` pega o zero, o portão de 0,5 m dispara e o robô para para sempre na frente de nada — é a causa número um de "o vigia trava sozinho". E um LIDAR de 360° vê a parede **atrás** do robô, que não é obstáculo para quem anda para a frente. A cura das três é filtrar por `range_min`/`range_max` do próprio cabeçalho da mensagem, que existem exatamente para isso, e recortar o leque por ângulo (`setor_graus`, ±60° por padrão).

O `setor_graus` do `vigia` e o do `gravar_pose` **têm de ser o mesmo**. Se não forem, a coluna `dist_min_scan` do CSV não explica as interrupções do mesmo CSV, e a figura fica com um X marcado num ponto em que o `/scan` desenhado está a 2 m.

## A armadilha do enunciado, que vale a nota

Esperar 2 s só resolve obstáculo que **sai sozinho**. É por isso que o obstáculo desta sessão é uma pessoa atravessando, e não uma caixa no chão: contra a caixa, a sequência vira esperar → tentar → falhar → esperar → tentar, e o robô fica preso ali até as seis tentativas do `RecoveryNode` se esgotarem e o goal ser abortado. O `vigia.py` tem uma carência de 1,5 s depois de retomar, e ela **não conserta isso** — ela só troca "para sempre" por "a cada 1,5 s".

Repare que a árvore oficial tem razão em **não** pôr a espera na frente: limpar o costmap e girar mudam alguma coisa no mundo do robô; esperar não muda nada. Se você trocar a ordem, troque com conhecimento de causa e diga no relatório por quê.

A régua acusa esse caso: o `medir_sessao.py` marca como **reincidência** dois disparos a menos de 60 cm um do outro, e o grupo 7 do `testar.py` prova que ela acusa. Se o seu bag do TP4 sair com reincidência, o problema não é a sua implementação — é o enunciado aplicado a um obstáculo que ele não cobre, e dizer isso no relatório vale mais do que esconder.

## Conferir a régua antes de confiar nela

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 testar.py
```

Dez grupos, 68 conferências, cerca de 1 s, todas com a resposta sabida de antemão. O grupo 1 confere que duas corridas com a semente 42 dão arquivos **idênticos byte a byte** e que a semente 7 dá outro. O grupo 2 confere o contrato das 11 colunas e que **nenhuma coluna de verdade vazou** para o arquivo. O grupo 3 acha os dois eventos, confere que nos dois o `/scan` furou os 0,5 m, que a ordem dos estados é a do enunciado duas vezes, e que o percurso nunca chega a menos de 1,34 m de uma parede — quem disparou foi a pessoa, não a parede. O grupo 4 é o da espera, pelos dois lados. O grupo 5 é o coração: usando a verdade que o simulador guarda e não grava, ele prova que o erro da odometria cresce de 0,081 m para 0,739 m enquanto o do AMCL nunca passa de 0,101 m — e que o vão de 0,75 m do CSV é uma medida válida dessa deriva. O grupo 6 gera a figura e confere que ela tem tinta (8,2% dos pixels não são brancos). O grupo 7 testa a régua contra casos construídos: reincidência, giro que não é parada, veredito. O grupo 8 é o da honestidade — ele confere **só o que dá para conferir sem ROS 2**. O grupo 9 mede sessões gravadas *como o `vigia` real grava* — só `navegando` e `esperando` —, que é o caso em que a régua errou no ensaio de 09/11, e também uma sessão com `--limiar 0.75`. O grupo 10 roda a máquina de estados do `vigia.py` com **dublês** do `rclpy`: confere a sequência publicada no `/estado_vigia` em cada transição, o reenvio do mesmo goal, a carência e o portão desarmado depois do sucesso. Dublê prova a lógica do nó, não que ele conversa com o Nav2.

## O que cada arquivo faz

| Arquivo | Papel | Roda aqui? |
|---|---|---|
| `simular_sessao.py` | gera a sessão sintética: percurso fixo de 13 trechos, deriva de 3%, dois obstáculos, quatro estados. Grava **só** as 11 colunas do contrato; a verdade fica dentro. `--semente`, `--deriva`, `--espera`, `--limiar`, `--sem-eventos`, `--como-vigia-real`, `--saida` | sim |
| `plotar_trajetoria.py` | a figura do item 2 em matplotlib: `/odom` e `/amcl_pose` no mesmo eixo com as costuras do vão e os X das interrupções, e o painel do `/scan` contra o limiar. Usa os eventos do `medir_sessao.py`, que tem de estar ao lado. `--saida`, `--so-trajetoria`, `--titulo`, `--limiar` | sim |
| `medir_sessao.py` | a régua, com os limiares declarados no topo: três distâncias, o vão odom × amcl, os eventos com tempo parado e espera, a reincidência e o veredito. `--limiar` para medir com o `limiar_m` do `vigia`. Lê qualquer CSV do contrato — do simulador ou do seu bag | sim |
| `testar.py` | 10 grupos, 68 conferências; termina em `todos os testes passaram.` e sai com código 0 ou 1 | sim |
| `arvores/padrao_comentada.xml` | a árvore oficial do Humble, intacta, comentada bloco a bloco — o `testar.py` prova que é a mesma | — |
| `arvores/com_espera.xml` | a variante com `Wait wait_duration="2"` como primeira recuperação do rodízio, e o parágrafo do que ela **não** faz | — |
| `aula16_arvore/vigia.py` | o portão de 0,5 m: assina `/scan`, `cancel_goal_async`, espera 2 s, reenvia o mesmo goal. Publica `/estado_vigia` (a 10 Hz e em cada transição) e `/dist_min` para o bag. `objetivo`, `limiar_m`, `espera_s`, `carencia_s`, `setor_graus`, `arvore` | com dublês; com ROS 2, em 09/11 |
| `aula16_arvore/gravar_pose.py` | assina os cinco tópicos com o bag tocando e escreve o CSV do contrato. Best Effort nos cinco, retenção de ordem zero a 10 Hz, *flush* por linha | com ROS 2, em 09/11 |
| `aula16_arvore/varredura.py` | a menor distância válida do `/scan` dentro do setor frontal — a função que o `vigia` e o `gravar_pose` compartilham para não divergirem | com ROS 2, em 09/11 |
| `aula16_arvore/launch/analise.launch.py` | sobe **só** o `gravar_pose`, com `use_sim_time:=true`, para rodar ao lado do `ros2 bag play` | com ROS 2, em 09/11 |

## O que foi e o que não foi verificado

Esta seção existe porque a diferença importa, e porque material de aula que finge ter sido testado custa caro na hora da entrega.

**Foi verificado sem ROS 2, e o `testar.py` prova:**

o determinismo bit a bit da sessão com a semente 42 (e que a semente 7 dá outra); o contrato das 11 colunas do CSV e a ausência de qualquer coluna de verdade nele; os dois eventos de obstáculo, com o `/scan` em 0,402 m e 0,406 m contra um limiar de 0,50 m; a ordem `navegando → interrompido → esperando → retomando` duas vezes; as esperas de 2,00 s e 2,10 s dentro de ±0,25 s, e a reprovação de uma sessão que espera 1,2 s; que o erro da odometria cresce para 0,739 m enquanto o do AMCL fica em 0,101 m no pior instante; que o vão odom × amcl do CSV bate com a deriva real; que somar passos do `/amcl_pose` infla a distância em 92%; que a figura é gerada e tem tinta; que a régua acusa reincidência e não confunde giro com parada; que todos os `.py` passam no `ast.parse`, nenhum passa de 99 colunas e nenhum tem byte não-ASCII; que o `package.xml` é XML bem formado e declara `ament_python`; que o `padrao_comentada.xml` é **estruturalmente idêntico** à árvore oficial do Humble embutida no teste; que o `com_espera.xml` difere dela exatamente onde deveria; que todo nome de nó das duas árvores existe na lista do Humble; que o `tools/conferir-launch.py` do repositório aprova o `analise.launch.py`; que a régua conta os eventos de uma sessão sem nenhuma linha `interrompido` ou `retomando`, não inventa evento no começo da sessão e mede com `--limiar`; e que a máquina de estados do `vigia.py`, com dublês do `rclpy`, publica `navegando → interrompido → esperando → retomando → navegando` na hora de cada transição.

Os três conferidores do repositório — `conferir-caminhos.py`, `conferir-comandos.py` e `conferir-launch.py` — passaram sobre este exemplo.

**Foi verificado numa máquina com ROS 2 Humble, em 09/11/2026** (a máquina do professor, com o Nav2 da Aula 15 no mundo da Aula 11):

- o `colcon build --packages-select aula16_arvore` passou;
- o `vigia`, com `-p limiar_m:=0.75`, **cancelou e retomou** um goal: obstáculo a 0,70 m, cancelamento aceito 1,8 ms depois, espera de 2,0 s, o **mesmo** goal reenviado e cumprido — "1 interrupcao(oes) no caminho". Isso responde a uma das dúvidas da versão anterior desta seção: o Nav2 **aceitou** o reenvio do mesmo goal 2 s depois do cancelamento;
- `ros2 bag record` com `/estado_vigia` (985 mensagens) e `/dist_min`, e `ros2 bag play --clock`;
- o `gravar_pose`, pelo `analise.launch.py`, gravou **1157 linhas a 10 Hz** de um bag de 123 s;
- e a régua, sobre esse CSV, contou **0** interrupções onde houve 1 — o defeito descrito em "O que é um evento", corrigido depois, com os testes do grupo 9.

**Observado, e sem causa confirmada:** a **primeira** execução do `vigia` naquele dia, cerca de 20 s depois de subir o Nav2, terminou em `status 6 (ABORTADO)` 3,4 s depois de enviar o goal. A segunda, um minuto depois, com o mesmo goal, completou. A causa provável é o Nav2 ainda estabilizando costmaps e TF — **não confirmada**. Até ter confirmação, espere o Nav2 assentar antes de rodar o `vigia`, e se o primeiro goal abortar, rode de novo antes de procurar defeito.

**Mudou DEPOIS do ensaio e não rodou com ROS 2:** o `vigia` publicar o `/estado_vigia` em cada transição e não imprimir o feedback com `faltam 0.0 m` antes de o Nav2 ter caminho; e a régua nova (eventos por bloco, `--limiar`, os dois mínimos do `/scan`). As mudanças do `vigia` são uma chamada de publicação depois de cada troca de estado e um `return` no feedback — sem tocar na lógica de cancelamento —, passam no `py_compile` e no grupo 10 do `testar.py`, com dublês. A régua nova foi conferida com sessões simuladas, não com o CSV do ensaio.

**Continua NÃO verificado, e ninguém viu rodar:**

as duas árvores **nunca foram carregadas num `bt_navigator`**. O ensaio usou a árvore padrão (o parâmetro `arvore` vazio). Elas são XML bem formado e os nomes de nó foram conferidos contra a fonte, mas o BehaviorTree.CPP tem validações próprias (portas obrigatórias, tipos, o `main_tree_to_execute`) que só acontecem em tempo de carga. Em particular, **não foi observado** que a espera de 2 s como primeira entrada do `RoundRobin` produza o comportamento descrito — o raciocínio sobre o `RecoveryNode` retentar o ramo de navegação é leitura de código, não experimento. Também **não sabemos** se o `behavior_tree` de um goal reenviado é respeitado do mesmo jeito que o do primeiro.

o portão com o limiar do enunciado, **0,5 m, disparando**. Numa execução anterior com o limiar padrão, a rota não passou a menos de 0,5 m de nada com o portão armado e o `vigia` terminou com "0 interrupcao(oes)" — por isso o ensaio usou 0,75 m. Uma interrupção a menos de 0,5 m pede um obstáculo posto na rota.

a taxa real do `/amcl_pose` no mundo da Aula 11, e portanto se 10 Hz no `gravar_pose` é taxa demais (linhas repetidas) ou de menos.

**As fontes do Humble que foram lidas** (branch `humble`, nunca `main` — os nomes mudaram entre versões):

- `https://github.com/ros-navigation/navigation2/blob/humble/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml` — a árvore padrão, copiada verbatim para o `padrao_comentada.xml`
- `https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/nav2_tree_nodes.xml` — a lista completa de nós registrados: ações, condições, controles e decoradores, com as portas de cada um. É daqui que sai a afirmação de que **não existe** condição de distância a obstáculo no Humble
- `https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/include/nav2_behavior_tree/plugins/action/wait_action.hpp` — `BT::InputPort<int>("wait_duration", 1, "Wait time")`: é daqui que sai a afirmação de que `wait_duration` é **inteiro**
- `https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/plugins/condition/goal_updated_condition.cpp` — o `GoalUpdated` devolvendo `FAILURE` no primeiro tique e `SUCCESS` quando a chave `goal` do blackboard muda
- `https://github.com/ros-navigation/navigation2/blob/humble/nav2_bringup/params/nav2_params.yaml` — `behavior_plugins: ["spin", "backup", "drive_on_heading", "assisted_teleop", "wait"]`, de onde sai a afirmação de que o `Wait` precisa do `behavior_server`; e o comentário que diz que `default_nav_to_pose_bt_xml` tem como padrão a árvore acima
- `https://github.com/ros2/rosbag2/blob/humble/ros2bag/ros2bag/verb/play.py` — as opções de `ros2 bag play`
- `https://github.com/ros2/rosbag2/blob/humble/README.md` — as opções de `ros2 bag record` (`-a`, `-o`, `-b`, `-d`, `--compression-mode`, `--use-sim-time`)
- e, do material desta disciplina: `exemplos/aula15-nav2/aula15_nav2/aula15_nav2/rota.py`, de onde vêm o `behavior_tree` do goal, o `std_msgs/Empty` do resultado e o parágrafo do `spin_until_future_complete`

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `No module named 'matplotlib'` | `sudo apt install -y python3-matplotlib`; pacote do apt, nunca `pip` |
| `nao achei sessao.csv` | rode `python3 simular_sessao.py` antes — a mensagem traz o comando |
| a tabela sai com 0 eventos | você gerou com `--sem-eventos`, ou o seu bag não tem `/estado_vigia` e a coluna `estado` ficou toda em `navegando`. Se `estados vistos` mostra `esperando`, confira se a sua régua é a de depois de 09/11/2026 — a antiga só contava `interrompido` |
| `ATENCAO: ... o /scan nao ficou abaixo de 0.50 m` num bag seu | o `vigia` rodou com outro `limiar_m`: meça com o mesmo, `--limiar 0.75` |
| o menor `/scan` da sessão está abaixo do limiar e o `vigia` não interrompeu ali | normal se foi com o portão desarmado — parado no destino, na espera ou na carência. Olhe a linha `com o portao armado` da régua |
| a régua acusa `ESPERA FORA DO ALVO` com um CSV do seu robô | quase sempre é o bag tocado sem `--clock` ou com `--rate` diferente de 1: o relógio do CSV não é o relógio do bag |
| a régua acusa `REINCIDENCIA` | o obstáculo não saiu do lugar — veja a seção da armadilha; esperar não resolve obstáculo parado |
| a distância percorrida saiu absurda | você citou a soma dos passos do `/amcl_pose`; cite a odometria ou a integral de `cmd_v` |
| `python3 testar.py` falha no grupo 8, na árvore padrão | o `padrao_comentada.xml` foi editado sem querer — o teste compara com a oficial do Humble |
| a árvore não carrega, e a mensagem não ajuda | comentário XML com **dois traços seguidos** é proibido pela especificação, e o tinyxml2 recusa o arquivo inteiro. Se você colou um comando ROS 2 dentro de um comentário da sua árvore, é isso |
| `Error loading XML file` com um caminho que existe | você apontou para a pasta de **fontes**; o `bt_navigator` lê o XML instalado, em `install/.../share/` |
| o `colcon build` passa e a árvore não é instalada | o `arvores/` não foi copiado para dentro do pacote — o `setup.py` agora para com mensagem, mas uma árvore de cópia antiga pode mascarar isso |
| o primeiro goal do `vigia` termina em `status 6` segundos depois do envio, logo depois de subir o Nav2 | observado em 09/11, sem causa confirmada (provável: costmaps e TF ainda assentando). Espere um minuto e rode de novo |
| `ros2 run aula16_arvore vigia` diz que o servidor não apareceu | o `bt_navigator` não está **ativo**: `ros2 lifecycle get /bt_navigator`. Sem pose inicial não há `map → odom`, e ele fica esperando a TF |
| o `vigia` cancela e nunca retoma | o `fim_da_espera` não está rodando: confira se o `use_sim_time` do `vigia` bate com quem publica `/clock`. Temporizador em tempo simulado sem `/clock` nunca dispara |
| o `vigia` cancela em loop, parado no mesmo lugar | é a reincidência, do lado do robô: obstáculo que não anda. A carência de 1,5 s só espaça o loop |
| o `vigia` dispara o tempo todo em corredor estreito | `setor_graus` largo demais, ou o seu percurso passa a menos de 0,5 m da parede. O portão não distingue parede de pessoa |
| o `gravar_pose` não grava nenhuma linha | falta `/odom` ou falta o primeiro `/amcl_pose` (`exigir_amcl:=false` desliga a segunda exigência); ou `use_sim_time:=true` sem `--clock` |
| o CSV começa com várias linhas em (0, 0) | `exigir_amcl:=false` com o AMCL ainda não convergido |
| a coluna `dist_min_scan` não explica os X da figura | o `setor_graus` do `gravar_pose` não é o mesmo do `vigia` que gravou o bag |
| o bag passou de 1 GB | você gravou com `-a`; grave a lista de tópicos |
| o RViz2 não mostra nada na reprodução | faltou gravar `/tf` e `/tf_static` |

## Como adequar ao seu projeto

**Troque o CSV sintético pelo seu.** As ferramentas offline leem o contrato das 11 colunas e nada mais — nenhuma delas importa o simulador. Gere o seu com o `gravar_pose.py` em cima do seu bag, ou escreva o CSV com o que você já tiver, e a régua e a figura continuam valendo. A régua pode ser copiada sozinha para o seu repositório; o `plotar_trajetoria.py` vai junto com ela, porque marca os eventos pela função da régua.

**Declare os seus limiares antes de rodar.** Os deste exemplo estão no topo do `medir_sessao.py`: 0,50 m e 2,0 s vêm do enunciado e não são escolha sua (o `--limiar` existe para medir com o `limiar_m` com que o seu `vigia` rodou, e o veredito avisa quando ele não é 0,50 m); a tolerância de ±0,25 s, o `LIMIAR_PARADO` de 0,005 e o raio de reincidência de 0,60 m são. Os seus serão outros — um robô com `velocity_smoother` agressivo precisa de um `LIMIAR_PARADO` maior; uma árvore com `bt_loop_duration` folgado precisa de uma tolerância maior. O que não muda é a regra da Aula 9: escolha o limiar **antes** de ver o resultado.

**Escolha um dos dois caminhos do item 2, e diga qual.** O `vigia.py` resolve o portão de 0,5 m sem C++; o `com_espera.xml` resolve a espera de 2 s sem Python. Os dois juntos cobrem o item inteiro — e, se você usar os dois, diga no relatório que as duas esperas podem se somar quando a navegação falhar logo depois de uma interrupção.

**Grave o bag uma vez e trabalhe nele a semana toda.** É o ponto do G4.4 e a melhor coisa que esta aula tem a oferecer para a sua produtividade: com o bag na mão, você depura a análise no ônibus, sem robô, sem Gazebo e sem WSL2 esquentando o laptop. E, quando a análise estiver pronta, ela roda igual no robô.

## Licença

MIT, como todo o diretório `exemplos/`.
