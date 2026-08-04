# Renomear um pacote ROS 2 (`ament_python`) sem quebrar nada

Copiar um exemplo da aula e renomear para o seu domínio é o fluxo padrão desta disciplina — é assim que `aula03_visao` vira `percepcao_pomar`. A operação parece trivial e tem uma armadilha específica: o nome do pacote está escrito em **mais lugares do que parece**, e cada lugar esquecido produz um erro diferente, em um momento diferente, com uma mensagem que não menciona a renomeação.

Esta página é a referência única para essa operação. Vale para qualquer pacote `ament_python` — os da aula, os do seu TP, e os que você vai clonar depois.

## Antes de tudo: onde a modificação acontece

Um workspace ROS 2 tem quatro pastas, e só **uma** delas você edita:

| Pasta | O que é | Você edita? |
|---|---|---|
| `src/` | **código-fonte.** Seus pacotes moram aqui: `package.xml`, `setup.py`, `setup.cfg`, `resource/`, os `.py`, `launch/`, `config/` | **Sim — é o único lugar.** |
| `build/` | área de trabalho intermediária do colcon | Não. É apagável e regenerável. |
| `install/` | o resultado instalado — **é daqui que o `ros2 run` e o `ros2 launch` leem** | Não. Sobrescrito a cada build. |
| `log/` | logs de build e de execução | Não, mas leia quando algo falhar. |

Daí sai a regra que resolve a maior parte das confusões: **se você editou um arquivo e o comportamento não mudou, ou você editou a cópia errada, ou faltou recompilar.** Editar `install/percepcao_pomar/...` "funciona" até o próximo `colcon build` jogar a alteração fora.

!!! tip "`--symlink-install` e os arquivos que não são código"
    Com `colcon build --symlink-install`, os `.py` em `install/` viram links para os de `src/` — você edita e roda sem recompilar. **Mas `config/*.yaml` e os arquivos de `launch/` costumam ser copiados**, não linkados, dependendo de como o `setup.py` os declara. Se você mudou um YAML de parâmetros e o nó continua com os valores antigos, recompile antes de suspeitar do código.

## Os quatro lugares — mais o `setup.cfg`

!!! warning "A regra completa"
    Em pacotes `ament_python`, ao renomear pacote, alinhar `<name>` em `package.xml`, `package_name` em `setup.py`, arquivo `resource/<package_name>` e `setup.cfg` (`script_dir`/`install_scripts` em `$base/lib/<package_name>`).

    - Se `setup.cfg` ficar com nome antigo, `ros2 launch` falha com: `libexec directory .../lib/<package_name> does not exist`.

Somando a pasta do pacote e a pasta do módulo Python, a lista completa fica assim — e o valor da coluna da direita é o que faz cada esquecimento render um erro **diferente**:

| Onde | O que trocar | Sintoma se você esquecer |
|---|---|---|
| `src/<pacote>/` | o nome da pasta do pacote | nenhum imediato; o colcon usa o `package.xml`, mas a bagunça te confunde depois |
| `src/<pacote>/package.xml` | `<name>` | `Package not found` teimoso, sobrevive a recompilações |
| `src/<pacote>/setup.py` | `package_name` **e** os `entry_points` | executável some: `No executable found` |
| `src/<pacote>/<modulo>/` | a pasta do módulo Python (a que tem `__init__.py`) | `ModuleNotFoundError` no import relativo |
| `src/<pacote>/resource/<nome>` | o nome do arquivo-marcador (o conteúdo é vazio mesmo) | o pacote compila e **não é indexado** pelo ament: `Package not found` |
| `src/<pacote>/setup.cfg` | `script_dir` e `install_scripts` (`$base/lib/<nome>`) | **`libexec directory '.../lib/<pacote>' does not exist`** no `ros2 launch` |

O `setup.cfg` é o que mais escapa, porque ele não tem nada a ver com o resto: `package.xml` e `setup.py` são "quem eu sou", e o `setup.cfg` é "onde meus executáveis vão ser instalados". Se ele aponta para `lib/nome_antigo`, o `colcon` instala os executáveis lá, o `ros2 launch` procura em `lib/nome_novo`, não acha, e reclama de um diretório `libexec` que ninguém sabia que existia.

Além dos arquivos, confira também as referências **dentro** do código e dos launch files: `Node(package='...')` no `.launch.py`, o caminho em `get_package_share_directory('...')`, e o campo `packages=` do `setup.py`.

## Sequência de comandos recomendada

Depois de trocar os nomes, compile do jeito previsível. O passo do `rm -rf` é opcional: use quando houver sujeira de build anterior — que é exatamente o caso depois de uma renomeação, porque os artefatos com o nome velho continuam em `build/` e `install/`.

```bash
cd ~/SEU-REPO/ros2_ws

# opcional, quando houver muita sujeira de build anterior
rm -rf build/<nome_do_pacote> install/<nome_do_pacote> log/latest_build

colcon build --packages-select <nome_do_pacote> --symlink-install
source install/setup.bash
ros2 launch <nome_do_pacote> <arquivo>.launch.py
```

`--packages-select` compila só o pacote em que você mexeu, o que transforma um build de minutos em um de segundos. `source install/setup.bash` é por terminal: terminal novo, source novo.

Se o erro insistir mesmo depois disso, aí sim limpe o workspace inteiro com `rm -rf build install log` e compile tudo. É lento, mas fecha a questão sobre resíduo de build.

## Pontos de atenção para não repetir

Ao clonar/renomear pacote Python ROS 2, mantenha os nomes alinhados em:

- `package.xml` (`name`)
- `setup.py` (`package_name` e `entry_points`)
- a pasta do módulo Python e o `resource/<nome_do_pacote>`
- `setup.cfg` (`lib/<nome_do_pacote>`)

Se aparecer erro ao sair com `Ctrl+C` (`rcl_shutdown already called`), normalmente é ruído de encerramento e não quebra a execução principal. Os nós dos exemplos desta disciplina já fecham com `if rclpy.ok(): rclpy.shutdown()` justamente para não imprimir esse ruído — se você escreveu o seu do zero e ele aparece, é essa a causa, e a cura é a mesma linha.

## Um teste de 10 segundos que evita a viagem toda

Depois de compilar, antes de rodar o launch:

```bash
ros2 pkg list | grep <nome_do_pacote>            # o ament enxerga o pacote?
ros2 pkg executables <nome_do_pacote>            # os entry_points chegaram?
ls install/<nome_do_pacote>/lib/<nome_do_pacote> # o setup.cfg apontou para o lugar certo?
```

As três linhas cobrem, nessa ordem, o `resource/` + `package.xml`, o `setup.py`, e o `setup.cfg`. Se as três respondem, o `ros2 launch` vai funcionar.

## Escolha bem o nome, de uma vez

Renomear é barato; renomear duas vezes não é. Escolha um nome que descreva o **seu domínio**, não a aula: `percepcao_estoque`, `visao_pomar`, `deteccao_epi`. O nome do pacote é a primeira coisa que o avaliador lê, e vai aparecer em todos os comandos do seu vídeo de entrega.

Veja também: [Workspace e colcon](workspace-colcon.md) e o [cheatsheet do colcon](../cheatsheets/colcon.md).
