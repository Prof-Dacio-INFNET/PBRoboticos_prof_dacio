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
| [Aula 6](etapa03-aula06/index.md) | 25/08/2026 | 3 | Interfaces próprias e detecção inteligente | <span class="pb-tag next">atual</span> |
| Aula 7 | 01/09/2026 | 4 | SLAM e percepção veicular | <span class="pb-tag soon">a seguir</span> |

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

## Como as aulas se conectam com as outras disciplinas do bloco

O PB é a terça-feira, e ele **consolida na prática** o que as disciplinas de referência apresentam nos outros dias. A DR1 (segundas e quartas) trata da arquitetura e da evolução do ROS 2; a DR2 (quintas e sextas) cobre fundamentos de OpenCV e captura de imagem. Vale explicitar a costura enquanto estuda: a imagem que você aprende a capturar na DR2 é exatamente a que vai viajar como `sensor_msgs/Image` no tópico `/camera/image_raw` do seu projeto.

## Se você faltou

Comece pelo PDF da aula, depois rode o exemplo correspondente e por fim faça a tarefa da semana. As tarefas não valem nota isoladamente, mas cada uma delas é um pedaço já pronto do TP seguinte — pular uma custa mais tarde do que custaria agora.
