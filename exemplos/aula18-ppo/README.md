# Exemplo — `aula18-ppo`

**Aula 18 · Etapa 9.** O item 4 do TP5 diz, no enunciado: *"PPO — Stable Baselines3 em highway-env, 300k steps (≈30 min CPU); comparação com BC; gráfico de barras e análise crítica PID × BC × PPO no relatório final."* O gate **G5.5** pede a curva de recompensa e a política avaliada em **≥10 episódios**, com a evidência em `docs/evidencias/tp5/ppo-curva.png`. Este exemplo percorre esse enunciado de ponta a ponta: o ambiente Python, um treino de 300 mil passos que sobrevive a interrupção, a curva, a avaliação com **duas linhas de base** e o gráfico de barras.

> ## Leia isto antes de qualquer coisa
>
> **300 mil passos não levam 30 minutos.** Nesta máquina (2 núcleos Xeon a 2,1 GHz, torch com 1 thread, outros processos disputando a CPU) levaram **2 h 58 min**, a **28,1 passos por segundo**. Na máquina do professor (WSL2), o treino rodou a **55 passos/s**, estáveis, com a estimativa total de **1 h 31 min** (aos 57 min estava em 188 mil passos). O gargalo é o simulador, que é Python puro, e não a rede. No seu notebook pode ser mais rápido ou mais lento; o que **não** muda é a ordem de grandeza: são horas, não minutos. **Dispare o treino hoje**, em segundo plano, e faça o resto do TP5 enquanto ele roda.
>
> **A recompensa sobe nos primeiros ~10 mil passos e depois fica plana.** Os outros 290 mil não mudaram a curva. A política aprendeu a ir para a faixa da direita e **frear** — e, com isso, a bater bem menos que as linhas de base. Se isso é "dirigir bem" é a pergunta do relatório.
>
> **A recompensa do highway-env não se compara com a do MetaDrive.** O comparativo PID × BC × PPO cruza dois simuladores; a seção **"PPO × BC × PID: o que dá para comparar"** diz o que dá e o que não dá.
>
> O que rodou e o que não rodou está separado em **"O que foi e o que não foi verificado"**, no fim.

```
aula18-ppo/
├── treinar_ppo.py   # PPO do SB3, checkpoints, retomada, progresso com estimativa de termino
├── avaliar.py       # N episodios com sementes fixas: PPO, aleatoria e IDLE nos MESMOS episodios
├── curva.py         # monitor.csv -> ppo-curva.png; resumo.csv -> grafico de barras
├── testar.py        # 5 grupos; prova o que da sem treinar de verdade
└── amostra/         # um treino de verdade: modelo, monitor.csv, curva, avaliacao, barras
```

## Baixar

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"

mkdir -p "$PB_DIR" && cd /tmp && rm -rf pb-a18p && \
  git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git pb-a18p && \
  rm -rf "$PB_DIR/aula18-ppo" && \
  cp -r pb-a18p/exemplos/aula18-ppo "$PB_DIR/"
```

Tudo pende do `git clone` pelo `&&`: se o clone falhar, nenhum `rm -rf` roda. **Cuidado:** o bloco apaga e recria `aula18-ppo/`. Se você treinar **dentro** dessa pasta e baixar de novo, o treino vai junto. Os comandos abaixo gravam o treino em `$PB_DIR/ppo-treino`, fora dela.

## O ambiente — `uv`, Python 3.10 e o torch **só CPU**

O PPO vai num ambiente próprio, `$PB_DIR/.venv-rl`, fora da pasta do exemplo pelo mesmo motivo do treino. Como o venv da CNN da Aula 17, ele nasce **sem** `--system-site-packages`: ele nunca importa ROS 2, e o NumPy 2 dele não pode encontrar pacotes do apt compilados contra o NumPy 1.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; . ~/.bashrc; }
test -x "$PB_DIR/.venv-rl/bin/python" || uv venv --python 3.10 .venv-rl
uv pip install --python .venv-rl/bin/python --torch-backend cpu stable-baselines3 highway-env gymnasium matplotlib
```

O `test -x ... ||` só cria o venv se ele ainda não existe. Sem a guarda, colar o bloco de novo faz o `uv` perguntar `A virtual environment already exists ... replace it?` — e um `yes` **recria o venv embaixo de um treino que está rodando** (aconteceu no ensaio de 16/11; o treino sobreviveu por sorte).

**O `--torch-backend cpu` é a linha que mais importa.** Sem ele, o `uv` resolve o torch do PyPI, que no Linux vem com CUDA: o `uv pip install --dry-run` sem a opção lista **17 pacotes** a mais (`torch`, `triton` e 15 `nvidia-*`), e a soma dos arquivos no PyPI dá **cerca de 3,0 GB** de download (somei os tamanhos publicados; não baixei). Com a opção, o torch vem do índice CPU do PyTorch: **187 MB** de download, e a instalação inteira levou **11 s** aqui. O venv pronto ocupa **977 MB** — 730 MB são o torch. Num WSL2 sem GPU configurada, o CUDA não serve para nada.

Se o seu `uv` responder `unexpected argument '--torch-backend'`, ele é antigo: atualize com `uv self update` e repita a linha.

!!! tip "CPU ou GPU: a GPU não acelera este treino"
    O padrão é CPU, e é nela que todos os números desta página foram medidos. O tempo do PPO está no simulador, que é Python puro; a rede escolhendo uma ação leva uns 0,04 ms. A documentação do Stable Baselines3 diz que o PPO com `MlpPolicy` foi feito para rodar na CPU. Para **medir** com os próprios olhos, o `treinar_ppo.py` aceita `--dispositivo cuda` (padrão `cpu`) num venv separado com o torch de GPU — nunca neste. A receita, e a armadilha da série RTX 50, estão em [CPU ou GPU: os dois caminhos](../../tutoriais/gpu-cpu.md).

As versões que o `uv` resolveu aqui, em 15/11/2026 (30 pacotes):

| pacote | versão |
|---|---|
| Python | 3.10.20 (baixado pelo `uv`) |
| stable-baselines3 | 2.9.2 |
| highway-env | 1.12.1 |
| gymnasium | 1.4.0 |
| torch | 2.14.1+cpu |
| numpy | 2.2.6 |
| matplotlib | 3.10.9 |
| pandas | 2.3.3 (o highway-env usa na observação) |
| pygame-ce | 2.5.8 (só para desenhar; o treino não abre janela) |

O `tensorboard` **não** foi instalado: o `treinar_ppo.py` imprime o progresso e grava o `monitor.csv`, e a curva sai do `curva.py`.

Confira antes de seguir:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
"$PB_DIR/.venv-rl/bin/python" -c "import torch, stable_baselines3, highway_env, gymnasium; print(torch.__version__, stable_baselines3.__version__, gymnasium.__version__, torch.cuda.is_available())"
```

A linha esperada termina em `+cpu 2.9.2 1.4.0 False` (com as versões que o seu `uv` resolver).

## Conferir antes de confiar

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-ppo"
"$PB_DIR/.venv-rl/bin/python" testar.py
```

Cinco grupos, 48 conferências, 1 min 36 s com o venv (quase tudo é o treino de fumaça e o torch subindo três vezes), menos de 1 s sem ele neste container. O teste não prova que o PPO aprende; prova que as peças estão no lugar: os `.py` são ASCII e compilam, as funções puras dão a resposta sabida (estimativa de término, leitura do `monitor.csv` atravessando uma retomada), a `amostra/` tem as colunas combinadas com o `aula18-pid-bc`, e — só com o venv — um treino de 300 passos grava checkpoint, **retoma** dele, continua o `monitor.csv`, desenha a curva e avalia o modelo da amostra. Termina em `todos os testes passaram.` Sem o venv (`python3 testar.py`), o grupo 5 é pulado e diz por quê.

## Treinar

**Terminal A — o treino.** Roda com `nohup`, em segundo plano: você pode fechar o terminal (no WSL2, **não** desligue o Windows nem feche a distribuição — `wsl --shutdown` mata o treino). A saída vai para `treino.log`.

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-ppo"
mkdir -p "$PB_DIR/ppo-treino"
nohup "$PB_DIR/.venv-rl/bin/python" treinar_ppo.py --saida "$PB_DIR/ppo-treino" > "$PB_DIR/ppo-treino/treino.log" 2>&1 &
```

**Terminal B — acompanhar.** Uma linha por minuto, com passos/s e quanto falta; Ctrl+C sai do `tail` sem parar o treino:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
tail -f "$PB_DIR/ppo-treino/treino.log"
```

As linhas são assim (as primeiras desta rodada):

```
treino PPO: highway-fast-v0, alvo 300000 passos (faltam 300000), semente 7, torch com 1 thread(s)
hiperparametros: lr 0.0005, n_steps 768, lote 64, epocas 10, gamma 0.8, rede [256, 256]
a primeira linha de progresso sai em 60 s; Ctrl+C interrompe e o ultimo checkpoint fica em ...
passos    1670/300000   27.8 passos/s  decorrido 1min 00s  falta ~2h58min  ultimos 20 ep: recompensa 8.72, bateu 85%
```

**Se o treino parar** (o notebook dormiu, o WSL2 foi desligado), retome do último checkpoint — um `.zip` a cada 20 mil passos em `checkpoints/`. Troque o número pelo do último arquivo que existe (`ls "$PB_DIR/ppo-treino/checkpoints"`):

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-ppo"
nohup "$PB_DIR/.venv-rl/bin/python" treinar_ppo.py --saida "$PB_DIR/ppo-treino" --retomar "$PB_DIR/ppo-treino/checkpoints/ppo_120000_steps.zip" >> "$PB_DIR/ppo-treino/treino.log" 2>&1 &
```

O `--passos` continua sendo o **total** (300 000 por padrão): o script desconta o que o checkpoint já tem. O `monitor.csv` continua no mesmo arquivo (o `curva.py` lê o segundo cabeçalho que aparece no meio). Os episódios entre o último checkpoint e a queda se perdem, e o eixo de passos da curva fica levemente à frente do contador do modelo — algumas centenas de passos em 300 mil.

**O que os hiperparâmetros são.** Os valores estão no topo do `treinar_ppo.py`, cada um com uma linha de porquê. São os do exemplo de PPO da documentação do highway-env — rede 256×256, `gamma=0.8`, 768 passos por coleta, lotes de 64, 10 épocas, taxa 5·10⁻⁴ —, **não** os padrões do SB3 (`gamma=0.99`, 2048 passos, rede 64×64), que são os do `PPO("MlpPolicy", "highway-fast-v0")` da cheatsheet. O motivo do `gamma` baixo: o episódio tem 30 decisões, e o que importa é não bater nos próximos segundos. A rodada com os padrões do SB3 **não** foi feita aqui. O SB3 completa sempre a coleta de 768: o alvo de 300 000 vira **300 288** passos.

**Por que `highway-fast-v0` e não `highway-v0`.** Medi os dois com ações aleatórias, nesta máquina: **35 passos/s** no `highway-fast-v0` e **3,1 passos/s** no `highway-v0`. O `highway-v0` simula 15 vezes por decisão (o fast, 5), tem 4 faixas e 50 carros (o fast, 3 e 20) e episódios de 40 s (o fast, 30 s). Com ele, 300 mil passos levariam uns **dias**. O fast é a versão que a própria documentação usa para treinar. A configuração exata vai para `config_ambiente.json` ao lado do modelo — e é ela que a avaliação tem de repetir.

## A curva medida

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-ppo"
"$PB_DIR/.venv-rl/bin/python" curva.py --monitor "$PB_DIR/ppo-treino/monitor.csv" --saida "$PB_DIR/ppo-treino/ppo-curva.png"
```

**O tempo.** 300 288 passos em **2 h 58 min** de parede, média de **28,1 passos/s**, com `torch.set_num_threads(1)`, numa CPU de 2 núcleos (Intel Xeon a 2,1 GHz) em que outros processos rodavam ao mesmo tempo — a carga média ficou entre 3 e 4 durante quase todo o treino. A taxa começou em 27,8, caiu a 23 quando um segundo treino rodou ao lado (o da reprodutibilidade, abaixo) e subiu a 28 no fim. O `progresso.txt` da amostra tem todas as linhas, uma por minuto.

De onde vem o tempo: só o simulador, com ações aleatórias e sem rede nenhuma, deu **35 passos/s** nesta máquina. O PPO acrescenta uns 25% de tempo por cima. Mais threads no torch não ajudam (a rede é pequena); dois ambientes em paralelo (`SubprocVecEnv`) deram 31,9 passos/s contra 28,1 com um, numa medida de 2048 passos — pouco, num computador de 2 núcleos ocupado. **O "≈30 min CPU" do enunciado não vale aqui**: exigiria 167 passos/s, seis vezes o medido.

**A curva** é a `amostra/ppo-curva.png` (o G5.5 pede exatamente esta figura). Em números, janelas de 5 mil passos de treino:

```
passos de treino     episodios  recompensa media  bateu
ate 2 000                 168        8,9           90%
2 000 a 5 000             310       11,9           76%
5 000 a 10 000            198       18,8           32%
15 000 a 20 000           210       18,4           43%
45 000 a 50 000           207       18,9           44%
95 000 a 100 000          216       18,4           43%
195 000 a 200 000         221       17,9           46%
295 000 a 300 000         217       18,5           43%
```

**A recompensa sobe e estabiliza em uns 8 a 10 mil passos — uns 6 minutos de treino.** Os 290 mil passos seguintes não mudaram a média. Isso não quer dizer que 300 mil sejam inúteis em qualquer configuração; quer dizer que, **nesta**, a curva parou cedo, e o relatório diz isso com o número.

**A curva de treino mostra 43% de batidas — e a avaliação, menos.** O `monitor.csv` registra os episódios do treino, em que o PPO **sorteia** a ação (é assim que ele explora). A avaliação usa a ação mais provável. São duas políticas diferentes; a armadilha 2 mostra quanto.

**Por que a recompensa empaca perto de 19.** A recompensa do `highway-fast-v0` vai de 0 a 1 **por passo**, e o episódio tem 30 passos: o teto é 30. Pela fórmula (`_reward` no `highway_env/envs/highway_env.py`), um passo **sem batida** vale pelo menos 0,67 — na faixa da esquerda a 72 km/h —, 0,73 na faixa da direita na mesma velocidade, e 1,0 na faixa da direita a 108 km/h. Sobreviver os 30 passos devagar já rende uns 22; ir rápido acrescenta no máximo 8. **Quem paga é a sobrevivência**, e a política aprendeu exatamente isso.

**Reprodutibilidade, na mesma máquina.** Rodei um segundo treino com a mesma semente, até 15 360 passos, em outro processo: os **738 episódios** do `monitor.csv` saíram idênticos aos primeiros 738 da rodada longa — recompensa, duração e batida, linha a linha. Outro treino curto, de 1 536 passos, também. Em **outra** máquina isso não é garantido: na Aula 17 a mesma semente deu números diferentes entre este container e o WSL2 do professor. A **avaliação**, porém, se repetiu: o modelo da amostra, avaliado no WSL2 do professor em 16/11, deu exatamente a tabela abaixo (e os 60% / 40% do `--estocastico`). Com o highway-env, o mesmo modelo e as mesmas sementes, a tabela foi igual nestas duas máquinas — observado nelas, não garantido em outras.

## Avaliar: PPO × aleatória × IDLE

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-ppo"
"$PB_DIR/.venv-rl/bin/python" avaliar.py --modelo "$PB_DIR/ppo-treino/modelo_final.zip" --saida "$PB_DIR/ppo-treino/avaliacao"
"$PB_DIR/.venv-rl/bin/python" curva.py --barras "$PB_DIR/ppo-treino/avaliacao/resumo.csv" --saida-barras "$PB_DIR/ppo-treino/barras.png"
```

Sem esperar o seu treino, o mesmo comando roda sobre o modelo da amostra:

```bash
# ── herda as variáveis do bloco de download ──
: "${PB_WS:?defina PB_USER, PB_DIR e PB_WS — o bloco está no topo desta página}"
cd "$PB_DIR/aula18-ppo"
"$PB_DIR/.venv-rl/bin/python" avaliar.py --modelo amostra/modelo_ppo.zip --saida /tmp/avaliacao-amostra
```

`avaliar.py` roda as três políticas nos **mesmos** episódios — sementes 1000 a 1009, nunca as do treino —, e a mesma semente dá o mesmo trânsito inicial. **Aleatória** sorteia uma das 5 ações a cada passo; **IDLE** escolhe sempre "manter faixa e velocidade-alvo". Sem as duas, o número do PPO não diz nada.

O modelo final, 300 288 passos (`amostra/avaliacao/saida.txt`):

```
RESUMO (10 episodios; media +- desvio entre episodios)
  politica          concluiu   colidiu   vel_media (km/h)  recompensa
  ppo                 70%       30%      86.1 +-  7.1       21.50 +-  5.33
  aleatoria           10%       90%      83.4 +-  9.1        9.75 +-  6.42
  idle                10%       90%      87.4 +-  1.8       13.82 +-  6.28

  o que cada politica fez (soma dos episodios):
  ppo              faixa da direita  99% do tempo, 1.0 trocas/ep, LANE_LEFT=0 IDLE=23 LANE_RIGHT=45 FASTER=85 SLOWER=107
  aleatoria        faixa da direita  21% do tempo, 3.6 trocas/ep, LANE_LEFT=29 IDLE=31 LANE_RIGHT=24 FASTER=22 SLOWER=29
  idle             faixa da direita  30% do tempo, 0.0 trocas/ep, LANE_LEFT=0 IDLE=173 LANE_RIGHT=0 FASTER=0 SLOWER=0
```

As mesmas três políticas em **50** episódios (sementes 1000 a 1049, `amostra/avaliacao-50/`), mais o PPO sorteando a ação:

```
  politica          concluiu   colidiu   vel_media (km/h)  recompensa
  ppo                 68%       32%      83.8 +-  6.1       20.14 +-  6.57
  aleatoria            2%       98%      88.1 +-  8.2        7.16 +-  4.71
  idle                 8%       92%      87.4 +-  2.2       12.86 +-  6.53
  ppo_estocastico     44%       56%      85.4 +-  7.2       18.73 +-  6.76
```

O gráfico de barras é a `amostra/barras.png` (10 episódios) e a `amostra/avaliacao-50/barras.png` (50). Nas taxas, a barra de erro é o intervalo de 95% de Wilson; o desvio-padrão de uma coluna de zeros e uns daria barras que passam de 100%.

**O que a política aprendeu.** Vai para a faixa da direita **uma vez**, no começo (1,0 troca por episódio), e fica lá 99% do tempo (90% nos 50 episódios). Depois alterna acelerar e frear — `SLOWER` é a ação mais escolhida — e anda a 84–86 km/h. Ela também escolhe `LANE_RIGHT` dezenas de vezes já estando na faixa da direita, onde a ação não tem para onde ir. Não ultrapassa, não troca de faixa para fugir de ninguém. É uma política de **ficar na direita e não encostar no da frente**, que é o que a recompensa paga.

**O IDLE não é "não fazer nada" seguro.** Ele bate em 9 de 10. No highway-env, `IDLE` mantém a velocidade-alvo (90 km/h) e a faixa, **sem frear** para o carro da frente: o ego vai em linha reta até alcançar alguém mais lento. Por isso a linha de base mais dura aqui não é a aleatória, é ela: é o que um carro faz sem decidir nada.

**O PPO não ganha em tudo — e isso é achado, não defeito.** Na velocidade média, o IDLE (87,4 km/h) passa o PPO (86,1 em 10 episódios, 83,8 em 50). O PPO comprou a redução de batidas — de 90% para 30% — andando mais devagar. E ele **ainda bate em 3 de 10**: o relatório que chama isso de "aprendeu a dirigir" está errado; "aprendeu a bater três vezes menos que o IDLE, andando de 1 a 4 km/h mais devagar" está certo.

**10 episódios sugerem a diferença entre o PPO e as linhas de base; pelo critério conservador, não a separam — 50 separam.** Com 10, o PPO conclui 7 de 10 (intervalo de 95% de Wilson de 40% a 89%) e o IDLE 1 de 10 (de 2% a 40%): os intervalos se tocam por um fio (39,7% e 40,4%). Com 50, o PPO conclui 34 de 50 (de 54% a 79%) e o IDLE 4 de 50 (de 3% a 19%), e os intervalos ficam longe um do outro. O [`aula19-comparativo`](../aula19-comparativo/index.md) desenha esses intervalos no gráfico de barras. Os 50 episódios em blocos de 10:

```
batidas por bloco de 10    PPO: 3 4 3 3 3    PPO sorteando: 4 6 3 8 7    IDLE: 9 10 9 8 10    aleatoria: 9 10 10 10 10
```

A diferença entre 3 e 9 batidas aparece em qualquer bloco — o sinal é consistente, e é por isso que 10 episódios a **sugerem**; para dizer que ela está medida, o intervalo pede mais episódios. A diferença entre dois **checkpoints** do mesmo treino, não. Avaliados com 10 episódios, os checkpoints de 20k a 180k deram de **0 a 4 batidas** (o de 60k, zero; o de 120k, quatro). Com 50 (`amostra/checkpoints.txt`):

```
checkpoint  episodios  concluiu  colidiu  vel_media_kmh  recompensa
     20000         50       78%      22%           80.1       20.80
     60000         50       84%      16%           81.5       22.04
    120000         50       74%      26%           83.2       20.79
    180000         50       80%      20%           80.9       22.21
    240000         50       78%      22%           82.6       21.62
    300288         50       68%      32%           83.8       20.14
```

O modelo **final** é o que mais bate. Os intervalos de 95% de 16% e 32% em 50 episódios mal se separam (de 8% a 29% e de 21% a 46%): os dados **sugerem** que mais treino não melhorou e pode ter piorado, e não provam. O que eles provam é que "o último checkpoint é o melhor" é uma hipótese, não um fato — e que avaliar dois checkpoints com 10 episódios cada e escolher o maior é escolher pelo sorteio.

## As armadilhas que o enunciado não avisa

**1. "≈30 min CPU".** É a frase do enunciado e da cheatsheet `veiculos-rl.md`, e foi a maior diferença medida aqui: 2 h 58 min. Rodei o trecho da cheatsheet como está — `PPO("MlpPolicy", "highway-fast-v0", verbose=1)` e `model.learn(...)` —, em segundo plano, com a saída num arquivo. O sintoma literal: durante **69 segundos** o arquivo só tem as linhas `Using cpu device`, `Creating environment from the given name 'highway-fast-v0'`, ``Wrapping the env with a `Monitor` wrapper`` e `Wrapping the env in a DummyVecEnv.`; depois aparece a primeira tabela, com `fps | 29`, `time_elapsed | 69` e `total_timesteps | 2048`. Nenhuma linha diz quanto falta — a conta (300 000 ÷ 29 ≈ 2 h 52 min) é sua. E o `model.save` só roda no fim: se o notebook dormir na segunda hora, não sobra nada. O `treinar_ppo.py` imprime a estimativa a cada minuto e grava um checkpoint a cada 20 mil passos por causa disso.

**2. Avaliar sorteando a ação.** O `model.predict(obs)` do SB3 tem `deterministic=False` como padrão: sem o argumento, a avaliação **sorteia** a ação pela distribuição da política, como no treino. Medido com o modelo final, nos mesmos 50 episódios: **32% de batidas com `deterministic=True`, 56% sem**. É o mesmo arquivo `.zip`. O `avaliar.py` usa `deterministic=True`, e o `--estocastico` existe para você ver a diferença. É também por isso que a curva de treino mostra mais batidas que a avaliação.

**3. Avaliar num ambiente diferente do treino.** O modelo treinado no `highway-fast-v0` roda no `highway-v0` **sem erro nenhum** — a observação tem o mesmo formato, 5 veículos × 5 números —, e a recompensa sobe: **29,16** contra 21,50, mesmo modelo, mesmas sementes (`amostra/avaliacao-highway-v0/`). Não ficou melhor: o episódio do `highway-v0` tem 40 s, e não 30, então o teto da recompensa é 40. A estrada também é outra (4 faixas, 50 carros). As batidas foram 1 em 10, contra 3 em 10 — o que, com 10 episódios, não separa nada. A regra: **recompensa só se compara com a mesma configuração**, e o `config_ambiente.json` grava a do treino. Avalie com `--ambiente` igual ao dele.

**4. Mudar a configuração do jeito antigo.** Tutoriais escritos para versões antigas do gym fazem `env.configure({...})`. Com o gymnasium 1.4 e o highway-env 1.12, o sintoma é:

```
AttributeError: 'OrderEnforcing' object has no attribute 'configure'
```

O `gym.make` devolve o ambiente embrulhado. Os dois jeitos que funcionam: `gym.make("highway-fast-v0", config={"lanes_count": 4})`, ou `env.unwrapped.configure({...})` **seguido de** `env.reset()` — sem o reset, a configuração muda no dicionário e a estrada continua a antiga. Se mudar a configuração, ela tem de ser a mesma no treino e na avaliação (armadilha 3).

**5. A barra de progresso do SB3.** `model.learn(..., progress_bar=True)` com a instalação desta página dá `ImportError: You must install tqdm and rich in order to use the progress bar callback.` O `treinar_ppo.py` não precisa dela.

## PPO × BC × PID: o que dá para comparar

O enunciado pede um gráfico de barras com os três. O PID e o BC rodam no **MetaDrive** (exemplo `aula18-pid-bc`); o PPO, no **highway-env**. São dois simuladores, duas estradas, dois carros e dois tráfegos. Não há conserto para isso dentro do TP5, e o relatório que finge que há perde mais do que o que diz.

**Não se compara:**

- **a recompensa.** Cada simulador tem a sua fórmula. A do highway-env vai de 0 a 1 por passo e paga **sobreviver** (veja acima); a do MetaDrive paga avanço na rota e pune sair da faixa. Um 24 aqui e um 300 lá não estão na mesma escala, nem na mesma unidade;
- **a velocidade média como medida de desempenho.** As duas colunas estão em km/h (o `avaliar.py` converte), mas no highway-env o carro escolhe entre 72, 90 e 108 km/h numa autoestrada reta, e no MetaDrive o PID segue uma rota com curvas e cruzamentos. A velocidade descreve o que cada um fez; não diz qual é melhor;
- **a colisão em números absolutos** sem dizer contra o quê: o highway-env tem 20 carros em 3 faixas, sempre; o `aula18-pid-bc` avalia **sem tráfego** (`TRAFEGO = 0.0` no `avaliar.py` de lá), e lá bater é bater em objeto ou sair da pista.

**Dá para pôr lado a lado, com a ressalva escrita:**

- **taxa de colisão em N episódios** e **taxa de conclusão em N episódios** — são frações, sem unidade. Com 10 episódios, cada uma anda em degraus de 10% (e a seção da avaliação mostra quanto ela oscila);
- **a fração do episódio concluída** — `passos / 30` aqui, `fracao_rota` lá;
- **a posição de cada um em relação às linhas de base do próprio simulador.** Essa é a comparação mais honesta: o PPO contra a aleatória e o IDLE **no highway-env**; o PID e o BC contra o que for a linha de base de lá. "O PPO reduziu a colisão de 90% (IDLE) para 30% no highway-env; o BC ficou a X pontos do PID no MetaDrive" é uma frase que se sustenta. "O PPO bateu menos que o BC" não é.

As colunas do `avaliacao_*.csv` são as mesmas nos dois exemplos — `episodio,semente,concluiu,colidiu,vel_media,passos,recompensa` — para o gráfico de barras sair de um script só. **Mesmas colunas não quer dizer mesma tarefa.** O gráfico precisa dizer isso no título ou na legenda.

## O que foi e o que não foi verificado

**Rodou neste container** — Linux sem GPU, 2 núcleos Intel Xeon a 2,1 GHz, 8 GB, Python 3.10.20 instalado pelo `uv`, as versões da tabela do ambiente, com outros processos usando a CPU ao mesmo tempo:

a criação do venv e a instalação com `--torch-backend cpu` (11 s; venv de 977 MB); o `uv pip install --dry-run` **sem** a opção, que listou os 17 pacotes CUDA (o tamanho de ~3,0 GB é a soma do que o PyPI publica, sem baixar); a velocidade do `highway-fast-v0` e do `highway-v0` com ações aleatórias; o `treinar_ppo.py` completo, 300 288 passos em 2 h 58 min, com um thread do torch; um segundo treino de 15 360 passos com a mesma semente, idêntico episódio a episódio; o `SubprocVecEnv` com 2 ambientes, numa medida de 2 048 passos; a avaliação do modelo final em 10 e em 50 episódios com as duas linhas de base, com `deterministic=True` e `False`, e no `highway-v0`; a avaliação de nove checkpoints com 10 episódios e de cinco com 50; o `curva.py` (curva e barras); o trecho da cheatsheet em segundo plano até a primeira tabela; o `env.configure` no gymnasium 1.4 e o `progress_bar=True`; o `testar.py` com e sem o venv (48 conferências); e os conferidores `conferir-caminhos.py` e `conferir-comandos.py` do repositório.

**Não rodou, e é o que você vai encontrar:**

o treino de 300 mil **até o fim no WSL2 com Ubuntu 22.04**. Na máquina do professor, em 15/11, o venv resolveu as mesmas versões desta página (`2.14.1+cpu`, SB3 2.9.2, gymnasium 1.4.0, highway-env 1.12.1) em uns 13 s; o treino curto de 3000 passos fez **50 a 58 passos/s** (53 a 61 s); o de 300 mil rodou a 55 passos/s estáveis e, aos 57 min, estava em 188 mil passos (`ultimos 20 ep: recompensa 18.73, bateu 45%`), com a previsão total de 1 h 31 min — o fim dele e a avaliação do modelo dele ainda não estão aqui. Em 16/11, lá, o `testar.py` passou inteiro e a avaliação do **modelo da amostra** deu a mesma tabela desta página, em 12 a 14 s. A velocidade no seu notebook não foi medida: pode ficar perto de 28 passos/s (esta CPU é lenta e estava dividida), perto de 55, ou abaixo (WSL2 com pouca memória). **Meça nos primeiros cinco minutos** — a linha de progresso dá a estimativa — antes de planejar a semana.

o **render com janela** (`render_mode="human"`, pygame). Nenhum script deste exemplo abre janela, e o container não tem tela. No WSL2 a janela depende do WSLg.

**outras sementes de treino.** Só a semente 7 foi treinada até o fim. Se outra semente estabiliza mais alto, mais baixo ou no mesmo lugar, não se sabe.

os **hiperparâmetros padrão do SB3** (os do trecho da cheatsheet) por 300 mil passos. Só os 2 048 primeiros passos rodaram, para ver o sintoma da armadilha 1.

a mesma semente em **outra máquina**. Não prometa igualdade.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| `AttributeError: 'OrderEnforcing' object has no attribute 'configure'` | `env.configure(...)` no ambiente que o `gym.make` devolve. Use `gym.make("highway-fast-v0", config={...})` ou `env.unwrapped.configure(...)` seguido de `env.reset()` |
| a configuração mudou e nada aconteceu | `env.unwrapped.configure(...)` só vale no próximo `env.reset()` |
| `ImportError: You must install tqdm and rich in order to use the progress bar callback` | `model.learn(..., progress_bar=True)` sem os pacotes extras. O `treinar_ppo.py` não usa barra; imprime uma linha por minuto |
| `unexpected argument '--torch-backend'` | `uv` antigo: `uv self update` |
| a instalação baixa `nvidia-cublas`, `nvidia-cudnn-cu13`... (uns 3 GB) | faltou `--torch-backend cpu` na linha do `uv pip install`. Apague o `.venv-rl` e refaça |
| `No module named stable_baselines3` (ou `highway_env`) | rodou com `python3` em vez de `"$PB_DIR/.venv-rl/bin/python"` |
| `treino.log` parado na linha `a primeira linha de progresso sai em 60 s` | normal no primeiro minuto. Se passar disso, `ps aux \| grep treinar` diz se o processo ainda existe |
| a linha mostra `passos 1139/800` | o SB3 completa a coleta de 768 passos antes de parar; o alvo é arredondado para cima |
| `falta ~3h` e o prazo é amanhã | treine o que der, com checkpoints, e **diga no relatório quantos passos foram**. A curva fica plana muito antes de 300 mil |
| a curva de treino mostra 40–50% de batidas e a avaliação mostra 10% | a curva mede a política **sorteando** ações (o PPO explora); a avaliação usa `deterministic=True`. Ver as armadilhas |
| o PPO avaliado no `highway-v0` foi muito pior | foi treinado no `highway-fast-v0`: outra estrada, outro tráfego. Avalie no ambiente do `config_ambiente.json` |
| `nada a fazer: o checkpoint ja tem N passos` | o `--passos` é o total; o checkpoint já chegou lá |
| `FileNotFoundError: ... 'amostra/modelo_ppo.zip.zip'` | o arquivo **não existe**: quando não acha o caminho dado, o SB3 tenta de novo com `.zip` acrescentado, e a mensagem mostra o nome dobrado. Confira com `ls amostra/`; se faltar ali, baixe o exemplo de novo |
| o seu `modelo_final.zip` não aparece no clone do GitHub | um `*.zip` no `.gitignore` o engoliu. `git check-ignore -v ppo-treino/modelo_final.zip` diz qual regra; acrescente a exceção `!ppo-treino/modelo_final.zip` depois dela, ou ponha o link do modelo no relatório |

## Como adequar ao seu projeto

**Comece hoje e deixe rodando.** O treino não precisa de você. Um treino de 300 mil passos iniciado na véspera do gate é o mais provável motivo de G5.5 atrasado.

**A semente vai no relatório.** Mesma semente, mesmo computador: a mesma curva, episódio por episódio (medido aqui). Outro computador: não prometa igualdade — na Aula 17 a mesma semente deu números diferentes entre esta máquina e o WSL2 do professor.

**Avalie com as linhas de base, sempre.** O número do PPO sozinho não diz nada. O que vai para o relatório é a tabela das três políticas nos mesmos episódios, com o desvio, e o que a política fez (faixa, ações).

**Se mudar alguma coisa** — hiperparâmetro, configuração do ambiente, recompensa —, mude uma de cada vez, com a mesma semente, e avalie com a mesma configuração do treino. O `config_ambiente.json` é a prova de qual foi.

## O que cada arquivo faz

| Arquivo | Papel | Roda com |
|---|---|---|
| `treinar_ppo.py` | PPO (`MlpPolicy`) no `highway-fast-v0`; `Monitor` grava `monitor.csv` (com a coluna `crashed`); checkpoint a cada 20 mil passos; progresso com passos/s e estimativa; `--passos`, `--semente`, `--saida`, `--retomar`, `--threads`, `--checkpoint`, `--relatorio`, `--ambiente`, `--dispositivo` (padrão `cpu`) | venv do PPO |
| `avaliar.py` | N episódios (padrão 10) com sementes 1000, 1001...; PPO (`deterministic=True`), aleatória e IDLE nos mesmos episódios; `avaliacao_<politica>.csv`, `comportamento_<politica>.csv`, `resumo.csv`; `--modelo`, `--episodios`, `--so-linhas-de-base`, `--sem-linhas-de-base`, `--estocastico`, `--ambiente`, `--saida` | venv do PPO |
| `curva.py` | `monitor.csv` → curva (recompensa e batidas, média móvel, eixo em passos); `resumo.csv` → barras; `--monitor`, `--saida`, `--janela`, `--linhas-de-base`, `--barras`, `--saida-barras` | venv do PPO |
| `testar.py` | 5 grupos: higiene, funções puras, amostra, configuração, treino de fumaça com retomada (só com o venv: `--python` ou `PPO_PYTHON`) | qualquer Python 3 (grupo 5: venv do PPO) |
| `amostra/modelo_ppo.zip` | o modelo final, 300 288 passos, semente 7 (1,8 MB) | `avaliar.py --modelo` |
| `amostra/monitor.csv`, `progresso.txt`, `config_ambiente.json` | os 13 008 episódios de treino, as linhas de progresso e a configuração exata | — |
| `amostra/ppo-curva.png`, `barras.png` | a curva do G5.5 (com as linhas de base) e as barras de 10 episódios | — |
| `amostra/avaliacao/` | PPO, aleatória e IDLE em 10 episódios: CSVs, `resumo.csv`, `saida.txt` | — |
| `amostra/avaliacao-50/` | as mesmas em 50 episódios, mais o PPO com `deterministic=False`, e `barras.png` | — |
| `amostra/avaliacao-highway-v0/` | o mesmo modelo avaliado no `highway-v0` (armadilha 3) | — |
| `amostra/checkpoints.txt` | seis checkpoints em 50 episódios | — |

## Licença

MIT, como todo o diretório `exemplos/`.
