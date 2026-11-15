#!/usr/bin/env python3
"""Desenha a curva de treino (G5.5) a partir do monitor.csv do Stable Baselines3.

    python curva.py --monitor rodada/monitor.csv --saida ppo-curva.png
    python curva.py --monitor rodada/monitor.csv --linhas-de-base avaliacao/resumo.csv
    python curva.py --barras avaliacao/resumo.csv --saida-barras barras.png

A curva tem dois paineis com o MESMO eixo x (passos de treino):
    em cima   recompensa de cada episodio (pontos claros) e a media movel (linha)
    embaixo   fracao de episodios que terminaram em batida (media movel)
Com --linhas-de-base, a recompensa media da aleatoria e da idle na AVALIACAO entra
como linha horizontal tracejada -- mesma configuracao do ambiente, outras sementes.

O --barras desenha concluiu / colidiu / vel_media por politica; nas taxas, a barra de
erro e o intervalo de 95% de Wilson (10 episodios dao um intervalo largo); na
velocidade, o desvio entre episodios. E o grafico de barras do comparativo do TP5.
"""
import argparse
import csv
import sys

CORES = {"ppo": "#2a78d6", "ppo_estocastico": "#6250d6", "aleatoria": "#eb6834",
         "idle": "#1baf7a"}
COR_PADRAO = "#52514e"
TINTA = "#0b0b0b"
TINTA2 = "#52514e"


def ler_monitor(caminho):
    """monitor.csv do SB3 -> lista de dicts com passo (acumulado), r, l, crashed.

    A primeira linha do arquivo e um comentario JSON (#{"t_start": ...}). Na
    retomada (treinar_ppo.py --retomar) aparece um SEGUNDO cabecalho no meio do
    arquivo; as linhas que nao sao numeros sao puladas. Funcao pura sobre o texto.
    """
    eps = []
    passo = 0
    with open(caminho) as arq:
        cab = None
        for bruta in arq:
            bruta = bruta.strip()
            if not bruta or bruta.startswith("#"):
                continue
            campos = bruta.split(",")
            if campos[0] == "r":
                cab = campos
                continue
            if cab is None:
                continue
            d = dict(zip(cab, campos))
            passo += int(float(d["l"]))
            eps.append({"passo": passo, "r": float(d["r"]), "l": int(float(d["l"])),
                        "crashed": d.get("crashed", "") == "True"})
    return eps


def media_movel(valores, janela):
    """Media dos ultimos `janela` valores (menos no comeco). Mesmo tamanho da entrada."""
    out, soma = [], 0.0
    for i, v in enumerate(valores):
        soma += v
        if i >= janela:
            soma -= valores[i - janela]
        out.append(soma / min(i + 1, janela))
    return out


def wilson(taxa, n, z=1.96):
    """Intervalo de 95% de Wilson para uma proporcao medida em n episodios."""
    if n <= 0:
        return 0.0, 1.0
    den = 1 + z * z / n
    centro = (taxa + z * z / (2 * n)) / den
    meia = z * ((taxa * (1 - taxa) / n + z * z / (4 * n * n)) ** 0.5) / den
    return max(0.0, centro - meia), min(1.0, centro + meia)


def ler_resumo(caminho):
    with open(caminho, newline="") as arq:
        return list(csv.DictReader(arq))


def eixo_limpo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#b9b8b2")
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)


def desenhar_curva(eps, saida, janela, titulo, base=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = [e["passo"] for e in eps]
    r = [e["r"] for e in eps]
    b = [1.0 if e["crashed"] else 0.0 for e in eps]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1.6]})
    a1.plot(x, r, ".", color="#86b6ef", markersize=2.5, alpha=0.5,
            label="recompensa do episodio")
    a1.plot(x, media_movel(r, janela), color=CORES["ppo"], linewidth=2,
            label="media movel (%d episodios)" % janela)
    for lin in base or []:
        nome = lin["politica"]
        if nome.startswith("ppo"):
            continue
        y = float(lin["recompensa_media"])
        a1.axhline(y, color=CORES.get(nome, COR_PADRAO), linestyle="--", linewidth=1.5,
                   label="%s na avaliacao (%.1f)" % (nome, y))
    a1.set_ylabel("recompensa por episodio", color=TINTA)
    a1.set_title(titulo, color=TINTA, fontsize=11, loc="left")
    a1.legend(fontsize=8, loc="lower right", framealpha=0.9, edgecolor="none")
    eixo_limpo(a1)
    a2.plot(x, [100 * v for v in media_movel(b, janela)], color=CORES["ppo"], linewidth=2)
    a2.set_ylabel("bateu (%%, %d ep)" % janela, color=TINTA)
    a2.set_ylim(0, 100)
    a2.set_xlabel("passos de treino", color=TINTA)
    eixo_limpo(a2)
    a2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: "%gk" % (v / 1000) if v else "0"))
    fig.tight_layout()
    fig.savefig(saida, dpi=110)
    plt.close(fig)


def desenhar_barras(resumo, saida, titulo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    nomes = [x["politica"] for x in resumo]
    cores = [CORES.get(n, COR_PADRAO) for n in nomes]
    n_ep = resumo[0]["episodios"]
    paineis = [("concluiu", "concluiu o episodio (%)", 100),
               ("colidiu", "colidiu (%)", 100),
               ("vel_media", "velocidade media (km/h)", 1)]
    fig, eixos = plt.subplots(1, 3, figsize=(10, 3.6))
    for ax, (chave, rotulo, esc) in zip(eixos, paineis):
        med = [esc * float(x[chave + "_media"]) for x in resumo]
        if esc == 100:   # taxa: intervalo de Wilson, nao o desvio de zeros e uns
            ints = [wilson(float(x[chave + "_media"]), int(x["episodios"]))
                    for x in resumo]
            baixo = [m - 100 * lo for m, (lo, hi) in zip(med, ints)]
            cima = [100 * hi - m for m, (lo, hi) in zip(med, ints)]
        else:
            baixo = cima = [float(x[chave + "_desvio"]) for x in resumo]
        pos = list(range(len(nomes)))
        ax.bar(pos, med, color=cores, width=0.6, yerr=[baixo, cima], capsize=4,
               error_kw={"ecolor": TINTA2, "elinewidth": 1})
        for p, m, c in zip(pos, med, cima):
            ax.text(p + 0.08, m + c, "%.0f" % m if esc == 100 else "%.1f" % m,
                    ha="left", va="bottom", fontsize=9, color=TINTA)
        ax.set_xticks(pos)
        ax.set_xticklabels(nomes, fontsize=9)
        ax.set_title(rotulo, fontsize=10, color=TINTA)
        if esc == 100:
            ax.set_ylim(0, 112)
        eixo_limpo(ax)
    fig.suptitle("%s -- %s episodios; barra de erro: intervalo de 95%% (Wilson) nas "
                 "taxas, desvio entre episodios na velocidade" % (titulo, n_ep),
                 fontsize=9, color=TINTA2)
    fig.tight_layout()
    fig.savefig(saida, dpi=110)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--monitor", help="o monitor.csv do treino")
    p.add_argument("--saida", default="ppo-curva.png")
    p.add_argument("--janela", type=int, default=50, help="episodios da media movel")
    p.add_argument("--linhas-de-base", help="resumo.csv do avaliar.py")
    p.add_argument("--barras", help="resumo.csv do avaliar.py -> grafico de barras")
    p.add_argument("--saida-barras", default="barras.png")
    p.add_argument("--titulo", default="PPO no highway-fast-v0")
    a = p.parse_args(argv)
    if not a.monitor and not a.barras:
        print("passe --monitor e/ou --barras")
        return 2
    if a.monitor:
        eps = ler_monitor(a.monitor)
        if not eps:
            print("nao achei episodios em %s" % a.monitor)
            return 1
        base = ler_resumo(a.linhas_de_base) if a.linhas_de_base else None
        desenhar_curva(eps, a.saida, a.janela, a.titulo, base)
        ult = eps[-a.janela:]
        print("achei %d episodios, %d passos; ultimos %d: recompensa media %.2f, bateu %.0f%%"
              % (len(eps), eps[-1]["passo"], len(ult), sum(e["r"] for e in ult) / len(ult),
                 100 * sum(e["crashed"] for e in ult) / len(ult)))
        print("gravado: %s" % a.saida)
    if a.barras:
        desenhar_barras(ler_resumo(a.barras), a.saida_barras, a.titulo)
        print("gravado: %s" % a.saida_barras)
    return 0


if __name__ == "__main__":
    sys.exit(main())
