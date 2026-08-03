# Projeto simulado × projeto com hardware real — como a régua funciona

Todo projeto do PB nasce em simulação. A pergunta não é *"posso simular?"* (pode, e a maioria vai) — é **"em que ponto, e com que fatia do meu projeto, eu encosto no mundo real?"**. Este documento explica a regra do jogo, para que ninguém escolha uma trilha achando que escolheu a fácil.

## A regra em uma frase

> **Simulação não é o caminho fácil — é o caminho sem desculpas.** Quem simula tem o ambiente sob controle, então a expectativa de **complexidade e eficácia é maior**. Quem coloca hardware real no circuito gasta uma parte grande do esforço em problemas que a simulação não tem — e isso é reconhecido, mesmo quando o resultado final é visivelmente mais modesto.

Essa é a assimetria deliberada da disciplina. Ela existe porque as duas trilhas ensinam coisas diferentes e igualmente valiosas: a simulação ensina **profundidade algorítmica e método experimental**; o hardware ensina **integração, tolerância a falha e humildade de engenheiro**.

## Por que a expectativa é maior na simulação

Num mundo simulado, a iluminação não muda sozinha, a bateria não cai, a roda não patina, o driver da câmera não some, a rede não engasga e o robô não quebra às 23h de véspera de entrega. Você pode rodar o mesmo cenário cem vezes e obter cem resultados comparáveis. Pode automatizar experimentos. Pode reiniciar em dois segundos. Pode gravar o vídeo perfeito na décima tentativa.

Tudo isso é tempo devolvido para você — e o que a disciplina cobra em troca é que esse tempo apareça no **conteúdo**: mais classes detectadas, mapa maior e mais difícil, comportamento de recuperação de falha, métricas medidas em múltiplos episódios, comparação entre abordagens, análise de sensibilidade a parâmetros. O desafio simulado é mais previsível, então a resposta esperada é mais ambiciosa.

O contrário também vale, e é honesto dizer em voz alta: um projeto simulado que entrega o mínimo — um robô que anda em linha reta numa sala vazia detectando um cubo vermelho — está **abaixo** do esperado, ainda que tudo funcione. "Funciona" é o piso da simulação, não o teto.

## Por que hardware real ganha reconhecimento

Quem pluga uma Raspberry Pi, um drone ou uma webcam de verdade herda uma lista de problemas que não aparecem em nenhum tutorial: alimentação e queda de tensão, driver e permissão de dispositivo, latência e perda de frames, calibração de câmera, ruído de encoder, atrito real, Wi-Fi instável, ROS 2 atravessando duas máquinas, e o clássico "funcionava ontem". Resolver isso **é** engenharia de sistemas robóticos, e consome uma fatia do orçamento de esforço que a simulação gasta em conteúdo.

Por isso, na trilha de hardware, escopo menor e desempenho inferior são aceitáveis — **desde que a dificuldade esteja documentada**. É a documentação que transforma sofrimento em evidência: o que quebrou, como você diagnosticou, o que tentou, o que funcionou, o que ficou como limitação conhecida. Um relatório de hardware sem essa seção perde justamente aquilo que compensa o escopo menor.

## As três trilhas

| Trilha | O que significa | Para quem |
|---|---|---|
| **S — Simulada** | Gazebo/RViz2/MetaDrive do começo ao fim; TP5 pela Opção B (drone PX4 simulado) | maioria da turma; quem quer profundidade algorítmica |
| **H — Híbrida** (recomendada) | núcleo em simulação + **um** elemento real: webcam via usbipd, ou validação do TP5 numa Raspberry Pi | quem tem algum hardware e não quer apostar o semestre nele |
| **R — Real** | robô físico como palco principal a partir do TP4/TP5 | quem já tem a plataforma montada e tempo |

A trilha **H** é a recomendação padrão da disciplina. Ela captura quase todo o aprendizado de integração real — a webcam sozinha já entrega ruído, iluminação, latência e driver — sem colocar o cronograma inteiro na mão de um componente que pode chegar quebrado.

**Você não escolhe a trilha para o semestre inteiro no TP1.** Escolhe por TP, e a decisão só é irreversível no TP5 (Opção A/B). O que se pede no TP1 é apenas declarar a intenção e o plano B.

## O que cada trilha precisa entregar, TP a TP

A tabela lê assim: nas duas colunas está o que se espera de um trabalho **plenamente desenvolvido** (D) em cada trilha. Não é o teto — é a régua.

| TP | Trilha S (simulada) — mais profundidade | Trilha H/R (hardware no circuito) — mais integração |
|---|---|---|
| **TP1** | pipeline de visão com ≥2 classes ou 2 critérios (ex.: cor **e** área/forma); tratamento de caso difícil (oclusão, sombra) discutido com evidência | webcam real publicando em `/camera/image_raw` com FPS medido; discussão de iluminação/latência; pipeline pode ser mais simples |
| **TP2** | interfaces do domínio bem modeladas; Action com feedback, cancelamento **e** tratamento de estados; rastreamento estável com métrica (perda de alvo em %) | mesma Action, cenário mais curto; foco em manter o rastreamento com imagem real ruidosa; URDF que corresponde ao robô físico e é medido |
| **TP3** | mapa de ambiente **não trivial** (≥2 cômodos, obstáculos, laço fechado); segmentação por instância com classes do domínio; análise do TF tree | SLAM com dados reais ou bag gravado do robô; mapa menor aceitável; documentar deriva de odometria e ruído do sensor |
| **TP4** | Nav2 com recuperação de falha; rota com ≥3 waypoints e obstáculo dinâmico; CNN com dataset balanceado e comparação com/sem augmentation | navegação real em espaço reduzido; behavior tree simples; percepção veicular continua no MetaDrive (igual para todos) |
| **TP5** | MoveIt 2 com ≥3 poses e colisões; Opção B (drone PX4) com missão de waypoints; comparativo PID × BC × PPO com métricas em ≥10 episódios | Opção A (Raspberry Pi): robô que percebe e se move de verdade, com fotos e vídeo; comparativo pode rodar em simulação (é o padrão para todos) |
| **Final** | sistema integrado operando ponta a ponta e demonstrado em cenário completo | sistema real operando, ainda que em versão reduzida, + seção franca de limitações |

O módulo veicular (MetaDrive/highway-env, TPs 4 e 5) é **simulado para todos**, independentemente da trilha. Ninguém precisa de carro.

## A moeda de troca: escopo × robustez

Pense no esforço do TP como um orçamento fixo. A trilha S gasta pouco em infraestrutura e muito em conteúdo; a trilha R gasta muito em infraestrutura e pouco em conteúdo. As duas gastam tudo. O que **não** é aceito, em nenhuma das duas, é sobrar orçamento — projeto simulado raso ou robô real que só liga e pisca LED.

| Se você está na trilha… | Você pode reduzir… | Mas tem que aumentar… |
|---|---|---|
| S — simulada | nada de infraestrutura (não há) | complexidade do cenário, número de casos testados, rigor das métricas, análise crítica |
| H — híbrida | um pouco do cenário no TP em que o hardware entra | a documentação do que a peça real mudou (com números: FPS, latência, taxa de acerto) |
| R — real | escopo do cenário e desempenho absoluto | evidência de integração, diagnóstico de falhas, registro de limitações |

## Gestão de risco de hardware (leia antes de comprar qualquer coisa)

Hardware falha, e falha perto do prazo. Três regras salvam semestres. **Primeira: nunca deixe hardware no caminho crítico de mais de um TP.** Se a peça atrasa, você perde um TP, não três. **Segunda: mantenha o caminho simulado sempre funcionando** — o mesmo pacote ROS 2 deve rodar com `fonte:=sintetico` e com `fonte:=webcam`; o exemplo da Aula 3 já é assim de propósito. **Terceira: grave evidência no dia em que funciona.** Vídeo curto, bag do ROS 2, fotos. O robô que funcionou na terça e queimou na quinta ainda vale nota se está gravado — e não vale nada se está só na sua memória.

O plano B nunca é "peço prorrogação". O plano B é a versão simulada equivalente, declarada no `PROJETO.md` desde o TP1, e o custo de acioná-la é apenas registrar a decisão em `docs/decisoes.md`.

## Como declarar sua trilha

No `PROJETO.md`, um bloco curto — e mantenha o marcador, ele é lido automaticamente na correção:

```markdown
<!-- PB:TRILHA -->
- **Trilha:** H (híbrida)
- **Elemento real:** webcam USB via usbipd a partir do TP1; Raspberry Pi 4 na validação do TP5 (Opção A)
- **Plano B:** fonte sintética/vídeo gravado no lugar da webcam; TP5 pela Opção B (drone PX4 simulado)
- **Gatilho do plano B:** se o item real não estiver funcionando até o gate G_x.2 do TP em questão
```

Mudou de ideia no meio do semestre? Ótimo, é o comportamento esperado de quem gerencia risco. Registre em `docs/decisoes.md` com data e motivo e siga em frente — mudança documentada **não** tira nota; mudança silenciosa, sim, porque quebra a rastreabilidade do projeto.

## Perguntas que sempre aparecem

**"Simulação vale menos que hardware?"** Não. Valem o mesmo, com réguas diferentes: a simulação é cobrada por profundidade, o hardware por integração.

**"Se eu usar hardware, posso entregar menos?"** Menos **escopo**, sim; menos **evidência**, não. A troca é escopo por documentação da dificuldade.

**"Uso hardware só para o vídeo ficar bonito. Vale?"** Vale como demonstração, não como trilha H. Trilha H é o dado real atravessando o grafo ROS 2, não o robô parado ao fundo.

**"Meu computador não roda o Gazebo bem. Isso me joga para a trilha R?"** Não — te joga para cenários mais leves (mundos menores, RViz2 + fonte de imagem sintética, MetaDrive com resolução reduzida). Fale com o professor antes do TP3, que é onde o Gazebo pesa.

**"Posso fazer tudo com a câmera do notebook e nenhum robô?"** Sim, com a ressalva do TP3/TP4: você precisa de um robô **simulado** para SLAM e Nav2. A câmera real entra como fonte de percepção; o corpo do robô pode ser simulado. É exatamente a trilha H.

Veja também: [derivações de projeto](derivacoes-projetos.md), [gates de cada TP](gates-tps.md) e o [catálogo](catalogo-projetos.md).
