# Aula 11 — O mundo, a deriva e o mapa que corrige

**Terça, 29/09/2026 · sala SJ205 · Etapa 6 (28/09–10/10)**

[:material-file-pdf-box: Slides da Aula 11 (PDF)](apresentacao-aula11.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula11-mundo`](../../exemplos/aula11-mundo/index.md){ .md-button }
[:material-code-tags: Exemplo `aula10-bringup`](../../exemplos/aula10-bringup/index.md){ .md-button }

## Cenas dos últimos episódios

**Na Aula 10** vocês fecharam o TP2: a clínica de URDF validou o modelo do robô e a árvore de transformadas, e a aterrissagem cobriu branch, tag e relatório. O bloco de launch estava previsto como o que cederia se o tempo apertasse — e cedeu. Ele abre hoje.

Quatro coisas de antes voltam agora, e vale ter as quatro na cabeça antes de começar:

| De onde vem | O que era | Onde entra hoje |
|---|---|---|
| **Aula 2** — launch | um arquivo sobe vários nós com um comando | hoje ele passa a subir o **projeto inteiro**, não um exemplo |
| **Aula 6** — interfaces | o contrato fica, o miolo troca | é o que permite trocar o simulador sem mexer no resto |
| **Aula 8** — ações | objetivo longo, com feedback e cancelamento | o objetivo do Nav2 é uma ação; voltamos a isso no fim |
| **Aula 10** — URDF e TF | `base_footprint → ... → camera_link`, validada | hoje a árvore ganha **duas arestas acima**: `odom` e `map` |

E uma ideia da Aula 9 que reaparece em outro assunto: **ruído se combate com repetição, porque ele se cancela** — foi por isso que a métrica usou mediana em vez de uma medida só. Hoje aparece o erro que **não** se cancela, e a diferença entre os dois é o que a aula toda gira em torno.

## A ideia da aula em uma frase

**A odometria não erra por ruído; erra por viés.** Ruído se cancela: medir mais vezes ajuda, a média converge. Viés não se cancela — ele entra na conta sempre com o mesmo sinal, e **cresce com a distância percorrida**.

Por isso nenhum filtro sobre `/odom` conserta um robô perdido, e por isso existe o SLAM: para medir o erro acumulado contra uma referência que não se mexe — as paredes — e publicar a correção. Essa correção tem nome, e é uma aresta da sua árvore de TF: `map → odom`.

## Por que a aula está nesta ordem

Ordenada por **custo de perda**, como a anterior. O que vence antes vem primeiro; o que tem folga vem por último, e fica declarado de antemão.

| Bloco | O que você sai sabendo fazer | Prazo da entrega | Se faltar tempo |
|---|---|---|---|
| 1. Launch do sistema inteiro | subir o projeto todo com um comando, e provar que subiu | **amanhã** | não pode cair |
| 2. O mundo é um produtor de dados | produzir `/scan` e `/odom` sem depender do simulador | 06/10 | não pode cair |
| 3. `map → odom` e a deriva | medir o erro da odometria e explicar de onde ele vem | 10/10 | não pode cair |
| 4. O que o Nav2 acrescenta | dizer o que falta a um robô que só reage | 30/10 | **volta na Aula 12** |

As datas da coluna do meio são as do TP3, e estão todas em [gates e entregas](../../recursos/gates-tps.md) — aqui elas aparecem só para explicar a ordem da aula.

## Objetivos

Ao final da aula você deve conseguir subir o seu projeto inteiro com um `ros2 launch` e provar que ele subiu; explicar quem publica cada aresta da árvore `map → odom → base_link → sensores`; demonstrar a deriva da odometria com um número, e justificar por que ela não se resolve com mais medições; e dizer o que o Nav2 acrescenta a um robô que apenas reage.

## Baixar o material desta aula

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

# 1) baixar o material (pode repetir sempre — a linha do rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) o mundo mínimo desta aula
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula11-mundo/aula11_mundo \
      "$PB_WS/src/"

# 3) o bringup da Aula 10, se você ainda não tem
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula10-bringup/aula10_bringup \
      "$PB_WS/src/"

cd "$PB_WS"
colcon build --packages-select aula11_mundo aula10_bringup
source install/setup.bash
```

Sem compilar e sem ROS 2, o mundo roda e se testa sozinho:

```bash
cd /tmp/PBRoboticos_prof_dacio/exemplos/aula11-mundo
python3 testar.py
python3 simular.py --segundos 90
```

## Parte 1 — Um comando sobe o sistema inteiro

Este é o bloco que faltou na semana passada, e o **G3.0 vence amanhã**.

```bash
ros2 launch aula10_bringup bringup.launch.py
```

O [`aula10-bringup`](../../exemplos/aula10-bringup/index.md) demonstra os três mecanismos que o seu `bringup.launch.py` vai precisar: **compor** com `IncludeLaunchDescription`, **parametrizar** com um YAML que vem de fora, e **condicionar** com `IfCondition`.

### Um launch que sobe sem erro não é um launch que funciona

Subir é o que o launch faz. Funcionar é outra afirmação, e ela precisa de prova:

```bash
ros2 launch aula10_bringup bringup.launch.py --show-args   # o que dá para configurar
ros2 node list                                             # quem realmente subiu
ros2 param dump /percepcao/detector                        # com que valores
```

A terceira é a que quase ninguém faz, e é a que pega o erro abaixo.

### O YAML que ninguém lê

```bash
ros2 launch aula10_bringup bringup.launch.py \
  params:=$(ros2 pkg prefix aula10_bringup)/share/aula10_bringup/config/sistema-armadilha.yaml
ros2 param get /percepcao/detector taxa_hz     # 2.0 — o padrão do código, não o 9.0 do arquivo
```

O arquivo pedia `taxa_hz: 9.0`. O nó subiu com `2.0`. **Nenhum erro foi impresso em lugar nenhum.**

A causa é a chave do YAML: `detector:` significa o nó `/detector`, na raiz, mas o launch empurrou o nó para `/percepcao/detector`. Os nomes não casam, e a regra do ROS 2 é ignorar o que não casa — sem avisar. As curas são `/percepcao/detector:` ou o curinga `/**:`; **prefira o curinga**, que sobrevive à mudança de namespace.

O `conferir-params.py` pega isso sem ROS 2 instalado:

```bash
ros2 node list | python3 conferir-params.py config/sistema.yaml -
```

### Nada espera nada

Repare na subida: o `supervisor` quase sempre nasce antes do `detector`, avisa que não recebeu dado, e se recupera sozinho. Isso é **correto**.

Em ROS 2 o grafo é descoberto, não montado em ordem. Um nó que só funciona se subir depois de outro vai quebrar no dia em que a máquina estiver mais lenta, e esse dia costuma ser o da apresentação. A regra é o nó **tolerar a ausência do outro**.

## Parte 2 — O mundo é um produtor de dados, não uma janela

O TP3 pede um cenário de simulação. A pergunta que importa é: **do que o seu sistema realmente depende?**

Não do Gazebo. Ele depende de um tópico `/scan`, de um tópico `/odom`, e de uma árvore de TF que ligue os dois ao robô. Qualquer coisa que produza esses três serve — e é por isso que este exemplo existe.

```bash
ros2 launch aula11_mundo mundo.launch.py
ros2 topic hz /scan
ros2 topic echo /odom --once
```

O [`aula11-mundo`](../../exemplos/aula11-mundo/index.md) tem 12 × 8 metros, duas salas ligadas por uma porta e três obstáculos — o "cenário não trivial" que o TP3 pede. O laser é ray-casting sobre uma grade de ocupação, em numpy. **Sem física, sem render e sem janela.**

!!! tip "Isso não é desistir do Gazebo — é chegar nele com o esqueleto pronto"
    Trocar o nó `mundo` por um Gazebo publicando nos mesmos tópicos deixa **todo o resto valendo**: o launch, os frames, o SLAM, o Nav2.

    É o mesmo movimento das Aulas 6, 9 e 10 — o contrato fica, o miolo troca. O simulador é um detalhe de implementação atrás de uma interface, e quem monta o sistema na ordem certa pode trocar de simulador numa tarde.

    Quando quiser fazer a troca, o caminho está no tutorial [Gazebo para o TP3](../../tutoriais/gazebo-para-o-tp3.md) — que começa pela armadilha da versão (**Humble pareia com Fortress, não com Harmonic**) e termina com um critério de desistência de trinta minutos.

### Quem publica cada aresta

Saber isto é metade do G3.2:

```
map ──────────► odom ──────────► base_footprint ──► (URDF) ──► camera_link
 │               │                    │
 │               │                    └──► laser_frame
 │               │
 │               └── o nó `mundo`, integrando a odometria
 └── um static_transform_publisher — e ele é um PLACEHOLDER
```

`base_footprint → camera_link` já é conhecido: é o `robot_state_publisher` lendo o seu URDF, que foi o G2.5. O que é novo hoje são as duas arestas de cima — e a de cima de tudo está, neste momento, **mentindo**.

## Parte 3 — `map → odom`: a aresta que corrige

Suba o mundo e olhe o número crescer:

```bash
ros2 launch aula11_mundo mundo.launch.py
ros2 topic echo /deriva      # noutro terminal
```

`/deriva` é a distância entre onde o robô **está** e onde a odometria **acha** que ele está. Ela cresce. Agora desligue o viés e compare:

```bash
ros2 launch aula11_mundo mundo.launch.py deriva:=0.0
```

Offline, a mesma coisa sai em figura — linha cinza é a verdade, vermelha é a odometria:

```bash
python3 simular.py --deriva 3 --saida com-deriva.png
python3 simular.py --deriva 0 --saida sem-deriva.png
```

### Viés não é ruído, e essa é a diferença que decide tudo

O modelo aplica um erro de **escala** de 3% — o erro de quem mediu o raio da roda com régua. Não é aleatório: tem sinal constante.

Ruído você combate com repetição, porque ele se cancela; foi por isso que a Aula 9 usou mediana em vez de uma medida só. Viés não se cancela nunca. Ele entra na integral toda vez com o mesmo sinal, e o erro **cresce com a distância percorrida**. Rodar mais tempo piora.

Daí a conclusão que a aula quer: **nenhum filtro sobre `/odom` resolve.** O conserto não está em medir melhor a roda; está em medir contra outra coisa — algo que não se mexe. As paredes.

O SLAM faz exatamente isso: compara o `/scan` de agora com o mapa que vem construindo, calcula quanto a odometria já errou, e publica essa correção como `map → odom`. Enquanto essa aresta for identidade, como hoje, o robô acredita na própria odometria — e no RViz2 você vê o laser deslizar para fora das paredes.

```bash
ros2 launch aula11_mundo mundo.launch.py rviz:=true
```

!!! tip "RViz2 aberto e nada desenhado não é defeito do sistema"
    É ausência de displays. O `rviz2` sem `-d` abre com o Grid e mais nada — quadro fixo `map`, status `Ok`, tela vazia. O launch já passa a configuração pronta; se você abrir o RViz2 na mão, passe também:

    ```bash
    rviz2 -d $(ros2 pkg prefix aula11_mundo)/share/aula11_mundo/rviz/mundo.rviz
    ```

    O que você vai ver: as paredes paradas (o tópico `/mundo_real`, que é a verdade e o robô não tem), e o laser — desenhado pela odometria — escorregando para fora delas conforme a deriva cresce.

!!! warning "É por isso que o G3.2 é o gate de verdade do TP3"
    Noventa por cento dos problemas de SLAM e de Nav2 são problemas de TF disfarçados. Se o `view_frames` mostrar árvore quebrada ou dois `odom`, **pare tudo** e conserte antes de tocar no G3.3 — insistir no SLAM com TF errada é queimar uma semana.

## Parte 4 — O que o Nav2 acrescenta

!!! warning "Não trabalhada em 29/09 — recuperada na Aula 12"
    Este era o bloco de folga declarado na abertura, e foi ele que cedeu quando o tempo apertou — como combinado. Ele fecha a [Aula 12, de 06/10](../etapa06-aula12/index.md), e cai melhor ali: com o mapa construído em aula, duas das quatro linhas da tabela abaixo deixam de ser abstratas.

O `piloto.py` é o navegador mais burro que funciona: anda reto e gira quando fecha na frente. Trinta linhas, e ele explora o mundo inteiro.

Repare no que ele **não** tem — e é essa lista, e não outra coisa, que o Nav2 é:

| O piloto não sabe | O Nav2 acrescenta |
|---|---|
| onde está | localização (AMCL) contra o mapa |
| para onde vai | um objetivo, enviado como **action** |
| o que há além do que o laser vê agora | custos global e local, construídos do mapa |
| o que fazer quando trava | comportamentos de recuperação |

A segunda linha é a que fecha o semestre até aqui: **o objetivo do Nav2 é uma action** — com feedback periódico e cancelamento, exatamente as da Aula 8. O Nav2 não é assunto novo; é a montagem de peças que já estão no lugar.

## Tarefa da semana

### O que fazer

Fazer o **seu** projeto subir inteiro com um comando, produzindo dado de sensor e uma árvore de transformadas completa — de `map` até os seus sensores.

Ao terminar, três coisas têm de ser verdade ao mesmo tempo, com um único `ros2 launch` rodando: os seus nós todos no ar, `/scan` e `/odom` publicando, e `view_frames` desenhando **uma árvore só**, sem frames órfãos.

### O que usar

| Para | Use |
|---|---|
| a estrutura do launch | [`aula10-bringup`](../../exemplos/aula10-bringup/index.md) — compor, parametrizar, condicionar |
| o produtor de dados | [`aula11-mundo`](../../exemplos/aula11-mundo/index.md) — `/scan`, `/odom` e as arestas de TF |
| conferir o YAML | `conferir-params.py`, do `aula10-bringup` |
| conferir o mundo | `testar.py`, do `aula11-mundo` |
| se for de Gazebo | [Gazebo para o TP3](../../tutoriais/gazebo-para-o-tp3.md) — leia a seção 1 antes de instalar |

### Como adequar ao seu projeto

O exemplo é genérico; o seu projeto não é. Três traduções, e elas são o trabalho de verdade:

**O nome.** O `bringup.launch.py` mora no **seu** pacote e sobe **os seus** nós — o detector do seu domínio, o servidor de ação do TP2, a sua parametrização. O exemplo mostra a forma, não o conteúdo.

**O cenário.** O mundo mínimo tem duas salas e três obstáculos. O seu deve parecer com o ambiente onde o seu robô trabalharia: um armazém tem corredores longos; uma estufa tem fileiras; uma garagem tem colunas. Edite `mapa.py` — as paredes são retângulos e círculos, e mudar o cenário é mudar as linhas de `_construir`.

**Os quadros.** Os seus sensores precisam de frames com os nomes que os seus nós usam. Se o seu projeto tem câmera, o `camera_link` já veio do URDF; se ganhou laser, ele precisa de uma transformada estática até `base_footprint`, como a do exemplo.

### Como saber que terminou

Rode isto, com o seu launch no ar, e guarde a saída em `docs/evidencias/tp3/`:

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco de download, no começo da página ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_WS" && source install/setup.bash

ros2 launch <seu_pacote> bringup.launch.py &     # aba 1, deixe rodando
sleep 5

ros2 node list                    # todos os seus nós aparecem?
ros2 topic hz /scan               # o sensor publica, e a que taxa?
ros2 run tf2_tools view_frames    # gera frames.pdf: UMA árvore, sem órfãos
```

Se `view_frames` gerar um PDF vazio, o launch não está rodando — TF é fluxo, não arquivo. Se aparecerem duas árvores, falta uma aresta ligando as partes.

## Desafio — qual é o orçamento de deriva do seu projeto?

Opcional, para quem terminou a tarefa. Ele não completa nada: explora.

A Aula 9 estabeleceu que **uma métrica é uma decisão, e vem antes**. Aqui a decisão é outra: **quanto erro de posição o seu projeto tolera antes de fazer besteira?**

Um robô que desvia de obstáculos tolera bem mais que um que encosta numa prateleira; um que conta frutos numa fileira tolera bem menos, porque a 30 cm de erro ele conta a fileira errada. Decida o seu número — e **decida antes de medir**.

Depois meça quanto o seu robô pode andar até estourar esse orçamento:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula11-mundo" 2>/dev/null || cd /tmp/PBRoboticos_prof_dacio/exemplos/aula11-mundo

for d in 0.5 1 2 3 5; do
  echo "--- deriva $d% ---"
  python3 simular.py --deriva "$d" --segundos 120 --quieto --saida "deriva-$d.png" | grep deriva
done
```

Entregue, em `docs/evidencias/tp3/orcamento-deriva.md`: o número que você escolheu, **a justificativa a partir do seu domínio**, a distância que o robô percorre até estourá-lo, e o que você faria se precisasse do dobro dessa distância.

A última pergunta é a interessante, e tem mais de uma resposta defensável. Uma delas você já viu hoje.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package not found` | terminal sem `source install/setup.bash` |
| `No module named 'numpy'` | `sudo apt install python3-numpy` — nunca pip no python do sistema |
| o YAML não muda nada | a chave não casa com o nome do nó — use `/**:` |
| `package 'meu_robo_description' not found` | suba com `modelo:=false` |
| `/deriva` sempre 0 | subiu com `deriva:=0.0`, ou o robô não está andando |
| o robô não anda | `ros2 topic hz /scan` — sem laser, o piloto não decide |
| `view_frames` mostra duas árvores | falta a aresta `map → odom` |
| `view_frames` gera PDF vazio | o launch não está rodando — TF é fluxo, não arquivo |
| RViz2 vazio | o G3.2 não depende dele — `view_frames` e `tf2_echo` provam o gate |
| o laser desliza para fora das paredes | **é o ponto da aula**, não um defeito |

## Para a próxima aula (06/10)

**[O SLAM paga a conta da deriva](../etapa06-aula12/index.md).** A aresta `map → odom` deixa de ser identidade e passa a ser calculada a partir do `/scan` — e a correção que ela publica é exatamente a deriva que vocês mediram hoje, com o sinal trocado. Chegue com a árvore de transformadas fechada: o SLAM é construído sobre ela, e não conserta TF errada.
