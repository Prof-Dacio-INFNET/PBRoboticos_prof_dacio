---
titulo: "Tarefa da Aula 3 — pipeline de visão do seu projeto"
aula: 3
etapa: 2
data_aula: 2026-08-04
prazo: 2026-08-11
obrigatoria: true
vira_no_tp: "TP1 itens 3 e 4"
---

# Tarefa da Aula 3 — pipeline de visão do seu projeto

**Publicada em 04/08/2026 · trazer pronta para a Aula 4, em 11/08/2026**

Esta tarefa não é um exercício avulso. O que você entregar aqui é, quase sem modificação, o que o **TP1 vai cobrar nos itens 3 e 4** em 28/08. Fazer bem feito agora significa que, daqui a três semanas, o TP1 será uma questão de escrever o relatório.

O exemplo da aula caça círculos vermelhos desenhados em código. Seu trabalho é fazer o mesmo pipeline caçar **o objeto do seu projeto**, e provar que funciona.

## O que você vai entregar

Um pacote ROS 2 no seu repositório `projeto-pb-<usuario>`, na branch `dev`, com o pipeline rodando sobre o seu objeto, mais quatro evidências commitadas. Nada disso precisa estar bonito. Precisa estar **verificável**.

<!-- PB:TAREFA-A03 -->
- [ ] T3.1 pacote próprio compilando (`colcon build --symlink-install` limpo)
- [ ] T3.2 pipeline rodando sobre o **seu** objeto, não sobre o círculo vermelho do exemplo
- [ ] T3.3 taxa real do tópico medida e registrada (`ros2 topic hz`)
- [ ] T3.4 `/vision/status` respondendo com informação do **seu** domínio
- [ ] T3.5 parâmetros em YAML, zero constante de cor no código
- [ ] T3.6 evidências em `docs/evidencias/aula03/` e commit na `dev`

## Passo 1 — Adote o exemplo como seu

Copie, renomeie, compile, rode **antes** de mudar qualquer coisa. Rodar o exemplo intacto no seu workspace parece perda de tempo e é o oposto: quando algo quebrar depois da sua primeira alteração, você saberá que o problema é seu.

```bash
cp -r aula03-visao/aula03_visao ~/SEU-REPO/ros2_ws/src/percepcao_meu_projeto
cd ~/SEU-REPO/ros2_ws
colcon build --symlink-install && source install/setup.bash
ros2 launch percepcao_meu_projeto visao.launch.py
```

**Toda essa edição acontece em `src/`** — nunca em `build/` ou `install/`, que são gerados pelo `colcon build` e sobrescritos a cada compilação.

!!! warning "Renomear pacote: os quatro lugares (e o `setup.cfg` que todo mundo esquece)"
    Em pacotes `ament_python`, ao renomear pacote, alinhar `<name>` em `package.xml`, `package_name` em `setup.py`, arquivo `resource/<package_name>` e `setup.cfg` (`script_dir`/`install_scripts` em `$base/lib/<package_name>`).

    - Se `setup.cfg` ficar com nome antigo, `ros2 launch` falha com: `libexec directory .../lib/<package_name> does not exist`.

    Faltando o `package.xml` ou o `resource/`, o sintoma é outro: um `Package not found` teimoso que sobrevive a recompilações. Passo a passo completo, com a sequência de comandos e o teste de 10 segundos que confere os três pontos: [Renomear um pacote ROS 2](renomear-pacote-ros2.md).

Escolha um nome que descreva o seu domínio, não a aula. `percepcao_estoque`, `visao_pomar`, `deteccao_epi`. O nome do pacote é a primeira coisa que o avaliador lê.

## Passo 2 — Troque o alvo

Aqui está o coração da tarefa. Você precisa de **duas classes distinguíveis** — não uma. Uma classe só esconde o problema interessante: com uma classe, qualquer limiar que detecte alguma coisa parece funcionar.

Como escolher as duas classes depende da sua derivação de projeto. Alguns pares que funcionam bem, por serem separáveis em matiz e terem tamanhos parecidos:

| Domínio | Classe A | Classe B | Onde conseguir |
|---|---|---|---|
| Estoque / logística | caixa azul | caixa amarela | papel colorido, dois post-its grandes |
| Agrícola | fruto maduro (vermelho) | fruto verde | tomate cereja, ou dois círculos impressos |
| Segurança do trabalho | capacete amarelo | colete laranja | recorte de papel, foto no celular |
| Tráfego | sinal verde | sinal vermelho | imagem na tela do celular apontada para a webcam |
| Triagem / reciclagem | tampa azul | tampa verde | duas tampas de garrafa |

!!! tip "Sem webcam ainda? A tarefa continua valendo"
    Rode com `fonte:=sintetico` e **edite a cena sintética** para desenhar os seus dois objetos, com as suas cores e os seus tamanhos. Isso satisfaz a tarefa inteira. A câmera entra quando o `usbipd` estiver resolvido — ver o [tutorial da câmera](camera-wsl2-usbipd.md). Não espere hardware para começar: quem espera chega ao TP1 com uma semana a menos.

Para descobrir os limiares HSV do seu objeto, não chute. Meça:

```bash
ros2 run percepcao_meu_projeto amostrar_hsv          # clique no objeto, tecle q, cole o YAML
```

Clique em vários pontos do objeto, inclusive nas partes em sombra: a faixa precisa cobrir o objeto real, não o objeto bem iluminado. A máscara prevista aparece em verde enquanto você clica, e ao sair o nó imprime o bloco de YAML pronto.

Sem câmera, ou sem janela gráfica no WSL? Fotografe o objeto com o celular, copie a foto para dentro do WSL e meça na foto — vale igual:

```bash
ros2 run percepcao_meu_projeto amostrar_hsv --ros-args -p imagem:=/caminho/foto.jpg
python3 teste_offline.py /caminho/foto.jpg           # nem precisa do ROS 2 no ar
```

Anote os valores encontrados — eles vão para o YAML no Passo 4, e para o relatório do TP1.

Lembre da armadilha do vermelho: no OpenCV o matiz vai de **0 a 179**, e o vermelho ocupa as duas pontas. Se uma das suas classes for vermelha, ela precisa de duas máscaras somadas (0–10 e 170–179). Uma máscara só detecta metade dos vermelhos, e o sintoma é uma contagem que funciona às vezes.

## Passo 3 — Meça a taxa real

Este passo é o que separa "rodou" de "funciona". Com o pipeline em execução, em outro terminal:

```bash
ros2 topic hz /camera/image_raw
ros2 topic hz /vision/contagem
ros2 topic info /camera/image_raw --verbose
```

Registre os três números em `docs/evidencias/aula03/taxas.md`: a taxa de entrada, a taxa de saída e a QoS de cada ponta. Depois responda, em duas ou três linhas, à pergunta que importa: **a taxa de saída caiu em relação à de entrada?** Se caiu, o seu processamento não acompanha a câmera, e isso é uma informação de projeto, não um defeito a esconder. Reduza a resolução para 640×480, ou processe um quadro a cada N, e meça de novo.

Se `ros2 topic hz` não imprime nada enquanto `ros2 topic list` mostra o tópico, o problema é quase certamente QoS incompatível — `BEST_EFFORT` de um lado e `RELIABLE` do outro. O `--verbose` mostra os dois perfis lado a lado.

## Passo 4 — Parâmetros fora do código

Nenhum limiar de cor, nenhuma área mínima e nenhum caminho de dispositivo pode estar escrito como constante no `.py`. Tudo em `config/percepcao.yaml`, carregado pelo launch:

```yaml
segmentador_hsv:
  ros__parameters:
    classe_a_h_min: 100
    classe_a_h_max: 130
    classe_b_h_min: 20
    classe_b_h_max: 35
    s_min: 80
    v_min: 60
    area_min: 800.0
    area_max: 60000.0
```

O teste de aceitação é objetivo: você consegue trocar a classe detectada com o sistema **em execução**, sem recompilar?

```bash
ros2 param set /segmentador_hsv classe_a_h_min 0
ros2 param set /segmentador_hsv classe_a_h_max 10
```

Isso não é preciosismo de estilo. O TP2 cobra configuração externa explicitamente, e quem já entregou assim no TP1 não reescreve nada depois.

## Passo 5 — `/vision/status` com o seu domínio

O serviço do exemplo devolve uma contagem genérica. O seu deve devolver algo que faça sentido para quem usaria o seu sistema. A diferença entre as duas respostas abaixo é a diferença entre um exercício e um projeto:

```text
# genérico, do exemplo
"2 objetos detectados"

# seu, com domínio
"pomar setor 3: 2 maduros, 5 verdes, taxa 12.4 Hz, ultima deteccao ha 0.3 s"
```

Chame e guarde a saída:

```bash
ros2 service call /vision/status std_srvs/srv/Trigger "{}"
```

Enquanto o `std_srvs/Trigger` basta agora, ele já vai apertar — devolver números dentro de uma string é feio e frágil. Guarde esse incômodo: no TP2 você cria o seu próprio `.srv` com campos tipados, e a motivação vai ser exatamente esta.

## Passo 6 — Evidências e commit

Em `docs/evidencias/aula03/` do seu repositório:

| Arquivo | O que mostra |
|---|---|
| `pipeline.png` | `rqt_image_view` com a imagem segmentada e os contornos marcados |
| `grafo.png` | `rqt_graph` mostrando câmera → segmentador → contagem |
| `taxas.md` | as três medidas do Passo 3, com a sua interpretação |
| `status.txt` | a saída do `ros2 service call` |

```bash
git add -A && git commit -m "T3: pipeline de visao sobre <seu objeto>, taxas medidas, status com dominio"
git push origin dev
```

Um commit só está bom. Vários, um por passo, está melhor — a mensagem de commit é a única narrativa do seu processo que sobrevive até a arguição.

## O gate que essa tarefa fecha

Esta tarefa entrega, na prática, o **G1.3** (segmentação e contagem funcionando) e boa parte do **G1.4** (`/vision/status` e grafo) da [tabela de gates do TP1](../recursos/gates-tps.md). Marque os dois no seu `PROJETO.md` quando terminar.

Ela **não** fecha o G1.1 — declarar domínio, usuário, classes, trilha e plano B — que vence em **11/08** e é pré-requisito de tudo. Se você ainda não escolheu o projeto, faça isso **antes** desta tarefa, não depois: é a escolha do domínio que define quais são as suas duas classes.

## Se der errado

| Sintoma | O que verificar |
|---|---|
| `Package not found` depois de renomear | `package.xml` e `resource/<nome>`; ver [renomear pacote](renomear-pacote-ros2.md) |
| `libexec directory .../lib/<pacote> does not exist` | o `setup.cfg` ficou com o nome antigo (`script_dir`/`install_scripts`) |
| `AttributeError: _ARRAY_API not found` e depois `KeyError: 16` | `cv_bridge` do apt compilado contra NumPy 1.x rodando sob NumPy 2 — o exemplo cai sozinho no modo manual; para curar, `uv pip install "numpy<2"` no venv |
| `rcl_shutdown already called` ao sair com `Ctrl+C` | ruído de encerramento, não quebra nada; feche com `if rclpy.ok(): rclpy.shutdown()` |
| máscara toda preta | `s_min`/`v_min` altos demais; comece frouxo (S≥60, V≥40) e aperte |
| máscara toda branca | faixa de matiz larga demais, ou objeto e fundo com a mesma cor — troque o fundo |
| contagem pulando entre 1 e 2 | `area_min` baixo, ou falta morfologia `OPEN`; se os objetos se tocam, é oclusão (registre) |
| `ros2 topic hz` sem saída | QoS incompatível — `ros2 topic info --verbose` |
| tudo funciona, taxa em 2 Hz | resolução alta demais, ou `imshow` dentro do callback |

Antes de pedir ajuda, tenha em mãos o comando exato, a saída completa do erro, o que você já tentou e a saída de `ros2 topic info --verbose`. Pergunta com diagnóstico é resolvida em minutos.
