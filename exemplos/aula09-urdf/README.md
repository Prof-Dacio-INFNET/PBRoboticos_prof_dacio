# Exemplo — `aula09-urdf`

**Aula 9 · Etapa 5.** URDF mínimo de um robô com câmera, para aprender **TF** e **RViz2**. Cobre o gate **G2.5** do TP2.

O tutorial passo a passo, com instalação e configuração, está em **[URDF, TF e RViz2 — do zero ao robô na tela](../../tutoriais/urdf-tf-rviz2.md)**. Este README é a referência do pacote.

```
aula09-urdf/
└── meu_robo_description/
    ├── urdf/meu_robo.urdf        # 6 links, 5 juntas, raiz em base_link
    ├── launch/ver_robo.launch.py # robot_state_publisher + gui + rviz2
    └── rviz/meu_robo.rviz        # config salva DENTRO do pacote, de propósito
```

## Baixar e rodar

```bash
# 1) baixar o material (pode repetir sempre -- o rm evita o erro de pasta ja existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar para dentro do SEU projeto
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula09-urdf/meu_robo_description \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar e rodar
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select meu_robo_description --symlink-install
source install/setup.bash
ros2 launch meu_robo_description ver_robo.launch.py
```

Antes de rodar, valide — economiza a tarde:

```bash
check_urdf src/meu_robo_description/urdf/meu_robo.urdf
```

## A estrutura do modelo

| Link | Junta que o prende | Tipo | Por quê |
|---|---|---|---|
| `base_link` | — | — | a **raiz**. Todo robô tem uma, e por convenção é este nome |
| `roda_esquerda` / `roda_direita` | `junta_roda_*` | `continuous` | roda gira sem limite — é o tipo certo |
| `mastro` | `junta_mastro` | `fixed` | peça aparafusada. Parece inútil e é o tipo mais usado |
| `camera_link` | `junta_camera` | `fixed` | onde o sensor está montado, com inclinação de 0,2 rad |
| `marcador_alvo` | `junta_pan` | `revolute` | a única que se mexe pelo slider — é ela que faz a TF mudar ao vivo |

## Os três experimentos

**1. Mova o slider `junta_pan` e leia a TF ao mesmo tempo.**

```bash
ros2 run tf2_ros tf2_echo base_link marcador_alvo
```

Os números mudam enquanto você arrasta. TF é uma função do tempo, e ver isso acontecer vale mais que a definição.

**2. Desenhe a árvore.**

```bash
ros2 run tf2_tools view_frames     # gera frames.pdf
```

Uma árvore só, `base_link` na raiz, sem órfãos. **Duas árvores separadas** significam que falta uma junta ligando as partes — é o achado mais comum na correção do G2.5.

**3. Troque um `<origin>` de lugar, de propósito.** Mova o `<origin>` da `junta_camera` para dentro do `<visual>` do `camera_link`, recompile e compare o `tf2_echo`. No RViz2 continua *parecendo* certo; a TF fica errada.

Esse é o erro que consome uma tarde: o `origin` do **visual** move só o desenho; o do **joint** move a peça e tudo que pende dela, e é ele que entra na TF. O sintoma aparece longe da causa — o seu objeto detectado passa a estar 20 cm fora do lugar, e você procura na visão computacional.

## Adaptar para o seu projeto

Renomeie o pacote para `<seuprojeto>_description` (o nome bate em `package.xml`, `setup.py`, `resource/<nome>` e `setup.cfg`) e ajuste as medidas. Se o projeto é simulado, invente números plausíveis e **anote que são inventados**; se tem hardware, meça com régua. URDF com número chutado produz TF errada, e TF errada não dá erro: dá resultado errado.

Mantenha os nomes convencionais de sensor — `camera_link`, `laser_link`. Convenção de nome não é estética: é o que faz outras ferramentas acharem o seu sensor sem configuração.

## Licença

MIT, como todo o diretório `exemplos/`.
