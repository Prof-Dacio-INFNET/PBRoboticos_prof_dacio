# Diagnosticar o Nav2 — onde olhar, não um veredito

Esta ferramenta **não corrige, não valida, não antecipa nota e não substitui o enunciado do TP4**: ela diz **onde olhar** quando o Nav2 está no ar e o robô não navega. A referência é o enunciado; a responsabilidade pela entrega é sua, antes e depois de rodar isto.

!!! danger "Isto não é correção, nem validação prévia"
    Os três estados são `achei`, `nao achei` e `olhe`. Não existe `ok`, não existe `falha`, não existe `passou`. A diferença de vocabulário não é capricho: o script **não tem como saber se está certo**. `achei` não quer dizer que o seu Nav2 está bom, e `nao achei` não quer dizer que está ruim. Nos dois casos quer dizer a mesma coisa: **vá olhar isso.**

Ela existe por causa de um fato desagradável: *"o Nav2 não navega"* tem umas dez causas, e **nove delas não emitem mensagem de erro nenhuma.** O gerenciador de ciclo de vida que para calado no quarto nó. A pose inicial que ninguém deu — e sem ela, no Humble, o AMCL não publica `map → odom` nem `/amcl_pose`, porque o código dele diz literalmente `if (!initial_pose_is_known_) return;`. O publicador intruso em `/cmd_vel` — o `piloto` da Aula 11 que ficou no ar —, com o robô obedecendo ao último que falou. Sozinho na véspera do **G4.1 (04/11)**, o aluno testa essas dez coisas na ordem errada e gasta a noite na última. O script testa na ordem em que compensa.

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

No fim ele imprime **onde olhar, na ordem em que costuma compensar** — e cada item vem com uma linha concreta de *o que fazer a seguir*, não com um diagnóstico. O que é só consequência de outro item não ganha item próprio: entra numa linha agrupada embaixo da causa (veja *A ordem não é decorativa*, abaixo). Quando a lista sai vazia, ele diz com todas as letras **o que isso não significa**: que esgotou o que um script enxerga, e não que o Nav2 está pronto.

## O que cada verificação olha

| # | Verificação | Comando | Por que ela existe, e nessa posição |
|---|---|---|---|
| 1 | o ambiente | `which ros2`, `$ROS_DISTRO`, `$AMENT_PREFIX_PATH` | sem `ros2` no PATH nada abaixo quer dizer nada; `AMENT_PREFIX_PATH` só com `/opt/ros` é o terminal que nunca sourceou o workspace do projeto, e o erro que ele produz fala de "pacote não encontrado" |
| 2 | os nós no ar | `ros2 node list` | os onze nomes do bringup do Humble, um por linha. "Falta algo no Nav2" não ajuda; "falta o `velocity_smoother`" resolve em dez segundos |
| 3 | o ciclo de vida | `ros2 lifecycle get <nó>` | `active [3]` ou não. Os dois `lifecycle_manager` ficam de fora: eles **gerenciam** o ciclo de vida, não o têm |
| 4 | a TF | `ros2 topic echo /tf_static --once`, `ros2 run tf2_ros tf2_echo map odom` | `map → odom` é a aresta que decide o TP4, e quem a publica é o AMCL **depois** da pose inicial |
| 5 | a pose inicial | `ros2 topic info /amcl_pose`, `ros2 topic echo /amcl_pose --once` | duas linhas separadas de propósito: ter publicador não é ter publicado. No Humble o AMCL cria o tópico na configuração e só escreve nele depois do `2D Pose Estimate` |
| 6 | o `/cmd_vel` | `ros2 topic info /cmd_vel --verbose` | **publicador que não é do Nav2 é defeito** e não dá erro: o robô obedece ao último que falou, o sintoma é andar truncado, e nenhum nó reclama. A regra é por **nome**, não por contagem: um Nav2 Humble saudável já tem **seis** publicadores ali — o `velocity_smoother` e o `behavior_server` cinco vezes, um por plugin de comportamento (spin, backup, drive_on_heading, assisted_teleop, wait). Qualquer outro nome é intruso, e é ele que a linha nomeia (`intruso: piloto`). A quantidade de `behavior_server` muda com os plugins do seu `nav2.yaml`, e por isso não é conferida; sem `velocity_smoother` entre os publicadores, ou com ele em dobro (dois Nav2 no ar), a linha também acusa |
| 7 | a cadeia do `/cmd_vel` | `ros2 topic info /cmd_vel_nav --verbose`, `ros2 topic hz /cmd_vel_nav` | `controller_server → /cmd_vel_nav → velocity_smoother → /cmd_vel`. Publicador sem assinante aqui é o "robô não anda e ninguém reclama" clássico |
| 8 | os servidores de ação | `ros2 action list` | `/navigate_to_pose` é a ação do **G4.1**; `/follow_waypoints` ou `/navigate_through_poses`, a do **G4.2** |
| 9 | os costmaps | `ros2 topic info /global_costmap/costmap`, idem local | o global é do `planner_server`, o local é do `controller_server` — qual dos dois falta já aponta o nó |
| 10 | o mapa | `ros2 topic info /map --verbose` | o mapa é publicado **uma vez**: com durabilidade `VOLATILE`, quem assina depois (RViz2, AMCL, costmaps) nunca recebe nada, e o sintoma é um RViz2 cinza sem mensagem de erro |

Duas minúcias de QoS que dão trabalho a quem não as conhece estão embutidas. O `/tf_static` é *transient local*: um `topic echo` com a durabilidade padrão (*volatile*) **não recebe** a mensagem latched e parece que ninguém publica — por isso o script pede `--qos-durability transient_local`, e cai no `echo` simples se a sua versão do CLI não aceitar a opção. E o `tf2_echo` do Humble não termina sozinho nem aceita `--timeout`: quem o corta é o timeout do `subprocess`, e a transformada já está na saída parcial, se existir.

### A ordem não é decorativa, e ele para quando a base cai

Cada verificação supõe a anterior. Sem `ros2` no PATH não há o que consultar; sem nó do Nav2 no ar não há ciclo de vida para consultar; sem `map → odom` o planejador não tem onde planejar. Então, quando falta o comando `ros2`, ou quando **nenhum** dos onze nós está no ar, o script **para ali** e declara que o resto não foi olhado — em vez de imprimir dez pendências que são todas eco da primeira. Dez itens numa lista esconde o único que importa.

Dentro da seção 3 vale o mesmo raciocínio, e ele aparece na redação do conselho: o gerenciador ativa **um nó por vez**, então o primeiro inativo na ordem de subida é **onde ele parou**, e os de baixo estão inativos por consequência. O script diz isso em vez de mandar consertar três coisas.

E a lista final leva isso até o fim. Na seção 3 cada nó inativo continua com a sua linha — ali ela mostra até onde o gerenciador chegou —, mas em *Onde olhar* só o primeiro vira item; os outros entram numa **linha agrupada** logo embaixo dele, junto com o que o mesmo ciclo de vida parado explica: a aresta `map → odom` quando o AMCL nem está ativo, e o `/cmd_vel` sem `velocity_smoother` quando o `velocity_smoother` está inativo. Com `autostart:=false` a lista tinha onze itens, oito deles *provavelmente consequência, não causa*, e a única linha que importava se afogava no meio; agora é um item:

```text
Onde olhar, na ordem em que costuma compensar:
   1. ativo: map_server
      este e' o primeiro da ordem de subida que nao esta ativo: o gerenciador
      parou AQUI -- ou alguem o desativou a mao. [...]
      (e mais 8 nos inativos por consequencia: amcl, controller_server,
      smoother_server, planner_server, behavior_server, bt_navigator,
      waypoint_follower, velocity_smoother; e, pelo mesmo ciclo de vida
      parado, a aresta map -> odom e o /cmd_vel sem velocity_smoother --
      resolva o primeiro e rode de novo)
```

A ordem de subida usada é a do bringup oficial do Humble (`localization_launch.py` e depois `navigation_launch.py`), e não a ordem alfabética: listar em outra ordem apontaria o lugar errado.

## O que foi e o que não foi verificado

**A ferramenta já rodou contra um ROS 2 Humble de verdade**, na máquina do professor, em **02/11**, duas vezes: uma com o sistema saudável e navegando (e o `piloto` da Aula 11 subido de propósito para provocar um publicador a mais em `/cmd_vel`), outra com `autostart:=false`, sem nenhum nó ativo. Os **formatos do CLI bateram** com o que o script supunha: `active [3]` e `unconfigured [1]` no `ros2 lifecycle get`, a linha `Publisher count:` e os blocos `Node name:` / `Endpoint type:` do `ros2 topic info --verbose`, o `/tf_static` com as três transformadas, os dois costmaps, o `/map` em `TRANSIENT_LOCAL`, o `ros2 action list`. Nenhuma linha virou `olhe` por formato desconhecido.

O que a execução real **corrigiu** foram duas interpretações, não formatos:

- **A regra do `/cmd_vel`.** Ela dizia "UM publicador", e a tela saudável mostrou sete — o `piloto`, o `velocity_smoother` e o `behavior_server` **cinco vezes**. Sem o intruso seriam seis, todos legítimos, e a ferramenta diria `nao achei` num Nav2 sem defeito. A regra agora é por nome: `velocity_smoother` e `behavior_server` (em qualquer quantidade) são esperados, **qualquer outro nome é intruso**, e só o intruso aparece no detalhe.
- **A lista final do ciclo de vida parado.** Com `autostart:=false` a ordem saiu certa (`ativo: map_server` primeiro, `map → odom` como consequência), mas a lista tinha onze itens e oito eram eco do primeiro. Agora as consequências entram numa linha agrupada embaixo da causa, e a lista tem **um** item.

O que **está** provado, além disso, é a **interpretação das saídas** em cenários que não dá para provocar sob demanda. O `testar.py` monta um `ros2` de mentira — um diretório temporário com um script executável chamado `ros2` posto no **início** do `PATH`, que devolve saídas fixas conforme os argumentos — e roda o `diagnosticar_nav2.py` inteiro, por `subprocess`, contra onze cenários montados à mão; três deles, (a2), (e2) e (f), reproduzem as duas telas de 02/11. O diagnóstico não sabe que o `ros2` é falso, e é isso que faz o teste valer.

O que **não** está provado: que o Nav2 de **cada aluno** responde igual ao da máquina do professor. Um `nav2.yaml` com outros plugins de comportamento muda quantas vezes o `behavior_server` aparece em `/cmd_vel` (a regra já não depende disso); um launch com namespace muda os nomes (veja *Como adequar ao seu projeto*). Se algum formato vier diferente, o sintoma será uma linha `olhe` onde devia haver `achei` — o script foi escrito para degradar assim, nunca para travar: todo subprocesso tem timeout, e toda saída que ele não entende vira `olhe` com a causa provável.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-clinica"
python3 testar.py
```

Cerca de 50 segundos, e termina em `todos os testes passaram.` (saída 0) ou na lista das falhas (saída 1). Os cenários:

| Cenário | O que ele monta | O que o teste cobra do diagnóstico |
|---|---|---|
| (a) | tudo no ar e ativo, pose inicial dada, só o `velocity_smoother` em `/cmd_vel` | lista final **vazia**, saída 0 — e a frase de que lista vazia não é Nav2 pronto |
| (a2) | o saudável **de verdade** de 02/11: `velocity_smoother` + `behavior_server` x5 em `/cmd_vel` | `achei`, com o detalhe `velocity_smoother + behavior_server x5, como esperado`; lista vazia. E com `behavior_server` x2 também `achei`: a contagem não é regra |
| (b) | nenhum nó do Nav2 no ar | **uma** pendência, não onze; as seções 3 a 10 declaradas como não olhadas; o conselho cita `ros2 launch` e o `ROS_DOMAIN_ID` |
| (c) | nós no ar, `bt_navigator` em `unconfigured` | o `bt_navigator` é o **primeiro** da lista e leva o conselho "o gerenciador parou AQUI"; os dois abaixo dele e o `/cmd_vel` mudo entram na linha agrupada, e continuam com linha própria na seção 3; `/navigate_to_pose` ausente aparece junto, como no mundo real |
| (d) | tudo ativo e **ninguém deu a pose inicial** | o ciclo de vida não acusa nada — e `map → odom` é a primeira pendência, com `initial_pose_is_known_` nomeado no conselho |
| (d2) | sem pose inicial **e** o gerenciador parado no `planner_server` (a tela de 26/10) | `map → odom` vem **antes** do `planner_server`; os quatro nós abaixo dele vão para a linha agrupada |
| (e) | o `piloto` da Aula 11 junto do `velocity_smoother` em `/cmd_vel` | `nao achei` com detalhe `intruso: piloto`; o conselho diz o que derrubar (`Ctrl+C`, `piloto:=false`); nada mais na saída acusa coisa alguma |
| (e2) | a tela 1 de 02/11: os seis do Nav2 e o `piloto` | `nao achei` nomeando **só** o `piloto`; nem `behavior_server` nem `velocity_smoother` são chamados de intruso |
| (f) | a tela 2 de 02/11: `autostart:=false`, nenhum nó ativo, os tópicos dos nós do Nav2 ainda não criados | **um** item na lista final, `ativo: map_server`, com a linha agrupada nomeando os oito nós, a aresta e o `/cmd_vel`; a seção 3 mantém as nove linhas; tópico inexistente vira `olhe` |
| (g) | dois Nav2 no ar: `velocity_smoother` em dobro em `/cmd_vel` | `nao achei` com `velocity_smoother x2`, e o conselho aponta o segundo launch |
| (h) | sem `ros2` no PATH | acusa o comando ausente, para ali, e não tenta chamar o que não existe — rodar no Windows, fora do WSL2, não quebra nada |

O sétimo grupo cobra as regras que valem em **todo** cenário: que `--rapido` olha 1, 2, 3 e 6, **declara** as que não olhou e agrupa as consequências do mesmo jeito; que `--sem-cor` não deixa escape nenhum na saída; que as 432 linhas de relatório de todos os casos usam **só** `achei`, `nao achei` e `olhe`; que o cabeçalho diz sempre as quatro coisas que a ferramenta não faz; que a seção do que está fora do alcance sai sempre, inclusive em `--rapido` e inclusive quando não sobrou pendência; e que todo item da lista final vem com o que fazer a seguir.

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
| `/cmd_vel so' com os publicadores do Nav2: intruso: piloto` | sobrou um publicando que não é do Nav2: o `piloto` reativo da Aula 11 (`Ctrl+C` no terminal dele, ou `piloto:=false` no launch), um `teleop_twist_keyboard` esquecido. O `behavior_server` repetido várias vezes na mesma lista **não** é defeito: é um publicador por comportamento |
| `/cmd_vel so' com os publicadores do Nav2: ... velocity_smoother x2` | dois Nav2 no ar — um launch antigo num terminal esquecido |
| `/cmd_vel tem assinante: nao achei` | o Nav2 manda velocidade e ninguém ouve: o nó do robô (o `mundo` da Aula 11, ou a sua base) não subiu. Planejar funciona e o robô fica parado |
| `/cmd_vel_nav: 1 publicador(es) e nenhum assinante` | o `velocity_smoother` saiu do launch, ou saiu **com os remapeamentos ainda no lugar** — o `controller_server` fala em `/cmd_vel_nav` e ninguém ouve |
| `/navigate_to_pose existe: nao achei` | o `bt_navigator` não está no ar ou não está ativo; sem essa ação o `Nav2 Goal` do RViz2 não tem com quem falar |
| `/map durabilidade transient local: nao achei` (`VOLATILE`) | o mapa é publicado uma única vez; no display `Map` do RViz2, `Durability Policy` tem de ser `Transient Local` |
| `/global_costmap/costmap com publicador: nao achei` | o `planner_server` não está ativo, ou o `global_costmap` do seu `nav2.yaml` aponta um frame que a sua TF não tem |
| `trafego em /cmd_vel_nav: olhe` sempre | é o esperado **sem goal ativo**. Essa linha nunca vira pendência: o script não tem como saber se há um goal em curso |
| `[XMLPARSER Error] getcwd failed No such file or directory` ao subir um nó | o diretório em que o terminal estava foi apagado e recriado — o bloco de download faz exatamente isso com `aula16-clinica` — e o shell ficou apontando para a pasta antiga. Não é defeito do nó nem da ferramenta: rode `cd "$PB_DIR/aula16-clinica"` de novo nesse terminal |
| a saída toda vira `olhe` | o `ros2` responde mas o formato da saída não é o que o script lê; rode o comando da coluna "Comando" da tabela à mão e compare |

## Como adequar ao seu projeto

As duas listas que importam estão no topo do `diagnosticar_nav2.py`, declaradas e comentadas: `ESPERADOS` (os onze nomes, na ordem de subida) e `CURA_NO` (uma linha de *o que fazer* por nó). Se o seu launch batiza os nós de outro jeito, ou se você tirou o `smoother_server` da lista do gerenciador, mexa nessas duas e o resto continua valendo. Se você usa namespace, troque a comparação por nome curto (`nome_curto`) pela comparação com o caminho completo — está numa função de três linhas, de propósito.

E se um comando novo passar a valer a pena olhar, o molde está pronto: uma função `secao_N_...`, uma chamada a `rodar`, e um `conferir(nome, estado, detalhe, ordem, cura)` por linha. O `testar.py` ganha o cenário correspondente antes da função, não depois: foi assim que os cenários apareceram, inclusive os dois que reproduzem as telas de 02/11.

Veja também: [aula 15 — Nav2](../aula15-nav2/index.md), [revisar a entrega do TP3](../tp3/revisar-entrega/index.md) e [os gates dos TPs](../../recursos/gates-tps.md).

## Licença

MIT, como todo o diretório `exemplos/`.
