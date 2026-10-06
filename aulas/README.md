# Aulas

Encontros de **terça-feira, sala SJ205**. Cada aula tem uma página com o conteúdo trabalhado, o PDF da apresentação, os exemplos usados em sala e a tarefa da semana.

O bloco tem dez etapas de conteúdo distribuídas em dois trimestres (26T3, de 20/07 a 03/10, e 26T4, de 05/10 a 19/12). Cada etapa cobre duas semanas, e as aulas dentro de uma etapa são sequenciais: a segunda assume que a primeira aconteceu.

| Aula | Data | Etapa | Tema | |
|---|---|---|---|---|
| [Aula 1](etapa01-aula01/index.md) | 21/07/2026 | 1 | Abertura, ROS 2 e o projeto do semestre | <span class="pb-tag ok">dada</span> |
| [Aula 2](etapa01-aula02/index.md) | 28/07/2026 | 1 | Primeiros nós: tópicos e serviços | <span class="pb-tag ok">dada</span> |
| [Aula 3](etapa02-aula03/index.md) | 04/08/2026 | 2 | Comunicação e visão computacional | <span class="pb-tag ok">dada</span> |
| [Aula 4](etapa02-aula03/index.md) | 11/08/2026 | 2 | Pipeline de visão: continuação e mentoria de projeto | <span class="pb-tag ok">dada</span> |
| [Aula 5](etapa02-aula03/index.md) | 18/08/2026 | 2 | Fechamento do pipeline de visão e leitura do TP1 | <span class="pb-tag ok">dada</span> |
| [Aula 6](etapa03-aula06/index.md) | 25/08/2026 | 3 | Interfaces próprias e detecção inteligente | <span class="pb-tag ok">dada</span> |
| [Aula 7](etapa04-aula07/index.md) | 01/09/2026 | 4 | Abertura com webcam; ações apresentadas | <span class="pb-tag ok">dada</span> |
| [Aula 8](etapa04-aula08/index.md) | 08/09/2026 | 4 | Ações a fundo: o ciclo de vida de um objetivo | <span class="pb-tag ok">dada</span> |
| [Aula 9](etapa05-aula09/index.md) | 15/09/2026 | 5 | Detecção treinada e métrica declarada | <span class="pb-tag ok">dada</span> |
| [Aula 10](etapa05-aula10/index.md) | 22/09/2026 | 5 | Aterrissagem do TP2: clínica de URDF e bringup | <span class="pb-tag ok">dada</span> |
| [Aula 11](etapa06-aula11/index.md) | 29/09/2026 | 6 | O mundo, a deriva e o mapa que corrige | <span class="pb-tag ok">dada</span> |
| [Aula 12](etapa06-aula12/index.md) | 06/10/2026 | 6 | O SLAM paga a conta da deriva | <span class="pb-tag next">próxima</span> |
| Aula 13 | 13/10/2026 | 7 | Percepção: segmentação e módulo veicular | <span class="pb-tag soon">a seguir</span> |

!!! note "Por que as Aulas 4 e 5 apontam para a página da Aula 3"
    O material da Aula 3 é denso e foi trabalhado ao longo de três encontros — 04, 11 e 18/08 —, com a leitura oficial do TP1 no último deles. As datas do calendário não mudaram; o que mudou foi o ritmo, e isso é normal num bloco prático. As três aulas compartilham a mesma página porque compartilham o mesmo conteúdo.

    Consequência prática: a **Etapa 3 tem um encontro só**, o de 25/08. Por isso a Aula 6 cobre interfaces próprias em profundidade e apenas *aponta* para detecção inteligente, que volta com calma na Etapa 4.

## As etapas do semestre

| Etapa | Período | Conteúdo |
|---|---|---|
| 1 | 20/07–01/08 | Fundamentos de sistemas robóticos |
| 2 | 03/08–15/08 | **Comunicação e visão computacional** |
| 3 | 17/08–29/08 | Interfaces ROS 2 e detecção inteligente |
| 4 | 31/08–12/09 | SLAM e percepção veicular |
| 5 | 14/09–26/09 | Navegação autônoma e deep learning |
| 6 | 28/09–10/10 | Integração robótica e IA autônoma |
| 7 | 12/10–24/10 | Sistemas robóticos inteligentes |
| 8 | 26/10–07/11 | Manipulação e navegação avançada |
| 9 | 09/11–21/11 | Integração final de sistemas autônomos |
| 10 | 23/11–05/12 | Finalização do projeto e entrega |
| — | 07/12–19/12 | Apresentações e fechamento |

## Mapa de cobertura — o que cada aula entrega

Esta tabela existe para uma pergunta específica: **a redistribuição das aulas deixou algum conteúdo de fora?** A resposta é não, e é aqui que dá para conferir. Cada gate dos TPs é um requisito verificável; a coluna da direita diz em que encontro ele é ensinado, e a regra que precisa valer é simples — **todo gate é ensinado antes da data em que vence**.

| Gate | O que exige | Ensinado em | Vence em | Folga |
|---|---|---|---|---|
| G1.0 | ambiente operante | Aula 1 · 21/07 | 07/08 | 17 dias |
| G1.1 | projeto declarado | Aula 1 · 21/07 (catálogo) e Aula 5 · 18/08 (leitura do TP1) | 11/08 | — |
| G1.2 | grafo de imagem no ar | Aula 3 · 04/08 | 15/08 | 11 dias |
| G1.3 | segmentação detectando o objeto | Aula 3 · 04/08 | 20/08 | 16 dias |
| G1.4 | serviço + `rqt_graph` | Aula 2 · 28/07 (serviços) e Aula 3 · 04/08 | 24/08 | 20 dias |
| G1.5 | relatório fechado | Aula 6 · 25/08 (clínica) | 26/08 | 1 dia |
| G2.0 | pacote de interfaces compilando | Aula 6 · 25/08 | 04/09 | 10 dias |
| G2.1 | `.msg`/`.srv` do domínio | Aula 6 · 25/08 | 08/09 | 14 dias |
| G2.2 | action com servidor respondendo | [Aula 8](etapa04-aula08/index.md) · 08/09 | 12/09 | 4 dias |
| G2.3 | action com feedback e cancelamento | [Aula 8](etapa04-aula08/index.md) · 08/09 | 16/09 | 8 dias |
| G2.4 | detecção evoluída com métrica declarada | [Aula 9](etapa05-aula09/index.md) · 15/09 (régua) + [Aula 10](etapa05-aula10/index.md) · 22/09 (contrato) | 19/09 | 4 dias / **−3** |
| G2.5 | YAML + URDF no RViz2 com TF coerente | [tutorial](../tutoriais/urdf-tf-rviz2.md) publicado 08/09 + clínica na [Aula 10](etapa05-aula10/index.md) · 22/09 | 22/09 | **0 dias** |
| G2.6 | entrega: branch, tag, relatório, Moodle | [Aula 10](etapa05-aula10/index.md) · 22/09 | 25/09 | 3 dias |
| G3.0 | `bringup.launch.py` sobe o sistema inteiro | [Aula 11](etapa06-aula11/index.md) · 29/09 | 30/09 | **1 dia** |
| G3.1 | mundo de simulação com robô e câmera | [Aula 11](etapa06-aula11/index.md) · 29/09 | 06/10 | 7 dias |
| G3.2 | árvore `map → odom → base_link → sensores` | [Aula 11](etapa06-aula11/index.md) · 29/09 | 10/10 | 11 dias |
| G3.3 | SLAM Toolbox com mapa persistido | [Aula 12](etapa06-aula12/index.md) · 06/10 | 15/10 | 9 dias |
| G3.4 | segmentação por instância | Aula 13 · 13/10 | 18/10 | 5 dias |
| G3.5 | percepção veicular documentada | Aula 13 · 13/10 | 20/10 | 7 dias |

### O que a redistribuição custou, dito com todas as letras

O material da Etapa 2 ocupou três encontros em vez de dois, e o encontro extra saiu da **Etapa 3**, que tinha duas datas na janela 17/08–29/08 e ficou com uma. Nada foi cortado, mas quatro requisitos do TP2 mudaram de lugar:

**Ações** (G2.2 e G2.3) eram da Etapa 3 e passam para a Aula 7. O deslocamento é confortável porque ação é pré-requisito de navegação — o Nav2 é construído sobre ações —, então ela entra na Etapa 4 como fundamento e não como enxerto.

**Detecção treinada com métrica** (G2.4) era o "detecção inteligente" da Etapa 3 e passa para a Aula 8, dentro de percepção veicular. É o mesmo assunto com mais contexto: detectar veículo, pedestre ou placa é o caso de uso que justifica sair da segmentação por cor.

**Parametrização e URDF** (G2.5) passa para a Aula 9, junto de SLAM e TF — que é onde URDF e RViz2 seriam necessários de qualquer forma. Aqui a redistribuição melhora a sequência em vez de piorar: ensinar URDF isolado é abstrato; ensinar URDF porque o SLAM precisa de TF coerente é concreto.

### Segunda correção: a Aula 7 abriu ações, a Aula 8 as entrega

A Aula 7 (01/09) foi ocupada pelas demonstrações com a webcam e pelos cartões, e ações ficaram **apresentadas, não trabalhadas**. A Aula 8 (08/09) passa a ser a entrega completa — ciclo de vida do objetivo, os três verbos de término, e o cancelamento demonstrado —, o que fecha G2.2 e G2.3 com quatro e oito dias de folga.

O efeito colateral é que a **Aula 9 (15/09) carrega dois gates**: G2.4 (detecção treinada com métrica) e G2.5 (YAML, URDF e TF no RViz2). Todos continuam sendo ensinados antes de vencer, mas a folga do G2.4 caiu para quatro dias e a aula ficou densa.

**A mitigação foi aplicada: o URDF saiu da aula e virou leitura prévia.** O tutorial [URDF, TF e RViz2](../tutoriais/urdf-tf-rviz2.md) foi publicado em 08/09, cobrindo desde a instalação até a árvore de TF validada, o que devolve ao G2.5 uma folga de catorze dias e deixa a Aula 9 como clínica. Parametrização em YAML a turma já pratica desde a Aula 3 (`ros2 param set`, `config/*.yaml`); o que era realmente novo no G2.5 é URDF e TF, e isso é mecânico o bastante para caber num tutorial.

**As folgas de quatro dias — G2.2 e G2.4 — são o novo ponto a vigiar.** Quatro dias é o suficiente para quem sai da aula com o exemplo rodando, e insuficiente para quem sai com o exemplo quebrado. É por isso que as duas aulas têm bloco de mão na massa com todo mundo executando, e não só demonstração no projetor.

### Terceira correção: a Aula 9 parou na Parte 4

A Aula 9 (15/09) trabalhou as Partes 1 a 4 — por que a cor acaba, a métrica como decisão declarada, o banco de provas na mão de todos, e a leitura dos três resultados. As Partes 5 e 6 não foram trabalhadas.

**O que a Parte 5 carregava** era o contrato do detector: o `avaliar.py` chama uma função que recebe imagem e devolve `(x, y, w, h)` ou `None`, e trocar de detector é escrever outra função com essa assinatura. Junto ia a regra prática do gate — `cv2.dnn` roda ONNX sem `torch`, e **o que se avalia é a métrica e a justificativa, não o modelo**.

A metade do G2.4 que a correção efetivamente verifica — a métrica declarada, com os números e o lugar onde cada versão falha — **foi inteiramente ensinada**. O que ficou de fora foi o caminho barato para a palavra *evoluída*, e a ausência dele tem um custo de direção, não de capacidade: sem essa orientação, a rota mais provável a três dias da entrega é instalar `torch` às pressas e quebrar o ambiente. A Parte 5 é recuperada na Aula 10, e a página da Aula 9 continua publicada com ela desde 15/09.

**O que a Parte 6 carregava** era a clínica de URDF e TF inteira — que já era, ela própria, a mitigação aplicada quando a Aula 9 ficou densa. A clínica passa para a Aula 10, e o G2.5 fica com folga **zero**: é ensinado no mesmo dia em que vence. Isso ainda satisfaz a regra da tabela, mas sem nenhuma margem, e só funciona porque a evidência do gate é produzida dentro da própria clínica.

**O custo maior não é o TP2, é o TP3.** O G3.2 — árvore de TF completa e sem warning — é o gate de verdade daquele TP, e noventa por cento dos problemas de SLAM e de Nav2 são problemas de TF disfarçados. Uma turma que nunca passou pela bancada de URDF não arrisca só o G2.5: ela entra no TP3 com a fundação por testar.

### O padrão por trás das três correções

Nas Aulas 7 e 9, o bloco perdido foi o **último**. Duas vezes em três encontros, e nas duas o bloco final era a prática supervisionada — que é justamente o que não se recupera em casa.

Isso deixou de ser azar e virou característica do desenho: pôr a clínica no fim faz dela a absorvedora de todo o atraso acumulado. A correção aplicada na Aula 10 é estrutural, não de conteúdo — **a aula está ordenada por custo de perda**, com a clínica primeiro e o bloco de folga por último, declarado de antemão como o que cede se o tempo apertar.

O bloco que cede é o de launch, porque o G3.0 vence em 30/09 e a Aula 11 (29/09) ainda o alcança. É a mesma disciplina que a Aula 9 ensina sobre medição, aplicada ao tempo: a régua vem antes da medida, e o corte vem antes do aperto.

### Navegação autônoma passa para a Aula 11

A Aula 10 era "navegação autônoma + aterrissagem do TP2". Navegação sai e vai para a Aula 11 (29/09), na Etapa 6.

A troca é barata porque **nenhum gate de navegação vence antes de 30/10** — o primeiro é o G4.0, do TP4. Navegação era o único conteúdo da Aula 10 sem prazo pressionando, e por isso foi o escolhido para ceder o lugar à clínica e à aterrissagem.

O destino também não é arbitrário: a Etapa 6 é "integração robótica e IA autônoma", e o Nav2 é integração — ele se monta sobre ações (Aula 8) e TF coerente (G2.5), que é exatamente o que a Aula 10 fecha. A sequência melhora em vez de piorar.

Em troca, a Aula 10 recebe o bloco de **launch**, que não estava previsto nela. Isso resolve um problema que a tabela acima já mostrava: o G3.0 vence em 30/09 e a Aula 11 é em 29/09 — um dia de folga, o mesmo aperto do G1.5. Ensinando launch em 22/09, a folga do G3.0 vai de um dia para oito.

### Quarta correção: a Aula 10 parou no slide 20, e o corte declarado funcionou

A Aula 10 trabalhou até o slide 20 — clínica de URDF completa, aterrissagem do TP2 completa, e o contrato do detector até a frase "o contrato fica, o miolo troca". O que ficou de fora foi o **bloco de launch** (Parte 4) e as duas últimas telas da Parte 3.

**Isto é diferente das três correções anteriores, e a diferença importa.** Nas Aulas 7 e 9 o bloco perdido foi uma surpresa. Aqui ele foi escolhido antes: a aula estava ordenada por custo de perda, launch era o bloco de folga, e a turma foi avisada disso no primeiro minuto. O plano previu a perda e escolheu onde ela cairia — então o que se perdeu foi o mais barato, e não o mais próximo do fim.

A consequência é que **o G3.0 passa a ser ensinado com um dia de folga** — 29/09 para vencer em 30/09. É apertado, e era o preço combinado. Launch abre a Aula 11.

**O que se perdeu junto, e não estava no combinado**, foram os slides 21 e 22: a regra prática do gate (`cv2.dnn` roda ONNX sem `torch`) e o fecho "o que se avalia é a métrica e a justificativa, não o modelo". Como o TP2 entregou em 25/09, isso deixou de valer para o G2.4 — mas volta a valer para o G3.4, o G3.5 e o G4.6, e precisa ser dito antes do primeiro deles, em 18/10.

### A Aula 11 recebe três gates, e por isso o mundo entra leve

Com launch recuperado, a Aula 11 carrega **G3.0** (30/09), **G3.1** (06/10) e **G3.2** (10/10). O G3.1 é o que pesa: ele pede cenário de simulação, e o caminho óbvio é o Gazebo — que é justamente a peça mais frágil na pilha gráfica desta turma, como a clínica de URDF já mostrou.

A decisão foi tratar o mundo como **produtor de dados, e não como janela**. O que o sistema consome é `/scan`, `/odom` e uma árvore de TF; o exemplo [`aula11-mundo`](../exemplos/aula11-mundo/index.md) produz os três com ray-casting em numpy, sem física, sem render e sem janela. O Gazebo entra como upgrade — mesmo contrato, produtor mais pesado —, e quem trocar mantém launch, frames, SLAM e Nav2 intactos.

É a terceira vez que o mesmo movimento resolve um aperto de calendário: o G2.5 sem depender do RViz2, o detector atrás de uma assinatura, e agora o simulador atrás de dois tópicos. **O contrato fica, o miolo troca** deixou de ser tema de uma aula e virou o método do bloco.

### Navegação autônoma desce mais um degrau, e continua sem custo

Prevista para a Aula 11, a navegação vira o bloco de folga desta vez — introduzida como "o que o Nav2 acrescenta ao piloto reativo", e trabalhada de fato quando o mapa existir.

O custo continua sendo zero: **nenhum gate de navegação vence antes de 30/10** (G4.0, do TP4). E a sequência melhora de novo, porque Nav2 sobre mapa inexistente é exposição, não prática: o SLAM do G3.3 entrega o mapa em 15/10, e é depois dele que navegar quer dizer alguma coisa.

### Quinta correção: o bloco de folga cedeu de novo, e de novo era o planejado

A Aula 11 trabalhou os três primeiros blocos — launch, o mundo como produtor de dados, e a deriva. O bloco sobre navegação era o de folga declarado na abertura, e foi ele que cedeu.

**É a segunda vez seguida que o corte sai como anunciado**, e isso deixou de ser sorte: a aula ordenada por custo de perda entrega os blocos caros antes de o tempo apertar, e o que sobra é sempre o mesmo — o de maior folga. O custo acumulado é zero, porque nenhum gate de navegação vence antes de 30/10.

A navegação entra na Aula 12 no último bloco, e **cai melhor ali do que teria caído antes**: com mapa construído em aula, duas das quatro linhas da tabela "o que o Nav2 acrescenta" deixam de ser abstratas.

### A Aula 12 abre com bancada de TF, e isso não é revisão

O G3.2 vence em 10/10, três dias depois da aula, e o G3.3 é construído literalmente em cima dele. O `slam_toolbox` lê a árvore de transformadas para saber onde o laser estava quando mediu: com a árvore quebrada ele **sobe sem reclamar e não produz mapa**.

Por isso o primeiro bloco é a bancada que prova que a árvore fecha. Ele serve a um gate que vence em três dias **e** é pré-requisito do bloco seguinte — a justificativa mais forte que um bloco de abertura pode ter.

### E o que continua onde estava

As Etapas 6 a 10 não foram tocadas, e os TP3, TP4 e TP5 mantêm datas e conteúdo. A compressão foi absorvida inteiramente dentro do trimestre 26T3, entre a Etapa 3 e a Etapa 5.

## Como as aulas se conectam com as outras disciplinas do bloco

O PB é a terça-feira, e ele **consolida na prática** o que as disciplinas de referência apresentam nos outros dias. A DR1 (segundas e quartas) trata da arquitetura e da evolução do ROS 2; a DR2 (quintas e sextas) cobre fundamentos de OpenCV e captura de imagem. Vale explicitar a costura enquanto estuda: a imagem que você aprende a capturar na DR2 é exatamente a que vai viajar como `sensor_msgs/Image` no tópico `/camera/image_raw` do seu projeto.

## Se você faltou

Comece pelo PDF da aula, depois rode o exemplo correspondente e por fim faça a tarefa da semana. As tarefas não valem nota isoladamente, mas cada uma delas é um pedaço já pronto do TP seguinte — pular uma custa mais tarde do que custaria agora.
