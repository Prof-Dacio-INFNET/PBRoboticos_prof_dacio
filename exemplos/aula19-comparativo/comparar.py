#!/usr/bin/env python3
"""Junta CSVs de avaliacao (PID, BC, PPO, linhas de base) numa tabela e num grafico de barras.

APOIO, NAO VEREDITO: este script relata o que achou nos CSVs. Nao decide quem
ganhou, nao valida a entrega, nao antecipa nota e nao substitui o enunciado.

    python3 comparar.py \\
        --csv pid=metadrive/pid.csv bc=metadrive/bc.csv ppo=highway/avaliacao_ppo.csv \\
        --grupo "pid,bc=MetaDrive (SCSCS, sem trafego)" "ppo=highway-fast-v0 (20 carros)" \\
        --png barras.png --md analise.md

Entrada: um CSV por controlador, UMA LINHA POR EPISODIO, com pelo menos as colunas
    episodio,semente,concluiu,colidiu,vel_media
-- as do avaliar.py do aula18-pid-bc (pid.csv, bc.csv, constante.csv) e do
aula18-ppo (avaliacao_<politica>.csv). As colunas a mais sao ignoradas, menos
saiu_da_pista (entra na tabela) e recompensa (so com --recompensa).

--grupo diz em que simulador/cenario cada controlador rodou. Controladores de
grupos diferentes ficam em colunas separadas da figura, cada uma com o nome do
seu grupo, e o script NUNCA os compara entre si. A recompensa (--recompensa)
so aparece dentro de um grupo: recompensa de simuladores diferentes nao vai
para o mesmo eixo.

Nas taxas (concluiu, colidiu, saiu da pista), o intervalo e o de 95% de Wilson.
Com 10 episodios ele e LARGO -- e isso e o que a tabela tem de mostrar.
"""
import argparse
import csv
import math
import os
import sys

CABECALHO = ("Apoio, nao veredito: relato o que achei nos CSVs. Nao decido quem ganhou, "
             "nao valido a entrega,\nnao antecipo nota e nao substituo o enunciado.")
OBRIGATORIAS = ("episodio", "semente", "concluiu", "colidiu", "vel_media")
LINHAS_DE_BASE = ("aleatoria", "idle", "constante")
SEM_GRUPO = "(grupo nao declarado)"
TAXAS = (("concluiu", "concluiu"), ("colidiu", "colidiu"), ("saiu_da_pista", "saiu da pista"))

COR_TAXA = {"concluiu": "#1baf7a", "colidiu": "#eb6834", "saiu_da_pista": "#e0a100"}
COR_BARRA = "#2a78d6"
TINTA = "#0b0b0b"
TINTA2 = "#52514e"


# ---------------------------------------------------------------- contas puras

def wilson(k, n, z=1.96):
    """Intervalo de 95% de Wilson para k sucessos em n episodios -> (baixo, alto).

    Diferente do "p +- 1,96 desvio", nao sai de [0, 1] e nao vira um ponto quando
    k = 0 ou k = n. Com n = 0 nao ha o que medir: devolve (0, 1).
    """
    if n <= 0:
        return 0.0, 1.0
    p = float(k) / n
    den = 1.0 + z * z / n
    centro = (p + z * z / (2.0 * n)) / den
    meia = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / den
    return max(0.0, centro - meia), min(1.0, centro + meia)


def media_desvio(valores):
    """Media e desvio-padrao amostral (n - 1), como os resumos do aula18-pid-bc."""
    n = len(valores)
    if n == 0:
        return float("nan"), float("nan")
    m = sum(valores) / n
    if n < 2:
        return m, 0.0
    return m, math.sqrt(sum((v - m) ** 2 for v in valores) / (n - 1))


def sobrepoem(a, b):
    """Dois intervalos (baixo, alto) se tocam?"""
    return a[0] <= b[1] and b[0] <= a[1]


# ---------------------------------------------------------------- leitura

def ler_csv(caminho):
    """CSV de avaliacao -> lista de dicts (uma linha por episodio).

    Recusa o resumo.csv do aula18-ppo (uma linha por POLITICA, coluna 'politica'):
    ele nao tem as sementes nem os episodios, e o intervalo precisa de k e n.
    """
    with open(caminho, newline="") as arq:
        linhas = list(csv.DictReader(arq))
        colunas = list(linhas[0].keys()) if linhas else []
    if "politica" in colunas and "episodio" not in colunas:
        raise ValueError("%s e um resumo (uma linha por politica), nao uma avaliacao por "
                         "episodio: passe os avaliacao_<politica>.csv" % caminho)
    if not linhas:
        raise ValueError("%s: nenhum episodio no arquivo" % caminho)
    faltam = [c for c in OBRIGATORIAS if c not in colunas]
    if faltam:
        raise ValueError("%s: faltam as colunas %s (tem: %s)"
                         % (caminho, ",".join(faltam), ",".join(colunas)))
    return linhas


def rotulo_do_arquivo(caminho):
    """'x/avaliacao_ppo.csv' -> 'ppo'; 'x/bc.csv' -> 'bc'."""
    nome = os.path.splitext(os.path.basename(caminho))[0]
    return nome[len("avaliacao_"):] if nome.startswith("avaliacao_") else nome


def separar_csv(itens):
    """['pid=a.csv', 'b/avaliacao_ppo.csv'] -> [('pid', 'a.csv'), ('ppo', 'b/...')]."""
    pares = []
    for item in itens:
        if "=" in item:
            rot, cam = item.split("=", 1)
        else:
            rot, cam = rotulo_do_arquivo(item), item
        rot = rot.strip()
        if not rot:
            raise ValueError("rotulo vazio em --csv %s" % item)
        if rot in [r for r, _ in pares]:
            raise ValueError("rotulo repetido em --csv: %s" % rot)
        pares.append((rot, cam))
    return pares


def separar_grupos(itens):
    """['pid,bc=MetaDrive (sem trafego)', 'ppo=highway'] -> {'pid': 'MetaDrive ...', ...}.

    A esquerda do PRIMEIRO '=' vem um ou mais rotulos separados por virgula; a
    direita, o nome do grupo (pode ter virgula e espaco).
    """
    grupos = {}
    for item in itens or []:
        if "=" not in item:
            raise ValueError("--grupo espera rotulos=nome, recebeu: %s" % item)
        esq, nome = item.split("=", 1)
        nome = nome.strip()
        for rot in esq.split(","):
            rot = rot.strip()
            if rot:
                if rot in grupos and grupos[rot] != nome:
                    raise ValueError("%s esta em dois grupos: %s e %s" % (rot, grupos[rot], nome))
                grupos[rot] = nome
    return grupos


def resumir(rotulo, linhas, grupo):
    """Linhas de um CSV -> o resumo de um controlador (dict)."""
    n = len(linhas)
    r = {"rotulo": rotulo, "grupo": grupo, "n": n,
         "sementes": sorted(int(float(x["semente"])) for x in linhas)}
    for chave, _ in TAXAS:
        if chave in linhas[0]:
            k = sum(int(float(x[chave])) for x in linhas)
            r[chave] = (k, wilson(k, n))
        else:
            r[chave] = None
    r["vel"] = media_desvio([float(x["vel_media"]) for x in linhas])
    if "recompensa" in linhas[0]:
        r["recompensa"] = media_desvio([float(x["recompensa"]) for x in linhas])
    else:
        r["recompensa"] = None
    return r


def carregar(pares, grupos):
    return [resumir(rot, ler_csv(cam), grupos.get(rot, SEM_GRUPO)) for rot, cam in pares]


def por_grupo(ctrls):
    """Lista de (grupo, [controladores]) na ordem em que os grupos aparecem."""
    ordem, d = [], {}
    for c in ctrls:
        if c["grupo"] not in d:
            ordem.append(c["grupo"])
            d[c["grupo"]] = []
        d[c["grupo"]].append(c)
    return [(g, d[g]) for g in ordem]


def mesmo_grupo_ou_recusa(ctrls):
    """Recompensa so dentro de UM grupo declarado; o resto e recusado com ValueError."""
    grupos = sorted(set(c["grupo"] for c in ctrls))
    if len(grupos) != 1:
        raise ValueError("recuso: recompensa de grupos diferentes (%s) no mesmo eixo. Cada "
                         "simulador tem a sua formula; os numeros nao estao na mesma escala"
                         % " | ".join(grupos))
    if grupos[0] == SEM_GRUPO:
        raise ValueError("recuso: sem --grupo nao sei se estes controladores rodaram no mesmo "
                         "simulador, e recompensa so se compara dentro de um")
    return grupos[0]


# ---------------------------------------------------------------- texto

def pct(x):
    return "%.0f%%" % (100 * x)


def celula_taxa(t):
    if t is None:
        return "-", "-"
    k, (lo, hi) = t
    return "%s" % k, "%s a %s" % (pct(lo), pct(hi))


def faixa_sementes(s):
    if s and s == list(range(s[0], s[0] + len(s))):
        return "%d a %d" % (s[0], s[-1])
    return ",".join(str(x) for x in s)


def tabela(ctrls):
    """A tabela em markdown (legivel tambem no terminal)."""
    cab = ["grupo", "controlador", "n", "concluiu", "IC 95%", "colidiu", "IC 95%",
           "saiu da pista", "IC 95%", "vel. media km/h", "sementes"]
    linhas = []
    for c in ctrls:
        cel = [c["grupo"], c["rotulo"], str(c["n"])]
        for chave, _ in TAXAS:
            k, ic = celula_taxa(c[chave])
            cel += ["%s/%d" % (k, c["n"]) if k != "-" else "-", ic]
        cel.append("%.1f +- %.1f" % c["vel"])
        cel.append(faixa_sementes(c["sementes"]))
        linhas.append(cel)
    larg = [max(len(cab[i]), *(len(lin[i]) for lin in linhas)) for i in range(len(cab))]
    fmt = lambda cels: "| " + " | ".join(x.ljust(w) for x, w in zip(cels, larg)) + " |"
    out = [fmt(cab), "|" + "|".join("-" * (w + 2) for w in larg) + "|"]
    out += [fmt(lin) for lin in linhas]
    out.append("")
    out.append("IC 95%: intervalo de Wilson da taxa em n episodios. vel. media: media +- "
               "desvio-padrao amostral entre episodios.")
    return "\n".join(out)


def tabela_recompensa(ctrls):
    """Uma tabela de recompensa POR GRUPO, cada uma com o aviso. Devolve (texto, recusas)."""
    out, recusas = [], []
    for g, cs in por_grupo(ctrls):
        cs = [c for c in cs if c["recompensa"] is not None]
        if not cs:
            continue
        try:
            mesmo_grupo_ou_recusa(cs)
        except ValueError as e:
            recusas.append(str(e))
            continue
        out.append("recompensa -- SO dentro de: %s (nao compare com outro grupo)" % g)
        for c in cs:
            out.append("  %-18s %8.2f +- %.2f" % ((c["rotulo"],) + c["recompensa"]))
    return "\n".join(out), recusas


def achados(ctrls):
    """As linhas achei / nao achei / olhe. Nenhuma diz quem e melhor."""
    out = []
    grupos = por_grupo(ctrls)
    out.append("achei %d controlador(es) em %d grupo(s): %s"
               % (len(ctrls), len(grupos), "; ".join("%s -> %s" % (g, ", ".join(
                   c["rotulo"] for c in cs)) for g, cs in grupos)))

    sem = [c["rotulo"] for c in ctrls if c["grupo"] == SEM_GRUPO]
    if sem:
        out.append("olhe: sem --grupo para %s: nao sei em que simulador rodaram; a figura "
                   "os junta numa coluna so" % ", ".join(sem))
    if len(grupos) > 1:
        out.append("olhe: %d grupos diferentes. Colidiu, velocidade e recompensa nao querem "
                   "dizer a mesma coisa entre eles; nao comparo barras de grupos diferentes"
                   % len(grupos))

    ns = sorted(set(c["n"] for c in ctrls))
    if len(ns) > 1:
        out.append("olhe: numero de episodios diferente entre controladores: %s"
                   % ", ".join("%s=%d" % (c["rotulo"], c["n"]) for c in ctrls))
    else:
        out.append("nao achei numero de episodios diferente: todos com %d" % ns[0])

    poucos = [c for c in ctrls if c["n"] < 10]
    for c in poucos:
        out.append("olhe: %s tem %d episodio(s), menos que os 10 do enunciado"
                   % (c["rotulo"], c["n"]))
    if not poucos:
        out.append("nao achei controlador com menos de 10 episodios")

    for g, cs in grupos:
        sem_ref = set(tuple(c["sementes"]) for c in cs)
        if len(cs) > 1 and len(sem_ref) > 1:
            out.append("olhe: sementes diferentes dentro de '%s': %s -- episodios diferentes, "
                       "estradas/transito diferentes" % (g, "; ".join(
                           "%s=%s" % (c["rotulo"], faixa_sementes(c["sementes"])) for c in cs)))
        elif len(cs) > 1:
            out.append("achei as mesmas sementes (%s) em todos de '%s'"
                       % (faixa_sementes(cs[0]["sementes"]), g))
        base = [c["rotulo"] for c in cs
                if any(c["rotulo"].lower().startswith(b) for b in LINHAS_DE_BASE)]
        if base:
            out.append("achei linha de base em '%s': %s" % (g, ", ".join(base)))
        else:
            out.append("olhe: nao achei linha de base em '%s' (nenhum rotulo comeca com %s): "
                       "sem ela, o numero do controlador nao tem com o que se medir"
                       % (g, "/".join(LINHAS_DE_BASE)))

        sobre, separados = 0, []
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                a, b = cs[i], cs[j]
                for chave, nome in TAXAS:
                    if a[chave] is None or b[chave] is None:
                        continue
                    (ka, int_a), (kb, int_b) = a[chave], b[chave]
                    if float(ka) / a["n"] == float(kb) / b["n"]:
                        continue
                    if not sobrepoem(int_a, int_b):
                        separados.append("%s x %s em %s" % (a["rotulo"], b["rotulo"], nome))
                        continue
                    sobre += 1
                    out.append("olhe: %s %d/%d (%s a %s) e %s %d/%d (%s a %s) em '%s': os "
                               "intervalos se sobrepoem -- estes dois nao estao separados "
                               "por estes numeros"
                               % (a["rotulo"], ka, a["n"], pct(int_a[0]), pct(int_a[1]),
                                  b["rotulo"], kb, b["n"], pct(int_b[0]), pct(int_b[1]), nome))
        if len(cs) > 1 and not sobre:
            out.append("nao achei, em '%s', taxas diferentes com intervalos sobrepostos" % g)
        if separados:
            out.append("achei, em '%s', intervalos que nao se tocam: %s"
                       % (g, "; ".join(separados)))
    out.append("")
    out.append("Intervalos que se tocam nao provam que os dois sao iguais: dizem que estes n nao "
               "bastam para\nsepara-los. Mais episodios estreitam o intervalo: com 5 vezes "
               "mais, ele fica com cerca\nde metade da largura.")
    out.append("Isto nao significa que a comparacao esta certa nem que a entrega esta pronta: "
               "esgotei o que\num script enxerga num CSV. O que pesa -- se a regua foi a mesma, "
               "se a analise fala do seu\nprojeto, se as limitacoes estao ditas -- esta no "
               "relatorio, nao aqui.")
    return out


# ---------------------------------------------------------------- figura

def eixo_limpo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#b9b8b2")
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)


def barras_taxas(ax, cs):
    """Concluiu / colidiu / saiu da pista por controlador, com o intervalo de Wilson."""
    chaves = [ch for ch, _ in TAXAS if any(c[ch] is not None for c in cs)]
    larg = 0.8 / len(chaves)
    for j, ch in enumerate(chaves):
        xs, ys, lo, hi, txt = [], [], [], [], []
        for i, c in enumerate(cs):
            if c[ch] is None:
                continue
            k, (a, b) = c[ch]
            y = 100.0 * k / c["n"]
            xs.append(i - 0.4 + larg * (j + 0.5))
            ys.append(y)
            lo.append(y - 100 * a)
            hi.append(100 * b - y)
            txt.append("%d/%d" % (k, c["n"]))
        ax.bar(xs, ys, width=larg * 0.92, color=COR_TAXA[ch], yerr=[lo, hi], capsize=3,
               error_kw={"ecolor": TINTA2, "elinewidth": 1})
        for x, y, h, t in zip(xs, ys, hi, txt):
            ax.text(x, y + h + 1.5, t, ha="center", va="bottom", fontsize=7, color=TINTA)
    ax.set_ylim(0, 112)
    ax.set_xticks(list(range(len(cs))))
    ax.set_xticklabels([c["rotulo"] for c in cs], fontsize=9)
    eixo_limpo(ax)


def barras_simples(ax, cs, chave):
    """Uma barra por controlador, media +- desvio entre episodios (velocidade, recompensa)."""
    pos = list(range(len(cs)))
    med = [c[chave][0] for c in cs]
    dp = [c[chave][1] for c in cs]
    ax.bar(pos, med, width=0.55, color=COR_BARRA, yerr=dp, capsize=4,
           error_kw={"ecolor": TINTA2, "elinewidth": 1})
    for p, m, d in zip(pos, med, dp):
        ax.text(p, m + d, "%.1f" % m, ha="center", va="bottom", fontsize=8, color=TINTA)
    if med:
        ax.set_ylim(0, max(m + d for m, d in zip(med, dp)) * 1.15)
    ax.set_xticks(pos)
    ax.set_xticklabels([c["rotulo"] for c in cs], fontsize=9)
    eixo_limpo(ax)


def desenhar(ctrls, saida, recompensa=False):
    """Uma COLUNA por grupo (simulador). Linhas: taxas; velocidade; recompensa (opcional)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    grupos = por_grupo(ctrls)
    if recompensa:
        for _, cs in grupos:
            mesmo_grupo_ou_recusa(cs)
    nlin = 3 if recompensa else 2
    larguras = [max(2, len(cs)) for _, cs in grupos]
    altura = 3.0 * nlin + 1.0
    fig, eixos = plt.subplots(nlin, len(grupos), squeeze=False,
                              figsize=(max(7.0, 1.45 * sum(larguras) + 1.5), altura),
                              gridspec_kw={"width_ratios": larguras})
    vmax = max(c["vel"][0] + c["vel"][1] for c in ctrls)
    for col, (g, cs) in enumerate(grupos):
        a_tax, a_vel = eixos[0][col], eixos[1][col]
        barras_taxas(a_tax, cs)
        a_tax.set_title("%s\n%d episodios por controlador%s" % (
            g, cs[0]["n"], "" if len(set(c["n"] for c in cs)) == 1 else " (n DIFERENTE)"),
            fontsize=9.5, color=TINTA, loc="left")
        barras_simples(a_vel, cs, "vel")
        a_vel.set_ylim(0, vmax * 1.18)
        if col == 0:
            a_tax.set_ylabel("% dos episodios", color=TINTA)
            a_vel.set_ylabel("velocidade media (km/h)", color=TINTA)
        a_vel.set_title("velocidade media: descreve o que fez, nao ranqueia", fontsize=8.5,
                        color=TINTA2, loc="left")
        if recompensa:
            a_rec = eixos[2][col]
            barras_simples(a_rec, [c for c in cs if c["recompensa"] is not None], "recompensa")
            a_rec.set_title("recompensa: SO dentro deste grupo", fontsize=8.5, color="#b3261e",
                            loc="left")
            if col == 0:
                a_rec.set_ylabel("recompensa por episodio", color=TINTA)
    chaves = [ch for ch, _ in TAXAS if any(c[ch] is not None for c in ctrls)]
    nomes = dict(TAXAS)
    fig.legend(handles=[Patch(color=COR_TAXA[ch], label=nomes[ch]) for ch in chaves],
               loc="upper right", ncol=len(chaves), fontsize=8.5, frameon=False)
    fig.suptitle("Cada coluna e um simulador/cenario diferente: nao compare barras entre "
                 "colunas.\nBarra de erro: IC 95% de Wilson nas taxas; desvio entre "
                 "episodios na velocidade.", x=0.01, ha="left", fontsize=9, color=TINTA2)
    fig.tight_layout(rect=(0, 0, 1, 1.0 - 0.55 / altura))
    fig.savefig(saida, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- analise.md

ESQUELETO = """
## 1. O que cada controlador ve

> Perguntas para responder com o SEU sistema. Nenhuma tem resposta pronta aqui.

- O PID le o estado do simulador (desvio e rumo da faixa). O BC so tem a imagem.
  O PPO recebe uma observacao cinematica dos 5 veiculos mais proximos. O que cada
  um deixa de saber, e o que isso muda na tabela acima?
- Algum deles teria como existir fora do simulador do jeito que esta? O que teria
  de ser trocado (sensor, estimador) para isso?

_escreva aqui_

## 2. O que cada um custou

- Quanto tempo de SEU trabalho e de maquina foi cada linha da tabela: ganhos
  sintonizados a mao (quantas tentativas?), 1000 quadros pilotados (quanto tempo?),
  N mil passos de PPO (quantos de fato, a quantos passos/s, em quanto tempo)?
- O que o custo comprou, medido na tabela -- e o que nao comprou?

_escreva aqui_

## 3. Onde cada um quebra

- O BC: o que aconteceu quando o carro saiu do centro (o empurrao, ou uma curva
  para o lado que o dataset quase nao tem)? Mediu? Com que numeros?
- O PPO: o que a politica aprendeu de fato (em que faixa fica, quantas vezes
  freia)? Isso e "dirigir" ou e "o que a recompensa paga"?
- O PID: de que informacao do simulador ele depende, e em que velocidade ou
  situacao os mesmos ganhos deixam de servir?

_escreva aqui_

## 4. O que estes numeros deixam e nao deixam dizer

- Releia as linhas "olhe:" acima. Quais pares de controladores NAO estao
  separados pelos intervalos? O que voce precisaria (mais episodios? outra
  medida?) para separa-los?
- Se o seu BC foi 8/10 numa maquina e 10/10 em outra, o que a tabela diz sobre
  ele?

_escreva aqui_

## 5. O que NAO da para concluir

- Os controladores que estao em grupos diferentes rodaram em simuladores
  diferentes (estrada, trafego, carro, recompensa). Que frase comparando um com
  o outro voce NAO pode escrever? Que frase voce pode, com a ressalva?

_escreva aqui_

## 6. Limitacoes e trade-offs

- O que voce mudaria primeiro, e qual linha da tabela isso deveria mexer?

_escreva aqui_
"""


def md_intocado(caminho):
    """O arquivo nao existe, ou e um esqueleto em que ninguem escreveu ainda?

    O --md regrava o esqueleto a cada execucao (a receita e idempotente), mas NUNCA
    por cima de um arquivo em que voce ja comecou a escrever: sem a nota do topo ou
    com menos "_escreva aqui_" do que o esqueleto tem, ele se recusa.
    """
    if not os.path.exists(caminho):
        return True
    with open(caminho) as arq:
        texto = arq.read()
    return (texto.startswith("# Analise critica -- ESQUELETO")
            and texto.count("_escreva aqui_") >= ESQUELETO.count("_escreva aqui_"))


def escrever_md(caminho, ctrls, linhas_achados, comando, txt_rec=""):
    with open(caminho, "w") as arq:
        arq.write("# Analise critica -- ESQUELETO\n\n")
        arq.write("> **Isto e um esqueleto, nao uma analise.** O `comparar.py` gerou a tabela "
                  "e as linhas\n> achei/olhe; as secoes abaixo sao PERGUNTAS. Quem escreve as "
                  "respostas e voce, com os\n> numeros do seu projeto. Apague esta nota quando "
                  "terminar.\n>\n> " + CABECALHO.replace("\n", "\n> ") + "\n\n")
        arq.write("Gerado por:\n\n```\n%s\n```\n\n" % comando)
        arq.write("## A tabela\n\n%s\n\n" % tabela(ctrls))
        if txt_rec:
            arq.write("```\n%s\n```\n\n" % txt_rec)
        arq.write("## O que o script achou\n\n```\n%s\n```\n" % "\n".join(linhas_achados))
        arq.write(ESQUELETO)


# ---------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--csv", nargs="+", required=True, metavar="ROTULO=CAMINHO",
                   help="um CSV por controlador; sem ROTULO=, o nome do arquivo")
    p.add_argument("--grupo", nargs="+", metavar="ROTULOS=NOME",
                   help="ex.: 'pid,bc,constante=MetaDrive (sem trafego)'")
    p.add_argument("--png", help="grava o grafico de barras")
    p.add_argument("--md", help="grava a tabela e o ESQUELETO da analise critica")
    p.add_argument("--recompensa", action="store_true",
                   help="acrescenta a recompensa, SO dentro de cada grupo")
    a = p.parse_args(argv)

    print(CABECALHO)
    print("")
    try:
        pares = separar_csv(a.csv)
        grupos = separar_grupos(a.grupo)
        sobra = sorted(set(grupos) - set(r for r, _ in pares))
        if sobra:
            raise ValueError("--grupo cita rotulos que nao estao em --csv: %s" % ", ".join(sobra))
        ctrls = carregar(pares, grupos)
    except (OSError, ValueError) as e:
        print("nao consegui ler: %s" % e)
        return 2

    print(tabela(ctrls))
    txt_rec, recusas = "", []
    if a.recompensa:
        txt_rec, recusas = tabela_recompensa(ctrls)
        print("")
        print("AVISO: a recompensa so se le dentro de um grupo. Cada simulador tem a sua formula.")
        if txt_rec:
            print(txt_rec)
        for r in recusas:
            print(r)
    print("")
    linhas = achados(ctrls)
    for lin in linhas:
        print(lin)

    if a.png:
        if a.recompensa and recusas:
            print("\nrecuso desenhar a recompensa: %s" % recusas[0])
            return 2
        desenhar(ctrls, a.png, recompensa=a.recompensa)
        print("\ngravado: %s" % a.png)
    if a.md and not md_intocado(a.md):
        print("\nnao sobrescrevo %s: parece que voce ja escreveu nele. Grave o esqueleto com "
              "outro nome (--md outro.md) e copie o que precisar." % a.md)
        return 2
    if a.md:
        cmd = "python3 comparar.py " + " ".join(
            ("'%s'" % x) if (" " in x or "(" in x) else x for x in (argv or sys.argv[1:]))
        escrever_md(a.md, ctrls, linhas, cmd, txt_rec)
        print("gravado: %s (ESQUELETO: as respostas sao suas)" % a.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
