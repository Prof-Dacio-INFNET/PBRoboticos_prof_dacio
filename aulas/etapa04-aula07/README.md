# Aula 7 — Ações: tarefas longas, feedback e cancelamento

**Terça, 01/09/2026 · sala SJ205 · Etapa 4 (31/08–12/09)**

[:material-file-pdf-box: Slides da Aula 7 (PDF)](apresentacao-aula07.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula07-acoes`](../../exemplos/aula07-acoes/index.md){ .md-button }
[:material-clipboard-check: Tarefa da semana](../../tutoriais/tarefa-aula07-acoes.md){ .md-button }

## A ideia da aula em uma frase

**Hoje o seu robô ganha a capacidade de ser interrompido.** Tópico e serviço, que você usa desde a Aula 2, cobrem duas situações: informação que flui e pergunta que se responde na hora. Nenhum dos dois cobre a terceira, que é a mais comum em robótica — a tarefa que **demora**, que precisa dizer como está indo, e que às vezes precisa parar no meio.

Essa terceira forma é a **action**, e ela é a base de tudo que vem daqui em diante: navegar até um ponto, mapear uma área, executar uma trajetória. O Nav2, que você vai usar na Etapa 5, é construído inteiro sobre ações. Aprender action agora não é um desvio da Etapa 4 — é o pré-requisito dela.

## Objetivos

Ao final da aula você deve conseguir justificar a escolha entre tópico, serviço e action a partir da natureza da tarefa, e não por gosto; escrever um `.action` com os três blocos e explicar o papel de cada um; implementar um servidor que aceita ou **rejeita** objetivos, publica feedback periódico e responde a cancelamento; explicar por que um servidor aparentemente correto não cancela, e corrigir isso; e usar `ros2 action send_goal --feedback` para exercitar tudo isso sem escrever cliente nenhum.

## Antes de mais nada: o TP1 foi entregue

Reserve os dez primeiros minutos para olhar para trás. Não é cerimônia — é o único momento em que a informação ainda está fresca e ainda é barata de aproveitar.

Três perguntas, respondidas por escrito no seu `PROJETO.md`, na seção de retrospectiva:

**O que você descobriu tarde demais?** Quase todo mundo tem um item aqui, e ele quase nunca é técnico: é uma decisão adiada, uma evidência não commitada, um link não testado.

**Qual gate você marcou `[x]` sem estar confortável?** Esse é o que vai voltar. Um gate passado no limite é dívida, e a dívida do TP1 é cobrada no TP3, quando o pipeline de visão precisa alimentar o mapeamento.

**O que você faria diferente no TP2, sabendo o que sabe agora?** Escreva uma frase. Uma só. Frase concreta vale mais que parágrafo genérico.

## Baixar o material desta aula

Os exemplos vivem no repositório da disciplina. Você **não** trabalha dentro dele: copia o pacote para dentro do **seu** projeto e compila lá. Troque `SEU-USUARIO` pelo seu usuário do GitHub.

```bash
# 1) baixar o material (pode repetir sempre — a linha do rm evita o erro de pasta já existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar. O pb_interfaces vem DE NOVO porque ele mudou: ganhou a action
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/pb_interfaces \
      /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/aula06_percepcao \
      /tmp/PBRoboticos_prof_dacio/exemplos/aula07-acoes/aula07_acoes \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar no SEU workspace — interfaces primeiro, sempre
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select pb_interfaces
source install/setup.bash
colcon build --packages-select aula06_percepcao aula07_acoes --symlink-install
source install/setup.bash
```

!!! tip "Rode antes de modificar"
    Compile e rode o exemplo **como ele veio**, antes da sua primeira alteração. Parece perda de tempo e é o contrário: quando algo quebrar depois, você sabe que o problema é seu e não do exemplo.

## Parte 1 — As três formas de conversar, e onde cada uma quebra

Você já usou duas. A terceira existe porque as duas primeiras falham num caso específico e muito comum.

| | Tópico | Serviço | Action |
|---|---|---|---|
| Quem espera | ninguém | quem chamou, bloqueado | ninguém fica bloqueado |
| Sabe se chegou | não | sim | sim, e em que passo |
| Dá para recusar | não | não de forma explícita | **sim** — objetivo rejeitado |
| Dá para cancelar | não faz sentido | não | **sim** |
| Duração típica | contínua | milissegundos | segundos a minutos |

Pense num pedido concreto: *"vá até a bancada e me avise quando chegar."*

Como **tópico** você publica a coordenada e torce. Ninguém confirma que chegou, e você não descobre se o caminho estava bloqueado. Como **serviço** o cliente fica travado esperando trinta segundos sem receber notícia nenhuma, e se você desistir no meio, o robô continua indo — porque o serviço não tem como ser cancelado. A **action** resolve os dois: o servidor confirma que aceitou, publica progresso enquanto anda, e para se você mandar parar.

!!! note "A regra prática"
    Se a resposta demora mais que uma fração de segundo, serviço é a escolha errada. Se você algum dia vai querer saber *como está indo* ou *mandar parar*, é action. Para todo o resto, tópico e serviço continuam certos — e action tem custo real de código, então não a use onde não precisa.

## Parte 2 — Anatomia de um `.action`

Três blocos separados por `---`, e a ordem é sempre esta:

```
# VarrerCena.action

# ---------- Goal: o que se pede ----------
float32 duracao_s
string  classe_alvo
uint32  minimo_para_parar
---
# ---------- Result: o que volta no fim ----------
uint32  total_visto
float32 confianca_media
uint32  quadros_analisados
string  resumo
---
# ---------- Feedback: o que volta DURANTE ----------
float32 decorrido_s
uint32  vistos_ate_agora
float32 progresso
```

O arquivo mora em `action/` dentro do **mesmo** `pb_interfaces` da Aula 6 — interface não ganha pacote novo a cada aula. Duas linhas mudam no pacote: o `.action` entra na lista do `rosidl_generate_interfaces`, e `action_msgs` entra como dependência nos dois lugares (`package.xml` e `DEPENDENCIES`), porque toda action carrega identificador e status de objetivo.

Um detalhe de projeto que vale a pena notar: `minimo_para_parar` existe para que a tarefa possa **terminar cedo**. Tarefa longa não é o mesmo que tarefa de duração fixa, e o campo que permite parar antes costuma ser o mais útil da action inteira.

## Parte 3 — O servidor: três decisões, não uma

Um servidor de action não tem só o código que executa. Ele tem três pontos de decisão, e cada um responde a uma pergunta diferente.

**Aceitar ou rejeitar** (`goal_callback`) acontece *antes* de qualquer trabalho. É onde se recusa um pedido impossível, fora de faixa ou perigoso. Rejeitado é diferente de falhou: o servidor olhou o pedido e disse não, sem gastar nada.

**Aceitar ou recusar o cancelamento** (`cancel_callback`) é uma decisão, não um automatismo. Observar a cena é inofensivo, então o exemplo aceita sempre. Um braço no meio de um movimento pode precisar recusar, ou aceitar e recolher antes de parar.

**Executar** (`execute_callback`) é o laço, e a ordem dentro dele importa mais do que o conteúdo:

```python
while True:
    if goal_handle.is_cancel_requested:      # 1. cancelamento SEMPRE primeiro
        goal_handle.canceled()               #    sem esta linha o cliente pendura
        return resultado_parcial
    ...                                      # 2. o trabalho
    if condicao_de_sucesso:                  # 3. sucesso antecipado
        goal_handle.succeed()
        return resultado
    goal_handle.publish_feedback(fb)         # 4. feedback
    time.sleep(PERIODO_S)                    # 5. dormir um pouco
```

Checar cancelamento no fim do laço em vez do início faz o servidor demorar um ciclo inteiro para obedecer. Com período de 200 ms ninguém nota; com período de dois segundos, o usuário aperta parar e o robô continua andando por dois segundos — o que numa bancada é irritante e num robô móvel é um problema de segurança.

## Parte 4 — O bug que não dá erro

Este é o coração da aula, e é o motivo de o gate **G2.3** reprovar tanta gente.

Escreva um servidor correto em tudo — `cancel_callback` aceitando, `is_cancel_requested` checado no lugar certo, `canceled()` chamado. Rode. Peça cancelamento. **Não cancela.** E não aparece erro nenhum, em lugar nenhum.

A causa está fora do código da action. Por padrão, o `rclpy` roda com um executor de **uma thread só**. Quando o `execute_callback` entra em execução, ele ocupa essa thread inteira até terminar. O pedido de cancelamento chega, entra na fila... e espera a thread ficar livre — o que só acontece quando a tarefa acaba sozinha. O `is_cancel_requested` nunca vira verdadeiro, porque nada nunca o setou.

A cura são duas linhas, e as duas são necessárias:

```python
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

# 1. no ActionServer:
callback_group=ReentrantCallbackGroup()

# 2. no main():
rclpy.spin(no, executor=MultiThreadedExecutor())
```

!!! warning "Faça o experimento, não acredite em mim"
    Comente as duas linhas no `servidor_varredura.py`, recompile e tente cancelar. Ver a coisa **não** funcionar, sem nenhuma mensagem, é o que fixa a lição — e é uma classe inteira de bug que você vai reencontrar: **o comportamento ausente não produz erro.** Testes procuram erro; comportamento ausente só aparece se você o exercitar de propósito.

    É por isso que o gate G2.3 pede cancelamento demonstrado, e não código de cancelamento escrito.

## Parte 5 — Do lado do cliente, sem escrever cliente

Antes de escrever qualquer código de cliente, use a linha de comando. Ela exercita a action inteira:

```bash
ros2 action list
ros2 action info /varrer_cena -t
ros2 action send_goal /varrer_cena pb_interfaces/action/VarrerCena \
  "{duracao_s: 15.0, classe_alvo: 'tomate_maduro', minimo_para_parar: 0}" --feedback
```

**O `--feedback` é a aula inteira em uma flag.** Sem ele você vê um comando que demora e devolve algo — indistinguível de um serviço lento. Com ele, o progresso chega enquanto a tarefa roda, que é a coisa que só action faz.

Depois, o cliente do exemplo, para exercitar o cancelamento de verdade:

```bash
ros2 run aula07_acoes cliente_varredura --ros-args -p duracao_s:=30.0
# deixe correr e dê Ctrl+C
```

Repare no que o `Ctrl+C` faz ali: ele **não** mata a tarefa no servidor. Ele envia um pedido de cancelamento e espera a confirmação. Matar o cliente e cancelar o objetivo são coisas diferentes, e confundir as duas é como se descobre, tarde, que o robô continuou andando depois que o terminal fechou.

## Parte 6 — Onde isso vira TP2, e onde vira navegação

No TP2, os gates **G2.2** e **G2.3** são exatamente esta aula: action com servidor respondendo, e action com feedback e cancelamento demonstrados. O aviso do documento de gates é direto — *"implementar a Action como um publisher com nome bonito"* — e agora você sabe qual é o teste que separa uma coisa da outra.

No resto do semestre, ação deixa de ser assunto e vira infraestrutura. `NavigateToPose`, do Nav2, é uma action: objetivo é a pose de destino, feedback é a distância restante, e cancelamento é o botão de parar. Quando você chegar lá, não vai aprender navegação e ações ao mesmo tempo — vai aprender navegação usando uma coisa que já entende.

## Tarefa da semana

[Tarefa da Aula 7 — a ação do seu projeto](../../tutoriais/tarefa-aula07-acoes.md): definir uma action que faça sentido no seu domínio, implementar o servidor com feedback e cancelamento, e **gravar a evidência de cancelamento** — que é o que o G2.3 cobra.

## Socorro rápido

| Sintoma | Causa provável |
|---|---|
| a action não aparece em `ros2 action list` | o servidor não subiu, ou o `pb_interfaces` não foi recompilado depois de ganhar o `.action` |
| erro de compilação mencionando `action_msgs` | falta `<depend>action_msgs</depend>` no `package.xml` **e** `action_msgs` em `DEPENDENCIES` |
| `ModuleNotFoundError: pb_interfaces.action` | compilou as interfaces mas não deu `source install/setup.bash` — em **todos** os terminais |
| o cliente fica pendurado para sempre | o servidor não chamou `succeed()`, `abort()` nem `canceled()`. Todo caminho de saída do `execute_callback` precisa fechar o objetivo |
| **o cancelamento não faz nada, e não há erro** | executor de uma thread só — [Parte 4](#parte-4-o-bug-que-nao-da-erro) |
| o cancelamento demora um ciclo para obedecer | `is_cancel_requested` está sendo checado no fim do laço; mova para o começo |
| `send_goal` diz "Goal was rejected" | é o `goal_callback` funcionando. Confira a faixa aceita — no exemplo, `0 < duracao_s <= 120` |
| feedback não aparece | faltou a flag `--feedback` no `send_goal` |
| `ros2 topic hz` com `min:` negativo | relógio do WSL2 saltando — [diagnóstico e cura](../../tutoriais/setup-ros2-humble-wsl2.md#o-relogio-do-wsl2-pode-saltar-e-isso-estraga-qualquer-medicao) |
| `No module named 'PyQt5'` ao abrir rqt | venv ativado; `deactivate` resolve |

## Para a próxima aula (08/09)

**Percepção veicular: detecção treinada e métrica declarada** — o gate **G2.4**. É onde a segmentação por cor finalmente dá lugar a um detector treinado, e onde você vai ter que declarar uma métrica em vez de dizer "ficou bom". Chegue com a sua action funcionando: a varredura de hoje é o esqueleto que vai chamar o detector de lá.
