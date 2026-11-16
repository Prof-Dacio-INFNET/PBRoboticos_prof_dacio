"""A sequencia de alvos e as tabelas que ela imprime. Sem ROS 2.

ADVERTENCIA: a logica foi conferida pelo testar.py com movimentos falsos
(sucesso, falha de planejamento, goal recusado, sem resposta). Rodou com um
move_group de verdade no ensaio de 16/11 (tres_poses e comparar); o
lado a lado com a pose D falhando so com a caixa ainda nao foi visto.

Este modulo nao sabe o que e MoveIt: ele recebe uma lista de alvos e uma
funcao `mover(alvo)` que devolve um `Resultado`. Quem fala com o move_group e
o `cliente.py`. Separado assim, a ordem, a contagem e as tabelas do
`tres_poses` rodam no testar.py sem nenhum duble -- e o que vai para a tela
da aula e exatamente o que foi testado.
"""
from aula18_moveit import codigos


class Resultado:
    """O que se sabe de UM alvo depois de pedir ao move_group.

    Os campos sao separados de proposito, porque cada um conta uma coisa:

      recusado      o servidor nem aceitou o goal (nao planejou)
      sem_resposta  aceitou e nao respondeu dentro do prazo deste no
      codigo        o MoveItErrorCodes.val do PLANEJAMENTO
      tempo_moveit  o planning_time que o move_group informa -- so vem no
                    modo de planejar (plan_only); no modo direto ele vem 0,
                    e quem conta e o relogio
      tempo_relogio o tempo, medido aqui, entre enviar e receber a resposta
      pontos        pontos da trajetoria planejada
      comprimento   soma dos deslocamentos das juntas, em rad
      execucao      None = nao pediu para executar; senao, o codigo da execucao
    """

    def __init__(self, nome, recusado=False, sem_resposta=False, codigo=None,
                 tempo_moveit=0.0, tempo_relogio=0.0, pontos=0, comprimento=0.0,
                 execucao=None, trajetoria=None):
        self.nome = nome
        self.recusado = recusado
        self.sem_resposta = sem_resposta
        self.codigo = codigo
        self.tempo_moveit = tempo_moveit
        self.tempo_relogio = tempo_relogio
        self.pontos = pontos
        self.comprimento = comprimento
        self.execucao = execucao
        self.trajetoria = trajetoria

    @property
    def planejou(self):
        return (not self.recusado and not self.sem_resposta
                and self.codigo == codigos.SUCESSO)

    @property
    def executou(self):
        return self.planejou and self.execucao == codigos.SUCESSO

    def situacao(self):
        """Uma palavra para a tabela: o que o move_group respondeu."""
        if self.recusado:
            return 'goal RECUSADO'
        if self.sem_resposta:
            return 'SEM RESPOSTA'
        return codigos.descrever(self.codigo)


def percorrer(alvos, mover, log=print):
    """Pede cada alvo, em ordem, e NAO para no primeiro tropeco.

    Um alvo que falha nao mexe o robo, e o proximo parte de onde o robo
    esta. Parar no primeiro erro esconderia justamente o que a aula quer
    mostrar: com a caixa, uma das poses falha e as outras continuam.
    """
    resultados = []
    for i, alvo in enumerate(alvos, start=1):
        log('[%d/%d] %s: %s' % (i, len(alvos), alvo['nome'], alvo.get('descricao', '')))
        r = mover(alvo)
        resultados.append(r)
        log('      -> %s' % linha(r))
        if not r.planejou:
            log('      olhe: %s' % dica(r))
        elif r.execucao not in (None, codigos.SUCESSO):
            log('      olhe (execucao): %s' % codigos.dica(r.execucao))
    return resultados


def dica(r):
    """Onde olhar quando o PLANEJAMENTO nao deu SUCCESS (recusa, prazo ou codigo)."""
    if r.recusado:
        return ('o move_group recusou antes de planejar -- o motivo esta no Terminal A '
                '(grupo ou link com nome errado e o mais comum)')
    if r.sem_resposta:
        return ('o move_group aceitou e nao respondeu no prazo. Olhe o Terminal A; se ele '
                'diz que terminou e aqui nada chegou, veja "Socorro rapido" no README (DDS)')
    return codigos.dica(r.codigo)


def linha(r):
    """Uma linha por alvo: o que o MoveIt disse, e os numeros."""
    s = r.situacao()
    if r.planejou:
        s += ('  planejamento %.3f s (MoveIt) / %.2f s (relogio)  %d pontos  %.2f rad'
              % (r.tempo_moveit, r.tempo_relogio, r.pontos, r.comprimento))
        if r.pontos == 0:
            s += '  (trajetoria vazia: o robo ja estava no alvo)'
        if r.execucao is not None:
            s += '  execucao: %s' % codigos.descrever(r.execucao)
    elif not r.recusado:
        s += '  depois de %.2f s' % r.tempo_relogio
    return s


def tabela(resultados, titulo=''):
    """A tabela que vai para o print do relatorio."""
    linhas = []
    if titulo:
        linhas.append(titulo)
    linhas.append('%-10s %-30s %9s %9s %7s %9s  %s' % (
        'alvo', 'planejamento', 't MoveIt', 't relog', 'pontos', 'juntas', 'execucao'))
    for r in resultados:
        exe = '-' if r.execucao is None else codigos.nome(r.execucao)
        if r.planejou:
            linhas.append('%-10s %-30s %8.3fs %8.2fs %7d %8.2fr  %s' % (
                r.nome, r.situacao(), r.tempo_moveit, r.tempo_relogio, r.pontos,
                r.comprimento, exe))
        else:
            linhas.append('%-10s %-30s %9s %8.2fs %7s %9s  %s' % (
                r.nome, r.situacao(), '-', r.tempo_relogio, '-', '-', '-'))
    return linhas


def comparar(sem, com):
    """As MESMAS poses, sem e com a caixa, lado a lado."""
    linhas = ['%-10s | %-30s %8s | %-30s %8s' % (
        'alvo', 'SEM a caixa', 'juntas', 'COM a caixa', 'juntas')]
    por_nome = {r.nome: r for r in com}
    for a in sem:
        b = por_nome.get(a.nome)
        ja = '%.2fr' % a.comprimento if a.planejou else '-'
        if b is None:
            linhas.append('%-10s | %-30s %8s | %-30s %8s' % (a.nome, a.situacao(), ja,
                                                             '(nao pedido)', ''))
            continue
        jb = '%.2fr' % b.comprimento if b.planejou else '-'
        linhas.append('%-10s | %-30s %8s | %-30s %8s' % (a.nome, a.situacao(), ja,
                                                         b.situacao(), jb))
    return linhas


def resumo(resultados):
    """O fecho: o que foi contado, e o que essa contagem NAO quer dizer."""
    n = len(resultados)
    planejou = sum(1 for r in resultados if r.planejou)
    executou = sum(1 for r in resultados if r.executou)
    pediu_exec = sum(1 for r in resultados if r.execucao is not None)
    linhas = ['contei: %d de %d alvos com SUCCESS no planejamento' % (planejou, n)]
    if pediu_exec:
        linhas.append('       %d de %d com SUCCESS na execucao' % (executou, pediu_exec))
    linhas.append('isto e o que o move_group RESPONDEU, nao uma conferencia do TP5:')
    linhas.append('  a evidencia do G5.1 e o print ou o video do RViz2 com as poses e a')
    linhas.append('  caixa, e a explicacao do que mudou no relatorio. Este no nao ve o RViz2.')
    return linhas
