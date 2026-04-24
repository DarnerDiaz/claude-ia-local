# 🔧 Solucionar Problemas (Troubleshooting)

## Inicio Rápido de Soluciones

### ❌ "command not found: claude"
```bash
# Solución: Necesitas instalar Claude Code CLI
npm install -g @anthropic-ai/claude-code
claude --version  # debería mostrar version reciente
```

---

### ❌ El launcher pregunta por credenciales de Claude
```bash
# Probable causa: CLI de Claude es muy viejo
# Solución: Actualizar
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code

# Los launchers pasan --bare para forzar API-key local auth
# Si Claude es viejo, no entiende ese flag y cae a login
```

---

### ❌ "No module named 'mlx'" o "ImportError: No module named 'mlx_lm'"

```bash
# Solución: El venv no tiene MLX instalado
# Opción 1: Re-crear venv limpio
rm -rf ~/.local/mlx-server
python3.12 -m venv ~/.local/mlx-server
~/.local/mlx-server/bin/pip install mlx-lm

# Opción 2: Verificar que Python 3.12+ está disponible
python3.12 --version  # debería ser 3.12+
which python3.12
```

---

### ❌ "GPU memory error" o "Out of memory on device: metal"

Esto significa el modelo es demasiado grande para tu Mac.

| Error | RAM tu Mac | Solución |
|-------|-----------|----------|
| **Metal memory error** | < 32 GB | Usa Gemma 4 31B (need ~18-24 GB) |
| **Allocation failed** | < 64 GB | Usa Gemma 4 31B + cierra otras apps |
| **Still failing** | < 64 GB | Baja KV cache: `MLX_KV_BITS=4` |

```bash
# Verificar RAM disponible (macOS)
system_profiler SPHardwareDataType | grep "Memory:"

# Ejecutar con KV cache reducido (ahorra ~20% RAM)
MLX_KV_BITS=4 bash scripts/iniciar-servidor-mlx.sh
```

---

### ❌ El servidor empieza pero Claude Code no se conecta

```bash
# Verificar que el servidor está escuchando en puerto 4000
lsof -i :4000

# Debería mostrar: python3 ... (LISTEN) ... 127.0.0.1:4000

# Si NO lo muestra:
# 1. Asegurar que el servidor está ejecutándose
# 2. Revisar si hay otro proceso en el puerto 4000
lsof -i :4000 | grep LISTEN

# Liberar el puerto (si es necesario)
kill -9 $(lsof -t -i :4000)

# Reintentar startup
bash scripts/iniciar-servidor-mlx.sh
```

---

### ❌ "ANTHROPIC_BASE_URL no está siendo usado"

```bash
# Verificar que la variable está seteada ANTES de ejecutar
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=sk-local
echo $ANTHROPIC_BASE_URL  # debería imprimir http://localhost:4000

# Luego ejecutar Claude Code
claude --model claude-sonnet-4-6

# O usar directamente en el comando
ANTHROPIC_BASE_URL=http://localhost:4000 ANTHROPIC_API_KEY=sk-local claude --model claude-sonnet-4-6
```

---

### ❌ La descarga de modelo se cuelga o es muy lenta

```bash
# MLX usa descargador automático con reintentos
# Pero si está MUY lenta:

# Opción 1: Usar descargador persistente (con reintentos exponenciales)
bash scripts/descarga-persistente.sh divinetribe/gemma-4-31b-it-abliterated-4bit-mlx

# Opción 2: Verificar conexión de red
ping huggingface.co
# Debería resolver y responder

# Opción 3: Alternativa — descargar manualmente (más control)
huggingface-cli download divinetribe/gemma-4-31b-it-abliterated-4bit-mlx --local-dir ~/.cache/huggingface/hub

# Luego setear
export HF_HOME=~/.cache/huggingface
bash scripts/iniciar-servidor-mlx.sh
```

---

### ❌ "ModuleNotFoundError: No module named 'anthropic'"

El servidor MLX necesita la librería Anthropic para emular su API.

```bash
# Solución
~/.local/mlx-server/bin/pip install anthropic
```

---

### ⚠️ El servidor arranca pero genera respuestas extrañas/garbled

Esto puede ocurrir si:
1. KV cache cuantizado está muy agresivo
2. Temperatura demasiado alta
3. Modelo no compatible

```bash
# Aumentar KV precision (menos garbled)
MLX_KV_BITS=8 bash scripts/iniciar-servidor-mlx.sh

# Bajar temperatura (más consistencia en tool-calls)
# Esto ya está en server.py, pero si necesitas ajustar:
# Edita proxy/server.py y busca: temperature = 0.2
# (0.2 es bueno para herramientas, 0.7 para creatividad)
```

---

### ❌ Tool-calls no se ejecutan (loop infinito)

Claude Code dice "let me do that" pero nunca lo hace.

**Causa:** Modelo genera tool-calls mal formados (JSON/XML mezclados). El server.py tiene recovery automático, pero puede fallar si:
- KV cache está garbled
- Modelo es muy pequeño (< 4B params)
- Prompt del sistema está corrupto

```bash
# Soluciones en orden de intento:

# 1. Aumentar reintentos de tool-call recovery
MLX_TOOL_RETRIES=5 bash scripts/iniciar-servidor-mlx.sh
# (default es 2, máximo sugerido es 5)

# 2. Mejorar KV cache
MLX_KV_BITS=8 MLX_TOOL_RETRIES=5 bash scripts/iniciar-servidor-mlx.sh

# 3. Cambiar modelo (si el actual es muy pequeño)
MLX_MODEL=divinetribe/llama-3.3-70b-instruct-abliterated-8bit-mlx \
  bash scripts/iniciar-servidor-mlx.sh
```

---

### ❌ Verificar que el server.py está actualizado

Si hiciste edits directos o hay drift entre versiones:

```bash
# setup.sh instala como symlink:
# ~/.local/mlx-native-server/server.py → claude-ia-local/proxy/server.py

# Verificar
ls -la ~/.local/mlx-native-server/server.py
# Debería mostrar un symlink (→ ...) apuntando al repo

# Si NO es symlink (es una copia), reinstalar:
bash setup.sh  # automáticamente lo arregla
```

---

### 🔍 Debug — Ver qué está pasando

```bash
# Activar logs verbosos
MLX_DEBUG=1 bash scripts/iniciar-servidor-mlx.sh

# Ver request/response del servidor (mientras corre)
# En otra terminal:
lsof -i :4000  # ver conexiones
strace -e openat python3 $(which server.py)  # syscalls (Linux)
# macOS: log stream --predicate 'eventMessage contains[c] "mlx"'

# Ver que variables de entorno están siendo usadas
env | grep MLX
env | grep ANTHROPIC
```

---

### 📊 Benchmarks Locales — Saber Qué Esperar

Test real: "Escribe una función que..."

| Modelo | Tiempo | Velocidad |
|--------|--------|-----------|
| Gemma 4 31B | ~20 seg | ~15 tok/s |
| Llama 70B | ~45 seg | ~7 tok/s |
| Qwen 122B | ~3 seg | ~65 tok/s |
| **Claude Cloud (Sonnet)** | ~5-10 seg | ~40 tok/s |

Si tus tiempos son **2-3× más lentos**, probablemente:
- Hay otra app usando la GPU
- KV cache está muy cuantizado
- Conexión a localhost tiene latencia (poco probable)

---

### 🎯 Modo Navegador — "No responde o commands no se ejecutan"

Si usas `MLX_BROWSER_MODE=1` pero aún tiene problemas:

```bash
# 1. Verificar que Brave está disponible y con CDP habilitado
# (debería estar en puerto 9222)
lsof -i :9222

# 2. Si no aparece, iniciar Brave manualmente con remote debugging:
/Applications/Brave\ Browser.app/Contents/MacOS/Brave --remote-debugging-port=9222

# 3. Luego iniciar servidor
MLX_BROWSER_MODE=1 bash scripts/iniciar-servidor-mlx.sh

# 4. En otra terminal
ANTHROPIC_BASE_URL=http://localhost:4000 \
  ANTHROPIC_API_KEY=sk-local \
  claude --model claude-sonnet-4-6
```

---

### 💬 ¿Todavía no funciona?

1. **Abre un issue** en el repo con:
   - Tu hardware (M1/M2/M3/Max/Ultra + RAM)
   - Qué comando ejecutaste
   - Qué error viste exactamente
   - Output de `python3 --version` y `node --version` y `npm list -g @anthropic-ai/claude-code`

2. **Discord oficial** (comunidad hispanohablante) → [servidor privado]

3. **Verificar logs** con `--verbose` o `MLX_DEBUG=1`

---

## 📋 Checklist de Salud del Sistema

Antes de reportar un bug, verifica:

```bash
#!/bin/bash

echo "=== SYSTEM HEALTH CHECK ==="

# Hardware
echo -n "✓ RAM: "
system_profiler SPHardwareDataType 2>/dev/null | grep "Memory:" || echo "UNKNOWN"

# Python
echo -n "✓ Python: "
python3.12 --version 2>/dev/null || echo "NOT FOUND - need 3.12+"

# Node + Claude Code
echo -n "✓ Claude Code: "
claude --version 2>/dev/null || echo "NOT FOUND"

# Git
echo -n "✓ Git: "
git --version

# MLX venv
if [ -d ~/.local/mlx-server ]; then
  echo "✓ MLX venv exists"
else
  echo "✗ MLX venv MISSING"
fi

# Servidor
if lsof -i :4000 | grep LISTEN > /dev/null 2>&1; then
  echo "✓ Server running on :4000"
else
  echo "✗ Server NOT running"
fi

echo "=== END CHECKS ==="
```

Guarda esto como `check-health.sh`, hazlo ejecutable y corre:
```bash
chmod +x check-health.sh
./check-health.sh
```

---

**¡Gracias por usar Claude IA Local! 🚀**
