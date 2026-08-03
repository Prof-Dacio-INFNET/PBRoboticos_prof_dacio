# Projeto

Tudo o que estrutura **o seu projeto do semestre**: o que fazer, em que aplicação vesti-lo, com que grau de realidade, e em que ritmo. Os quatro documentos abaixo respondem, nessa ordem, às quatro perguntas que todo aluno faz — e é útil lê-los nessa sequência.

<div class="grid cards" markdown>

-   **1. O que eu faço?**

    ---

    Sete famílias de projeto compatíveis com os cinco TPs, com escopo, riscos e o que cada uma exige.

    [:octicons-arrow-right-24: Catálogo de projetos](catalogo-projetos.md)

-   **2. Em que aplicação?**

    ---

    O núcleo técnico é quase sempre o mesmo; o que muda é o domínio. Cinco derivações por família e uma tabela de troca de setor.

    [:octicons-arrow-right-24: Derivações e aplicações](derivacoes-projetos.md)

-   **3. Simulado ou real?**

    ---

    A régua é assimétrica de propósito. Trilhas S, H e R, com o que cada uma precisa entregar em cada TP.

    [:octicons-arrow-right-24: Simulação × hardware real](simulado-vs-hardware.md)

-   **4. Em que ritmo?**

    ---

    Checkpoints verificáveis por comando, com data e evidência, do TP1 à apresentação final.

    [:octicons-arrow-right-24: Gates de cada TP](gates-tps.md)

</div>

## Desafios semanais

Exercícios opcionais, sem nota, publicados junto com as aulas. Servem como aquecimento para o TP da etapa e são o melhor lugar para errar sem custo.

[:octicons-arrow-right-24: Ver os desafios](desafios/index.md)

## Ferramentas de apoio

O script `check-ambiente.sh` verifica, de uma vez, se o seu ambiente atende aos pré-requisitos da disciplina: distribuição correta, ROS 2 Humble presente, workspace compilável, git e `gh` configurados. Rode antes de cada aula prática e antes de pedir ajuda com qualquer problema de ambiente.

```bash
curl -sSL https://raw.githubusercontent.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio/main/recursos/check-ambiente.sh | bash
```

!!! note "Sobre executar scripts da internet"
    O comando acima baixa e executa um script. Isso é seguro **porque você pode ler o código antes** — está no repositório, é curto e não instala nada, apenas verifica. Ganhe o hábito de abrir o arquivo antes de rodar qualquer `curl | bash`, aqui e em qualquer outro lugar.

## Uma observação sobre mudar de ideia

Trocar de projeto, de derivação ou de trilha no meio do semestre é **permitido e saudável** — é o que engenheiro faz quando o risco muda. O que a disciplina cobra é o registro: uma entrada em `docs/decisoes.md` com data e motivo. Mudança documentada não tira nota; mudança silenciosa tira, porque quebra a rastreabilidade que a arguição final vai procurar.
