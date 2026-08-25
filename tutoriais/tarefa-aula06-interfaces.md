---
titulo: "Tarefa da Aula 6 — as interfaces do seu projeto"
tipo: tarefa
etapa: 3
alvo: "Ubuntu 22.04 · ROS 2 Humble"
---

# Tarefa da Aula 6 — as interfaces do seu projeto

**Publicada em 25/08/2026 · trazer pronta para a Aula 7, em 01/09/2026**

!!! danger "Antes de sexta, 28/08, existe uma coisa só: entregar o TP1"
    Esta tarefa é do TP2. Se o seu TP1 ainda não está fechado, o [checklist de entrega](checklist-entrega-tp1.md) vem primeiro — sem discussão. Volte aqui no fim de semana.

O objetivo é dar ao seu projeto um vocabulário próprio, e o critério de pronto é simples: **um colega consegue entender o que o seu robô percebe lendo só os seus `.msg`**, sem abrir o seu código.

## 1. Crie o seu pacote de interfaces

```bash
cd ~/SEU-REPO/ros2_ws/src
ros2 pkg create --build-type ament_cmake <seuprojeto>_interfaces
```

Ajuste o `package.xml` e o `CMakeLists.txt` como no [exemplo da aula](../exemplos/aula06-interfaces/index.md). As três linhas do `package.xml` que fazem o pacote gerar código são `rosidl_default_generators`, `rosidl_default_runtime` e `member_of_group`.

## 2. Escreva uma mensagem que descreva o SEU domínio

Comece pela `Deteccao.msg` do exemplo e **troque o vocabulário**. Se o seu projeto conta vagas de estacionamento, `classe` vale `vaga_livre` e `vaga_ocupada`; se inspeciona peças, vale `peca_ok` e `peca_refugo`. Acrescente o campo que o **seu** domínio precisa e o exemplo não tem — e apague o que não serve.

Duas perguntas para se fazer em cada campo: *quem vai ler isto?* e *o que a pessoa faz de diferente se este número mudar?* Campo que não muda decisão de ninguém é peso morto.

## 3. Migre o `/vision/status` do `Trigger` para o seu serviço

Este é o coração da tarefa, porque é uma **migração**, não uma criação: o serviço já existe e já funciona. Você troca o tipo, ajusta o nó e confere que o grafo continua de pé.

```bash
ros2 service type /vision/status          # antes: std_srvs/srv/Trigger
                                          # depois: <seuprojeto>_interfaces/srv/...
```

## 4. Publique detecções, não só a contagem

Mantenha o `/vision/contagem` funcionando — ele é a régua leve que você usa para medir taxa — e **acrescente** o tópico de detecções. Manter os dois é uma decisão consciente, não indecisão: um serve para medir, o outro para informar.

## 5. Evidência

Commite em `docs/evidencias/tp2/`:

```bash
ros2 interface show <seuprojeto>_interfaces/msg/<SuaMensagem> > docs/evidencias/tp2/interface.txt
ros2 topic echo /vision/deteccoes --once >> docs/evidencias/tp2/interface.txt
ros2 service call /vision/status <seuprojeto>_interfaces/srv/<SeuServico> "{}" >> docs/evidencias/tp2/interface.txt
```

## Critério de pronto

- [ ] `ros2 interface list | grep <seuprojeto>` mostra as suas interfaces
- [ ] o `/vision/status` responde no tipo novo, com informação do seu domínio
- [ ] `/vision/deteccoes` publica classe, confiança e posição
- [ ] os rótulos são do seu domínio — nenhum `objeto_alvo` sobrando
- [ ] evidência commitada

## Se travar

O erro mais comum é `ModuleNotFoundError` do pacote de interfaces, e ele quase nunca é o que parece: é falta de `source install/setup.bash` **depois** do build, em **todos** os terminais. O segundo mais comum é editar um `.msg` e esquecer de recompilar — o campo novo simplesmente não existe, com um erro que não menciona nada disso. Terminal novo resolve os dois.
