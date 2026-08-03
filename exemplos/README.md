# Exemplos

Pacotes ROS 2 prontos para rodar, usados em aula e pensados para serem **copiados e adaptados** ao seu projeto. Não são demonstrações de vitrine: cada um deles é o esqueleto de um item concreto de algum TP.

!!! info "Licença MIT — pode copiar"
    Tudo em `exemplos/` está sob **MIT** (ver `exemplos/LICENSE`), separado do restante do material, que é CC BY-NC-ND. Você pode copiar para o seu repositório, modificar à vontade e entregar como seu, mantendo apenas o aviso de copyright. Adaptar o exemplo **não** é considerado cópia indevida — é o uso pretendido. O que se avalia é o que você fez a partir dele.

## Exemplos por aula

| Pacote | Aula | O que demonstra | Vira o quê |
|---|---|---|---|
| [`aula02-comunicacao`](aula02-comunicacao/index.md) | Aula 2 | publisher, subscriber e serviço `/contagem`, com launch | estrutura de pacote do TP1 |
| [`aula03-visao`](aula03-visao/index.md) | Aula 3 | `câmera → segmentação HSV → contagem → serviço`, tudo parametrizado | itens 3 e 4 do TP1 |

## Exemplos por TP

As pastas [`tp1`](tp1/index.md), [`tp2`](tp2/index.md), [`tp3`](tp3/index.md), [`tp4`](tp4/index.md) e [`tp5`](tp5/index.md) recebem exemplos específicos conforme cada TP se aproxima. Elas são publicadas mesmo quando ainda vazias, para que você saiba onde procurar.

## Como usar um exemplo sem se machucar

O caminho que funciona é sempre o mesmo: copie a pasta do pacote para o `src/` do **seu** workspace, compile com `--symlink-install`, rode como está, e só então comece a mudar. Rodar antes de modificar parece perda de tempo e é o contrário: quando algo quebrar depois da sua primeira alteração, você sabe que o problema é seu e não do exemplo.

```bash
cp -r aula03-visao/aula03_visao ~/SEU-REPO/ros2_ws/src/
cd ~/SEU-REPO/ros2_ws && colcon build --symlink-install && source install/setup.bash
```

Ao adaptar, **renomeie o pacote** (`aula03_visao` → `percepcao_meu_projeto`) e lembre que o nome precisa bater em três lugares: a pasta, o `package.xml` e o `setup.py`. Quando não bate, `rm -rf build install log` e recompile.

## Nenhum exemplo exige hardware

Todos rodam sem webcam, sem robô e sem GPU. O exemplo da Aula 3, por exemplo, gera a cena em código por padrão e só usa a câmera se você pedir — e volta sozinho para a fonte sintética se a câmera falhar. Isso é intencional, e é também o padrão que você deve seguir no seu projeto: **o caminho simulado precisa continuar funcionando**, mesmo quando o hardware entra. Ver [simulação × hardware real](../recursos/simulado-vs-hardware.md).
