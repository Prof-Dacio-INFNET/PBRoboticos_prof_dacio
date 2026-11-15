# Exemplo — `aula18-moveit`

**Aula 18 · Etapa 9.** O item 1 do TP5 diz, no enunciado: *"MoveIt 2 — pick-and-place com Collision Object, ros2_control, cinemática inversa no RViz2; ≥3 poses destino evitando colisões."* A correção cobra *"MoveIt 2: cinemática inversa, planejamento, colisão compreendidos"*, e o gate **G5.1** pede o MoveIt 2 configurado e planejando para **≥3 poses distintas com detecção de colisão**, com vídeo ou prints das três poses no RViz2 em `docs/evidencias/tp5/moveit/`. Este exemplo é o caminho mais curto até essa evidência: um braço pronto, uma caixa no caminho, três poses — e a mesma lista rodada com e sem a caixa, para você **ver** o planejador desviar.

> ## Leia isto antes de qualquer coisa
>
> **Nada da parte ROS 2 deste exemplo rodou ainda.** Ele foi escrito numa máquina sem ROS 2, lendo a **fonte** das versões Humble do MoveIt (as URLs estão no fim desta página), e a primeira execução de verdade é o ensaio do professor. Todo arquivo do pacote abre com uma `ADVERTENCIA` dizendo isso. A seção **"O que foi e o que NAO foi verificado"** separa o que foi conferido do que é leitura de código.
>
> **O que roda aqui, sem ROS 2:** o `testar.py`, com 9 grupos e 124 conferências, em menos de 1 s (mais 23 no grupo opcional `--fonte`). Ele monta cada mensagem contra dublês que recusam campo inexistente e tipo errado como o Python gerado pelo ROS 2, roda os nós inteiros contra um `move_group` de mentira e confere a geometria das poses com a cinemática do URDF do Panda.
>
> **As poses padrão são plausíveis, não testadas.** Se uma delas falhar no seu ensaio, a seção [Achar uma pose válida em um minuto](#achar-uma-pose-valida-em-um-minuto) resolve.

```
aula18-moveit/
├── testar.py                 # 9 grupos, sem ROS 2: mensagens, nos, geometria
└── aula18_moveit/            # o pacote ROS 2 -- NUNCA EXECUTADO (ver aviso acima)
    ├── aula18_moveit/cena.py           # a caixa (Collision Object): adicionar | remover
    ├── aula18_moveit/tres_poses.py     # as poses A, B, C; com_proibida; comparar
    ├── aula18_moveit/pegar_e_soltar.py # ROTEIRO de pick-and-place, para a tarefa
    ├── aula18_moveit/cliente.py        # os clientes de acao e de servico do move_group
    ├── aula18_moveit/mensagens.py      # cada mensagem do MoveIt, campo por campo
    ├── aula18_moveit/sequencia.py      # a ordem dos alvos e as tabelas (sem ROS 2)
    └── aula18_moveit/codigos.py        # o numero do erro virando nome e "onde olhar"
```

O robô é o **Panda**, o braço de 7 juntas da Franka que os próprios pacotes do MoveIt trazem prontos pelo `apt` — URDF, SRDF, controladores e um launch de demonstração. Não há *Setup Assistant* nesta aula: ele é o assunto da seção [Como adequar ao seu projeto](#como-adequar-ao-seu-projeto), e custa uma tarde.

```
 Terminal A: ros2 launch moveit_resources_panda_moveit_config demo.launch.py
 +-------------------------------------------------------------------------+
 |  move_group  <-- planeja: OMPL + IK (KDL) + verificador de colisao       |
 |     |  /move_action  /execute_trajectory  /apply_planning_scene          |
 |     v                                                                    |
 |  ros2_control (hardware FALSO: mock_components)                          |
 |     panda_arm_controller   (FollowJointTrajectory)                       |
 |     panda_hand_controller  (GripperCommand)                              |
 |  RViz2 com o painel MotionPlanning                                       |
 +-------------------------------------------------------------------------+
        ^ /apply_planning_scene         ^ /move_action, /execute_trajectory
        |                               |
 Terminal B: cena                Terminal C: tres_poses
 (poe a caixa na cena)           (pede as poses, uma por vez, e conta)
```

Os dois nós deste pacote não sabem nada de cinemática nem de colisão. São **clientes de ação e de serviço** — o mesmo gesto das Aulas 7, 8 e 15. O MoveIt 2 não é uma biblioteca que você chama: é um nó que você contrata.

## Instalar

Uma vez por máquina. O `apt` do MoveIt **não** traz os controladores do `ros2_control` que o demo do Panda sobe, e o pacote do Panda tem as dependências do `move_group` comentadas no `package.xml` dele (para não criar dependência circular) — por isso são quatro nomes, e não um:

```bash
sudo apt update
sudo apt install -y ros-humble-moveit ros-humble-moveit-resources-panda-moveit-config \
  ros-humble-ros2-control ros-humble-ros2-controllers
```

Pelo índice do repositório do ROS 2 (jammy, amd64, novembro de 2026), isso são uns **90 pacotes ROS e cerca de 120 MB** além do `ros-humble-desktop`, mais algumas bibliotecas do Ubuntu que o índice não soma. Não foi medido numa máquina de verdade. Quem já instalou o `ros2_control` para o Gazebo tem uma parte disso.

## Baixar e compilar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

mkdir -p "$PB_WS/src" && cd /tmp && rm -rf pb-a18 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a18 && \
  rm -rf "$PB_DIR/aula18-moveit" "$PB_WS/src/aula18_moveit" && \
  cp -r pb-a18/exemplos/aula18-moveit "$PB_DIR/" && \
  cp -r pb-a18/exemplos/aula18-moveit/aula18_moveit "$PB_WS/src/"
```

No mesmo terminal:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source /opt/ros/humble/setup.bash
cd "$PB_WS" && colcon build --packages-select aula18_moveit
```

## Conferir sem ROS 2

Antes de subir qualquer coisa — e em qualquer máquina, até sem ROS:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-moveit"
python3 testar.py
```

Termina em `todos os testes passaram.` O que ele **não** prova está no fim da saída e no fim desta página.

## Rodar: três terminais

**Terminal A — o braço.** Terminal novo, nada precisa estar no ar. O launch ocupa o terminal até o `Ctrl+C`:

```bash
# ── Terminal A: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 launch moveit_resources_panda_moveit_config demo.launch.py
```

Espere duas coisas antes de seguir: o RViz2 abrir com o Panda em pé, e a linha **`You can start planning now!`** aparecer no terminal. É o `move_group` dizendo que carregou tudo; antes dela, os outros terminais esperam e, passados 20 s, desistem dizendo o que conferir. O demo sobe sete coisas — RViz2, `static_transform_publisher` (`world → panda_link0`), `robot_state_publisher`, `move_group`, `ros2_control_node` e três *spawners* de controlador —, e o que mais costuma demorar é o RViz2.

**Terminal B — a caixa.** Terminal novo, com o A no ar:

```bash
# ── Terminal B: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 run aula18_moveit cena
```

Uma caixa verde aparece no RViz2, 40–50 cm à frente do robô: 10 × 20 × 40 cm, de pé no chão. O nó termina sozinho — a caixa fica, porque ela mora na cena do `move_group`, não no nó que a pediu.

**Terminal C — as três poses.** Terminal novo, com o A no ar e a caixa na cena:

```bash
# ── Terminal C: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 run aula18_moveit tres_poses
```

O braço vai a `ready` (por juntas) e depois a A, B e C (por pose do efetuador), planejando e executando cada uma. Para cada alvo, uma linha: o que o `move_group` respondeu (`SUCCESS (1)`, `PLANNING_FAILED (-1)`...), o tempo de planejamento que o MoveIt informa, o tempo de relógio, o número de pontos da trajetória e o comprimento dela no espaço das juntas, em radianos. Quando um alvo não dá certo, uma linha `olhe:` diz onde procurar. No fim, uma tabela e um resumo — que conta respostas, e diz com todas as letras que isso **não** é uma conferência do TP5.

| Alvo | O quê | Onde |
|---|---|---|
| `ready` | estado nomeado do SRDF, **por juntas** — sem IK | o ponto de partida fixo |
| A | `panda_link8` em (0,45; 0,30; 0,35) m, garra para baixo | à esquerda da caixa |
| B | (0,45; −0,30; 0,35) | à direita: de A para B a reta atravessa a caixa |
| C | (0,45; 0,00; 0,60) | em cima da caixa, garra 10 cm acima dela |
| D | (0,45; 0,00; 0,30) — só com `com_proibida:=true` | **dentro** da caixa |

### As variações, no mesmo Terminal C

Cada bloco abaixo é uma alternativa; rode um de cada vez, no Terminal C, que já tem o `source`.

Só planejar, sem mexer o robô — o RViz2 anima cada trajetória planejada, e todas partem do mesmo lugar:

```bash
# ── Terminal C (já com o source) ──
ros2 run aula18_moveit tres_poses --ros-args -p modo:=planejar
```

Acrescentar a pose D, dentro da caixa — a que **tem** de falhar:

```bash
# ── Terminal C (já com o source) ──
ros2 run aula18_moveit tres_poses --ros-args -p com_proibida:=true
```

A comparação inteira num comando só: tira a caixa, roda A–B–C–D, põe a caixa, roda de novo, e imprime as duas rodadas lado a lado. É a demonstração da aula. Ao terminar, **a caixa fica na cena**:

```bash
# ── Terminal C (já com o source) ──
ros2 run aula18_moveit tres_poses --ros-args -p comparar:=true -p com_proibida:=true
```

Planejar e executar num pedido só (o *Plan & Execute* do RViz2), em vez de separados:

```bash
# ── Terminal C (já com o source) ──
ros2 run aula18_moveit tres_poses --ros-args -p modo:=direto
```

Tirar a caixa:

```bash
# ── Terminal B (já com o source) ──
ros2 run aula18_moveit cena --ros-args -p acao:=remover
```

Os outros parâmetros: `poses` (lista achatada `[x, y, z, x, y, z, ...]`, em metros, no `panda_link0`, **sempre com ponto decimal** — `0.0`, nunca `0`, senão o ROS 2 recusa o tipo), `orientacao` (`[x, y, z, w]`), `comecar_em_ready`, `tempo_planejamento` (padrão 5 s), `tentativas`, `velocidade` (fator de 0 a 1, padrão 0,5), `espera_servidor_s`. No `cena`: `acao`, `id`, `centro`, `tamanho`.

### O que a comparação deve mostrar — e o que pode mostrar

O esperado, pelo raciocínio que está no `testar.py` (grupo 6): sem a caixa, os quatro alvos dão `SUCCESS`; com a caixa, A, B e C continuam dando `SUCCESS`, mas a ida de A para B fica **mais longa** (a coluna de radianos cresce) porque o braço dá a volta; e D falha. O código com que D falha **provavelmente não é** `GOAL_IN_COLLISION` nem `NO_IK_SOLUTION`: no caminho que este exemplo usa (ação `/move_action`, planejador OMPL), a fonte do Humble devolve `GOAL_STATE_INVALID (-27)` quando o OMPL não consegue amostrar nenhum estado válido para o objetivo, ou `TIMED_OUT (-6)` se ele gastar o tempo todo tentando. Os dois querem dizer a mesma coisa aqui — não existe postura do braço que ponha a garra ali sem atravessar a caixa — e o Terminal A diz qual dos dois foi, com `Invalid goal state` ou `Timed out`.

O que **pode** acontecer e não é defeito: duas execuções iguais dão números diferentes (o OMPL é aleatório — veja [Conceitos](#conceitos-em-linguagem-simples)); e, raramente, uma pose válida falha com `PLANNING_FAILED` numa execução e passa na seguinte.

## O que olhar no RViz2

O demo abre o RViz2 já configurado. Os três displays que importam, na árvore da esquerda:

- **MotionPlanning** — o painel de baixo, à esquerda. Na aba *Planning*, os botões **Plan**, **Execute** e **Plan & Execute**; em *Planning Group*, `panda_arm`. O braço laranja com a bolinha azul e as setas é o **estado objetivo**: arraste-o e clique *Plan* — é a mesma IK que o `tres_poses` usa, feita com o mouse. Na aba *Scene Objects*, a caixa do `cena` aparece pelo nome (`caixa`).
- **PlanningScene** — desenha a cena que o `move_group` publica em `/monitored_planning_scene`: o robô e os objetos de colisão, em verde. Se a caixa não aparece aqui, ela não está na cena, e o planejador não sabe que ela existe.
- **Trajectory** — anima a última trajetória planejada (tópico `/display_planned_path`). Marque **Loop Animation** para ela repetir e **Show Trail** para ver o rastro do braço inteiro: é o melhor print para o relatório, porque mostra o **caminho**, não só o destino.

Link em **vermelho** no RViz2 quer dizer colisão. Com o estado objetivo arrastado para dentro da caixa, o braço laranja fica vermelho ali — e o *Plan* falha. É a pose D, feita à mão.

**Para o G5.1**, grave um vídeo curto ou tire três prints — um por pose — com a caixa visível e o *Show Trail* ligado, e cole no relatório a tabela que o Terminal C imprime. Os prints mostram que o braço chegou; a tabela mostra o que o planejador respondeu; o texto do relatório explica o que mudou com a caixa. Os três juntos são a evidência; nenhum sozinho é.

## Achar uma pose válida em um minuto

Se A, B ou C falharem na sua máquina, não procure o erro: troque a pose. Com o Terminal A no ar, arraste o marcador interativo do estado objetivo no RViz2 até onde você quer a garra, clique **Plan & Execute**, e leia a pose do efetuador **onde ele chegou**:

```bash
# ── Terminal D: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 run tf2_ros tf2_echo panda_link0 panda_link8
```

A linha `Translation: [x, y, z]` é a pose que vai no parâmetro `poses`; a `Rotation: in Quaternion [x, y, z, w]` vai em `orientacao`, se você não quiser a garra para baixo. `Ctrl+C` para parar. Como o braço **chegou** lá, a pose tem IK e não colide — é válida por construção. Repita para três lugares e rode o `tres_poses` com elas.

## Conceitos em linguagem simples

**Planning group.** O MoveIt não planeja "o robô": planeja um *grupo* de juntas, declarado no SRDF. No Panda, `panda_arm` é a cadeia de `panda_link0` a `panda_link8` — as 7 juntas do braço; a garra é outro grupo (`hand`). Pedir um plano é sempre pedir para um grupo.

**Cinemática inversa (IK).** Você diz onde quer a **ponta** (posição e orientação do `panda_link8`); a IK descobre os **ângulos das juntas** que a põem lá. Para um braço de 7 juntas, há infinitas respostas (uma junta "sobra"), e há poses sem resposta nenhuma — fora do alcance, que no Panda é de uns 85 cm. No código deste exemplo, a IK **não aparece**: o `tres_poses` manda uma pose, e o MoveIt resolve a IK por dentro do planejamento, chamando o solver do `kinematics.yaml` (KDL, no Panda) para cada candidato a estado final. É por isso que o `ready`, pedido por juntas, não precisa de IK, e A, B e C precisam.

**Planejador amostral (OMPL).** Entre o estado atual e o final, o planejador procura um caminho que não colida. O OMPL faz isso **sorteando** estados do braço e ligando os que não colidem, até conectar o começo ao fim; depois alisa o caminho. Por ser sorteio, **duas execuções iguais dão trajetórias diferentes** — com número de pontos, tempo e comprimento diferentes. Isso não é defeito, e é a frase que o relatório precisa ter quando você comparar "com caixa × sem caixa": a diferença que importa é a que se repete, não a de uma execução.

**Collision checking.** Antes de aceitar um estado, o MoveIt confere se algum link do robô encosta em outro link ou em algum objeto da **cena de planejamento**. A cena é o que alguém **declarou**: o MoveIt não enxerga nada. A caixa do `cena` não existe no mundo; existe na cena, e é por isso que o planejador desvia dela. Com sensor, uma nuvem de pontos vira octomap na cena — mas isso é outra aula.

**ros2_control com hardware falso.** Quem move o braço não é o MoveIt: é o `panda_arm_controller`, um `JointTrajectoryController` do `ros2_control`, que recebe a trajetória e a segue. Aqui o "hardware" é o `mock_components/GenericSystem`, que devolve como posição medida exatamente a posição comandada — um robô perfeito, sem inércia nem atrito. Troque o hardware por um Panda de verdade (ou pelo Gazebo) e o MoveIt e os nós deste exemplo **não mudam nada**: é o argumento do `ros2_control`.

**Plan × execute.** Planejar é calcular a trajetória; executar é mandá-la ao controlador. São dois passos, e o `tres_poses` os mantém separados de propósito (modo `executar`): planeja com `plan_only = True` na ação `/move_action`, olha o resultado, e só então manda a trajetória para `/execute_trajectory`. É o que os botões *Plan* e *Execute* do RViz2 fazem. O modo `direto` junta os dois num pedido só (`plan_only = False`), e o preço aparece na tabela: o `move_group` não informa o tempo de planejamento nesse caminho, só o relógio conta.

## Pick-and-place: o roteiro para a tarefa

O `pegar_e_soltar` é um **roteiro**, e está marcado assim no código: ninguém o executou, nem o professor. Ele faz o pick-and-place **sem física** em 14 passos — põe um cubo de 4 cm no chão, abre a garra, desce sobre ele, fecha, **anexa** o cubo à mão (`AttachedCollisionObject`), leva para o outro lado da caixa, desce, abre, **solta** e recua:

```bash
# ── Terminal C (já com o source) ──
ros2 run aula18_moveit pegar_e_soltar --ros-args -p ate_passo:=6
```

`ate_passo:=6` para depois de fechar a garra, antes de anexar — rode assim primeiro e olhe o RViz2. Sem física quer dizer que nada cai e a garra não sente o cubo: o que faz o cubo ir junto é a **anexação**, que o transforma em parte do robô para o verificador de colisão. A garra é a ação `control_msgs/action/GripperCommand` em `/panda_hand_controller/gripper_cmd`, e o `position` dela é o de **um** dedo (0,035 aberta, 0 fechada), não a abertura entre os dois.

Duas incertezas, ditas no código: se o verificador de colisão aceita os dedos em volta do cubo com a malha de colisão do Panda (a pegada fica 1 cm acima do meio do cubo, de propósito); e se o OMPL desce os 10 cm da pegada numa linha razoável — ele não promete linha reta. Para descida em linha reta, o MoveIt tem o serviço `/compute_cartesian_path` (`moveit_msgs/srv/GetCartesianPath`), que este exemplo não usa.

## O que cada arquivo faz

| Arquivo | Papel | Roda aqui? |
|---|---|---|
| `testar.py` | 9 grupos: sintaxe, pacote, códigos, mensagens contra dublês, sequência, geometria, cliente, nós inteiros, README; `--fonte` confere as definições copiadas contra um clone do `moveit_msgs` | sim |
| `aula18_moveit/cena.py` | põe ou tira a caixa pelo serviço `/apply_planning_scene`; `acao`, `id`, `centro`, `tamanho` | com dublês |
| `aula18_moveit/tres_poses.py` | `ready` + A, B, C (+ D); modos `executar`, `planejar`, `direto`; `comparar` | com dublês |
| `aula18_moveit/pegar_e_soltar.py` | o roteiro de 14 passos; `ate_passo` | com dublês (ordem e alturas) |
| `aula18_moveit/cliente.py` | os clientes de `/move_action`, `/execute_trajectory`, `/apply_planning_scene` e da garra; espera com prazo e diz o que conferir | com dublês |
| `aula18_moveit/mensagens.py` | cada mensagem montada campo por campo: restrição de pose (onde a IK acontece), de juntas, o goal, a caixa, a anexação | com dublês |
| `aula18_moveit/sequencia.py` | percorre os alvos sem parar no tropeço; tabela, comparação, resumo | sim, sem dublês |
| `aula18_moveit/codigos.py` | `MoveItErrorCodes` → nome → onde olhar | sim, sem dublês |

## Como adequar ao seu projeto

O seu robô do projeto é, quase sempre, uma base diferencial — e o MoveIt planeja **braços**. Há dois caminhos para o item 1 do TP5, e o custo deles é muito diferente:

**Caminho 1 — o Panda como o manipulador do seu projeto.** Você usa este exemplo, adapta a cena ao seu cenário (troque a caixa pelo que o seu robô encontra: uma prateleira, uma esteira, uma mesa — `centro` e `tamanho` do `cena`) e escolhe as suas poses com o `tf2_echo`. Custa uma tarde. O relatório diz, com todas as letras, que o braço é o Panda de referência e por quê; e conta como **o seu** sistema o usaria (o braço que pega o pacote que o robô diferencial trouxe, por exemplo). É o caminho que este exemplo recomenda para quem não tem braço no projeto.

**Caminho 2 — a configuração do seu próprio braço.** Se o seu URDF tem um braço, o *MoveIt Setup Assistant* gera o pacote `*_moveit_config` a partir dele: grupos, estados nomeados, matriz de colisão, controladores, e um `demo.launch.py` equivalente ao do Panda.

```bash
# ── um terminal novo ──
source /opt/ros/humble/setup.bash
ros2 launch moveit_setup_assistant setup_assistant.launch.py
```

Custa de um a dois dias na primeira vez, e o que mais toma tempo não é o assistente: é o URDF chegar a ele com limites de junta, inércias e malhas de colisão razoáveis, e os controladores do `ros2_control` baterem com os que o assistente gera. Com a configuração pronta, os três nós deste pacote servem **trocando três nomes** no topo do `mensagens.py`: `GRUPO`, `LINK_EFETUADOR` e `QUADRO` — e `ESTADOS`, `PARA_BAIXO` e as poses, que são do Panda.

**Em qualquer caminho, o que vai para o relatório** é a parte que nenhum script mede: por que essas três poses, o que a caixa representa no seu cenário, o que mudou na trajetória com ela, e o que o `GOAL_STATE_INVALID` da pose D quer dizer. "Cinemática inversa, planejamento, colisão compreendidos" é o critério de correção, e compreensão se mostra no texto.

**Python oficial do MoveIt.** Até a versão 2.5.9 do Humble não havia API Python do MoveIt pelo `apt`. A `moveit_py` foi portada para o Humble na versão **2.5.10** (setembro de 2026) e está no repositório (`ros-humble-moveit-py`). Este exemplo **não a usa**: o cliente de ação funciona em qualquer Humble, e mostra o que a API esconde. Se você quiser usá-la, diga no relatório, e confira com `apt list --installed ros-humble-moveit-py` que ela está na sua máquina.

## O que foi e o que NAO foi verificado

Esta seção existe porque a diferença importa, e porque material de aula que finge ter sido testado custa caro na hora da entrega.

**Foi verificado sem ROS 2, e o `testar.py` prova:**

que todo `.py` compila, é ASCII e cabe em 99 colunas, e que os sete módulos do pacote declaram na docstring que nunca rodaram; que o `package.xml` é XML bem formado, `ament_python`, e declara **todo** pacote ROS que o código importa (`rclpy`, `moveit_msgs`, `shape_msgs`, `geometry_msgs`, `control_msgs`) mais o Panda e o `move_group`; que os três *entry points* do `setup.py` apontam para módulos com `main()`; que a tabela de códigos é **igual** à do `MoveItErrorCodes.msg` do Humble, 30 constantes, e que nenhuma dica dá veredito; que cada mensagem é montada com os campos, quadros, links, tolerâncias e constantes certos **contra dublês gerados das definições do Humble** que recusam campo inexistente, `float64` recebendo `int` e o campo `byte` recebendo número — e que esses dublês de fato recusam; que, com um `move_group` de mentira, o cliente planeja com `plan_only = True` e executa **o mesmo** plano, não executa o que falhou, trata goal recusado, resposta que não chega, execução que não termina, plano vazio e servidor ausente (dizendo o que conferir); que o `comparar` remove a caixa, roda, adiciona, roda, nessa ordem; que o roteiro do pick-and-place tem os 14 passos na ordem, as alturas certas, e para no primeiro passo que falha.

E, por uma conta de cinemática **feita sem o MoveIt** (cinemática direta das 7 juntas copiadas do URDF do Panda, IK numérica dentro dos limites das juntas e um teste de colisão grosseiro com esferas ao longo dos elos): que `ready` põe o `panda_link8` em (0,307; 0; 0,590), o valor conhecido do Panda; que `PARA_BAIXO` é a orientação dele em `ready`; que A, B, C, D e as seis poses do pick-and-place têm IK; que `ready`, A, B e C ficam fora da caixa, que D fica dentro, e que a reta de A a B nas juntas **atravessa** a caixa em 15 de 21 pontos — ou seja, que o planejador tem de desviar.

Com `--fonte`, o grupo 10 conferiu as 22 definições de `moveit_msgs` e a tabela de códigos copiadas no `testar.py` contra um clone da branch `humble` (versão 2.2.3, a mesma do `apt`) — todas iguais.

Os três conferidores do repositório — `conferir-caminhos.py`, `conferir-comandos.py` e `conferir-launch.py` — passaram com este exemplo no lugar. O exemplo não tem launch próprio: ele usa o `demo.launch.py` do Panda sem modificá-lo.

**NAO foi verificado, e ninguém viu rodar — tudo o que é ROS 2:**

- que o `demo.launch.py` do Panda **sobe** numa máquina com Humble pelo `apt` e com os quatro pacotes da seção Instalar, inclusive no WSL2;
- que os nós deste pacote **conversam** com o `move_group`: os nomes `/move_action`, `/execute_trajectory`, `/apply_planning_scene` e `/panda_hand_controller/gripper_cmd` foram lidos na fonte, não vistos num `ros2 action list`;
- que A, B e C **planejam** com a caixa, que D **falha**, e com qual código; a IK do MoveIt (KDL) pode achar posturas diferentes das do `testar.py`, e o verificador de colisão dele usa as malhas do Panda, não esferas;
- que a trajetória de A para B **muda visivelmente** com a caixa;
- que o `tempo_planejamento` de 5 s basta, e que o prazo de 20 s para achar o `move_group` cobre o tempo de subida do demo no WSL2;
- o `pegar_e_soltar` inteiro: a pegada com os dedos em volta do cubo, a anexação, a soltura, e a garra respondendo com hardware falso;
- se o *middleware* padrão (Fast DDS) entrega os resultados grandes da ação `/move_action` sem problema — veja Socorro rápido.

**As fontes do Humble que foram lidas** (branch `humble`, nunca `main` — os nomes mudaram entre versões):

- `https://github.com/moveit/moveit_msgs/tree/humble` — `action/MoveGroup.action`, `action/ExecuteTrajectory.action`, `srv/ApplyPlanningScene.srv` e, em `msg/`, `MotionPlanRequest`, `Constraints`, `PositionConstraint`, `OrientationConstraint`, `JointConstraint`, `BoundingVolume`, `PlanningOptions`, `PlanningScene`, `PlanningSceneWorld`, `CollisionObject`, `AttachedCollisionObject`, `RobotState`, `RobotTrajectory`, `MoveItErrorCodes`. Versão 2.2.3, a mesma do `apt`
- `https://github.com/ros2/common_interfaces/tree/humble` — `shape_msgs/msg/SolidPrimitive.msg`, `geometry_msgs` (o `Quaternion` nasce com `w = 1`), `trajectory_msgs`
- `https://github.com/ros2/rosidl_python/blob/humble/rosidl_generator_py/resource/_msg.py.em` — as verificações de tipo do Python gerado, que os dublês imitam (`byte` como `bytes` de tamanho 1, `float64` recusando `int`)
- `https://github.com/moveit/moveit_resources/tree/humble/panda_moveit_config` — `launch/demo.launch.py` (o que ele sobe, `ros2_control_hardware_type` padrão `mock_components`, pipelines `ompl`, `chomp` e `pilz_industrial_motion_planner`), `config/panda.srdf` (grupos `panda_arm` e `hand`, estados `ready`, `extended`, `transport`, `open`, `close`, efetuador no `panda_link8`), `config/ros2_controllers.yaml` (`panda_arm_controller` e `panda_hand_controller`), `config/gripper_moveit_controllers.yaml` (`follow_joint_trajectory`, `gripper_cmd`), `config/kinematics.yaml` (KDL), `config/initial_positions.yaml`, `config/panda_hand.ros2_control.xacro` (a garra nasce em 0,0) e `package.xml` (as dependências do `move_group` comentadas). Versão 2.0.7, a mesma do `apt`
- `https://github.com/moveit/moveit_resources/blob/humble/panda_description/urdf/panda.urdf` — as juntas, origens e limites que o `testar.py` copia
- `https://github.com/moveit/moveit2/tree/humble` (2.5.10, a mesma do `apt`): `moveit_ros/move_group/include/moveit/move_group/capability_names.h` (os nomes das ações e serviços); `moveit_ros/move_group/src/move_group.cpp` (as capacidades padrão e a frase `You can start planning now!`); `moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp` (`plan_only`, e o `planning_time` só preenchido no modo de planejar); `.../apply_planning_scene_service_capability.cpp`; `moveit_ros/move_group/src/move_group_capability.cpp` (as mensagens de resultado); `moveit_ros/planning_interface/move_group_interface/src/move_group_interface.cpp` (o goal que o `plan()` monta, espelhado no `mensagens.pedido`); `moveit_core/kinematic_constraints/src/utils.cpp` (`constructGoalConstraints`, espelhado no `mensagens.restricoes_de_pose`); `moveit_core/planning_scene/src/planning_scene.cpp` (anexar pelo id, soltar devolvendo ao mundo, `ADD` repetido substituindo); `moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp` (o `is_diff`); `moveit_planners/ompl/ompl_interface/src/model_based_planning_context.cpp` (de onde vêm `GOAL_STATE_INVALID`, `TIMED_OUT` e `PLANNING_FAILED`); `moveit_ros/planning/planning_pipeline/src/planning_pipeline.cpp` (o `/display_planned_path`); `moveit_configs_utils/moveit_configs_utils/moveit_configs_builder.py` (`ompl` como pipeline padrão); `moveit_py/CHANGELOG.rst` (a `moveit_py` portada para o Humble na 2.5.10)
- `https://github.com/ros-controls/ros2_controllers/tree/humble/gripper_controllers` — a ação `~/gripper_cmd`, `reached_goal`, `goal_tolerance` 0,01 e `allow_stalling` falso por padrão
- `https://github.com/ros-controls/control_msgs/blob/humble/control_msgs/action/GripperCommand.action`
- `https://github.com/moveit/moveit2_tutorials/tree/humble/doc` — `tutorials/quickstart_in_rviz` (o painel MotionPlanning, *Show Trail*, vermelho = colisão) e `examples/planning_scene_ros_api` (serviço × tópico para a cena)
- `https://moveit.picknik.ai/humble/doc/tutorials/getting_started/getting_started.html` — a nota sobre o Cyclone DDS
- `https://github.com/ros/rosdistro/blob/master/humble/distribution.yaml` e o índice `Packages` do repositório do ROS 2 — as versões no `apt` e o tamanho da instalação

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `Package 'moveit_resources_panda_moveit_config' not found` | faltou o `apt` da seção Instalar, ou o `source /opt/ros/humble/setup.bash` neste terminal |
| o Terminal A sobe e o `move_group` morre com erro de plugin `chomp` ou `pilz` | o demo carrega os três pipelines; faltou o `ros-humble-moveit` inteiro (ele traz `moveit_planners`) |
| `Could not load controller` / os spawners falham no Terminal A | faltou `ros-humble-ros2-controllers` (o `joint_trajectory_controller` e o `gripper_controllers` vêm dele) |
| o RViz2 abre vazio ou preto no WSL2 | o caminho 3D do WSLg: `export LIBGL_ALWAYS_SOFTWARE=1` antes do `ros2 launch`, no Terminal A — é a mesma bisseção do tutorial *URDF, TF e RViz2*, seção "Se as janelas abrem vazias (WSL2)" |
| `nao achei: /move_action` depois de 20 s | o `move_group` não terminou de subir: espere `You can start planning now!` no Terminal A. Confira `ros2 node list \| grep move_group` e `ros2 action list` |
| `goal RECUSADO` | o `move_group` recusou antes de planejar; o motivo está no Terminal A |
| `PLANNING_FAILED (-1)` e, no Terminal A, `Unable to solve the planning problem` / `No motion plan found. No execution attempted.` | o OMPL não achou caminho no tempo dado. Rode de novo (é sorteio); se repetir, `-p tempo_planejamento:=10.0` ou mude a pose |
| `GOAL_STATE_INVALID (-27)` e `Invalid goal state` no Terminal A | não há postura do braço que satisfaça a pose sem colidir: pose dentro de um objeto, ou fora do alcance. É o esperado para a pose D com a caixa |
| `TIMED_OUT (-6)` e `Timed out` no Terminal A | o tempo acabou; no OMPL, quase sempre é a mesma causa do `GOAL_STATE_INVALID` |
| `NO_IK_SOLUTION (-31)` | não aparece pelo caminho deste exemplo (a IK roda dentro do OMPL); se aparecer, a pose está fora do alcance |
| `START_STATE_IN_COLLISION (-10)`, ou `Start state appears to be in collision` no Terminal A | o braço **já** encosta em algo: a caixa foi posta em cima dele (`centro`/`tamanho` seus?). Tire-a: `cena --ros-args -p acao:=remover` |
| `CONTROL_FAILED (-4)`, ou `Action client not connected to action server: panda_arm_controller/follow_joint_trajectory` | o controlador do braço não está ativo: `ros2 control list_controllers` tem de mostrar `panda_arm_controller` e `joint_state_broadcaster` como `active` |
| `Unable to identify any set of controllers that can actuate the specified joints` | o `move_group` não acha controlador para as juntas: o spawner do `panda_arm_controller` falhou no Terminal A |
| `Invalid Trajectory: start point deviates from current robot state` | o robô andou entre planejar e executar (outro nó, ou o RViz2, mandou mover). Rode de novo |
| `SEM RESPOSTA`: o Terminal A diz que terminou e o Terminal C não recebe | suspeita de DDS com resultados grandes. A documentação do MoveIt para Humble recomenda o Cyclone DDS: `sudo apt install ros-humble-rmw-cyclonedds-cpp` e `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` **em todos os terminais**, inclusive o A. Não verificado aqui |
| `cena` diz `success = False` ao remover, e o Terminal A diz `Tried to remove world object 'caixa', but it does not exist in this scene.` | não havia caixa; nada a fazer |
| a caixa não aparece no RViz2 e o `cena` disse `success = True` | o display **PlanningScene** está desmarcado, ou o *Planning Scene Topic* dele não é `/monitored_planning_scene` |
| `InvalidParameterTypeException` ao passar `poses` | um número sem ponto decimal: `0` em vez de `0.0` |
| `pegar_e_soltar`: `Attempting to attach object 'peca' to link 'panda_hand' but no geometry specified and such an object does not exist in the collision world` | o passo 1 (o cubo) não entrou na cena; rode com `ate_passo:=1` e olhe o RViz2 |
| `pegar_e_soltar`: a garra não responde | `ros2 control list_controllers` deve mostrar `panda_hand_controller` `active`; a ação é `/panda_hand_controller/gripper_cmd` |
| `pegar_e_soltar` para no passo 5 (pegada) | os dedos tocam o cubo na malha de colisão do Panda. Suba a pegada (`FOLGA` no topo do arquivo) ou use um cubo menor |

## Licença

MIT, como todo o diretório `exemplos/`.
