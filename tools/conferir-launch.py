#!/usr/bin/env python3
"""Confere launch files contra a armadilha de escopo do IncludeLaunchDescription.

POR QUE ESTE CONFERIDOR EXISTE

    `launch_arguments` de um IncludeLaunchDescription NAO sao escopadas. O
    include devolve um SetLaunchConfiguration por argumento, no escopo de QUEM
    INCLUI -- esta no fim do `execute()` de
    launch/launch/actions/include_launch_description.py, no Humble:

        set_launch_configuration_actions = []
        for name, value in self.launch_arguments:
            set_launch_configuration_actions.append(SetLaunchConfiguration(name, value))
        return [*set_launch_configuration_actions, launch_description]

    E o `SetLaunchConfiguration.execute` grava sem olhar o que ja estava la:

        context.launch_configurations[perform_substitutions(context, self.name)] = \
            perform_substitutions(context, self.value)

    Consequencia: um launch que declara `rviz` e passa `'rviz': 'false'` a um
    include APAGA o `rviz:=true` que o usuario digitou -- e o no condicionado a
    `rviz`, avaliado depois, nao sobe. Sem erro e sem aviso.

    Isso aconteceu de verdade, duas vezes: o RViz2 do `aula12_slam` (cujo
    default era 'true', ou seja, nunca subiu) e o do `aula15_nav2`.

A REGRA

    Para cada arquivo *.launch.py, e para cada par k: v de um launch_arguments:
    se `k` tambem e declarado por DeclareLaunchArgument NO MESMO ARQUIVO e `v`
    e uma CONSTANTE, o include tem de estar dentro de um GroupAction.

    Passar `k: LaunchConfiguration(k)` (repasse) nao e flagrado: o valor que
    vaza de volta e o mesmo que ja estava la. O perigoso e a constante.

    As duas curas valem, e as duas foram exercitadas com a biblioteca `launch`
    do branch humble, cada uma sozinha:
      1. GroupAction em volta do include (scoped=True por padrao, embrulha em
         Push/PopLaunchConfigurations);
      2. condicionar o no a um nome que o filho nao conhece, definido antes do
         include com SetLaunchConfiguration.
    Este conferidor cobra a (1), que e a estrutural e da para ver no AST.

Uso: python3 tools/conferir-launch.py [raiz]   (padrao: exemplos/)
"""
import ast
import os
import sys


def nome_chamada(no):
    """O nome da funcao chamada, seja `Foo(...)` ou `mod.Foo(...)`."""
    f = no.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ''


def declarados(arvore):
    """Nomes passados a DeclareLaunchArgument como primeiro argumento literal."""
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and nome_chamada(no) == 'DeclareLaunchArgument':
            if no.args and isinstance(no.args[0], ast.Constant):
                nomes.add(no.args[0].value)
            for kw in no.keywords:
                if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                    nomes.add(kw.value.value)
    return nomes


def dentro_de_group(arvore, alvo):
    """True se o Call `alvo` esta em algum lugar dentro de um GroupAction."""
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and nome_chamada(no) == 'GroupAction':
            for filho in ast.walk(no):
                if filho is alvo:
                    return True
    return False


def argumentos_do_include(no):
    """Pares (chave, valor_ast) do launch_arguments de um IncludeLaunchDescription.

    Aceita a forma usual `launch_arguments={...}.items()` e tambem o dict cru.
    """
    for kw in no.keywords:
        if kw.arg != 'launch_arguments':
            continue
        v = kw.value
        if isinstance(v, ast.Call) and nome_chamada(v) == 'items':
            v = v.func.value
        if isinstance(v, ast.Dict):
            for chave, valor in zip(v.keys, v.values):
                if isinstance(chave, ast.Constant):
                    yield chave.value, valor
    return


def conferir(caminho):
    with open(caminho, encoding='utf-8') as f:
        fonte = f.read()
    arvore = ast.parse(fonte, filename=caminho)
    decl = declarados(arvore)
    achados = []
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.Call)
                and nome_chamada(no) == 'IncludeLaunchDescription'):
            continue
        protegido = dentro_de_group(arvore, no)
        for chave, valor in argumentos_do_include(no):
            if chave in decl and isinstance(valor, ast.Constant) and not protegido:
                achados.append((no.lineno, chave, valor.value))
    return achados


def main():
    raiz = sys.argv[1] if len(sys.argv) > 1 else 'exemplos'
    arquivos = []
    for pasta, _, nomes in os.walk(raiz):
        for n in nomes:
            if n.endswith('.launch.py'):
                arquivos.append(os.path.join(pasta, n))
    arquivos.sort()

    problemas = 0
    for caminho in arquivos:
        for linha, chave, valor in conferir(caminho):
            problemas += 1
            print('%s:%d: o include fixa `%s` em %r, e este arquivo DECLARA '
                  '`%s` como argumento.' % (caminho, linha, chave, valor, chave))
            print('    launch_arguments nao sao escopadas: esse valor apaga o '
                  '%s:= da linha de comando, calado.' % chave)
            print('    cura: ponha o IncludeLaunchDescription dentro de um '
                  'GroupAction([...]) -- scoped=True e o padrao.')
    if problemas:
        print('\nlaunch: %d colisao(oes) de argumento em %d arquivo(s) conferido(s)'
              % (problemas, len(arquivos)))
        return 1
    print('launch ok: %d arquivo(s) conferido(s), nenhum argumento sobrescrito '
          'por include' % len(arquivos))
    return 0


if __name__ == '__main__':
    sys.exit(main())
