# Diagnosticar o Nav2 — onde olhar, não um veredito

Esta ferramenta **não corrige, não valida, não antecipa nota e não substitui o enunciado do TP4**: ela diz **onde olhar** quando o Nav2 está no ar e o robô não navega. A referência é o enunciado; a responsabilidade pela entrega é sua, antes e depois de rodar isto.

!!! danger "Isto não é correção, nem validação prévia"
    Os três estados são `achei`, `nao achei` e `olhe`. Não existe `ok`, não existe `falha`, não existe `passou`. A diferença de vocabulário não é capricho: o script **não tem como saber se está certo**. `achei` não quer dizer que o seu Nav2 está bom, e `nao achei` não quer dizer que está ruim. Nos dois casos quer dizer a mesma coisa: **vá olhar isso.**

Ela existe por causa de um fato desagradável: *"o Nav2 não navega"* tem umas dez causas, e **nove delas não emitem mensagem de erro nenhuma.** O gerenciador de ciclo de vida que para calado no quarto nó. A pose inicial que ninguém deu — e sem ela, no Humble, o AMCL não publica `map → odom` nem `/amcl_pose`, porque o código dele diz literalmente `if (!initial_pose_is_known_) return;`. O segundo publicador em `/cmd_vel`, com o robô obedecendo ao último que falou. Sozinho na véspera do **G4.1 (04/11)**, o aluno testa essas dez coisas na ordem errada e gasta a noite na última. O script testa na ordem em que compensa.

Ele chama o CLI (`ros2 node list`, `ros2 lifecycle get`, `ros2 topic info`, …) por `subprocess` e **interpreta a saída**. Não usa `rclpy` de propósito: assim roda com qualquer workspace sourceado, não cria nó nenhum, não assina tópico nenhum e não concorre com o seu Nav2 pelo *discovery*.

### O que ele não alcança — e é o que os gates cobram

Um comando consegue dizer que um nó está no ar, que um tópico tem publicador, que uma transformada existe. Nenhum comando consegue dizer se **o robô realmente anda**, se o mapa publicado é **do seu cenário** e não o do exemplo, se a **rota faz sentido** na sua planta, ou se o **relatório responde ao que foi pedido**. Isso é exatamente o que o G4.1 e o G4.2 avaliam, e é por isso que essas quatro linhas aparecem **em toda execução**, sempre como `olhe`, numa seção com esse nome. Declarar o limite é parte da ferramenta, não rodapé dela.

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

# a cópia antiga sai antes, e só depois de o clone ter dado certo: cp -r sobre
# pasta existente ANINHA (aula16-clinica/aula16-clinica) e você passa a rodar a
# versão velha sem ela dizer nada. A guarda é o próprio encadeamento com &&:
# comentário no meio da cadeia a quebraria, e por isso ele está aqui em cima.
cd /tmp && rm -rf pb-a16 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a16 && \
  rm -rf "$PB_DIR/aula16-clinica" && \
  cp -r pb-a16/exemplos/aula16-clinica "$PB_DIR/"
```

Só biblioteca padrão do Python 3.10: nada de `pip`, nada de `apt`, nada para compilar. Não é um pacote ROS 2 — não entra no `$PB_WS/src` e não precisa de `colcon build`.

## Rodar

Com o Nav2 **no ar**, em **outro** terminal — o mesmo gesto do `rqt_graph`: um terminal segura o launch, outro faz as perguntas.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
cd "$PB_DIR/aula16-clinica"
python3 diagnosticar_nav2.py
```

Três opções, e um `--help` que explica cada uma:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-clinica"
python3 diagnosticar_nav2.py --rapido                  # só 1, 2, 3 e 6
python3 diagnosticar_nav2.py --timeout 10              # máquina cheia, WSL2 lento
python3 diagnosticar_nav2.py --sem-cor | tee diag.txt  # para colar no fórum
python3 diagnosticar_nav2.py --help
```

A cor desliga sozinha quando a saída não é um terminal — redirecionar para arquivo ou canalizar para `tee` não enche o texto de lixo de escape. O `--sem-cor` serve para o caso contrário: desligar a cor **estando** num terminal.

**Código de saída:** `0` quando não sobrou nada para olhar, `1` quando sobrou, `2` quando a opção passada não faz sentido. E nenhum dos três é um julgamento sobre a sua entrega.

## Como ler a saída

| Marca | Significado | O que fazer |
|---|---|---|
| `achei` | o comando devolveu o que se procurava | nada — e isso não quer dizer que esteja certo |
| `nao achei` | o comando não devolveu | olhar: entra na lista final, com o que fazer a seguir |
| `olhe` | o script **não consegue** decidir aquilo | ler você mesmo; não conta para o código de saída |

No fim ele imprime **onde olhar, na ordem em que costuma compensar** — e cada item vem com uma linha concreta de *o que fazer a seguir*, não com um diagnóstico. Quando a lista sai vazia, ele diz com todas as letras **o que isso não significa**: que esgotou o que um script enxerga, e não que o Nav2 está pronto.

## O que cada verificação olha

| # | Verificação | Comando | Por que ela existe, e nessa posição |
|---|---|---|---|
| 1 | o ambiente | `which ros2`, `$ROS_DISTRO`, `$AMENT_PREFIX_PATH` | sem `ros2` no PATH nada abaixo quer dizer nada; `AMENT_PREFIX_PATH` só com `/opt/ros` é o terminal que nunca sourceou o workspace do projeto, e o erro que ele produz fala de "pacote não encontrado" |
| 2 | os nós no ar | `ros2 node list` | os onze nomes do bringup do Humble, um por linha. "Falta algo no Nav2" não ajuda; "falta o `velocity_smoother`" resolve em dez segundos |
| 3 | o ciclo de vida | `ros2 lifecycle get <nó>` | `active [3]` ou não. Os dois `lifecycle_manager` ficam de fora: eles **gerenciam** o ciclo de vida, não o têm |
| 4 | a TF | `ros2 topic echo /tf_static --once`, `ros2 run tf2_ros tf2_echo map odom` | `map → odom` é a aresta que decide o TP4, e quem a publica é o AMCL **depois** da pose inicial |
| 5 | a pose inicial | `ros2 topic info /amcl_pose`, `ros2 topic echo /amcl_pose --once` | duas linhas separadas de propósito: ter publicador não é ter publicado. No Humble o AMCL cria o tópico na configuração e só escreve nele depois do `2D Pose Estimate` |
| 6 | o `/cmd_vel` | `ros2 topic info /cmd_vel --verbose` | **dois publicadores é defeito** e não dá erro: o robô obedece ao último que falou, o sintoma é andar truncado, e nenhum nó reclama. Lê os **nomes** das pontas, porque saber que são dois não ajuda — saber que um deles é o `piloto` da Aula 11 diz o que derrubar |
| 7 | a cadeia do `/cmd_vel` | `ros2 topic info /cmd_vel_nav --verbose`, `ros2 topic hz /cmd_vel_nav` | `controller_server → /cmd_vel_nav → velocity_smoother → /cmd_vel`. Publicador sem assinante aqui é o "robô não anda e ninguém reclama" clássico |
| 8 | os servidores de ação | `ros2 action list` | `/navigate_to_pose` é a ação do **G4.1**; `/follow_waypoints` ou `/navigate_through_poses`, a do **G4.2** |
| 9 | os costmaps | `ros2 topic info /global_costmap/costmap`, idem local | o global é do `planner_server`, o local é do `controller_server` — qual dos dois falta já aponta o nó |
| 10 | o mapa | `ros2 topic info /map --verbose` | o mapa é publicado **uma vez**: com durabilidade `VOLATILE`, quem assina depois (RViz2, AMCL, costmaps) nunca recebe nada, e o sintoma é um RViz2 cinza sem mensagem de erro |

Duas minúcias de QoS que dão trabalho a quem não as conhece estão embutidas. O `/tf_static` é *transient local*: um `topic echo` com a durabilidade padrão (*volatile*) **não recebe** a mensagem latched e parece que ninguém publica — por isso o script pede `--qos-durability transient_local`, e cai no `echo` simples se a sua versão do CLI não aceitar a opção. E o `tf2_echo` do Humble não termina sozinho nem aceita `--timeout`: quem o corta é o timeout do `subprocess`, e a transformada já está na saída parcial, se existir.

### A ordem não é decorativa, e ele para quando a base cai

Cada verificação supõe a anterior. Sem `ros2` no PATH não há o que consultar; sem nó do Nav2 no ar não há ciclo de vida para consultar; sem `map → odom` o planejador não tem onde planejar. Então, quando falta o comando `ros2`, ou quando **nenhum** dos onze nós está no ar, o script **para ali** e declara que o resto não foi olhado — em vez de imprimir dez pendências que são todas eco da primeira. Dez itens numa lista esconde o único que importa.

Dentro da seção 3 vale o mesmo raciocínio, e ele aparece na redação do conselho: o gerenciador ativa **um nó por vez**, então o primeiro inativo na ordem de subida é **onde ele parou**, e os de baixo estão inativos por consequência. O script diz isso em vez de mandar consertar três coisas.

A ordem de subida usada é a do bringup oficial do Humble (`localization_launch.py` e depois `navigation_launch.py`), e não a ordem alfabética: listar em outra ordem apontaria o lugar errado.

## O que foi e o que não foi verificado

**Não há ROS 2 na máquina em que isto foi escrito.** Nada aqui rodou contra um Nav2 de verdade — sem `colcon build`, sem `ros2 launch`, sem nó no ar. A primeira execução contra um sistema real é a sua, na Aula 16.

O que **está** provado, e está provado de verdade, é a **interpretação das saídas**. O `testar.py` monta um `ros2` de mentira — um diretório temporário com um script executável chamado `ros2` posto no **início** do `PATH`, que devolve saídas fixas conforme os argumentos — e roda o `diagnosticar_nav2.py` inteiro, por `subprocess`, contra seis cenários montados à mão. O diagnóstico não sabe que o `ros2` é falso, e é isso que faz o teste valer.

O que **não** está provado: que `ros2 lifecycle get` devolve exatamente `active [3]` na sua máquina, que `ros2 topic info --verbose` imprime os blocos no formato que o script lê, que o `tf2_echo` do seu Humble escreve `- Translation:`. Os formatos foram copiados da saída documentada do CLI do Humble, mas **copiados, não observados aqui**. Se na Aula 16 algum deles vier diferente, o sintoma será uma linha `olhe` onde devia haver `achei` — o script foi escrito para degradar assim, nunca para travar: todo subprocesso tem timeout, e toda saída que ele não entende vira `olhe` com a causa provável.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-clinica"
python3 testar.py
```

Cerca de 20 segundos, e termina em `todos os testes passaram.` (saída 0) ou na lista das falhas (saída 1). Os seis cenários:

| Cenário | O que ele monta | O que o teste cobra do diagnóstico |
|---|---|---|
| (a) | tudo no ar e ativo, pose inicial dada, um publicador em `/cmd_vel` | lista final **vazia**, saída 0 — e a frase de que lista vazia não é Nav2 pronto |
| (b) | nenhum nó do Nav2 no ar | **uma** pendência, não onze; as seções 3 a 10 declaradas como não olhadas; o conselho cita `ros2 launch` e o `ROS_DOMAIN_ID` |
| (c) | nós no ar, `bt_navigator` em `unconfigured` | o `bt_navigator` é o **primeiro** da lista e leva o conselho "o gerenciador parou AQUI"; os dois abaixo dele são tratados como consequência; `/cmd_vel` sem publicador e `/navigate_to_pose` ausente aparecem juntos, como no mundo real |
| (d) | tudo ativo e **ninguém deu a pose inicial** | o ciclo de vida não acusa nada — e `map → odom` é a primeira pendência, com `initial_pose_is_known_` nomeado no conselho |
| (e) | **dois** publicadores em `/cmd_vel` | os dois são achados e **nomeados**; o conselho diz o que derrubar (`piloto:=false`); nada mais na saída acusa coisa alguma |
| (f) | sem `ros2` no PATH | acusa o comando ausente, para ali, e não tenta chamar o que não existe — rodar no Windows, fora do WSL2, não quebra nada |

O sétimo grupo cobra as regras que valem em **todo** cenário: que `--rapido` olha 1, 2, 3 e 6 e **declara** as que não olhou; que `--sem-cor` não deixa escape nenhum na saída; que as 221 linhas de relatório dos sete casos usam **só** `achei`, `nao achei` e `olhe`; que o cabeçalho diz sempre as quatro coisas que a ferramenta não faz; que a seção do que está fora do alcance sai sempre, inclusive em `--rapido` e inclusive quando não sobrou pendência; e que todo item da lista final vem com o que fazer a seguir.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `comando ros2 no PATH: nao achei` | falta `source /opt/ros/humble/setup.bash` **neste** terminal |
| `workspace sourceado: 2 prefixo(s), todos sob /opt/ros` | falta `source "$PB_WS/install/setup.bash"`; o `ros2 launch` vai reclamar de pacote inexistente, e a causa é esta |
| `ros2 node list responde: olhe` | o `ros2` existe mas o *daemon* não respondeu; tente `ros2 daemon stop` e rode de novo, ou aumente o `--timeout` |
| `algum no do Nav2 no ar: nao achei`, com o launch rodando | `ROS_DOMAIN_ID` diferente entre os dois terminais — é o motivo nº 1 de um terminal não ver os nós do outro |
| vários nós em `unconfigured`, nenhum erro no terminal | o gerenciador parou no **primeiro** da lista; o nome do nó em que ele travou está no terminal do `lifecycle_manager`, e em nenhum outro lugar |
| um nome na lista `node_names` do gerenciador que não existe de verdade | o gerenciador fica preso esperando e o Nav2 todo para em "Configuring", calado. É o jeito nº 1 de perder uma hora |
| `aresta map -> odom: nao achei` | **você ainda não deu a pose inicial.** No Humble o AMCL não publica nada antes dela; clique o `2D Pose Estimate` no RViz2, ou suba com `pose_inicial_auto:=true` |
| `/amcl_pose ja publicou: nao achei`, e você jurou ter clicado | parado o AMCL pode ficar calado; mande um goal e rode de novo. A nuvem que não aparece no RViz2 tem essa mesma causa |
| a nuvem de partículas não aparece no RViz2 | três causas, nesta ordem: a pose inicial não foi dada; o display tem de ser `nav2_rviz_plugins/ParticleCloud`; o QoS tem de ser *Best Effort* |
| `/cmd_vel tem UM publicador: 2 publicadores` | sobrou um publicando: o `piloto` reativo da Aula 11 (`piloto:=false`), um `teleop_twist_keyboard` esquecido, um segundo launch no ar |
| `/cmd_vel tem assinante: nao achei` | o Nav2 manda velocidade e ninguém ouve: o nó do robô (o `mundo` da Aula 11, ou a sua base) não subiu. Planejar funciona e o robô fica parado |
| `/cmd_vel_nav: 1 publicador(es) e nenhum assinante` | o `velocity_smoother` saiu do launch, ou saiu **com os remapeamentos ainda no lugar** — o `controller_server` fala em `/cmd_vel_nav` e ninguém ouve |
| `/navigate_to_pose existe: nao achei` | o `bt_navigator` não está no ar ou não está ativo; sem essa ação o `Nav2 Goal` do RViz2 não tem com quem falar |
| `/map durabilidade transient local: nao achei` (`VOLATILE`) | o mapa é publicado uma única vez; no display `Map` do RViz2, `Durability Policy` tem de ser `Transient Local` |
| `/global_costmap/costmap com publicador: nao achei` | o `planner_server` não está ativo, ou o `global_costmap` do seu `nav2.yaml` aponta um frame que a sua TF não tem |
| `trafego em /cmd_vel_nav: olhe` sempre | é o esperado **sem goal ativo**. Essa linha nunca vira pendência: o script não tem como saber se há um goal em curso |
| a saída toda vira `olhe` | o `ros2` responde mas o formato da saída não é o que o script lê; rode o comando da coluna "Comando" da tabela à mão e compare |

## Como adequar ao seu projeto

As duas listas que importam estão no topo do `diagnosticar_nav2.py`, declaradas e comentadas: `ESPERADOS` (os onze nomes, na ordem de subida) e `CURA_NO` (uma linha de *o que fazer* por nó). Se o seu launch batiza os nós de outro jeito, ou se você tirou o `smoother_server` da lista do gerenciador, mexa nessas duas e o resto continua valendo. Se você usa namespace, troque a comparação por nome curto (`nome_curto`) pela comparação com o caminho completo — está numa função de três linhas, de propósito.

E se um comando novo passar a valer a pena olhar, o molde está pronto: uma função `secao_N_...`, uma chamada a `rodar`, e um `conferir(nome, estado, detalhe, ordem, cura)` por linha. O `testar.py` ganha o cenário correspondente antes da função, não depois: foi assim que os seis cenários apareceram.

Veja também: [aula 15 — Nav2](../aula15-nav2/index.md), [revisar a entrega do TP3](../tp3/revisar-entrega/index.md) e [os gates dos TPs](../../recursos/gates-tps.md).

## Licença

MIT, como todo o diretório `exemplos/`.
