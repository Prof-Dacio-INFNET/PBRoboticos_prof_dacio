# Dataset `dataset-pid`

> Relatorio do `histograma.py`: o que ele achou no `acoes.csv`. Nao diz se o
> dataset serve, nao valida a entrega e nao substitui o enunciado.

| | |
|---|---|
| quadros | 1000 |
| episodios | 5 (sementes 0, 1, 2, 3, 4) |
| piloto | pid |
| direcao: media, desvio | -0.009, 0.061 |
| direcao: min, max | -0.451, 0.494 |
| abs(direcao) < 0.02 | 644 quadros (64%) |
| esquerda (>= 0.02) / direita (<= -0.02) | 81 / 275 |

Direcao em faixas de 0,02 (+1 = volante todo a esquerda; as pontas juntam
tudo abaixo de -0,2 e acima de +0,2):

```
[-1.00, -0.20)     3 
[-0.20, -0.18)     0 
[-0.18, -0.16)     2 
[-0.16, -0.14)     1 
[-0.14, -0.12)     5 
[-0.12, -0.10)     5 
[-0.10, -0.08)    15 #
[-0.08, -0.06)   204 ####################
[-0.06, -0.04)    23 ##
[-0.04, -0.02)    17 ##
[-0.02, +0.00)   122 ############
[+0.00, +0.02)   522 ##################################################
[+0.02, +0.04)    12 #
[+0.04, +0.06)    11 #
[+0.06, +0.08)     4 
[+0.08, +0.10)     7 #
[+0.10, +0.12)    11 #
[+0.12, +0.14)    13 #
[+0.14, +0.16)     3 
[+0.16, +0.18)     4 
[+0.18, +0.20)     1 
[+0.20, +1.00)    15 #
```

Por episodio:

| episodio | semente | quadros | abs(direcao) < 0.02 |
|---|---|---|---|
| 0 | 0 | 234 | 64% |
| 1 | 1 | 211 | 73% |
| 2 | 2 | 221 | 62% |
| 3 | 3 | 229 | 62% |
| 4 | 4 | 105 | 61% |

O que isto NAO significa: uma tabela sem nada estranho e "o script nao achou
mais nada para contar", nao "dataset pronto". Se a direcao de verdade das
curvas esta la, so a sua pista e o comportamento do modelo dizem.
