#!/usr/bin/env python3
"""Prova o que o comparar.py faz, com o Python do sistema (matplotlib e NumPy do apt).

    python3 testar.py

Grupos:
    1. higiene dos .py: ast.parse, ASCII puro, linhas <= 99 colunas
    2. Wilson contra valores publicados (Newcombe, 1998, metodo sem correcao de
       continuidade) e contra os casos de 10 episodios que a aula usa
    3. leitura dos dois formatos (aula18-pid-bc e aula18-ppo), a recusa do resumo.csv
       e do CSV sem coluna obrigatoria, os argumentos --csv e --grupo
    4. cada linha "olhe:" disparada por um caso feito para ela, e calada quando nao cabe
    5. a recusa da recompensa entre grupos (e sem grupo), na funcao e na linha de comando
    6. o PNG gerado de verdade (assinatura, tamanho, pixels que nao sao todos iguais),
       o analise.md com o aviso de ESQUELETO no topo, e a recusa de regravar por cima
       de um analise.md em que o aluno ja escreveu
    7. a amostra/: os CSVs, a saida.txt igual a uma execucao nova, a figura, nada > 2 MB

Termina em "todos os testes passaram." e sai com 0, ou com 1 se algo falhou.
"""
import ast
import contextlib
import csv
import io
import os
import pathlib
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
AMOSTRA = AQUI / "amostra"
sys.dont_write_bytecode = True
sys.path.insert(0, str(AQUI))

import comparar  # noqa: E402

FALHAS = []
COLUNAS_PPO = ["episodio", "semente", "concluiu", "colidiu", "vel_media", "passos", "recompensa"]

# o comando da amostra: o mesmo do README
ARGS_AMOSTRA = [
    "--csv", "pid=amostra/metadrive/pid.csv", "bc=amostra/metadrive/bc.csv",
    "constante=amostra/metadrive/constante.csv",
    "ppo=amostra/highway/avaliacao_ppo.csv", "aleatoria=amostra/highway/avaliacao_aleatoria.csv",
    "idle=amostra/highway/avaliacao_idle.csv",
    "--grupo", "pid,bc,constante=MetaDrive (mapa SCSCS, sem trafego)",
    "ppo,aleatoria,idle=highway-fast-v0 (3 faixas, 20 carros)",
]


def confere(cond, msg):
    print("  [%s] %s" % ("ok" if cond else "FALHOU", msg))
    if not cond:
        FALHAS.append(msg)


def rodar(args):
    """Roda comparar.main(args) e devolve (codigo, saida impressa)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cod = comparar.main(args)
    return cod, buf.getvalue()


def csv_falso(pasta, nome, n, k_concluiu, k_colidiu, semente0=100, extras=None):
    """Escreve um CSV de avaliacao com n episodios e as contagens dadas."""
    cam = os.path.join(pasta, nome)
    cols = COLUNAS_PPO + (list(extras) if extras else [])
    with open(cam, "w", newline="") as arq:
        w = csv.writer(arq)
        w.writerow(cols)
        for i in range(n):
            lin = [i, semente0 + i, int(i < k_concluiu), int(i < k_colidiu), 40.0 + i % 3, 300,
                   100.0 + i]
            lin += [int(i < (extras or {}).get(c, 0)) for c in (extras or [])]
            w.writerow(lin)
    return cam


def grupo1():
    print("1. higiene dos .py")
    for p in sorted(AQUI.glob("*.py")):
        bruto = p.read_bytes()
        try:
            ast.parse(bruto)
            ok_ast = True
        except SyntaxError:
            ok_ast = False
        largas = [i + 1 for i, lin in enumerate(bruto.decode("utf-8").splitlines())
                  if len(lin) > 99]
        confere(ok_ast and all(c < 128 for c in bruto) and not largas,
                "%s: ast ok, ASCII puro, nenhuma linha > 99%s"
                % (p.name, "" if not largas else " (linhas %s)" % largas))


def grupo2():
    print("2. Wilson contra valores conhecidos")
    # Newcombe RG (1998), Stat Med 17:857-872, tabela II, metodo 3 (Wilson sem correcao)
    publicados = [((81, 263), (0.2553, 0.3662)), ((15, 148), (0.0624, 0.1605)),
                  ((0, 20), (0.0, 0.1611)), ((1, 29), (0.0061, 0.1718)),
                  ((29, 29), (0.8830, 1.0))]
    # os de 10 episodios que a tabela da aula mostra (conferidos a mao com a formula)
    aula = [((8, 10), (0.4902, 0.9433)), ((10, 10), (0.7225, 1.0)), ((0, 10), (0.0, 0.2775)),
            ((7, 10), (0.3968, 0.8922)), ((1, 10), (0.0179, 0.4042)),
            ((3, 10), (0.1078, 0.6032)), ((34, 50), (0.5419, 0.7924))]
    for (k, n), (lo, hi) in publicados + aula:
        a, b = comparar.wilson(k, n)
        confere(abs(a - lo) < 6e-5 and abs(b - hi) < 6e-5,
                "wilson(%d, %d) = (%.4f, %.4f), esperado (%.4f, %.4f)" % (k, n, a, b, lo, hi))
    confere(comparar.wilson(0, 0) == (0.0, 1.0), "wilson(0, 0) = (0, 1): sem episodio, sem medida")
    lo10, hi10 = comparar.wilson(7, 10)
    lo50, hi50 = comparar.wilson(35, 50)
    confere((hi50 - lo50) < 0.55 * (hi10 - lo10),
            "a mesma taxa (70%%) com 50 episodios: intervalo %.2f contra %.2f com 10"
            % (hi50 - lo50, hi10 - lo10))
    m, d = comparar.media_desvio([1.0, 2.0, 3.0, 4.0])
    confere(abs(m - 2.5) < 1e-12 and abs(d - 1.2909944) < 1e-6,
            "media_desvio([1,2,3,4]) = 2.5 +- 1.291 (desvio amostral, n-1)")


def grupo3():
    print("3. leitura dos dois formatos")
    md = comparar.ler_csv(str(AMOSTRA / "metadrive" / "bc.csv"))
    confere(len(md) == 10 and "saiu_da_pista" in md[0],
            "aula18-pid-bc (bc.csv): 10 episodios, com saiu_da_pista")
    hw = comparar.ler_csv(str(AMOSTRA / "highway" / "avaliacao_ppo.csv"))
    confere(len(hw) == 10 and "saiu_da_pista" not in hw[0],
            "aula18-ppo (avaliacao_ppo.csv): 10 episodios, sem saiu_da_pista")
    r = comparar.resumir("bc", md, "M")
    confere(r["concluiu"][0] == 8 and r["saiu_da_pista"][0] == 2 and r["colidiu"][0] == 0,
            "bc: concluiu 8, colidiu 0, saiu 2 (os numeros do README do aula18-pid-bc)")
    r = comparar.resumir("ppo", hw, "H")
    confere(r["concluiu"][0] == 7 and r["colidiu"][0] == 3 and r["saiu_da_pista"] is None,
            "ppo: concluiu 7, colidiu 3, sem coluna saiu_da_pista")
    confere(abs(r["vel"][0] - 86.1211) < 1e-3 and abs(r["vel"][1] - 7.1135) < 1e-3,
            "ppo: vel_media 86.12 +- 7.11, igual ao resumo.csv do aula18-ppo")
    with tempfile.TemporaryDirectory() as tmp:
        res = os.path.join(tmp, "resumo.csv")
        with open(res, "w") as arq:
            arq.write("politica,episodios,concluiu_media\nppo,10,0.7\n")
        try:
            comparar.ler_csv(res)
            confere(False, "resumo.csv recusado")
        except ValueError as e:
            confere("resumo" in str(e), "resumo.csv recusado: '%s'" % str(e)[-50:])
        ruim = os.path.join(tmp, "ruim.csv")
        with open(ruim, "w") as arq:
            arq.write("episodio,semente,concluiu\n0,1,1\n")
        try:
            comparar.ler_csv(ruim)
            confere(False, "CSV sem colidiu/vel_media recusado")
        except ValueError as e:
            confere("colidiu" in str(e), "CSV sem colidiu/vel_media recusado, nomeando a coluna")
    pares = comparar.separar_csv(["pid=a/pid.csv", "b/avaliacao_ppo.csv", "x/bc.csv"])
    confere(pares == [("pid", "a/pid.csv"), ("ppo", "b/avaliacao_ppo.csv"), ("bc", "x/bc.csv")],
            "--csv aceita rotulo=caminho e so caminho (avaliacao_ppo.csv -> ppo)")
    g = comparar.separar_grupos(["pid, bc=MetaDrive (SCSCS, sem trafego)", "ppo=highway"])
    confere(g == {"pid": "MetaDrive (SCSCS, sem trafego)", "bc": "MetaDrive (SCSCS, sem trafego)",
                  "ppo": "highway"}, "--grupo: varios rotulos por grupo; virgula no nome vale")
    try:
        comparar.separar_csv(["pid=a.csv", "pid=b.csv"])
        confere(False, "rotulo repetido recusado")
    except ValueError:
        confere(True, "rotulo repetido em --csv recusado")


def olhes(saida):
    return [lin for lin in saida.splitlines() if lin.startswith("olhe:")]


def grupo4():
    print("4. cada linha olhe:")
    with tempfile.TemporaryDirectory() as tmp:
        a = csv_falso(tmp, "a.csv", 10, 10, 0)
        b = csv_falso(tmp, "b.csv", 10, 0, 0)
        base = csv_falso(tmp, "idle.csv", 10, 0, 9)
        # um caso limpo: mesmo n, mesmas sementes, com linha de base, intervalos separados
        _, s = rodar(["--csv", "a=" + a, "b=" + b, "idle=" + base, "--grupo", "a,b,idle=G"])
        confere(olhes(s) == [], "caso limpo: nenhuma linha olhe (%d)" % len(olhes(s)))
        confere("nao achei numero de episodios diferente" in s
                and "nao achei controlador com menos de 10" in s
                and "achei as mesmas sementes (100 a 109)" in s
                and "achei linha de base em 'G': idle" in s,
                "caso limpo: as linhas achei/nao achei correspondentes")
        confere("melhor" not in s.lower() and "venceu" not in s.lower()
                and "ganhou" not in s.lower().replace("nao decido quem ganhou", ""),
                "nenhuma linha diz quem e melhor, venceu ou ganhou")
        # n diferente e menos de 10
        c = csv_falso(tmp, "c.csv", 5, 5, 0)
        _, s = rodar(["--csv", "a=" + a, "c=" + c, "idle=" + base, "--grupo", "a,c,idle=G"])
        confere(any("numero de episodios diferente" in x for x in olhes(s)),
                "olhe: numero de episodios diferente (10 x 5)")
        confere(any("c tem 5 episodio" in x for x in olhes(s)), "olhe: menos de 10 episodios")
        # sementes diferentes no mesmo grupo
        d = csv_falso(tmp, "d.csv", 10, 10, 0, semente0=500)
        _, s = rodar(["--csv", "a=" + a, "d=" + d, "idle=" + base, "--grupo", "a,d,idle=G"])
        confere(any("sementes diferentes dentro de 'G'" in x for x in olhes(s)),
                "olhe: sementes diferentes dentro do mesmo grupo")
        # sementes diferentes em grupos DIFERENTES nao e olhe de semente
        _, s = rodar(["--csv", "a=" + a, "d=" + d, "--grupo", "a=G1", "d=G2"])
        confere(not any("sementes diferentes" in x for x in olhes(s)),
                "sementes diferentes em grupos diferentes: sem olhe de semente")
        confere(any("2 grupos diferentes" in x for x in olhes(s)),
                "olhe: grupos diferentes nao se comparam")
        # intervalos que se sobrepoem (10/10 x 8/10)
        e = csv_falso(tmp, "e.csv", 10, 8, 0)
        _, s = rodar(["--csv", "a=" + a, "e=" + e, "idle=" + base, "--grupo", "a,e,idle=G"])
        confere(any("a 10/10" in x and "e 8/10" in x and "nao estao separados" in x
                    for x in olhes(s)), "olhe: 10/10 e 8/10 com intervalos sobrepostos")
        confere(not any("a 0/10" in x for x in olhes(s)),
                "contagens iguais (0/10 e 0/10 em colidiu) nao viram olhe")
        # falta de linha de base
        _, s = rodar(["--csv", "a=" + a, "b=" + b, "--grupo", "a,b=G"])
        confere(any("nao achei linha de base em 'G'" in x for x in olhes(s)),
                "olhe: grupo sem aleatoria/idle/constante")
        _, s = rodar(["--csv", "a=" + a, "constante-zero=" + b, "--grupo", "a,constante-zero=G"])
        confere(not any("linha de base" in x for x in olhes(s)),
                "'constante-zero' conta como linha de base (prefixo)")
        # sem grupo
        _, s = rodar(["--csv", "a=" + a, "idle=" + base])
        confere(any("sem --grupo" in x for x in olhes(s)), "olhe: controlador sem --grupo")
        # saiu_da_pista entra quando existe
        f = csv_falso(tmp, "f.csv", 10, 8, 0, extras={"saiu_da_pista": 2})
        g = csv_falso(tmp, "g.csv", 10, 10, 0, extras={"saiu_da_pista": 0})
        _, s = rodar(["--csv", "f=" + f, "g=" + g, "--grupo", "f,g=G"])
        confere(any("saiu da pista" in x for x in olhes(s)) and "| 2/10" in s,
                "saiu_da_pista entra na tabela e nos intervalos quando a coluna existe")
        confere(s.rstrip().endswith("nao aqui."), "termina dizendo o que isso nao significa")


def grupo5():
    print("5. recompensa: so dentro de um grupo")
    with tempfile.TemporaryDirectory() as tmp:
        a = csv_falso(tmp, "a.csv", 10, 10, 0)
        b = csv_falso(tmp, "b.csv", 10, 5, 0)
        ca = comparar.resumir("a", comparar.ler_csv(a), "MetaDrive")
        cb = comparar.resumir("b", comparar.ler_csv(b), "highway")
        try:
            comparar.mesmo_grupo_ou_recusa([ca, cb])
            confere(False, "recompensa de dois grupos no mesmo eixo recusada")
        except ValueError as e:
            confere(str(e).startswith("recuso"), "recompensa de dois grupos: '%s...'"
                    % str(e)[:60])
        cs = comparar.resumir("b", comparar.ler_csv(b), comparar.SEM_GRUPO)
        try:
            comparar.mesmo_grupo_ou_recusa([cs])
            confere(False, "recompensa sem grupo declarado recusada")
        except ValueError:
            confere(True, "recompensa sem grupo declarado recusada")
        confere(comparar.mesmo_grupo_ou_recusa([ca]) == "MetaDrive", "um grupo so: aceita")
        png = os.path.join(tmp, "r.png")
        cod, s = rodar(["--csv", "a=" + a, "b=" + b, "--recompensa", "--png", png])
        confere(cod == 2 and not os.path.exists(png) and "recuso" in s,
                "linha de comando sem --grupo e com --recompensa: recusa e nao desenha")
        cod, s = rodar(["--csv", "a=" + a, "b=" + b, "--grupo", "a=G1", "b=G2", "--recompensa",
                        "--png", png])
        confere(cod == 0 and os.path.exists(png) and s.count("SO dentro de:") == 2,
                "com dois grupos declarados: uma tabela de recompensa por grupo, com o aviso")
        cod, s = rodar(["--csv", "a=" + a, "b=" + b, "--grupo", "a=G1", "b=G2"])
        confere("recompensa" not in s.split("achei 2 controlador")[0],
                "sem --recompensa, a recompensa nao aparece na tabela")


def png_ok(caminho):
    import matplotlib.image as mpimg
    with open(caminho, "rb") as arq:
        assinatura = arq.read(8)
    img = mpimg.imread(caminho)
    return (assinatura == b"\x89PNG\r\n\x1a\n" and os.path.getsize(caminho) > 20000
            and img.shape[0] > 300 and img.shape[1] > 500 and float(img.std()) > 0.05,
            "%dx%d, %d bytes, desvio dos pixels %.3f"
            % (img.shape[1], img.shape[0], os.path.getsize(caminho), float(img.std())))


def grupo6():
    print("6. o PNG e o analise.md")
    os.chdir(str(AQUI))
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "barras.png")
        md = os.path.join(tmp, "analise.md")
        cod, _ = rodar(ARGS_AMOSTRA + ["--png", png, "--md", md])
        confere(cod == 0, "comparar.py na amostra sai com 0")
        ok, desc = png_ok(png)
        confere(ok, "PNG de verdade e nao vazio: %s" % desc)
        texto = pathlib.Path(md).read_text()
        confere(texto.startswith("# Analise critica -- ESQUELETO")
                and "Isto e um esqueleto, nao uma analise" in texto[:300],
                "analise.md diz no topo que e ESQUELETO")
        confere(texto.count("_escreva aqui_") >= 6 and "| pid " in texto,
                "analise.md tem a tabela e seis secoes de perguntas em branco")
        cod, _ = rodar(ARGS_AMOSTRA + ["--md", md])
        confere(cod == 0, "--md de novo sobre o esqueleto intocado: regrava (receita idempotente)")
        with open(md, "a") as arq:
            arq.write("minha resposta")
        with open(md) as arq:
            escrito = arq.read().replace("_escreva aqui_", "o PID ve o estado", 1)
        with open(md, "w") as arq:
            arq.write(escrito)
        cod, s = rodar(ARGS_AMOSTRA + ["--md", md])
        intacto = "o PID ve o estado" in pathlib.Path(md).read_text()
        confere(cod == 2 and "nao sobrescrevo" in s and intacto,
                "--md sobre um arquivo em que o aluno ja escreveu: recusa e nao apaga nada")
        png2 = os.path.join(tmp, "r.png")
        cod, _ = rodar(ARGS_AMOSTRA + ["--recompensa", "--png", png2])
        confere(cod == 0 and png_ok(png2)[0], "com --recompensa e grupos declarados: PNG gerado")


def grupo7():
    print("7. a amostra/")
    csvs = sorted(AMOSTRA.rglob("*.csv"))
    confere(len(csvs) == 9, "9 CSVs na amostra (3 MetaDrive, 3 highway, 3 highway-50): %d"
            % len(csvs))
    for p in csvs:
        linhas = comparar.ler_csv(str(p))
        n_esp = 50 if "highway-50" in str(p) else 10
        confere(len(linhas) == n_esp, "%s: %d episodios" % (p.relative_to(AQUI), len(linhas)))
    os.chdir(str(AQUI))
    _, s = rodar(ARGS_AMOSTRA)
    sem_gravado = lambda t: "\n".join(x for x in t.splitlines()
                                       if not x.startswith("gravado:")).rstrip()
    salvo = (AMOSTRA / "saida.txt").read_text()
    confere(sem_gravado(salvo) == sem_gravado(s),
            "amostra/saida.txt igual a uma execucao nova do comando do README")
    ok, desc = png_ok(str(AMOSTRA / "barras.png"))
    confere(ok, "amostra/barras.png: %s" % desc)
    confere((AMOSTRA / "analise.md").read_text().startswith("# Analise critica -- ESQUELETO"),
            "amostra/analise.md e o esqueleto")
    grandes = [p.name for p in AQUI.rglob("*") if p.is_file() and p.stat().st_size > 2 * 2 ** 20]
    confere(not grandes, "nenhum arquivo > 2 MB %s" % (grandes or ""))


def main():
    for g in (grupo1, grupo2, grupo3, grupo4, grupo5, grupo6, grupo7):
        g()
    print("")
    if FALHAS:
        print("%d conferencia(s) falharam:" % len(FALHAS))
        for f in FALHAS:
            print("  - " + f)
        return 1
    print("todos os testes passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
