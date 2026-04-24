# ⚡ Referencia Rápida — Comandos y Variables

## 📋 Copiar-Pegar (Copy-Paste Ready)

### Instalación (One-Liner)

```bash
git clone https://github.com/DarnerDiaz/claude-ia-local.git ~/Desktop/"Claude IA Local" && cd ~/Desktop/"Claude IA Local" && bash setup.sh
```

### Inicio Manual Rápido

```bash
# Terminal 1: Descargar modelo
bash scripts/descargar-e-importar.sh gemma

# Terminal 2: Iniciar servidor
MODELO_MLX=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx \
  bash scripts/iniciar-servidor-mlx.sh

# Terminal 3: Ejecutar Claude Code
ANTHROPIC_BASE_URL=http://localhost:4000 \
ANTHROPIC_API_KEY=sk-local \
claude --model claude-sonnet-4-6
```

---

## 🔧 Variables de Entorno (Cheat Sheet)

### Cambiar Modelo

```bash
# OPCIÓN 1: Gemma (rápido, 18 GB RAM)
MLX_MODEL=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx bash scripts/iniciar-servidor-mlx.sh

# OPCIÓN 2: Llama (inteligente, 70 GB RAM)
MLX_MODEL=divinetribe/llama-3.3-70b-instruct-abliterated-8bit-mlx bash scripts/iniciar-servidor-mlx.sh

# OPCIÓN 3: Qwen (rápido, 75 GB RAM)
MLX_MODEL=Qwen/Qwen2.5-32B-Instruct bash scripts/iniciar-servidor-mlx.sh
```

### Optimizaciones de Memoria

```bash
# Ahorrar RAM (4-bit KV cache)
MLX_KV_BITS=4 bash scripts/iniciar-servidor-mlx.sh

# Máxima precisión (8-bit KV cache) — default
MLX_KV_BITS=8 bash scripts/iniciar-servidor-mlx.sh

# Combinar: Gemma + 4-bit + menos tokens
MLX_MODEL=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx \
  MLX_KV_BITS=4 \
  MLX_MAX_TOKENS=4096 \
  bash scripts/iniciar-servidor-mlx.sh
```

### Modo Navegador (Browser Automation)

```bash
# Iniciar en modo navegador optimizado
MLX_BROWSER_MODE=1 bash scripts/iniciar-servidor-mlx.sh

# Luego: Brave debe estar corriendo con remote debugging
# Si no está:
/Applications/Brave\ Browser.app/Contents/MacOS/Brave --remote-debugging-port=9222
```

### Debug Verboso

```bash
# Ver logs detallados
MLX_DEBUG=1 bash scripts/iniciar-servidor-mlx.sh

# Ver qué tool-calls se están procesando
ANTHROPIC_BASE_URL=http://localhost:4000 \
ANTHROPIC_API_KEY=sk-local \
claude --verbose --model claude-sonnet-4-6
```

---

## 🎯 Soluciones Rápidas (Quick Fixes)

### Servidor no responde

```bash
# Ver si está escuchando
lsof -i :4000

# Matar proceso si está colgado
kill -9 $(lsof -t -i :4000)

# Reiniciar
MODELO_MLX=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx \
  bash scripts/iniciar-servidor-mlx.sh
```

### Out of Memory

```bash
# Opción 1: Cambiar a modelo más pequeño
MLX_MODEL=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx bash scripts/iniciar-servidor-mlx.sh

# Opción 2: Reducir KV cache
MLX_KV_BITS=4 bash scripts/iniciar-servidor-mlx.sh

# Opción 3: Limitar tokens de salida
MLX_MAX_TOKENS=4096 bash scripts/iniciar-servidor-mlx.sh
```

### Tool-calls no funcionan (garbled)

```bash
# Aumentar reintentos
MLX_TOOL_RETRIES=5 bash scripts/iniciar-servidor-mlx.sh

# O usar modelo más grande
MLX_MODEL=divinetribe/llama-3.3-70b-instruct-abliterated-8bit-mlx \
  bash scripts/iniciar-servidor-mlx.sh
```

---

## 🏥 Health Check

```bash
#!/bin/bash
echo "1. Hardware RAM:"
system_profiler SPHardwareDataType 2>/dev/null | grep Memory || echo "ERROR: macOS only"

echo -e "\n2. Python 3.12+:"
python3.12 --version

echo -e "\n3. Claude Code CLI:"
claude --version

echo -e "\n4. Git:"
git --version

echo -e "\n5. MLX venv:"
test -d ~/.local/mlx-server && echo "✓ Exists" || echo "✗ Missing"

echo -e "\n6. Server running:"
lsof -i :4000 | grep LISTEN && echo "✓ Running" || echo "✗ Not running"
```

Guarda como `health-check.sh`, haz ejecutable y corre:
```bash
chmod +x health-check.sh && ./health-check.sh
```

---

## 📊 Benchmarks Esperados

| Modelo | RAM | Vel | Primer request | Requests siguientes |
|--------|-----|-----|----------------|------------------|
| Gemma 31B | 18-24 GB | 15 tok/s | ~35s (cold) | ~4s (cached) |
| Llama 70B | 70 GB | 7 tok/s | ~40s (cold) | ~8s (cached) |
| Qwen 122B | 75 GB | 65 tok/s | ~45s (cold) | ~3s (cached) |

> **Nota:** Primer request es lento porque carga el modelo. Requests siguientes usan prompt caching.

---

## 🎤 Modo Hands-Free (Voice)

### Instalación completa

```bash
# 1. Instalar este repo
git clone https://github.com/DarnerDiaz/claude-ia-local.git ~/Desktop/"Claude IA"
cd ~/Desktop/"Claude IA"
bash setup.sh

# 2. Instalar NarrateClaude (sibling repo)
git clone https://github.com/nicedreamzapp/NarrateClaude.git ~/NarrateClaude
cd ~/NarrateClaude
chmod +x dictation/bin/* narrative-claude.sh
./dictation/bin/dictation setup

# 3. Ejecutar
./narrative-claude.sh
```

### Ejecutar solo servidor + CLI

```bash
# Terminal 1: Servidor con narración forzada
MLX_APPEND_SYSTEM_PROMPT_FILE=$HOME/Desktop/"Claude IA"/NarrativeGemma/CLAUDE.md \
  bash scripts/iniciar-servidor-mlx.sh

# Terminal 2: Claude Code (narración saldrá por ~/.local/bin/speak)
ANTHROPIC_BASE_URL=http://localhost:4000 \
ANTHROPIC_API_KEY=sk-local \
claude --model claude-sonnet-4-6
```

---

## 🔗 Links Útiles

| Recurso | URL |
|---------|-----|
| **Repo original (inglés)** | https://github.com/nicedreamzapp/claude-code-local |
| **Este repo (español)** | https://github.com/DarnerDiaz/claude-ia-local |
| **Arquitectura completa** | [ARQUITECTURA.md](docs/ARQUITECTURA.md) |
| **Solucionar problemas** | [SOLUCIONAR-PROBLEMAS.md](docs/SOLUCIONAR-PROBLEMAS.md) |
| **Cómo contribuir** | [CONTRIBUTING.md](CONTRIBUTING.md) |
| **Cambios/Roadmap** | [CHANGELOG.md](CHANGELOG.md) |
| **Discord (comunidad)** | https://discord.gg/ZdSqgAxUW |

---

## 📱 Control desde iPhone (iMessage)

```bash
# Instalar repo de control remoto
git clone https://github.com/nicedreamzapp/claude-screen-to-phone.git ~/claude-screen-to-phone
cd ~/claude-screen-to-phone
bash setup.sh

# Configurar tu número de teléfono
# Luego: Envía comandos por iMessage, obtén videos de respuesta
```

---

## 🔐 Verificar Seguridad (No hay data leaks)

```bash
# Verificar que cero llamadas salen del localhost
while true; do
  lsof -i -P | grep -E '(ESTABLISHED|LISTENING)' | grep -v '127.0.0.1\|localhost'
  sleep 5
done

# Debería ser vacío (solo localhost en el output)
```

---

## ✨ Tips Pro

1. **Usa double-click launchers** (`launchers/*.command`) — no necesitas terminal
2. **Symlink setup.sh** — edita `proxy/server.py` en el repo, se refleja automáticamente
3. **Prompt caching** — segundo request es 8-10× más rápido
4. **MLX_TOOL_RETRIES** — aumenta si tienes tool-calls garbled frecuentes
5. **test suite** — corre `python3 scripts/test_mlx_server.py` después de cambios

---

**¿Más dudas?** → [Abre un issue](https://github.com/DarnerDiaz/claude-ia-local/issues) o ve [SOLUCIONAR-PROBLEMAS.md](docs/SOLUCIONAR-PROBLEMAS.md)

⭐ **Si esto te ayudó, stargazo el repo!** ⭐
