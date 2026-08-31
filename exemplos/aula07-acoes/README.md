# Exemplo — `aula07-acoes`

**Aula 7 · Etapa 4.** Uma action completa: objetivo aceito ou rejeitado, feedback durante a execução, sucesso antecipado e **cancelamento que funciona de verdade**.

```
aula07-acoes/
└── aula07_acoes/                  # ament_python
    ├── servidor_varredura.py      # o servidor: aceita, executa, publica feedback, cancela
    └── cliente_varredura.py       # o cliente: envia, acompanha, e sabe pedir cancelamento
```

A action em si — `VarrerCena.action` — mora no **mesmo** `pb_interfaces` da Aula 6. Interface não ganha pacote novo a cada aula: o pacote de interfaces do projeto cresce.

## Baixar o material desta aula

```bash
# 1) baixar o material (pode repetir sempre -- o rm evita o erro de pasta ja existente)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar. pb_interfaces vem de novo porque ele MUDOU: ganhou a action
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/pb_interfaces \
      /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/aula06_percepcao \
      /tmp/PBRoboticos_prof_dacio/exemplos/aula07-acoes/aula07_acoes \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar -- interfaces primeiro, sempre
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select pb_interfaces
source install/setup.bash
colcon build --packages-select aula06_percepcao aula07_acoes --symlink-install
source install/setup.bash
```

## Rodar

```bash
ros2 launch aula07_acoes varredura.launch.py classe:=tomate_maduro
```

Noutro terminal, pela linha de comando — sem escrever cliente nenhum:

```bash
ros2 action list
ros2 action info /varrer_cena -t
ros2 action send_goal /varrer_cena pb_interfaces/action/VarrerCena \
  "{duracao_s: 15.0, classe_alvo: 'tomate_maduro', minimo_para_parar: 0}" --feedback
```

O `--feedback` é o que mostra a diferença: você vê o progresso chegando **enquanto** a tarefa roda. Sem ele, a action parece um serviço lento.

Depois, com o cliente, para exercitar o cancelamento:

```bash
ros2 run aula07_acoes cliente_varredura --ros-args -p duracao_s:=30.0
# deixe rodar uns segundos e dê Ctrl+C: o cliente PEDE cancelamento,
# o servidor aceita, e o resultado volta com "cancelada em N.Ns"
```

## Os três experimentos que valem a aula

**1. A rejeição.** Peça algo absurdo e veja o servidor recusar antes de começar:

```bash
ros2 action send_goal /varrer_cena pb_interfaces/action/VarrerCena \
  "{duracao_s: 999.0, classe_alvo: 'x', minimo_para_parar: 0}"
```

Rejeitado é diferente de falhou: o servidor olhou o pedido e disse não. Essa distinção não existe em tópico, e num serviço custa um campo de erro na resposta.

**2. O sucesso antecipado.** Com `minimo_para_parar: 2`, a varredura termina assim que vir dois objetos, sem esperar o prazo. Tarefa longa não é tarefa de duração fixa.

**3. O cancelamento — e a razão de ele falhar.** Comente as duas linhas marcadas no `servidor_varredura.py` (o `ReentrantCallbackGroup` e o `MultiThreadedExecutor`), recompile, e tente cancelar. **Não cancela.** Não aparece erro nenhum: o `execute_callback` ocupa a única thread do executor, e o pedido de cancelamento fica na fila até a tarefa acabar sozinha.

Esse é o experimento mais importante do exemplo, porque é o modo de falha que o gate **G2.3** testa, e porque ele não se manifesta como erro — se manifesta como uma funcionalidade que simplesmente não acontece.

## O que copiar para o seu projeto

A forma do `VarrerCena.action` serve para quase qualquer tarefa longa de percepção: um prazo, um alvo, uma condição de parada antecipada, e um feedback com progresso. Troque o vocabulário e mantenha a estrutura de três blocos.

Do servidor, o que se copia não é o corpo do laço — é a **ordem** dentro dele: checar cancelamento primeiro, trabalhar depois, publicar feedback por último, e dormir um pouco. Inverter essa ordem produz servidores que demoram um ciclo inteiro para responder ao cancelamento.

## Licença

MIT, como todo o diretório `exemplos/`.
