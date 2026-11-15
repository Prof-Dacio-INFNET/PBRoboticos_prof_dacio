#!/usr/bin/env python3
"""Treina um PPO (Stable Baselines3) no highway-env, com checkpoints e retomada.

    python treinar_ppo.py                                  # 300000 passos, semente 7
    python treinar_ppo.py --passos 20000 --saida rodada-curta
    python treinar_ppo.py --retomar rodada/checkpoints/ppo_120000_steps.zip

Grava em --saida (padrao: rodada/):
    monitor.csv            uma linha por episodio de treino (Monitor do SB3):
                           r = recompensa, l = passos, t = segundos, crashed = bateu
    checkpoints/           ppo_<passos>_steps.zip a cada --checkpoint passos
    modelo_final.zip       o modelo no fim do treino
    config_ambiente.json   a configuracao EXATA do ambiente usada no treino
    progresso.txt          as mesmas linhas de progresso impressas na tela

Imprime uma linha de progresso a cada --relatorio segundos: passos, passos/s,
estimativa de termino e a recompensa media dos ultimos episodios. Sem isso, um
treino de horas parece travado.
"""
import argparse
import json
import os
import pathlib
import sys
import time

# ---------------------------------------------------------------------------
# Hiperparametros -- declarados ANTES de qualquer resultado. Os valores sao os
# do exemplo de PPO da documentacao do highway-env, nao os padroes do SB3.
# ---------------------------------------------------------------------------
AMBIENTE = "highway-fast-v0"  # 3 faixas, 20 carros, 5 Hz de simulacao: ~10x mais rapido
#                               que o highway-v0 nesta CPU (o README traz a medida)
POLITICA = "MlpPolicy"        # a observacao e uma tabela 5x5 de numeros, nao imagem
REDE = [256, 256]             # duas camadas de 256, para a politica e para o valor
TAXA_APRENDIZADO = 5e-4       # Adam; o padrao do SB3 (3e-4) tambem funciona, mais devagar
N_PASSOS = 768                # passos coletados por atualizacao (12 lotes de 64)
LOTE = 64                     # tamanho do minilote do gradiente
EPOCAS = 10                   # passadas sobre cada coleta de 768 passos
GAMMA = 0.8                   # horizonte curto: o que importa e nao bater nos proximos ~5 s
#                               (0.99, o padrao do SB3, valoriza 100 passos; o episodio tem 30)
PASSOS_PADRAO = 300_000       # o que o TP5 pede
CHECKPOINT_PADRAO = 20_000    # um .zip a cada 20k passos: ~12 min de treino nesta CPU
THREADS_PADRAO = 1            # o gargalo e o simulador (Python puro), nao a rede

AQUI = pathlib.Path(__file__).resolve().parent


def fmt_tempo(seg):
    """Segundos -> 'HhMMmin' ou 'MMmin SSs'. Funcao pura (o testar.py confere)."""
    seg = max(0, int(round(seg)))
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    if h:
        return "%dh%02dmin" % (h, m)
    return "%dmin %02ds" % (m, s)


def estimar_termino(feitos, alvo, decorrido):
    """Segundos que faltam, supondo a taxa media ate agora. None se nao da para dizer."""
    if feitos <= 0 or decorrido <= 0:
        return None
    return (alvo - feitos) / (feitos / decorrido)


def passos_do_checkpoint(caminho):
    """'ppo_120000_steps.zip' -> 120000. None se o nome nao for de checkpoint."""
    nome = pathlib.Path(caminho).name
    partes = nome.replace(".zip", "").split("_")
    for i, p in enumerate(partes):
        if p == "steps" and i > 0 and partes[i - 1].isdigit():
            return int(partes[i - 1])
    return None


def config_serializavel(cfg):
    """A config do highway-env tem tuplas e tipos do numpy; o json nao aceita tudo."""
    def conv(v):
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [conv(x) for x in v]
        if hasattr(v, "item"):
            return v.item()
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        return str(v)
    return conv(dict(cfg))


def argumentos(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--passos", type=int, default=PASSOS_PADRAO,
                   help="passos TOTAIS de treino (contando os do checkpoint retomado)")
    p.add_argument("--semente", type=int, default=7)
    p.add_argument("--saida", default="rodada")
    p.add_argument("--ambiente", default=AMBIENTE)
    p.add_argument("--checkpoint", type=int, default=CHECKPOINT_PADRAO,
                   help="salva um checkpoint a cada N passos")
    p.add_argument("--retomar", help="caminho de um checkpoint .zip para continuar dele")
    p.add_argument("--threads", type=int, default=THREADS_PADRAO,
                   help="threads do torch (torch.set_num_threads)")
    p.add_argument("--relatorio", type=float, default=60.0,
                   help="segundos entre duas linhas de progresso")
    return p.parse_args(argv)


def main(argv=None):
    a = argumentos(argv)
    # imports pesados aqui dentro: o testar.py importa este arquivo sem o torch
    import gymnasium as gym
    import highway_env  # noqa: F401  (registra os ambientes highway-*)
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv

    torch.set_num_threads(a.threads)
    saida = pathlib.Path(a.saida)
    (saida / "checkpoints").mkdir(parents=True, exist_ok=True)
    log = open(saida / "progresso.txt", "a")

    def diga(msg):
        print(msg, flush=True)   # flush: com nohup e saida em arquivo, sem ele nada aparece
        log.write(msg + "\n")
        log.flush()

    retomando = bool(a.retomar)

    def fabrica():
        env = gym.make(a.ambiente)
        # override_existing=False: na retomada, o monitor.csv continua em vez de recomecar
        return Monitor(env, str(saida / "monitor.csv"), info_keywords=("crashed",),
                       override_existing=not retomando)

    venv = DummyVecEnv([fabrica])
    venv.seed(a.semente)
    cfg = config_serializavel(venv.envs[0].unwrapped.config)
    with open(saida / "config_ambiente.json", "w") as arq:
        json.dump({"ambiente": a.ambiente, "config": cfg}, arq, indent=1, sort_keys=True)

    if retomando:
        modelo = PPO.load(a.retomar, env=venv, device="cpu")
        ja = modelo.num_timesteps
        diga("retomando de %s: %d passos ja feitos" % (a.retomar, ja))
    else:
        modelo = PPO(POLITICA, venv, learning_rate=TAXA_APRENDIZADO, n_steps=N_PASSOS,
                     batch_size=LOTE, n_epochs=EPOCAS, gamma=GAMMA,
                     policy_kwargs=dict(net_arch=dict(pi=REDE, vf=REDE)),
                     seed=a.semente, device="cpu", verbose=0)
        ja = 0
    faltam = a.passos - ja
    if faltam <= 0:
        diga("nada a fazer: o checkpoint ja tem %d passos (alvo %d)" % (ja, a.passos))
        return 0

    class Progresso(BaseCallback):
        def _on_training_start(self):
            self.t0 = time.time()
            self.passo0 = self.model.num_timesteps
            self.ultimo = self.t0
            self.recomp = []
            self.batidas = []

        def _on_step(self):
            for info in self.locals.get("infos", []):
                ep = info.get("episode")
                if ep:
                    self.recomp.append(ep["r"])
                    self.batidas.append(1 if info.get("crashed") else 0)
            agora = time.time()
            if agora - self.ultimo >= a.relatorio:
                self.ultimo = agora
                self.imprime(agora)
            return True

        def imprime(self, agora):
            feitos = self.model.num_timesteps - self.passo0
            dec = agora - self.t0
            resta = estimar_termino(min(feitos, faltam), faltam, dec)
            ult_r = self.recomp[-20:]
            ult_b = self.batidas[-20:]
            media = sum(ult_r) / len(ult_r) if ult_r else float("nan")
            bat = sum(ult_b) / len(ult_b) if ult_b else float("nan")
            diga("passos %7d/%d  %5.1f passos/s  decorrido %s  falta ~%s  "
                 "ultimos %d ep: recompensa %.2f, bateu %.0f%%"
                 % (self.model.num_timesteps, a.passos, feitos / dec if dec else 0,
                    fmt_tempo(dec), fmt_tempo(resta) if resta is not None else "?",
                    len(ult_r), media, 100 * bat))

    salvar = CheckpointCallback(save_freq=a.checkpoint, save_path=str(saida / "checkpoints"),
                                name_prefix="ppo")
    diga("treino PPO: %s, alvo %d passos (faltam %d), semente %d, torch com %d thread(s)"
         % (a.ambiente, a.passos, faltam, a.semente, a.threads))
    diga("hiperparametros: lr %g, n_steps %d, lote %d, epocas %d, gamma %g, rede %s"
         % (TAXA_APRENDIZADO, N_PASSOS, LOTE, EPOCAS, GAMMA, REDE))
    diga("a primeira linha de progresso sai em %.0f s; Ctrl+C interrompe e o ultimo "
         "checkpoint fica em %s" % (a.relatorio, saida / "checkpoints"))
    prog = Progresso()
    t0 = time.time()
    try:
        modelo.learn(total_timesteps=faltam, callback=[salvar, prog],
                     reset_num_timesteps=not retomando)
    except KeyboardInterrupt:
        diga("interrompido em %d passos" % modelo.num_timesteps)
        modelo.save(str(saida / ("ppo_interrompido_%d_steps" % modelo.num_timesteps)))
        diga("salvo: %s" % (saida / ("ppo_interrompido_%d_steps.zip" % modelo.num_timesteps)))
        return 130
    prog.imprime(time.time())
    modelo.save(str(saida / "modelo_final"))
    dur = time.time() - t0
    feitos = modelo.num_timesteps - ja
    diga("fim: %d passos em %s (%.1f passos/s); modelo em %s"
         % (modelo.num_timesteps, fmt_tempo(dur), feitos / dur if dur else 0,
            saida / "modelo_final.zip"))
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
