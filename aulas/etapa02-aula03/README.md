# Aula 3 — Comunicação e visão computacional

**Terça, 04/08/2026 · 07h00–09h30 · sala SJ205 · Etapa 2 (03/08–15/08)**

[:material-file-pdf-box: Slides da Aula 3 (PDF)](apresentacao-aula03.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula03-visao`](../../exemplos/aula03-visao/index.md){ .md-button }
[:material-clipboard-check: Tarefa da semana](../../tutoriais/tarefa-aula03-visao.md){ .md-button }

## A ideia da aula em uma frase

**Hoje o tópico deixa de carregar texto e passa a carregar imagem.** Tudo o que você aprendeu na Aula 2 continua valendo — publisher, subscriber, serviço, launch —; o que muda é o tipo da mensagem e, com ele, um conjunto de preocupações novas: taxa, latência, perda de quadro, conversão entre formatos e política de entrega. É a diferença entre uma conversa e um fluxo.

Ao fim da aula você terá rodando o pipeline `câmera → segmentação → contagem → serviço`, que é **literalmente** o esqueleto dos itens 3 e 4 do TP1.

## Objetivos

Ao final da aula você deve conseguir publicar imagem em um tópico ROS 2 e explicar por que a QoS de sensor é diferente da QoS padrão; converter entre `sensor_msgs/Image` e a matriz do OpenCV nos dois sentidos, com e sem `cv_bridge`; segmentar um objeto por cor em HSV e justificar por que HSV e não BGR; contar ocorrências com contornos e filtro de área; expor o resultado por um serviço; e ajustar todo o comportamento por parâmetro, sem editar código.

Fora do teclado, você deve sair da aula com **três decisões de projeto tomadas**: a derivação de aplicação que vai seguir, a trilha (simulada, híbrida ou real) e os gates do TP1 marcados no seu `PROJETO.md`.

## Roteiro do encontro

| Horário | Bloco | O que acontece |
|---|---|---|
| 07h00–07h15 | Retomada e checagem | pendências de ambiente, `check-ambiente.sh`, quem ainda não tem repositório de pé |
| 07h15–08h00 | Imagem no grafo | `sensor_msgs/Image`, QoS de sensor, `cv_bridge` e o plano B; demo do exemplo rodando |
| 08h00–08h20 | Visão: HSV e contornos | por que HSV, o problema do vermelho, morfologia, filtro de área, oclusão |
| 08h20–09h00 | Mão na massa | rodar o exemplo, trocar a cor por parâmetro, adaptar ao objeto do próprio projeto |
| 09h00–09h30 | Bloco de projeto | derivações, simulação × hardware, gates do TP1, mentoria individual |

## Parte 1 — Imagem viajando no grafo

### O tipo `sensor_msgs/Image`

Uma imagem em ROS 2 é uma mensagem com cabeçalho (carimbo de tempo e `frame_id`), dimensões, um `encoding` que descreve o formato dos bytes (`bgr8`, `rgb8`, `mono8`), o `step` — quantos bytes tem uma linha — e o vetor `data` com os pixels. Não há mágica: é a matriz do OpenCV serializada, mais os metadados necessários para quem recebe saber como interpretá-la.

```bash
ros2 interface show sensor_msgs/msg/Image
```

O carimbo de tempo no cabeçalho parece detalhe e não é: no TP3 ele é o que permite ao TF associar a imagem à pose do robô no instante da captura. Comece a preenchê-lo agora, mesmo sem usar.

### QoS: por que a configuração padrão está errada para câmera

A QoS padrão do ROS 2 é confiável (`RELIABLE`) com histórico de dez mensagens. Para um sensor de imagem isso é a escolha errada, e a razão é prática: se um quadro se perde, **retransmitir é pior do que descartar** — quando ele chegar, já estará velho, e a fila acumulada só aumenta a latência. Por isso o perfil de sensor usa `BEST_EFFORT` com `KEEP_LAST` e profundidade 1: sempre o quadro mais recente, nunca uma fila de quadros vencidos.

Há uma consequência que morde na hora: publisher e subscriber precisam de perfis **compatíveis**. Um publisher `BEST_EFFORT` com um subscriber `RELIABLE` simplesmente não se conectam, e o sintoma é cruel — `ros2 topic list` mostra o tópico, `ros2 node info` mostra os dois nós, e nada chega. Quando "o tópico existe mas não chega nada", suspeite de QoS antes de qualquer outra coisa:

```bash
ros2 topic info /camera/image_raw --verbose
```

### `cv_bridge` — e o que fazer quando ele não está instalado

O `cv_bridge` faz a ponte entre `sensor_msgs/Image` e o `numpy.ndarray` do OpenCV. É a forma canônica e é o que você deve usar. Acontece que ele é um pacote à parte (`ros-humble-cv-bridge`) e, em algumas instalações, não veio junto — e um pacote faltando não pode travar a turma inteira.

Por isso o exemplo da aula tem um módulo `ponte.py` que tenta importar o `cv_bridge` e, se não encontrar, monta a mensagem à mão. A conversão manual não tem segredo, e vale entender: `bgr8` significa três bytes por pixel na ordem azul-verde-vermelho, `step` é `largura * 3`, e o corpo é o array contíguo em bytes. Saber fazer isso na mão é o que separa quem usa a biblioteca de quem entende o que ela faz.

## Parte 2 — Segmentação por cor

### Por que HSV e não BGR

Em BGR, "vermelho" não é uma região compacta: um vermelho iluminado e um vermelho na sombra têm valores completamente diferentes nos três canais, porque **brilho e cor estão misturados**. O espaço HSV separa isso em matiz (que cor), saturação (quão pura) e valor (quão clara). Assim a regra "é vermelho" vira uma faixa estreita em H, e as variações de iluminação viram variações em V, que você tolera com um limiar frouxo.

No OpenCV, H vai de 0 a 179 — metade do círculo de 360°, para caber em um byte. Isso cria a pegadinha do vermelho: ele fica **nas duas pontas** do intervalo, perto de 0 e perto de 179. Segmentar vermelho exige duas máscaras somadas; azul, verde e amarelo vivem no meio e precisam de uma só. É a primeira armadilha de visão que quase todo mundo encontra, e agora você já a conhece.

### Máscara, morfologia e contagem

O caminho é sempre o mesmo. Converta para HSV, gere a máscara binária com `inRange`, limpe a máscara com morfologia — `OPEN` remove pontos isolados de ruído, `CLOSE` fecha buracos dentro do objeto —, extraia contornos com `findContours` em modo `RETR_EXTERNAL` e descarte os contornos de área pequena. O que sobrou é a sua contagem.

O **filtro de área é o parâmetro mais útil de todos** e o mais subestimado: ele sozinho elimina a maior parte dos falsos positivos, e é a primeira coisa a ajustar quando a contagem oscila.

### O experimento da oclusão

O exemplo desenha dois círculos vermelhos que, em alguns quadros, se sobrepõem. Quando isso acontece a contagem cai de 2 para 1, e **isso não é um defeito do exemplo** — é oclusão, o problema número um de qualquer sistema de percepção real. Reproduza, registre com print e discuta no relatório do TP1: por que acontece, e o que você faria a respeito (área máxima além da mínima, rastreamento entre quadros, `watershed`, ou um detector por aparência no TP2). Um parágrafo honesto sobre isso vale mais do que um pipeline que finge que o problema não existe.

## Parte 3 — Mão na massa

```bash
cp -r aula03-visao/aula03_visao ~/SEU-REPO/ros2_ws/src/
cd ~/SEU-REPO/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch aula03_visao visao.launch.py          # fonte sintética: não precisa de webcam
ros2 topic echo /vision/contagem                  # em outro terminal
ros2 service call /vision/status std_srvs/srv/Trigger "{}"
```

A fonte padrão é **sintética**: a cena é desenhada em código, então o exemplo funciona sem webcam, sem `usbipd` e sem driver. Quem já tiver a câmera passada para o WSL2 roda com `fonte:=webcam`; quem tiver um vídeo gravado usa `fonte:=video`. E se a webcam falhar ao abrir, o nó cai sozinho para a fonte sintética em vez de morrer — que é o comportamento que você também quer no seu projeto.

Depois de rodar, o exercício que importa é este: **troque a cor sem tocar no código.**

```bash
ros2 param set /segmentador_hsv h_min 100
ros2 param set /segmentador_hsv h_max 130     # agora ele caça azul
ros2 param set /segmentador_hsv area_min 1200.0
```

Configuração em YAML e parâmetro em vez de constante no código é exatamente o que o TP2 vai cobrar. Comece o hábito hoje, enquanto é barato.

## Parte 4 — Bloco de projeto (09h00–09h30)

Este bloco não é "sobra de aula": ele decide o semestre. Três documentos novos entram em vigor hoje.

**[Derivações e aplicações](../../recursos/derivacoes-projetos.md)** mostra que o núcleo técnico é quase sempre o mesmo — `sensor → percepção → representação → decisão → navegação → evidência` — e que o que muda entre um projeto e outro é o domínio. Isso libera você a escolher uma aplicação que realmente te interessa, sem aumentar o risco técnico. São cinco derivações para cada uma das sete famílias do catálogo, mais uma tabela de troca de setor.

**[Simulação × hardware real](../../recursos/simulado-vs-hardware.md)** explicita a régua da disciplina, e ela é assimétrica de propósito: quem simula tem o ambiente sob controle, então a expectativa de **complexidade e eficácia é maior**; quem coloca hardware real no circuito gasta boa parte do esforço em problemas que a simulação não tem, e isso é reconhecido mesmo com resultado final mais modesto. A recomendação padrão é a trilha **híbrida**: núcleo simulado com **um** elemento real — a webcam já basta para trazer ruído, iluminação e latência de verdade.

**[Gates de cada TP](../../recursos/gates-tps.md)** transforma cada TP em uma sequência de checkpoints verificáveis por comando, com data e com evidência commitada. Copie o bloco do TP1 para o seu `PROJETO.md` hoje e faça **um commit por gate**.

!!! warning "O gate mais urgente é o G1.1, e vence em 11/08"
    Declarar domínio, usuário, classes percebidas, trilha e plano B. Sem isso o G1.3 não tem o que detectar, e você gasta duas semanas afinando HSV de um cubo vermelho genérico que não vai para lugar nenhum. A leitura oficial do TP1 é na Aula 4, em 11/08 — chegue lá com o projeto já escolhido.

## Tarefa da semana

[Tarefa da Aula 3 — pipeline de visão do seu projeto](../../tutoriais/tarefa-aula03-visao.md): adaptar o exemplo ao objeto do seu projeto, medir a taxa real do tópico, expor o `/vision/status` com informação do seu domínio e registrar as evidências. Opcional, para quem quer ir além: [Desafio 2 — visão](../../recursos/desafios/desafio-02-visao.md).

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| tópico existe, `echo` não mostra nada | QoS incompatível (`BEST_EFFORT` × `RELIABLE`) — confira com `ros2 topic info --verbose` |
| `ModuleNotFoundError: cv_bridge` | pacote ausente; o exemplo cai no modo manual sozinho, ou instale `ros-humble-cv-bridge` |
| janela do `rqt_image_view` não abre | WSLg desatualizado — `wsl --update` e reabra o terminal |
| webcam não abre no WSL2 | falta o `usbipd attach` — ver [tutorial da câmera](../../tutoriais/camera-wsl2-usbipd.md); enquanto isso, `fonte:=sintetico` |
| vermelho quase não é detectado | faltou a segunda faixa de matiz (170–180); vermelho ocupa as duas pontas do círculo |
| contagem oscilando muito | `area_min` baixo demais, ou falta morfologia `OPEN` |
| taxa muito baixa | resolução alta demais; comece em 640×480 |

## Para a próxima aula (11/08)

Leitura oficial do TP1 e mentoria de projeto. Chegue com o `PROJETO.md` preenchido — domínio, classes, trilha e plano B —, com o pipeline da tarefa rodando sobre o **seu** objeto e com os gates do TP1 marcados. A Aula 4 rende muito mais para quem chega com uma pergunta específica do que para quem chega com o projeto ainda em branco.
