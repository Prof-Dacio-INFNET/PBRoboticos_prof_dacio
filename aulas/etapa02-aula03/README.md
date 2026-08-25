# Aula 3 — Comunicação e visão computacional

**Terça, 04/08/2026 · sala SJ205 · Etapa 2 (03/08–15/08)**

[:material-file-pdf-box: Slides da Aula 3 (PDF)](apresentacao-aula03.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula03-visao`](../../exemplos/aula03-visao/index.md){ .md-button }
[:material-clipboard-check: Tarefa da semana](../../tutoriais/tarefa-aula03-visao.md){ .md-button }

## A ideia da aula em uma frase

**Hoje o tópico deixa de carregar texto e passa a carregar imagem.** Tudo o que você aprendeu na Aula 2 continua valendo — publisher, subscriber, serviço, launch —; o que muda é o tipo da mensagem e, com ele, um conjunto de preocupações novas: taxa, latência, perda de quadro, conversão entre formatos e política de entrega. É a diferença entre uma conversa e um fluxo.

Ao fim da aula você terá rodando o pipeline `câmera → segmentação → contagem → serviço`, que é **literalmente** o esqueleto dos itens 3 e 4 do TP1.

## Objetivos

Ao final da aula você deve conseguir publicar imagem em um tópico ROS 2 e explicar por que a QoS de sensor é diferente da QoS padrão; converter entre `sensor_msgs/Image` e a matriz do OpenCV nos dois sentidos, com e sem `cv_bridge`; segmentar um objeto por cor em HSV e justificar por que HSV e não BGR; contar ocorrências com contornos e filtro de área; expor o resultado por um serviço; e ajustar todo o comportamento por parâmetro, sem editar código.

Fora do teclado, você deve sair da aula com **três decisões de projeto tomadas**: a derivação de aplicação que vai seguir, a trilha (simulada, híbrida ou real) e os gates do TP1 marcados no seu `PROJETO.md`.

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

### `cv_bridge` — e o que fazer quando ele não coopera

O `cv_bridge` faz a ponte entre `sensor_msgs/Image` e o `numpy.ndarray` do OpenCV. É a forma canônica e é o que você deve usar. Acontece que ele é um pacote à parte (`ros-humble-cv-bridge`) e falha de duas maneiras bem diferentes: às vezes **não está instalado** (`ModuleNotFoundError`), e às vezes está instalado, importa sem reclamar e **quebra na primeira conversão**, com um `KeyError: 16` que não parece ter relação nenhuma com o que você fez.

Por isso o exemplo da aula tem um módulo `ponte.py` que, no import, faz um **round-trip de teste** — converte uma imagem minúscula ida e volta. Se qualquer coisa falhar, ele monta a mensagem à mão e segue. Você vê qual dos dois modos está valendo na linha de log do publicador: `cv_bridge=sim (round-trip conferido no import)` ou `cv_bridge=nao, conversão manual bgr8 | motivo: …`. **Os dois estão certos** e a tarefa vale igual nos dois.

A conversão manual não tem segredo, e vale entender: `bgr8` significa três bytes por pixel na ordem azul-verde-vermelho, `step` é `largura * 3`, e o corpo é o array contíguo em bytes. Saber fazer isso na mão é o que separa quem usa a biblioteca de quem entende o que ela faz.

!!! warning "O `KeyError: 16` e a lição que ele ensina — leia antes de instalar qualquer coisa"
    O `cv_bridge` do `apt` é compilado contra o **OpenCV 4.5.4** e o **NumPy 1.x** que vêm do `apt`. Se você rodar `pip install opencv-python` ou `pip install numpy` **fora de um venv**, o pip instala versões novas em `~/.local`, que têm precedência no `python3` do sistema — e o `cv_bridge` passa a falar com uma biblioteca que não é a que ele conhece. O sintoma é um `KeyError: 16` na primeira conversão de imagem.

    Duas caras do mesmo problema, e dá para distinguir pela mensagem: se antes do erro aparecer `AttributeError: _ARRAY_API not found`, é **NumPy 2**; se não aparecer nada de NumPy, é **OpenCV 5** (a versão 5 renumerou as constantes de tipo). A cura é a mesma nos dois casos:

    ```bash
    # confira de onde vêm — o esperado é /usr/lib/python3/dist-packages nos dois
    python3 -c "import numpy, cv2; print(numpy.__version__, numpy.__file__); print(cv2.__version__, cv2.__file__)"

    # se algum vier de ~/.local ou /usr/local, devolva o sistema ao apt
    python3 -m pip uninstall -y numpy opencv-python opencv-contrib-python opencv-python-headless
    sudo apt install --reinstall python3-opencv python3-numpy
    python3 -c "from cv_bridge import CvBridge; print(16 in CvBridge().cvtype_to_name)"   # True = resolvido
    ```

    **Mexer no seu venv não resolve isto.** Os nós ROS 2 rodam com o `python3` do sistema, não com o do venv — é por isso que a doutrina da disciplina é: bibliotecas do sistema vêm do **apt**, e o `uv` só é usado **dentro** de um venv (`uv venv --system-site-packages`), nunca com `sudo` e nunca com `--system`.

    Guarde o formato desta história, porque ela vai se repetir no seu TP: **um comando aparentemente inofensivo trocou uma biblioteca por baixo do ROS 2, e o erro apareceu horas depois, em outro lugar, sem relação aparente com a causa.**

## Parte 2 — Segmentação por cor

### Por que HSV e não BGR

Em BGR, "vermelho" não é uma região compacta: um vermelho iluminado e um vermelho na sombra têm valores completamente diferentes nos três canais, porque **brilho e cor estão misturados**. O espaço HSV separa isso em matiz (que cor), saturação (quão pura) e valor (quão clara). Assim a regra "é vermelho" vira uma faixa estreita em H, e as variações de iluminação viram variações em V, que você tolera com um limiar frouxo.

No OpenCV, H vai de 0 a 179 — metade do círculo de 360°, para caber em um byte. Isso cria a pegadinha do vermelho: ele fica **nas duas pontas** do intervalo, perto de 0 e perto de 179. Segmentar vermelho exige duas máscaras somadas; azul, verde e amarelo vivem no meio e precisam de uma só. É a primeira armadilha de visão que quase todo mundo encontra, e agora você já a conhece.

### Máscara, morfologia e contagem

O caminho é sempre o mesmo. Converta para HSV, gere a máscara binária com `inRange`, limpe a máscara com morfologia — `OPEN` remove pontos isolados de ruído, `CLOSE` fecha buracos dentro do objeto —, extraia contornos com `findContours` em modo `RETR_EXTERNAL` e descarte os contornos de área pequena. O que sobrou é a sua contagem.

O **filtro de área é o parâmetro mais útil de todos** e o mais subestimado: ele sozinho elimina a maior parte dos falsos positivos, e é a primeira coisa a ajustar quando a contagem oscila.

### O experimento da oclusão

O exemplo desenha dois círculos vermelhos que, em alguns quadros, se sobrepõem. Quando isso acontece a contagem cai de 2 para 1, e **isso não é um defeito do exemplo** — é oclusão, o problema número um de qualquer sistema de percepção real. Reproduza, registre com print e discuta no relatório do TP1: por que acontece, e o que você faria a respeito (área máxima além da mínima, rastreamento entre quadros, `watershed`, ou um detector por aparência no TP2). Um parágrafo honesto sobre isso vale mais do que um pipeline que finge que o problema não existe.

## Baixar o material desta aula

Os exemplos vivem no repositório da disciplina. Você **não** trabalha dentro dele: copia o pacote para dentro do **seu** projeto e compila lá. Troque `SEU-USUARIO` pelo seu usuário do GitHub.

```bash
# 1) baixar o material (pode repetir sempre — a linha do rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar o pacote desta aula para dentro do SEU projeto
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula03-visao/aula03_visao \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar no SEU workspace
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select aula03_visao --symlink-install
source install/setup.bash
```

!!! tip "Rode antes de modificar"
    Compile e rode o exemplo **como ele veio**, antes da sua primeira alteração. Parece perda de tempo e é o contrário: quando algo quebrar depois, você sabe que o problema é seu e não do exemplo.

## Parte 3 — Mão na massa

Com o pacote já copiado e compilado (seção [Baixar o material desta aula](#baixar-o-material-desta-aula)):

```bash
ros2 launch aula03_visao visao.launch.py          # fonte sintética: não precisa de webcam
ros2 topic echo /vision/contagem                  # em outro terminal
ros2 service call /vision/status std_srvs/srv/Trigger "{}"
```

A fonte padrão é **sintética**: a cena é desenhada em código, então o exemplo funciona sem webcam e sem driver nenhum, em qualquer rota de ambiente. Quem já tiver a câmera visível dentro do Ubuntu roda com `fonte:=webcam`; quem tiver um vídeo gravado usa `fonte:=video`. E se a webcam falhar ao abrir, o nó cai sozinho para a fonte sintética em vez de morrer — que é o comportamento que você também quer no seu projeto.

Depois de rodar, o exercício que importa é este: **troque a cor sem tocar no código.**

```bash
ros2 param set /segmentador_hsv h_min 100
ros2 param set /segmentador_hsv h_max 130     # agora ele caça azul
ros2 param set /segmentador_hsv area_min 1200.0
```

Configuração em YAML e parâmetro em vez de constante no código é exatamente o que o TP2 vai cobrar. Comece o hábito hoje, enquanto é barato.

## Parte 4 — Bloco de projeto

Este bloco não é "sobra de aula": ele decide o semestre. Três documentos novos entram em vigor hoje.

**[Derivações e aplicações](../../recursos/derivacoes-projetos.md)** mostra que o núcleo técnico é quase sempre o mesmo — `sensor → percepção → representação → decisão → navegação → evidência` — e que o que muda entre um projeto e outro é o domínio. Isso libera você a escolher uma aplicação que realmente te interessa, sem aumentar o risco técnico. São cinco derivações para cada uma das sete famílias do catálogo, mais uma tabela de troca de setor.

**[Simulação × hardware real](../../recursos/simulado-vs-hardware.md)** explicita a régua da disciplina, e ela é assimétrica de propósito: quem simula tem o ambiente sob controle, então a expectativa de **complexidade e eficácia é maior**; quem coloca hardware real no circuito gasta boa parte do esforço em problemas que a simulação não tem, e isso é reconhecido mesmo com resultado final mais modesto. **Não há trilha recomendada:** as três são defensáveis, e a escolha certa é a que você consegue sustentar até o TP5. A trilha **híbrida** aparece no material como *exemplo de meio termo plausível* — núcleo simulado com **um** elemento real, e a webcam já basta para trazer ruído, iluminação e latência de verdade —, não como escolha padrão.

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
| `KeyError: 16` na conversão de imagem | OpenCV ou NumPy vindos de `pip` no python do sistema — [veja o aviso acima](#cv_bridge-e-o-que-fazer-quando-ele-nao-coopera). O exemplo não trava: cai no modo manual |
| `Exception ignored in: <function Future.__del__ …>` / `'Task' object has no attribute '_exception'` ao sair | ruído do `rclpy` na coleta de lixo do desligamento. `Exception ignored in:` é o próprio Python avisando que descartou a exceção. A linha que importa é `process has finished cleanly` |
| janela do `rqt_image_view` não abre | **WSL2:** WSLg desatualizado — `wsl --update` e reabra o terminal. **VirtualBox:** Guest Additions faltando, ou **aceleração 3D ligada** (desligue-a) |
| webcam não abre | **WSL2:** falta o `usbipd attach` — ver [tutorial da câmera](../../tutoriais/camera-wsl2-usbipd.md). **VirtualBox:** Extension Pack + *Dispositivos → Webcams* ([seção do guia](../../tutoriais/setup-ros2-humble-virtualbox.md#webcam-extension-pack-nao-usbipd)). Enquanto isso, `fonte:=sintetico` |
| vermelho quase não é detectado | faltou a segunda faixa de matiz (170–180); vermelho ocupa as duas pontas do círculo |
| contagem oscilando muito | `area_min` baixo demais, ou falta morfologia `OPEN` |
| taxa muito baixa, ou imagem travando | meça antes de culpar a câmera. `ros2 topic hz` num tópico de **imagem** é um nó Python desserializando ~900 kB por mensagem: ele mede a si mesmo se afogando. Use a régua leve — `ros2 topic hz /vision/contagem` — e siga o [roteiro de medição](../../tutoriais/camera-wsl2-usbipd.md#medir-a-taxa-sem-se-enganar) |
| `ros2 topic hz` com `min:` **negativo**, ou buracos de segundos | intervalo negativo entre duas mensagens é impossível — nada chega antes de ter sido enviado. É o **relógio do WSL2 saltando**, e ele também congela os timers do `rclpy`, o que parece câmera travada. [Diagnóstico e cura](../../tutoriais/setup-ros2-humble-wsl2.md#o-relogio-do-wsl2-pode-saltar-e-isso-estraga-qualquer-medicao) |
| `ModuleNotFoundError: No module named 'PyQt5'` ao abrir o `rqt_image_view` | **venv ativado.** O ROS 2 entra pelo `PYTHONPATH` e sobrevive ao venv (por isso o `ros2 launch` funciona); o `python3-pyqt5` do apt não, porque um venv sem `--system-site-packages` corta o caminho do sistema. `deactivate` resolve na hora |
| `A message was lost!!!` no `echo` de imagem | mensagem grande fragmentada em UDP: perdeu um fragmento, perdeu o quadro. Numa máquina só, `export ROS_LOCALHOST_ONLY=1` em todos os terminais costuma bastar. É por isso que não se dá `echo` em tópico de imagem |

## Para a próxima aula (11/08)

Leitura oficial do TP1 e mentoria de projeto. Chegue com o `PROJETO.md` preenchido — domínio, classes, trilha e plano B —, com o pipeline da tarefa rodando sobre o **seu** objeto e com os gates do TP1 marcados. A Aula 4 rende muito mais para quem chega com uma pergunta específica do que para quem chega com o projeto ainda em branco.
