# 🤝 Guía de Contribución

¡Bienvenido! Este proyecto es código abierto (MIT) y las contribuciones son bienvenidas.

## Antes de empezar

1. **Lee** [ARQUITECTURA.md](docs/ARQUITECTURA.md) — entiende cómo funciona internamente
2. **Lee** [SOLUCIONAR-PROBLEMAS.md](docs/SOLUCIONAR-PROBLEMAS.md) — conoce los problemas conocidos
3. **Forkea** el repo si no tienes acceso de push
4. **Crea una rama** para tu cambio: `git checkout -b feature/tu-idea`

---

## Tipos de Contribuciones Bienvenidas

### 🐛 Reportes de Bugs

Abre un issue con:
- **Descripción:** Qué esperabas vs qué pasó
- **Hardware:** M1/M2/M3/Max/Ultra + cantidad RAM
- **Steps:** Cómo reproducir
- **Logs:** Output de:
  ```bash
  python3 --version
  claude --version
  lsof -i :4000  # si el servidor está corriendo
  ```

### ✨ Nuevas Características

¿Idea para mejorar? Abre un issue primero (antes de code).

Ej: "Agrega soporte para Mistral 7B"
- Describe por qué es valioso
- Explica cómo lo harías
- Espera feedback antes de codear

### 📚 Mejoras de Documentación

- **README:** Si algo es confuso, dímelo
- **Troubleshooting:** Nuevo problema que encontraste? Agrégalo
- **Ejemplos:** Casos de uso reales

### 🚀 Optimizaciones

- Velocidad más rápida
- Menos RAM
- Mejor detección de tool-calls
- Mejor prompt caching

---

## Flujo de Contribución

### Paso 1: Fork + Clone (si no tienes acceso)

```bash
# En GitHub: Click "Fork" arriba a la derecha
git clone https://github.com/YOUR-USERNAME/claude-ia-local.git
cd claude-ia-local
git remote add upstream https://github.com/DarnerDiaz/claude-ia-local.git
```

### Paso 2: Crea una rama

```bash
git checkout -b feature/descriptive-name
# Ejemplos:
# - feature/mistral-support
# - fix/garbled-tool-recovery
# - docs/quick-start-guide
```

### Paso 3: Haz cambios

```bash
# Edita archivos
# Prueba localmente (si es código)
# Asegúrate que el formamto esté limpio
```

### Paso 4: Commit

```bash
git add .
git commit -m "breve descripción"
# Ej: "Add Mistral 7B support to model lineup"
```

### Paso 5: Push + PR

```bash
git push origin feature/descriptive-name

# Luego en GitHub:
# 1. Click "Compare & pull request"
# 2. Describe qué hace tu PR
# 3. Espera review
```

---

## Guías Específicas

### Si editaste el servidor (`proxy/server.py` + paquete `proxy/mlx_server/`)

El servidor está modularizado. `server.py` es solo el arranque; la lógica vive
en `proxy/mlx_server/`:

| Módulo | Responsabilidad | ¿Importa MLX? |
|--------|-----------------|:---:|
| `config.py` | Configuración (env vars) + `log()` | No |
| `text_cleaning.py` | Limpia el output del modelo | No |
| `tool_calls.py` | Conversión y parsing de tool-calls + recuperación | No |
| `messages.py` | Conversión de mensajes Anthropic + tokenización | No |
| `modes.py` | Detección de sesión code/browser + prompts | No |
| `metrics.py` | Recolector de métricas (thread-safe, acotado) | No |
| `dashboard.py` | HTML del panel de observabilidad | No |
| `model_loader.py` | Carga del modelo MLX + chat template | Sí |
| `generation.py` | Pipeline de inferencia + prompt cache + reintentos | Sí |
| `http_app.py` | Handler HTTP de la Messages API + /dashboard, /metrics | No |

- **Comentarios:** Agrega si es lógica nueva no obvia
- **Breaking changes:** Documenta en CHANGELOG
- **Tests:**
  - **Unitarios (rápidos, sin modelo):** `scripts/probar-funciones-puras.py` cubre
    la lógica pura (parsing de tool-calls, limpieza, conversión, modos). Corre con
    cualquier `python3`. Si tocas un módulo "No importa MLX", añade/actualiza su test aquí.
  - **End-to-end (necesita servidor corriendo):** `scripts/probar-servidor-mlx.py`.

```bash
# Tests unitarios (no requieren modelo ni MLX)
python3 scripts/probar-funciones-puras.py

# Test end-to-end (con el servidor MLX corriendo en :4000)
~/.local/mlx-server/bin/python scripts/probar-servidor-mlx.py
```

### Si editaste un launcher (`.command`)

- Verifica que siga el patrón de los otros
- Testing: ejecuta el launcher desde Finder (double-click)
- No debe necesitar terminal para usuarios normales

### Si editaste docs

- Usa Markdown limpio
- ASCII diagrams para arquitectura (no PNG)
- Mantén ejemplos actualizados
- Traduce al español si es documentación de usuario

### Si agregaste un nuevo modelo

1. Edita `README.md` tabla de modelos
2. Crea launcher en `launchers/`
3. Documenta en `SOLUCIONAR-PROBLEMAS.md` si hay quirks
4. Test: verifica que baja del Hugging Face

---

## Code Style

No tenemos linter estricto. Pero:

```python
# ✅ Bueno
def recover_garbled_tool_json(self, text):
    """Reconstructs valid JSON from garbled XML/JSON mix."""
    if "<function=" in text and "{" in text:
        # Probable garbled output
        ...
        return json_object

# ❌ Malo
def recovergarbedtooljson(self,text):
    # poco claro
    if '<function=' in text:
        ...
```

Reglas simples:
1. Nombra variables claramente (`response_text` no `r`)
2. Comenta por qué, no qué
3. Mantén funciones < 50 líneas si es posible
4. Usa type hints si es Python 3.10+

---

## Antes de hacer PR

- [ ] Probé localmente (si es código)
- [ ] Documenté cambios en CHANGELOG.md
- [ ] Actualicé README si es cambio público
- [ ] Verifiqué que `git diff` no tiene reformateos innecesarios
- [ ] Commit message describe QUÉ se cambió

---

## Proceso de Review

1. Yo (o mantenedor) reviso el PR
2. Pido cambios o apruebo
3. Si todo bien → merge a `master`
4. Automáticamente va a la siguiente release

---

## Reconocimiento

Todos los contributors aparecen en:
- Archivo `CONTRIBUTORS.md` (próximamente)
- GitHub "Contributors" graph
- Release notes si es cambio notable

---

## Preguntas?

- **Discord:** [servidor privado]
- **Issues:** Abre una
- **Email:** En mi bio de GitHub

¡Gracias por contribuir! 🚀
