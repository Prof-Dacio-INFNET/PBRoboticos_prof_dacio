# aula03-visao — câmera → segmentação → contagem → serviço

Exemplo da **Aula 3 (Etapa 2)**. É o `aula02-comunicacao` crescido: onde antes viajava um texto, agora viaja **imagem**. Este é o esqueleto dos itens 3 e 4 do TP1.

```
publicador_camera  --/camera/image_raw-->  segmentador_hsv  --/vision/segmented-->  (rqt_image_view)
                                                   |
                                                   +--/vision/contagem--> (ros2 topic echo)
                                                   +--/vision/status (serviço) <-- monitor
```

## Rodar (5 comandos)

```bash
cp -r aula03-visao/aula03_visao ~/SEU-REPO/ros2_ws/src/
cd ~/SEU-REPO/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch aula03_visao visao.launch.py            # fonte sintética: não precisa de webcam
ros2 topic echo /vision/contagem                    # noutro terminal
ros2 service call /vision/status std_srvs/srv/Trigger "{}"
```

Ver a imagem processada: `ros2 run rqt_image_view rqt_image_view` e escolha `/vision/segmented`.

## Fontes de imagem

| `fonte` | Quando usar | Comando |
|---|---|---|
| `sintetico` (padrão) | sempre funciona — cena gerada em código, 2 objetos vermelhos + 1 distrator azul | `ros2 launch aula03_visao visao.launch.py` |
| `webcam` | você já passou a câmera para o WSL2 com usbipd | `ros2 launch aula03_visao visao.launch.py fonte:=webcam` |
| `video` | arquivo `.mp4` em loop (ótimo para o vídeo do TP) | `ros2 run aula03_visao publicador_camera --ros-args -p fonte:=video -p arquivo:=/caminho/clip.mp4` |

Sem webcam no WSL2? Ver [tutoriais/camera-wsl2-usbipd.md](../../tutoriais/camera-wsl2-usbipd.md). **A fonte sintética é aceita no TP1** desde que você explique a escolha — o que se avalia é o pipeline.

## Ajustar sem tocar no código

```bash
ros2 param set /segmentador_hsv area_min 1200.0   # ignora manchas pequenas
ros2 param set /segmentador_hsv h_min 100         # ...
ros2 param set /segmentador_hsv h_max 130         # ...caça o AZUL em vez do vermelho
ros2 param list /segmentador_hsv
```

Os valores padrão estão em `config/segmentacao.yaml`. Editar YAML em vez de código é exatamente o que o **TP2** vai cobrar — comece o hábito agora.

## Descobrir os limiares do *seu* objeto (sem chutar)

Chutar `h_min` é a forma mais cara de perder uma tarde. Meça:

```bash
ros2 run aula03_visao amostrar_hsv                                   # ao vivo, assina /camera/image_raw
ros2 run aula03_visao amostrar_hsv --ros-args -p imagem:=/caminho/foto.jpg   # sobre uma foto
```

Clique no objeto em vários pontos — inclusive nas partes escuras dele —, veja a máscara prevista aparecer em verde por cima da imagem e tecle `q`. O nó imprime um bloco de YAML pronto para colar. `r` limpa as amostras se você clicou fora.

Ele lê a **mediana** de uma vizinhança 9×9 em volta do clique, não o pixel isolado: um pixel sozinho carrega ruído de sensor e artefato de compressão. E, se as amostras aparecerem partidas nas duas pontas do círculo de matiz, ele devolve **duas faixas** automaticamente — que é o caso do vermelho.

Sem WSLg para abrir janela? O caminho é o teste offline abaixo, com uma foto.

## Teste offline (sem ROS 2)

```bash
python3 teste_offline.py                  # cena sintética: 2 vermelhos + 1 distrator azul
python3 teste_offline.py minha_foto.jpg   # a mesma segmentação sobre uma foto sua
```

O primeiro modo imprime a contagem por frame — útil para depurar visão sem subir o grafo, e para entender o experimento abaixo. O segundo aplica **a mesma** função de máscara do nó da aula sobre uma foto, diz quanto da imagem a máscara cobriu, lista as áreas encontradas e sugere os limiares. É a saída de emergência para quem ainda não tem câmera nem interface gráfica: tire a foto com o celular, copie para dentro do WSL e meça ali.

## O experimento que vale ouro no relatório

Em alguns frames a contagem cai de **2 para 1**: os dois círculos vermelhos se sobrepõem e viram um único contorno. Isso não é bug do exemplo, é **oclusão** — o problema nº 1 de qualquer sistema de percepção real. Registre isso no seu relatório do TP1 (com print), diga por que acontece e como você pretende tratar (área mínima/máxima, rastreamento entre frames, `cv2.watershed`, ou detector por aparência no TP2).

## Adapte para o seu projeto

1. Renomeie o pacote (`aula03_visao` → `percepcao_meu_projeto`) e os nós — [passo a passo, com os quatro lugares do nome e o `setup.cfg`](../../tutoriais/renomear-pacote-ros2.md).
2. Troque a faixa HSV pela cor/classe que interessa ao **seu** projeto.
3. Faça `/vision/status` responder algo do seu domínio ("3 EPIs detectados", "faixa perdida").
4. Guarde o `.launch.py`: no TP3 ele vira o `bringup.launch.py` do sistema inteiro.

## Onde editar o quê

Depois de copiar o pacote para `~/SEU-REPO/ros2_ws/src/`, **toda** alteração acontece em `src/`. As pastas `build/`, `install/` e `log/` são geradas pelo `colcon build` e sobrescritas a cada compilação — editar ali é trabalho que some no próximo build. Mapa rápido do que fica onde:

| Quero mudar… | Arquivo, dentro de `src/<pacote>/` |
|---|---|
| a cena, a fonte de imagem, a taxa | `aula03_visao/publicador_camera.py` |
| a máscara HSV, a morfologia, a contagem, o serviço | `aula03_visao/segmentador_hsv.py` |
| os valores padrão dos parâmetros | `config/segmentacao.yaml` |
| quais nós sobem e com que argumentos | `launch/visao.launch.py` |
| a conversão imagem ↔ mensagem | `aula03_visao/ponte.py` |
| o nome do pacote | `package.xml`, `setup.py`, `resource/<nome>` e `setup.cfg` — [ver o guia](../../tutoriais/renomear-pacote-ros2.md) |

## Sequência de comandos recomendada

```bash
cd ~/SEU-REPO/ros2_ws

# opcional, quando houver muita sujeira de build anterior
rm -rf build/aula03_visao install/aula03_visao log/latest_build

colcon build --packages-select aula03_visao --symlink-install
source install/setup.bash
ros2 launch aula03_visao visao.launch.py
```

## Se der errado

| Sintoma | O que é, e o que fazer |
|---|---|
| `KeyError: 16` na conversão, com ou sem `AttributeError: _ARRAY_API not found` antes | o `cv_bridge` do apt está conversando com uma biblioteca que não é a que ele esperava — NumPy 2, ou OpenCV 5, os dois vindos de pip. 16 é `CV_8UC3`, que é exatamente `bgr8`. O `ponte.py` detecta isso sozinho — faz um round-trip de teste no import — e cai na conversão manual, então o exemplo continua rodando e a tarefa pode ser feita. Para curar de vez, veja [Curando o `KeyError: 16` de vez](#curando-o-keyerror-16-de-vez) |
| `cv_bridge=nao, conversao manual bgr8` no log de partida | é o aviso acima em forma de log: o exemplo está no plano B. Funciona, mas vale consertar o ambiente |
| `libexec directory '.../lib/<pacote>' does not exist` | o `setup.cfg` ficou com o nome antigo depois de renomear — [guia de renomeação](../../tutoriais/renomear-pacote-ros2.md) |
| `rcl_shutdown already called on the given context` ao sair com `Ctrl+C` | ruído de encerramento; não quebra a execução principal. Os nós daqui já fecham com `if rclpy.ok(): rclpy.shutdown()` |
| `The following packages are in the environment but not in the workspace` / caminho inexistente em `AMENT_PREFIX_PATH` | resíduo de um `install/` de pacote que você apagou. Abra um terminal novo (sem o `source` antigo) e refaça `source install/setup.bash` |
| tópico existe e `echo` não mostra nada | QoS incompatível — `ros2 topic info /camera/image_raw --verbose` |
| mudei `config/segmentacao.yaml` e nada mudou | o YAML é copiado no build: recompile, ou passe `--params-file` apontando para o arquivo em `src/` |

### Curando o `KeyError: 16` de vez

Esse erro tem **duas causas possíveis**, e as duas vêm da mesma raiz: algum `pip install` fora de um venv trocou, por baixo do ROS 2, uma biblioteca que o `cv_bridge` do apt esperava encontrar.

O ponto que engana antes de tudo: **os nós ROS 2 rodam com o `python3` do sistema**, não com o python de um venv — repare no `/usr/lib/python3.10/...` que aparece no traceback. Instalar coisa dentro de um venv não muda nada para eles. O que atrapalha está num diretório que o python do sistema enxerga, e é de lá que precisa sair.

Comece pelo diagnóstico:

```bash
python3 - <<'PY'
import cv2, numpy as np
print("cv2  ", cv2.__version__, cv2.__file__)
print("numpy", np.__version__, np.__file__)
from cv_bridge import CvBridge
b = CvBridge()
print("tem a chave 16?", 16 in b.cvtype_to_name)
print("encoding_to_cvtype2('bgr8') =", b.encoding_to_cvtype2('bgr8'))
PY
```

O esperado num ambiente correto é `cv2 4.5.4` e `numpy 1.x`, ambos vindos de `/usr/lib/python3/dist-packages`, e `tem a chave 16? True`.

**Causa 1 — NumPy 2.** Se aparecer NumPy 2.x, e antes do `KeyError` o terminal tiver cuspido `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x` e `AttributeError: _ARRAY_API not found`: a extensão em C++ do `cv_bridge` foi compilada contra NumPy 1.x e falha ao carregar sob NumPy 2. O detalhe cruel é que o `import` **passa** assim mesmo — a tabela interna de tipos fica vazia e o erro só aparece na primeira conversão.

**Causa 2 — OpenCV 5.** Se o `cv2.__version__` disser 5.x, é isto: **o OpenCV 5 renumerou as constantes de tipo.** `cv2.CV_8UC3` continua existindo, mas não vale mais 16. O `cv_bridge` do apt foi compilado contra o OpenCV 4.5.4 e pergunta em numeração antiga (`getCvType('bgr8')` devolve 16), enquanto a tabela do `CvBridge` foi montada com a numeração nova. Os dois lados falam versões diferentes do mesmo dicionário, e sobra o `KeyError: 16`. É a causa mais provável quando **não** há mensagem nenhuma sobre NumPy antes do erro.

A cura das duas é a mesma: tirar do caminho o que veio por pip.

| O que o caminho mostra | De onde veio | Como tirar |
|---|---|---|
| `~/.local/lib/python3.10/site-packages/...` | `pip install --user` | `python3 -m pip uninstall -y numpy opencv-python opencv-contrib-python opencv-python-headless` |
| `/usr/local/lib/python3.10/dist-packages/...` | `sudo pip` ou `uv pip install --system` | o mesmo comando, com `sudo` |
| `/usr/lib/python3/dist-packages/...` | é o do apt, está correto | nada a fazer |

Repita o `uninstall` até dizer que não está instalado; pode haver mais de uma camada. Se alguma das bibliotecas sumir de vez, reponha pelo apt: `sudo apt install --reinstall python3-opencv python3-numpy`. Confirme com o script de diagnóstico acima — `tem a chave 16? True` é o sinal de que a ponte fechou.

A regra de instalação da disciplina existe justamente por causa disso: **OpenCV e cv_bridge vêm do apt** (`python3-opencv`, `ros-humble-cv-bridge`), e o **uv só é usado dentro de um venv** — nunca `sudo uv`, nunca `uv pip install --system`. Um pip fora do venv reescreve, sem avisar, bibliotecas que o ROS 2 usa; o sintoma só aparece muito depois, longe da causa.

Licença: MIT (ver `exemplos/LICENSE`) — pode copiar para o seu repositório mantendo o aviso de copyright.
