# Aula 17 — Fechar o item 2, a câmera que não é a sua, e a rede que decora

**Terça, 10/11/2026 · sala SJ205 · Etapa 9 (09/11–21/11)**

[:material-file-pdf-box: Slides da Aula 17 (PDF)](apresentacao-aula17.pdf){ .md-button .md-button--primary }
[:material-car-side: Câmera sintética: MetaDrive](../../exemplos/aula17-metadrive/index.md){ .md-button }
[:material-brain: A CNN, as duas rodadas e a matriz](../../exemplos/aula17-cnn/index.md){ .md-button }
[:material-chart-timeline-variant: Árvore e sessão gravada](../../exemplos/aula16-arvore-bag/index.md){ .md-button }

!!! info "Como esta página funciona"
    Em sala eu **demonstrei** o caminho no meu ambiente, e vocês observaram. **O que é para rodar no seu ambiente está na [tarefa da semana](#a-tarefa-da-semana)**, como uma sequência ordenada para fazer em casa, no seu ritmo — é lá que a aula acontece para cada um.

    As seções dos blocos 1 a 4 descrevem **o que foi mostrado e o que observar**: elas servem para reconhecer, na sua tela, o que apareceu na minha. Cada bloco se sustenta sozinho e diz o que pressupõe; dá para ler fora de ordem.

## Cenas dos últimos episódios

**Na Aula 16** o diagnóstico do Nav2 rodou contra o sistema saudável e contra os três defeitos mudos que mais aparecem — sem pose inicial, um intruso em `/cmd_vel`, o gerenciador parado —, e em cada um a primeira linha de *Onde olhar* apontou a causa, mesmo quando o terminal do launch falava de outra coisa. Depois veio a descoberta que decide o item 2: **no Humble não existe nó de árvore que meça distância a obstáculo**, e por isso quem diz que há obstáculo é você — por um nó de condição em C++, ou pelo `vigia.py`, do lado do cliente.

O que ficou pela metade foi o **bloco da sessão gravada**. Era o que cederia se o tempo apertasse, e foi o que cedeu. Ele abre a aula de hoje, porque é o que vence primeiro.

Os conceitos de antes que a aula de hoje vai usar:

- **Cancelar e reenviar um objetivo** é a Aula 8. É tudo o que o `vigia.py` faz: ele contrata o servidor de ação do Nav2, cancela quando o laser vê algo perto, espera e manda o mesmo objetivo de novo — sem o Nav2 saber que ele existe.
- **cor → borda → reta**, com os limiares no topo do arquivo, é o `faixas.py` da Aula 13. Hoje ele roda sobre uma câmera que não foi a dele, e a primeira etapa é a que quebra.
- **A métrica declarada antes de medir** é a Aula 9. Vale para o limiar de 0,5 m da régua da sessão, para o limiar de cor da faixa e para a acurácia da rede.
- **A métrica que mede o instrumento** apareceu três vezes: o IoU médio alto do pior detector (Aula 13), a nuvem mais concentrada do robô mais perdido (Aula 15) e os 49 m de trajetória do robô que andou 25 (Aula 16). Hoje é a quarta.
- **Versão desalinhada falha calada.** Hoje há três Pythons em jogo — o do sistema, o do MetaDrive e o da rede —, e cada um existe por um motivo que a página explica.

## A ideia da aula em uma frase

**Acertar 90% respondendo sempre a mesma coisa não é aprender.** Uma rede treinada num conjunto em que nove de cada dez imagens são *via livre* acerta 90% sem olhar a imagem. A régua da sessão gravada, o detector de faixas e a rede do item 4 são três lugares em que um número bonito pode estar medindo o instrumento — e a aula mostra, nos três, o número que denuncia.

## O que você sai sabendo hoje, e o que isso vale no seu projeto

| A capacidade | No seu projeto |
|---|---|
| gravar uma sessão, tocá-la sem o robô e tirar dela a tabela e a figura | a análise do item 2 roda no ônibus, sem robô, sem simulador e sem WSL2 esquentando |
| dizer **onde mora a decisão** de interromper, e ler o que a régua diz dela | é arquitetura, e é a pergunta certa da arguição |
| subir o MetaDrive, capturar quadros e dizer o que a cena tem e **não tem** | o item 3 deixa de depender de você ter uma câmera boa |
| ajustar um detector a uma câmera nova, e **declarar** o ajuste | o relatório explica o detector em vez de pedir desculpas por ele |
| treinar a mesma rede duas vezes e saber **qual número merece confiança** | a matriz de confusão é a frase que separa a rede que aprende da que decora |

## O que foi demonstrado, onde está na tarefa, e quando vence

As datas estão nesta tabela e em [Gates de cada TP](../../recursos/gates-tps.md) — elas são **referência para consultar**, não o assunto da aula.

| Bloco demonstrado | O que você faz em casa | Gate | Vence em |
|---|---|---|---|
| 1. Fechar o item 2: a interrupção e a sessão gravada | [passos 1 e 2](#passo-1-preparar-os-terminais-e-o-pacote-da-arvore) da tarefa | G4.3 · G4.4 | 12/11 · **15/11** |
| 2. A câmera sintética: MetaDrive, faixas e formas | [passos 3 e 4](#passo-3-o-metadrive-instalado-e-500-quadros-em-cinco-sementes) | G4.5 | 17/11 |
| 3. A rede que decora | [passos 5 e 6](#passo-5-rotular-com-revisao-contando-as-correcoes) | G4.6 | 19/11 |
| 4. A entrega do TP4, e a decisão do TP5 | [passos 7 e 8](#passo-7-o-relatorio-e-a-entrega) | G4.7 · G5.0 | 21/11 **até 12h** · **14/11** |

Repare na última linha: **a decisão do TP5 vence antes da entrega do TP4**. Não é erro de calendário — entre os dois TPs há poucos dias, e o TP5 tem de começar durante o TP4.

## Pegar o material

Este é o bloco que abre o seu trabalho em casa. Ele define as três variáveis da disciplina e copia três pastas para dentro do seu projeto: os dois exemplos de hoje e o da Aula 13, que tem de ficar **ao lado** deles — o `medir_faixas.py` importa o `faixas.py` de lá, e o `gerar_sintetico.py` importa o `cena_estrada.py`, os dois pelo caminho.

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
mkdir -p "$PB_WS/src"

sudo apt install -y python3-numpy python3-opencv python3-matplotlib

# a cópia antiga sai antes: cp -r sobre pasta existente ANINHA. A guarda é o
# próprio encadeamento com &&: se o clone falhar, nada é apagado. (Comentário
# DENTRO de uma cadeia `&& \` a quebraria — por isso ele está aqui em cima.)
cd /tmp && rm -rf pb-a17 && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a17 && \
  rm -rf "$PB_DIR/aula17-metadrive" "$PB_DIR/aula17-cnn" "$PB_DIR/aula13-veicular" && \
  cp -r pb-a17/exemplos/aula17-metadrive "$PB_DIR/" && \
  cp -r pb-a17/exemplos/aula17-cnn "$PB_DIR/" && \
  cp -r pb-a17/exemplos/aula13-veicular "$PB_DIR/"
```

Os dois ambientes Python — o do MetaDrive e o da rede — ficam em `$PB_DIR/.venv-metadrive` e `$PB_DIR/.venv-cnn`, **fora** das pastas dos exemplos, de propósito: este bloco apaga e recria as pastas, e um venv de 1 a 2 GB lá dentro iria junto. Eles são criados nos passos 3 e 6.

O item 2 usa o `aula16-arvore-bag`, baixado na semana passada. Se ele não estiver em `$PB_DIR`, o bloco de download está na [página da Aula 16](../etapa08-aula16/index.md#pegar-o-material).

!!! tip "A linha `: \"${PB_WS:?...}\"` que aparece nos blocos seguintes"
    Ela confere que as variáveis existem **neste** terminal. Um bloco que começa com ela supõe que o mesmo terminal já rodou um bloco que define as variáveis; um terminal novo começa sempre pelas três variáveis — e, se for chamar `ros2`, pelas duas linhas de `source` —, como no [passo 1](#passo-1-preparar-os-terminais-e-o-pacote-da-arvore) da tarefa.

!!! warning "O que rodou onde — leia antes de confiar em qualquer número"
    **Na nuvem** (um servidor Linux sem placa de vídeo, em 09/11): o MetaDrive inteiro, a captura, as faixas, as formas, a CNN nas quatro configurações. **Na minha máquina** (WSL2 com Ubuntu 22.04, no ensaio da véspera): a mesma receita, mais a camada ROS 2 do item 2 — o `vigia.py`, o `gravar_pose` e o `analise.launch.py` rodaram ali **pela primeira vez**. O MetaDrive rodou pelo WSLg, **sem Xvfb**, com a GPU, e umas vinte vezes mais rápido que na nuvem. **E as duas máquinas não deram os mesmos números**: as faixas mudaram com a renderização, e a rede, com a mesma semente, deu outra tabela. Onde a diferença importa, esta página dá os dois. **No WSL2 de vocês**: ninguém viu ainda — o número que vale é o da sua tela. Os READMEs dos exemplos separam, linha a linha, o que foi visto do que não foi.

---

## Bloco 1 — Fechar o item 2: a interrupção e a sessão gravada

**Pressupõe:** o Nav2 da Aula 15 e o pacote `aula16_arvore` compilados no seu workspace. **Para fazer: passos 1 e 2 da [tarefa](#a-tarefa-da-semana).**

### O sistema, e o vigia mandando o objetivo

No **Terminal A**, o sistema da semana passada, agora com a pose vinda do launch (`pose_inicial_auto:=true`): sem clique no RViz2, a sessão começa igual toda vez, e duas gravações passam a ser comparáveis. No **Terminal B**, o `vigia` — o caminho de cliente do item 2 — com um objetivo na sala 2, do outro lado da porta.

Foi dito em sala, e repito aqui: **o `vigia.py` nunca tinha rodado** antes do meu ensaio da véspera. Ele foi escrito sem ROS 2 na máquina, e o README do exemplo diz isso no topo. O que se viu em sala foi a primeira vez em público.

Duas coisas do exemplo que custam caro se ninguém avisar:

**Passe sempre o seu objetivo.** O padrão do `vigia` era `(9,0; 5,5)` até 09/11 — o mesmo ponto da rota padrão da Aula 15, dentro do retângulo da sala 2 (de 8,6 a 9,6 m em x, de 5,2 a 5,8 m em y) — e foi corrigido para `[10.5, 6.5, 1.57]`. Mesmo assim, passe o seu com `-p objetivo:=`, escolhido sobre o costmap global do **seu** mapa. Em sala foi `[9.0, 2.2, -1.57]`.

**No mundo mínimo da Aula 11, nada entra na frente do robô.** Ele é uma grade fixa: numa rota normal, nada chega a 0,5 m do leque frontal do laser — o batente da porta passa a uns 70 cm. Para o portão disparar em sala, **subi o limiar para 0,75 m** (`-p limiar_m:=0.75`) e mandei o robô pela porta. Isso é recurso da **demonstração**: a entrega do item 2 pede um disparo abaixo de 0,5 m, e o [passo 2](#passo-2-o-seu-bag-gravar-tocar-com-clock-e-a-regua-sobre-ele) diz como provocá-lo. O log do `vigia` mostra a sequência inteira — as linhas abaixo são as do meu ensaio; a distância exata depende da sua sessão:

```text
enviando objetivo (9.00, 2.20, -1.57)
obstaculo a 0.70 m (< 0.75 m): cancelando o objetivo
cancelamento aceito (1 goal em cancelamento); esperando 2.0 s
espera cumprida; retomando o MESMO objetivo
objetivo cumprido. 1 interrupcao(oes) no caminho.
```

Guarde esse atalho: daqui a pouco a régua vai cobrá-lo.

### A gravação, e a linha que não se corrige depois

No **Terminal C**, o `ros2 bag record` foi disparado **antes** de o `vigia` mandar o objetivo, e parado quando ele disse `objetivo cumprido`. A lista de tópicos é a do exemplo, com dois a mais que a da semana passada:

```text
/odom /amcl_pose /scan /cmd_vel /estado_vigia /dist_min /tf /tf_static
```

O `/estado_vigia` é o que registra **por que** o robô parou — sem ele, a figura não tem como marcar a interrupção. No `ros2 bag info` da gravação, o `/tf_static` aparece com **uma** mensagem: ela sai no instante em que o sistema sobe, e quem esquece o tópico na lista só descobre na reprodução, quando não há mais como regravar a sessão.

### Tocar sem o robô, e a régua

Com o sistema e o `vigia` derrubados, o **Terminal A** subiu o `analise.launch.py` — ele sobe **só** o `gravar_pose`, com `use_sim_time:=true` — e o **Terminal C** tocou o bag com `--clock`. Do lado de quem assina, o bag é indistinguível do robô: o `gravar_pose` não sabe que o sistema está desligado, e o CSV vai nascendo, uma linha por 0,1 s.

Depois, a mesma régua da sessão sintética sobre o CSV do bag, medindo com o limiar com que o `vigia` rodou (`--limiar 0.75`). E uma sessão como essa — um disparo só, com o laser acima de 0,5 m — ela não aprova. As frases do veredito estão no código do `medir_sessao.py`:

```text
VEREDITO
  1 evento(s) -- a sessao de referencia tem 2. Nao e erro, so nao e a mesma sessao.
  todas as esperas dentro de 2.00 s +- 0.25 s.
  olhe: o TP4 pede 0.50 m; esta sessao foi medida com --limiar 0.75 m, e o relatorio tem de dizer isso.
```

Sem o `--limiar`, ela mede com os 0,50 m do enunciado, declarados no topo do arquivo, e escreve `ATENCAO: em 1 evento(s) o /scan nao ficou abaixo de 0.50 m`. Nos dois casos, o portão disparou a 0,70 m, e a régua diz. **A régua não sabe quem está medindo, e é por isso que ela serve.** O `--limiar` existe para medir com o limiar que o `vigia` usou, e ele mesmo escreve a linha `olhe:`; o que não passa é mudar o `LIMIAR_OBSTACULO_M` do topo da régua para o veredito ficar bonito. Para a entrega, o caminho é outro: um disparo de verdade abaixo de 0,5 m.

E a régua também é código: no primeiro contato com o bag de verdade, a versão anterior contou **0** interrupções numa sessão que teve 1, porque o estado `interrompido` dura milissegundos e não chega ao CSV de 10 Hz. Foi corrigida antes desta aula — o [exemplo](../../exemplos/aula16-arvore-bag/index.md#o-que-e-um-evento-e-por-que-a-regua-errou-no-primeiro-ensaio) conta como. Se o seu material é anterior a 10/11, recopie.

!!! note "O que a sessão sintética já tinha ensinado, e vale para o seu bag"
    A régua roda sobre o CSV sintético sem ROS 2 nenhum (`simular_sessao.py` e `medir_sessao.py`, no [exemplo](../../exemplos/aula16-arvore-bag/index.md#medir-sem-ros-2-sem-nav2-e-sem-bag)), e a tabela dela tem três leituras que valem para qualquer bag. **Três distâncias:** 25,52 m mandados andar, 26,29 m somando o `/odom` (+3%, a deriva de escala) e **49,03 m** somando o `/amcl_pose` — o tremor virando caminho; não cite distância a partir do `/amcl_pose`. **O vão de 0,75 m** entre as duas trajetórias não é "erro do AMCL": é exatamente o que a transformada `map → odom` corrige. **As esperas de 2,00 s e 2,10 s** são diferentes de propósito, e a tolerância de ±0,25 s está declarada antes de medir.

### Esperar só resolve obstáculo que sai sozinho

Contra uma caixa parada, o `vigia` vira um laço — cancelar, esperar 2 s, retomar, cancelar de novo depois da carência de 1,5 s — e a régua escreve `REINCIDENCIA`. No mundo mínimo nada entra e sai da frente do robô; no Gazebo Fortress dá para criar e remover um modelo com a sessão rodando. Os dois mundos passam. O que conta é o relatório dizer **qual** foi usado e o que a régua leu.

**O item 2 no relatório, em cinco declarações:** em que mundo a sessão foi gravada (o mínimo da Aula 11 ou o Fortress); a árvore que você entrega e onde mora a decisão de interromper (num nó seu, ou num nó de árvore em C++); o limiar que disparou **de verdade**, lido na régua — e, na entrega, abaixo de 0,5 m; os tópicos gravados e o que ficou de fora; e a tabela e a figura saídas do **seu** bag, com a distância citada pela conta certa.

---

## Bloco 2 — A câmera sintética: o MetaDrive, as faixas e as formas

**Pressupõe:** nada no ar; o MetaDrive é um processo Python sem ROS 2. **Para fazer: passos 3 e 4 da [tarefa](#a-tarefa-da-semana).**

### A instalação que funcionou

O MetaDrive vai num venv próprio, criado com `uv`, com `--python 3.10` e `--system-site-packages`, e o pacote fixado em `metadrive-simulator==0.4.3`. O `--python 3.10` é obrigatório: o MetaDrive 0.4.3 depende do `panda3d==1.10.13`, que só tem wheel até o Python 3.11, e num 3.12 ou 3.13 o `uv` recusa com `has no wheels with a matching Python ABI tag`. O venv fica com uns **850 MB**, e na primeira execução o MetaDrive baixa sozinho mais uns 170 MB de modelos e texturas. O NumPy 2 e o OpenCV 5 que ele traz ficam **dentro** do venv: o `python3` do sistema, que o ROS 2 usa, continua com os do apt.

A conferência que o próprio pacote oferece, `verify_headless_installation --camera rgb`, é a que liga a câmera. **Sem servidor X ela falha com `AttributeError: 'NoneType' object has no attribute 'set_shader'`** — uma frase que não fala de tela nenhuma. No WSL2 o WSLg já fornece o X; num servidor sem tela, ou com o WSLg desligado, o remédio é o `xvfb-run`.

### A captura, e o que há na cena

O `capturar_frames.py` sobe o MetaDrive sem janela, deixa o piloto **IDM** do próprio simulador dirigir, e grava `quadroNNN.png` com um `estado.csv` ao lado. Duas coisas que o material da Aula 13 dizia errado, corrigidas: a imagem **já sai BGR**, a mesma ordem do OpenCV — não inverta nada —, e a observação tem **quatro** eixos, `(altura, largura, 3, pilha)`, porque o MetaDrive empilha quadros para aprendizado por reforço.

A velocidade depende de quem desenha. Na nuvem, sem placa de vídeo, com renderização por software, foram **0,37 quadros por segundo** — 500 quadros, uns **23 minutos**. Na minha máquina, com a GPU pelo WSLg, foram **7 a 9 quadros por segundo** — 500 quadros em 1 a 1,5 minuto. O seu número é um desses dois, ou outro: a primeira captura curta diz qual. A captura entra na tarefa, e não na aula, porque o que vale são os **seus** quadros.

**O MetaDrive não tem placa de trânsito**, e o mapa procedural não tem semáforo. O que há na cena são cones, um triângulo de advertência, uma barreira e veículos de cinco tamanhos. O enunciado do item 3 fala em "placas": a resposta honesta é trocar por **cone e veículo** e escrever no relatório que o MetaDrive não tem placa. E o piloto IDM mantém distância de quem está na frente — os 60 quadros da semente 7 saíram **54 via livre, 0 obstáculo, 6 cruzamento**. Esse número abre o bloco 3.

### Caso 1 — o detector da Aula 13, sem mudar nada

O primeiro caso ao vivo foi o `faixas.py` da Aula 13, inalterado, sobre um quadro do MetaDrive, com as quatro etapas gravadas:

```text
faixa_esq   : NAO ACHADA
faixa_dir   : NAO ACHADA
etapa 1 cor :      0 px na ROI  (esq 0 / dir 0 / longe 0 / amarelo 0)
etapa 2 bord:      0 px de borda
etapa 3 reta:   0 segmentos -> 0 esq + 0 dir, 0 recusados por inclinacao
```

**Zero pixels na máscara de cor.** Não é o Hough nem o Canny: é a primeira etapa, e as outras são eco dela. A tinta do MetaDrive chega no máximo a V = 149 no HSV, e o limiar branco da Aula 13 é 150 — um ponto de diferença. A faixa amarela tem 1 pixel de largura a 320×240, e a limpeza morfológica 3×3 a apaga. Nos 60 quadros completos, o detector da Aula 13 acha **zero** segmentos.

Depois, o `medir_faixas.py`: as **mesmas** funções do `faixas.py`, sem mudar uma linha, chamadas duas vezes — com a configuração da Aula 13 e com a **ajustada**, declarada no topo do arquivo antes de medir: ampliar o quadro 3×, branco a partir de V = 130, amarelo a partir de 70, Canny (20, 60). Nos 12 quadros da amostra, a ajustada acha as duas faixas em 11; nos 60 da nuvem, em **51**. Os quadros sem faixa são os do cruzamento: lá dentro não há tinta, e "não achei" é a resposta certa.

**Esses números dependem da renderização.** Nos 60 quadros que eu capturei com GPU, o mesmo código deu outra coisa: a configuração da Aula 13 achou a tracejada branca da direita em 51 quadros e a amarela da esquerda em nenhum, e a ajustada achou as duas em 52. A sua tabela é a dos **seus** quadros — meça antes de afirmar.

!!! danger "Limiar é da fonte de imagem, e se declara"
    O detector da Aula 13 não está errado: ele foi afinado numa cena, e nada viaja sozinho para outra. O relatório diz **qual configuração, para qual câmera e por quê**. E continua valendo o que a Aula 13 disse: sem verdade não há erro a medir — a tabela conta quantas vezes cada faixa foi achada, não se ela foi achada no lugar certo.

    A configuração ajustada foi escolhida a 320×240 com renderização por software. Com GPU a tinta sai mais clara — foi o que aconteceu na minha máquina —, e em outra resolução também pode mudar: rode a configuração da Aula 13 primeiro, olhe a máscara de cor, e só então mexa.

### Círculos e cantos

`HoughCircles` com `param2 = 30`: **zero círculos** — e é o número certo, porque não há placa. Baixando o limiar aparecem dezenas, a maioria **acima do horizonte**, no céu: falso positivo por construção, e a coluna "no céu" do `formas.py` existe para medir isso sem verdade nenhuma. O Harris acha de **30 a 180 cantos por quadro** — o limiar dele é relativo ao maior valor do quadro, e limiar relativo acha canto em qualquer imagem; os que importam são as quinas dos veículos, a base dos cones e a ponta de cada tracejado. Quem quiser provar que o detector de círculo funciona desenha a forma num quadro real, em posição conhecida, e exige achá-la. Baixar o `param2` até aparecer alguma coisa não é prova.

---

## Bloco 3 — A rede que decora

**Pressupõe:** nada no ar. **Para fazer: passos 5 e 6 da [tarefa](#a-tarefa-da-semana).**

### O problema começa no conjunto

Com o piloto IDM, a classe *obstáculo* **não aparece sozinha**: ela tem de ser provocada — mais tráfego (`--trafego`), mais sementes, e o relatório diz o que mudou. E uma semente é uma estrada: 500 quadros dela são 500 vistas do mesmo trecho, e a rede aprende o trecho. Por isso a tarefa captura **cinco sementes de cem quadros**.

Por esse mesmo motivo, os números deste bloco **não vêm do MetaDrive**: vêm de 500 imagens **sintéticas**, desenhadas pelo `gerar_sintetico.py` sobre a estrada da Aula 13, equilibradas em 167 / 167 / 166, com semente 7. Elas servem para aprender o caminho com três classes que existem. **O seu relatório usa os seus quadros do MetaDrive.**

### Rotular: a sugestão, a revisão, e o círculo vicioso

O `estado.csv` sugere um rótulo por **geometria do simulador**, não por visão: ele chama de cruzamento os metros *antes* do cruzamento e não vê o carro escondido atrás de uma curva. O `rotular.py` abre cada quadro com a sugestão ao lado, você confirma ou corrige pelo teclado, e no fim ele conta **quantos você corrigiu** — esse é o número que vai para o relatório. Zero correções em 500 quadros é suspeito, não é mérito.

E a tentação seguinte — revisar sessenta, treinar, e deixar a rede rotular os outros 440 — é **circular**: o rótulo é a resposta contra a qual a rede é medida. Se quem escreve a resposta é a rede, a matriz de confusão mede quanto ela concorda consigo mesma.

### O ambiente da rede, que é a exceção da disciplina

Em toda a disciplina o venv nasce com `--system-site-packages`, para enxergar o NumPy e o OpenCV do apt que o `cv_bridge` exige. **O da rede nasce sem.** O TensorFlow 2.21 traz o NumPy 2 dele; num venv que enxerga o sistema, basta um pacote compilado contra o NumPy 1 — o `cv2` ou o `matplotlib` do apt — ser importado ao lado para tudo morrer com `_ARRAY_API not found`, uma frase que não fala de versão. Sem enxergar o sistema, o mesmo esquecimento vira `No module named cv2`, que nomeia a causa. Este venv **nunca importa ROS 2**: lê PNG e CSV e grava PNG, JSON e `.keras`. A regra continua valendo para tudo o que fala com o ROS 2.

### As duas rodadas, e a tabela medida

A mesma rede — três blocos `Conv2D → BatchNormalization → ReLU → MaxPooling`, `Dropout(0.5)`, três saídas —, treinada duas vezes, 20 épocas cada: **sem** e **com** augmentation (rotação de ±15°, zoom de 0,2, espelho horizontal). Mesma divisão, mesmos pesos iniciais, mesma ordem dos lotes; a única diferença são as três camadas de augmentation. Uns 45 segundos por rodada na CPU de dois núcleos da nuvem; uns 23 na minha. A tabela abaixo é a da nuvem:

```text
linha de base: responder SEMPRE "via_livre" acerta 0.330 da validacao

rodada  acc_val  perda_val  acc_treino  melhor_acc_val(ep)  pior recall          acc_val_pert
sem       0.980      0.046       0.913       0.990 (10)     obstaculo   0.941         0.910
com       0.930      0.387       0.678       1.000 (19)     via_livre   0.788         0.940
```

**A mesma semente não deu a mesma tabela na minha máquina.** O mesmo código, os mesmos dados e a semente 7, em outra CPU e com o mesmo TensorFlow:

| | nuvem | minha máquina |
|---|---|---|
| `acc_val` sem / com | 0,980 / 0,930 | 0,980 / 0,850 |
| `acc_val_pert` sem / com | 0,910 / 0,940 | 0,880 / 0,940 |
| diferença (com − sem) na limpa | −0,050 | −0,130 |
| diferença (com − sem) na perturbada | +0,030 | +0,060 |

O número na sua tela é o seu. O que se sustenta nas duas máquinas é o **sinal** da diferença, não a terceira casa.

**O augmentation piorou a validação limpa** — cinco pontos numa máquina, treze na outra —, e isso não é defeito: a validação não tem imagem girada nem espelhada, e a tarefa sintética é fácil. A coluna `acc_val_pert` é a **mesma** validação passada uma vez por rotação, zoom e espelho — o tipo de variação que só a rodada `com` viu no treino —, e ali a ordem se inverte nas duas máquinas. É a direção que a teoria prevê, e são **três a seis imagens em cem**: escreve-se a direção e escreve-se que ela não basta. É também a resposta honesta ao "relate a melhoria de generalização" do enunciado: **a melhoria aparece na validação perturbada, não na limpa**. E a última época sozinha é frágil — a rodada `com` fez 1,000 na época 19 e 0,930 na 20 na nuvem; 0,960 na 19 e 0,850 na 20 na minha.

A matriz diz o que a acurácia esconde. Na nuvem, a rodada `sem` chama **dois obstáculos de via livre** — o erro perigoso. A `com` chama **sete vias livres de obstáculo** — o carro que freia à toa. Mesma ordem de grandeza na acurácia, comportamentos opostos no carro.

### Caso 2 — a BatchNormalization com o padrão do Keras

O segundo caso ao vivo foi a mesma rede com `--bn-momento 0.99`, que é o padrão do Keras:

```text
rodada  acc_val  acc_treino
sem       0.330       0.913

matriz sem (linha = verdade, coluna = previsto, via_livre / obstaculo / cruzamento)
  via_livre      33     0     0
  obstaculo      34     0     0
  cruzamento     33     0     0
```

O treino chega a 0,913 — **idêntico** ao da rodada sadia da mesma máquina, época a época — e a validação fica em 0,330, respondendo *via livre* para tudo (na nuvem e na minha máquina). A causa: no treino, a normalização usa a média e a variância **do lote**; na inferência, as **médias móveis**. Com 400 imagens em lotes de 32 são 260 passos em 20 épocas, e 0,99²⁶⁰ ≈ 0,07: 7% da variância móvel ainda é o valor inicial. Com `momentum=0.9`, 0,9²⁶⁰ ≈ 10⁻¹², e a validação vai a 0,98. **Se a sua curva de validação ficar colada em 1/3 — ou na fração da classe mais comum — enquanto a de treino sobe, é isto.** O `treinar.py` usa 0,9 por padrão.

### Caso 3 — 54 : 0 : 6, e a rede que nunca diz cruzamento

O terceiro caso ao vivo foi um conjunto com a proporção da amostra do MetaDrive — 450 via livre, 0 obstáculo, 50 cruzamento — e a mesma armadilha da normalização:

```text
linha de base: responder SEMPRE "via_livre" acerta 0.900 da validacao
sem       0.900   (treino 1.000)    pior recall: cruzamento 0.000

  via_livre      90     0     0
  obstaculo       0     0     0
  cruzamento     10     0     0
```

**Noventa por cento, igual à linha de base, e a coluna `cruzamento` toda em zero.** A rede nunca disse cruzamento. Quem olhar só a acurácia entrega isso como resultado; a única coisa da tabela que denuncia é a coluna da matriz.

E foi dito em sala, com a verdade: **com o momentum certo, a mesma rede faz 1,000 nesse conjunto** — o cruzamento sintético é fácil demais. Mas ela ensina outra coisa. Posta diante dos 167 obstáculos do conjunto equilibrado, ela chamou **157 de via livre e 10 de cruzamento**: zero obstáculos, porque não tem como responder uma classe que nunca viu — e a validação dela não tem como mostrar isso, porque também não tem obstáculo. Repetir os poucos exemplos raros cinquenta vezes não cria o que a câmera não viu: **capture mais**.

**A ordem de leitura da tabela, no relatório:** a contagem por classe, a linha de base, a acurácia — e a matriz por último, com mais peso. IoU, nuvem, trajetória, acurácia: quatro vezes no semestre a métrica mediu o instrumento.

---

## Bloco 4 — A entrega do TP4, e a decisão que abre o TP5

**Pressupõe:** nada. **Para fazer: passos 7 e 8 da [tarefa](#a-tarefa-da-semana).**

### O que o relatório declara, item por item

Cada uma destas frases saiu de um bloco de hoje, e cada uma é o que separa um relatório honesto de um que finge que tudo rodou:

| Item | O que se declara |
|---|---|
| 1 | o mundo em que você navegou — o mínimo da Aula 11 ou o Gazebo Fortress — e por quê |
| 2 | a **árvore** que você entrega (o XML, com a espera de 2 s) e o **nó que mede a distância** (o `vigia` ou um nó de condição em C++) — e por que, no Humble, a decisão ficou dividida entre os dois; um disparo **abaixo de 0,5 m**, lido pela régua no seu bag; os tópicos gravados e o que ficou de fora |
| 3 | a troca de "placa" por **cone e veículo**, com a frase de que o MetaDrive não tem placa; a configuração do detector **por fonte de imagem**, declarada antes de medir |
| 4 | quantos rótulos você **corrigiu**; a contagem por classe antes de treinar, e o que você fez para a classe rara aparecer; as duas rodadas **com a mesma semente**, a linha de base e a matriz; a comparação sem × com em `acc_val` **e** em `acc_val_pert`, e a frase sobre generalização — inclusive quando não houve melhoria |
| todos | o que rodou onde — e o que você não conseguiu rodar, dito como tal |

### A ordem da entrega

A mesma dos TPs anteriores: tudo na `main`, a branch `entrega-tp4` igual à `main`, a tag `tp4` empurrada, e o **Moodle** com o PDF do relatório, o ZIP do código e os links — a entrega oficial. Bag, vídeo e modelo vão por link público ou não listado, testado numa janela anônima. **O prazo do TP4 é ao meio-dia, não à meia-noite** — está na tabela do topo e em [Gates de cada TP](../../recursos/gates-tps.md).

### A decisão do TP5

O TP5 valida o projeto por um de dois caminhos: **A, hardware** — o robô de verdade percebendo e se movendo — ou **B, o drone PX4 simulado**, com missão de waypoints. A escolha vai **por escrito** para o `docs/decisoes.md`, com data e **com plano B declarado**: o que você faz se a opção escolhida travar. Se você não tem o hardware na mão esta semana, registre B como plano principal e A como plano B, não o contrário. A comparação entre as duas está em [Simulação × hardware real](../../recursos/simulado-vs-hardware.md).

---

## A tarefa da semana

**É aqui que a aula acontece para você.** Os nove passos abaixo são o que eu demonstrei, na ordem em que compensa fazer, para rodar no seu ambiente e no seu ritmo. Cada passo diz o que pressupõe, o que observar e o que fazer quando o observado não bater.

| | |
|---|---|
| **O que fazer** | o seu bag gravado, tocado sem o robô e medido pela régua, com a figura; 500 quadros do MetaDrive em cinco sementes, com as faixas e as formas sobre eles; os quadros rotulados com revisão; a mesma rede treinada duas vezes, com as curvas e a matriz; o relatório do TP4 com as declarações; e a decisão do TP5 registrada |
| **O que usar** | `vigia`, `gravar_pose`, `analise.launch.py`, `medir_sessao.py` e `plotar_trajetoria.py` (em `aula16-arvore-bag`); `capturar_frames.py`, `medir_faixas.py` e `formas.py` (em `aula17-metadrive`); `rotular.py`, `treinar.py` e `curvas.py` (em `aula17-cnn`); o `faixas.py` da `aula13-veicular` |
| **Como adequar ao seu projeto** | o objetivo do `vigia` sai do **seu** mapa; o mundo e o limiar que dispararam vão declarados; a configuração do detector é a da **sua** captura; os rótulos são **revisados por você**; a rede treina nos **seus** quadros, não no sintético |
| **Como saber que terminou** | o [passo 9](#passo-9-como-saber-que-terminou) |

São cinco terminais, sempre com o mesmo nome: **A — o sistema** (o launch ocupa o terminal), **B — o vigia** (depois, a régua), **C — o bag**, **D — o MetaDrive e as faixas**, e **E — a rede**. A, B e C chamam `ros2`: todo terminal novo desses começa pelas três variáveis e pelas duas linhas de `source`. D e E não chamam `ros2`: começam só pelas variáveis.

**Comece pelo passo 3.** A captura dos 500 quadros leva de um a dois minutos com GPU até uns 23 minutos com renderização por software, e roda sozinha: dispare-a no Terminal D e faça o passo 2 enquanto ela anda.

### Passo 1 — Preparar os terminais, e o pacote da árvore

**Pressupõe:** o material baixado ([Pegar o material](#pegar-o-material)), o Nav2 da Aula 15 e o `aula16-arvore-bag` em `$PB_DIR`.

**Terminal A — o sistema.** Terminal novo, nada precisa estar no ar:

```bash
# ── Terminal A: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 pkg list | grep -c aula15_nav2        # tem de ser 1
ros2 pkg list | grep -c aula16_arvore      # tem de ser 1
```

Se a segunda devolveu `0`, o pacote do `vigia` e do `gravar_pose` não está compilado neste workspace. As árvores vão para **dentro** do pacote antes do `colcon build` — o `setup.py` para com uma mensagem se não as achar. No mesmo Terminal A:

```bash
# ── Terminal A, só se aula16_arvore deu 0 ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
rm -rf "$PB_WS/src/aula16_arvore" && \
  cp -r "$PB_DIR/aula16-arvore-bag/aula16_arvore" "$PB_WS/src/" && \
  cp -r "$PB_DIR/aula16-arvore-bag/arvores" "$PB_WS/src/aula16_arvore/" && \
  cd "$PB_WS" && colcon build --symlink-install --packages-select aula16_arvore && \
  source install/setup.bash
```

Se a primeira deu `0`, é o pacote da Aula 15 — o passo 1 da [tarefa da Aula 16](../etapa08-aula16/index.md#passo-1-preparar-os-terminais) tem o `colcon build` dele.

### Passo 2 — O seu bag: gravar, tocar com `--clock`, e a régua sobre ele

**Pressupõe:** o passo 1, e a sua escolha de caminho para a interrupção (o passo 6 da semana passada). Os comandos abaixo são os do caminho de cliente, com o `vigia`; quem foi de C++ grava a mesma lista de tópicos com a sua árvore no ar. **Observe:** o log do `vigia`, a contagem do `/tf_static` no `bag info`, e o veredito da régua.

Escolha o objetivo **no seu mapa**, olhando o costmap global no RViz2: `[x, y, rumo]`. O padrão do `vigia` era `[9.0, 5.5, 1.57]` até 09/11 — um ponto **dentro** de um obstáculo do mundo da Aula 11, que o Nav2 recusa sem explicar; foi corrigido para `[10.5, 6.5, 1.57]`, e o mesmo ponto errado era o terceiro da rota padrão do `rota.py`. Se o seu material é anterior a 10/11, recopie.

**O que se entrega no item 2 é a árvore e o nó que mede a distância.** A árvore é o XML com a espera de 2 s — o `com_espera.xml` do exemplo é o ponto de partida, que você adapta —, e a sessão gravada para a entrega roda com ela: o parâmetro `arvore` do `vigia` recebe o caminho **instalado**. <!-- ARVORE-NAO-VERIFICADA -->Aviso honesto: esta árvore ainda não foi carregada num `bt_navigator` de verdade; se o Terminal A acusar erro ao receber o goal, poste no fórum as linhas do `bt_navigator` e grave sem o `-p arvore:=` enquanto isso.<!-- /ARVORE-NAO-VERIFICADA -->

**Terminal A — o sistema.** O launch ocupa o terminal até o `Ctrl+C`:

```bash
# ── Terminal A (o do passo 1, já com o source) ──
ros2 launch aula15_nav2 nav2.launch.py rviz:=true pose_inicial_auto:=true
```

**Terminal C — o bag.** Terminal novo, com o Terminal A no ar e a nuvem concentrada no RViz2. Comece a gravar **antes** de mandar o objetivo:

```bash
# ── Terminal C: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
mkdir -p "$PB_DIR/bags" && cd "$PB_DIR/bags" && rm -rf sessao-tp4
ros2 bag record -o sessao-tp4 /odom /amcl_pose /scan /cmd_vel \
  /estado_vigia /dist_min /tf /tf_static
```

**Terminal B — o vigia.** Terminal novo, com o A e o C no ar. Troque o objetivo pelo do seu mapa:

```bash
# ── Terminal B: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
source /opt/ros/humble/setup.bash
source "$PB_WS/install/setup.bash"
ros2 run aula16_arvore vigia --ros-args -p objetivo:="[9.0, 2.2, -1.57]" \
  -p arvore:="$PB_WS/install/aula16_arvore/share/aula16_arvore/arvores/com_espera.xml"
```

**O que você tem de ver:** `enviando objetivo`, as linhas `faltam N m`, e — se algo passar a menos de 0,5 m do leque frontal — `obstaculo a ... m: cancelando o objetivo`, `esperando 2.0 s`, `retomando o MESMO objetivo`. No fim, `objetivo cumprido. N interrupcao(oes) no caminho.` Aí, `Ctrl+C` no Terminal C, para fechar o bag.

**Se o primeiro goal terminar abortado** segundos depois do envio, logo depois de subir o sistema: aconteceu no meu ensaio, sem causa confirmada. Espere o Nav2 assentar (meio minuto depois de `Managed nodes are active`) e mande de novo.

**Se o portão nunca disparar:** no mundo mínimo, com um objetivo comum, é o esperado — nada entra na frente do robô. Subir o limiar, como eu fiz em sala, serve para **ver** o comportamento; a entrega pede um disparo **abaixo de 0,5 m**. Há dois jeitos: um objetivo rente a um obstáculo do seu mapa, que obrigue o robô a passar a menos de 0,5 m dele, ou um obstáculo posto na rota — no Gazebo Fortress, criado e removido com a sessão rodando, como na seção [Esperar só resolve obstáculo que sai sozinho](#esperar-so-resolve-obstaculo-que-sai-sozinho). O que você usou vai declarado no relatório, e a régua vai dizer o que aconteceu de verdade. **Se ele disparar em laço no mesmo lugar:** é a reincidência — obstáculo que não sai —, e a régua também vai acusar. **Se aparecer `goal RECUSADO`:** o objetivo está em célula ocupada ou inflada; escolha outro sobre o costmap global.

Com o bag fechado, a conferência. No Terminal C:

```bash
# ── Terminal C, depois do Ctrl+C no record ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/bags" && ros2 bag info sessao-tp4
mkdir -p "$PB_DIR/docs/evidencias/tp4" && ros2 bag info sessao-tp4 > "$PB_DIR/docs/evidencias/tp4/bag-info.txt"
```

**O que você tem de ver:** os oito tópicos, o `/tf_static` com `Count: 1`, e o `/estado_vigia` com uma contagem perto de 10 por segundo de gravação. Se o `/tf_static` não está na lista, regrave agora — depois não dá.

Agora, **tudo desligado**: `Ctrl+C` no Terminal B (o `vigia`) e no Terminal A (o sistema). Espere o prompt voltar no A. A reprodução usa dois terminais, nesta ordem.

**Terminal A — a análise.** O mesmo Terminal A, já com o `source`. O CSV sai na pasta de onde você roda o launch:

```bash
# ── Terminal A, com o sistema derrubado ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/bags" && ros2 launch aula16_arvore analise.launch.py saida:=sessao-tp4.csv
```

**Terminal C — tocar o bag.** Com o Terminal A no ar:

```bash
# ── Terminal C ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/bags" && ros2 bag play sessao-tp4 --clock
```

Quando o `play` terminar, `Ctrl+C` no Terminal A: o CSV já está completo, porque o `gravar_pose` grava linha a linha. **Se o CSV saiu só com o cabeçalho:** o `play` foi sem `--clock` (o nó espera um relógio que nunca chega, e não reclama), ou o `/amcl_pose` não está no bag.

**A régua e a figura.** No Terminal B (o do `vigia`, já com as variáveis):

```bash
# ── Terminal B, com o play terminado ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag"
python3 medir_sessao.py "$PB_DIR/bags/sessao-tp4.csv"
python3 plotar_trajetoria.py "$PB_DIR/bags/sessao-tp4.csv" --saida "$PB_DIR/docs/evidencias/tp4/trajetoria.png"
```

**Leia a tabela de cima para baixo**, e o veredito por último. Cite a distância pela integral do `cmd_v` ou pelo `/odom`, nunca pela soma do `/amcl_pose`. Chame o vão entre as trajetórias pelo nome — a correção da `map → odom`. E copie para o rascunho do relatório **as frases do veredito**, inclusive as que você preferia não ver: `ATENCAO`, `REINCIDENCIA` ou `ESPERA FORA DO ALVO` pedem uma declaração, não um bag novo.

### Passo 3 — O MetaDrive instalado, e 500 quadros em cinco sementes

**Pressupõe:** o material baixado. Nada no ar. **Observe:** a linha `Headless mode Offscreen render launched successfully!`, e a contagem de rótulos sugeridos por classe.

**Terminal D — o MetaDrive e as faixas.** Terminal novo; ele não chama `ros2`:

```bash
# ── Terminal D: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
cd "$PB_DIR"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
uv venv --python 3.10 --system-site-packages .venv-metadrive
uv pip install --python .venv-metadrive/bin/python "metadrive-simulator==0.4.3"
```

A conferência do próprio pacote, que liga a câmera. Rode-a de dentro da pasta do exemplo — uma pasta com uma subpasta chamada `metadrive` faria o `python -m` importar a pasta em vez do pacote. No mesmo Terminal D:

```bash
# ── Terminal D ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
"$PB_DIR/.venv-metadrive/bin/python" -m metadrive.examples.verify_headless_installation --camera rgb
```

**O que você tem de ver:** `Headless mode Offscreen render launched successfully!` — na primeira vez, depois do download de uns 170 MB de *assets*. **Se aparecer `'NoneType' object has no attribute 'set_shader'`:** não há servidor X. Confira o `echo $DISPLAY`; no WSL2 ele deveria valer `:0`, pelo WSLg. Se estiver vazio, o plano B é o Xvfb, que desenha na memória e roda em CPU. No Terminal D:

```bash
# ── Terminal D, só se deu o erro do set_shader ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
sudo apt install -y xvfb
cd "$PB_DIR/aula17-metadrive"
xvfb-run -a -s "-screen 0 1280x1024x24" "$PB_DIR/.venv-metadrive/bin/python" -m metadrive.examples.verify_headless_installation --camera rgb
```

Se você precisou do Xvfb, ponha `xvfb-run -a -s "-screen 0 1280x1024x24"` na frente de todo comando com o Python do `.venv-metadrive` daqui em diante. **Se aparecer `panda3d==1.10.13 has no wheels`:** o venv nasceu com outro Python; apague `$PB_DIR/.venv-metadrive` e recrie com o bloco acima.

**A captura.** Cinco sementes de cem quadros, cada uma na sua pasta. O tempo depende de quem desenha: na nuvem, com renderização por software, 0,37 quadros por segundo, uns 23 minutos para os 500; na minha máquina, com GPU pelo WSLg, 7 a 9 quadros por segundo, de um a dois minutos. Dispare e vá fazer o passo 2. No Terminal D:

```bash
# ── Terminal D ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
for s in 7 8 9 10 11; do "$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py --frames 100 --semente "$s" --saida "quadros-s$s"; done
```

**O que você tem de ver**, ao fim de cada semente: `forma da imagem : (240, 320, 3), uint8, canais BGR`, e `quadros gravados: 100`. **Se um episódio terminar antes dos cem quadros**, o carro bateu ou saiu da pista: o script avisa e grava o que tinha. Troque aquela semente por outra.

Depois, a contagem de rótulos sugeridos. No Terminal D:

```bash
# ── Terminal D, com a captura terminada ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
cut -d, -f14 quadros-s*/estado.csv | grep -v rotulo_sugerido | sort | uniq -c
```

**Se `obstaculo` saiu com zero ou quase**, é o piloto IDM mantendo distância — o esperado. Provoque a classe com mais tráfego, em sementes novas, e diga no relatório o que mudou. No Terminal D:

```bash
# ── Terminal D, só se faltou obstáculo ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
for s in 21 22; do "$PB_DIR/.venv-metadrive/bin/python" capturar_frames.py --frames 100 --semente "$s" --trafego 0.4 --saida "quadros-t$s"; done
```

Ninguém mediu quanto obstáculo esse tráfego rende: conte de novo, e decida com o número na mão.

### Passo 4 — As faixas com a configuração da sua câmera, e as formas

**Pressupõe:** o passo 3. **Observe:** a coluna PADRAO zerada, a AJUSTADA achando as duas, e a máscara de cor.

Primeiro, as duas configurações sobre os **seus** quadros. No Terminal D:

```bash
# ── Terminal D ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
python3 medir_faixas.py --pasta quadros-s7 --sobreposicao faixas-s7.png --quadro 20
```

**O que você tem de ver:** a coluna PADRAO (a da Aula 13) com zero segmentos, e a AJUSTADA com `E D` na maioria dos quadros fora do cruzamento. **Se a PADRAO achou alguma coisa**, a sua tinta saiu mais clara que a da nuvem — com GPU isso acontece: na minha máquina ela achou a faixa da direita em 51 de 60 quadros, e a da esquerda em nenhum. Não é problema: é informação, e vai para o relatório.

**As três etapas, que a evidência do item 3 pede.** O `faixas.py --etapas` grava a cor, a borda e a reta de um quadro — mas com a configuração da Aula 13, que no MetaDrive dá as três pretas. O caminho é uma cópia do `faixas.py` **no seu projeto**, com os três números ajustados, rodando sobre um quadro ampliado 3×. Os números abaixo são os do `medir_faixas.py`; troque-os pelos que a **sua** captura pedir. No Terminal D:

```bash
# ── Terminal D ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
mkdir -p "$PB_DIR/tp4" "$PB_DIR/docs/evidencias/tp4/veicular" && cd "$PB_DIR/tp4"
cp "$PB_DIR/aula13-veicular/faixas.py" faixas_metadrive.py
sed -i "s/'branco_v_min': 150,/'branco_v_min': 130,/; s/'amarelo_v_min': 110,/'amarelo_v_min': 70,/; s/'canny': (50, 150),/'canny': (20, 60),/" faixas_metadrive.py
grep -n "branco_v_min\|amarelo_v_min\|'canny'" faixas_metadrive.py | head -3
python3 -c "import cv2, sys; i = cv2.imread(sys.argv[1]); cv2.imwrite(sys.argv[2], cv2.resize(i, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))" "$PB_DIR/aula17-metadrive/quadros-s7/quadro020.png" quadro020x3.png
python3 faixas_metadrive.py --quadro quadro020x3.png --etapas "$PB_DIR/docs/evidencias/tp4/veicular"
```

**O que você tem de ver:** o `grep` mostrando 130, 70 e (20, 60); e as duas faixas achadas, com `1-cor.png`, `2-borda.png`, `3-reta.png` e `4-final.png` em `docs/evidencias/tp4/veicular/`. Sobre um quadro da amostra, na nuvem, isso deu 14 segmentos, 5 à esquerda e 9 à direita. Para ver a primeira etapa quebrando, rode o `faixas.py` original sobre o mesmo quadro, sem ampliar — a `1-cor.png` sai preta, e é a melhor figura da "discussão de falhas" que o item pede.

**As formas.** No Terminal D:

```bash
# ── Terminal D ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
python3 formas.py --pasta quadros-s7 --sobreposicao "$PB_DIR/docs/evidencias/tp4/veicular/formas.png" --quadro 20
python3 formas.py --pasta quadros-s7 --param2 15 | tail -2
```

**O que você tem de ver:** a primeira linha dizendo que o MetaDrive não tem placa; zero círculos com o limiar padrão; e, com `--param2 15`, círculos aparecendo — a maioria na coluna "no céu". Essas duas linhas, lado a lado, são a resposta do item 3 sobre formas.

!!! warning "Pasta de quadros é pasta só de quadros"
    O `faixas.py --pasta` lê **todo** PNG da pasta. Se você gravar uma sobreposição (uma figura com as faixas desenhadas por cima) na mesma pasta dos quadros, ela entra na conta e "acha" segmentos que ninguém detectou. Por isso as figuras do exemplo moram em `amostra/figuras/`, separadas — faça o mesmo com as suas.

### Passo 5 — Rotular com revisão, contando as correções

**Pressupõe:** o passo 3. **Observe:** a linha de progresso a cada tecla, e a última linha do `rotular.py`, com quantos você revisou e quantos diferem da sugestão.

O `rotular.py` roda com o `python3` **do sistema**, porque a janela precisa do OpenCV do apt. Uma pasta de cada vez; feche com `q` e ele grava — se reabrir na mesma pasta, continua do primeiro quadro que você ainda não revisou. No Terminal D:

```bash
# ── Terminal D ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
python3 rotular.py --pasta ../aula17-metadrive/quadros-s7
```

As teclas: **1 / 2 / 3** escolhem `via_livre` / `obstaculo` / `cruzamento` e avançam; **Enter** aceita o que está na tela; **setas** (ou **a** e **d**) andam sem mudar; **q** grava e sai. Elas valem **na janela ou no terminal** de onde você chamou o script, e cada rótulo imprime uma linha de progresso no terminal. Se uma tecla não fizer nada, o terminal imprime `tecla sem funcao: codigo N (0xHEX)` — anote o código e poste no fórum. Repita para `quadros-s8` a `quadros-s11` (e as `quadros-t*`, se você as capturou).

Depois, as correções de cada pasta. No Terminal D:

```bash
# ── Terminal D, com as pastas revisadas ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-metadrive"
for p in quadros-*/; do echo "$p $(awk -F, 'NR>1 && $2!=$3' "$p/rotulos.csv" | wc -l) corrigidos de $(awk -F, 'NR>1 && $4==1' "$p/rotulos.csv" | wc -l) revisados"; done
```

Esse número vai para o relatório. A coluna `revisado` do `rotulos.csv` vale 1 só nos quadros em que você apertou 1/2/3 ou Enter: "de N revisados" conta o que você olhou, não o que a pasta tem. **Se a janela não abrir ou não responder** (WSLg desligado, `echo $DISPLAY` vazio), o `--sem-janela` faz a mesma revisão só pelo terminal, com as mesmas teclas — abra o PNG num visualizador ao lado. No Terminal D:

```bash
# ── Terminal D, só se a janela não abriu ou não respondeu ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
python3 rotular.py --pasta ../aula17-metadrive/quadros-s7 --sem-janela
``` **Não deixe a rede rotular os quadros**: o rótulo é a resposta contra a qual ela será medida.

### Passo 6 — A rede: as duas rodadas com a mesma semente, as curvas e a matriz

**Pressupõe:** o passo 5. **Observe:** a contagem por classe e a linha de base, antes da acurácia; e a matriz, por último e com mais peso.

**Terminal E — a rede.** Terminal novo; ele não chama `ros2`. O venv nasce **sem** `--system-site-packages` — é a exceção da disciplina, e o [bloco 3](#o-ambiente-da-rede-que-e-a-excecao-da-disciplina) diz por quê:

```bash
# ── Terminal E: uma vez por terminal ──────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
cd "$PB_DIR"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
uv venv --python 3.10 .venv-cnn
uv pip install --python .venv-cnn/bin/python tensorflow-cpu opencv-python-headless matplotlib scikit-learn
"$PB_DIR/.venv-cnn/bin/python" -c "import tensorflow as tf, keras, numpy, cv2; print(tf.__version__, keras.__version__, numpy.__version__, cv2.__version__)"
```

**O que você tem de ver**, depois de umas linhas de `oneDNN` (informação, não erro): `2.21.0 3.12.4 2.2.6 5.0.0`, ou versões vizinhas. **Se a instalação parar no download do `tensorflow-cpu`** (são 261 MB), interrompa com `Ctrl+C` e repita a linha: o `uv` aproveita o que já baixou.

**Primeiro, o sintético, para conferir o caminho.** A sua tabela **não** vai sair igual à da aula: com a mesma semente, a nuvem deu 0,980 / 0,930 na validação limpa e a minha máquina, 0,980 / 0,850. O que confere o caminho é o sinal: a rodada `com` abaixo da `sem` na `acc_val`, e acima na `acc_val_pert`. Anote os seus números. Uns três minutos. No Terminal E:

```bash
# ── Terminal E ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" gerar_sintetico.py --saida sintetico
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta sintetico --saida resultado
"$PB_DIR/.venv-cnn/bin/python" curvas.py --pasta resultado --saida resultado/curvas.png
```

**Agora, os seus quadros.** O `--pasta` aceita várias; a divisão treino/validação é feita uma vez, sobre o conjunto inteiro, e as duas rodadas usam a mesma semente. Acrescente as `quadros-t*` à lista se você as capturou. No Terminal E:

```bash
# ── Terminal E ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta ../aula17-metadrive/quadros-s7 ../aula17-metadrive/quadros-s8 ../aula17-metadrive/quadros-s9 ../aula17-metadrive/quadros-s10 ../aula17-metadrive/quadros-s11 --saida resultado-metadrive
"$PB_DIR/.venv-cnn/bin/python" curvas.py --pasta resultado-metadrive --saida resultado-metadrive/curvas.png
cp resultado-metadrive/matriz_sem.png "$PB_DIR/docs/evidencias/tp4/matriz-confusao.png"
cp resultado-metadrive/curvas.png "$PB_DIR/docs/evidencias/tp4/curvas-augmentation.png"
```

**Leia o `resultado-metadrive/tabela.txt` na ordem certa:** a contagem por classe, a linha de base, a acurácia das duas rodadas, o pior recall e a matriz. Nenhum número da aula vale para os seus quadros — o MetaDrive tem céu, terreno e faixas finas, e o seu relatório é o primeiro lugar em que essa rede vai ser medida.

**A comparação que o enunciado pede** ("relate a melhoria de generalização") vai para o relatório com os seus números: a `acc_val` sem × com, a `acc_val_pert` sem × com, a diferença em imagens, e uma frase sobre generalização — **inclusive quando não houve melhoria**. "Na validação limpa o augmentation perdeu N pontos; na perturbada ganhou M; são K imagens em 100, a direção e não uma conclusão" é uma resposta completa. "Não melhorou" também é, se vier com os números.

**O que fazer quando o observado não bater:**

- **A validação colada num valor só** — 1/3, ou a fração da classe mais comum — com o treino subindo: é a armadilha da normalização. O padrão do `treinar.py` é 0,9; confira que ninguém passou `--bn-momento 0.99`.
- **Acurácia alta e uma coluna inteira da matriz em zero:** a rede decora a classe dominante. Compare a acurácia com a linha de base que a própria tabela imprime. O remédio é capturar mais da classe rara (passo 3), não mais épocas.
- **Recall `n/a` e uma linha de zeros:** a classe não está na validação — e, se também não está no treino, a rede nunca vai respondê-la.
- **A rede não aprende nos seus quadros:** mude **uma** coisa de cada vez e diga qual — mais épocas (`--epocas 40`), depois mais resolução (`--tamanho 160x120`) —, sempre com a mesma semente nas duas rodadas.

!!! note "A evidência do item 4 que a tabela de gates lista é um notebook"
    Em [Gates de cada TP](../../recursos/gates-tps.md), o G4.6 pede um **notebook executado de ponta a ponta** (`notebooks/tp4_cnn.ipynb`) e a matriz em `docs/evidencias/tp4/matriz-confusao.png`. Os scripts deste exemplo são o caminho; o notebook pode chamá-los célula a célula e mostrar a tabela, as curvas e a matriz. O Jupyter **não** está na linha de instalação do venv da rede, e instalá-lo nele (`uv pip install --python .venv-cnn/bin/python jupyter`) **não foi testado** nesta disciplina. Se travar, poste no fórum antes de perder a noite.

### Passo 7 — O relatório e a entrega

**Pressupõe:** os passos 2 a 6.

Escreva as declarações do [bloco 4](#o-que-o-relatorio-declara-item-por-item), item por item, com os números que **você** mediu. Depois, a entrega, na ordem de sempre — a mesma do [Git — fluxo e tags](../../cheatsheets/git-cheatsheet.md). Bag, vídeo e modelo vão por link, testado numa janela anônima. No seu repositório, em qualquer terminal:

```bash
# ── qualquer terminal, com tudo commitado na dev ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
git checkout main && git merge dev && git push
git checkout entrega-tp4 && git merge --ff-only main && git push
git tag tp4 && git push origin tp4
git checkout dev
git tag --list | grep tp4
```

E depois, **no Moodle**: o PDF do relatório, o ZIP do código e os links. A postagem no Moodle é a entrega oficial; o repositório é critério de avaliação, não anexo. **O prazo do TP4 é ao meio-dia** — confira a data na tabela do topo.

### Passo 8 — A decisão do TP5, registrada

**Pressupõe:** nada. **Observe:** o plano B escrito.

Acrescente uma entrada ao seu `docs/decisoes.md`, no formato do [manual do aluno](../../tutoriais/manual-do-aluno-github.md) — data, o que mudou, onde, por quê, impacto —, mais o **plano B**. Um exemplo, para a opção B:

```markdown
## 2026-11-12 — TP5: opção B (drone PX4 simulado)

- **O que mudou:** o TP5 será validado em simulação, com missão de waypoints do drone PX4.
- **Onde:** `docs/decisoes.md`; o plano do TP5 em `PROJETO.md`.
- **Por quê:** não tenho Raspberry Pi; o projeto é simulado desde o TP3.
- **Plano B:** se o PX4 não subir até o fim da semana, ...
- **Impacto:** ...
```

Commit e push na `dev`, como qualquer outra mudança. A data do registro é a do commit — e o gate dela vence **antes** da entrega do TP4.

### Passo 9 — Como saber que terminou

Em qualquer terminal com as variáveis:

```bash
# ── qualquer terminal ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula16-arvore-bag" && python3 medir_sessao.py "$PB_DIR/bags/sessao-tp4.csv" | tail -5
wc -l "$PB_DIR"/aula17-metadrive/quadros-s*/estado.csv
cat "$PB_DIR/aula17-cnn/resultado-metadrive/tabela.txt"
ls "$PB_DIR/docs/evidencias/tp4" "$PB_DIR/docs/evidencias/tp4/veicular"
grep -n "TP5" "$PB_DIR/docs/decisoes.md"
```

Você terminou quando tem, nesta ordem:

1. o bag com o `/tf_static` e o `/estado_vigia`, o `bag-info.txt`, a tabela da régua e a `trajetoria.png` — e as frases do veredito copiadas para o relatório, inclusive as incômodas;
2. 500 quadros do MetaDrive em pelo menos cinco sementes — cada `estado.csv` com 101 linhas, o cabeçalho e cem quadros;
3. as quatro etapas das faixas com a configuração da **sua** captura, e a figura das formas, em `docs/evidencias/tp4/veicular/`;
4. os `rotulos.csv` revisados, com o número de correções de cada pasta;
5. a tabela das duas rodadas sobre os **seus** quadros, as curvas e a matriz em `docs/evidencias/tp4/matriz-confusao.png`;
6. o relatório com as declarações de cada item;
7. a decisão do TP5 no `docs/decisoes.md`, com plano B.

Travou num passo e o observado não bate com nada desta página? Os socorros dos exemplos — [MetaDrive](../../exemplos/aula17-metadrive/index.md#socorro-rapido), [CNN](../../exemplos/aula17-cnn/index.md#socorro-rapido), [árvore e sessão](../../exemplos/aula16-arvore-bag/index.md#socorro-rapido) — cobrem os sintomas que já apareceram. Se não estiver lá, poste no fórum do Moodle a saída do comando e o passo em que você está.

## Desafio — qual coluna denuncia?

Opcional, e responde-se medindo. **Pressupõe:** o passo 6, com o sintético já treinado.

Mude **uma** coisa e treine de novo, numa pasta de saída à parte. Por exemplo, reproduza a armadilha da normalização. No Terminal E:

```bash
# ── Terminal E ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula17-cnn"
"$PB_DIR/.venv-cnn/bin/python" treinar.py --pasta sintetico --bn-momento 0.99 --saida resultado-bn099
"$PB_DIR/.venv-cnn/bin/python" curvas.py --pasta resultado-bn099 --saida resultado-bn099/curvas.png
```

Ou rode as duas rodadas com outra semente (`--semente 11`, com `--saida resultado-s11`) e veja se a ordem da validação perturbada — `sem` abaixo de `com` — se mantém. A pergunta é a mesma da semana passada: **qual coluna da tabela denuncia a mudança, e qual fica igual?**

A resposta cabe numa frase, e vale mais no relatório do que mais uma época de treino — é ela que mostra que você sabe ler a sua própria tabela.

## Para a próxima aula

**A Aula 18 é a aterrissagem do TP4**: o enunciado lido item por item, com os repositórios de vocês do lado — o que cada item pede, o que a evidência precisa mostrar, e o que costuma faltar. Tragam o **bag medido**, os **quadros rotulados**, a **tabela das duas rodadas** e a **decisão do TP5** escrita. As datas estão na [tabela](#o-que-foi-demonstrado-onde-esta-na-tarefa-e-quando-vence) e em [Gates de cada TP](../../recursos/gates-tps.md).
