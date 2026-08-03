# Gates de cada TP — o mapa de checkpoints da implementação

Um **gate** é um ponto de controle: um estado do projeto que ou **é verdade** ou **não é**, verificável por um comando e provado por um artefato no repositório. Não é uma etapa de cronograma ("estudar SLAM"), não é uma intenção ("começar o mapa"). É uma porta: você passou, ou você ainda não passou.

Este documento existe porque a causa nº 1 de TP entregue pela metade não é falta de capacidade — é descobrir na quinta-feira que a coisa que deveria estar de pé desde a semana anterior nunca ficou. Os gates deslocam essa descoberta para o dia em que ela ainda é barata.

> **Como usar na prática.** Copie o bloco de checklist do seu TP para o `PROJETO.md`, marque cada gate no dia em que ele passou, e faça **um commit por gate** com a mensagem começando pelo código (`G2.3: action com feedback publicando`). O histórico do repositório vira, sozinho, o diário de bordo que a arguição final vai cobrar.

## Como ler as tabelas

Cada linha tem quatro colunas, e as quatro importam:

**O que tem de estar verdadeiro** é o critério, escrito de forma que a resposta seja sim ou não. **Como provar** é o comando que qualquer pessoa (você, o professor, um colega) roda para verificar — se não existe comando, não é gate. **Evidência no repo** é o arquivo que fica como prova depois que o terminal fechou; nenhum gate está fechado enquanto a evidência não está commitada. **Quando** é a data-limite recomendada, sempre com folga em relação à entrega.

As datas são recomendações, não prazos formais — o único prazo formal é a entrega do TP no Moodle. Mas quem cumpre os gates entrega no prazo, e quem os ignora entrega no susto.

## Regra dos três estados

Todo gate está sempre em um destes estados, e o `PROJETO.md` deve refletir isso:

| Marca | Significado | O que fazer |
|---|---|---|
| `[x]` | passou, com evidência commitada | seguir para o próximo |
| `[ ]` | ainda não chegou a data | seguir o plano |
| `[!]` | **venceu sem passar** | acionar a escada de recuperação (fim deste documento) **no mesmo dia** |

Um `[!]` não é vergonha nem perda de nota — é informação. O que custa nota é um `[!]` silencioso que vira surpresa na entrega.

---

## TP1 — Ambiente, Comunicação Básica e Pipeline Inicial de Visão

**Entrega: sexta, 28/08/2026** · Etapas 1–2 · o TP que decide o resto do semestre, porque é onde o projeto ganha identidade.

| Gate | O que tem de estar verdadeiro | Como provar | Evidência no repo | Quando |
|---|---|---|---|---|
| **G1.0** | Ambiente ROS 2 Humble operante: `ros2` responde, workspace compila, dois terminais conversam | `ros2 doctor --report \| head -20` e `bash recursos/check-ambiente.sh` | `docs/evidencias/tp1/check-ambiente.txt` | 07/08 |
| **G1.1** | Projeto **escolhido, derivado e declarado**: domínio, usuário, classes percebidas, trilha S/H/R e plano B | leitura do `PROJETO.md` (marcadores `<!-- PB:PROJETO -->` e `<!-- PB:TRILHA -->` presentes) | `PROJETO.md` | 11/08 |
| **G1.2** | Grafo mínimo de imagem no ar: um nó publica em `/camera/image_raw`, outro consome — **sem travar** | `ros2 topic hz /camera/image_raw` mostrando taxa estável por 10 s | `docs/evidencias/tp1/topic-hz.txt` | 15/08 |
| **G1.3** | Segmentação por cor detectando **o objeto do seu projeto** e publicando contagem | `ros2 topic echo /vision/contagem --once` com o valor esperado na cena montada | print/GIF em `docs/evidencias/tp1/segmentacao.png` | 20/08 |
| **G1.4** | Serviço `/vision/status` respondendo com informação **do seu domínio**, e `rqt_graph` mostrando o grafo completo | `ros2 service call /vision/status std_srvs/srv/Trigger "{}"` | `docs/evidencias/tp1/rqt_graph.png` + saída do serviço | 24/08 |
| **G1.5** | Relatório fechado: decisões, o experimento de oclusão, limitações conhecidas, uso de IA declarado | revisão de leitura do `docs/relatorio-tp1.md` (todas as seções preenchidas) | `docs/relatorio-tp1.md` | 26/08 |
| **G1.6** | **Entrega**: `main` atualizado, branch `entrega-tp1` criado, tag `tp1` empurrada, PDF+ZIP no Moodle, link do repositório no Moodle | `git tag --list` mostra `tp1`; a página do GitHub abre em janela anônima | tag `tp1` + postagem no Moodle | 28/08 |

**O gate que mais gente subestima é o G1.1.** Ele parece burocracia e é o oposto disso: sem domínio e classes definidos, o G1.3 não tem o que detectar, e o aluno passa duas semanas afinando HSV de um cubo vermelho genérico que não vai para lugar nenhum. Escolha o domínio antes de escrever a primeira linha de visão.

---

## TP2 — Interfaces Próprias, Ações e Parametrização

**Entrega: sexta, 25/09/2026** · Etapa 3 · o TP em que o projeto deixa de usar só mensagens prontas e passa a **falar a própria língua**.

| Gate | O que tem de estar verdadeiro | Como provar | Evidência no repo | Quando |
|---|---|---|---|---|
| **G2.0** | Pacote de interfaces separado (`<projeto>_interfaces`) compilando com `rosidl` | `colcon build --packages-select <projeto>_interfaces` sem erro | log de build em `docs/evidencias/tp2/build.txt` | 04/09 |
| **G2.1** | `.msg` e `.srv` do **domínio** definidos e visíveis no ambiente | `ros2 interface show <projeto>_interfaces/msg/<SuaMsg>` | arquivos `.msg`/`.srv` versionados | 08/09 |
| **G2.2** | Action definida e servidor respondendo goal → resultado | `ros2 action list` e `ros2 action send_goal ...` completando | `docs/evidencias/tp2/action-goal.txt` | 12/09 |
| **G2.3** | Action com **feedback periódico** e **cancelamento** funcionando de verdade | `ros2 action send_goal ... --feedback` e cancelamento com `Ctrl-C` no cliente, com log do servidor tratando o cancel | GIF/asciinema em `docs/evidencias/tp2/` | 16/09 |
| **G2.4** | Detecção/rastreamento evoluída (YOLO ou equivalente) com **métrica declarada** (ex.: % de frames com alvo mantido) | script/notebook que imprime a métrica sobre um vídeo fixo | `docs/evidencias/tp2/metrica-tracking.md` | 19/09 |
| **G2.5** | Parametrização em YAML + URDF carregando no RViz2 com TF coerente | `ros2 param dump /<no>` e `ros2 run rviz2 rviz2` mostrando o modelo | `config/*.yaml`, `urdf/*.urdf`, print do RViz2 | 22/09 |
| **G2.6** | **Entrega**: relatório, branch `entrega-tp2`, tag `tp2`, Moodle | `git tag --list` mostra `tp2` | tag + postagem | 25/09 |

**Armadilha clássica do TP2:** implementar a Action como um "publisher com nome bonito". Se o seu servidor não consegue ser cancelado no meio, o G2.3 não passou — e o G2.3 é o gate que a correção efetivamente testa.

---

## TP3 — Integração, Mapeamento e Percepção Avançada

**Entrega: sexta, 23/10/2026** · Etapa 4 · o TP mais pesado do semestre em infraestrutura. Comece pelo launch, não pelo SLAM.

| Gate | O que tem de estar verdadeiro | Como provar | Evidência no repo | Quando |
|---|---|---|---|---|
| **G3.0** | `bringup.launch.py` sobe o sistema **inteiro** com um comando | `ros2 launch <projeto> bringup.launch.py` e `ros2 node list` com todos os nós | `launch/bringup.launch.py` | 30/09 |
| **G3.1** | Mundo/cenário de simulação carregando com o robô e a câmera no lugar | print do Gazebo/RViz2 com o robô no mundo | `worlds/` ou `models/` + print | 06/10 |
| **G3.2** | Árvore TF **completa e sem warning**: `map → odom → base_link → sensores` | `ros2 run tf2_tools view_frames` (gera PDF) | `docs/evidencias/tp3/frames.pdf` | 10/10 |
| **G3.3** | SLAM Toolbox produzindo mapa persistido do cenário | `ros2 run nav2_map_server map_saver_cli -f mapa` e o par `.pgm`/`.yaml` | `maps/mapa.pgm` + `maps/mapa.yaml` + print | 15/10 |
| **G3.4** | Segmentação por instância publicando em `/vision/segmented` com as classes do domínio | `ros2 topic echo /vision/segmented --once` + `rqt_image_view` | print em `docs/evidencias/tp3/` | 18/10 |
| **G3.5** | Módulo de percepção veicular rodando e documentado | script executando sobre o dado de referência | `docs/evidencias/tp3/veicular.md` | 20/10 |
| **G3.6** | **Entrega**: relatório, branch `entrega-tp3`, tag `tp3`, Moodle | `git tag --list` mostra `tp3` | tag + postagem | 23/10 |

**G3.2 é o gate de verdade deste TP.** Noventa por cento dos problemas de SLAM e de Nav2 são problemas de TF disfarçados. Se `view_frames` mostra árvore quebrada ou dois `odom`, pare tudo e conserte antes de tocar no G3.3 — insistir no SLAM com TF errado é queimar uma semana.

---

## TP4 — Navegação Autônoma, Registro e Percepção Veicular

**Entrega: sábado, 21/11/2026, até 12h** · Etapa 5 · atenção ao horário: o prazo é **meio-dia**, não meia-noite.

| Gate | O que tem de estar verdadeiro | Como provar | Evidência no repo | Quando |
|---|---|---|---|---|
| **G4.0** | Nav2 sobe com o mapa do TP3 e localiza (AMCL convergindo) | `ros2 launch` do Nav2 + print do RViz2 com a nuvem de partículas concentrada | `docs/evidencias/tp4/amcl.png` | 30/10 |
| **G4.1** | Robô navega até **um** goal enviado pelo RViz2 sem intervenção | vídeo curto de 20 s | `docs/evidencias/tp4/goal-unico.mp4` (ou link) | 04/11 |
| **G4.2** | Rota com **≥3 waypoints** completada, costmaps local e global configurados e explicados | `ros2 topic echo /navigate_through_poses/_action/status` + prints dos costmaps | `config/nav2_params.yaml` + prints | 09/11 |
| **G4.3** | Comportamento de obstáculo (<0,5 m) disparando e o robô se recuperando | vídeo do obstáculo entrando na frente do robô | `docs/evidencias/tp4/obstaculo.mp4` (ou link) | 12/11 |
| **G4.4** | `ros2 bag` gravado e **reproduzível**: dá para rodar a análise sem o robô ligado | `ros2 bag info <bag>` e `ros2 bag play <bag>` alimentando os nós de análise | `bags/` (ou link, se grande) + `docs/evidencias/tp4/bag-info.txt` | 15/11 |
| **G4.5** | Percepção veicular no MetaDrive: HSV + Canny + Hough sobre a cena, com discussão de falhas | script + prints das três etapas | `docs/evidencias/tp4/veicular/` | 17/11 |
| **G4.6** | CNN treinada (≥500 frames, 3 classes) com **comparação com/sem augmentation** e matriz de confusão | notebook executado de ponta a ponta | `notebooks/tp4_cnn.ipynb` + `docs/evidencias/tp4/matriz-confusao.png` | 19/11 |
| **G4.7** | **Entrega**: relatório, branch `entrega-tp4`, tag `tp4`, Moodle **até 12h** | `git tag --list` mostra `tp4` | tag + postagem | 21/11 |

**Aviso de calendário:** entre o TP4 (21/11) e o TP5 (27/11) há **seis dias**. Isso não é erro do cronograma — é a razão pela qual o TP5 tem de começar durante o TP4. O gate G5.0 abaixo tem data **anterior** à entrega do TP4 de propósito.

---

## TP5 — Manipulação, Aprendizado e Validação

**Entrega: sexta, 27/11/2026** · Etapa 6 · o TP mais curto em calendário e mais amplo em conteúdo. Paralelize.

| Gate | O que tem de estar verdadeiro | Como provar | Evidência no repo | Quando |
|---|---|---|---|---|
| **G5.0** | Opção A (hardware) **ou** B (drone PX4 simulado) escolhida e registrada, com plano B declarado | `docs/decisoes.md` com data | `docs/decisoes.md` | 14/11 |
| **G5.1** | MoveIt 2 configurado e planejando para **≥3 poses** distintas com detecção de colisão | vídeo/prints das três poses no RViz2 | `docs/evidencias/tp5/moveit/` | 20/11 |
| **G5.2** | Dataset de ≥1000 frames coletado para o comparativo de condução | `ls dataset/ \| wc -l` e histograma das ações | `docs/evidencias/tp5/dataset.md` | 21/11 |
| **G5.3** | Baseline PID rodando e medido (métrica objetiva, não impressão) | script imprimindo a métrica em ≥10 episódios | `docs/evidencias/tp5/pid.md` | 23/11 |
| **G5.4** | Behavioral Cloning treinado e **comparado** com o PID na mesma métrica | tabela PID × BC no relatório | `docs/evidencias/tp5/comparativo.md` | 25/11 |
| **G5.5** | PPO no highway-env com ~300k steps: curva de recompensa e política avaliada | gráfico de treino + avaliação em ≥10 episódios | `docs/evidencias/tp5/ppo-curva.png` | 26/11 |
| **G5.6** | Opção escolhida no G5.0 **demonstrada**: robô real percebendo e se movendo, ou missão de waypoints do drone | vídeo | link/vídeo em `docs/evidencias/tp5/` | 26/11 |
| **G5.7** | **Entrega**: relatório, branch `entrega-tp5`, tag `tp5`, Moodle | `git tag --list` mostra `tp5` | tag + postagem | 27/11 |

**O PPO é o item que mais atrasa entregas**, porque 300k steps não terminam em quinze minutos e ninguém descobre isso no dia 26. Dispare o treino **cedo** (ele roda sozinho enquanto você faz o MoveIt) e salve os checkpoints. Treino que roda em segundo plano é tempo que você ganha de graça; treino iniciado na véspera é nota perdida por relógio.

---

## Entrega final e apresentação

**Entrega final: sexta, 04/12/2026** · **Apresentações: terças 08/12 e 15/12/2026**

| Gate | O que tem de estar verdadeiro | Como provar | Evidência no repo | Quando |
|---|---|---|---|---|
| **GF.0** | Sistema integrado sobe com **um** comando e opera ponta a ponta | `ros2 launch <projeto> bringup.launch.py` em máquina limpa (ou container) | roteiro de reprodução no `README.md` | 30/11 |
| **GF.1** | Vídeo de demonstração publicado (YouTube **público ou não-listado**, nunca privado) e o link abre em janela anônima | abrir o link em janela anônima e assistir | link no `README.md` e no Moodle | 02/12 |
| **GF.2** | Repositório navegável por quem nunca o viu: README com o quê/por quê/como rodar, licença, estrutura | um colega consegue rodar seguindo só o README | `README.md`, `LICENSE` | 02/12 |
| **GF.3** | Relatório final consolidado com resultados, limitações honestas e trabalhos futuros | revisão de leitura | `docs/relatorio-final.md` | 03/12 |
| **GF.4** | **Entrega final**: `main` atualizado, tag `final`, PDF+ZIP+links no Moodle | `git tag --list` mostra `final` | tag + postagem | 04/12 |
| **GF.5** | Apresentação ensaiada dentro do tempo, com plano B para demo ao vivo (vídeo gravado no bolso) | ensaio cronometrado | slides no repositório | 07/12 |

**Sobre a demo ao vivo:** ela impressiona quando funciona e destrói o tempo da apresentação quando não funciona. A regra profissional é ter o vídeo gravado aberto numa aba. Rodar ao vivo é escolha, não obrigação — e ninguém perde ponto por apresentar a gravação.

---

## Gates × níveis da rubrica

Os gates não substituem a rubrica; eles são o caminho mais curto até ela. A leitura aproximada:

| Situação dos gates do TP | Nível provável |
|---|---|
| gates centrais não passaram; entrega parcial ou não reproduzível | **ND** — não desenvolvido |
| todos os gates passaram, com evidência, sem aprofundamento além do pedido | **D** — desenvolvido |
| todos os gates + análise crítica, métricas próprias, tratamento de caso difícil | **DL** — desenvolvido com louvor |
| tudo acima + contribuição original (derivação bem construída, ferramenta reutilizável, comparação que ninguém pediu e que ensina algo) | **DML** — desenvolvido com muito louvor |

Repare no que **não** aparece nessa tabela: esforço, tempo gasto, intenção. A régua lê evidência. É por isso que cada gate exige um artefato commitado — sem ele, o trabalho existiu e não pôde ser avaliado, o que na prática é o mesmo que não ter existido.

## Escada de recuperação (o que fazer quando um gate vence)

Quando um gate vira `[!]`, existe uma ordem de tentativas. Ela é curta de propósito, porque o inimigo é o tempo.

**Degrau 1 — no mesmo dia, reduza o escopo do gate, não o abandone.** Menos classes, cena menor, mapa de um cômodo, menos waypoints. Um gate passado em versão reduzida mantém o projeto avançando; um gate pendente trava todos os que vêm depois.

**Degrau 2 — troque o caminho, mantenha o objetivo.** Webcam não abre no WSL2? `fonte:=video` ou `fonte:=sintetico`. Gazebo não roda? RViz2 com fonte sintética. YOLO não instala? Detector clássico com métrica honesta. O objetivo do TP quase nunca depende da ferramenta específica.

**Degrau 3 — acione o plano B declarado no `PROJETO.md`.** Ele existe justamente para este momento; registre em `docs/decisoes.md` com data e motivo. Plano B acionado e documentado **não** tira nota.

**Degrau 4 — fale com o professor, com o diagnóstico pronto.** Traga o comando que falhou, a mensagem de erro completa, o que você já tentou e o que a busca retornou. Pergunta com diagnóstico costuma ser resolvida em minutos; "não está funcionando" leva a semana inteira.

O que **não** está na escada: esperar melhorar sozinho, começar o TP seguinte deixando o gate para trás, ou entregar sem mencionar o que ficou faltando. A limitação declarada com franqueza custa pouco; a limitação escondida que aparece na arguição custa caro.

## Bloco para copiar no `PROJETO.md`

Mantenha o marcador — ele é lido automaticamente na correção.

```markdown
<!-- PB:GATES -->
### TP1 — entrega 28/08
- [ ] G1.0 ambiente operante (07/08)
- [ ] G1.1 projeto declarado: domínio, classes, trilha, plano B (11/08)
- [ ] G1.2 grafo de imagem estável (15/08)
- [ ] G1.3 segmentação + contagem do meu objeto (20/08)
- [ ] G1.4 serviço /vision/status + rqt_graph (24/08)
- [ ] G1.5 relatório fechado (26/08)
- [ ] G1.6 tag tp1 + Moodle (28/08)
```

Replique o bloco para os demais TPs conforme avançar. Cada `[x]` deve vir acompanhado do commit correspondente — é a rastreabilidade que transforma o repositório em prova de processo, e não apenas em depósito de arquivos.

Veja também: [derivações de projeto](derivacoes-projetos.md), [simulação × hardware real](simulado-vs-hardware.md) e o [catálogo](catalogo-projetos.md).
