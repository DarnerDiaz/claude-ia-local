# 🧠⚡ Claude IA Local — El Alineamiento

**Ejecuta Claude Code 100% localmente en Apple Silicon. Sin nube. Sin suscripción. Sin que tus datos salgan de tu Mac.**

## 🎬 VER LA DEMOSTRACIÓN — IA AirGap

Una verdadera NDA. Llama 3.3 70B. Wi-Fi físicamente APAGADO. `lsof` ejecutándose en directo.
Observa un modelo de 70 mil millones de parámetros auditar un documento legal confidencial, en el dispositivo, con las pruebas en pantalla.

- **[Demostración AirGap IA — Wi-Fi APAGADO](https://www.youtube.com/watch?v=V_J1LpNGwmY)**
- **Construido por:** [Matt Macosko](https://x.com/NiceDreamzApps) — Original en inglés
- **Traducción y mejoras:** Para la comunidad hispanohablante

---

## 🤔 ¿Qué es esto?

Tu MacBook tiene una GPU poderosa integrada en el chip. Este proyecto usa esa GPU para ejecutar modelos de IA masivos — del mismo tipo que impulsan ChatGPT y Claude — completamente en tu computadora.

```
     Flujo de datos (TODO DENTRO DE TU MAC):

     📝 Tu código
         ↓
    🤖 Claude Code
         ↓
    ⚡ Servidor MLX Local (puerto 4000)
         ↓
    🥊 Elige tu modelo: Gemma 31B | Llama 70B | Qwen 122B
         ↓
    🖥️  GPU Apple Silicon (memoria unificada)
```

### ✨ Lo que obtienes:

- **🚫 Sin internet** — Funciona completamente offline
- **💰 Sin suscripción** — $0/mes para siempre
- **🔒 Sin data-leaks** — Tu código nunca sale de tu Mac
- **✅ Experiencia Claude Code completa** — Escribe código, edita archivos, gestiona proyectos, controla tu navegador
- **🎤 Sesión hands-free** — Habla en tu propia voz, escucha respuestas en tu voz clonada (ambas direcciones, 100% local)

---

## 🥊 Los Modelos — Elige tu Combatiente

| Apodo | Velocidad | RAM | Parámetros | Mejor para | Launcher |
|-------|-----------|-----|-----------|-----------|----------|
| 🟢 **La Rápida** | ~15 tok/s | ~18 GB | 31B | Programación diaria, Macs 64 GB | `Gemma 4.command` |
| 🟠 **La Sabia** | ~7 tok/s | ~70 GB | 71B dense | Razonamiento avanzado, precisión | `Llama 70B.command` |
| 🔵 **La Bestia** | 65 tok/s 🚀 | ~75 GB | 122B (activos 10B) | Máximo rendimiento | `Qwen 122B.command` |

**Velocidad comparada con nube:**
- Qwen local: 65 tok/s vs Claude Opus cloud (~40 tok/s) ⚡
- **Costo:** $0/mes vs $20-100+/mes en cloud

---

## 🔒 Seguridad + Cómo Fluyen los Datos

### Diagrama de Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    🖥️  TU MACBOOK                           │
│                                                             │
│   📝 Tu código         ┌────────────────────┐               │
│       │                │  🤖 Claude Code     │               │
│       └───────────────▶│  (CLI en tu Mac)    │               │
│                        └────────┬───────────┘               │
│                                 │  HTTP localhost:4000       │
│                                 ▼                            │
│                        ┌────────────────────┐               │
│                        │  ⚡ Servidor MLX    │               │
│                        │  (Python, nuestro) │               │
│                        └────────┬───────────┘               │
│                                 │  Metal API                 │
│                                 ▼                            │
│                        ┌────────────────────┐               │
│                        │  🧠 Modelo local   │               │
│                        │ (Gemma·Llama·Qwen) │               │
│                        └────────┬───────────┘               │
│                                 │                            │
│                                 ▼                            │
│                        ┌────────────────────┐               │
│                        │  🖥️  GPU Apple      │               │
│                        │  (memoria unificada)│              │
│                        └────────────────────┘               │
│                                                             │
│             🚫 CERO llamadas de red salientes               │
│             🚫 CERO telemetría                              │
│             🚫 CERO "phone-home"                            │
└─────────────────────────────────────────────────────────────┘
                   │
                   ✗  ← Nada de nuestro código cruza esta línea
                   │
┌─────────────────────────────────────────────────────────────┐
│                    ☁️  INTERNET                              │
│              (tu código NUNCA va aquí)                      │
└─────────────────────────────────────────────────────────────┘
```

### ¿Qué verificamos?

| Componente | Autor | Llamadas salientes | Estado |
|-----------|-------|-------------------|--------|
| **server.py** (nuestro) | Lo escribimos línea por línea | 0 | ✅ Seguro |
| **Browser Agent** | nicedreamzapp | 0 (solo CDP localhost) | ✅ Seguro |
| **MLX** | Apple | 0 | ✅ Seguro |
| **Pesos del modelo** | HuggingFace verificado | 0 en runtime | ✅ Seguro |
| **Claude Code CLI** | Anthropic (binario) | 1 llamada no bloqueante | ⚠️ Divulgado |

> **Nota sobre la excepción:** El CLI de Claude Code hace un handshake no bloqueante a `api.anthropic.com` (probablemente verificación de versión). No podemos suprimirlo — está hardcodeado en el binario cerrado de Anthropic. **Pero:** Tus prompts, código y completions nunca salen de la máquina. Verificado con `lsof -i -P` una vez que el modelo está cargado.

---

## 💻 Requisitos Mínimos

| Hardware | RAM | GPU | Modelos posibles |
|----------|-----|-----|------------------|
| M1/M2/M3/M4 (base) | 8-16 GB | Integrada | 🟡 Modelos 4B |
| M1/M2/M3/M4 Pro | 18-36 GB | Pro | 🟠 Gemma 31B (justo) |
| M2/M3/M4/M5 Max | 64-128 GB | Max | 🟢 Gemma 31B + 🔵 Qwen 122B |
| M2/M3/M4 Ultra | 128-192 GB | Ultra | 🔵 Todos los modelos |

**También necesitas:**
- 🐍 Python 3.12+
- 🤖 Claude Code: `npm install -g @anthropic-ai/claude-code`

---

## 🚀 Inicio Rápido (3 Comandos)

### Opción 1: Automático (Recomendado)

```bash
git clone https://github.com/DarnerDiaz/claude-ia-local.git
cd claude-ia-local
bash setup.sh
```

`setup.sh` detecta automáticamente tu RAM, elige un modelo de la alineación, lo descarga, instala el servidor MLX y crea un launcher `Claude Local.command` en tu Desktop.

Luego: **double-click en `Claude Local.command`** ✨

### Opción 2: Manual

```bash
# 1. Configurar venv MLX
python3.12 -m venv ~/.local/mlx-server
~/.local/mlx-server/bin/pip install mlx-lm

# 2. Elegir y descargar un modelo (~18-75 GB)
bash scripts/descargar-e-importar.sh gemma   # o 'llama' o 'qwen'

# 3. Iniciar el servidor
MODELO_MLX=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx \
  bash scripts/iniciar-servidor-mlx.sh

# 4. En otra terminal: Lanzar Claude Code
ANTHROPIC_BASE_URL=http://localhost:4000 \
ANTHROPIC_API_KEY=sk-local \
claude --model claude-sonnet-4-6
```

---

## 🔧 Cómo Funciona Por Dentro

```
┌──────────────────────────────────────────────────┐
│              Tu MacBook (M5 Max)                 │
│                                                  │
│  📝 Tú escribes ──> 🤖 Claude Code               │
│                      │                           │
│                      ▼                           │
│                 ⚡ Servidor MLX (puerto 4000)    │
│                      │                           │
│                      ▼                           │
│           🥊 Modelo local ──> 🖥️  GPU           │
│        (Gemma·Llama·Qwen)                       │
│                      │                           │
│                      ▼                           │
│  📝 Respuesta <─── ✨ Limpia y formateada        │
│                                                  │
│    🔒 Nada sale de esta caja. Nunca.            │
└──────────────────────────────────────────────────┘
```

### El servidor (`proxy/server.py`) — ~1000 líneas

Hace 6 cosas principales:

1. **📦 Carga el modelo** — Framework MLX de Apple, GPU Metal nativo, memoria unificada. Maneja automáticamente la quirk de `RotatingKVCache` de Gemma.

2. **🔌 Habla API Anthropic** — Claude Code piensa que habla con Anthropic. No es así.

3. **🔧 Traduce tool-calls** — Maneja 3 formatos diferentes:
   - Gemma 4 nativo: `<|tool_call>call:Nombre{...}<tool_call|>`
   - Llama 3.3 JSON: `{\"type\":\"function\",...}`
   - HuggingFace: `<tool_call>JSON</tool_call>`
   
   Todo se convierte a bloques `tool_use` de Anthropic, con recuperación de output garbled.

4. **🧹 Limpia output** — Los modelos locales piensan en voz alta: `<think>`, `<|channel>thought`, emiten stop markers, etc. Los eliminamos.

5. **⚡ Reutiliza caches de prompt** — El prompt del sistema de Claude Code (~4K tokens) se cachea, no se re-rellena cada vez.

6. **🎯 Modo código** — Auto-detecta sesiones de Claude Code coding (Bash/Read/Edit/Write/Grep/Glob) e intercambia el prompt harness de ~10K tokens por uno slim de ~100 tokens tuned para modelos locales.

---

## 📊 Benchmarks

### Velocidad Generacional

| Generación | Backend | Velocidad |
|-----------|---------|-----------|
| 🐌 Gen 1 | Ollama | 30 tok/s |
| 🏃 Gen 2 | llama.cpp | 41 tok/s |
| 🚀 Gen 3 | MLX Nativo (nuestro) | 65 tok/s |

### Tarea Real: Pedir a Claude Code que escriba una función

```
😴 Ollama + Proxy:       133 seg
😐 llama.cpp + Proxy:    133 seg
🔥 MLX Nativo (sin proxy): 17.6 seg
```

**7.5× más rápido** ⚡ — Un cambio (eliminar proxy) produjo todo el delta.

---

## 🎮 Los Modos (4 formas de ejecutar la alineación)

| Modo | Descripción | Launcher |
|------|------------|----------|
| 🤖 **Código** | Claude Code con modelo local (sin API key) | `Claude Local.command` |
| 🌐 **Navegador** | IA local controla Brave real vía Chrome DevTools | `Browser Agent.command` |
| 🎤 **Voice Hands-Free** | Habla en, escucha en tu voz clonada — 100% on-device | `Narrative Gemma.command` |
| 📱 **Teléfono** | iMessage in → texto/imagen/video out, pipeline completo | `~/.claude/imessage-*.sh` |

---

## 🌐 Browser Agent

Un agente de navegador autónomo que controla tu navegador Brave real vía Chrome DevTools Protocol — alimentado enteramente por IA local.

```
         📝 Tu tarea
          │
     🤖 agent.py (repo separado)
          │
     ⚡ Servidor MLX
     (Gemma · Llama · Qwen)
          │
     🌐 Brave (Puerto CDP 9222) ← clicks, escribe, navega
          │
     📊 Context Meter → muestra el uso de memoria
```

**Característica especial:** Context memory inteligente
- Si alcanza 60% del presupuesto de 32K tokens, se comprime en resumen
- La tarea original se re-inyecta cada ciclo
- Color-codificado: verde/amarillo/rojo

→ **[Browser Agent repo separado](https://github.com/nicedreamzapp/browser-agent)**

---

## 🎤 Modo Hands-Free — El Loop Completo On-Device

**Habla a tu Mac. Te responde en tu voz clonada. Nada toca internet en ninguna dirección.**

```
┌─────────────────────────────────────────────────────────────────┐
│                     TU MACBOOK (Apple Silicon)                  │
│                                                                 │
│    🎙️  Tu voz                                                   │
│         │                                                       │
│         ▼                                                       │
│    🎧 listen (binario Swift compilado)                          │
│       • SFSpeechRecognizer de Apple (motor on-device)           │
│       • Escucha continua, fin de utterance por estabilidad      │
│       • Pausa automática durante reproducción (sin feedback)    │
│       • Reciclaje preventivo cada 10 min                        │
│         │                                                       │
│         ▼                                                       │
│    📬 dispatch (bash watchdog)                                  │
│         │                                                       │
│         ▼                                                       │
│    ⌨️  inject (AppleScript → terminal por window ID)            │
│         │                                                       │
│         ▼                                                       │
│    🤖 claude (persona de narración desde CLAUDE.md)             │
│         │                                                       │
│         ▼                                                       │
│    ⚡ Servidor MLX → 🟢 Gemma 4 31B  (~15 tok/s)               │
│         │                                                       │
│         ▼                                                       │
│    🔊 ~/.local/bin/speak (TTS con tu voz clonada)              │
│         │                                                       │
│         ▼                                                       │
│    🎵 afplay (listener pausa durante esto)                      │
│         │                                                       │
│         ▼                                                       │
│    👂 Tú escuchas → y sigues hablando                           │
│                                                                 │
│           🔒 Tu voz NUNCA sale de esta caja. Nunca.            │
└─────────────────────────────────────────────────────────────────┘
```

### Por qué funciona realmente:

- **🎙️ Speech-in** — Binario Swift compilado que envuelve `SFSpeechRecognizer` de Apple en loop de escucha continua (no el Fn-Fn toggle usual)
- **🔊 Speech-out** — CLI en `~/.local/bin/speak` que usa Pocket TTS con tu voz clonada
- **🔁 Prevención de feedback** — El listener pausa mientras `afplay` reproduce, evitando loops
- **🧠 Narración forzada** — El prompt del sistema asegura narración de cada tool call y resultado
- **🛡️ Hardening real** — Reciclaje preventivo cada 10 min, detección de backlog, no es un demo script

→ **[NarrateClaude repo separado](https://github.com/nicedreamzapp/NarrateClaude)** — Listening stack + TTS

---

## 🌐 Servidores MCP — Ecosistema de plugins de Claude Code, 100% local

**El ÚNICO modo de ejecutar el ecosistema completo de plugins de Claude Code 100% localmente en Apple Silicon.**

Configura MCP servers normalmente (`~/.claude.json` o por-proyecto `.mcp.json`). Ejemplos:

### 1️⃣ Sistema de archivos
```bash
claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem ~/projects
```
Ahora tu modelo local puede leer/escribir cualquier carpeta.

### 2️⃣ GitHub
```bash
claude mcp add github --env GITHUB_TOKEN=$GITHUB_TOKEN -- npx -y @modelcontextprotocol/server-github
```
Issues, PRs, búsqueda de código — todo local.

### 3️⃣ Búsqueda Web (Brave)
```bash
claude mcp add brave-search --env BRAVE_API_KEY=$BRAVE_API_KEY -- npx -y @modelcontextprotocol/server-brave-search
```
Respuestas frescas cuando el modelo necesita info reciente.

**El proxy mantiene MCP intacto:**
- Pasa definiciones de tools → tu modelo local
- Traduce `tool_use` blocks ← de vuelta a Anthropic format
- Compatible con todos los 3 modelos y familias

---

## ⚙️ Ajustes y Variables de Entorno

Sobrescribe defaults:

```bash
# Variable | Default | Descripción
# ---------|---------|-------------
MLX_MODEL | divinetribe/gemma-4-31b-it-abliterated-4bit-mlx | Elige tu combatiente
MLX_KV_BITS | 8 | Bits de quantización KV cache (4 = menos RAM, 8 = mejor coherencia)
MLX_KV_QUANT_START | 1024 | Token donde empieza la quantización KV
MLX_TOOL_RETRIES | 2 | Reintentos máx en tool-calls garbled
MLX_MAX_TOKENS | 8192 | Tokens máx por respuesta
MLX_BROWSER_MODE | (no set) | Optimiza para chrome-devtools MCP
```

### 🎯 Modo Navegador Optimizado

Si usas MCP browser automation, la lista de tools es enorme (~30+ tools, 10K+ tokens del sistema). Eso mata a los modelos locales.

Setea:
```bash
MLX_BROWSER_MODE=1 ./scripts/iniciar-servidor-mlx.sh
```

Auto-detecta sesiones MCP de Claude Code (por `mcp__chrome-devtools__*` tools) y mantiene solo los 9 tools esenciales. Misma automatización de navegador, **~99% menos tokens** para masticar.

---

## 📱 Control desde tu Teléfono — Pipeline Media Completo

Texto → comando, obtén video.

```
📱 Tu iPhone                    💻 Tu Mac
     │                              │
     │─ "find me an article ──────>│─ imessage-receive.sh lee
     │   and send me a video"      │─ modelo local planifica
     │                              │─ Brave browser encuentra
     │                              │─ speak narra en tu voz
     │                              │─ Studio Record captura
     │                              │─ build_production_video.py edita
     │<─ 🎥 video in iMessage ────│─ imessage-send-video.sh envía
     │                              │
   🛋️  Desde sofá              🖥️  En tu escritorio
```

Tipos de contenido soportados:

| Solicitud | Qué pasa | Salida |
|-----------|---------|--------|
| "summarize this article" | Modelo lee + responde | 💬 Texto |
| "send me a screenshot of X" | Claude captura | 📸 Imagen en iMessage |
| "screen record you doing Y" | Graba + envía | 🎥 Video en iMessage |
| "make me a produced video" | Pipeline edit completo | 🎬 Título + subtítulos |

→ **[claude-screen-to-phone repo](https://github.com/nicedreamzapp/claude-screen-to-phone)** — Pipeline completo

---

## 📁 Estructura del Repositorio

```
📦 claude-ia-local/
 ├── ⚡ proxy/
 │   └── server.py                ← MLX Anthropic Server (~1000 líneas)
 │
 ├── 🚀 launchers/
 │   ├── Claude-Local.command      ← Default + modelo local
 │   ├── Gemma-4-Codigo.command    ← 🟢 LA RÁPIDA
 │   ├── Llama-70B.command         ← 🟠 LA SABIA
 │   ├── Browser-Agent.command     ← 🌐 Control navegador
 │   ├── Gemma-Narrativa.command   ← 🎭 Modo auto-narración
 │   └── lib/claude-ia-local-comun.sh ← Shared utilities
 │
 ├── 🎭 Gemmanarrativa/
 │   └── CLAUDE.md                 ← Persona de narración
 │
 ├── 🛠️  scripts/
 │   ├── descargar-e-importar.sh   ← Descarga un modelo
 │   ├── descarga-persistente.sh   ← Reintentos automáticos
 │   ├── iniciar-servidor-mlx.sh   ← Helper de inicio
 │   ├── probar-servidor-mlx.py    ← Suite de tests
 │   └── subir-quant-mlx.sh        ← Publica quantizaciones
 │
 ├── 📊 docs/
 │   ├── BENCHMARKS.md             ← Comparativas de velocidad
 │   ├── SOLUCIONAR-PROBLEMAS.md   ← Troubleshooting detallado
 │   └── ARQUITECTURA.md           ← Explicación técnica
 │
 ├── setup.sh                      ← Instalador de un comando
 ├── .gitignore
 ├── LICENSE                       ← MIT
 └── README.md                     ← Aquí estás

```

---

## ✈️ Cuándo Usar Esto

| Caso | Local? | Nube? | ¿Mejor opción? |
|------|--------|-------|----------------|
| Trabajar en avión (sin wifi) | ✅ | ❌ | **Local** |
| Código sensible / NDA | ✅ | ❌ | **Local** |
| No quiero costos API | ✅ | ❌ | **Local** |
| Máxima velocidad | ☁️ | ✅ | Cloud (ligeramente) |
| Necesito razonamiento de Claude-level | ☁️ | ✅ | Cloud |
| Control desde teléfono | ✅ | ✅ | **Local** (iMessage) |
| Healthcare / Legal / Finance | ✅ | ❌ | **Local** (auditeable) |

---

## 🧩 El Stack Local-First Completo

Esto es solo la parte **cerebro**. Se combina con 3 repos hermanos:

### 🤖 **claude-ia-local** (aquí)
MLX + Gemma/Llama/Qwen · Servidor API Anthropic · Traducción de tool-calls · Caché de prompts. Sin cloud, 65 tok/s en Apple Silicon.

### 🎤 **[NarrateClaude](https://github.com/nicedreamzapp/NarrateClaude)**
Habla a Claude, escucha en tu voz clonada — ambas direcciones on-device. Loop hands-free completamente usando Apple `SFSpeech` + TTS clonado.

### 🌐 **[browser-agent](https://github.com/nicedreamzapp/browser-agent)**
Controla un navegador Brave real vía Chrome DevTools Protocol. Maneja iframes, Shadow DOM, editores.

### 📱 **[claude-screen-to-phone](https://github.com/nicedreamzapp/claude-screen-to-phone)**
Convierte tu iPhone en terminal Claude Code completa. Texto cualquier comando — git, shell, file edits, deploys — y obtén texto/screenshots/videos de pantalla en Messages. 100% sobre iMessage.

**Combina cualquiera. Los 4 juntos = computación ambiental en un Mac, nada en cloud.**

---

## 💡 Por qué esto importa — El ángulo de computación ambiental

El objetivo real no es "un Claude Code más rápido" — es salir de pantallas. La computación encorvada es mala para nosotros. Estos 3 repos son piezas de lo que viene después: computación que está **alrededor** de ti en lugar de **frente a** ti.

👉 **[Ver manifesto completo en NarrateClaude README](https://github.com/nicedreamzapp/NarrateClaude#-why-i-built-this--ambient-computing-starts-here)**

---

## 🤝 Contribuir

Si tienes ideas, reportes de bugs, un nuevo launcher, o un workflow que esto no cubre — abre un issue o PR.

Especialmente interesado en:
- **🧠** Quién corre en Apple Silicon más viejo (M1/M2, 16-36 GB)
- **🎤** Stress-test del loop voice en diferentes hardwares
- **🔊** Recetas TTS además de Pocket TTS
- **🌐** Workflows nuevos que esto no toca

---

## 📜 Licencia

**MIT** — Úsalo como quieras.

---

## 🙏 Créditos

Construido sobre hombros de gigantes:

| Componente | Autor |
|-----------|-------|
| 🤖 Claude Code | Anthropic |
| 🍎 MLX | Apple |
| 📦 mlx-lm | Apple |
| 🟢 Gemma 4 31B Base | Google DeepMind |
| 🟠 Llama 3.3 70B Base | Meta |
| 🔵 Qwen 3.5 122B | Alibaba |

**Original en inglés por:** Matt Macosko ([@NiceDreamzApps](https://x.com/NiceDreamzApps))
**Traducción, mejoras y optimizaciones:** [DarnerDiaz](https://github.com/DarnerDiaz)

---

## 💬 Comunidad

Discord para builders:
- **[Únete al Discord](https://discord.gg/ZdSqgAxUW)**

⭐ **¡Stargazo si esto te ayudó!** ⭐

---

**Última actualización:** Abril 2026 | Versión: 2.0 (traducida y mejorada)
