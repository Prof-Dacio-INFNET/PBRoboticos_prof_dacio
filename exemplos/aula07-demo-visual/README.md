# Exemplo — `aula07-demo-visual`

**Aula 7 · abertura.** Duas demonstrações com a webcam do notebook, feitas para serem projetadas antes de qualquer slide. As duas mostram a mesma coisa por caminhos diferentes: **o que hoje é um desenho na tela, amanhã é um comando no motor.**

```
aula07-demo-visual/
└── demo_visual/
    ├── piloto.py               # Demo 1: percepção + desenho, SEM rclpy dentro
    ├── guia_visual.py          # Demo 1: o nó — publica ComandoMovimento
    ├── formas.py               # Demo 2: formas dos marcadores (gerador E detector)
    ├── detector_marcadores.py  # Demo 2: acha a forma e CHAMA o serviço
    ├── painel_robo.py          # Demo 2: os quatro serviços — o lugar do robô
    ├── teste_offline.py        # plano B: roda sem ROS 2
    └── marcadores/
        ├── gerar_folhas.py
        └── marcadores-aula07.pdf   # 5 folhas A4 para imprimir
```

## Baixar o material desta aula

```bash
# 1) baixar o material (pode repetir sempre -- o rm evita o erro de pasta ja existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar. pb_interfaces vem de novo: ganhou ComandoMovimento e a action
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/pb_interfaces \
      /tmp/PBRoboticos_prof_dacio/exemplos/aula07-demo-visual/demo_visual \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar -- interfaces primeiro, sempre
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select pb_interfaces
source install/setup.bash
colcon build --packages-select demo_visual --symlink-install
source install/setup.bash
```

## Demo 1 — a seta que um dia será um motor

```bash
ros2 launch demo_visual demo1.launch.py
```

Mostre um objeto vermelho à câmera. O nó acha a **maior** mancha vermelha e desenha a seta do movimento que a câmera precisaria fazer: primeiro centralizar (esquerda, direita, cima, baixo), depois aproximar ou afastar até a área bater com a esperada. Quando está certo, o comando fica **PARADO**, em verde.

Não tem objeto vermelho à mão? A primeira folha do `marcadores-aula07.pdf` é um círculo vermelho grande.

O que assistir, além da seta:

```bash
ros2 topic echo /demo/comando          # a seta, como MENSAGEM
ros2 topic hz /demo/comando
```

A seta na tela e a mensagem no tópico são a **mesma informação**. Trocar o desenho por um driver de tração não muda uma linha da percepção — e é exatamente por isso que o `ComandoMovimento` existe como interface própria em vez de o nó desenhar e pronto.

## Demo 2 — a folha que chama um serviço

Imprima `marcadores/marcadores-aula07.pdf` (5 páginas) e distribua as quatro folhas de marcador.

```bash
ros2 launch demo_visual demo2.launch.py
```

Cada forma reconhecida dispara **um serviço diferente**, e o `painel_robo` imprime um banner grande no terminal:

| Marcador | Serviço | O que seria no robô |
|---|---|---|
| triângulo | `/robo/parar` | motores em zero, freio acionado |
| quadrado | `/robo/seguir` | controle de trajetória assumindo |
| círculo | `/robo/girar` | rotação no próprio eixo |
| cruz | `/robo/emergencia` | corte de potência, requer rearme |

A folha do **alvo vermelho** não dispara nada, de propósito — o detector exige que o marcador seja **preto**, e isso é a demonstração ao vivo de por que cor e forma são pistas independentes.

## Os detalhes que valem discussão

**Vermelho ocupa as duas pontas do círculo de matiz.** O `piloto.py` usa duas faixas de HSV (0–10 e 170–180). Com uma só, metade dos vermelhos escapa, e o sintoma é "às vezes detecta, às vezes não" — que é muito pior do que não detectar nunca.

**Saturação não significa nada quando não há luz.** O detector de marcadores decide "isto é preto?" pelo canal **V**, não pelo **S**. Num pixel quase preto, `S = (max−min)/max` com `max` minúsculo vira ruído puro: um preto com um pingo de ruído mede saturação 200. Foi exatamente isso que rejeitou todos os marcadores na primeira versão deste código.

**Debounce não é firula.** O detector só chama o serviço depois de ver a forma em **três quadros seguidos**, e depois espera três segundos antes de repetir. Sem isso, o serviço é chamado dezenas de vezes por segundo enquanto a folha estiver levantada. É o que separa *detectou* de *decidiu*.

**Uma correção por vez.** O Demo 1 centraliza primeiro e só depois aproxima, em vez de corrigir os dois erros juntos. É decisão de projeto: robô que corrige tudo ao mesmo tempo é confuso de assistir e difícil de depurar.

## Plano B, sem ROS 2

```bash
python3 teste_offline.py             # webcam
python3 teste_offline.py foto.jpg    # so uma foto, sem camera
```

Se isto roda e o nó ROS não, o problema está no ROS. Se nem isto roda, está na câmera ou no OpenCV — e você dividiu o espaço de busca pela metade sem depurar nada.

## Licença

MIT, como todo o diretório `exemplos/`.
