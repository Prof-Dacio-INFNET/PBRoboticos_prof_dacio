# Tarefa da Aula 2 — Seus primeiros nós ROS 2 (passo a passo)

Este é o "esqueleto do seu TP1": um publisher, um subscriber e um serviço, no **seu** repositório. Faça na branch `dev`. Tempo: ~40 min. Pré-requisito: ambiente pronto (rode o [check](../recursos/check-ambiente.sh)).

## 0. Confirme o ambiente
```bash
curl -sSL https://raw.githubusercontent.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio/main/recursos/check-ambiente.sh | bash
```
Tudo ✓? Siga. Faltou algo? Volte ao tutorial da **sua** rota de ambiente: [WSL2](setup-ros2-humble-wsl2.md) ou [VirtualBox](setup-ros2-humble-virtualbox.md). O script diz na primeira linha qual rota ele detectou — se estiver errada, você está no terminal errado.

## 1. Trabalhe na branch dev, dentro do seu repositório (no terminal do Ubuntu)
```bash
cd ~/projeto-pb-SEU-USUARIO      # onde você clonou (nunca em /mnt/c)
git checkout dev
```

## 2. Copie o pacote de exemplo para o seu workspace
Baixe o exemplo do repositório de material e copie o pacote para `ros2_ws/src/`:
```bash
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula02-comunicacao/aula02_comunicacao ~/projeto-pb-SEU-USUARIO/ros2_ws/src/
cd ~/projeto-pb-SEU-USUARIO
```

## 3. Compile e rode
```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch aula02_comunicacao comunicacao.launch.py
```
**Esperado:** no terminal, o `assinante` logando `[1] recebi: "frame 0: 0 objeto(s) detectado(s)"`, `[2] ...` etc.

Noutro terminal (lembre do `source install/setup.bash`):
```bash
ros2 topic echo /camera/status          # veja as mensagens cruas
ros2 service call /contagem std_srvs/srv/Trigger "{}"   # "N mensagens ... até agora"
rqt_graph                                # veja o grafo: publicador → /camera/status → assinante
```
> ⚠️ Erro nº 1: "package not found" = faltou `source install/setup.bash` **neste** terminal.

## 4. Torne o pacote SEU (renomeie)
Renomeie a pasta e ajuste os 3 lugares onde o nome aparece (`package.xml`, `setup.py`, pasta interna). Ex.: `aula02_comunicacao` → `percepcao_meuprojeto`. Depois `rm -rf build install log && colcon build`.
> Dica: se preferir, mantenha o exemplo e crie um pacote novo com `ros2 pkg create --build-type ament_python percepcao_meuprojeto`.

## 5. Modifique o publisher (algo do seu domínio)
Em `publicador.py`, troque o texto por algo do seu projeto — ex.: um contador de "detecções" simulado:
```python
msg.data = f'frame {self.n}: {self.n % 3} objeto(s) detectado(s)'   # 0,1,2,0,1,2...
```
Recompile (com `--symlink-install`, mudanças em Python já valem sem rebuild) e rode de novo.

## 6. Adicione um SEGUNDO subscriber
Crie `assinante_alerta.py` que só loga quando há objeto (>0):
```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class AssinanteAlerta(Node):
    def __init__(self):
        super().__init__('assinante_alerta')
        self.create_subscription(String, '/camera/status', self.cb, 10)
    def cb(self, msg):
        if 'objeto' in msg.data and not msg.data.split('objeto')[0].rstrip().endswith('0'):
            self.get_logger().warn(f'ALERTA: {msg.data}')

def main():
    rclpy.init(); rclpy.spin(AssinanteAlerta()); rclpy.shutdown()
```
Registre o executável no `setup.py` (`'assinante_alerta = PKG.assinante_alerta:main'`), recompile e adicione ao launch.

## 7. Ponte com o TP1
O tópico já é `/camera/status`. No TP1, o publisher passará a publicar a **imagem** da câmera em `/camera/image_raw` (`sensor_msgs/Image`), o subscriber fará HSV/detecção e o serviço vira `/vision/status`. Você já tem o esqueleto.

## 8. Salve seu trabalho (na dev)
```bash
git add .
git commit -m "Primeiros nós: publisher + 2 subscribers + serviço"
git push
```
Capture um `rqt_graph` e salve em `docs/evidencias/aula02/` do seu repositório.

## Checklist de conclusão
- [ ] Exemplo rodando (launch) 
- [ ] pacote renomeado
- [ ] publisher modificado
- [ ] 2º subscriber (alerta)
- [ ] tópico `/camera/status`
- [ ] serviço `/contagem` respondendo
- [ ] commit+push na `dev`
- [ ] captura em docs/evidencias/
