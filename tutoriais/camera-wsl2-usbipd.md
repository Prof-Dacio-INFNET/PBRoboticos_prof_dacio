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

## Passo 2 — Instalar o `v4l-utils` no Ubuntu

```bash
sudo apt update
sudo apt install -y v4l-utils
```

O `v4l-utils` não participa do encaminhamento — ele é o **instrumento**. É com ele que você confere, mais adiante, se a câmera apareceu de verdade e em que formatos ela opera.

!!! note "Se você viu instruções mandando instalar `linux-tools-virtual` e criar um `update-alternatives` para o `usbip`, elas envelheceram"
    As versões atuais do `usbipd-win` carregam o módulo `vhci_hcd` sozinhas — você vê a linha `usbipd: info: Loading vhci_hcd module.` na saída do `attach` — e o cliente `usbip` do lado do Linux deixou de ser necessário.

    Pior do que desnecessário: o `linux-tools-virtual` do repositório do Ubuntu traz ferramentas para o kernel **do Ubuntu** (algo como `5.15.0-190`), enquanto o WSL2 roda um kernel próprio da Microsoft — confira com `uname -r`, vai aparecer algo como `6.x…-microsoft-standard-WSL2`. O resultado é um aviso barulhento sobre pacotes faltando "para este kernel específico" que **não é a causa de problema nenhum** e manda você caçar no lugar errado. Se você já instalou, não precisa desfazer: ignore o aviso.

## Passo 3 — Descobrir e compartilhar o dispositivo

No PowerShell como administrador:

```powershell
usbipd list
```

A saída lista os dispositivos com um `BUSID`. Identifique a sua câmera pela descrição — costuma conter "Camera", "Webcam" ou o nome do fabricante. **Anote o BUSID**; ele muda quando você troca a porta USB.

```powershell
usbipd bind --busid <SEU-BUSID>
```

O `<SEU-BUSID>` é para ser substituído pelo número que apareceu na *sua* saída — não é um exemplo que funciona. Um número plausível nessa linha convida a copiar e colar sem trocar, e o que acontece depois não aponta para a causa: no melhor caso um `device is not shared`, no pior o silêncio de ter compartilhado o dispositivo errado.

O `bind` é feito **uma vez** por dispositivo e persiste entre reinicializações.

## Passo 4 — Conectar ao WSL (toda vez)

```powershell
usbipd attach --wsl --busid <SEU-BUSID>
```

Este é o comando que você vai esquecer. **O `attach` se perde a cada reinício do Windows, a cada `wsl --shutdown` e sempre que a câmera é desconectada fisicamente.** Quando a webcam "parar de funcionar do nada", este é o primeiro comando a rodar.

!!! warning "O laço que pega todo mundo pelo menos três vezes"
    Repare que quase toda cura deste tutorial e do [guia de ambiente](setup-ros2-humble-wsl2.md) termina em `wsl --shutdown`: trocar de grupo, arrumar o relógio, destravar a janela gráfica. **E o `wsl --shutdown` derruba o `attach`.**

    Então a ordem é sempre esta, e sempre inteira:

    1. `wsl --shutdown` no PowerShell
    2. reabrir o Ubuntu
    3. `usbipd attach --wsl --busid <SEU-BUSID>` no PowerShell, **de novo**

    Pular o passo 3 devolve um `/dev/video0` que não existe, com uma mensagem de erro que fala de câmera — nunca de ordem de comandos. Se você se pegar repetindo "mas funcionava agora há pouco", é quase sempre isto.

Confirme no Ubuntu:

```bash
ls -l /dev/video*
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

O `--list-formats-ext` mostra as resoluções e taxas que a câmera aceita de verdade. Peça uma combinação que esteja nessa lista: pedir 1920×1080 a 30 fps de uma câmera que só entrega 1280×720 a 30 fps costuma resultar em 5 fps silenciosos, e você perde uma tarde achando que o problema é o ROS.

## Quando o `attach` falha com `Device busy (exported)`

Se a saída for esta:

```
WSL usbip: error: Attach Request for <SEU-BUSID> failed - Device busy (exported)
usbipd: warning: The device appears to be used by Windows; stop the software
using the device, or bind the device using the '--force' option.
```

o Windows está segurando o dispositivo. Em **notebook**, a causa quase sempre tem nome próprio: a webcam interna costuma ser um dispositivo composto — a listagem mostra algo como `FHD Webcam, IR Camera` — e a metade infravermelha é a do **Windows Hello**, que fica aberta o tempo todo, não só quando algum aplicativo está filmando. Fechar Teams, Zoom e o app Câmera não resolve, porque nenhum deles é o culpado.

Três saídas, da menos à mais invasiva:

1. **Use outra câmera.** Uma webcam USB comum, sem infravermelho, não é disputada pelo Windows Hello e anexa na primeira tentativa. É a solução mais barata se você já tem uma na gaveta.
2. **Desligue o reconhecimento facial** em *Configurações → Contas → Opções de entrada → Reconhecimento facial → Remover*, e repita o `attach`.
3. **Force a liberação do driver do Windows**, no PowerShell **como administrador**:

    ```powershell
    usbipd bind --force --busid <SEU-BUSID>
    usbipd attach --wsl --busid <SEU-BUSID>
    ```

    Enquanto o `--force` estiver valendo, **o Windows perde a câmera** e o login por reconhecimento facial para de funcionar. A volta é limpa e imediata:

    ```powershell
    usbipd detach --busid <SEU-BUSID>
    usbipd unbind --busid <SEU-BUSID>
    ```

Nada disso é obrigatório para a disciplina: `fonte:=sintetico` roda o exemplo inteiro sem câmera nenhuma.

## Passo 5 — Permissão de acesso

Se o dispositivo existe mas o OpenCV não abre, é permissão:

```bash
sudo usermod -aG video "$USER"
```

Trocar de grupo **não vale na sessão que já está aberta**. A linha entra no `/etc/group` na hora, mas os processos existentes seguem carregando as credenciais antigas — e o sintoma é cruel, porque o `ls -l /dev/video0` mostra o dispositivo lá, com o grupo `video` no lugar certo, e mesmo assim tudo falha com `Permission denied`.

Para **testar agora**, sem derrubar nada:

```bash
newgrp video          # abre um shell novo ja com o grupo
groups                # tem que listar 'video'
v4l2-ctl --list-devices
```

Para **valer de vez**, é sessão nova de verdade: `wsl --shutdown` no PowerShell, reabrir o Ubuntu — e refazer o `attach`, como diz a caixa do Passo 4. O `groups` é o jeito rápido de saber em que pé você está: se `video` não aparece, este terminal não enxerga a câmera, por mais que ela exista.

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
| `attach` falha com `device is not shared` | faltou o `bind` (Passo 3), que precisa ser administrador |
| `attach` falha com `Device busy (exported)` | o Windows está segurando o dispositivo — em notebook, quase sempre o Windows Hello na metade IR da webcam interna. [Seção própria acima](#quando-o-attach-falha-com-device-busy-exported) |
| `/dev/video0` não existe depois do attach | confirme que o `attach` **realmente** passou (ele imprime `Loading vhci_hcd module`, sem linha de erro). Se você deu `wsl --shutdown` no meio do caminho, o attach caiu junto: reabra o Ubuntu e **refaça o attach** — nesta ordem |
| `/dev/video*` existe, com grupo `video`, e mesmo assim tudo dá `Permission denied` | a sessão atual carrega as credenciais antigas. `groups` para confirmar; `newgrp video` para testar; `wsl --shutdown` + reabrir + **re-attach** para valer (Passo 5) |
| `VideoCapture` devolve `False` e o log fala em GStreamer | o OpenCV tentou o GStreamer antes do V4L2. Abra com o backend explícito: `cv2.VideoCapture(0, cv2.CAP_V4L2)` |
| funcionava e parou depois de reiniciar | o `attach` se perdeu; refaça o Passo 4 |
| imagem abre mas a taxa é ridícula | veja [Medir a taxa sem se enganar](#medir-a-taxa-sem-se-enganar) — a causa mais comum **não** é a câmera |
| taxa erráticas, com buracos de segundos | quase sempre o relógio do WSL2 saltando, não o ROS. [Diagnóstico e cura no guia de ambiente](setup-ros2-humble-wsl2.md#o-relogio-do-wsl2-pode-saltar-e-isso-estraga-qualquer-medicao) |
| `ModuleNotFoundError: No module named 'PyQt5'` ao abrir `rqt_image_view` | você está com um **venv ativado**. As ferramentas gráficas do ROS 2 usam o `python3-pyqt5` do apt, que mora em `/usr/lib/python3/dist-packages` — caminho que um venv sem `--system-site-packages` corta fora. `deactivate` resolve na hora; a cura durável é recriar com `uv venv --system-site-packages` |
| a janela do `rqt_image_view` não aparece | é WSLg, não é a câmera — `wsl --update` e reabra o terminal |

!!! warning "O encaminhamento USB tem um custo real"
    O `usbipd` empacota o tráfego USB e o envia pela rede virtual. Para uma webcam a 640×480 isso é irrelevante; para 1080p a 30 fps, o gargalo passa a ser o encaminhamento, não o seu código. Se você está medindo taxa para a tarefa da Aula 3, **registre que a captura passa por usbipd** — é uma variável experimental legítima, e mencioná-la no relatório demonstra exatamente o tipo de cuidado que a disciplina avalia.

## Medir a taxa sem se enganar

Quando a imagem parece lenta, a tentação é culpar a câmera. Na prática ela costuma ser inocente, e existem quatro estágios entre o sensor e a sua tela — cada um capaz de derrubar a taxa sozinho. Meça em ordem, do mais perto do sensor para o mais longe.

**1. O que a câmera entrega, sem ROS no meio.** Uma câmera UVC oferece pelo menos dois formatos: `YUYV`, sem compressão, e `MJPG`, comprimido. O OpenCV escolhe `YUYV` por padrão, e a diferença no fio é grande — um quadro 640×480 em YUYV ocupa 614 kB; o mesmo quadro em MJPG ocupa umas dezenas de kB. Em 1080p a conta fica brutal: 4,1 MB por quadro. Como o `usbipd` empacota o tráfego USB e o manda pela rede virtual do WSL, esse volume vira gargalo bem antes de virar problema numa máquina com USB de verdade.

```bash
v4l2-ctl -d /dev/video0 --list-formats-ext        # o que a camera aceita
```

Peça uma combinação que esteja nessa lista. Pedir 1920×1080 a 30 fps de uma câmera que só entrega isso em MJPG resulta em 5 fps silenciosos, e você perde uma tarde achando que o problema é o ROS. O exemplo da disciplina já negocia `MJPG` por padrão e **imprime o formato que a câmera aceitou**, não o que foi pedido:

```
webcam negociada: 640x480 MJPG @30fps (o que a camera ACEITOU, nao o que foi pedido)
```

Se quiser comparar os dois: `ros2 launch aula03_visao visao.launch.py fonte:=webcam fourcc:=YUYV`.

**2. O instrumento também consome.** `ros2 topic hz /camera/image_raw` é um nó **Python** que desserializa cada mensagem inteira — a 15 fps são uns 13 MB/s passando por Python. Ele não está medindo o tópico: está medindo a si mesmo se afogando. O `rqt_image_view` sob WSLg tem o mesmo problema. Meça com uma régua leve, que anda junto do pipeline mas pesa alguns bytes:

```bash
ros2 topic hz /vision/contagem
```

Se essa marcar a taxa esperada, o pipeline está saudável e quem está lento são os observadores.

**3. Desconfie do impossível antes de desconfiar do provável.** Se o `hz` mostrar um `min:` **negativo**, pare tudo: intervalo negativo entre duas mensagens não existe, nada chega antes de ter sido enviado. Isso é o relógio saltando, e ele estraga toda medição feita com ele — [diagnóstico e cura aqui](setup-ros2-humble-wsl2.md#o-relogio-do-wsl2-pode-saltar-e-isso-estraga-qualquer-medicao).

**4. Só então, o transporte.** Imagem crua é mensagem grande, e mensagem grande é fragmentada em datagramas UDP. Perdeu um fragmento, perdeu o quadro inteiro — e aparece o `A message was lost!!!`. Numa máquina só, `export ROS_LOCALHOST_ONLY=1` em todos os terminais costuma resolver sem `sudo`. Se não resolver, aumente os buffers do kernel:

```bash
sudo sysctl -w net.core.rmem_max=2147483647
sudo sysctl -w net.ipv4.ipfrag_high_thresh=134217728
sudo sysctl -w net.ipv4.ipfrag_time=3
```

E, para uma demonstração, o caminho mais seguro é sempre carregar menos: `largura:=320 altura:=240` derruba o quadro de 900 kB para 230 kB.

## Um atalho que vale o esforço

Como o `attach` precisa ser repetido, deixe um atalho pronto no Windows para não depender da memória. Salve como `camera.ps1` na sua Área de Trabalho e rode com o botão direito → "Executar com PowerShell":

```powershell
usbipd attach --wsl --busid <SEU-BUSID>
```

Troque o `<SEU-BUSID>` pelo seu. Se você usa mais de uma porta USB, o mais robusto é rodar `usbipd list` antes — o BUSID acompanha a porta, não o dispositivo.

## Onde isso entra na disciplina

A câmera real é o **um elemento de hardware** do exemplo de trilha híbrida. Ela é suficiente para trazer variação de iluminação, ruído de sensor e latência de captura para o seu pipeline — os três fenômenos que a simulação não reproduz de graça — sem que você precise montar um robô. Se o seu projeto vai ter hardware, comece por aqui e leia o que a [régua assimétrica](../recursos/simulado-vs-hardware.md) espera de cada trilha antes de decidir ir além.
