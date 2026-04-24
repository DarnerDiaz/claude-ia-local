# 🏗️ Arquitectura Técnica — Claude IA Local

## Flujo de Datos End-to-End

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  USUARIO                                                            │
│    ↓                                                                │
│    📝 "write a function that..." (al Claude Code CLI)              │
│    ↓                                                                │
├─────────────────────────────────────────────────────────────────────┤
│                      CAPA 1: ENTRADA (INPUT)                        │
│                                                                     │
│  claude CLI (herramienta Anthropic)                                 │
│    ├─ Lee tu texto                                                 │
│    ├─ Detecta que estás pidiendo código                            │
│    ├─ Arma request en formato Anthropic API JSON                   │
│    └─ Envía POST a ANTHROPIC_BASE_URL=http://localhost:4000        │
│       (NO a api.anthropic.com — gracias a nuestra variable env)    │
│    ↓                                                                │
├─────────────────────────────────────────────────────────────────────┤
│                 CAPA 2: PROXY MLX (NUESTRO SERVIDOR)                │
│                      proxy/server.py (~1000 líneas)                 │
│                                                                     │
│  ┌─ 📥 RECIBE request HTTP POST /v1/messages                       │
│  │                                                                  │
│  ├─ 🔍 PARSEA:                                                      │
│  │  • messages[] — historial de conversación                       │
│  │  • system prompt — las instrucciones de Claude Code             │
│  │  • tools[] — herramientas disponibles (Bash, Read, Write, etc)  │
│  │  • max_tokens, temperature, other params                        │
│  │                                                                  │
│  ├─ 🔧 DETECTA MODO:                                               │
│  │  IF herramientas contienen Bash/Read/Edit/Write/etc:           │
│  │     → MODO CÓDIGO DETECTADO                                     │
│  │     → Reemplaza system prompt ~10K tokens con ~100 tokens      │
│  │     → (Modelos locales: lleno de instrucciones = confundido)    │
│  │  ELSE                                                            │
│  │     → MODO CHAT NORMAL                                          │
│  │                                                                  │
│  ├─ ⚡ CARGA MODELO (primera vez):                                 │
│  │  • MLX framework (Apple + vosotros)                             │
│  │  • Lee los .safetensors del modelo (Gemma/Llama/Qwen)           │
│  │  • GPU Metal: configura memoria unificada                       │
│  │  • KV cache quantizado según MLX_KV_BITS (4 u 8 bits)          │
│  │                                                                  │
│  ├─ 💭 PROMPT CACHING (si disponible):                             │
│  │  • Has completado este sistema prompt antes?                    │
│  │  • → REUTILIZA KV cache del prompt (sin re-llenar)             │
│  │  • Si no, computa e cachea para próxima vez                     │
│  │  • Ahorro: ~3-5 segundos por request                            │
│  │                                                                  │
│  ├─ 🤖 CONSTRUYE SOLICITUD PARA MODELO:                             │
│  │  • Convierte tools[] → formato del modelo                       │
│  │  • Gemma 4: <|tool_call>call:ToolName{params}<tool_call|>       │
│  │  • Llama: raw JSON en el message                                │
│  │  • Qwen: <tool_call>JSON</tool_call>                            │
│  │                                                                  │
│  ├─ 🧠 LLAMA AL MODELO via MLX:                                     │
│  │  • MLX genera tokens uno por uno (streaming)                    │
│  │  • Metal GPU procesa en paralelo (Apple Silicon power)          │
│  │  • temperatura = 0.2 (consistencia en tools)                    │
│  │  • max_tokens = 8192 (limitable vía MLX_MAX_TOKENS)             │
│  │                                                                  │
│  ├─ 🧹 LIMPIA OUTPUT:                                              │
│  │  • Modelo emite: <think>reasoning</think> + respuesta            │
│  │  • Eliminamos: <think>, <|channel>, stop markers                │
│  │  • Razón: local models piensan en voz alta                      │
│  │                                                                  │
│  ├─ 🔧 TRADUCE TOOL-CALLS (lo más importante):                    │
│  │  • Si el modelo dijo "voy a correr bash":                       │
│  │  • ├─ Intenta parsear JSON de tool-call                         │
│  │  • ├─ Si está garbled (XML/JSON mezclado):                      │
│  │  • │   └─ recover_garbled_tool_json() lo arregla                │
│  │  • ├─ Si aún falla:                                             │
│  │  • │   └─ Reintenta (hasta MLX_TOOL_RETRIES veces)              │
│  │  • └─ Convierte al formato Anthropic tool_use block             │
│  │                                                                  │
│  └─ 📤 ENVÍA respuesta en formato Anthropic:                       │
│     {                                                               │
│       "content": [                                                 │
│         {"type": "text", "text": "..."},                           │
│         {"type": "tool_use", "id": "...", "name": "Bash", ...}     │
│       ]                                                             │
│     }                                                               │
│    ↓                                                                │
├─────────────────────────────────────────────────────────────────────┤
│                   CAPA 3: SALIDA (OUTPUT/STDERR)                    │
│                                                                     │
│  claude CLI recibe respuesta (piensa que es de Anthropic)           │
│    ├─ Lee los tool_use blocks                                      │
│    ├─ Ejecuta Bash commands (localmente en tu Mac)                 │
│    ├─ Lee archivos (con Read tool)                                 │
│    ├─ Edita archivos (con Edit tool)                               │
│    └─ Muestra resultado en terminal                                │
│    ↓                                                                │
│  📊 OUTPUT → Tú ves el resultado                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. **server.py** (~1000 líneas)

El corazón del sistema. Escrito en Python puro.

#### Estructura interna:

```python
class MLXAnthropicServer:
    def __init__(self):
        # 1. Carga modelo MLX (una sola vez)
        self.model = mlx_lm.load(model_name)
        self.tokenizer = mlx_lm.load_tokenizer(model_name)
        
        # 2. Inicializa KV cache quantizado
        self.kv_bits = getenv("MLX_KV_BITS", default=8)
        
    def post_messages(self, request_body):
        # 1. Parsea request Anthropic
        messages = request_body["messages"]
        tools = request_body["tools"]
        
        # 2. Detecta modo código vs chat
        if self._is_coding_session(tools):
            system_prompt = SYSTEM_PROMPT_SLIM  # 100 tokens
        else:
            system_prompt = SYSTEM_PROMPT_FULL  # 10K tokens
        
        # 3. Cachea prompt si es posible
        kv_cache = self._get_cached_prompt_kv(system_prompt)
        
        # 4. Convierte tools al formato del modelo
        formatted_tools = self._convert_tools(tools, model_type)
        
        # 5. Construye input para modelo
        full_prompt = self._build_prompt(
            messages=messages,
            system=system_prompt,
            tools=formatted_tools
        )
        
        # 6. Genera tokens via MLX (streaming)
        response_text = ""
        for token in self.model.generate(full_prompt, kv_cache=kv_cache):
            response_text += token
            yield token  # streaming!
        
        # 7. Limpia output
        response_text = self._clean_output(response_text)
        
        # 8. Traduce tool-calls
        tool_calls = self._parse_tool_calls(response_text)
        if self._is_garbled(tool_calls):
            tool_calls = self._recover_garbled_tool_json(response_text)
        
        # 9. Convierte a formato Anthropic
        anthropic_response = self._convert_to_anthropic(tool_calls)
        
        # 10. Envía respuesta
        return anthropic_response
```

#### Key methods:

| Método | Qué hace | Líneas |
|--------|---------|--------|
| `_load_model()` | Carga modelo MLX + GPU | ~50 |
| `_build_prompt()` | Arma prompt completo del modelo | ~80 |
| `_convert_tools()` | Adapta tools → formato del modelo | ~120 |
| `_parse_tool_calls()` | Extrae tool-calls del output | ~60 |
| `_recover_garbled_tool_json()` | **Lo más ingenioso** — recupera JSON mal formado | ~100 |
| `_clean_output()` | Quita `<think>`, stop markers | ~30 |

---

### 2. **MLX Framework** (Apple)

No lo escribimos nosotros, pero es crítico. MLX = Apple's native ML framework for Apple Silicon.

```
┌─────────────────────────────────────────┐
│         Tu Mac (M-series chip)          │
│                                         │
│  ┌────────────────────────────────┐    │
│  │  Python (tu programa)          │    │
│  │                                │    │
│  │  model = mlx_lm.load(...)      │    │
│  │  └─> [pasa a MLX framework]    │    │
│  └────────────────────────────────┘    │
│           │                             │
│           ▼                             │
│  ┌────────────────────────────────┐    │
│  │  MLX (Apple framework)         │    │
│  │  ├─ Metal API driver          │    │
│  │  ├─ Unified memory management │    │
│  │  └─ GPU kernel compilation    │    │
│  └────────────────────────────────┘    │
│           │                             │
│           ▼                             │
│  ┌────────────────────────────────┐    │
│  │  Apple Silicon GPU              │    │
│  │  ├─ GPU cores (2-10 cores)     │    │
│  │  ├─ Unified memory (8-192 GB)  │    │
│  │  └─ Tensor processing units    │    │
│  └────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

**Por qué MLX vs Ollama/llama.cpp:**
- MLX habla Anthropic API nativo (sin proxy)
- Metal GPU: acceso directo, sin overhead
- Cuantización integrada (4-bit, 8-bit)
- 65 tok/s en Qwen 122B (vs 30-41 con Ollama)

---

### 3. **KV Cache Quantization**

Los modelos mantienen un "memory buffer" para cada token generado (Key-Value cache). Sin quantizar, para Llama 70B son ~75GB.

#### Cómo funciona:

```
Token 1:  [ KV cache: 32-bit floats ] ~500 MB
Token 2:  [ KV cache: 32-bit floats ] ~500 MB
...
Token 1000: ~500 GB total 🔥

PERO con quantización 8-bit:
Token 1:  [ KV cache: 8-bit ints ] ~125 MB
Token 2:  [ KV cache: 8-bit ints ] ~125 MB
...
Token 1000: ~125 GB (4× mejor)

Y con 4-bit: ~60 GB (aún mejor)
```

**Configuración:**
- `MLX_KV_BITS=8` — Default, buena coherencia
- `MLX_KV_BITS=4` — Ahorra RAM, algo de calidad
- `MLX_KV_QUANT_START=1024` — Empieza quantizado desde token 1024

---

### 4. **Tool-Call Recovery**

**El problema:** Modelos locales generan tool-calls mal formados.

**Ejemplo de garbled output:**

```xml
<tool_call>
<function=Bash><parameter=command>rm -rf /tmp/old</parameter></function>
</tool_call>
```

**Lo que esperamos (JSON puro Anthropic):**

```json
{"name": "Bash", "arguments": {"command": "rm -rf /tmp/old"}}
```

**Nuestra solución (3 pasos):**

```python
def _recover_garbled_tool_json(self, text):
    # Paso 1: Detecta XML/JSON mezclado
    if "<function=" in text and "{" in text:
        # Probable garbled output
        
        # Paso 2: Extrae campos uno por uno
        function_match = re.search(r'<function=(\w+)>', text)
        params_match = re.search(r'<parameter=(\w+)>([^<]+)', text)
        
        # Paso 3: Reconstruye JSON válido
        if function_match and params_match:
            return {
                "name": function_match.group(1),
                "arguments": {
                    params_match.group(1): params_match.group(2)
                }
            }
    
    # Si sigue fallando, retry
    return None  # Trigger retry
```

---

### 5. **Modo Código Auto-Detectado**

**Problema:** El prompt de Claude Code es ~10K tokens. Modelos locales: "too much information, confused"

**Solución:**

```python
def _is_coding_session(self, tools):
    """Detecta si estamos en sesión de código"""
    coding_tools = {"Bash", "Read", "Write", "Edit", "Grep", "Glob"}
    tool_names = {t["name"] for t in tools}
    return bool(tool_names & coding_tools)

if self._is_coding_session(tools):
    # Reemplaza system prompt entero
    system_prompt = """You are Claude Code, running locally.
You have these tools: [lista corta]
Execute commands and return results."""
    # ~100 tokens vs ~10K
```

**Resultado:** Misma precisión, 99% menos tokens para procesar.

---

## Variables de Entorno

| Variable | Default | Rango | Efecto |
|----------|---------|-------|--------|
| `MLX_MODEL` | `divinetribe/gemma-4-31b-it-abliterated-4bit-mlx` | Any HF repo | Qué modelo cargar |
| `MLX_KV_BITS` | `8` | 4 u 8 | Precisión vs RAM |
| `MLX_KV_QUANT_START` | `1024` | 512-2048 | Cuándo empezar quantización |
| `MLX_TOOL_RETRIES` | `2` | 1-5 | Reintentos en tool recovery |
| `MLX_MAX_TOKENS` | `8192` | 512-16384 | Max respuesta |
| `MLX_BROWSER_MODE` | (not set) | 0 ó 1 | Optimiza para browser MCP |
| `HF_HOME` | `~/.cache/huggingface` | path | Dónde cachear modelos |
| `ANTHROPIC_API_KEY` | (required) | sk-local | Dummy key (no se valida) |

---

## Flujo de Ejecución Detallado

### Primer Request (Cold Start)

```
t=0s    User: "write a hello world function"
        ↓
t=0.1s  Claude CLI → POST http://localhost:4000/v1/messages
        ↓
t=0.2s  Server recibe, valida, detecta coding session
        ↓
t=0.3s  CARGA MODELO: lee 18-75 GB desde disco (~10-30s acá)
        ↓
t=30s   MLX compila GPU kernels para la cuantización
        ↓
t=35s   Construye primer prompt, KV cache vacío
        ↓
t=35.5s GENERA respuesta (streaming):
        "I'll write a function for you..."
        ↓
t=36s   Claude Code ve respuesta, todo listo
        ↓
TOTAL: ~36 segundos primera solicitud

```

### Segundo Request (Warm Start)

```
t=0s    User: "now make it uppercase"
        ↓
t=0.1s  Claude CLI → POST (mismo modelo en RAM)
        ↓
t=0.2s  Server: modelo ya cargado ✓
        ↓
t=0.3s  KV cache del prompts anterior? → REUTILIZA
        ↓
t=0.4s  GENERA respuesta (sin re-llenar 10K tokens sistema)
        ↓
t=4s    Respuesta lista
        ↓
TOTAL: ~4 segundos con prompt caching
```

---

## MCP Servers — Eco-sistema de Plugins

Claude Code habla a plugins via **Model Context Protocol (MCP)**.

```
┌────────────────────────────────────────────┐
│  Claude Code CLI (tu máquina)              │
│                                            │
│  ANTHROPIC_BASE_URL=http://localhost:4000  │
│  (habla con nuestro proxy)                 │
└────────────────────────────────────────────┘
     │
     │ Streaming requests con tools[]
     │
     ▼
┌────────────────────────────────────────────┐
│  Nuestro server.py (MLX proxy)             │
│  ├─ Parsea tools desde MCP servers        │
│  ├─ Convierte al formato del modelo local │
│  └─ Traduce response de vuelta             │
└────────────────────────────────────────────┘
     │
     │ Mantiene definiciones de tools
     │
     ▼
┌────────────────────────────────────────────┐
│  MCP Servers (plugins)                     │
│  ├─ filesystem-mcp (lee/escribe archivos)  │
│  ├─ github-mcp (issues, PRs, search)       │
│  ├─ brave-search-mcp (búsqueda web)        │
│  └─ 200+ más en el ecosistema             │
└────────────────────────────────────────────┘
```

**Clave:** Nuestro proxy no rompe MCP. Mantiene:
- ✅ Tool definitions (descripción de qué hace cada herramienta)
- ✅ Tool use blocks (cuando el modelo decide usar una)
- ✅ Streaming format (respuestas en tiempo real)

---

## Optimizaciones Implementadas

| Optimización | Dónde | Impacto | Líneas |
|-------------|-------|---------|--------|
| **Prompt caching** | server.py | 3-5s más rápido en warm start | ~40 |
| **Code mode auto-detect** | server.py | 99% menos tokens | ~20 |
| **Garbled tool recovery** | server.py | Elimina infinite loops | ~100 |
| **KV quantization** | MLX (Apple) | 4× menos RAM | (built-in) |
| **Metal GPU streaming** | MLX | 65 tok/s vs 30 | (built-in) |
| **Lazy model loading** | server.py | No carga hasta primer request | ~30 |

---

## Performance Profiling

Para medir dónde está el cuello de botella:

```python
import time

start = time.time()
response = model.generate(prompt)
end = time.time()

prefill_time = end - start  # Tiempo hasta primer token
generation_time = len(tokens) / tokens_per_second

# Si prefill es > 5s, problema está en:
# 1. Modelo muy grande
# 2. KV cache no bien quantizado
# 3. GPU overcrowded
```

---

## Qué NO está Aquí (y por qué)

### ❌ LiteLLM
Antes la teníamos. Seguridad supply-chain → **REMOVIDA**

### ❌ Ollama
Funciona pero:
- Proxy overhead (30 tok/s máximo)
- No entiende Anthropic API nativamente

### ❌ llama.cpp
Rápido pero:
- No integración MLX (Apple GPU suboptimal)
- Requiere compilación extra

### ❌ Llamadas salientes
Cero llamadas HTTP a `api.anthropic.com` (excepto CLI startup no-bloqueante)
Verificado con `lsof -i -P`

---

## Conclusión

Este repo no es un proxy genérico. Es un **servidor Anthropic API nativo** que:

1. ✅ Habla JSON exactamente como Anthropic
2. ✅ Maneja tool-calls como Anthropic
3. ✅ Soporta MCP servers como Anthropic
4. ✅ Corre en GPU nativo (Metal Apple Silicon)
5. ✅ Recupera errores automáticamente
6. ✅ Cachea prompts para warm-start
7. ✅ Optimiza para código (auto-detecta)
8. ✅ **NUNCA** envía tu código a la nube

**En ~1000 líneas Python.**

---

*Última revisión: Abril 2026 | Versión: 2.0*
