# 📜 Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [2.0] - 2026-04-24

### ✨ Nuevos (Esta Versión)

- **Traducción completa al español**
  - README.md traducido y mejorado
  - Comentarios de código en español
  - Documentación técnica en español

- **Documentación mejorada**
  - `ARQUITECTURA.md` — Explicación técnica profunda del servidor MLX
  - `SOLUCIONAR-PROBLEMAS.md` — Guía completa de troubleshooting con soluciones step-by-step
  - `CONTRIBUTING.md` — Guía para contribuyentes

- **Optimizaciones**
  - Mejor detección de modo código (reduce tokens innecesarios)
  - Recovery mejorado de tool-calls garbled
  - Prompt caching más efectivo

### 🔄 Cambios

- Reestructuración de la documentación para claridad
- Diagramas ASCII mejorados en lugar de enlaces a imágenes externas
- Guía paso-a-paso más detallada en el README

### 🐛 Bugs Arreglados

- Recuperación automática de tool-calls mal formados mejorada
- Mejor detección de modelos incompatibles

### 📝 Notas

- **Repositorio original:** [nicedreamzapp/claude-code-local](https://github.com/nicedreamzapp/claude-code-local)
- **Traducción y mejoras:** DarnerDiaz (2026)
- **Licencia:** MIT (igual que original)

---

## [1.0] - Original (Matt Macosko)

### ✨ Características Principales

- MLX Native Anthropic API Server (~1000 líneas Python)
- Soporte para 3 modelos: Gemma 4 31B, Llama 3.3 70B, Qwen 3.5 122B
- 4 modos: Código, Navegador, Voice hands-free, Control por iPhone
- Prompt caching para warm-start rápido
- KV cache quantizado (4-bit / 8-bit)
- Recovery automático de tool-calls garbled
- MCP servers totalmente soportados
- 65 tok/s en Apple Silicon (7.5× más rápido que Ollama)

### 🔒 Seguridad

- Totalmente on-device (zero cloud calls en operación normal)
- 100% auditeable (todo el código visible)
- Verificación manual de todas las dependencias

### 📊 Benchmarks

- Ollama: 30 tok/s
- llama.cpp: 41 tok/s
- **MLX Native (nuestro): 65 tok/s** ⚡

---

## Roadmap Futuro (Planeado)

### 🟡 Próximas Semanas

- [ ] Full Qwen 3.5 122B benchmark suite
- [ ] Fully-local Whisper fallback para macs viejos
- [ ] One-click DMG installer (macOS)
- [ ] `MLX_MODEL=<hf-url>` auto-register fighters
- [ ] Más modelos: DeepSeek, Mistral, Phi

### 🟠 Mediano Plazo

- [ ] Soporte Windows + Linux (vía WSL2)
- [ ] Documentación más detallada en español
- [ ] Ejemplos de uso prácticos
- [ ] Community-contributed optimizaciones

### 🔴 Largo Plazo

- [ ] Chat web UI (no solo CLI)
- [ ] Mobile companion app
- [ ] Integración con otros frameworks (Langchain, etc)
- [ ] Benchmark vs cloud APIs (costo-beneficio)

---

## Cómo Reportar un Bug

Abre un issue en [GitHub](https://github.com/DarnerDiaz/claude-ia-local/issues) con:
1. Descripción clara del problema
2. Tu hardware (M1/M2/M3/Max + RAM)
3. Pasos para reproducir
4. Output de comandos relevantes

---

## Convención de Versiones

Seguimos [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) — Breaking changes en API o funcionalidad crítica
- **MINOR** (1.X.0) — Nuevas features, backward-compatible
- **PATCH** (1.0.X) — Bug fixes, optimizaciones

Ej:
- 2.0.0 — Versión con traducción española + mejoras (breaking: docs en nuevo idioma)
- 2.1.0 — Nuevo modelo agregado (feature)
- 2.0.1 — Bug en tool recovery (fix)

---

## Licencia

Este proyecto mantiene la licencia **MIT** original. Ver [LICENSE](LICENSE) para detalles completos.

**Créditos:**
- 🤖 Claude Code — Anthropic
- 🍎 MLX Framework — Apple
- 🔴 Modelo base Gemma/Llama/Qwen — Google/Meta/Alibaba
- 💜 Original por Matt Macosko ([@NiceDreamzApps](https://x.com/NiceDreamzApps))
- 🔵 Traducción + mejoras — DarnerDiaz

---

**Última actualización:** Abril 2026

Para cambios próximos, sigue este repo o [sígueme en GitHub](https://github.com/DarnerDiaz).
