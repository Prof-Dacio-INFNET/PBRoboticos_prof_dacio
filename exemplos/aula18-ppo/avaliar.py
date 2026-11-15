#!/usr/bin/env python3
"""Avalia uma politica no highway-env em N episodios com sementes fixas.

    python avaliar.py --modelo rodada/modelo_final.zip           # PPO + 2 linhas de base
    python avaliar.py --modelo amostra/modelo_ppo.zip --episodios 30
    python avaliar.py --so-linhas-de-base                        # sem modelo nenhum

Avalia TRES politicas nos MESMOS episodios (mesma semente = mesmo transito inicial):
    ppo        o modelo do SB3, com deterministic=True (a acao mais provavel)
    aleatoria  uma acao sorteada a cada passo
    idle       "nao faz nada": a acao IDLE sempre (mantem faixa e velocidade-alvo)
Sem as linhas de base, o numero do PPO nao diz nada.

Por episodio: recompensa, colidiu, vel_media (km/h), passos e concluiu -- chegou ao
fim do horizonte (`duration` da config) sem bater. O highway-env nao tem rota:
"concluir" aqui e sobreviver ao episodio inteiro.

Grava em --saida (padrao: avaliacao/):
    avaliacao_<politica>.csv     episodio,semente,concluiu,colidiu,vel_media,passos,recompensa
    comportamento_<politica>.csv o que a politica FEZ: acoes, faixa, distancia
    resumo.csv                   media e desvio de cada metrica, por politica
"""
import argparse
import csv
import math
import pathlib
import sys

COLUNAS = ["episodio", "semente", "concluiu", "colidiu", "vel_media", "passos", "recompensa"]
COLUNAS_COMPORT = ["episodio", "semente", "distancia_m", "frac_faixa_direita",
                   "trocas_faixa", "acao_esquerda", "acao_idle", "acao_direita",
                   "acao_acelera", "acao_freia"]
# a ordem das acoes do DiscreteMetaAction do highway-env (o avaliar.py confere no ambiente)
ACOES = ["LANE_LEFT", "IDLE", "LANE_RIGHT", "FASTER", "SLOWER"]
SEMENTE_BASE = 1000   # episodio i usa a semente SEMENTE_BASE + i; nunca as do treino


def media_desvio(valores):
    """Media e desvio-padrao amostral (n-1). Funcao pura."""
    n = len(valores)
    if n == 0:
        return float("nan"), float("nan")
    m = sum(valores) / n
    if n == 1:
        return m, 0.0
    return m, math.sqrt(sum((v - m) ** 2 for v in valores) / (n - 1))


def resumir(linhas):
    """Lista de dicts (COLUNAS) -> dict com taxas, medias e desvios. Funcao pura."""
    def col(nome):
        return [float(x[nome]) for x in linhas]
    r = {"episodios": len(linhas)}
    for nome in ("concluiu", "colidiu", "vel_media", "passos", "recompensa"):
        r[nome + "_media"], r[nome + "_desvio"] = media_desvio(col(nome))
    return r


def gravar_csv(caminho, colunas, linhas):
    with open(caminho, "w", newline="") as arq:
        w = csv.DictWriter(arq, fieldnames=colunas)
        w.writeheader()
        for lin in linhas:
            w.writerow({k: lin[k] for k in colunas})


def ler_csv(caminho):
    with open(caminho, newline="") as arq:
        return list(csv.DictReader(arq))


def rodar_episodio(env, escolher, semente):
    """Um episodio. escolher(obs) -> acao. Devolve (linha, comportamento)."""
    obs, info = env.reset(seed=semente)
    base = env.unwrapped
    duracao = base.config["duration"] * base.config["policy_frequency"]
    x0 = float(base.vehicle.position[0])
    n_faixas = base.config["lanes_count"]
    total, passos, vel, direita, trocas = 0.0, 0, [], 0, 0
    acoes = [0] * len(ACOES)
    faixa_ant = base.vehicle.lane_index[2]
    colidiu = False
    while True:
        a = int(escolher(obs))
        acoes[a] += 1
        obs, r, term, trunc, info = env.step(a)
        total += float(r)
        passos += 1
        vel.append(3.6 * float(info["speed"]))   # m/s -> km/h, como no aula18-pid-bc
        faixa = base.vehicle.lane_index[2]
        direita += 1 if faixa == n_faixas - 1 else 0
        trocas += 1 if faixa != faixa_ant else 0
        faixa_ant = faixa
        colidiu = colidiu or bool(info.get("crashed"))
        if term or trunc:
            break
    linha = {"semente": semente,
             "concluiu": int(not colidiu and passos >= duracao),
             "colidiu": int(colidiu),
             "vel_media": round(sum(vel) / len(vel), 3),
             "passos": passos,
             "recompensa": round(total, 4)}
    comp = {"semente": semente,
            "distancia_m": round(float(base.vehicle.position[0]) - x0, 1),
            "frac_faixa_direita": round(direita / passos, 3),
            "trocas_faixa": trocas}
    for nome, n in zip(COLUNAS_COMPORT[5:], acoes):
        comp[nome] = n
    return linha, comp


def argumentos(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--modelo", help="o .zip do SB3 (PPO)")
    p.add_argument("--so-linhas-de-base", action="store_true",
                   help="avalia so a aleatoria e a idle, sem modelo")
    p.add_argument("--sem-linhas-de-base", action="store_true",
                   help="avalia so o modelo")
    p.add_argument("--episodios", type=int, default=10)
    p.add_argument("--semente-base", type=int, default=SEMENTE_BASE)
    p.add_argument("--ambiente", default="highway-fast-v0",
                   help="TEM de ser o mesmo do treino (veja o config_ambiente.json)")
    p.add_argument("--estocastico", action="store_true",
                   help="sorteia a acao do PPO (deterministic=False) -- so para comparar")
    p.add_argument("--saida", default="avaliacao")
    return p.parse_args(argv)


def imprimir_tabela(nome, linhas):
    print("\n%s -- %d episodios" % (nome, len(linhas)))
    print("  ep  semente  concluiu  colidiu  vel_km/h  passos  recompensa")
    for x in linhas:
        print("  %2d  %7d  %8s  %7s  %8.1f  %6d  %10.2f"
              % (x["episodio"], x["semente"], "sim" if x["concluiu"] else "nao",
                 "sim" if x["colidiu"] else "nao", x["vel_media"], x["passos"],
                 x["recompensa"]))


def main(argv=None):
    a = argumentos(argv)
    if not a.modelo and not a.so_linhas_de_base:
        print("passe --modelo <arquivo.zip> ou --so-linhas-de-base")
        return 2
    import gymnasium as gym
    import highway_env  # noqa: F401
    import numpy as np

    env = gym.make(a.ambiente)
    nomes_env = env.unwrapped.action_type.actions_indexes
    if [nomes_env.get(n) for n in ACOES] != list(range(len(ACOES))):
        print("olhe: a ordem das acoes deste highway-env e %s, nao a esperada %s"
              % (nomes_env, ACOES))
        return 2
    idle = nomes_env["IDLE"]
    cfg = env.unwrapped.config
    print("ambiente %s: %d faixas, %d carros, %d s de episodio a %d Hz de decisao"
          % (a.ambiente, cfg["lanes_count"], cfg["vehicles_count"], cfg["duration"],
             cfg["policy_frequency"]))
    print("sementes %d a %d (as mesmas para todas as politicas)"
          % (a.semente_base, a.semente_base + a.episodios - 1))

    politicas = []
    if a.modelo:
        import torch
        from stable_baselines3 import PPO
        torch.set_num_threads(1)
        modelo = PPO.load(a.modelo, device="cpu")
        det = not a.estocastico
        nome = "ppo" if det else "ppo_estocastico"
        politicas.append((nome, lambda o: modelo.predict(o, deterministic=det)[0]))
    if not a.sem_linhas_de_base:
        rng = np.random.default_rng(a.semente_base)
        politicas.append(("aleatoria", lambda o: rng.integers(len(ACOES))))
        politicas.append(("idle", lambda o: idle))

    saida = pathlib.Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    resumo = []
    for nome, escolher in politicas:
        linhas, comps = [], []
        for i in range(a.episodios):
            lin, comp = rodar_episodio(env, escolher, a.semente_base + i)
            lin["episodio"] = comp["episodio"] = i
            linhas.append(lin)
            comps.append(comp)
        imprimir_tabela(nome, linhas)
        gravar_csv(saida / ("avaliacao_%s.csv" % nome), COLUNAS, linhas)
        gravar_csv(saida / ("comportamento_%s.csv" % nome), COLUNAS_COMPORT, comps)
        r = resumir(linhas)
        r["politica"] = nome
        tot = [sum(c[k] for c in comps) for k in COLUNAS_COMPORT[5:]]
        r["frac_faixa_direita_media"] = media_desvio(
            [c["frac_faixa_direita"] for c in comps])[0]
        r["trocas_faixa_media"] = media_desvio([c["trocas_faixa"] for c in comps])[0]
        r["acoes"] = " ".join("%s=%d" % (n, t) for n, t in zip(ACOES, tot))
        resumo.append(r)

    print("\nRESUMO (%d episodios; media +- desvio entre episodios)" % a.episodios)
    print("  politica          concluiu   colidiu   vel_media (km/h)  recompensa")
    for r in resumo:
        print("  %-16s  %4.0f%%     %4.0f%%     %5.1f +- %4.1f      %6.2f +- %5.2f"
              % (r["politica"], 100 * r["concluiu_media"], 100 * r["colidiu_media"],
                 r["vel_media_media"], r["vel_media_desvio"],
                 r["recompensa_media"], r["recompensa_desvio"]))
    print("\n  o que cada politica fez (soma dos episodios):")
    for r in resumo:
        print("  %-16s faixa da direita %3.0f%% do tempo, %.1f trocas/ep, %s"
              % (r["politica"], 100 * r["frac_faixa_direita_media"],
                 r["trocas_faixa_media"], r["acoes"]))
    cols = ["politica", "episodios"] + [k for k in resumo[0]
                                       if k.endswith("_media") or k.endswith("_desvio")]
    with open(saida / "resumo.csv", "w", newline="") as arq:
        w = csv.DictWriter(arq, fieldnames=cols + ["acoes"])
        w.writeheader()
        for r in resumo:
            w.writerow({k: (round(r[k], 4) if isinstance(r[k], float) else r[k])
                        for k in cols + ["acoes"]})
    print("\ngravado em %s/ (avaliacao_*.csv, comportamento_*.csv, resumo.csv)" % saida)
    print("olhe: %d episodios dao uma taxa de colisao em degraus de %.0f%%; duas politicas "
          "que diferem em 1 ou 2 batidas nao estao separadas por estes numeros."
          % (a.episodios, 100.0 / a.episodios))
    return 0


if __name__ == "__main__":
    sys.exit(main())
