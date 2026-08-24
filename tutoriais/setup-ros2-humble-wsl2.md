# Tutorial — Setup do ambiente: WSL2 + Ubuntu 22.04 + ROS 2 Humble

**Disciplina:** PB Sistemas Robóticos · caminho padrão da disciplina (Windows 11). Ubuntu nativo/dual boot também é aceito — pule direto ao Passo 3. Tempo total: ~40–60 min (dependendo da internet).

> **Está numa máquina do laboratório, ou o WSL2 não instala nesta máquina?** Existe uma rota alternativa: [ROS 2 Humble no VirtualBox](setup-ros2-humble-virtualbox.md). Faça os Passos 1–4 de lá e volte para cá **a partir do [Passo 2](#passo-2-preparar-o-ubuntu)** — do preparo do Ubuntu em diante os dois caminhos são idênticos. Escolha **uma rota por máquina**: manter WSL2 e VirtualBox ativos na mesma máquina Windows costuma quebrar os dois (Hyper-V).

## Passo 1 — Instalar o WSL2 com Ubuntu 22.04

No **PowerShell como Administrador**:

```powershell
wsl --install -d Ubuntu-22.04
```

Reinicie quando pedido. Na primeira abertura do Ubuntu, crie usuário e senha (a senha não aparece ao digitar — é normal). Depois, atualize o WSL:

```powershell
wsl --update
wsl --version    # confirme WSL versão 2.x e WSLg presente
```

> **Se falhar:** virtualização provavelmente desativada na BIOS/UEFI (procure *Intel VT-x / AMD SVM* e ative) ou recursos do Windows desligados (`Plataforma de Máquina Virtual` e `Subsistema do Windows para Linux` em "Ativar ou desativar recursos do Windows").

### ⚠️ Passo 1.5 — CONFIRA a versão antes de continuar (erro nº 1 da turma)

Se você **já tinha** um Ubuntu no WSL (ou instalou sem o `-d Ubuntu-22.04`), o terminal pode estar abrindo **outra versão** — ex.: Ubuntu 26.04 "Resolute Raccoon", que é o padrão atual do `wsl --install`. **O ROS 2 Humble só existe para o 22.04 (codinome `jammy`)** — em qualquer outro, o Passo 3 falha com `Unable to locate package ros-humble-desktop`.

No PowerShell:

```powershell
wsl --list --verbose              # liste os distros instalados
wsl -d Ubuntu-22.04               # abra especificamente o 22.04
wsl --set-default Ubuntu-22.04    # torne-o o padrão do terminal
```

E dentro do Ubuntu, confirme antes de seguir:

```bash
lsb_release -a    # DEVE mostrar: Ubuntu 22.04.x LTS (jammy)
```

Se mostrar outra versão, volte ao Passo 1 e instale o `Ubuntu-22.04` — não adianta continuar.

> 💼 **Você já usa WSL para trabalho/outras tarefas?** Mantenha uma **distro dedicada ao bloco** (`Ubuntu-22.04`) separada da sua distro de trabalho, e crie o hábito de conferir **em qual distro cada terminal está** antes de rodar qualquer coisa da disciplina (`lsb_release -a` na dúvida; o nome também aparece na aba do Windows Terminal). Misturar contextos é a receita para "funcionava ontem".

## Passo 2 — Preparar o Ubuntu

No terminal do Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y locales curl gnupg software-properties-common
sudo locale-gen pt_BR.UTF-8 en_US.UTF-8
```

## Passo 3 — Instalar o ROS 2 Humble (desktop-full)

Primeiro, a trava de segurança — este bloco só deixa continuar se o Ubuntu for o correto:

```bash
source /etc/os-release
[ "$UBUNTU_CODENAME" = "jammy" ] && echo "OK: Ubuntu 22.04 (jammy) — pode seguir" \
  || echo "PARE: este Ubuntu é '$UBUNTU_CODENAME' ($VERSION). O Humble exige 22.04 (jammy) — volte ao Passo 1.5"
```

Só depois do **OK**, instale (repare que o repositório usa `jammy` fixo, de propósito):

```bash
# habilitar o repositório universe
sudo add-apt-repository universe -y

# chave e repositório do ROS 2 (jammy = Ubuntu 22.04, alvo do Humble)
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu jammy main" | \
  sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-humble-desktop ros-dev-tools python3-colcon-common-extensions python3-rosdep
sudo rosdep init && rosdep update
```

## Passo 4 — Configurar o ambiente (faça uma vez)

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=SEU_NUMERO" >> ~/.bashrc   # veja o aviso abaixo!
source ~/.bashrc
```

> ⚠️ **ROS_DOMAIN_ID — importante no laboratório:** máquinas na mesma rede com o mesmo domain ID **enxergam os tópicos umas das outras** — na aula, você veria os nós dos colegas misturados aos seus. Use um número único seu (ex.: seu número na lista de chamada, entre 1 e 101) em **todas** as suas máquinas.

## Passo 5 — Reiniciar o WSL e testar

**Antes dos testes gráficos, reinicie o WSL** (evita janelas cinzas/minúsculas com título `[WARN:COPY MODE]` — glitch conhecido do WSLg logo após instalações grandes). No **PowerShell**:

```powershell
wsl --shutdown
```

Reabra o Ubuntu-22.04 e teste:

```bash
ros2 doctor          # deve terminar com "All ... checks passed"
ros2 run demo_nodes_cpp talker    # terminal 1
ros2 run demo_nodes_py listener   # terminal 2 — deve ecoar as mensagens
ros2 run turtlesim turtlesim_node # janela gráfica deve abrir (WSLg)
rqt_graph                         # visualize o grafo — captura útil p/ relatórios!
```

**Capturas do `ros2 doctor` e do talker/listener são evidências do TP1 — guarde-as.**

## Passo 6 — Ferramentas da disciplina

```bash
sudo apt install -y git gh python3-opencv
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@exemplo.com"
gh auth login
```

**Pacotes e ambientes Python: o padrão da disciplina é o [`uv`](https://docs.astral.sh/uv/)** (rápido e sem dor de cabeça de versões — não usaremos `pip` direto). Instale-o agora; ele será usado **sempre via ambientes virtuais**, nos tutoriais que precisarem:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc          # (ou abra um novo terminal)
uv --version
```

**Regras de ouro do Python na disciplina:**

1. **O Python do sistema é território do `apt`** — as bibliotecas base do TP1 já vieram nos passos anteriores (`python3-opencv` inclui o NumPy). Confirme:
   ```bash
   python3 -c "import cv2, numpy; print('OpenCV', cv2.__version__, '| NumPy', numpy.__version__, numpy.__file__)"
   ```
   Os dois têm que vir de `/usr/lib/python3/dist-packages` — OpenCV **4.x** e NumPy **1.x**. Se aparecer OpenCV 5.x, NumPy 2.x, ou um caminho em `~/.local` ou `/usr/local`, algum `pip` fora de venv passou por aqui:

   ```bash
   python3 -m pip uninstall -y numpy opencv-python opencv-contrib-python opencv-python-headless
   sudo apt install --reinstall python3-opencv python3-numpy
   ```

   Repita o `uninstall` até dizer que não está instalado (use `sudo` se o caminho for `/usr/local`). Isso importa porque o `cv_bridge` do ROS 2 é compilado contra OpenCV 4.5.4 e NumPy 1.x: sob NumPy 2 a extensão em C++ não carrega, e o OpenCV 5 renumerou as constantes de tipo. Nos dois casos o sintoma aparece só lá na frente, longe da causa, como `KeyError: 16` na primeira conversão de imagem.
2. **Nunca `sudo uv ...`** (o uv vive no seu usuário; o root não o encontra) e **nunca `uv pip install --system`** (tentaria escrever nas pastas do sistema — sem permissão, e nem queremos mexer nelas).
3. Pacotes além do apt (YOLO, TensorFlow, MetaDrive — TPs 2+) entram em **ambientes `uv venv --system-site-packages`** (que continuam enxergando o `rclpy` do ROS) — cada tutorial que precisar mostrará o comando exato.

(Gazebo, YOLO, TensorFlow, MetaDrive etc. têm tutoriais próprios, publicados quando cada etapa precisar.)

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `wsl --install` falha / WSL1 | Virtualização na BIOS; recursos do Windows; `wsl --set-default-version 2` |
| **`Unable to locate package ros-humble-desktop`** | Você não está no Ubuntu 22.04 — `lsb_release -a` para conferir (se aparecer 26.04 "resolute" ou outro, é o distro errado). Passo 1.5: abra/instale o `Ubuntu-22.04`. Limpeza no distro errado: `sudo rm /etc/apt/sources.list.d/ros2.list /usr/share/keyrings/ros-archive-keyring.gpg && sudo apt update` |
| `rosdep: command not found` | Consequência do erro acima: o `apt install` abortou e nada foi instalado. Resolva a versão do Ubuntu e repita o Passo 3 |
| `sudo: uv: command not found` | Não use `sudo` com uv — ele é instalado no SEU usuário (`~/.local/bin`), invisível para o root |
| `Permission denied ... dist-packages` (uv/pip) | Você tentou instalar no Python do sistema — não faça: o sistema é do `apt`; pacotes extras vão em `uv venv` (regras de ouro do Passo 6) |
| Janela gráfica não abre (turtlesim/rviz) | `wsl --update` no PowerShell e reinicie o WSL (`wsl --shutdown`); WSLg exige Win11 atualizado. **Na rota VirtualBox nada disso se aplica:** lá a janela é do próprio Ubuntu, e o culpado costuma ser Guest Additions ausente ou **aceleração 3D ligada** — [veja o guia do VirtualBox](setup-ros2-humble-virtualbox.md#quando-a-coisa-nao-coopera) |
| Janela abre **cinza/minúscula com `[WARN:COPY MODE]`** | Glitch do WSLg pós-instalação: `wsl --shutdown` no PowerShell e reabra o Ubuntu — resolve |
| `ros2: command not found` | Faltou `source /opt/ros/humble/setup.bash` (confira o `.bashrc`) |
| `ModuleNotFoundError: No module named 'PyQt5'` no `rqt_image_view`/`rqt_graph`/`rviz2` | Você está com um **venv ativado**. O `source /opt/ros/humble/setup.bash` expõe o ROS 2 via `PYTHONPATH`, que sobrevive à ativação do venv — por isso `ros2 launch` continua funcionando e só as ferramentas gráficas morrem. Já o `python3-pyqt5` do apt mora em `/usr/lib/python3/dist-packages`, caminho padrão do sistema que um venv sem `--system-site-packages` corta fora. `deactivate` resolve na hora; para não repetir, recrie com `uv venv --system-site-packages` |
| Taxas erráticas, `ros2 topic hz` com buracos de segundos ou `min:` negativo | O relógio do WSL2 está saltando — [seção abaixo](#o-relogio-do-wsl2-pode-saltar-e-isso-estraga-qualquer-medicao) |
| Vejo tópicos/nós que não criei | Colega na mesma rede com o mesmo `ROS_DOMAIN_ID` — defina o seu (Passo 4) |
| apt muito lento / trava | Rede da instituição pode limitar — tente hotspot ou faça em casa |
| Pouco espaço em disco | A disciplina pede ~50 GB livres. Limpe dentro do Ubuntu: `sudo apt clean` e apague `build/ install/ log/` antigos. **Não use** `--set-sparse true` (o WSL atual desativou por risco de corrupção de dados; forçar com `--allow-unsafe` não vale o risco). Compactar o disco virtual é possível via `diskpart`/`compact vdisk` (avançado, opcional). **Na rota VirtualBox:** o `.vdi` cresce e **nunca encolhe sozinho** — apagar arquivo dentro da VM não devolve espaço ao Windows; dimensione o disco com folga desde o início |
| Webcam | **WSL2:** precisa do `usbipd-win` — [tutorial próprio da disciplina](camera-wsl2-usbipd.md) (a partir da Etapa 2). **VirtualBox:** `usbipd` não existe nessa rota; a webcam entra pelo Extension Pack, em *Dispositivos → Webcams* ([seção do guia](setup-ros2-humble-virtualbox.md#webcam-extension-pack-nao-usbipd)) |

## O relógio do WSL2 pode saltar — e isso estraga qualquer medição

Este é um defeito do ambiente, não do seu código, e vale conhecer **antes** de perder uma tarde. O WSL2 sincroniza continuamente o relógio do Ubuntu com o do Windows. Se o Ubuntu também estiver rodando o próprio serviço de hora — o `systemd-timesyncd`, ativo por padrão quando `/etc/wsl.conf` tem `systemd=true` — os dois corrigem o mesmo relógio em direções opostas, e ele passa a oscilar vários segundos, várias vezes por minuto. Some a isso a suspensão da VM pelo gerenciamento de energia do Windows (notebook na bateria, ocioso) e o resultado é um relógio que anda para frente e para trás sozinho.

### Como reconhecer

O sinal mais claro aparece em `ros2 topic hz`:

```
average rate: 0.891
        min: -5.108s max: 6.300s
```

**Um intervalo negativo entre duas mensagens é impossível** — nada chega antes de ter sido enviado. Quando um número desses aparece na saída, ele não é ruído: é a prova de que uma premissa da medição quebrou. Aqui, a premissa é que o relógio anda sempre para frente.

Para confirmar em trinta segundos, compare o relógio de parede com o monotônico — o monotônico nunca anda para trás, então divergência entre os dois acusa quem saltou:

```bash
python3 - <<'PY'
import time
t0, m0 = time.time(), time.monotonic()
saltos = 0
for _ in range(60):
    time.sleep(0.5)
    dw, dm = time.time() - t0, time.monotonic() - m0
    if abs(dw - dm) > 0.2:
        saltos += 1
        print(f"  SALTO: parede {dw:6.2f}s  monotonico {dm:6.2f}s  ->  {dw-dm:+.2f}s")
        t0, m0 = time.time(), time.monotonic()
print(f"saltos em 30s: {saltos}")
PY
```

Saltos de tamanho sempre igual, repetindo com período regular, são a assinatura de duas autoridades de tempo brigando. Deriva de relógio de verdade é lenta e monótona, e não faz isso.

### Como curar

```bash
timedatectl status                                  # "NTP service: active" = ha um servico interno
sudo systemctl disable --now systemd-timesyncd      # deixe so o WSL sincronizar
```

Se persistir, `wsl --shutdown` no PowerShell e reabra — **e refaça o `usbipd attach` se estiver usando webcam**, porque o shutdown derruba o encaminhamento. Em notebook, mantenha a máquina na tomada durante a aula: a economia de energia suspende a VM do WSL, e o tempo suspenso não é contado pelo relógio monotônico, mas é contado pelo de parede.

### Por que isso quebra mais do que a medição

O `create_timer` do `rclpy` usa, por padrão, o relógio do sistema. Um salto de −6 s faz o timer esperar seis segundos a mais pelo próximo disparo: o nó **congela de verdade**, sem erro nenhum no log, e o sintoma aparece como se a câmera ou a rede tivessem travado. O exemplo da Aula 3 se protege pedindo o relógio monotônico explicitamente:

```python
from rclpy.clock import Clock, ClockType
self.create_timer(periodo, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))
```

O `header.stamp` das mensagens continua no relógio de parede — ele é o carimbo do mundo, e tem que ser comparável com o de outras máquinas. O que muda é só o laço, que passa a andar num relógio que não pode retroceder.

!!! tip "O hábito que isso ensina"
    Procure o **impossível** na saída antes de procurar o improvável. "Está meio lento" comporta dez explicações confortáveis e nenhuma decisiva; um intervalo negativo comporta uma só, e aponta direto para a premissa quebrada. Vale para o TP de vocês: quando um número não pode existir, ele é o melhor lugar para começar.

## Checklist final

- [ ] `ros2 doctor` passou · - [ ] talker/listener funcionando · - [ ] turtlesim abriu (GUI ok)
- [ ] `ROS_DOMAIN_ID` único definido · - [ ] git + gh autenticados + `uv` instalado · - [ ] capturas guardadas

**➡️ Próximo passo: tutorial "Workspace Colcon e o seu primeiro pacote ROS 2"** — é lá que você aprende a compilar e cria seu primeiro nó.

Dúvidas: traga na aula ou no Infnet.Online. Referências: docs oficiais ROS 2 Humble (https://docs.ros.org/en/humble/) e bibliografia A/B do bloco (O'Reilly).
