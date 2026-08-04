#!/usr/bin/env bash
# check-ambiente.sh — confere se seu ambiente está pronto para a disciplina.
# Rode DENTRO do Ubuntu — no WSL2, na máquina virtual do VirtualBox ou no Ubuntu nativo.
# NUNCA no PowerShell/CMD do Windows. NÃO altera nada, só verifica.
# Uso rápido (sem clonar):
#   curl -sSL https://raw.githubusercontent.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio/main/recursos/check-ambiente.sh | bash
ok(){ printf "  \033[32m✓\033[0m %s\n" "$1"; }
no(){ printf "  \033[31m✗\033[0m %s\n" "$1"; FAIL=1; }
inf(){ printf "  · %s\n" "$1"; }
FAIL=0
echo "== Checagem de ambiente — PB Sistemas Robóticos =="

# 0) Qual rota de ambiente é esta? (muda o diagnóstico dos itens 6 e 7)
ROTA="nativo"
if grep -qi "microsoft" /proc/version 2>/dev/null || [ -n "$WSL_DISTRO_NAME" ]; then
  ROTA="wsl2"
elif [ "$(systemd-detect-virt 2>/dev/null)" = "oracle" ] || grep -qi "virtualbox" /sys/class/dmi/id/product_name 2>/dev/null; then
  ROTA="virtualbox"
fi
inf "rota detectada: $ROTA"

# 1) Ubuntu jammy
. /etc/os-release 2>/dev/null
[ "$UBUNTU_CODENAME" = "jammy" ] && ok "Ubuntu 22.04 (jammy)" || no "Ubuntu não é 22.04/jammy (é '${UBUNTU_CODENAME:-?}') — o ROS 2 Humble só existe para o 22.04"

# 2) ROS 2 Humble
[ -f /opt/ros/humble/setup.bash ] && ok "ROS 2 Humble instalado" || no "ROS 2 Humble ausente (tutorial setup, Passos 3–5)"
if command -v ros2 >/dev/null 2>&1; then ok "comando ros2 disponível"; else no "ros2 não encontrado — faltou instalar ou 'source /opt/ros/humble/setup.bash' (adicione no ~/.bashrc)"; fi

# 3) colcon
command -v colcon >/dev/null 2>&1 && ok "colcon" || no "colcon ausente (python3-colcon-common-extensions)"

# 4) git / gh / uv
command -v git >/dev/null 2>&1 && ok "git" || no "git ausente"
if command -v gh >/dev/null 2>&1; then
  gh auth status >/dev/null 2>&1 && ok "gh autenticado" || no "gh instalado mas não autenticado (gh auth login)"
else no "gh (GitHub CLI) ausente"; fi
command -v uv >/dev/null 2>&1 && ok "uv" || inf "uv ausente (opcional agora; necessário nos TPs 2+)"

# 5) ROS_DOMAIN_ID
if [ -z "$ROS_DOMAIN_ID" ] || [ "$ROS_DOMAIN_ID" = "0" ]; then inf "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-vazio} — defina seu nº de chamada no ~/.bashrc"; else ok "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"; fi

# 6) repositório + branches (se rodado dentro do repo)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  RAIZ="$(git rev-parse --show-toplevel)"
  ok "dentro de um repositório git ($(basename "$RAIZ"))"
  git show-ref --verify --quiet refs/heads/dev && ok "branch dev existe" || no "branch dev ausente — rode ./scripts/init-branches.sh"
  case "$RAIZ" in
    /mnt/[a-z]/*)   no "repo em $RAIZ — isso é o disco do WINDOWS visto de dentro do Linux: colcon fica lentíssimo e o git acusa arquivos modificados que você não tocou. Clone na home (~)";;
    /media/sf_*)    no "repo em $RAIZ — isso é uma PASTA COMPARTILHADA do VirtualBox: mesma armadilha do /mnt/c (build lento, permissões erradas). Clone na home (~)";;
    *)              ok "repo no filesystem do Linux";;
  esac
else
  inf "rode este script DENTRO do seu repositório clonado para checar as branches"
fi

# 7) OpenCV / NumPy / cv_bridge — a armadilha do pip fora de venv (Etapa 2 em diante)
python3 - <<'PY'
import importlib, sys
FALHOU = []
def cor(s, c): return "\033[%dm%s\033[0m" % (c, s)
def ok(m):  print("  %s %s" % (cor("✓", 32), m))
def no(m):  print("  %s %s" % (cor("✗", 31), m)); FALHOU.append(m)
def inf(m): print("  · %s" % m)

if sys.prefix != sys.base_prefix:
    inf("você está DENTRO de um venv (%s). Os nós ROS 2 não usam o venv — eles rodam com o "
        "python3 do sistema. Rode 'deactivate' e repita esta checagem" % sys.prefix)

for nome in ("numpy", "cv2"):
    try:
        m = importlib.import_module(nome)
    except Exception as e:
        inf("%s não importa (%s) — normal antes da Etapa 2" % (nome, type(e).__name__))
        continue
    caminho = getattr(m, "__file__", "") or ""
    versao = getattr(m, "__version__", "?")
    if "/usr/lib/python3/dist-packages" in caminho:
        ok("%s %s vindo do apt (certo)" % (nome, versao))
    else:
        no("%s %s vindo de %s — isso veio de pip FORA de venv e vai quebrar o cv_bridge. "
           "Cure com: python3 -m pip uninstall -y numpy opencv-python opencv-contrib-python "
           "opencv-python-headless && sudo apt install --reinstall python3-opencv python3-numpy"
           % (nome, versao, caminho))

try:
    from cv_bridge import CvBridge
    b = CvBridge()
    if 16 in b.cvtype_to_name:
        ok("cv_bridge saudável (a tabela de tipos conhece a chave 16)")
    else:
        no("cv_bridge instalado mas com a tabela de tipos ERRADA (sem a chave 16): "
           "é NumPy 2 ou OpenCV 5 vindo de pip no python do sistema. Veja a cura acima. "
           "Nada trava: o ponte.py do exemplo detecta isso sozinho e converte na mão")
except ImportError:
    inf("cv_bridge ausente — instale com: sudo apt install ros-humble-cv-bridge (a partir da Aula 3)")
except Exception as e:
    no("cv_bridge quebrado no import (%s: %s)" % (type(e).__name__, e))

sys.exit(1 if FALHOU else 0)
PY
[ $? -ne 0 ] && FAIL=1

echo ""
[ "$FAIL" = 0 ] && echo "✅ Tudo pronto!" || echo "⚠️  Há itens pendentes acima — veja os tutoriais e rode de novo."
