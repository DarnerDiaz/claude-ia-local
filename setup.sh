#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║   Claude IA Local — Instalador de un comando / One-command    ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Detecta tu hardware, instala el servidor MLX, descarga un modelo y crea
# un launcher en tu Desktop. Idempotente: puedes re-ejecutarlo sin romper nada.
#
# Detects your hardware, installs the MLX server, downloads a model and
# creates a Desktop launcher. Idempotent: safe to re-run.
#
# Uso / Usage:
#   bash setup.sh                      # interactivo / interactive
#   bash setup.sh --yes                # sin preguntas (CI) / non-interactive
#   bash setup.sh --model llama        # gemma | llama | qwen
#   bash setup.sh --no-download        # solo instalar el servidor / server only
#   bash setup.sh --no-launchers       # no crear launchers en el Desktop
#   IDIOMA=en bash setup.sh            # forzar idioma / force language
#
set -euo pipefail

# ── Locate the repo and shared helpers ────────────────────────
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/lib/i18n.sh
source "$REPO_DIR/scripts/lib/i18n.sh"

# ── Colors ────────────────────────────────────────────────────
if [ -t 1 ]; then
  C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
  C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_CYAN=$'\033[36m'
else
  C_BOLD=""; C_DIM=""; C_RESET=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_CYAN=""
fi
ok()   { echo "${C_GREEN}✓${C_RESET} $*"; }
warn() { echo "${C_YELLOW}!${C_RESET} $*"; }
err()  { echo "${C_RED}✗${C_RESET} $*"; }
step() { echo ""; echo "${C_CYAN}${C_BOLD}▶ $*${C_RESET}"; }

# ── Defaults / flags ──────────────────────────────────────────
ASSUME_YES=0
MODEL_CHOICE=""        # gemma | llama | qwen (empty = auto by RAM)
DO_DOWNLOAD=1
DO_LAUNCHERS=1

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes)        ASSUME_YES=1 ;;
    --model)         MODEL_CHOICE="${2:-}"; shift ;;
    --model=*)       MODEL_CHOICE="${1#*=}" ;;
    --no-download)   DO_DOWNLOAD=0 ;;
    --no-launchers)  DO_LAUNCHERS=0 ;;
    -h|--help)
      # Print the header comment block (stops at the first non-comment line).
      awk 'NR>1 { if ($0 !~ /^#/) exit; sub(/^# ?/, ""); print }' "$0"
      exit 0 ;;
    *) err "$(t "Opción desconocida" "Unknown option"): $1"; exit 1 ;;
  esac
  shift
done

# ── Header ────────────────────────────────────────────────────
echo ""
echo "${C_CYAN}╔══════════════════════════════════════════════════╗${C_RESET}"
echo "${C_CYAN}║${C_RESET}   ${C_BOLD}Claude IA Local — $(t "Instalador" "Installer")$(t "                       " "                        ")${C_RESET}${C_CYAN}║${C_RESET}"
echo "${C_CYAN}╚══════════════════════════════════════════════════╝${C_RESET}"

# ── 1. Apple Silicon ──────────────────────────────────────────
step "$(t "Verificando hardware" "Checking hardware")"
if [ "$(uname -m)" != "arm64" ]; then
  err "$(t "Se requiere Apple Silicon (M1 o superior). Arquitectura detectada:" \
          "Apple Silicon (M1 or later) is required. Detected architecture:") $(uname -m)"
  exit 1
fi
MEM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}')
CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon')
ok "$CHIP — ${MEM_GB} GB RAM"

# ── 2. Disk space ─────────────────────────────────────────────
DISK_FREE_GB=$(df -k "$HOME" 2>/dev/null | awk 'NR==2 {print int($4/1024/1024)}')
ok "$(t "Espacio libre en disco" "Free disk space"): ${DISK_FREE_GB} GB"

# ── 3. Recommend a model by RAM tier (mirrors doctor.sh) ──────
PHI_ID="mlx-community/Phi-3-mini-4k-instruct-4bit"
GEMMA_ID="divinetribe/gemma-4-31b-it-abliterated-4bit-mlx"
LLAMA_ID="divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx"
QWEN_ID="mlx-community/Qwen3.5-122B-A10B-4bit"

if [ -z "$MODEL_CHOICE" ]; then
  if [ "$MEM_GB" -lt 16 ]; then
    # Gemma 31B needs ~18-20 GB RAM; it won't load here. Recommend a model
    # that actually fits instead of a fallback that's guaranteed to fail.
    warn "$(t "Con ${MEM_GB} GB, Gemma 31B no entra (necesita ~18-20 GB)." \
            "With ${MEM_GB} GB, Gemma 31B won't fit (needs ~18-20 GB).")"
    warn "$(t "Se usará Phi-3 Mini (~2 GB), el único que corre cómodo aquí." \
            "Using Phi-3 Mini (~2 GB), the only one that runs comfortably here.")"
    MODEL_CHOICE="phi"
  else
    MODEL_CHOICE="gemma"   # Gemma 4 31B is the recommended default across all viable tiers
  fi
fi

case "$MODEL_CHOICE" in
  phi)   MODEL_ID="$PHI_ID";   MODEL_LABEL="Phi-3 Mini"; MODEL_GB=3 ;;
  gemma) MODEL_ID="$GEMMA_ID"; MODEL_LABEL="Gemma 4 31B"; MODEL_GB=20 ;;
  llama) MODEL_ID="$LLAMA_ID"; MODEL_LABEL="Llama 3.3 70B"; MODEL_GB=75 ;;
  qwen)  MODEL_ID="$QWEN_ID";  MODEL_LABEL="Qwen 3.5 122B"; MODEL_GB=75 ;;
  *)     MODEL_ID="$MODEL_CHOICE"; MODEL_LABEL="$MODEL_CHOICE"; MODEL_GB=20 ;;
esac
ok "$(t "Modelo elegido" "Chosen model"): ${C_BOLD}${MODEL_LABEL}${C_RESET} (${MODEL_ID})"

if [ "$DO_DOWNLOAD" -eq 1 ] && [ "$DISK_FREE_GB" -lt "$MODEL_GB" ]; then
  warn "$(t "Solo ${DISK_FREE_GB} GB libres; ${MODEL_LABEL} necesita ~${MODEL_GB} GB." \
          "Only ${DISK_FREE_GB} GB free; ${MODEL_LABEL} needs ~${MODEL_GB} GB.")"
fi

# ── Confirmation gate (skipped with --yes) ────────────────────
if [ "$ASSUME_YES" -ne 1 ]; then
  echo ""
  printf '%s ' "$(t "¿Continuar con la instalación? [S/n]" "Proceed with installation? [Y/n]")"
  read -r REPLY || REPLY=""
  case "$REPLY" in
    n|N|no|NO) echo "$(t "Cancelado." "Cancelled.")"; exit 0 ;;
  esac
fi

# ── 4. Python 3.12+ ───────────────────────────────────────────
step "$(t "Buscando Python 3.12+" "Locating Python 3.12+")"
PYBIN=""
for cand in python3.13 python3.12 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,12) else 1)' 2>/dev/null; then
      PYBIN="$(command -v "$cand")"; break
    fi
  fi
done
if [ -z "$PYBIN" ]; then
  err "$(t "No se encontró Python 3.12+." "Python 3.12+ not found.")"
  echo "  $(t "Instálalo con" "Install it with"): ${C_CYAN}brew install python@3.12${C_RESET}"
  exit 1
fi
ok "Python: $PYBIN ($("$PYBIN" -V 2>&1))"

# ── 5. Claude Code CLI ────────────────────────────────────────
step "$(t "Verificando Claude Code CLI" "Checking Claude Code CLI")"
CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"
if command -v claude >/dev/null 2>&1 || [ -x "$CLAUDE_BIN" ]; then
  ok "Claude Code CLI $(t "encontrado" "found")"
else
  warn "$(t "Claude Code CLI no encontrado." "Claude Code CLI not found.")"
  if command -v npm >/dev/null 2>&1; then
    if [ "$ASSUME_YES" -eq 1 ]; then
      echo "  $(t "Instalando vía npm..." "Installing via npm...")"
      npm install -g @anthropic-ai/claude-code || warn "$(t "Falló npm install; instálalo manualmente." "npm install failed; install it manually.")"
    else
      echo "  $(t "Instálalo con" "Install it with"): ${C_CYAN}npm install -g @anthropic-ai/claude-code${C_RESET}"
    fi
  else
    echo "  $(t "Instala Node/npm y luego" "Install Node/npm then"): ${C_CYAN}npm install -g @anthropic-ai/claude-code${C_RESET}"
  fi
fi

# ── 6. MLX virtualenv + mlx-lm ────────────────────────────────
step "$(t "Instalando servidor MLX" "Installing MLX server")"
MLX_VENV="$HOME/.local/mlx-server"
if [ -d "$MLX_VENV" ] && [ -x "$MLX_VENV/bin/python3" ]; then
  ok "$(t "venv MLX ya existe" "MLX venv already exists"): $MLX_VENV"
else
  echo "  $(t "Creando venv en" "Creating venv at") $MLX_VENV ..."
  "$PYBIN" -m venv "$MLX_VENV"
  ok "$(t "venv creado" "venv created")"
fi
echo "  $(t "Instalando/actualizando mlx-lm..." "Installing/updating mlx-lm...")"
"$MLX_VENV/bin/pip" install --quiet --upgrade pip
"$MLX_VENV/bin/pip" install --quiet --upgrade mlx-lm
ok "mlx-lm: $("$MLX_VENV/bin/pip" show mlx-lm 2>/dev/null | awk '/^Version:/ {print $2}')"

# ── 7. Symlink server.py (source of truth = repo) ─────────────
step "$(t "Enlazando el servidor (symlink)" "Linking the server (symlink)")"
SERVER_DIR="$HOME/.local/mlx-native-server"
SERVER_LINK="$SERVER_DIR/server.py"
SERVER_SRC="$REPO_DIR/proxy/server.py"
mkdir -p "$SERVER_DIR"
if [ ! -f "$SERVER_SRC" ]; then
  err "$(t "No se encontró" "Could not find") $SERVER_SRC"; exit 1
fi
# Replace any existing file/copy/old symlink with a fresh symlink to the repo.
if [ -e "$SERVER_LINK" ] || [ -L "$SERVER_LINK" ]; then
  rm -f "$SERVER_LINK"
fi
ln -s "$SERVER_SRC" "$SERVER_LINK"
ok "$(t "Symlink" "Symlink"): $SERVER_LINK → $SERVER_SRC"

# ── 8. Download the model ─────────────────────────────────────
if [ "$DO_DOWNLOAD" -eq 1 ]; then
  step "$(t "Descargando el modelo (puede tardar)" "Downloading the model (this can take a while)")"
  MLX_MODEL="$MODEL_ID" bash "$REPO_DIR/scripts/descargar-e-importar.sh" "$MODEL_CHOICE"
else
  warn "$(t "Descarga omitida (--no-download)." "Download skipped (--no-download).")"
fi

# ── 9. Desktop launchers (thin wrappers → repo launchers) ─────
if [ "$DO_LAUNCHERS" -eq 1 ]; then
  step "$(t "Creando launchers en el Desktop" "Creating Desktop launchers")"
  DESKTOP="$HOME/Desktop"
  if [ -d "$DESKTOP" ] && [ -d "$REPO_DIR/launchers" ]; then
    # A wrapper avoids breaking the launcher's `source lib/...` (it runs the
    # real one in place, where lib/ lives), so double-click works from anywhere.
    for launcher in "$REPO_DIR"/launchers/*.command; do
      [ -e "$launcher" ] || continue
      name="$(basename "$launcher")"
      wrapper="$DESKTOP/$name"
      {
        echo "#!/bin/bash"
        echo "# Auto-generado por setup.sh / Auto-generated by setup.sh"
        printf 'exec %q\n' "$launcher"
      } > "$wrapper"
      chmod +x "$wrapper"
      ok "$name"
    done
  else
    warn "$(t "No se encontró el Desktop o la carpeta launchers; omitido." \
            "Desktop or launchers folder not found; skipped.")"
  fi
fi

# ── 10. Done ──────────────────────────────────────────────────
step "$(t "¡Listo!" "Done!")"
echo ""
echo "  $(t "Siguiente paso" "Next step"):"
if [ "$DO_LAUNCHERS" -eq 1 ]; then
  echo "    ${C_BOLD}$(t "Doble clic en" "Double-click") 'Claude Local.command'${C_RESET} $(t "en tu Desktop" "on your Desktop") ✨"
fi
echo "    $(t "O en terminal" "Or in a terminal"):"
echo "    ${C_CYAN}MLX_MODEL=$MODEL_ID bash scripts/iniciar-servidor-mlx.sh${C_RESET}"
echo ""
echo "  $(t "Diagnóstico" "Diagnostics"): ${C_CYAN}bash scripts/doctor.sh${C_RESET}"
echo ""
