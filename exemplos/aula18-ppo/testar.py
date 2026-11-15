#!/usr/bin/env python3
"""Prova o que da para provar sem treinar de verdade.

    python3 testar.py                                        # grupos 1 a 4
    python3 testar.py --python "$PB_DIR/.venv-rl/bin/python" # + grupo 5 (treino de fumaca)

Grupos:
    1. higiene dos .py: ast.parse, ASCII puro, linhas <= 99 colunas
    2. funcoes puras com resposta sabida (tempo, estimativa, checkpoint, media,
       desvio, media movel, leitura do monitor.csv com retomada no meio)
    3. a amostra/: colunas do CSV de avaliacao (as mesmas do aula18-pid-bc),
       10 episodios por politica, coerencia concluiu/colidiu/passos, resumo.csv
       bate com os CSVs, monitor.csv legivel, modelo < 2 MB, PNG de verdade
    4. a config do ambiente gravada na amostra e a do highway-fast-v0
    5. SO COM O VENV (stable-baselines3 + highway-env): treina 300 passos, retoma
       do checkpoint ate 1536, confere que o monitor.csv continuou; avalia o
       modelo da amostra em 3 episodios e compara com a amostra; desenha a curva

Termina em "todos os testes passaram." e sai com 0, ou com 1 se algo falhou.
"""
import argparse
import ast
import csv
import json
import os
import pathlib
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
AMOSTRA = AQUI / "amostra"
sys.path.insert(0, str(AQUI))

import avaliar  # noqa: E402  (os imports pesados ficam dentro do main)
import curva  # noqa: E402
import treinar_ppo  # noqa: E402

FALHAS = []
POLITICAS = ("ppo", "aleatoria", "idle")


def confere(cond, msg):
    print("  [%s] %s" % ("ok" if cond else "FALHOU", msg))
    if not cond:
        FALHAS.append(msg)


def grupo1():
    print("1. higiene dos .py")
    for p in sorted(AQUI.glob("*.py")):
        bruto = p.read_bytes()
        try:
            ast.parse(bruto)
            ok_ast = True
        except SyntaxError:
            ok_ast = False
        ascii_ok = all(c < 128 for c in bruto)
        largas = [i + 1 for i, lin in enumerate(bruto.decode("utf-8").splitlines())
                  if len(lin) > 99]
        confere(ok_ast and ascii_ok and not largas,
                "%s: ast ok, ASCII puro, nenhuma linha > 99%s"
                % (p.name, "" if not largas else " (linhas %s)" % largas))


def grupo2():
    print("2. funcoes puras")
    t = treinar_ppo
    confere(t.fmt_tempo(59) == "0min 59s", "fmt_tempo(59) = '0min 59s'")
    confere(t.fmt_tempo(3 * 3600 + 7 * 60) == "3h07min", "fmt_tempo(3h07) = '3h07min'")
    confere(t.estimar_termino(100, 300, 10.0) == 20.0,
            "estimar_termino: 100 de 300 em 10 s -> faltam 20 s")
    confere(t.estimar_termino(0, 300, 10.0) is None, "estimar_termino sem passos -> None")
    confere(t.passos_do_checkpoint("x/ppo_120000_steps.zip") == 120000,
            "passos_do_checkpoint('ppo_120000_steps.zip') = 120000")
    confere(t.passos_do_checkpoint("modelo_final.zip") is None,
            "passos_do_checkpoint('modelo_final.zip') = None")
    cfg = t.config_serializavel({"a": (1, 2), "b": {"c": 1.5}, "d": object})
    confere(json.loads(json.dumps(cfg))["a"] == [1, 2], "config_serializavel vira JSON")
    m, d = avaliar.media_desvio([1, 2, 3, 4])
    confere(abs(m - 2.5) < 1e-12 and abs(d - 1.2909944) < 1e-6,
            "media_desvio([1,2,3,4]) = 2.5 +- 1.291 (amostral, n-1)")
    confere(avaliar.media_desvio([5]) == (5, 0.0), "media_desvio de 1 valor: desvio 0")
    r = avaliar.resumir([{"concluiu": 1, "colidiu": 0, "vel_media": 20, "passos": 30,
                          "recompensa": 10}, {"concluiu": 0, "colidiu": 1,
                                              "vel_media": 30, "passos": 10,
                                              "recompensa": 4}])
    confere(r["colidiu_media"] == 0.5 and r["vel_media_media"] == 25,
            "resumir: taxa de colisao 0.5, vel_media 25")
    confere(curva.media_movel([1, 2, 3, 4], 2) == [1, 1.5, 2.5, 3.5], "media_movel janela 2")
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "monitor.csv"
        p.write_text('#{"t_start": 1}\nr,l,t,crashed\n1.5,10,1.0,True\n2.0,30,2.0,False\n'
                     '#{"t_start": 9}\nr,l,t,crashed\n3.0,20,0.5,False\n')
        eps = curva.ler_monitor(str(p))
        confere([e["passo"] for e in eps] == [10, 40, 60],
                "ler_monitor: passos acumulados atravessam a retomada (10, 40, 60)")
        confere([e["crashed"] for e in eps] == [True, False, False],
                "ler_monitor: coluna crashed lida")


def ler(caminho):
    with open(caminho, newline="") as arq:
        leitor = csv.reader(arq)
        cab = next(leitor)
        return cab, [dict(zip(cab, lin)) for lin in leitor]


def grupo3():
    print("3. amostra/")
    av = AMOSTRA / "avaliacao"
    _, resumo = ler(av / "resumo.csv")
    por_nome = {x["politica"]: x for x in resumo}
    for nome in POLITICAS:
        cab, lin = ler(av / ("avaliacao_%s.csv" % nome))
        confere(cab == avaliar.COLUNAS == ["episodio", "semente", "concluiu", "colidiu",
                                           "vel_media", "passos", "recompensa"],
                "%s: colunas episodio,semente,concluiu,colidiu,vel_media,passos,"
                "recompensa" % nome)
        confere(len(lin) == 10, "%s: 10 episodios (achei %d)" % (nome, len(lin)))
        confere([int(x["semente"]) for x in lin] == list(range(1000, 1010)),
                "%s: sementes 1000 a 1009" % nome)
        coer = all(not (x["concluiu"] == "1" and x["colidiu"] == "1") and
                   (x["concluiu"] == "1") == (x["colidiu"] == "0" and x["passos"] == "30")
                   for x in lin)
        confere(coer, "%s: concluiu = nao colidiu e chegou aos 30 passos" % nome)
        r = avaliar.resumir(lin)
        confere(abs(r["colidiu_media"] - float(por_nome[nome]["colidiu_media"])) < 1e-3 and
                abs(r["vel_media_media"] - float(por_nome[nome]["vel_media_media"])) < 1e-3,
                "%s: resumo.csv bate com o CSV por episodio" % nome)
    eps = curva.ler_monitor(str(AMOSTRA / "monitor.csv"))
    confere(len(eps) > 1000, "monitor.csv: %d episodios de treino" % len(eps))
    confere(eps and eps[-1]["passo"] >= 100000,
            "monitor.csv: ultimo episodio em %d passos" % (eps[-1]["passo"] if eps else 0))
    zipm = AMOSTRA / "modelo_ppo.zip"
    confere(zipm.exists() and zipm.stat().st_size < 2 * 1024 * 1024,
            "modelo_ppo.zip existe e tem menos de 2 MB")
    for png in ("ppo-curva.png", "barras.png"):
        cab = (AMOSTRA / png).read_bytes()[:8] if (AMOSTRA / png).exists() else b""
        confere(cab == b"\x89PNG\r\n\x1a\n", "%s e um PNG" % png)


def grupo4():
    print("4. config do ambiente da amostra")
    with open(AMOSTRA / "config_ambiente.json") as arq:
        c = json.load(arq)
    cfg = c["config"]
    confere(c["ambiente"] == treinar_ppo.AMBIENTE == "highway-fast-v0",
            "treinado no highway-fast-v0")
    confere((cfg["lanes_count"], cfg["vehicles_count"], cfg["duration"],
             cfg["policy_frequency"]) == (3, 20, 30, 1),
            "3 faixas, 20 carros, 30 s, 1 decisao por segundo")
    confere(cfg["action"]["type"] == "DiscreteMetaAction" and
            cfg["observation"]["type"] == "Kinematics",
            "acao DiscreteMetaAction, observacao Kinematics")


def achar_python(pedido):
    candidatos = [pedido, os.environ.get("PPO_PYTHON"), sys.executable]
    for c in candidatos:
        if not c or not os.path.exists(c):
            continue
        r = subprocess.run([c, "-c", "import stable_baselines3, highway_env"],
                           capture_output=True)
        if r.returncode == 0:
            return c
    return None


def roda(py, args, cwd):
    return subprocess.run([py] + args, capture_output=True, text=True, cwd=cwd)


def grupo5(pedido):
    print("5. treino de fumaca (precisa do venv com stable-baselines3 e highway-env)")
    py = achar_python(pedido)
    if py is None:
        print("  [pulado] nenhum Python com stable_baselines3 e highway_env (passe "
              "--python ou defina PPO_PYTHON)")
        return
    with tempfile.TemporaryDirectory() as d:
        r = roda(py, [str(AQUI / "treinar_ppo.py"), "--passos", "300", "--checkpoint",
                      "384", "--relatorio", "5", "--saida", "r"], d)
        confere(r.returncode == 0, "treinar_ppo.py --passos 300 sai com 0%s"
                % ("" if r.returncode == 0 else ": " + r.stderr[-300:]))
        if r.returncode:
            return
        confere("passos/s" in r.stdout and "falta ~" in r.stdout,
                "imprime passos/s e a estimativa de termino")
        ck = pathlib.Path(d) / "r" / "checkpoints" / "ppo_768_steps.zip"
        confere(ck.exists(), "checkpoint ppo_768_steps.zip gravado (o SB3 completa a "
                "coleta de 768)")
        n1 = len(curva.ler_monitor(str(pathlib.Path(d) / "r" / "monitor.csv")))
        r = roda(py, [str(AQUI / "treinar_ppo.py"), "--passos", "1536", "--retomar",
                      str(ck), "--relatorio", "5", "--saida", "r"], d)
        confere(r.returncode == 0 and "768 passos ja feitos" in r.stdout,
                "--retomar continua do checkpoint de 768 passos")
        eps = curva.ler_monitor(str(pathlib.Path(d) / "r" / "monitor.csv"))
        confere(len(eps) > n1, "monitor.csv continuou (%d -> %d episodios)" % (n1, len(eps)))
        r = roda(py, [str(AQUI / "curva.py"), "--monitor", "r/monitor.csv", "--saida",
                      "c.png"], d)
        confere(r.returncode == 0 and (pathlib.Path(d) / "c.png").exists(),
                "curva.py grava o PNG")
        r = roda(py, [str(AQUI / "avaliar.py"), "--modelo", str(AMOSTRA / "modelo_ppo.zip"),
                      "--episodios", "3", "--saida", "av"], d)
        confere(r.returncode == 0, "avaliar.py com o modelo da amostra sai com 0")
        if r.returncode:
            return
        _, novo = ler(pathlib.Path(d) / "av" / "avaliacao_ppo.csv")
        _, velho = ler(AMOSTRA / "avaliacao" / "avaliacao_ppo.csv")
        iguais = all(novo[i][k] == velho[i][k] for i in range(3)
                     for k in ("concluiu", "colidiu", "passos"))
        print("  [info] 3 primeiros episodios do PPO iguais aos da amostra "
              "(concluiu, colidiu, passos): %s" % ("sim" if iguais else
                                                   "NAO -- outra maquina ou outra versao"))


def principal():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--python", help="Python do venv com stable-baselines3 (grupo 5)")
    a = p.parse_args()
    grupo1()
    grupo2()
    grupo3()
    grupo4()
    grupo5(a.python)
    if FALHAS:
        print("\n%d conferencia(s) falharam:" % len(FALHAS))
        for f in FALHAS:
            print("  - " + f)
        return 1
    print("\ntodos os testes passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
