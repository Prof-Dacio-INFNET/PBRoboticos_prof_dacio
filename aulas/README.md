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
| [Aula 8](etapa04-aula08/index.md) | 08/09/2026 | 4 | Ações a fundo: o ciclo de vida de um objetivo | <span class="pb-tag next">próxima</span> |
| Aula 9 | 15/09/2026 | 5 | Detecção treinada e métrica declarada · URDF e YAML | <span class="pb-tag soon">a seguir</span> |
| Aula 10 | 22/09/2026 | 5 | Navegação autônoma + aterrissagem do TP2 | <span class="pb-tag soon">a seguir</span> |

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
| G2.4 | detecção evoluída com métrica declarada | Aula 9 · 15/09 | 19/09 | 4 dias |
| G2.5 | YAML + URDF no RViz2 com TF coerente | Aula 9 · 15/09 | 22/09 | 7 dias |

### O que a redistribuição custou, dito com todas as letras

O material da Etapa 2 ocupou três encontros em vez de dois, e o encontro extra saiu da **Etapa 3**, que tinha duas datas na janela 17/08–29/08 e ficou com uma. Nada foi cortado, mas quatro requisitos do TP2 mudaram de lugar:

**Ações** (G2.2 e G2.3) eram da Etapa 3 e passam para a Aula 7. O deslocamento é confortável porque ação é pré-requisito de navegação — o Nav2 é construído sobre ações —, então ela entra na Etapa 4 como fundamento e não como enxerto.

**Detecção treinada com métrica** (G2.4) era o "detecção inteligente" da Etapa 3 e passa para a Aula 8, dentro de percepção veicular. É o mesmo assunto com mais contexto: detectar veículo, pedestre ou placa é o caso de uso que justifica sair da segmentação por cor.

**Parametrização e URDF** (G2.5) passa para a Aula 9, junto de SLAM e TF — que é onde URDF e RViz2 seriam necessários de qualquer forma. Aqui a redistribuição melhora a sequência em vez de piorar: ensinar URDF isolado é abstrato; ensinar URDF porque o SLAM precisa de TF coerente é concreto.

### Segunda correção: a Aula 7 abriu ações, a Aula 8 as entrega

A Aula 7 (01/09) foi ocupada pelas demonstrações com a webcam e pelos cartões, e ações ficaram **apresentadas, não trabalhadas**. A Aula 8 (08/09) passa a ser a entrega completa — ciclo de vida do objetivo, os três verbos de término, e o cancelamento demonstrado —, o que fecha G2.2 e G2.3 com quatro e oito dias de folga.

O efeito colateral é que a **Aula 9 (15/09) carrega dois gates**: G2.4 (detecção treinada com métrica) e G2.5 (YAML, URDF e TF no RViz2). Todos continuam sendo ensinados antes de vencer, mas a folga do G2.4 caiu para quatro dias e a aula ficou densa.

**A mitigação é tirar o URDF da aula e transformá-lo em leitura prévia.** Parametrização em YAML a turma já pratica desde a Aula 3 (`ros2 param set`, `config/*.yaml`); o que é realmente novo no G2.5 é URDF e TF no RViz2, e isso é mecânico o bastante para caber num tutorial. Com o tutorial publicado antes, a Aula 9 vira clínica em vez de primeira exposição.

**As folgas de quatro dias — G2.2 e G2.4 — são o novo ponto a vigiar.** Quatro dias é o suficiente para quem sai da aula com o exemplo rodando, e insuficiente para quem sai com o exemplo quebrado. É por isso que as duas aulas têm bloco de mão na massa com todo mundo executando, e não só demonstração no projetor.

### E o que continua onde estava

As Etapas 6 a 10 não foram tocadas, e os TP3, TP4 e TP5 mantêm datas e conteúdo. A compressão foi absorvida inteiramente dentro do trimestre 26T3, entre a Etapa 3 e a Etapa 5.

## Como as aulas se conectam com as outras disciplinas do bloco

O PB é a terça-feira, e ele **consolida na prática** o que as disciplinas de referência apresentam nos outros dias. A DR1 (segundas e quartas) trata da arquitetura e da evolução do ROS 2; a DR2 (quintas e sextas) cobre fundamentos de OpenCV e captura de imagem. Vale explicitar a costura enquanto estuda: a imagem que você aprende a capturar na DR2 é exatamente a que vai viajar como `sensor_msgs/Image` no tópico `/camera/image_raw` do seu projeto.

## Se você faltou

Comece pelo PDF da aula, depois rode o exemplo correspondente e por fim faça a tarefa da semana. As tarefas não valem nota isoladamente, mas cada uma delas é um pedaço já pronto do TP seguinte — pular uma custa mais tarde do que custaria agora.
