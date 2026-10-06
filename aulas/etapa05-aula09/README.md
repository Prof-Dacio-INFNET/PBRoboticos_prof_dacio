# Aula 9 — Detecção treinada e métrica declarada

**Terça, 15/09/2026 · sala SJ205 · Etapa 5 (14/09–26/09)**

[:material-file-pdf-box: Slides da Aula 9 (PDF)](apresentacao-aula09.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula09-metrica`](../../exemplos/aula09-metrica/index.md){ .md-button }
[:material-cube-outline: Tutorial de URDF e TF](../../tutoriais/urdf-tf-rviz2.md){ .md-button }

!!! warning "Esta aula carrega dois gates, e o TP2 vence em 25/09"
    **G2.4** (detecção com métrica declarada) vence em 19/09 — quatro dias depois desta aula. **G2.5** (YAML + URDF com TF coerente) vence em 22/09, e a parte de instalação já está publicada como [tutorial](../../tutoriais/urdf-tf-rviz2.md).

    A aula tem duas metades: a primeira ensina a medir; a segunda é clínica de URDF. Quem chegar sem ter feito o tutorial vai passar a segunda metade instalando pacote.

## A ideia da aula em uma frase

**"Ficou bom" deixa de ser resposta aceitável.** Até aqui vocês ajustaram HSV olhando para a tela e decidindo por impressão. A partir de hoje, afirmar que um detector melhorou exige um número, produzido sobre dado fixo, por uma régua declarada **antes** de rodar.

Não é burocracia acadêmica: é a única forma de saber se a sua próxima ideia ajudou ou atrapalhou. Sem métrica, um ano de ajustes pode piorar o sistema sem ninguém perceber.

## Objetivos

Ao final da aula você deve conseguir declarar uma métrica adequada ao seu domínio e justificar a escolha; explicar por que medir exige dado fixo e por que vídeo ao vivo não serve; ler um resultado agregado e dizer o que ele **esconde**; reconhecer o compromisso entre sensibilidade e falso positivo e escolher conscientemente onde ficar; e trocar o detector sem trocar a régua.

## Baixar o material desta aula

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

# 1) baixar o material (pode repetir sempre — a linha do rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) o banco de provas de detectores (não precisa de ROS 2 nem de câmera)
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula09-metrica \
      "$PB_DIR/"

# 3) o modelo do robô, para a clínica de URDF da segunda metade
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula09-urdf/meu_robo_description \
      "$PB_WS/src/"

cd "$PB_DIR/aula09-metrica"
python3 gerar_video.py
python3 avaliar.py
```

## Parte 1 — Por que a cor acaba

A segmentação por HSV responde a uma pergunta: **"onde há vermelho?"**. Ela nunca respondeu "onde há um tomate", e isso não era um problema enquanto a única coisa vermelha na cena era o tomate.

O que quebra não é a técnica — é a cena. Entra um pano vermelho ao fundo, a luz da tarde muda, o objeto aparece parcialmente escondido. Cada um desses casos tem conserto dentro do HSV, e cada conserto é uma linha a mais de condição. Em algum ponto você tem quarenta linhas de heurística que ninguém consegue justificar, e nenhuma forma de saber se a linha quarenta e um vai ajudar.

**É esse o momento de medir.** Não porque HSV seja ruim — vocês vão ver hoje um HSV chegando a 100% —, mas porque sem régua não dá para saber quando parar de remendar.

## Parte 2 — Uma métrica é uma decisão, e vem antes

A métrica desta disciplina, declarada aqui antes de qualquer resultado:

> **taxa de alvo mantido** = quadros em que o detector achou o alvo com IoU ≥ 0,5, dividido pelos quadros em que o alvo **realmente** estava na cena.

Duas coisas nessa frase merecem atenção.

**"Realmente estava na cena"** exige que alguém saiba a verdade em cada quadro. Isso se chama rótulo, e é o insumo mais caro de qualquer avaliação. Sem rótulo não há medição — há impressão.

**"Declarada antes"** não é formalidade. Métrica escolhida depois de ver o resultado é a que faz o seu detector parecer bom, e todo mundo sabe disso — inclusive quem vai corrigir o seu TP.

!!! tip "Qual métrica serve ao SEU domínio"
    Não existe métrica universal, e a escolha diz mais sobre o problema do que sobre a técnica.

    | Se o seu robô… | o erro que dói é | então priorize |
    |---|---|---|
    | **freia** ao ver obstáculo | falso positivo (freada fantasma) | precisão |
    | **conta** frutos maduros | perder o alvo (subcontagem) | taxa de alvo mantido |
    | **segue** uma pessoa | trocar de alvo no meio | continuidade de identidade |
    | **inspeciona** peças | deixar refugo passar | recall, com precisão declarada |

    Escreva no relatório qual você escolheu **e por quê**. É a justificativa que se avalia, não o número.

### Dado fixo: por que vídeo ao vivo não serve

Você não pode comparar dois detectores em filmagens diferentes. Se o detector A rodou com a luz da manhã e o B com a da tarde, a diferença entre eles está contaminada pela diferença entre as cenas, e nenhum dos dois números significa alguma coisa.

Medição exige **o mesmo dado**, o que na prática significa vídeo gravado — ou, como no exemplo de hoje, vídeo **gerado**, onde o rótulo sai de graça porque você mesmo desenhou o alvo.

Isso não substitui dado real. Substitui a falta dele no dia em que você precisa validar o seu **método** de medição: um medidor que erra no cenário sintético vai errar mais no real.

## Parte 3 — Mão na massa: o banco de provas

```bash
# ── herda PB_USER, PB_DIR e PB_WS do bloco acima ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula09-metrica"
python3 gerar_video.py      # cena.avi + rotulos.csv
python3 avaliar.py
```

A cena tem quatro trechos, e cada um foi construído para quebrar uma coisa diferente:

| Quadros | O que acontece | O que quebra |
|---|---|---|
| 0–59 | normal, alvo + distrator azul | nada; é a linha de base |
| 60–89 | **oclusão** atrás de uma barra | rótulo vira *ausente*; detectar aqui é falso positivo |
| 90–149 | entra um distrator **vermelho maior** | "a maior mancha" aponta errado |
| 150–239 | a luz cai até ~22% | limiar fixo de brilho para de enxergar |

O resultado dos três detectores:

| detector | alvo mantido | falso positivo | custo relativo |
|---|---|---|---|
| `hsv_ingenuo` | 65,7% | 43,3% | linha de base |
| `hsv_com_area` | 94,3% | 6,7% | igual (às vezes mais barato) |
| `hsv_adaptativo` | **100,0%** | 10,0% | ~40% mais caro |

As duas primeiras colunas são **determinísticas**: rodando de novo, saem idênticas. A terceira não — e por que ela não sai é o assunto da próxima seção.

### Ver o que o detector viu

```bash
python3 avaliar.py --video        # gera saida_<detector>.avi
```

Cada quadro sai anotado: a **caixa da verdade** em âmbar, a **detecção** em verde ou vermelho, o IoU do quadro, o veredito (`ACERTO`, `PERDA`, `FALSO POSITIVO`, `ausente (ok)`) e a métrica acumulada até ali.

Abra o vídeo do `hsv_ingenuo` e vá ao quadro 90: dá para **ver** o instante em que ele troca o alvo pelo distrator maior e não volta mais. O número diz que errou; o vídeo diz em que ele estava olhando.

!!! warning "Por que o vídeo é um parâmetro, e por que ele fica fora do cronômetro"
    Desenhar custa mais que detectar. Medido: a detecção leva **1,65 ms** por quadro e o OSD leva **2,07 ms**. Se o desenho entrasse na janela cronometrada, **56% do número reportado seria o OSD** — e a comparação entre detectores passaria a medir quem desenha mais rápido.

    A regra generaliza, e vale para o nó ROS 2 de vocês: **o que você mede não pode incluir o custo de observar.** Vale para OSD, para `print` de depuração dentro do laço e para qualquer visualização acrescentada. Instrumentação que entra na medição transforma o instrumento em parte do experimento.

## Parte 4 — Ler o resultado: três leituras

### A média esconde onde falhou

O `hsv_ingenuo` marca 65,7%, o que soa como "funciona na maior parte do tempo". O detalhamento por trecho conta outra história:

```
    normal               100.0% mantido
    oclusao              alvo ausente; 13 falso(s) positivo(s) em 30
    distrator vermelho     0.0% mantido      <---
    luz caindo            86.7% mantido
```

Não é um detector que erra um pouco em todo lugar. É um detector que funciona **perfeitamente** até encontrar uma mancha vermelha maior, e então erra **100% do tempo**.

Essas duas situações produzem o mesmo 65,7% e exigem decisões opostas: erro espalhado sugere afinar parâmetros; erro concentrado sugere que uma hipótese do método está errada. **Média é um resumo; modo de falha é o que você precisa saber.** Por isso o relatório do TP2 pede a métrica **e** onde ela falha.

### Cada ideia compra uma quantidade mensurável

Trocar "a maior mancha vermelha" por "a mancha do tamanho esperado" é **uma linha** de código conceitualmente diferente — e levou 65,7% para 94,3%, sem custo de tempo. Adaptar o limiar de brilho ao brilho médio da cena levou para 100%, e custou 45% mais CPU.

Repare no que isso permite: você passa a saber **quanto vale** cada complicação que adiciona. Sem a régua, as três versões seriam igualmente defensáveis num relatório.

### Medir tempo é mais difícil do que medir acerto

Repare que a coluna de custo não traz número absoluto, e isso é deliberado. Ao medir tempo, três coisas atrapalham:

**A ordem contamina.** Na primeira versão deste exemplo, o `hsv_ingenuo` aparecia mais lento que os outros — e ele é o mais simples dos três. O motivo não tinha nada a ver com o detector: **ele era o primeiro a rodar**, e pagava sozinho o custo de aquecer cache e alocar buffers. A correção é rodar alguns quadros antes de começar a cronometrar, e o `avaliar.py` faz isso na função `aquecer()`.

**A média mente.** Um único quadro lento — o sistema operacional resolveu fazer outra coisa naquele instante — desloca a média e não diz nada sobre o detector. Por isso o relatório usa **mediana**, e mostra o p90 ao lado para você ver a cauda.

**O valor absoluto não é seu.** O tempo depende da máquina, da carga e até da temperatura. O que viaja entre máquinas é a **razão**: o `hsv_adaptativo` custa consistentemente ~40% mais que os outros dois, em qualquer execução, porque faz uma conversão de cor e uma média da imagem inteira a mais.

Se você for reportar tempo no TP, reporte mediana, diga em que máquina mediu, e prefira comparar razões a comparar milissegundos.

### Não existe almoço grátis

O `hsv_adaptativo` acha o alvo sempre — **e inventa mais**. O falso positivo subiu de 6,7% para 10,0%.

Isso não é um defeito da implementação: é a natureza do problema. Um detector mais sensível enxerga mais coisa, inclusive coisa que não existe. Sensibilidade e falso positivo sobem juntos, e **escolher onde ficar nesse par é decisão de projeto**, tomada a partir do domínio.

Para um robô que freia, 10% de freada fantasma pode ser inaceitável e 6,7% com alguns alvos perdidos ser preferível. Para um robô que conta frutos, perder alvo é subcontagem sistemática e a escolha se inverte. **O mesmo número significa coisas opostas em domínios diferentes.**

## Parte 5 — Trocar o detector sem trocar a régua

!!! warning "Não trabalhada em 15/09 — recuperada na Aula 10"
    As Partes 5 e 6 não couberam no encontro. Elas foram para a [Aula 10, de 22/09](../etapa05-aula10/index.md), que abre com a clínica de URDF e recupera este bloco. O texto continua aqui, publicado desde 15/09, para quem quiser chegar lá com ele lido — e o conteúdo abaixo ainda vale para o relatório do TP2, que só vence em 25/09.

O `avaliar.py` não sabe nada sobre como o detector funciona. Ele chama uma função que recebe a imagem e devolve `(x, y, w, h)` ou `None`. Plugar um modelo treinado é escrever outra função com essa assinatura.

Essa separação é o ponto arquitetural da aula, e é o mesmo princípio das interfaces da Aula 6: **o contrato fica, o miolo troca**. A régua sobrevive à troca do detector, e é por isso que os números continuam comparáveis.

!!! note "Sobre YOLO, `torch` e a regra da disciplina"
    O gate diz *"YOLO ou equivalente"*, e o equivalente importa. O módulo `cv2.dnn` roda modelos ONNX e Darknet **sem** instalar `torch` nem `ultralytics` — é o OpenCV do apt que vocês já têm.

    Se quiser o ecossistema completo do YOLO, ele vai num **venv** (`uv venv --system-site-packages`), como script solto. Nunca no python do sistema, e nunca dentro de um nó ROS 2 — pelas mesmas razões do `KeyError: 16` da Aula 3.

    E o mais importante: **o que se avalia é a métrica e a justificativa, não o modelo.** Um HSV medido honestamente vale mais que um YOLO sem régua.

## Parte 6 — Clínica de URDF e TF

A segunda metade é bancada aberta sobre o [tutorial de URDF, TF e RViz2](../../tutoriais/urdf-tf-rviz2.md), que cobre o **G2.5**.

**Comece rodando o diagnóstico**, na raiz do seu `ros2_ws` — ele diz em que ponto você parou e qual é o próximo comando:

```bash
bash recursos/clinica-urdf.sh
```

Depois, rode o que ele mandar e traga o que travou:

```bash
check_urdf src/<seuprojeto>_description/urdf/<seu_robo>.urdf
ros2 launch <seuprojeto>_description ver_robo.launch.py
# noutro terminal, com o launch RODANDO:
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo base_footprint camera_link
```

Os três tropeços conhecidos, todos já documentados no tutorial: **TF exige o launch rodando** (sem ele o `view_frames` gera um PDF vazio sem reclamar); **janelas vazias no WSL2** se resolvem por bisseção com o `turtlesim`; e o **`<origin>` do joint confundido com o do visual** deixa o RViz2 parecendo certo com a TF errada.

E vale repetir o que o tutorial diz: **o G2.5 não depende da janela gráfica.** `check_urdf`, `view_frames` e `tf2_echo` rodam no terminal e provam o que o gate pede.

## Tarefa da semana

Duas entregas, as duas para o TP2:

**G2.4** — escolha e **declare** a sua métrica, monte o seu vídeo fixo (gravado ou gerado), e meça pelo menos **duas** versões do seu detector. Commite em `docs/evidencias/tp2/metrica-tracking.md` a métrica escolhida, a justificativa a partir do seu domínio, os números das duas versões e **onde cada uma falha**.

**G2.5** — o seu `<projeto>_description` com URDF validado e árvore de TF coerente. Evidência: `frames.pdf`, um print do RViz2 e o `ros2 param dump` do seu nó parametrizado.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `nao abri cena.avi` | faltou rodar `python3 gerar_video.py` antes do `avaliar.py` |
| todos os detectores dão 100% | você mexeu na cena e tirou a dificuldade; a cena precisa quebrar alguma coisa |
| taxa de alvo mantido acima de 100% | está dividindo pelo total de quadros em vez dos quadros **com alvo presente** |
| IoU sempre 0 | a caixa devolvida está em outro formato — o esperado é `(x, y, largura, altura)` |
| `view_frames` gera PDF vazio | o launch não está rodando — TF é fluxo, não arquivo |
| janelas do RViz2 vazias no WSL2 | bisseção com `turtlesim`; depois `LIBGL_ALWAYS_SOFTWARE=1` |
| `The passed action type is invalid` | terminal sem `source install/setup.bash` |

## Para a próxima aula (22/09)

**[Aterrissagem do TP2](../etapa05-aula10/index.md).** A entrega é 25/09, três dias depois. A aula abre com a clínica de URDF e TF, que fecha o G2.5 no dia em que ele vence, recupera o contrato do detector da Parte 5, e termina montando o `bringup.launch.py` que o TP3 vai cobrar.

Navegação autônoma passa para a Aula 11, em 29/09 — nenhum gate de navegação vence antes de 30/10, e o Nav2 se monta sobre ações e TF coerente, que é justamente o que a Aula 10 fecha.
