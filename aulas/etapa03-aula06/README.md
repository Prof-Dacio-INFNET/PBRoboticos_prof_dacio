# Aula 6 — Interfaces próprias e detecção inteligente

**Terça, 25/08/2026 · sala SJ205 · Etapa 3 (17/08–29/08)**

[:material-file-pdf-box: Slides da Aula 6 (PDF)](apresentacao-aula06.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula06-interfaces`](../../exemplos/aula06-interfaces/index.md){ .md-button }
[:material-clipboard-check: Tarefa da semana](../../tutoriais/tarefa-aula06-interfaces.md){ .md-button }
[:material-package-variant-closed: Checklist de entrega do TP1](../../tutoriais/checklist-entrega-tp1.md){ .md-button }

!!! danger "O TP1 vence nesta sexta, 28/08"
    Esta é a **última aula antes da entrega**. A primeira hora de hoje é clínica: fechar os gates que faltam, rodar o experimento de oclusão, escrever o relatório e **ensaiar a entrega inteira**. O conteúdo novo vem depois — e ele é do TP2, não do TP1. Se você tiver que escolher onde prestar atenção hoje, escolha a primeira hora.

## A ideia da aula em uma frase

**Hoje o seu projeto para de falar a língua de outra pessoa.** Até agora tudo viajou em mensagens prontas — `Int32`, `String`, `Image`, `Trigger` —, e isso foi certo: começar inventando tipo é uma forma cara de não entregar nada. Mas mensagem pronta tem um limite exato, e ele aparece quando você precisa dizer algo que o tipo não comporta. Um `Int32` valendo `3` não diz três de quê, com que certeza, nem onde.

Ao fim da aula você terá um pacote de interfaces seu, com uma mensagem e um serviço que descrevem o **seu** domínio, e o pipeline da Aula 3 publicando neles.

## Objetivos

Ao final da aula você deve conseguir explicar quando vale a pena criar uma interface própria e quando isso é só cerimônia; criar um pacote `ament_cmake` de interfaces e justificar por que ele **não** pode ser o mesmo pacote Python dos seus nós; escrever um `.msg` com tipos, arrays e `Header`, e um `.srv` com requisição e resposta; compilar, inspecionar com `ros2 interface show` e consumir a interface a partir de um nó Python; e reconhecer o que a segmentação por cor **não** consegue prometer — que é o assunto da Etapa 4.

---

## Parte 0 — Clínica: aterrissar o TP1 (primeira hora)

O calendário de gates diz que **G1.4 venceu ontem** e **G1.5 vence amanhã**. Isso não é motivo para pânico e é motivo para ordem. Comece medindo onde você está, com um comando só:

```bash
cd ~/SEU-REPO
bash recursos/check-ambiente.sh                       # G1.0
grep -c "PB:PROJETO\|PB:TRILHA" PROJETO.md            # G1.1 -- espera-se 2
ros2 topic hz /vision/contagem                        # G1.2 e G1.3, regua leve
ros2 service call /vision/status std_srvs/srv/Trigger "{}"   # G1.4
ls docs/evidencias/tp1/                               # a prova de tudo isso
```

Marque no `PROJETO.md` com a régua dos três estados: `[x]` passou com evidência commitada, `[ ]` ainda não venceu, `[!]` venceu sem passar. **Um `[!]` declarado hoje custa menos do que um `[!]` descoberto na sexta.**

### O experimento da oclusão, se você ainda não fez

Ele vale mais do que parece, porque é o único item do TP1 que produz uma **observação** em vez de um funcionamento. Passe um objeto na frente do outro e registre o que acontece com a contagem:

```bash
ros2 topic echo /vision/contagem
```

O que se espera ver é a contagem cair de 2 para 1 e voltar. O que se espera **escrever** no relatório é a interpretação: em que ponto o detector deixou de separar os dois objetos, por que a área combinada não é a soma das áreas, e o que isso significa para o seu domínio — se dois tomates encostados viram um, a sua contagem de colheita erra para menos, e isso é uma limitação conhecida, não um bug escondido.

### O relatório é um documento de decisões, não um diário

Quem trava no `relatorio-tp1.md` quase sempre travou porque tentou narrar o semestre. Não é isso. São cinco perguntas:

| Seção | A pergunta que ela responde |
|---|---|
| Domínio e derivação | que problema, de quem, e por que este e não outro |
| Decisões técnicas | o que você escolheu e **o que descartou** — trilha, faixa HSV, `area_min`, QoS |
| Experimento de oclusão | o que aconteceu, e o que isso implica no seu domínio |
| Limitações conhecidas | o que o sistema **não** faz, dito por você antes de ser dito por outro |
| Uso de IA | o que foi gerado, o que foi revisado, o que você sabe explicar |

A seção de limitações é a que mais rende nota e a que mais gente pula. Declarar "a segmentação por cor confunde tomate maduro com um pano vermelho ao fundo" demonstra que você entendeu o seu sistema. Omitir isso e deixar o avaliador descobrir demonstra o contrário.

### Ensaie a entrega hoje, não na sexta

O passo a passo completo está no [checklist de entrega do TP1](../../tutoriais/checklist-entrega-tp1.md). O resumo é: `main` atualizado, branch `entrega-tp1` criado, tag `tp1` empurrada, ZIP e PDF no Moodle, links testados em **janela anônima**. A regra é dura de propósito: **se o avaliador não consegue abrir, não existe.**

---

## Parte 1 — Quando a mensagem pronta acaba

Olhe o que o seu TP1 publica hoje:

```bash
ros2 topic echo /vision/contagem --once
# data: 3
```

Três. Três o quê? Com que confiança? Onde na imagem? De que instante? A informação existe dentro do seu nó — o `detectar()` conhece a área, a posição e o contorno de cada objeto — e é **jogada fora** na hora de publicar, porque o tipo escolhido não tem onde guardá-la.

Esse é o sintoma. O tipo pronto serviu enquanto a pergunta era "quantos?". Ele deixa de servir quando a pergunta vira "quantos, de que classe, com que certeza, e onde?".

!!! tip "A regra prática, para não cair no extremo oposto"
    Interface própria custa: um pacote a mais, um `colcon build` a mais, e uma dependência que todo colaborador precisa compilar antes de rodar o seu nó. Vale a pena quando **três ou mais campos** andam sempre juntos, ou quando você se pega publicando dois tópicos que só fazem sentido lidos ao mesmo tempo. Não vale a pena para um número solto — `Int32` continua sendo a resposta certa para "quantos".

    O erro comum de quem acabou de aprender isso é criar uma mensagem para cada coisa. O erro oposto é empacotar tudo em `String` e mandar JSON dentro. Os dois cobram depois.

## Parte 2 — Por que o pacote de interfaces é separado

Esta é a parte que trava mais gente, e ela é estrutural, não uma chatice do ROS.

Geração de interface é **geração de código**: o ROS 2 lê o seu `.msg` e produz código C++, Python e headers, para que a mesma mensagem seja usável em qualquer linguagem. Quem faz isso é o `rosidl`, que roda dentro de um pacote `ament_cmake`. Um pacote `ament_python` — que é o tipo dos seus nós desde a Aula 2 — **não tem** essa maquinaria.

Daí a arquitetura padrão, e ela é sempre a mesma:

```
ros2_ws/src/
├── pb_interfaces/          <- ament_cmake, SÓ mensagens e serviços, sem código de nó
│   ├── msg/Deteccao.msg
│   ├── msg/Deteccoes.msg
│   ├── srv/StatusVisao.srv
│   ├── CMakeLists.txt
│   └── package.xml
└── aula06_percepcao/       <- ament_python, os seus nós, dependendo do de cima
    ├── aula06_percepcao/detector.py
    ├── setup.py
    └── package.xml
```

!!! warning "O erro que você vai cometer se ninguém avisar"
    Tentar declarar `rosidl_generate_interfaces` num pacote `ament_python`, ou colocar `msg/` dentro do pacote dos nós. Não funciona, e a mensagem de erro não explica por quê — ela reclama de CMake num lugar onde você nem sabia que havia CMake.

    Separar não é burocracia: é o que permite que outra pessoa dependa das suas mensagens **sem** ter que compilar os seus nós. Repare que é exatamente assim que o `sensor_msgs` chega até você.

Três linhas do `package.xml` são as que fazem o pacote virar um pacote de interfaces. Sem elas, ele compila e não gera nada:

```xml
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

## Parte 3 — Anatomia de um `.msg` e de um `.srv`

Um `.msg` é uma lista de campos: tipo, nome, e um comentário que o seu eu de outubro vai agradecer.

```
# Deteccao.msg -- uma deteccao individual
string  classe        # rotulo do SEU dominio
float32 confianca     # 0.0 a 1.0
int32   x             # centro, em pixels
int32   y
int32   area
```

Mensagens compõem. Um campo pode ser outra mensagem sua, e `[]` faz array de tamanho variável:

```
# Deteccoes.msg -- o que a percepcao viu em UM quadro
std_msgs/Header header
Deteccao[]       deteccoes
uint32           total
```

O `Header` merece atenção porque é o campo que a turma sempre acha decorativo. Ele carrega `stamp` (quando) e `frame_id` (em que referencial). Sem `stamp`, você não consegue dizer se a detecção é de agora ou de três segundos atrás — e essa distinção é a diferença entre um robô que reage e um que alucina. Sem `frame_id`, você não consegue combinar esta informação com a de outro sensor, que é literalmente o assunto da Etapa 4.

O `.srv` é a mesma ideia com uma linha de `---` separando pergunta de resposta:

```
# StatusVisao.srv -- requisicao vazia: a pergunta e sempre a mesma
---
bool    ativo
string  classe_alvo
uint32  total_detectado
float32 confianca_media
string  mensagem
```

Compare com o `std_srvs/srv/Trigger` que o TP1 usa. O `Trigger` responde `success` e `message`: ele diz *estou vivo*. O `StatusVisao` diz *o que eu estou vendo*. É o mesmo serviço, no mesmo lugar do grafo, com um vocabulário que pertence ao seu projeto.

!!! note "Onde o serviço deixa de servir"
    Serviço é pergunta-e-resposta: quem chama fica bloqueado esperando. Isso é adequado para "qual o seu status?" e péssimo para "vá até a bancada e me avise quando chegar". Para tarefas longas, com progresso e possibilidade de cancelamento, existe a **action** — e ela é o coração do TP2. Hoje só marque o limite: se a resposta demora mais que uma fração de segundo, serviço é a escolha errada.

## Parte 4 — Compilar, inspecionar, consumir

A ordem importa: o pacote de interfaces precisa estar compilado **antes** de qualquer nó que o importe.

```bash
cd ~/SEU-REPO/ros2_ws
colcon build --packages-select pb_interfaces
source install/setup.bash                       # sem isto, o import falha
colcon build --packages-select aula06_percepcao --symlink-install
source install/setup.bash
```

Confira que o ROS 2 enxerga o que você criou — este comando é o teste de fumaça da aula:

```bash
ros2 interface show pb_interfaces/msg/Deteccoes
ros2 interface list | grep pb_interfaces
```

E rode:

```bash
ros2 launch aula06_percepcao percepcao.launch.py classe:=tomate_maduro
```

Noutro terminal:

```bash
ros2 topic echo /vision/deteccoes --once
ros2 service call /vision/status pb_interfaces/srv/StatusVisao "{}"
```

!!! warning "`source` depois de todo build de interface"
    Mudou um `.msg`? Recompile o pacote de interfaces **e** dê `source` de novo, em **todos** os terminais abertos. Um terminal antigo continua enxergando a versão velha da mensagem, e o sintoma é um erro de tipo que não faz sentido nenhum — o campo que você acabou de adicionar simplesmente não existe. Quando algo assim aparecer, o primeiro reflexo é abrir um terminal novo.

## Parte 5 — Detecção inteligente: onde a cor deixa de bastar

Repare no campo `confianca` da mensagem. O exemplo o preenche com a **solidez** do contorno — a razão entre a área do objeto e a área do seu fecho convexo. Isso não é uma probabilidade; é um substituto honesto, e o código diz isso em voz alta no comentário.

Rode o exemplo e observe: quando os dois objetos se aproximam e se encostam, a contagem cai de 2 para 1 **e a confiança cai junto**, porque a mancha resultante deixa de ser convexa. O detector tem um sinal interno de que algo saiu do esperado — e é exatamente esse sinal que um detector treinado produz de forma direta, calibrada e comparável.

É essa a fronteira entre a Etapa 3 e a Etapa 4. Segmentar por cor responde "onde há vermelho". Detectar responde "onde há um tomate, e o quanto eu acredito nisso". A primeira pergunta se resolve com quatro números de HSV; a segunda exige dados, rótulos e um modelo. O que **não** muda é a interface: `Deteccao` com classe, confiança e posição serve para os dois. Trocar o miolo sem trocar o contrato é o motivo pelo qual esta aula vem antes daquela.

## Tarefa da semana

[Tarefa da Aula 6 — as interfaces do seu projeto](../../tutoriais/tarefa-aula06-interfaces.md): criar o seu `<projeto>_interfaces`, migrar o `/vision/status` do `Trigger` para um serviço próprio, e publicar detecções com classe e confiança.

**Ela é opcional até sexta.** Antes de sexta existe uma coisa só: entregar o TP1.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `ModuleNotFoundError: No module named 'pb_interfaces'` | faltou compilar o pacote de interfaces, ou faltou `source install/setup.bash` depois de compilar |
| erro de CMake num pacote onde você não escreveu CMake | você tentou gerar interface num pacote `ament_python`. Interfaces vivem em pacote `ament_cmake` separado (Parte 2) |
| o pacote compila mas `ros2 interface list` não mostra nada | faltam as três linhas do `package.xml` (`rosidl_default_generators`, `rosidl_default_runtime`, `member_of_group`) |
| `Header` não resolve na compilação | faltou `<depend>std_msgs</depend>` no `package.xml` **e** `DEPENDENCIES std_msgs` no `rosidl_generate_interfaces` |
| campo novo "não existe" num terminal e existe noutro | terminal antigo com `source` velho. Abra um terminal novo — é sempre isto |
| `ros2 service call` reclama do tipo | o tipo agora é `pb_interfaces/srv/StatusVisao`, não `std_srvs/srv/Trigger`. Confira com `ros2 service type /vision/status` |
| a contagem cai quando os objetos se encostam | é o comportamento esperado, e é o experimento de oclusão. Registre no relatório em vez de "consertar" |
| `ros2 topic hz` com `min:` negativo | relógio do WSL2 saltando — [diagnóstico e cura](../../tutoriais/setup-ros2-humble-wsl2.md#o-relogio-do-wsl2-pode-saltar-e-isso-estraga-qualquer-medicao) |
| `No module named 'PyQt5'` ao abrir rqt | venv ativado; `deactivate` resolve |

## Para a próxima aula (01/09)

Começa a **Etapa 4 — SLAM e percepção veicular**, e com ela o TP2 entra no radar. Chegue com o TP1 entregue e com o seu pacote de interfaces compilando: a Etapa 4 assume que o seu projeto já tem vocabulário próprio.
