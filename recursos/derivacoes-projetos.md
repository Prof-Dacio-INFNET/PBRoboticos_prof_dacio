# Derivações de projeto — o mesmo núcleo, dezenas de aplicações

Complemento do [catálogo de projetos](catalogo-projetos.md). O catálogo responde *"que projeto eu escolho?"*. Este documento responde a pergunta seguinte, que é a que realmente diferencia um PB bom de um PB memorável: **"escolhido o núcleo técnico, em que aplicação eu vou vesti-lo?"**

## A ideia central: o núcleo é quase sempre o mesmo

Olhe os cinco TPs de longe e verá sempre a mesma espinha dorsal:

```
sensor → percepção → representação do mundo → decisão → navegação/atuação → evidência
```

O que muda de um projeto para outro **não é o pipeline** — é o *o quê* de cada caixa: qual sensor, que classe de objeto interessa, que decisão o robô toma, para onde ele vai. Isso tem duas consequências práticas:

A primeira é libertadora: você pode escolher um domínio de aplicação que te interessa de verdade (o setor onde você trabalha, um problema que você viu, um nicho que ninguém da turma vai pegar) sem aumentar o risco técnico, desde que o núcleo continue o mesmo. A segunda é uma advertência: trocar o domínio **não** desconta trabalho. Um "robô de inspeção de subestação elétrica" tem exatamente o mesmo esqueleto de um "robô de inspeção de galpão" — o que muda é a narrativa, o dataset e a régua de sucesso.

> **Como isso é avaliado.** A derivação não vale nota por si só. Ela puxa nota por três caminhos indiretos e poderosos: o relatório fica mais fácil de argumentar (você tem um usuário real em mente), o vídeo fica mais fácil de vender, e a arguição final flui melhor porque você entende *para quê* cada escolha técnica foi feita.

## Derivações por família do catálogo

As tabelas abaixo dizem, para cada derivação, **o que muda** em relação ao projeto-base. Onde não está escrito que muda, não muda.

### 1. Robô de inspeção visual

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Inspeção de subestação / painel elétrico | energia | detectar disjuntor fora de posição, indicador vermelho, mancha térmica simulada por cor | rota fixa entre painéis, poses repetíveis | braço aponta câmera para o painel |
| Inspeção de EPI em canteiro | construção / SST | pessoa **com/sem** capacete e colete (2 classes, dataset fácil de simular) | patrulha por zonas de risco | manipular cone/placa de sinalização |
| Vistoria de vazamentos em planta industrial | óleo & gás | mancha no piso (cor + área) e válvula aberta/fechada | corredores de planta, retorno à base | fechar registro (pick simples) |
| Inspeção de trilhos / esteira | logística / mineração | descontinuidade e objeto estranho sobre a esteira | trajeto linear com paradas | retirar o objeto estranho |
| Inspeção de estufa / lavoura | agro | folha doente vs. sadia (cor), fruto maduro | linhas de plantio (corredores) | colher o fruto detectado |

### 2. Seguidor de alvo

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Carrinho-assistente de compras/ferramentas | varejo / oficina | seguir a pessoa e reconhecer quando ela para | manter distância e desviar de gente | entregar/receber o item |
| Cinegrafista autônomo | mídia / esporte | manter o alvo **enquadrado**, não só detectado | órbita ao redor do alvo | apontar a câmera (pan/tilt no MoveIt) |
| Escolta de visitante | corporativo / hospitalar | identificar crachá/cor de uniforme | ir à frente, não atrás (guiar) | abrir/apontar porta |
| Comboio (robô segue robô) | logística | seguir marcador do robô da frente | formação em fila, parada em cadeia | acoplar o segundo veículo |
| Treinador esportivo | educação física | seguir e medir velocidade/tempo do atleta | acompanhar em pista | entregar cone/marcador |

### 3. Sentinela de segurança

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Ronda noturna com detecção de porta aberta | patrimonial | estado binário de portas/janelas | ronda com horários e pontos de checagem | fechar/empurrar a porta |
| Vigilância de perímetro externo | segurança | intruso vs. animal vs. sombra (falsos positivos!) | perímetro longo, retorno para recarga | acionar sinalizador |
| Detecção de aglomeração / contagem de pessoas | eventos, saúde | contar pessoas por região e disparar limiar | reposicionar para o melhor ponto de vista | ajustar câmera |
| Fiscal de zona proibida | industrial | linha virtual + cruzamento de fronteira | ir até o ponto do evento | posicionar barreira |
| Anti-furto em prateleira | varejo | objeto que **sumiu** (comparação com referência) | corredor da prateleira | repor o item |

### 4. Entregador indoor

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Entrega de medicamentos/amostras | hospitalar | marcador do posto + verificação do destinatário | rotas prioritárias, corredores estreitos | pick-and-place da bandeja |
| Robô garçom | food service | mesa livre/ocupada, chamada de mesa | evitar pessoas, ida-e-volta constante | levar/retirar o prato |
| Reposição de insumos em linha de produção | industrial | caixa cheia/vazia no posto | rota de milk-run entre postos | trocar a caixa |
| Correio interno de escritório | corporativo | número/QR da sala | mapa de andar, elevador simulado | depositar o envelope |
| Recolhimento de resíduos | facility | tipo de resíduo por cor (reciclagem!) | percurso por coletores | pegar e separar |

### 5. Inventário de prateleiras

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Contagem de SKU por gôndola | varejo | classificar 3–5 categorias e contar | corredores completos, cobertura garantida | pegar item para conferência |
| Ruptura de gargalo (falta de produto) | varejo | **espaço vazio** na prateleira (é mais fácil que classificar!) | mesma rota | repor |
| Conferência de pallets em CD | logística | etiqueta/cor por lote, altura da pilha | corredores largos com pilares | mover caixa |
| Inventário de ferramentas | manutenção | quadro-sombra: ferramenta presente/ausente | poucos pontos, alta precisão | devolver a ferramenta |
| Livros fora de ordem | biblioteca | sequência de lombadas (cor/altura) | estantes | reposicionar o livro |

### 6. Assistente de estacionamento / condução

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Detecção de vaga livre | mobilidade urbana | vaga ocupada/livre por visão | manobra de entrada na vaga | — (foco em BC/PID/PPO) |
| Assistente de faixa + alerta de saída | automotivo | faixa contínua/tracejada, desvio lateral | manter centro da faixa | — |
| Leitura de sinalização | automotivo | placas circulares (Hough) e semáforo por cor | reação: parar/seguir | — |
| Robô de pátio / rebocador de carga | aeroportuário, industrial | linha pintada no chão + obstáculo | seguir linha e desviar | engatar carga |
| Condução defensiva em cruzamento | pesquisa | prever conflito com outro veículo | política aprendida (PPO) | — |

> As derivações da família 6 são as únicas que podem **dispensar o braço no TP5** trocando a Opção A/B por foco no comparativo PID × BC × PPO. Combine isso com o professor **antes do TP4**.

### 7. Drone de inspeção

| Derivação | Domínio | O que muda na percepção | O que muda na navegação | Âncora do TP5 |
|---|---|---|---|---|
| Inspeção de telhado / placas solares | energia | placa suja/quebrada por textura e cor | grid aéreo de cobertura | pouso preciso em marcador |
| Contagem em pátio (carros, gado, pallets) | logística, agro | contagem em imagem aérea (área × densidade) | varredura em faixas | — |
| Busca e localização | resposta a emergência | alvo em ambiente amplo, baixo contraste | busca em espiral | soltar marcador |
| Mapeamento de fachada | construção | fissura/anomalia vertical | voo paralelo à parede | — |
| Escolta aérea de robô terrestre | híbrido | ver o robô terrestre de cima | dois grafos ROS 2 conversando | coordenação |

## Trocar o cenário sem trocar o pipeline

Se você já tem o núcleo e só quer um contexto que ninguém vai repetir na turma, use esta troca direta. Em todos os casos o TP1 continua sendo *câmera → segmentação por cor → contagem → serviço*; muda o significado do que é contado.

| Setor | O que "objeto detectado" passa a significar | Por que funciona bem no PB |
|---|---|---|
| Agronegócio | fruto maduro, planta invasora, falha de plantio | cores fortes, corredores naturais para navegar |
| Saúde / hospitalar | leito ocupado, insumo, higienização pendente | narrativa forte, exige cuidado ético no vídeo |
| Varejo | ruptura, preço trocado, fila | fácil de simular com caixas coloridas |
| Energia | conexão aquecida, disjuntor, vegetação sob linha | ótimo para inspeção de rota fixa |
| Saneamento | obstrução, vazamento, nível | permite câmera fixa + robô simples |
| Construção civil | EPI, entulho, sinalização | dataset de 2 classes, simulável com bonecos |
| Mineração | rocha fora de padrão, correia desalinhada | ambiente hostil justifica robô |
| Portuário / aeroportuário | contêiner, marcação de solo, FOD (objeto na pista) | grandes áreas, boa desculpa para drone |
| Educação | robô-tutor que reconhece peça/cor | ótimo para vídeo, cuidado com escopo raso |
| Doméstico / acessibilidade | objeto derrubado, obstáculo no caminho, pessoa caída | apelo social; cuidado com promessas médicas |

## Como escolher a derivação certa (em 4 perguntas)

Comece pelo **dataset**: você consegue produzir, hoje, no seu computador, 30 imagens da classe que quer detectar? Se a resposta for não, a derivação está errada — objetos coloridos, formas simples e cenários montados na sua mesa são aliados legítimos, e simulação no Gazebo conta.

Depois pergunte pela **demonstrabilidade**: o vídeo de 5 minutos do TP mostra a coisa acontecendo? Se o efeito só existe numa planilha, o projeto perde metade do impacto.

Em seguida, pela **escala do mundo**: existe um ambiente com pelo menos dois cômodos/corredores para o SLAM do TP3 e o Nav2 do TP4 fazerem sentido? Um robô que gira no lugar não sobrevive ao TP4.

Por fim, pela **honestidade do escopo**: você consegue descrever a versão mínima do projeto em uma frase que ainda seja útil? "Detecta pessoa sem capacete e registra o horário" é uma frase honesta. "Sistema completo de gestão de segurança do trabalho com IA" não é.

## Derivações que costumam dar errado

Há quatro armadilhas recorrentes. A primeira é o **projeto sem navegação**: braço fixo, esteira, câmera de teto. É tecnicamente respeitável e morre no TP3/TP4, quando SLAM e Nav2 não têm onde acontecer. A segunda é o **projeto sem percepção própria**: usar só odometria ou só LiDAR e deixar a câmera decorativa — o PB inteiro é ancorado em visão. A terceira é o **domínio que exige dado que você não tem**: imagens médicas reais, câmeras térmicas, dados de cliente. A quarta, mais sutil, é a **derivação que só troca o nome**: chamar "robô de inspeção" de "robô de inspeção 4.0" não é derivar; derivar é mudar quem é o usuário, o que ele ganha, e como você mede isso.

## O que registrar no `PROJETO.md`

Sua derivação precisa aparecer explicitamente, com três frases: (a) **domínio e usuário** — quem usa e para resolver o quê; (b) **o que o sistema percebe** — a lista fechada de classes/eventos; (c) **o que o sistema faz com isso** — a decisão e o movimento que se seguem. Depois disso, a tabela do plano TP a TP. Mudar de derivação depois é permitido e até saudável — basta registrar em `docs/decisoes.md` com data e motivo, do jeito que engenheiro de verdade faz.

Veja também: [simulação × hardware real](simulado-vs-hardware.md) e [gates de cada TP](gates-tps.md).
