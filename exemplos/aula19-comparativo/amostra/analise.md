# Analise critica -- ESQUELETO

> **Isto e um esqueleto, nao uma analise.** O `comparar.py` gerou a tabela e as linhas
> achei/olhe; as secoes abaixo sao PERGUNTAS. Quem escreve as respostas e voce, com os
> numeros do seu projeto. Apague esta nota quando terminar.
>
> Apoio, nao veredito: relato o que achei nos CSVs. Nao decido quem ganhou, nao valido a entrega,
> nao antecipo nota e nao substituo o enunciado.

Gerado por:

```
python3 comparar.py --csv pid=amostra/metadrive/pid.csv bc=amostra/metadrive/bc.csv constante=amostra/metadrive/constante.csv ppo=amostra/highway/avaliacao_ppo.csv aleatoria=amostra/highway/avaliacao_aleatoria.csv idle=amostra/highway/avaliacao_idle.csv --grupo 'pid,bc,constante=MetaDrive (mapa SCSCS, sem trafego)' 'ppo,aleatoria,idle=highway-fast-v0 (3 faixas, 20 carros)' --png amostra/barras.png --md amostra/analise.md
```

## A tabela

| grupo                                 | controlador | n  | concluiu | IC 95%     | colidiu | IC 95%    | saiu da pista | IC 95%     | vel. media km/h | sementes    |
|---------------------------------------|-------------|----|----------|------------|---------|-----------|---------------|------------|-----------------|-------------|
| MetaDrive (mapa SCSCS, sem trafego)   | pid         | 10 | 10/10    | 72% a 100% | 0/10    | 0% a 28%  | 0/10          | 0% a 28%   | 38.0 +- 0.3     | 100 a 109   |
| MetaDrive (mapa SCSCS, sem trafego)   | bc          | 10 | 8/10     | 49% a 94%  | 0/10    | 0% a 28%  | 2/10          | 6% a 51%   | 37.7 +- 1.3     | 100 a 109   |
| MetaDrive (mapa SCSCS, sem trafego)   | constante   | 10 | 0/10     | 0% a 28%   | 0/10    | 0% a 28%  | 10/10         | 72% a 100% | 28.9 +- 0.3     | 100 a 109   |
| highway-fast-v0 (3 faixas, 20 carros) | ppo         | 10 | 7/10     | 40% a 89%  | 3/10    | 11% a 60% | -             | -          | 86.1 +- 7.1     | 1000 a 1009 |
| highway-fast-v0 (3 faixas, 20 carros) | aleatoria   | 10 | 1/10     | 2% a 40%   | 9/10    | 60% a 98% | -             | -          | 83.4 +- 9.1     | 1000 a 1009 |
| highway-fast-v0 (3 faixas, 20 carros) | idle        | 10 | 1/10     | 2% a 40%   | 9/10    | 60% a 98% | -             | -          | 87.4 +- 1.8     | 1000 a 1009 |

IC 95%: intervalo de Wilson da taxa em n episodios. vel. media: media +- desvio-padrao amostral entre episodios.

## O que o script achou

```
achei 6 controlador(es) em 2 grupo(s): MetaDrive (mapa SCSCS, sem trafego) -> pid, bc, constante; highway-fast-v0 (3 faixas, 20 carros) -> ppo, aleatoria, idle
olhe: 2 grupos diferentes. Colidiu, velocidade e recompensa nao querem dizer a mesma coisa entre eles; nao comparo barras de grupos diferentes
nao achei numero de episodios diferente: todos com 10
nao achei controlador com menos de 10 episodios
achei as mesmas sementes (100 a 109) em todos de 'MetaDrive (mapa SCSCS, sem trafego)'
achei linha de base em 'MetaDrive (mapa SCSCS, sem trafego)': constante
olhe: pid 10/10 (72% a 100%) e bc 8/10 (49% a 94%) em 'concluiu': os intervalos se sobrepoem -- estes dois nao estao separados por estes numeros
olhe: pid 0/10 (0% a 28%) e bc 2/10 (6% a 51%) em 'saiu da pista': os intervalos se sobrepoem -- estes dois nao estao separados por estes numeros
achei, em 'MetaDrive (mapa SCSCS, sem trafego)', intervalos que nao se tocam: pid x constante em concluiu; pid x constante em saiu da pista; bc x constante em concluiu; bc x constante em saiu da pista
achei as mesmas sementes (1000 a 1009) em todos de 'highway-fast-v0 (3 faixas, 20 carros)'
achei linha de base em 'highway-fast-v0 (3 faixas, 20 carros)': aleatoria, idle
olhe: ppo 7/10 (40% a 89%) e aleatoria 1/10 (2% a 40%) em 'concluiu': os intervalos se sobrepoem -- estes dois nao estao separados por estes numeros
olhe: ppo 3/10 (11% a 60%) e aleatoria 9/10 (60% a 98%) em 'colidiu': os intervalos se sobrepoem -- estes dois nao estao separados por estes numeros
olhe: ppo 7/10 (40% a 89%) e idle 1/10 (2% a 40%) em 'concluiu': os intervalos se sobrepoem -- estes dois nao estao separados por estes numeros
olhe: ppo 3/10 (11% a 60%) e idle 9/10 (60% a 98%) em 'colidiu': os intervalos se sobrepoem -- estes dois nao estao separados por estes numeros

Intervalos que se tocam nao provam que os dois sao iguais: dizem que estes n nao bastam para
separa-los. Mais episodios estreitam o intervalo: com 5 vezes mais, ele fica com cerca
de metade da largura.
Isto nao significa que a comparacao esta certa nem que a entrega esta pronta: esgotei o que
um script enxerga num CSV. O que pesa -- se a regua foi a mesma, se a analise fala do seu
projeto, se as limitacoes estao ditas -- esta no relatorio, nao aqui.
```

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
