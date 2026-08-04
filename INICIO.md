---
hide:
  - navigation
---

# PB Sistemas Robóticos — INFNET 2026.2

Material da disciplina **Projeto de Bloco: Sistemas Robóticos**, turma GRPEDCR3C1-M1-P1.
Aulas às **terças, 07h00–09h30, sala SJ205** · Prof. Dácio Moreira de Souza.

<div class="pb-hero" markdown>
**Ao longo do semestre você vai construir um sistema robótico seu, do zero até a demonstração.** Não são cinco trabalhos avulsos: são cinco cortes do *mesmo* projeto, que cresce de um nó publicando imagem (TP1) até um robô que percebe, mapeia, navega, manipula e aprende (TP5). Escolher bem o projeto na primeira semana é a decisão mais barata e mais valiosa do bloco.
</div>

## Comece por aqui

<div class="grid cards" markdown>

-   :material-console:{ .lg .middle } **1. Monte o ambiente**

    ---

    Ubuntu 22.04 + ROS 2 Humble + Python 3.10. **Escolha uma rota por máquina:** WSL2 (padrão, Windows 10/11), VirtualBox (laboratório, Windows Home, política corporativa) ou Ubuntu nativo. Do ROS 2 em diante é tudo igual nas três. Os tutoriais validam cada pré-requisito antes de instalar.

    [:octicons-arrow-right-24: Setup ROS 2 Humble no WSL2](tutoriais/setup-ros2-humble-wsl2.md)

    [:octicons-arrow-right-24: Rota alternativa: VirtualBox](tutoriais/setup-ros2-humble-virtualbox.md)

-   :material-github:{ .lg .middle } **2. Prepare o seu repositório**

    ---

    Aceite o convite do GitHub Classroom, clone **dentro do Linux** (na home do Ubuntu — nunca numa pasta do Windows) e rode `init-branches.sh`. O repositório é parte da entrega, não um anexo dela.

    [:octicons-arrow-right-24: Manual do aluno: GitHub e entregas](tutoriais/manual-do-aluno-github.md)

-   :material-lightbulb-on:{ .lg .middle } **3. Escolha o seu projeto**

    ---

    Sete famílias no catálogo, dezenas de derivações possíveis. Escolha o domínio que te interessa — o esqueleto técnico é o mesmo.

    [:octicons-arrow-right-24: Catálogo de projetos](recursos/catalogo-projetos.md)

-   :material-flag-checkered:{ .lg .middle } **4. Marque os seus gates**

    ---

    Cada TP tem checkpoints verificáveis por comando, com data. Copie o checklist para o seu `PROJETO.md` e faça um commit por gate.

    [:octicons-arrow-right-24: Gates de cada TP](recursos/gates-tps.md)

</div>

## Aula mais recente

**Aula 3 — terça, 04/08/2026 — Comunicação e Visão Computacional** <span class="pb-tag next">atual</span>

O tópico deixa de carregar texto e passa a carregar **imagem**. Montamos o pipeline `câmera → segmentação HSV → contagem → serviço`, que é literalmente o esqueleto dos itens 3 e 4 do TP1.

[Conteúdo e slides da aula](aulas/etapa02-aula03/index.md){ .md-button .md-button--primary }
[Exemplo executável](exemplos/aula03-visao/index.md){ .md-button }
[Tarefa da semana](tutoriais/tarefa-aula03-visao.md){ .md-button }

!!! warning "Avisos de 04/08 — leia antes de rodar o exemplo da Aula 3"
    **1. `KeyError: 16` no `cv_bridge`.** Se você instalou OpenCV ou NumPy com `pip` **fora de um venv**, o exemplo da Aula 3 quebra com um `KeyError: 16` que não parece ter relação com nada. O material foi corrigido com o diagnóstico e a cura completa: [o aviso na página da aula](aulas/etapa02-aula03/index.md#cv_bridge-e-o-que-fazer-quando-ele-nao-coopera). **Nada trava:** o exemplo detecta o problema sozinho no import e converte a imagem na mão. A regra da disciplina continua a mesma — **bibliotecas do sistema vêm do `apt`; o `uv` só dentro de um venv**, nunca com `sudo`, nunca com `--system`.

    **2. `Exception ignored in: <function Future.__del__ …>` ao sair com `Ctrl+C`.** É ruído conhecido do `rclpy` do Humble na coleta de lixo do desligamento — não é erro do seu código. A linha que importa é `process has finished cleanly`.

    **3. Rota VirtualBox.** Quem usa (ou vai usar) as máquinas do **laboratório**, ou não consegue WSL2 na sua máquina, agora tem um guia próprio: [ROS 2 Humble no VirtualBox](tutoriais/setup-ros2-humble-virtualbox.md). Do ROS 2 em diante, tudo é igual às outras rotas — o que muda é a webcam, as pastas compartilhadas e a rede.

    **4. O `check-ambiente.sh` ficou mais esperto.** Ele detecta a sua rota e agora também confere de onde vêm o OpenCV e o NumPy: `curl -sSL https://raw.githubusercontent.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio/main/recursos/check-ambiente.sh | bash`

## Calendário de entregas

Todas as entregas são no **Moodle**, na sexta-feira indicada, com o repositório atualizado e a tag correspondente empurrada.

| Entrega | Data | Tema |
|---|---|---|
| **TP1** | sexta, 28/08/2026 | ambiente, comunicação básica e pipeline inicial de visão |
| **TP2** | sexta, 25/09/2026 | interfaces próprias, ações e parametrização |
| **TP3** | sexta, 23/10/2026 | integração, mapeamento (SLAM) e percepção avançada |
| **TP4** | **sábado, 21/11/2026 até 12h** | navegação autônoma, registro e percepção veicular |
| **TP5** | sexta, 27/11/2026 | manipulação, aprendizado e validação |
| **Entrega final** | sexta, 04/12/2026 | sistema integrado, vídeo e relatório |
| Apresentações | terças, 08/12 e 15/12/2026 | banca e arguição |

Prazo que cai em feriado passa para **meio-dia do dia seguinte** — foi o que aconteceu com o TP4.

## Como as entregas funcionam

A entrega **oficial e formal** de todo TP é no **Moodle**: ZIP dos códigos, PDF do relatório e os links. É o que gera registro acadêmico, e sem ela não há nota.

O **GitHub é complementar e obrigatório**, e também é critério de avaliação. O repositório é onde o processo fica visível: histórico de commits, branches `dev` → `main` → `entrega-tpN`, a tag `tpN` que congela o código corrigido, e as evidências commitadas. Um TP entregue só no Moodle, com repositório vazio ou com um único commit "projeto final", perde pontos — porque a disciplina avalia como você chegou lá, não apenas onde chegou.

Arquivos grandes (vídeos, datasets, bags, pesos de modelo) **não** vão para o Git. Publique em link acessível — YouTube **público ou não-listado**, nunca privado — e coloque o link no relatório e no README. A regra é dura de propósito: **se o avaliador não consegue abrir, não existe**. Teste cada link em uma janela anônima antes de entregar.

## Onde encontrar cada coisa

O material está organizado por uso, não por data. Em **[Aulas](aulas/index.md)** ficam o roteiro e os slides de cada encontro. Em **[Tutoriais](tutoriais/index.md)** ficam os guias que você segue passo a passo, de setup a tarefa da semana. Em **[Projeto](recursos/index.md)** ficam as decisões estruturais: catálogo, derivações, simulação × hardware e os gates. Em **[Exemplos](exemplos/index.md)** ficam os pacotes ROS 2 prontos para rodar e adaptar (licença MIT — pode copiar). E em **[Consulta rápida](cheatsheets/index.md)** ficam as referências de comando para o dia a dia.

!!! tip "Este site é atualizado a cada aula"
    Se preferir trabalhar offline, clone o repositório e rode `git pull` toda semana:
    ```bash
    gh repo clone Prof-Dacio-INFNET/PBRoboticos_prof_dacio
    ```
    Espelho e arquivos grandes: [daciosouza.com.br/PB_sistRoboticos](https://daciosouza.com.br/PB_sistRoboticos/).

## Uso de IA

Ferramentas de IA são **permitidas e incentivadas** — com declaração. O que se avalia é o seu entendimento, e a arguição final vai testar exatamente isso: você precisa saber explicar cada linha que entregou. As regras estão em [orientação sobre uso de IA](tutoriais/orientacao-uso-ia.md).

---

© 2026 Dácio Moreira de Souza. Material didático sob **CC BY-NC-ND 4.0**; códigos em `exemplos/` sob **MIT** e livremente reutilizáveis nos projetos, mantendo o aviso de copyright. Detalhes em [licença](licenca.md).
