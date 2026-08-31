# Exemplo — `aula06-interfaces`

**Aula 6 · Etapa 3.** Dois pacotes: um que só define mensagens e serviços, e outro que os usa. É a arquitetura padrão de qualquer projeto ROS 2 que cresce.

```
aula06-interfaces/
├── pb_interfaces/        # ament_cmake -- SÓ interfaces, nenhum nó
│   ├── msg/Deteccao.msg
│   ├── msg/Deteccoes.msg
│   ├── srv/StatusVisao.srv
│   └── action/VarrerCena.action   # acrescentada na Aula 7
└── aula06_percepcao/     # ament_python -- os nós, dependendo do de cima
    ├── detector.py       # segmenta e publica Deteccoes; serve StatusVisao
    ├── monitor.py        # lê /vision/deteccoes e imprime uma linha legível
    └── cena.py           # cena sintética + conversão Image→numpy sem cv_bridge
```

## Rodar

A ordem importa: interface compilada e `source` **antes** do nó que a importa.

```bash
# 1) baixar o material (pode repetir sempre)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

# 2) copiar os DOIS pacotes para dentro do SEU projeto
cp -r /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/pb_interfaces \
      /tmp/PBRoboticos_prof_dacio/exemplos/aula06-interfaces/aula06_percepcao \
      ~/projeto-pb-SEU-USUARIO/ros2_ws/src/

# 3) compilar -- a ORDEM importa
cd ~/projeto-pb-SEU-USUARIO/ros2_ws

colcon build --packages-select pb_interfaces
source install/setup.bash

colcon build --packages-select aula06_percepcao --symlink-install
source install/setup.bash

ros2 launch aula06_percepcao percepcao.launch.py classe:=tomate_maduro
```

Noutro terminal:

```bash
ros2 interface show pb_interfaces/msg/Deteccoes
ros2 topic echo /vision/deteccoes --once
ros2 service call /vision/status pb_interfaces/srv/StatusVisao "{}"
```

**Não precisa de câmera.** O padrão é `fonte:=sintetico`, que gera a cena internamente. Para encadear com o publicador da Aula 3, use `fonte:=topico` e o nó assina `/camera/image_raw`.

## O que observar

Deixe o `monitor` rodando e acompanhe a linha impressa. Os dois objetos vermelhos orbitam e, periodicamente, se encostam: **a contagem cai de 2 para 1 e a confiança cai junto**. Esse é o experimento de oclusão da Aula 3 visto pela mensagem nova — antes você via só o número mudar; agora vê o detector perdendo certeza, o que é uma informação diferente e mais útil.

A `confianca` aqui é a **solidez** do contorno (área ÷ área do fecho convexo), não uma probabilidade. O código diz isso no comentário, de propósito: um substituto honesto e declarado vale mais do que um número inventado com cara de probabilidade. Trocar esse miolo por um detector treinado, mantendo a mesma mensagem, é o assunto da Etapa 4.

## O que copiar para o seu projeto

Renomeie `pb_interfaces` para `<seuprojeto>_interfaces` e troque os rótulos pelos do seu domínio. O `Deteccao.msg` já tem a forma certa para quase qualquer projeto de percepção — classe, confiança, posição, área —, e é justamente por ser genérico na *forma* e específico no *conteúdo* que ele sobrevive até o TP5.

Ao renomear o pacote de interfaces, o nome precisa bater em três lugares: `package.xml` (`<name>`), `CMakeLists.txt` (`project(...)`) e a pasta. É menos lugar do que num pacote Python, mas o esquecimento tem o mesmo efeito.

## Licença

MIT, como todo o diretório `exemplos/`. Copie, modifique e entregue como seu, mantendo o aviso de copyright.
