# UAAF — Plan de Sesiones y Checklist

> Documento complementario a `SESSION_CONTEXT.md`
> Propósito: guía paso a paso para continuar el proyecto en sesiones independientes

---

## ✅ FASE 1 COMPLETADA — Architecture Auditor MVP

Todas las Test Suites A-F han sido implementadas, probadas y commiteadas:
- **Suite A** (Contrato): 43 tests
- **Suite B** (Descubrimiento): 27 tests
- **Suite C** (Imports): 28 tests
- **Suite D** (Reglas): 34 tests
- **Suite E** (Robustez): 19 tests
- **Suite F** (Integración): completada

**Plugin estable**: `plugins/architecture/architecture_auditor.py` v1.5.1

---

## 🚀 Flujo de trabajo por sesión (Fase 2)

```
┌─────────────────┐
│ 1. ABRIR CHAT   │ → Prompt estándar + objetivo específico
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. ASISTENTE    │ → Lee SESSION_CONTEXT.md + archivos relevantes
│    RECUPERA     │   desde tu repo raw (GitHub)
│    CONTEXTO     │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. IMPLEMENTAR  │ → Un solo objetivo por sesión
│    UN OBJETIVO  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. PROBAR EN    │ → VS Code, ejecutar tests
│    VS CODE      │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. COMMIT +     │ → git add . && git commit && git push
│    PUSH         │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. ACTUALIZAR   │ → Editar SESSION_CONTEXT.md con el nuevo estado
│    SESSION_     │   y subirlo al repo
│    CONTEXT.md   │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 7. CERRAR CHAT  │ → Nueva ventana de contexto limpia
└─────────────────┘
```

---

## 📋 Checklist de sesiones (FASE 2: Extensión)

### Sesión 2.1 — Report Engine
**Objetivo**: Generar reportes humanos y máquina-legibles a partir de `AuditResult`.

- [ ] Clase `ReportEngine` con método `generate(result: AuditResult, format: str) -> str`
- [ ] Formato **Markdown**: tabla de métricas, lista de findings con severidad, resumen ejecutivo
- [ ] Formato **JSON**: serialización completa y pretty-printed del `AuditResult`
- [ ] Template configurable (header, footer, branding UAAF)
- [ ] Escritura automática a `07_OUTPUTS/` con timestamp en el nombre de archivo
- [ ] Manejo de `AuditResult` vacío (sin findings) → reporte informativo, no vacío
- [ ] Manejo de múltiples findings → agrupados por severidad (CRITICAL → ERROR → WARNING → INFO)
- [ ] Smoke test: generar reporte desde un `AuditResult` real del architecture auditor
- [ ] Tests deterministas para ambos formatos

**Archivos de salida**:
- `08_SCRIPTS/uaaf_core/reporting/report_engine.py`
- `08_SCRIPTS/uaaf_core/reporting/__init__.py`
- `09_TESTS/unit/test_report_engine.py`

---

### Sesión 2.2 — Nuevo plugin: Documentation Auditor
**Objetivo**: Auditar la calidad y presencia de documentación en el proyecto.

- [ ] Especificación del plugin (`plugin.yaml`)
- [ ] Descubrimiento de archivos Markdown / RST / txt
- [ ] Reglas: README presente, CHANGELOG presente, docstrings mínimas
- [ ] Integración con el registro

**Archivo de salida**: `plugins/documentation/documentation_auditor.py`

---

### Sesión 2.3 — Nuevo plugin: Testing Auditor
**Objetivo**: Auditar la cobertura y calidad de tests del proyecto.

- [ ] Descubrimiento de archivos de test
- [ ] Reglas: cobertura mínima, tests unitarios presentes, fixtures

**Archivo de salida**: `plugins/testing/testing_auditor.py`

---

### Sesión 2.4 — Nuevos plugins: Configuration + AI Systems
**Objetivo**: Auditar configuraciones y sistemas de IA.

- [ ] Configuration Auditor: validación de config files, secrets, entornos
- [ ] AI Systems Auditor: validación de prompts, model cards, bias checks

**Archivos de salida**: `plugins/configuration/`, `plugins/ai_systems/`

---

### Sesión 2.5 — Features semánticas avanzadas (Architecture Auditor)
**Objetivo**: Extender el auditor arquitectónico con análisis estático avanzado.

- [ ] Complejidad ciclomática por función/módulo
- [ ] Dead code detection (funciones/imports no usados)
- [ ] Métricas de mantenibilidad (líneas de código, dependencias por módulo)
- [ ] Nuevos códigos de finding: `ARCH-COMPLEX-001`, `ARCH-DEAD-001`

**Archivo de salida**: `plugins/architecture/architecture_auditor.py` (extensión)

---

## 📝 Prompt estándar para iniciar cada sesión

Copia y pega esto exactamente al inicio de cada nuevo chat:

```
ROL: Actúa como Arquitecto Senior de IA, Ingeniero Full Stack especialista en LLMs, 
Prompt Engineer, Context Engineer y Agent Engineer. Posees experiencia equivalente 
a la de un líder técnico en empresas de IA.

Contexto: Estoy continuando mi proyecto UAAF (Universal Architecture Audit Framework). 
Lee PRIMERO el archivo SESSION_CONTEXT.md de mi repositorio público para entender 
el estado exacto del proyecto:
https://raw.githubusercontent.com/RayIA007/Universal-Architecture-Audit-Framework/main/SESSION_CONTEXT.md

Luego lee el archivo que te indicaré a continuación.

Objetivo de ESTA sesión: [COMPLETAR]

Limitaciones:
- Tengo VS Code con Python en Windows
- Dame solo el código listo para copiar y pegar
- Si hay múltiples archivos, indícame el path de cada uno
```

---

## ⚠️ Qué NUNCA hacer en una sesión

- ❌ Mezclar objetivos (no hacer "report engine + nuevo plugin" juntos)
- ❌ Pegar 500 líneas de código en el chat para "que recuerdes"
- ❌ Modificar `08_SCRIPTS/uaaf_core/audit/audit_result.py` sin coordinación
- ❌ Olvidar commitear y pushear antes de cerrar el chat
- ❌ Olvidar actualizar `SESSION_CONTEXT.md` al final de la sesión
- ❌ Intentar hacer todo en un solo chat (pierdo coherencia pasado cierto punto)

---

## ✅ Qué SÍ hacer en cada sesión

- ✅ Un objetivo = Un entregable = Un archivo de test o feature
- ✅ Commitear y pushear ANTES de cerrar el chat
- ✅ Actualizar `SESSION_CONTEXT.md` con el nuevo estado
- ✅ Pedirme que lea archivos raw desde GitHub (no pegar código)
- ✅ Probar en VS Code antes de confirmar que funciona
- ✅ Cerrar el chat y abrir uno nuevo para el siguiente objetivo
