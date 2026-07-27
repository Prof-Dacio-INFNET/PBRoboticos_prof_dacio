# aula02-comunicacao — publisher + subscriber + serviço

Exemplo da Aula 2 (Etapa 1). Mostra os três tijolos de comunicação do ROS 2 que o TP1 vai pedir:
`publicador` → publica em `/camera/status`; `assinante` → escuta e conta; `servico_contagem` → responde `/contagem` (pergunta/resposta).

```bash
cp -r aula02-comunicacao/aula02_comunicacao ~/SEU-REPO/ros2_ws/src/   # copie o pacote
cd ~/SEU-REPO/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch aula02_comunicacao comunicacao.launch.py                  # sobe os 3 nós
# noutro terminal:
ros2 topic echo /camera/status
ros2 service call /contagem std_srvs/srv/Trigger "{}"
rqt_graph
```
Adapte: troque o conteúdo publicado pela lógica do seu projeto; renomeie o pacote. É o esqueleto do seu TP1.
