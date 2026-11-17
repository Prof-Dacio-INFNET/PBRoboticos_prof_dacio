# MetaDrive · highway-env · Stable Baselines3 · PID — referência (TP4–TP5)

São **dois ambientes** com `uv`, e eles não se misturam: o do MetaDrive (com o `simple-pid`, onde o PID dirige) e o do PPO (com o torch **só CPU**). Os blocos completos, com as conferências, estão nos exemplos [`aula17-metadrive`](../exemplos/aula17-metadrive/index.md), [`aula18-pid-bc`](../exemplos/aula18-pid-bc/index.md) e [`aula18-ppo`](../exemplos/aula18-ppo/index.md).

```bash
# ── uma vez por terminal ──────────────────────────────
export PB_USER=seu-usuario-github          # ← troque pelo seu usuário do GitHub
export PB_DIR="$HOME/projeto-pb-$PB_USER"
export PB_WS="$PB_DIR/ros2_ws"
cd "$PB_DIR"
# MetaDrive + PID (Python 3.10 obrigatório: o panda3d do MetaDrive 0.4.3 não tem wheel para 3.12)
uv venv --python 3.10 --system-site-packages .venv-metadrive
uv pip install --python .venv-metadrive/bin/python "metadrive-simulator==0.4.3" simple-pid
# PPO: sem --torch-backend cpu o uv traz o torch com CUDA (17 pacotes, ~3 GB) que não ajuda aqui
test -x .venv-rl/bin/python || uv venv --python 3.10 .venv-rl
uv pip install --python .venv-rl/bin/python --torch-backend cpu stable-baselines3 highway-env gymnasium matplotlib
```

```python
# MetaDrive (percepção veicular; roda em CPU)
import metadrive, gymnasium as gym
env = gym.make("MetaDrive-validation-v0", config={"use_render": False})
obs,_ = env.reset(); obs,r,term,trunc,info = env.step(env.action_space.sample())
```
```python
# PID (controle clássico)
from simple_pid import PID
pid = PID(1.0, 0.1, 0.05, setpoint=0.0)   # ex.: manter centro da faixa
correcao = pid(erro_lateral, dt=0.1)      # em simulação, passe SEMPRE o dt do simulador:
                                          # sem ele o simple-pid usa o relógio do computador
```
```python
# PPO (aprendizado por reforço) com Stable Baselines3 -- com checkpoint
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
model = PPO("MlpPolicy", "highway-fast-v0", verbose=1)
ck = CheckpointCallback(save_freq=20_000, save_path="checkpoints", name_prefix="ppo")
model.learn(total_timesteps=300_000, callback=ck)   # HORAS, não minutos: ver abaixo
model.save("ppo_highway")
# avaliar: model.predict(obs, deterministic=True) -- o padrão (False) SORTEIA a ação
```

**Quanto tempo leva.** O "~30 min de CPU" do enunciado **não** se confirmou: medido numa CPU de 2 núcleos com carga, 300 mil passos levaram **2 h 58 min** (28 passos/s). O gargalo é o simulador, que é Python puro — mais threads ou GPU não aceleram. Meça os passos/s do **seu** treino nos primeiros minutos e faça a conta; dispare-o em segundo plano (`nohup`) e faça o resto do TP5 enquanto ele roda. Sem checkpoint, um notebook que dorme na segunda hora não deixa nada. O exemplo [`aula18-ppo`](../exemplos/aula18-ppo/index.md) tem o treino com progresso, checkpoint e retomada, e os hiperparâmetros da documentação do highway-env (não os padrões do SB3, que são os do trecho acima).

**CPU ou GPU.** PPO com `MlpPolicy`: GPU não acelera (o tempo está no simulador; a doc do SB3 recomenda CPU), e o `treinar_ppo.py` usa `--dispositivo cpu` por padrão. MetaDrive com câmera: a placa de vídeo já desenha pelo WSLg, sem CUDA — `glxinfo -B` diz qual placa. Detalhes: [CPU ou GPU: os dois caminhos](../tutoriais/gpu-cpu.md).

Behavioral Cloning: colete pares (quadro → ação) de pilotagem humana e treine uma CNN (ver [deep-learning.md](deep-learning.md) e o [`aula18-pid-bc`](../exemplos/aula18-pid-bc/index.md)). Compare PID × BC × PPO em taxa de colisão, velocidade média e conclusão de rota (TP5) — **cada um contra as linhas de base do próprio simulador**: o PID e o BC rodam no MetaDrive e o PPO no highway-env, e a recompensa de um não se compara com a do outro.
