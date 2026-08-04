---
titulo: "Câmera USB no WSL2 com usbipd"
tipo: ambiente
etapa: 2
alvo: "Ubuntu 22.04 (jammy) sobre WSL2 · Windows 10/11"
opcional: true
---

# Câmera USB no WSL2 com usbipd

> **Este guia é só para a rota WSL2.** Se o seu Ubuntu roda em **VirtualBox**, `usbipd` não se aplica: lá a webcam entra pelo Extension Pack, em *Dispositivos → Webcams*. Veja [a seção de webcam do guia do VirtualBox](setup-ros2-humble-virtualbox.md#webcam-extension-pack-nao-usbipd). Em Ubuntu **nativo**, a webcam já aparece em `/dev/video0` e nada disso é necessário.

**Este guia é opcional.** Todo o material da disciplina roda sem webcam — o exemplo da Aula 3 gera a cena em código, e o caminho simulado precisa continuar funcionando de qualquer forma. Siga este tutorial quando quiser trazer ruído, iluminação e latência reais para o seu pipeline — é o elemento real do [meio termo descrito em simulação × hardware](../recursos/simulado-vs-hardware.md), e nenhuma trilha é obrigatória.

O WSL2 é uma máquina virtual e, por padrão, **não enxerga dispositivos USB do Windows**. O `usbipd-win` resolve isso encaminhando o dispositivo pela rede local da VM. Funciona bem, com uma ressalva importante que aparece no fim deste guia.

## Antes de começar: confira os pré-requisitos

Rode os três comandos abaixo e compare com o esperado. Se algum falhar, resolva **antes** de prosseguir — instalar na ordem errada aqui produz erros que só aparecem três passos depois.

No **PowerShell do Windows**, como administrador:

```powershell
wsl --version
```

Espere `WSL version` 2.x e `Kernel version` 5.15 ou superior. Se o comando não existir, sua instalação é antiga: rode `wsl --update` e reinicie o terminal.

No **terminal do Ubuntu**:

```bash
lsb_release -a          # espera-se: Ubuntu 22.04.x LTS, Codename: jammy
uname -r                # espera-se: ...-microsoft-standard-WSL2
```

Se `lsb_release` mostrar algo diferente de **jammy**, pare aqui: o ROS 2 Humble exige 22.04, e o resto da disciplina assume essa versão. Volte ao [guia de ambiente](setup-ros2-humble-wsl2.md).

## Passo 1 — Instalar o usbipd no Windows

No PowerShell **como administrador**:

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

Feche e reabra o PowerShell depois da instalação, senão o comando `usbipd` não é encontrado.

## Passo 2 — Instalar o cliente no Ubuntu

```bash
sudo apt update
sudo apt install -y linux-tools-virtual hwdata v4l-utils
sudo update-alternatives --install /usr/local/bin/usbip usbip \
  "$(ls /usr/lib/linux-tools/*/usbip | tail -n1)" 20
```

O `v4l-utils` não é obrigatório para o encaminhamento, mas é ele que vai te dizer, mais adiante, se a câmera realmente apareceu e em que formatos ela opera.

## Passo 3 — Descobrir e compartilhar o dispositivo

No PowerShell como administrador:

```powershell
usbipd list
```

A saída lista os dispositivos com um `BUSID` (algo como `2-4`). Identifique a sua câmera pela descrição — costuma conter "Camera", "Webcam" ou o nome do fabricante. **Anote o BUSID**; ele muda quando você troca a porta USB.

```powershell
usbipd bind --busid 2-4
```

O `bind` é feito **uma vez** por dispositivo e persiste entre reinicializações.

## Passo 4 — Conectar ao WSL (toda vez)

```powershell
usbipd attach --wsl --busid 2-4
```

Este é o comando que você vai esquecer. **O `attach` se perde a cada reinício do Windows, a cada `wsl --shutdown` e sempre que a câmera é desconectada fisicamente.** Quando a webcam "parar de funcionar do nada", este é o primeiro comando a rodar.

Confirme no Ubuntu:

```bash
ls -l /dev/video*
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

O `--list-formats-ext` mostra as resoluções e taxas que a câmera aceita de verdade. Peça uma combinação que esteja nessa lista: pedir 1920×1080 a 30 fps de uma câmera que só entrega 1280×720 a 30 fps costuma resultar em 5 fps silenciosos, e você perde uma tarde achando que o problema é o ROS.

## Passo 5 — Permissão de acesso

Se o dispositivo existe mas o OpenCV não abre, é permissão:

```bash
sudo usermod -aG video "$USER"
```

Feche o terminal, rode `wsl --shutdown` no PowerShell, e abra de novo. Trocar de grupo exige sessão nova — `newgrp` resolve só no terminal atual e engana.

## Passo 6 — Testar antes de envolver o ROS

Sempre teste na camada mais simples primeiro. Se o Python puro não abre a câmera, o problema não é seu nó:

```bash
python3 -c "import cv2; c=cv2.VideoCapture(0); ok,f=c.read(); print(ok, None if f is None else f.shape)"
```

Esperado: `True (480, 640, 3)`. Se vier `False None`, volte aos passos 4 e 5 — não adianta seguir para o ROS.

Com isso funcionando, o exemplo da aula usa a câmera assim:

```bash
ros2 launch aula03_visao visao.launch.py fonte:=webcam dispositivo:=0
```

E se a câmera falhar ao abrir, o nó cai sozinho para a fonte sintética em vez de morrer. Esse comportamento é intencional e é o padrão que o seu projeto deve seguir: **degradar, não quebrar**.

## Quando a coisa não coopera

| Sintoma | Causa provável e cura |
|---|---|
| `usbipd: command not found` | PowerShell aberto antes da instalação, ou não é administrador |
| `attach` falha com "device is not shared" | faltou o `bind` (Passo 3), que precisa ser administrador |
| `/dev/video0` não existe depois do attach | `wsl --shutdown` no PowerShell e refaça o `attach` |
| existe `/dev/video0` mas `VideoCapture` devolve `False` | grupo `video` (Passo 5), ou a câmera está em uso pelo Windows — feche Teams, Zoom, o app Câmera |
| funcionava e parou depois de reiniciar | o `attach` se perdeu; refaça o Passo 4 |
| imagem abre mas a taxa é ridícula | resolução fora da lista do `--list-formats-ext`, ou o encaminhamento USB está saturado |
| a janela do `rqt_image_view` não aparece | é WSLg, não é a câmera — `wsl --update` e reabra o terminal |

!!! warning "O encaminhamento USB tem um custo real"
    O `usbipd` empacota o tráfego USB e o envia pela rede virtual. Para uma webcam a 640×480 isso é irrelevante; para 1080p a 30 fps, o gargalo passa a ser o encaminhamento, não o seu código. Se você está medindo taxa para a tarefa da Aula 3, **registre que a captura passa por usbipd** — é uma variável experimental legítima, e mencioná-la no relatório demonstra exatamente o tipo de cuidado que a disciplina avalia.

## Um atalho que vale o esforço

Como o `attach` precisa ser repetido, deixe um atalho pronto no Windows para não depender da memória. Salve como `camera.ps1` na sua Área de Trabalho e rode com o botão direito → "Executar com PowerShell":

```powershell
usbipd attach --wsl --busid 2-4
```

Troque o BUSID pelo seu. Se você usa mais de uma porta USB, o mais robusto é rodar `usbipd list` antes — o BUSID acompanha a porta, não o dispositivo.

## Onde isso entra na disciplina

A câmera real é o **um elemento de hardware** do exemplo de trilha híbrida. Ela é suficiente para trazer variação de iluminação, ruído de sensor e latência de captura para o seu pipeline — os três fenômenos que a simulação não reproduz de graça — sem que você precise montar um robô. Se o seu projeto vai ter hardware, comece por aqui e leia o que a [régua assimétrica](../recursos/simulado-vs-hardware.md) espera de cada trilha antes de decidir ir além.
