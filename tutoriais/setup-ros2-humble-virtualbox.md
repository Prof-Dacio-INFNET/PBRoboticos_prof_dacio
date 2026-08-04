---
titulo: "Ambiente alternativo: ROS 2 Humble no VirtualBox"
tipo: ambiente
etapa: 1
alvo: "Ubuntu 22.04.x LTS (jammy) Desktop sobre Oracle VirtualBox 7.x"
alternativa_de: "setup-ros2-humble-wsl2.md"
---

# Ambiente alternativo: ROS 2 Humble no VirtualBox

O caminho padrão da disciplina é o [WSL2](setup-ros2-humble-wsl2.md). Esta página é a **rota alternativa**, para quem roda o Ubuntu dentro do **Oracle VirtualBox** — que é o arranjo das máquinas do laboratório e a saída natural para quem não pode usar o WSL2 na própria máquina.

**Escolha uma rota por máquina e fique nela.** As três rotas aceitas na disciplina — WSL2, VirtualBox e Ubuntu nativo (dual boot) — entregam o mesmo ROS 2 Humble e a mesma nota. O que muda é a moldura: como a janela gráfica aparece, como a webcam chega, onde ficam os arquivos e o que acontece com a rede. É exatamente disso que esta página trata.

!!! info "O que **não** muda de uma rota para outra"
    Do `sudo apt install ros-humble-desktop` em diante, tudo é idêntico: os mesmos pacotes, os mesmos comandos, os mesmos exemplos, a mesma tarefa, os mesmos critérios de avaliação. A doutrina de instalação também é a mesma e vale igual: **OpenCV e `cv_bridge` vêm do `apt`; o `uv` só dentro de `venv`**. Um `pip install` fora de venv quebra o `cv_bridge` no VirtualBox exatamente como quebra no WSL2 — e do mesmo jeito, com um `KeyError: 16` que aparece longe da causa.

## Quando esta rota é a certa

Ela é a escolha adequada se você usa as **máquinas do laboratório**, que já vêm com o VirtualBox instalado; se está no **Windows Home** ou numa máquina corporativa onde o WSL2 é bloqueado por política; se está num **Mac Intel**; ou se simplesmente prefere uma máquina virtual descartável, que você pode apagar e refazer sem tocar no seu sistema.

Ela **não** é a escolha adequada em dois casos. Em **Mac com chip Apple (M1–M4)** o VirtualBox é experimental e não roda Ubuntu x86 — nesses casos use o laboratório, UTM ou uma alternativa combinada comigo antes. E, se você já tem o WSL2 funcionando, **não migre**: manter as duas coisas na mesma máquina Windows tem um custo real, explicado logo abaixo.

!!! warning "Windows: VirtualBox e WSL2 disputam o mesmo hardware"
    O WSL2 liga o Hyper-V, e com o Hyper-V ligado o VirtualBox deixa de usar a virtualização por hardware diretamente — ele passa a rodar *sobre* o Hyper-V, num modo bem mais lento (o ícone de tartaruga verde na barra da VM é esse aviso). O sintoma típico é uma VM que engasga, ou a mensagem `VT-x is not available`.

    A cura é escolher **uma** rota naquela máquina. Desligar o Hyper-V no boot é possível, é operação de administrador e **derruba o WSL2 junto** — só faz sentido se você decidiu abandonar o WSL2 nessa máquina. Se estiver nessa situação, fale comigo antes de mexer no boot.

## Passo 1 — Baixar o que é preciso

Você precisa de três downloads, e **as versões precisam combinar**:

| O quê | Onde | Observação |
|---|---|---|
| Oracle VirtualBox 7.x | <https://www.virtualbox.org/wiki/Downloads> | escolha o pacote do **seu** sistema hospedeiro (Windows/macOS Intel/Linux) |
| VirtualBox **Extension Pack** | mesma página | precisa ser **exatamente a mesma versão** do VirtualBox. É ele que traz USB 2.0/3.0 e webcam |
| Ubuntu **22.04.x LTS Desktop** (ISO) | <https://releases.ubuntu.com/22.04/> | **22.04, não 24.04 nem 26.04** — o ROS 2 Humble só existe para o `jammy` |

O Extension Pack não é opcional na prática: sem ele a webcam não passa para dentro da VM, e a Etapa 2 em diante fica sem hardware real.

## Passo 2 — Criar a máquina virtual

Ao criar a VM, **desmarque a "Instalação Desassistida" / "Skip Unattended Installation"**. O modo automático do VirtualBox 7 cria usuário e senha por conta própria e pula telas que você quer ver — inclusive a do idioma do teclado, que depois dá trabalho para corrigir.

Configure assim, ajustando para baixo se a sua máquina for modesta (os mínimos são o que ainda permite trabalhar, não o confortável):

| Ajuste | Onde | Mínimo | Recomendado |
|---|---|---|---|
| Memória RAM | Sistema → Placa-mãe | 4096 MB | 8192 MB |
| Processadores | Sistema → Processador | 2 | 4 |
| Disco (VDI dinâmico) | criação da VM | 40 GB | **60 GB** |
| Memória de vídeo | Tela → Tela | 64 MB | **128 MB** |
| Controlador gráfico | Tela → Tela | VMSVGA | VMSVGA |
| Aceleração 3D | Tela → Tela | **desligada** | **desligada** |
| Área de transferência / Arrastar e soltar | Geral → Avançado | — | Bidirecional |

Nunca dê à VM mais da metade da RAM nem todos os núcleos do hospedeiro: o Windows precisa dos dele, e uma VM com 100% dos núcleos fica **mais** lenta, não mais rápida.

!!! tip "Por que a aceleração 3D fica desligada"
    Com 3D ligado no VMSVGA, as janelas do `rqt_image_view` e do `rviz2` costumam sair pretas ou fechar sozinhas. Desligado, o Ubuntu desenha por software (`llvmpipe`): mais lento, e **estável** — que é o que interessa numa aula de 2h30. O preço aparece no Gazebo, na Etapa 3, que fica pesado; quando chegarmos lá eu indico o mundo reduzido, e quem tiver máquina nativa ou WSL2 leva vantagem nessa parte específica.

Antes de ligar a VM pela primeira vez, confirme que a virtualização está **ativa na BIOS/UEFI** do computador (procure *Intel VT-x* ou *AMD SVM*). Sem isso o VirtualBox não passa da tela inicial.

## Passo 3 — Instalar o Ubuntu 22.04

Aponte a unidade óptica da VM para a ISO, ligue a máquina e siga a instalação normal do Ubuntu. Três escolhas que valem atenção: instalação **mínima** é suficiente e economiza disco; marque **"Baixar atualizações durante a instalação"** se a rede permitir; e use "Apagar disco e instalar Ubuntu" **sem medo** — esse "disco" é o arquivo virtual da VM, não o seu HD.

Terminada a instalação, remova a ISO (Dispositivos → Unidades Ópticas → Remover disco) e reinicie.

Agora a mesma trava de segurança do tutorial principal — ela vale aqui igual:

```bash
lsb_release -a    # DEVE mostrar: Ubuntu 22.04.x LTS (jammy)
```

Se aparecer outra coisa, pare: refaça a VM com a ISO certa. Instalar o Humble sobre outra versão não funciona e você perde a noite descobrindo isso.

## Passo 4 — Guest Additions (não pule)

Sem as *Guest Additions* a tela fica presa em 800×600, a área de transferência não funciona e as pastas compartilhadas não montam. Dentro do Ubuntu:

```bash
sudo apt update
sudo apt install -y build-essential dkms linux-headers-$(uname -r)
```

Depois, no menu da janela da VM: **Dispositivos → Inserir imagem de CD dos Adicionais para Convidado**. O Ubuntu costuma oferecer para executar automaticamente; se não oferecer:

```bash
cd /media/$USER/VBox_GAs_*/
sudo ./VBoxLinuxAdditions.run
sudo reboot
```

Depois do reboot, redimensione a janela da VM: se a resolução acompanhar, funcionou.

## Passo 5 — ROS 2 Humble: daqui em diante é o tutorial principal

**Vá para o [Passo 2 do tutorial de ambiente](setup-ros2-humble-wsl2.md#passo-2-preparar-o-ubuntu) e siga até o fim**, incluindo o Passo 6 (git, `gh`, `python3-opencv` e as regras de ouro do Python). Nada ali é específico de WSL2 — é instalação de Ubuntu.

Três ajustes de leitura, ao percorrer aquele texto:

Onde estiver escrito **`wsl --shutdown` no PowerShell**, aqui é simplesmente **reiniciar a VM** (`sudo reboot`). Onde estiver escrito **`wsl --update` para consertar janela gráfica**, aqui o equivalente é conferir as Guest Additions e a aceleração 3D desligada — não existe WSLg nesta rota. E o **`ROS_DOMAIN_ID`** continua obrigatório: leia a próxima seção antes de decidir que "no VirtualBox não faz diferença".

Ao final, `ros2 doctor` precisa terminar com *All checks passed*, o par talker/listener precisa conversar e o `turtlesim` precisa abrir janela.

!!! success "Tire um snapshot agora — é a maior vantagem desta rota"
    Com o `ros2 doctor` passando, desligue a VM e faça **Máquina → Snapshots → Tirar snapshot**, com o nome `ros2-humble-ok`. Se daqui a três semanas você quebrar o ambiente (e alguém vai quebrar), voltar a esse ponto leva 30 segundos em vez de uma noite. Snapshots ocupam disco: mantenha um ou dois, não dez.

## O que é diferente nesta rota

| Assunto | WSL2 | VirtualBox |
|---|---|---|
| Janela gráfica (`rqt`, `rviz2`) | WSLg, automático | X do próprio Ubuntu; exige Guest Additions, 3D desligado |
| Reiniciar o ambiente | `wsl --shutdown` no PowerShell | `sudo reboot` dentro da VM |
| Webcam | `usbipd-win` ([tutorial](camera-wsl2-usbipd.md)) | Extension Pack + menu Dispositivos (abaixo) |
| Arquivos do Windows | `/mnt/c/...` | Pastas Compartilhadas em `/media/sf_<nome>` |
| Rede | compartilha a rede do Windows | NAT por padrão: **isolada** da rede local |
| Desempenho | quase nativo | 20–40% menor, e sem GPU |
| Disco | cresce e encolhe com o WSL | VDI **cresce e não encolhe sozinho** |
| Risco de perder tudo | baixo | **alto se a VM for de laboratório compartilhado** |

### Webcam: Extension Pack, não usbipd

O [tutorial do `usbipd`](camera-wsl2-usbipd.md) **não se aplica aqui** — ele resolve um problema que é só do WSL2. No VirtualBox o caminho é outro e é mais curto.

Instale o Extension Pack no hospedeiro (Arquivo → Ferramentas → Gerenciador de Extensões), com a VM desligada. No Linux hospedeiro, adicione também o seu usuário ao grupo `vboxusers`. Depois, com a VM ligada e a câmera conectada, use o menu **Dispositivos → Webcams** e escolha a câmera; se ela não aparecer ali, use **Dispositivos → USB** e marque o dispositivo pelo nome.

Confirme dentro do Ubuntu, exatamente como na outra rota:

```bash
sudo apt install -y v4l-utils
ls -l /dev/video*
v4l2-ctl --list-devices
python3 -c "import cv2; c=cv2.VideoCapture(0); ok,f=c.read(); print(ok, None if f is None else f.shape)"
```

Esperado: `True (480, 640, 3)`. Se vier `False None`, quase sempre é uma destas três coisas: o Extension Pack não está instalado, **algum programa do hospedeiro está com a câmera aberta** (feche Teams, Zoom, Meet, o app Câmera), ou falta você no grupo `video` dentro do Ubuntu (`sudo usermod -aG video "$USER"` e reiniciar a sessão).

Com a câmera funcionando, o exemplo da aula usa exatamente o mesmo comando das outras rotas:

```bash
ros2 launch aula03_visao visao.launch.py fonte:=webcam dispositivo:=0
```

E, como sempre, se a câmera falhar o nó cai sozinho para a fonte sintética. **A fonte sintética é aceita no TP1** — não trave o trabalho esperando hardware.

### Pastas compartilhadas: úteis para trocar arquivo, péssimas para o workspace

Para levar uma foto do celular ou um PDF para dentro da VM, configure uma pasta compartilhada (Configurações → Pastas Compartilhadas), marque **Montagem automática**, e dentro do Ubuntu:

```bash
sudo usermod -aG vboxsf "$USER"     # depois, encerre a sessão e entre de novo
ls /media/sf_<nome-da-pasta>
```

!!! danger "Não coloque o `ros2_ws` nem o clone do repositório na pasta compartilhada"
    É a mesma armadilha do `/mnt/c/...` no WSL2, pelo mesmo motivo: o sistema de arquivos atravessa a fronteira da VM a cada leitura. O `colcon build` fica absurdamente lento, as permissões saem erradas e o Git passa a ver arquivos modificados que ninguém tocou (fim de linha CRLF). **Clone em `~`**, dentro do Ubuntu, e use a pasta compartilhada só para copiar arquivos soltos.

### Rede: NAT esconde o problema que a aula quer mostrar

Por padrão o VirtualBox usa **NAT**, e a VM fica isolada da rede local: você não vê os tópicos de ninguém e ninguém vê os seus. No laboratório isso é conveniente — mas repare no efeito colateral. Se dois computadores no VirtualBox tentarem conversar por ROS 2, **não vão conseguir**, e o sintoma é aquele mesmo silêncio de sempre: o nó roda, o tópico existe, nada chega.

Duas consequências práticas. Primeira: **defina o `ROS_DOMAIN_ID` mesmo assim** — é o seu número de chamada, e vira hábito para quando importar. Segunda: quando o seu projeto precisar de duas máquinas conversando (Etapa 3 em diante, ou robô real), troque o adaptador para **Placa em modo Bridge** em Configurações → Rede → Adaptador 1. Aí a VM entra na rede local como se fosse um computador de verdade — e aí o `ROS_DOMAIN_ID` passa a ser o que separa você dos colegas.

### Se a VM é do laboratório, ela não é o seu backup

Máquinas de laboratório costumam ser restauradas entre turmas, e uma VM restaurada leva junto tudo o que estava dentro dela. **Trate a VM do laboratório como descartável**: no fim de cada sessão, `git add`, `git commit` e `git push` na sua branch `dev`. O que está empurrado sobrevive; o que está só na VM, não.

Isso não é burocracia da disciplina — é o motivo pelo qual o repositório é critério de avaliação. Quem trabalha assim chega no TP com histórico; quem trabalha só dentro da VM chega com um commit só, ou com nada.

## Quando a coisa não coopera

| Sintoma | Causa provável e cura |
|---|---|
| `VT-x is not available` / VM não liga | virtualização desativada na BIOS/UEFI, ou Hyper-V ligado no Windows (ver o aviso do início) |
| ícone de **tartaruga verde** na barra da VM | o VirtualBox está rodando sobre o Hyper-V, em modo lento. Escolha uma rota por máquina |
| tela presa em 800×600, sem tela cheia | Guest Additions não instaladas (Passo 4), ou instaladas antes do `linux-headers` |
| `rqt_image_view` / `rviz2` abre preto ou fecha sozinho | aceleração 3D **ligada**. Desligue em Tela → Tela e reinicie a VM |
| câmera não aparece em Dispositivos → Webcams | Extension Pack ausente ou de versão diferente da do VirtualBox |
| `/dev/video0` existe e `VideoCapture` devolve `False` | câmera em uso por um programa **do hospedeiro**, ou falta grupo `video` no Ubuntu |
| `colcon build` lentíssimo | o workspace está em `/media/sf_...`. Clone em `~` |
| Git mostra dezenas de arquivos modificados que você não tocou | mesmo motivo: repositório na pasta compartilhada, fim de linha trocado. `git checkout -- .` e mova o clone para `~` |
| "sem espaço" no Ubuntu, mas o Windows tem disco de sobra | o VDI atingiu o tamanho máximo, ou snapshots demais. `sudo apt clean`, apague `build/ install/ log/` antigos e snapshots velhos |
| disco do Windows encheu e a VM "não devolve" | o VDI dinâmico **cresce e não encolhe**. Compactar exige `zerofree`/`VBoxManage modifymedium --compact` (avançado) |
| `Unable to locate package ros-humble-desktop` | não é 22.04. `lsb_release -a` e refaça a VM com a ISO certa |
| `KeyError: 16` ao converter imagem | **nada a ver com VirtualBox** — é pip fora de venv. Ver a [tarefa da Aula 3](tarefa-aula03-visao.md#se-der-errado) |

## Checklist final

- [ ] `lsb_release -a` diz 22.04 (jammy) · - [ ] Guest Additions instaladas (tela redimensiona)
- [ ] Aceleração 3D desligada · - [ ] `ros2 doctor` passou · - [ ] talker/listener conversando
- [ ] `turtlesim` abriu janela · - [ ] `ROS_DOMAIN_ID` definido · - [ ] snapshot `ros2-humble-ok` tirado
- [ ] repositório clonado em `~`, **fora** da pasta compartilhada · - [ ] capturas guardadas para o TP1

**➡️ Próximo passo: [Workspace Colcon e o seu primeiro pacote ROS 2](workspace-colcon.md)** — a partir dali, a rota deixa de importar.

Dúvidas: traga na aula ou no Infnet.Online. Ao pedir ajuda, diga **em qual rota você está** (WSL2, VirtualBox ou nativo) e cole a saída de `lsb_release -a` — metade do diagnóstico vem daí.
