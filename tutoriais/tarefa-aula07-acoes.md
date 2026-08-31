---
titulo: "Tarefa da Aula 7 — a ação do seu projeto"
tipo: tarefa
etapa: 4
alvo: "Ubuntu 22.04 · ROS 2 Humble"
---

# Tarefa da Aula 7 — a ação do seu projeto

**Publicada em 01/09/2026 · trazer pronta para a Aula 8, em 08/09/2026**

Esta tarefa fecha dois gates do TP2 de uma vez: **G2.2** (action com servidor respondendo, vence 12/09) e **G2.3** (feedback e cancelamento demonstrados, vence 16/09). O G2.3 é o gate que a correção efetivamente testa, e é o que mais reprova.

## 1. Escolha uma tarefa que realmente demora

Antes de escrever qualquer coisa, responda: **qual tarefa do meu projeto leva mais de um segundo e faz sentido interromper?** Se você não encontrar nenhuma, procure melhor — todo projeto tem uma. Alguns exemplos, por família:

| Domínio | Action plausível |
|---|---|
| inspeção de peças | inspecionar um lote até achar N refugos ou esgotar a esteira |
| estacionamento | varrer o pátio e mapear as vagas livres |
| agricultura | percorrer a fileira contando frutos maduros |
| segurança | monitorar a área por N minutos e relatar intrusões |
| logística | seguir uma rota de coleta e reportar o progresso |

Se a sua tarefa **não** tem como ser interrompida no meio de forma útil, ela provavelmente é um serviço, e forçá-la a virar action é cerimônia. Diga isso no relatório em vez de fingir.

## 2. Escreva o `.action` no seu pacote de interfaces

No mesmo `<seuprojeto>_interfaces` da Aula 6, em `action/`. Não crie pacote novo.

Os três blocos precisam ganhar sentido no seu domínio, não copiar o exemplo:

- **Goal** — o que se pede, incluindo um critério de **parada antecipada**
- **Result** — o que ficou sabendo, e não só "deu certo"
- **Feedback** — algo que muda **durante**; progresso sozinho é pobre, acrescente uma medida do seu domínio

Duas linhas mudam no pacote: o `.action` entra no `rosidl_generate_interfaces`, e `action_msgs` entra como dependência no `package.xml` e no `DEPENDENCIES`.

## 3. Implemente o servidor

Com as três decisões separadas: `goal_callback` (aceita ou rejeita), `cancel_callback` (aceita ou recusa o cancelamento) e `execute_callback` (o laço). Dentro do laço, a ordem é cancelamento, trabalho, sucesso antecipado, feedback, dormir.

**Rejeite alguma coisa de propósito.** Uma faixa de valores, um alvo desconhecido, um pedido longo demais. Servidor que aceita tudo não exercita metade do mecanismo.

## 4. Prove que cancela

Esta é a parte que vale o gate, e não basta o código existir:

```bash
# terminal 1
ros2 run <seupacote> <seu_servidor>

# terminal 2 — comece um objetivo longo
ros2 action send_goal /<sua_action> <seuprojeto>_interfaces/action/<SuaAction> \
  "{...}" --feedback

# no terminal 2, com a tarefa correndo, dê Ctrl+C
```

Esperado: o servidor **loga** que recebeu o cancelamento, o objetivo termina com estado `CANCELED`, e o resultado volta parcial. Se a tarefa continuar até o fim, você caiu no executor de uma thread só — [Parte 4 da aula](../aulas/etapa04-aula07/index.md#parte-4-o-bug-que-nao-da-erro).

## 5. Evidência

Grave a sessão inteira — do envio ao cancelamento — porque o gate pede demonstração, não código:

```bash
# asciinema, se tiver; senão, redirecione a saida dos dois terminais
ros2 action send_goal ... --feedback 2>&1 | tee docs/evidencias/tp2/action-goal.txt
```

Commite em `docs/evidencias/tp2/`: `action-goal.txt` (G2.2) e o GIF ou asciinema do cancelamento (G2.3), com o log do servidor mostrando que ele **tratou** o cancel.

## Critério de pronto

- [ ] `ros2 action list` mostra a sua action
- [ ] `ros2 action info /<sua_action> -t` mostra o tipo certo
- [ ] um objetivo válido completa e devolve um Result com informação do seu domínio
- [ ] um objetivo inválido é **rejeitado** antes de começar
- [ ] o feedback chega durante a execução, com uma medida do seu domínio
- [ ] o cancelamento funciona, e há evidência gravada dele
- [ ] o `PROJETO.md` marca G2.2 e G2.3

## O erro que custa o gate

Implementar a action como um publisher com nome bonito: um servidor que aceita o objetivo, faz o trabalho inteiro num bloco e devolve o resultado, sem feedback intermediário e sem checar cancelamento. Compila, roda, entrega o resultado certo — e não passa no G2.3, porque não pode ser interrompido.

Se o seu servidor não consegue ser parado no meio, ele não é uma action. É um serviço lento com mais código.
