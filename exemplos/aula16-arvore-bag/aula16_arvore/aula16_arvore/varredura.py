"""A menor distancia de um /scan -- a conta que o `vigia` e o `gravar_pose` usam.

ADVERTENCIA: em 09/11/2026, numa maquina com Humble, o pacote compilou e o
`vigia`, o `gravar_pose` e o `analise.launch.py` rodaram. ESTE arquivo nao foi
exercitado isoladamente com ROS 2: ele segue coberto so pelo `testar.py`. O
que foi conferido esta na secao "O que foi e o que nao foi verificado" do
README deste exemplo -- leia antes de concluir que o erro e seu.

POR QUE ISTO E UM MODULO, e nao duas copias de tres linhas:

    O `vigia.py` decide pelo portao de 0,5 m e o `gravar_pose.py` grava a
    coluna `dist_min_scan` do CSV. Se as duas contas divergirem em um detalhe,
    o grafico do relatorio mostra uma distancia e o robo reage a outra -- e
    ninguem consegue explicar a figura. Uma funcao so', nos dois.

AS TRES ARMADILHAS DO `min(msg.ranges)`, que e o que todo mundo escreve
primeiro:

    1. `inf` e `nan`. Um feixe que nao achou nada devolve `inf` (ou `nan`, a
       depender do driver). `min` com `nan` no meio devolve lixo: a comparacao
       com `nan` e sempre falsa, e o resultado depende da ORDEM da lista.
    2. zero. Muito driver real devolve 0.0 para feixe invalido -- reflexo
       ruim, superficie preta, leitura perdida. `min` pega esse zero, o portao
       de 0,5 m dispara, e o robo para para sempre na frente de nada. E a
       causa numero um de "o vigia trava sozinho".
    3. o leque inteiro. Um LIDAR de 360 graus ve a parede ATRAS do robo. O
       enunciado fala de "obstaculo", e obstaculo que importa para quem anda
       para a frente e o que esta na frente. Por isso o setor.

    A cura das tres e a mesma: filtrar por `range_min`/`range_max` do proprio
    cabecalho da mensagem -- que existem exatamente para isso -- e recortar o
    leque por angulo.
"""
import math

SETOR_PADRAO_GRAUS = 60.0     # +- 60 graus em volta da frente do robo


def angulo_do_feixe(msg, i):
    """O angulo do feixe `i`, no quadro do laser. Zero e a frente."""
    return msg.angle_min + i * msg.angle_increment


def menor_distancia(msg, setor_graus=SETOR_PADRAO_GRAUS):
    """Menor leitura VALIDA do /scan dentro do setor frontal, em metros.

    Devolve `inf` quando nenhum feixe do setor e valido -- e `inf` e a
    resposta certa para "nao vi nada", nao um erro. Quem compara com o limiar
    (`dist < 0.5`) trata isso de graca; quem escreve `dist <= 0.5` nao.

    `setor_graus` e meia-largura: 60 significa de -60 a +60 graus. Com
    `setor_graus >= 180` o leque inteiro entra, que e o comportamento de quem
    tem um laser frontal de 180 graus e nao precisa recortar nada.
    """
    limite = math.radians(abs(float(setor_graus)))
    menor = math.inf
    minimo = float(msg.range_min)
    maximo = float(msg.range_max)
    for i, r in enumerate(msg.ranges):
        # Esta linha sozinha mata as armadilhas 1 e 2: `nan` reprova em
        # qualquer comparacao, e o zero fica abaixo de `range_min`.
        if not (minimo <= r <= maximo):
            continue
        if abs(angulo_do_feixe(msg, i)) > limite:
            continue
        if r < menor:
            menor = float(r)
    return menor
