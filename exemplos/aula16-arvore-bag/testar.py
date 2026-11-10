#!/usr/bin/env python3
"""Confere a regua e a sessao antes de voce citar qualquer numero. Sem ROS 2.

    python3 testar.py

Dez grupos, todos com a resposta sabida de antemao. O que eles provam e o
que eles NAO provam esta separado no README, na secao "O que foi e o que nao
foi verificado" -- e a separacao e o ponto. Aqui nao ha ROS 2: o grupo 8
confere o que da para conferir sem ele (sintaxe, XML bem formado, nomes de
no de arvore contra a fonte do Humble), o grupo 9 mede sessoes gravadas
"como o vigia real grava" (o defeito do ensaio de 09/11/2026) e o grupo 10
roda a maquina de estados do `vigia.py` com DUBLES do rclpy -- o que prova a
logica do no, nao que ele conversa com o Nav2.

O grupo 5 e o coracao: ele PROVA, com a verdade que o simulador guarda e nao
grava, que o erro da odometria cresce e o do AMCL nao. E a frase que o
grafico do item 2 esta la para mostrar, e e a unica coisa deste exemplo que
o CSV sozinho nao permite verificar.
"""
import ast
import filecmp
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import types
import xml.etree.ElementTree as ET

import medir_sessao
import plotar_trajetoria
import simular_sessao

AQUI = pathlib.Path(__file__).resolve().parent
PACOTE = AQUI / 'aula16_arvore'

falhas = []


def conferir(nome, ok, detalhe=''):
    print('  %s  %s%s' % ('ok  ' if ok else 'FALHA', nome,
                          '  -- ' + detalhe if detalhe else ''))
    if not ok:
        falhas.append(nome)


def erro_odom(r):
    return math.hypot(r['odom_x'] - r['x_verdade'], r['odom_y'] - r['y_verdade'])


def erro_amcl(r):
    return math.hypot(r['amcl_x'] - r['x_verdade'], r['amcl_y'] - r['y_verdade'])


t_inicio = time.perf_counter()
tmp = pathlib.Path(tempfile.mkdtemp(prefix='aula16-'))

# ---------------------------------------------------------------------- 1
print('1. determinismo: a mesma semente da o mesmo arquivo, byte a byte')
a = tmp / 'a.csv'
b = tmp / 'b.csv'
c = tmp / 'c.csv'
reg1, res1 = simular_sessao.simular()
reg2, _ = simular_sessao.simular()
reg3, _ = simular_sessao.simular(semente=7)
simular_sessao.gravar_csv(a, reg1)
simular_sessao.gravar_csv(b, reg2)
simular_sessao.gravar_csv(c, reg3)
conferir('duas corridas com a semente %d dao arquivos identicos'
         % simular_sessao.SEMENTE, filecmp.cmp(a, b, shallow=False),
         '%d bytes' % a.stat().st_size)
conferir('com outra semente, o arquivo muda',
         not filecmp.cmp(a, c, shallow=False),
         'semente 7 x semente %d' % simular_sessao.SEMENTE)
conferir('o numero de linhas nao depende da semente',
         len(reg1) == len(reg3), '%d linhas nos dois' % len(reg1))

# ---------------------------------------------------------------------- 2
print('2. o contrato do CSV: as 11 colunas, e a VERDADE fora do arquivo')
texto = a.read_text(encoding='utf-8')
cabecalho = texto.splitlines()[0].split(',')
conferir('o cabecalho e exatamente o contrato, nesta ordem',
         tuple(cabecalho) == simular_sessao.CAMPOS_CSV,
         ', '.join(cabecalho))
conferir('o `medir_sessao` exige o mesmo contrato',
         medir_sessao.COLUNAS == simular_sessao.CAMPOS_CSV)
conferir('nenhuma coluna de verdade vazou para o arquivo',
         not any(k in texto for k in ('x_verdade', 'y_verdade', 'th_verdade')),
         'o bag do robo nao tem verdade; o CSV dele tambem nao')
conferir('mas a verdade EXISTE dentro do simulador, para os testes',
         all(k in reg1[0] for k in ('x_verdade', 'y_verdade', 'th_verdade')))
estados = {r['estado'] for r in reg1}
conferir('so aparecem os quatro estados declarados',
         estados <= set(simular_sessao.ESTADOS),
         ', '.join(sorted(estados)))

# ---------------------------------------------------------------------- 3
print('3. os dois eventos de obstaculo aparecem, e sao obstaculo mesmo')
linhas = medir_sessao.ler_csv(a)
m = medir_sessao.medir(linhas)
conferir('a regua acha %d evento(s)' % medir_sessao.EVENTOS_ESPERADOS,
         len(m['eventos']) == medir_sessao.EVENTOS_ESPERADOS,
         't = %s' % '; '.join('%.1f s' % e['t'] for e in m['eventos']))
conferir('nos DOIS, o /scan furou o limiar do enunciado',
         all(e['scan'] < medir_sessao.LIMIAR_OBSTACULO_M for e in m['eventos']),
         '%s (limiar %.2f m)' % ('; '.join('%.3f m' % e['scan']
                                           for e in m['eventos']),
                                 medir_sessao.LIMIAR_OBSTACULO_M))
ordem = []
anterior = None
for r in linhas:
    if r['estado'] != anterior:
        ordem.append(r['estado'])
        anterior = r['estado']
esperada = ['navegando', 'interrompido', 'esperando', 'retomando'] * 2
conferir('a ordem dos estados e a do enunciado, duas vezes',
         ordem == esperada + ['navegando'], ' -> '.join(ordem))
conferir('o percurso nunca chega perto de parede: quem disparou foi a pessoa',
         res1['folga_minima'] > 1.0,
         'folga minima de %.2f m contra um limiar de %.2f m'
         % (res1['folga_minima'], medir_sessao.LIMIAR_OBSTACULO_M))
limpa, _ = simular_sessao.simular(com_eventos=False)
d = tmp / 'limpa.csv'
simular_sessao.gravar_csv(d, limpa)
m_limpa = medir_sessao.medir(medir_sessao.ler_csv(d))
conferir('sem obstaculo nenhum, a regua acha ZERO evento',
         len(m_limpa['eventos']) == 0
         and any('NAO ha evento' in s for s in medir_sessao.veredito(m_limpa)),
         'e o veredito diz isso em portugues')

# ---------------------------------------------------------------------- 4
print('4. a espera dura mesmo 2 s, dentro da tolerancia declarada')
conferir('as duas esperas passam no criterio de %.2f s +- %.2f s'
         % (medir_sessao.ESPERA_ALVO_S, medir_sessao.TOL_ESPERA_S),
         not m['fora_da_espera'],
         'medidas: %s' % '; '.join('%.2f s' % e['espera_s']
                                   for e in m['eventos']))
conferir('e as duas NAO sao iguais: a segunda carrega o atraso de tick',
         abs(m['eventos'][0]['espera_s'] - m['eventos'][1]['espera_s']) > 1e-9,
         '%.2f s e %.2f s -- a regua nao passou por sorte de numero redondo'
         % (m['eventos'][0]['espera_s'], m['eventos'][1]['espera_s']))
curta, _ = simular_sessao.simular(espera_s=1.2, atraso_tick=0.0)
e = tmp / 'curta.csv'
simular_sessao.gravar_csv(e, curta)
m_curta = medir_sessao.medir(medir_sessao.ler_csv(e))
conferir('uma sessao que espera 1,2 s e REPROVADA pela regua',
         len(m_curta['fora_da_espera']) == len(m_curta['eventos']) > 0
         and any('FORA DO ALVO' in s for s in medir_sessao.veredito(m_curta)),
         'espera medida: %.2f s' % m_curta['eventos'][0]['espera_s'])
conferir('parado conta os DOIS comandos: curva nao e parada',
         m['parado_total_s'] < 0.5 + sum(ev['espera_s'] for ev in m['eventos']),
         '%.2f s parado na sessao, contra %.1f s so de giro'
         % (m['parado_total_s'],
            sum(abs(d) for _, w, d in simular_sessao.PERCURSO if w)))

# ---------------------------------------------------------------------- 5
print('5. o erro da odometria CRESCE e o do AMCL NAO (so da para ver aqui)')
quarto = reg1[len(reg1) // 4]
fim = reg1[-1]
conferir('o erro da odometria no fim e muito maior que no primeiro quarto',
         erro_odom(fim) > 3.0 * erro_odom(quarto),
         '%.3f m no fim contra %.3f m em t = %.1f s'
         % (erro_odom(fim), erro_odom(quarto), quarto['t']))
pior_amcl = max(erro_amcl(r) for r in reg1)
conferir('o erro do AMCL nao cresce: o pior da sessao e pequeno',
         pior_amcl < 0.15,
         'pior %.3f m, final %.3f m -- nao acumula, porque reamarra ao mapa'
         % (pior_amcl, erro_amcl(fim)))
conferir('e e por isso que o vao odom x amcl do CSV vale como medida',
         abs(m['vao_final'] - erro_odom(fim)) < 0.12,
         'vao de %.2f m no CSV contra %.2f m de erro real da odometria'
         % (m['vao_final'], erro_odom(fim)))
conferir('somar passos de serie ruidosa infla a distancia -- e a regua avisa',
         m['dist_amcl'] > 1.4 * m['dist_cmd'],
         '%.1f m pelo /amcl_pose contra %.1f m de |cmd_v| dt integrado'
         % (m['dist_amcl'], m['dist_cmd']))

# ---------------------------------------------------------------------- 6
print('6. a figura e gerada, e nao esta em branco')
png = tmp / 'fig.png'
plotar_trajetoria.desenhar(plotar_trajetoria.ler_csv(str(a)), str(png))
conferir('o arquivo existe e tem tamanho de figura',
         png.is_file() and png.stat().st_size > 20000,
         '%d bytes' % png.stat().st_size)
imagem = plotar_trajetoria.plt.imread(str(png))
claros = (imagem[:, :, :3] > 0.97).all(axis=2)
tinta = 1.0 - claros.mean()
conferir('tem tinta de verdade na folha, e nao so moldura',
         0.02 < tinta < 0.9,
         '%.1f%% dos pixels nao sao brancos, em %dx%d'
         % (100 * tinta, imagem.shape[1], imagem.shape[0]))
conferir('o plotador acha as mesmas interrupcoes que a regua',
         len(plotar_trajetoria.interrupcoes(
             plotar_trajetoria.ler_csv(str(a)))) == len(m['eventos']),
         '%d marcas na figura' % len(m['eventos']))
png2 = tmp / 'fig-so-traj.png'
plotar_trajetoria.desenhar(plotar_trajetoria.ler_csv(str(a)), str(png2),
                           so_trajetoria=True)
conferir('a variante --so-trajetoria tambem sai, e sai menor',
         png2.is_file() and png2.stat().st_size < png.stat().st_size,
         '%d bytes contra %d' % (png2.stat().st_size, png.stat().st_size))

# ---------------------------------------------------------------------- 7
print('7. a regua em si: ela acusa o que tem de acusar')
falso = [dict(r) for r in linhas]
for r in falso:                       # mesma sessao, dois eventos no MESMO lugar
    r['amcl_x'], r['amcl_y'] = 3.0, 3.0
m_falso = medir_sessao.medir(falso)
conferir('dois disparos no mesmo lugar sao acusados como reincidencia',
         bool(m_falso['reincidentes'])
         and any('REINCIDENCIA' in s for s in medir_sessao.veredito(m_falso)),
         'obstaculo que nao anda nao se resolve esperando')
conferir('e na sessao de verdade, que sao lugares diferentes, nao acusa',
         not m['reincidentes'],
         '%.1f m entre os dois disparos'
         % math.hypot(m['eventos'][1]['x'] - m['eventos'][0]['x'],
                      m['eventos'][1]['y'] - m['eventos'][0]['y']))
giro = [{'cmd_v': 0.0, 'cmd_w': 0.6, 'estado': 'navegando'}] * 10
conferir('um trecho de giro puro nao conta como parada',
         medir_sessao.blocos_parado(giro) == [],
         'cmd_v zero com cmd_w de 0,6 rad/s e curva, nao parada')
parado = [{'cmd_v': 0.0, 'cmd_w': 0.0, 'estado': 'esperando'}] * 10
conferir('e um trecho com os dois em zero conta',
         len(medir_sessao.blocos_parado(parado)) == 1
         and len(medir_sessao.blocos_parado(parado)[0]) == 10)
conferir('o veredito aprova a sessao de referencia',
         any('sustenta o item 2' in s for s in medir_sessao.veredito(m)),
         [s for s in medir_sessao.veredito(m) if 'sustenta' in s][0][:60])

# ---------------------------------------------------------------------- 8
print('8. a camada ROS 2: SO o que da para conferir sem ROS 2')
fontes = sorted(PACOTE.rglob('*.py')) + [AQUI / 'simular_sessao.py',
                                         AQUI / 'plotar_trajetoria.py',
                                         AQUI / 'medir_sessao.py',
                                         pathlib.Path(__file__)]
erros_ast = []
for f in fontes:
    try:
        ast.parse(f.read_text(encoding='utf-8'), filename=str(f))
    except SyntaxError as exc:
        erros_ast.append('%s: %s' % (f.name, exc))
conferir('ast.parse em todos os .py do exemplo', not erros_ast,
         '%d arquivos; %s' % (len(fontes), '; '.join(erros_ast) or 'nenhum erro'))

longas, nao_ascii = [], []
for f in fontes:
    for n, linha in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
        if len(linha) > 99:
            longas.append('%s:%d (%d col)' % (f.name, n, len(linha)))
        if not linha.isascii():
            nao_ascii.append('%s:%d' % (f.name, n))
conferir('nenhuma linha acima de 99 colunas', not longas,
         '; '.join(longas[:3]) or 'a mais longa cabe')
conferir('nenhum byte nao-ASCII nos .py', not nao_ascii,
         '; '.join(nao_ascii[:3]) or 'tudo ASCII, como manda a disciplina')

ET.parse(PACOTE / 'package.xml')
conferir('package.xml e XML bem formado e declara ament_python',
         ET.parse(PACOTE / 'package.xml').getroot().find(
             './export/build_type').text == 'ament_python')

# A arvore OFICIAL do Humble, copiada de
# nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml
# (branch humble). Esta aqui para o teste poder provar que a copia comentada
# nao mexeu em nada -- se um dia a oficial mudar, e este texto que se atualiza.
OFICIAL = """<root main_tree_to_execute="MainTree">
  <BehaviorTree ID="MainTree">
    <RecoveryNode number_of_retries="6" name="NavigateRecovery">
      <PipelineSequence name="NavigateWithReplanning">
        <RateController hz="1.0">
          <RecoveryNode number_of_retries="1" name="ComputePathToPose">
            <ComputePathToPose goal="{goal}" path="{path}" planner_id="GridBased"/>
            <ClearEntireCostmap name="ClearGlobalCostmap-Context"
              service_name="global_costmap/clear_entirely_global_costmap"/>
          </RecoveryNode>
        </RateController>
        <RecoveryNode number_of_retries="1" name="FollowPath">
          <FollowPath path="{path}" controller_id="FollowPath"/>
          <ClearEntireCostmap name="ClearLocalCostmap-Context"
            service_name="local_costmap/clear_entirely_local_costmap"/>
        </RecoveryNode>
      </PipelineSequence>
      <ReactiveFallback name="RecoveryFallback">
        <GoalUpdated/>
        <RoundRobin name="RecoveryActions">
          <Sequence name="ClearingActions">
            <ClearEntireCostmap name="ClearLocalCostmap-Subtree"
              service_name="local_costmap/clear_entirely_local_costmap"/>
            <ClearEntireCostmap name="ClearGlobalCostmap-Subtree"
              service_name="global_costmap/clear_entirely_global_costmap"/>
          </Sequence>
          <Spin spin_dist="1.57"/>
          <Wait wait_duration="5"/>
          <BackUp backup_dist="0.30" backup_speed="0.05"/>
        </RoundRobin>
      </ReactiveFallback>
    </RecoveryNode>
  </BehaviorTree>
</root>"""


def assinatura(no):
    """(tag, atributos, filhos) -- a arvore que o bt_navigator realmente le.

    Descarta comentario (o ElementTree ja faz isso), espaco e ordem de
    atributo. E' o que precisa bater entre a copia comentada e a oficial.
    """
    return (no.tag, tuple(sorted(no.attrib.items())),
            tuple(assinatura(f) for f in no))


oficial = ET.fromstring(OFICIAL)
padrao = ET.parse(AQUI / 'arvores' / 'padrao_comentada.xml').getroot()
espera = ET.parse(AQUI / 'arvores' / 'com_espera.xml').getroot()
conferir('padrao_comentada.xml e a arvore do Humble, intacta',
         assinatura(padrao) == assinatura(oficial),
         'so mudaram os comentarios')
conferir('com_espera.xml NAO e identica a oficial (seria inutil se fosse)',
         assinatura(espera) != assinatura(oficial))

esperas_padrao = [n.get('wait_duration') for n in padrao.iter('Wait')]
esperas_nova = [n.get('wait_duration') for n in espera.iter('Wait')]
conferir('a variante espera %.0f s onde a oficial espera %s s'
         % (medir_sessao.ESPERA_ALVO_S, esperas_padrao[0]),
         esperas_nova == ['2'] and esperas_padrao == ['5'],
         'e wait_duration e INT no Humble: "2", nunca "2.0"')
rodizio = [f.tag for f in next(espera.iter('RoundRobin'))]
conferir('e a espera e a PRIMEIRA recuperacao do rodizio',
         rodizio[0] == 'Wait', ' -> '.join(rodizio))

# Os nomes de no sao conferidos contra a lista lida na fonte do Humble
# (nav2_behavior_tree/nav2_tree_nodes.xml do branch humble, mais os nos de
# controle genericos da BehaviorTree.CPP v3). Nome inventado aqui = arvore
# que carrega na sua maquina e nao carrega na do avaliador.
NOS_HUMBLE = {
    # nav2_behavior_tree (acoes)
    'ComputePathToPose', 'FollowPath', 'ClearEntireCostmap', 'Spin', 'Wait',
    'BackUp', 'DriveOnHeading', 'AssistedTeleop', 'SmoothPath', 'TruncatePath',
    'ComputePathThroughPoses', 'RemovePassedGoals', 'NavigateToPose',
    'NavigateThroughPoses', 'ReinitializeGlobalLocalization',
    'ClearCostmapExceptRegion', 'ClearCostmapAroundRobot',
    # nav2_behavior_tree (condicoes)
    'GoalReached', 'IsStuck', 'TransformAvailable', 'GoalUpdated',
    'GlobalUpdatedGoal', 'IsBatteryLow', 'IsBatteryCharging',
    'DistanceTraveled', 'TimeExpired', 'PathExpiringTimer',
    'InitialPoseReceived', 'IsPathValid',
    # nav2_behavior_tree (controle e decoradores)
    'PipelineSequence', 'RecoveryNode', 'RoundRobin', 'RateController',
    'DistanceController', 'SingleTrigger', 'GoalUpdater', 'SpeedController',
    'PathLongerOnApproach', 'GoalUpdatedController',
    # BehaviorTree.CPP v3, que e a versao do Humble
    'root', 'BehaviorTree', 'Sequence', 'SequenceStar', 'Fallback',
    'ReactiveSequence', 'ReactiveFallback', 'Parallel', 'Inverter',
    'ForceSuccess', 'ForceFailure', 'Repeat', 'RetryUntilSuccessful',
    'KeepRunningUntilFailure', 'Timeout', 'Delay', 'SubTree',
}
desconhecidos = set()
for arvore in (padrao, espera):
    for no in arvore.iter():
        if no.tag not in NOS_HUMBLE:
            desconhecidos.add(no.tag)
conferir('todo no das duas arvores existe no Humble', not desconhecidos,
         'nenhum nome inventado' if not desconhecidos
         else 'inventados: ' + ', '.join(sorted(desconhecidos)))
conferir('nenhuma condicao de DISTANCIA A OBSTACULO existe no Humble',
         not any('Obstacle' in n or 'Obstaculo' in n for n in NOS_HUMBLE),
         'e por isso que o portao de 0,5 m precisa do vigia.py ou de C++')

# O launch file tem de passar no conferidor de escopo do repositorio -- o
# mesmo tools/conferir-launch.py que roda na raiz. Aqui ele e exercitado
# sobre este pacote sozinho, para a falha aparecer antes.
conferidor = AQUI.parent.parent / 'tools' / 'conferir-launch.py'
if conferidor.is_file():
    r = subprocess.run([sys.executable, str(conferidor), str(PACOTE)],
                       capture_output=True, text=True)
    conferir('tools/conferir-launch.py aprova o analise.launch.py',
             r.returncode == 0, r.stdout.strip().splitlines()[-1]
             if r.stdout.strip() else '')
else:
    print('  (pulado) tools/conferir-launch.py nao esta ao lado')

# ---------------------------------------------------------------------- 9
print('9. a sessao como o vigia REAL grava: so navegando e esperando')
# No ensaio de 09/11/2026 o `interrompido` durou ~2 ms e nao caiu em nenhuma
# linha do CSV; a regua de entao contava evento so por ele e deu ZERO para
# uma sessao com uma interrupcao de verdade. Estes testes sao esse caso.
real, res_real = simular_sessao.simular(como_vigia_real=True)
f_real = tmp / 'real.csv'
simular_sessao.gravar_csv(f_real, real)
lin_real = medir_sessao.ler_csv(f_real)
m_real = medir_sessao.medir(lin_real)
conferir('o CSV nao tem nenhuma linha `interrompido` nem `retomando`',
         set(m_real['estados']) == {'navegando', 'esperando'},
         ', '.join(m_real['estados']))
conferir('e a regua conta os eventos mesmo assim',
         len(m_real['eventos']) == res_real['eventos'] == 2,
         '%d evento(s), o simulador disparou %d'
         % (len(m_real['eventos']), res_real['eventos']))
conferir('a espera medida cai na tolerancia, e o parado e MENOR que ela',
         not m_real['fora_da_espera']
         and all(e['parado_s'] < e['espera_s'] for e in m_real['eventos']),
         'espera %s; parado %s (o robo freia dentro da espera)'
         % ('/'.join('%.2f' % e['espera_s'] for e in m_real['eventos']),
            '/'.join('%.2f' % e['parado_s'] for e in m_real['eventos'])))
conferir('o plotador marca os mesmos eventos (a mesma funcao)',
         plotar_trajetoria.interrupcoes(plotar_trajetoria.ler_csv(str(f_real)))
         == [e['i'] for e in m_real['eventos']],
         '%d marca(s)' % len(m_real['eventos']))

# O ensaio de 09/11 em miniatura: 25 s de `navegando` parado antes (o
# gravar_pose poe `navegando` enquanto nao ouve o vigia, e o vigia comeca em
# `navegando` sem goal), UM evento so de `esperando`, e o robo parado no
# destino depois do sucesso, com o /scan MAIS perto que o limiar -- como os
# 0,480 m do ensaio, que o vigia de 0,75 m nunca comparou com nada.
# corta a sessao 3 s antes do segundo disparo, antes de a pessoa aparecer
um = [dict(r) for r in lin_real[:m_real['eventos'][1]['i'] - 30]]
dt = medir_sessao.passo_mediano(um)
antes = []
for k in range(250):
    r = dict(um[0])
    r.update(t=k * dt, cmd_v=0.0, cmd_w=0.0, estado='navegando')
    antes.append(r)
for r in um:
    r['t'] += 250 * dt
depois = []
for k in range(1, 51):
    r = dict(um[-1])
    r.update(t=um[-1]['t'] + k * dt, cmd_v=0.0, cmd_w=0.0,
             dist_min_scan=0.35, estado='navegando')
    depois.append(r)
ensaio = antes + um + depois
f_ens = tmp / 'ensaio.csv'
simular_sessao.gravar_csv(f_ens, ensaio)
m_ens = medir_sessao.medir(medir_sessao.ler_csv(f_ens))
conferir('o ensaio de 09/11 em miniatura da 1 evento, nao 0',
         len(m_ens['eventos']) == 1 and not m_ens['fora_da_espera'],
         'espera %.2f s' % m_ens['eventos'][0]['espera_s'])
conferir('25 s de `navegando` parado no comeco nao viram evento',
         m_ens['eventos'][0]['t'] > 250 * dt and m_ens['truncado'] is None,
         'evento em t = %.1f s' % m_ens['eventos'][0]['t'])
r_min = ensaio[m_ens['i_scan_min']]
conferir('0,35 m parado no destino e o minimo da sessao, mas nao do portao',
         abs(r_min['dist_min_scan'] - 0.35) < 1e-9 and not m_ens['furos']
         and ensaio[m_ens['i_scan_armado']]['dist_min_scan']
         >= medir_sessao.LIMIAR_OBSTACULO_M,
         'armado: %.3f m; nenhuma frase "olhe: ... portao armado"'
         % ensaio[m_ens['i_scan_armado']]['dist_min_scan'])
conferir('a figura do ensaio marca 1 interrupcao',
         len(plotar_trajetoria.interrupcoes(
             plotar_trajetoria.ler_csv(str(f_ens)))) == 1)

cortado = [dict(r) for r in ensaio[:5]]
for r in cortado:
    r['estado'] = 'esperando'          # o bag comecou no meio de uma espera
cortado += ensaio[5:]
m_cort = medir_sessao.medir(cortado)
conferir('um CSV que JA comeca em `esperando` nao ganha evento falso',
         len(m_cort['eventos']) == 1 and m_cort['truncado'] == (0, 5)
         and not m_cort['fora_da_espera'],
         'o bloco cortado e avisado, nao contado')

furo = [dict(r) for r in ensaio]
k_furo = 250 + 300
furo[k_furo]['dist_min_scan'] = 0.30   # portao armado, robo andando, sem evento
m_furo = medir_sessao.medir(furo)
conferir('/scan abaixo do limiar com o portao armado e sem evento: "olhe:"',
         m_furo['furos'] == [k_furo]
         and any(s.startswith('olhe: o /scan') for s in
                 medir_sessao.veredito(m_furo)),
         't = %.1f s' % furo[k_furo]['t'])

r75, res75 = simular_sessao.simular(como_vigia_real=True, limiar=0.75)
f75 = tmp / 'real75.csv'
simular_sessao.gravar_csv(f75, r75)
lin75 = medir_sessao.ler_csv(f75)
m75 = medir_sessao.medir(lin75, limiar=0.75)
v75 = medir_sessao.veredito(m75)
conferir('sessao com limiar_m 0,75 medida com --limiar 0.75: eventos certos',
         len(m75['eventos']) == res75['eventos'] > 0
         and all(e['scan'] < 0.75 for e in m75['eventos'])
         and not any(s.startswith('ATENCAO') for s in v75),
         '/scan nos eventos: %s' % '; '.join('%.3f' % e['scan']
                                             for e in m75['eventos']))
conferir('e o veredito diz em uma linha que o TP4 pede 0,50 m',
         sum('o TP4 pede 0.50 m' in s for s in v75) == 1
         and not any('sustenta o item 2' in s for s in v75),
         [s for s in v75 if 'TP4 pede' in s][0][:60])
v75_50 = medir_sessao.veredito(medir_sessao.medir(lin75))
conferir('medida com o limiar padrao, a regua aponta o --limiar',
         any(s.startswith('ATENCAO') and '--limiar' in s for s in v75_50))
conferir('e com o limiar padrao nao ha a linha do "TP4 pede"',
         not any('TP4 pede 0.50' in s for s in medir_sessao.veredito(m)))
cli = subprocess.run([sys.executable, str(AQUI / 'medir_sessao.py'), str(f75),
                      '--limiar', '0.75'], capture_output=True, text=True)
conferir('`medir_sessao.py --limiar 0.75` imprime o limiar em LIMIARES',
         cli.returncode == 0 and 'obstaculo   : 0.75 m' in cli.stdout,
         [s.strip() for s in cli.stdout.splitlines() if 'obstaculo   :' in s][0]
         if 'obstaculo   :' in cli.stdout else cli.stderr[-80:])

# --------------------------------------------------------------------- 10
print('10. a maquina de estados do vigia.py, com dubles do rclpy')


class _Futuro:
    def __init__(self):
        self.cbs, self.valor = [], None

    def add_done_callback(self, cb):
        self.cbs.append(cb)

    def resolver(self, valor):
        self.valor = valor
        for cb in self.cbs:
            cb(self)

    def result(self):
        return self.valor


class _Msg:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Pub:
    def __init__(self, topico):
        self.topico, self.msgs = topico, []

    def publish(self, m):
        self.msgs.append(m.data)


class _Timer:
    def __init__(self, periodo, cb):
        self.periodo, self.cb, self.ativo = periodo, cb, True

    def cancel(self):
        self.ativo = False


class _Log:
    def __init__(self):
        self.linhas = []

    def info(self, s):
        self.linhas.append(s)

    warn = error = info


class _Relogio:
    agora_ns = 0

    def now(self):
        return _Msg(nanoseconds=_Relogio.agora_ns, to_msg=lambda: None)


class _Node:
    parametros = {}

    def __init__(self, nome):
        self.pubs, self.timers, self.log = {}, [], _Log()
        self._par = {}

    def declare_parameter(self, nome, valor):
        self._par[nome] = _Node.parametros.get(nome, valor)

    def get_parameter(self, nome):
        return _Msg(value=self._par[nome])

    def create_subscription(self, *a):
        return None

    def create_publisher(self, tipo, topico, qos):
        self.pubs[topico] = _Pub(topico)
        return self.pubs[topico]

    def create_timer(self, periodo, cb):
        self.timers.append(_Timer(periodo, cb))
        return self.timers[-1]

    def destroy_timer(self, t):
        self.timers.remove(t)

    def get_logger(self):
        return self.log

    def get_clock(self):
        return _Relogio()


class _Punho:
    accepted = True

    def __init__(self):
        self.res, self.canc = _Futuro(), _Futuro()

    def get_result_async(self):
        return self.res

    def cancel_goal_async(self):
        return self.canc


class _Cliente:
    def __init__(self, *a):
        self.envios = []

    def send_goal_async(self, meta, feedback_callback=None):
        self.envios.append((meta, _Futuro()))
        return self.envios[-1][1]


def _modulo(nome, **attrs):
    mod = types.ModuleType(nome)
    mod.__dict__.update(attrs)
    return mod


class _Goal:
    def __init__(self):
        self.pose, self.behavior_tree = None, ''


class _Pose:
    def __init__(self):
        self.header = _Msg(frame_id='', stamp=None)
        self.pose = _Msg(position=_Msg(x=0.0, y=0.0),
                         orientation=_Msg(z=0.0, w=1.0))


dubles = {
    'rclpy': _modulo('rclpy', init=lambda: None, ok=lambda: False,
                     shutdown=lambda: None, spin=lambda n: None),
    'rclpy.node': _modulo('rclpy.node', Node=_Node),
    'rclpy.action': _modulo('rclpy.action', ActionClient=_Cliente),
    'rclpy.qos': _modulo('rclpy.qos', qos_profile_sensor_data=None),
    'action_msgs': _modulo('action_msgs'),
    'action_msgs.msg': _modulo('action_msgs.msg', GoalStatus=_Msg(
        STATUS_SUCCEEDED=4, STATUS_CANCELED=5)),
    'geometry_msgs': _modulo('geometry_msgs'),
    'geometry_msgs.msg': _modulo('geometry_msgs.msg', PoseStamped=_Pose),
    'nav2_msgs': _modulo('nav2_msgs'),
    'nav2_msgs.action': _modulo('nav2_msgs.action', NavigateToPose=_Msg(
        Goal=_Goal)),
    'sensor_msgs': _modulo('sensor_msgs'),
    'sensor_msgs.msg': _modulo('sensor_msgs.msg', LaserScan=object),
    'std_msgs': _modulo('std_msgs'),
    'std_msgs.msg': _modulo('std_msgs.msg', Float32=lambda: _Msg(data=0.0),
                            String=lambda: _Msg(data='')),
}
reais = {k: sys.modules.get(k) for k in dubles}
sys.modules.update(dubles)
sys.path.insert(0, str(PACOTE))
try:
    import aula16_arvore.vigia as vigia_mod
finally:
    sys.path.remove(str(PACOTE))
    for k, v in reais.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v
shutil.rmtree(PACOTE / 'aula16_arvore' / '__pycache__', ignore_errors=True)


def _scan(d):
    return _Msg(ranges=[d], angle_min=0.0, angle_increment=0.0,
                range_min=0.05, range_max=10.0)


_Node.parametros = {'limiar_m': 0.75}
no = vigia_mod.Vigia()
estados = no.pubs['estado_vigia'].msgs
no.enviar_objetivo()
punho1 = _Punho()
no.cliente.envios[-1][1].resolver(punho1)
conferir('goal aceito publica `navegando` na hora',
         estados == ['navegando'], ' -> '.join(estados))
_Relogio.agora_ns = int(10e9)
no.ao_scan(_scan(0.80))
conferir('/scan a 0,80 m com limiar 0,75 nao interrompe',
         no.estado == 'navegando' and len(estados) == 1)
no.ao_scan(_scan(0.70))
conferir('/scan a 0,70 m: `interrompido` publicado ANTES do cancelamento voltar',
         estados[-1] == 'interrompido' and no.interrupcoes == 1)
punho1.canc.resolver(_Msg(goals_canceling=[1]))
espera = [t for t in no.timers if t.periodo == 2.0]
conferir('cancelamento aceito: `esperando` publicado e temporizador de 2 s',
         estados[-1] == 'esperando' and len(espera) == 1)
punho1.res.resolver(_Msg(status=5))
espera[0].cb()
conferir('fim da espera: `retomando` publicado, temporizador destruido, '
         'MESMO goal reenviado',
         estados[-1] == 'retomando' and espera[0] not in no.timers
         and not espera[0].ativo and len(no.cliente.envios) == 2
         and no.cliente.envios[0][0].pose.pose.position.x
         == no.cliente.envios[1][0].pose.pose.position.x)
punho2 = _Punho()
no.cliente.envios[-1][1].resolver(punho2)
conferir('a sequencia publicada e a do enunciado, sem depender dos 10 Hz',
         estados == ['navegando', 'interrompido', 'esperando', 'retomando',
                     'navegando'], ' -> '.join(estados))
_Relogio.agora_ns = int(10.5e9)
no.ao_scan(_scan(0.30))
conferir('dentro da carencia o portao nao dispara',
         no.estado == 'navegando' and no.interrupcoes == 1)
no.ao_publicar()
conferir('o temporizador de 10 Hz continua publicando estado e distancia',
         estados[-1] == 'navegando'
         and abs(no.pubs['dist_min'].msgs[-1] - 0.30) < 1e-9)
n_log = len(no.log.linhas)
no.ao_feedback(_Msg(feedback=_Msg(distance_remaining=0.0,
                                  number_of_recoveries=0)))
conferir('feedback com distancia 0,0 (antes do caminho) nao vai para o log',
         len(no.log.linhas) == n_log)
no.ao_feedback(_Msg(feedback=_Msg(distance_remaining=7.3,
                                  number_of_recoveries=0)))
conferir('e o feedback de verdade vai',
         len(no.log.linhas) == n_log + 1 and '7.3' in no.log.linhas[-1])
punho2.res.resolver(_Msg(status=4))
conferir('sucesso: 1 interrupcao no log, e o portao desarma',
         '1 interrupcao' in no.log.linhas[-1] and no.punho is None)
_Relogio.agora_ns = int(30e9)
no.ao_scan(_scan(0.30))
conferir('parado no destino, /scan a 0,30 m nao interrompe (sem goal)',
         no.estado == 'navegando' and no.interrupcoes == 1,
         'e por isso que o minimo do CSV pode cair abaixo do limiar ali')

print()
print('tempo total: %.1f s' % (time.perf_counter() - t_inicio))
print('NAO testado aqui: tudo o que precisa de ROS 2 -- o vigia contra um Nav2')
print('de verdade (o grupo 10 usa dubles), o gravar_pose lendo um bag, a arvore')
print('carregando no bt_navigator. Veja "O que foi e o que nao foi verificado"')
print('no README.')
if falhas:
    print('%d FALHA(S): %s' % (len(falhas), '; '.join(falhas)))
    raise SystemExit(1)
print('todos os testes passaram.')
