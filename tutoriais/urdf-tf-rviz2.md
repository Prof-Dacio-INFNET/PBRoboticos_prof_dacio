---
titulo: "URDF, TF e RViz2 — do zero ao robô na tela"
tipo: tutorial
etapa: 5
alvo: "Ubuntu 22.04 (jammy) · ROS 2 Humble"
gate: "G2.5"
---

# URDF, TF e RViz2 — do zero ao robô na tela

**Leitura prévia da Aula 9.** Este tutorial existe para que a aula seja clínica e não primeira exposição: siga-o antes de 15/09 e chegue com o robô aparecendo no RViz2. Ele cobre o gate **G2.5** do TP2, que vence em 22/09.

## O problema que URDF e TF resolvem

Seu pipeline de visão já detecta um objeto e diz onde ele está — **em pixels**. Pixel é uma coordenada na imagem, e um robô não anda em pixels. Mais cedo ou mais tarde aparece a pergunta que trava todo projeto de percepção:

> *"Esse objeto que a câmera viu está a que distância da roda?"*

Para responder, o sistema precisa saber onde a câmera está montada em relação à base, onde a base está em relação ao chão, e como isso muda quando o robô se move. Esse conjunto de relações espaciais tem nome: **TF** (transform). E a descrição de onde cada peça está parafusada tem outro: **URDF**.

Uma frase para levar: **URDF é a descrição estática; TF é essa descrição viva, no tempo.** O URDF é um arquivo; a TF é um fluxo de mensagens que diz, a cada instante, onde tudo está.

!!! note "Por que isso vem antes do SLAM"
    No TP3 o seu robô vai mapear um ambiente. Um mapa é construído acumulando observações feitas de posições diferentes, e só dá para acumular se você souber **de onde** cada observação foi feita. Sem TF coerente, SLAM não é difícil: é impossível. Por isso o G2.5 vem antes.

## Passo 1 — Instalar o que falta

O `ros-humble-desktop` já traz o RViz2 e o `robot_state_publisher`. Faltam duas coisas:

```bash
sudo apt update
sudo apt install -y \
  ros-humble-joint-state-publisher-gui \
  ros-humble-xacro \
  ros-humble-tf2-tools \
  liburdfdom-tools
```

O que cada um faz, porque a lista não é óbvia:

| Pacote | Para quê |
|---|---|
| `joint-state-publisher-gui` | sliders para mover as juntas sem ter robô nenhum |
| `xacro` | macros para URDF, quando o arquivo cresce (Passo 8) |
| `tf2-tools` | `view_frames`, que desenha a árvore de TF em PDF |
| `liburdfdom-tools` | `check_urdf`, que valida o arquivo antes de você perder tempo |

Confira:

```bash
which check_urdf                       # /usr/bin/check_urdf
ros2 pkg list | grep joint_state_publisher_gui
```

!!! warning "Rota VirtualBox: a aceleração 3D precisa estar DESLIGADA"
    O RViz2 é o aplicativo mais exigente da disciplina em vídeo. Com aceleração 3D ligada no VMSVGA, ele costuma abrir preto ou fechar sozinho. Desligue em *Configurações → Tela*, com a VM **desligada**. No WSL2, se a janela não abrir, é WSLg: `wsl --update` e reabra o terminal.

## Passo 2 — Baixar o exemplo

```bash
# 1) baixar o material (pode repetir sempre — a linha do rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar para dentro do SEU projeto
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula09-urdf/meu_robo_description \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select meu_robo_description --symlink-install
source install/setup.bash
```

## Passo 3 — Validar o URDF antes de rodar qualquer coisa

Este passo economiza a tarde. O `check_urdf` lê o arquivo e imprime a árvore:

```bash
check_urdf ~/projeto-pb-SEU-USUARIO/ros2_ws/src/meu_robo_description/urdf/meu_robo.urdf
```

Esperado: `robot name is: meu_robo`, seguido da hierarquia começando em `base_footprint`. Se ele reclamar, **pare aqui** — um URDF inválido produz, mais adiante, sintomas que não parecem ter relação com o arquivo.

As três regras que o `check_urdf` verifica e que quebram na prática:

**Um link não pode ser filho de duas juntas.** URDF é uma **árvore**, não um grafo. Se a sua câmera está presa no mastro, o pai dela é o mastro — não a base também.

**Tem que existir exatamente uma raiz.** O link que não é filho de junta nenhuma. No exemplo é o `base_footprint` — um link **sem forma e sem massa**, na projeção do robô no chão. Ele existe por duas razões concretas, e a próxima seção é sobre isso.

**Junta `revolute` precisa de `<limit>`.** Sem limite, use `continuous` — que é o tipo certo para roda.

### Por que a raiz é um link vazio

Se você puser `<inertial>` no link raiz, o `robot_state_publisher` avisa assim que sobe:

```
[WARN] [kdl_parser]: The root link base_link has an inertia specified in the URDF,
but KDL does not support a root link with an inertia. As a workaround, you can add
an extra dummy link to your URDF.
```

**Não é bug e não quebra nada** — o robô aparece, a TF funciona. Mas o aviso está te dizendo uma coisa verdadeira: o KDL, a biblioteca de cinemática que o `robot_state_publisher` usa por baixo, não sabe o que fazer com massa na raiz da árvore.

A saída que o próprio aviso sugere é a que o exemplo usa, e ela é a **convenção da área**, não uma gambiarra:

```xml
<link name="base_footprint"/>          <!-- sem forma, sem massa -->

<joint name="junta_base" type="fixed">
  <parent link="base_footprint"/>
  <child  link="base_link"/>
  <origin xyz="0 0 0.09"/>             <!-- a altura do robo, explicita -->
</joint>
```

O `base_footprint` fica **no chão**, na projeção vertical do robô; o `base_link` fica **no corpo**. A distância entre os dois é a altura do robô, e escrevê-la aqui a deixa explícita em vez de escondida.

Isso importa além do aviso: **é o par que o Nav2 e o SLAM esperam encontrar** no TP3. Um robô que navega precisa saber onde ele toca o chão, não só onde fica o centro da carcaça.

## Passo 4 — Ver o robô

```bash
ros2 launch meu_robo_description ver_robo.launch.py
```

Sobem três nós, e **não confundir os papéis é metade do entendimento**:

| Nó | O que faz |
|---|---|
| `robot_state_publisher` | lê o URDF, escuta `/joint_states` e **publica a TF**. É ele que transforma descrição em geometria viva |
| `joint_state_publisher_gui` | **inventa** `/joint_states` com sliders. Existe só para você mexer nas juntas sem robô. Num robô real, quem publica isso são os encoders |
| `rviz2` | só **desenha**. Não calcula nada. Se algo não aparece, o problema quase nunca está nele |

Mexa no slider `junta_pan`. A esfera vermelha gira em torno da câmera — e a TF muda junto, ao vivo. **Esse é o momento em que a ficha cai:** o URDF não é um desenho, é um conjunto de relações que o sistema inteiro consulta.

## Passo 5 — Ler a TF por fora do RViz2

O RViz2 é bonito e é o pior lugar para depurar, porque ele esconde a diferença entre "não existe" e "não estou desenhando". Use as ferramentas de texto:

```bash
# a arvore inteira, em PDF (gera frames.pdf no diretorio atual)
ros2 run tf2_tools view_frames

# a transformacao entre dois frames, ao vivo
ros2 run tf2_ros tf2_echo base_link camera_link
```

O `tf2_echo` imprime translação e rotação a cada segundo. **É essa a resposta para "a que distância da roda"** — e repare que ela existe mesmo sem câmera nenhuma ligada, porque vem da descrição, não do sensor.

Mexa o slider e rode `tf2_echo base_link marcador_alvo`: os números mudam. A TF é uma função do tempo.

## Passo 6 — Configurar o RViz2 na mão (uma vez)

O exemplo já vem com um `.rviz` salvo, mas você precisa saber montar do zero — na hora que quebrar, será isso que vai fazer.

1. **Fixed Frame** (em *Global Options*): escolha `base_footprint`. Este é o campo que mais causa "não aparece nada": o RViz2 desenha tudo em relação a um frame, e se ele não existe, a tela fica vazia — sem erro visível.
2. *Add* → **RobotModel**. Em *Description Topic*, `/robot_description`.
3. *Add* → **TF**. Marque *Show Names*.
4. *File → Save Config As*, dentro do seu pacote, em `rviz/`.

!!! tip "Salve a configuração no pacote, não no home"
    Uma config do RViz2 que mora em `~/.rviz2/` não vai junto no `git push`, e o avaliador abre uma tela cinza. Salve em `rviz/` dentro do pacote e carregue com `-d` no launch, como o exemplo faz.

## Passo 7 — Quando não aparece nada

Quase todos os casos são um destes cinco, e a ordem de checagem importa:

| Sintoma | Causa provável | Como confirmar |
|---|---|---|
| tela cinza, nada desenhado | **Fixed Frame** aponta para um frame que não existe | o campo fica vermelho; troque para `base_footprint` |
| RobotModel vazio, sem erro | ninguém publicou `/robot_description` | `ros2 topic echo /robot_description --once` |
| `No transform from [x] to [base_link]` | o `robot_state_publisher` não subiu, ou o link não está na árvore | `ros2 run tf2_tools view_frames` |
| a TF existe mas o robô não se move | falta `/joint_states` | `ros2 topic echo /joint_states` — sem o GUI, ninguém publica |
| peças no lugar errado | `<origin>` do **joint** confundido com o do **visual** | é o erro nº 1; o do joint posiciona a peça, o do visual só deita a forma |
| ao sair, `joint_state_publisher_gui ... exit code -2` | **não é erro** — é ruído de encerramento | veja o aviso abaixo |

!!! note "`exit code -2` ao dar Ctrl+C não é falha"
    Ao encerrar o launch, você vai ver:

    ```
    [ERROR] [joint_state_publisher_gui-2]: process has died [pid 3890, exit code -2, ...]
    [INFO] [robot_state_publisher-1]: process has finished cleanly
    [INFO] [rviz2-3]: process has finished cleanly
    ```

    Código de saída **negativo** significa "terminado por sinal", e `-2` é o sinal 2, que é o próprio `SIGINT` do seu `Ctrl+C`. Ou seja: o processo **obedeceu**. O `joint_state_publisher_gui` é uma janela Qt e não instala um tratador de `SIGINT` que saia com código zero, então o launch classifica como `ERROR` o que na prática é encerramento normal.

    É a mesma família do `Exception ignored in: <function Future.__del__ …>` da Aula 3: **ruído de desligamento com cara de falha**. As linhas que importam são os dois `process has finished cleanly`.

!!! danger "O erro que consome uma tarde: `origin` do joint × `origin` do visual"
    Um `<origin>` dentro de `<visual>` move **só o desenho**. Um `<origin>` dentro de `<joint>` move **a peça e tudo que pende dela**, e é ele que entra na TF.

    O sintoma de trocar os dois é cruel: no RViz2 fica *parecendo* certo, e a TF fica errada. O seu objeto detectado passa a estar a 20 cm do lugar onde realmente está, e você vai procurar o erro na visão computacional.

## Passo 8 — Quando o URDF cresce: xacro

URDF puro fica repetitivo depressa — duas rodas iguais já são dois blocos idênticos. O `xacro` resolve com macros e variáveis:

```xml
<xacro:property name="raio_roda" value="0.05"/>

<xacro:macro name="roda" params="lado reflexo">
  <link name="roda_${lado}">
    <visual>
      <origin rpy="1.5708 0 0"/>
      <geometry><cylinder radius="${raio_roda}" length="0.03"/></geometry>
    </visual>
  </link>
  <joint name="junta_roda_${lado}" type="continuous">
    <parent link="base_link"/>
    <child link="roda_${lado}"/>
    <origin xyz="0 ${reflexo * 0.115} -0.04"/>
    <axis xyz="0 1 0"/>
  </joint>
</xacro:macro>

<xacro:roda lado="esquerda" reflexo="1"/>
<xacro:roda lado="direita"  reflexo="-1"/>
```

Para ver o URDF que sai do xacro:

```bash
xacro meu_robo.urdf.xacro > /tmp/gerado.urdf && check_urdf /tmp/gerado.urdf
```

**Não comece por xacro.** Faça o URDF puro funcionar, e migre quando a repetição incomodar — que é o critério certo para quase toda abstração.

## O que o G2.5 pede, exatamente

> *Parametrização em YAML + URDF carregando no RViz2 com TF coerente.*

Traduzido em comandos, é isto:

```bash
ros2 param dump /<seu_no>                     # a metade YAML
ros2 launch <seu_pacote> ver_robo.launch.py   # a metade URDF
ros2 run tf2_tools view_frames                # a prova de que a TF esta coerente
```

E "TF coerente" tem um teste objetivo: `view_frames` produz **uma árvore só**, sem frames órfãos, com `base_footprint` na raiz e `base_link` logo abaixo. Duas árvores separadas significam que falta uma junta ligando as partes — e é o achado mais comum na correção.

**Evidência para commitar** em `docs/evidencias/tp2/`: o `frames.pdf` do `view_frames`, um print do RViz2 com o modelo e a TF visíveis, e o `ros2 param dump` do seu nó parametrizado.

## Adapte para o seu projeto

O robô do exemplo tem base, duas rodas, mastro e câmera — a forma mínima de quase todo projeto do catálogo. O que muda no seu:

**Meça de verdade.** Se o seu projeto é simulado, invente medidas plausíveis e **anote que são inventadas**. Se tem hardware, meça com régua. Um URDF com números chutados produz TF errada, e TF errada não dá erro: dá resultado errado.

**Nomeie o sensor pelo que ele é.** `camera_link` para câmera, `laser_link` para LiDAR. Convenção de nome não é estética: é o que faz outras ferramentas encontrarem o seu sensor sem configuração.

**Uma junta fixa por peça aparafusada.** Parece burocrático até o dia em que você move a câmera dois centímetros e precisa que o sistema inteiro saiba disso mudando um número num arquivo.
