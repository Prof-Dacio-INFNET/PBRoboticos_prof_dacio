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

## Onde editar, e a sequência de comandos

Toda alteração é em `src/` — `build/`, `install/` e `log/` são gerados pelo `colcon build` e sobrescritos a cada compilação. Depois de editar:

```bash
cd ~/SEU-REPO/ros2_ws

# opcional, quando houver muita sujeira de build anterior
rm -rf build/<nome_do_pacote> install/<nome_do_pacote> log/latest_build

colcon build --packages-select <nome_do_pacote> --symlink-install
source install/setup.bash
ros2 launch <nome_do_pacote> comunicacao.launch.py
```

!!! warning "Ao clonar ou renomear o pacote, alinhe os nomes"
    Em pacotes `ament_python`, ao renomear pacote, alinhar `<name>` em `package.xml`, `package_name` em `setup.py`, arquivo `resource/<package_name>` e `setup.cfg` (`script_dir`/`install_scripts` em `$base/lib/<package_name>`).

    - Se `setup.cfg` ficar com nome antigo, `ros2 launch` falha com: `libexec directory .../lib/<package_name> does not exist`.

    Passo a passo e o teste de conferência: [renomear um pacote ROS 2](../../tutoriais/renomear-pacote-ros2.md).

Se aparecer erro ao sair com `Ctrl+C` (`rcl_shutdown already called`), normalmente é ruído de encerramento e não quebra a execução principal — fechar com `if rclpy.ok(): rclpy.shutdown()` resolve.
