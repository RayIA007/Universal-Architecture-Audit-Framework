# UAAF — Plan de Sesiones y Checklist

> Documento complementario a `SESSION_CONTEXT.md`
> Propósito: guía paso a paso para continuar el proyecto en sesiones independientes

---

## 🚀 Flujo de trabajo por sesión

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

## 📋 Checklist de sesiones (FASE 1: Cierre MVP)

### Sesión N+1 — Test Suite A: Contrato y configuración
**Objetivo**: Validar que el plugin rechace entradas inválidas y acepte las válidas.

- [ ] `project_path` válido (directorio existente)
- [ ] `project_path` inválido (no existe, no es directorio, no es string)
- [ ] `audit_type` correcto (`"architecture"`)
- [ ] `audit_type` incorrecto (cualquier otro valor)
- [ ] Campos desconocidos en context (debe lanzar `ValueError`)
- [ ] `ignored_directories` válidas (lista de strings)
- [ ] `ignored_directories` inválidas (path en lugar de nombre, tipos incorrectos)
- [ ] Valores predeterminados (sin `ignored_directories`, sin `audit_type`)
- [ ] `AuditResult` serializable y pasa `validate_audit_result()`
- [ ] `AuditResult` tiene exactamente las keys requeridas, ni más ni menos

**Archivo de salida**: `09_TESTS/unit/test_architecture_contract.py`

---

### Sesión N+2 — Test Suite B: Descubrimiento e índice
**Objetivo**: Validar descubrimiento determinista de archivos y construcción del índice.

- [ ] Proyecto vacío → 0 archivos, 0 módulos, 0 paquetes
- [ ] `main.py` en raíz → 1 módulo, 0 paquetes
- [ ] `package/__init__.py` → 1 módulo, 1 paquete
- [ ] `package/module.py` con `__init__.py` → 2 módulos, 1 paquete
- [ ] Paquetes anidados (`a/b/c/__init__.py`)
- [ ] Namespace packages (directorio sin `__init__.py`)
- [ ] Exclusiones predeterminadas (`.git`, `__pycache__`, etc. no aparecen)
- [ ] Exclusiones personalizadas del usuario
- [ ] Rutas Windows → salida POSIX (`/` en lugar de `\`)
- [ ] Orden estable (mismo resultado en ejecuciones repetidas)
- [ ] Archivos no-Python ignorados
- [ ] Directorios vacíos no generan paquetes

**Archivo de salida**: `09_TESTS/unit/test_architecture_discovery.py`

---

### Sesión N+3 — Test Suite C: Imports y grafo
**Objetivo**: Validar extracción AST de imports y construcción del grafo de dependencias.

- [ ] `import x` → detectado
- [ ] `import x.y` → detectado
- [ ] `from x import y` → detectado
- [ ] `from x import y, z` → múltiples aliases detectados
- [ ] Imports relativos (`from . import x`, `from .. import y`)
- [ ] Imports relativos con módulo (`from .module import x`)
- [ ] Imports externos → clasificación `third_party`
- [ ] Imports stdlib → clasificación `stdlib`
- [ ] Imports locales → clasificación `local` + arista en grafo
- [ ] Imports locales no resolubles → clasificación `third_party` (fallback)
- [ ] Alias (`import x as y`) → target sigue siendo `x`
- [ ] Múltiples imports en un archivo
- [ ] Archivo con sintaxis inválida → skip sin crash
- [ ] Archivo no legible (encoding) → skip sin crash
- [ ] Aristas sin duplicados (mismo import repetido = una arista)

**Archivo de salida**: `09_TESTS/unit/test_architecture_imports.py`

---

### Sesión N+4 — Test Suite D: Las 4 reglas
**Objetivo**: Validar cada una de las 4 reglas de arquitectura con casos de prueba.

#### Regla 1: Ciclos (Commit 0016)
- [ ] Grafo sin ciclos → 0 ciclos detectados
- [ ] Ciclo simple (A→B→C→A) → 1 ciclo
- [ ] Múltiples ciclos independientes → N ciclos
- [ ] Ciclos superpuestos (A→B→C→A y B→C→D→B)
- [ ] Normalización de ciclos equivalentes (A→B→C→A == B→C→A→B)

#### Regla 2: Capas (Commit 0017)
- [ ] Import válido (misma capa o capa inferior)
- [ ] Import inválido (capa superior desde capa inferior)
- [ ] Módulo no asignado a capa → ignorado
- [ ] Configuración `layers` inválida → `ValueError`

#### Regla 3: Forbidden (Commit 0018)
- [ ] Pattern global que matchea
- [ ] Pattern global que NO matchea
- [ ] Pattern `module.*` que matchea `module` (root) y `module.sub`
- [ ] Regla per-source que matchea
- [ ] Regla per-source que NO matchea
- [ ] Configuración `forbidden_imports` inválida → `ValueError`

#### Regla 4: Init (Commit 0019)
- [ ] Matriz completa de la especificación (20 casos)
- [ ] `require_package_initializers=False` → 0 violaciones
- [ ] Configuración omitida → 0 violaciones (default False)

**Archivo de salida**: `09_TESTS/unit/test_architecture_rules.py`

---

### Sesión N+5 — Test Suite E: Robustez
**Objetivo**: Validar comportamiento ante condiciones adversas.

- [ ] Error recuperable no detiene la auditoría (ej: un archivo con syntax error)
- [ ] Salida determinista (mismo input = mismo output bit a bit)
- [ ] Ningún archivo auditado se modifica (solo lectura)
- [ ] Proyecto grande (100+ archivos) → no crash, tiempo razonable
- [ ] Rutas profundas (nesting de 10+ niveles)
- [ ] Caracteres Unicode en nombres de archivo
- [ ] Ejecución repetida → resultados idénticos
- [ ] Ausencia de estado residual entre ejecuciones (no hay variables globales mutables)

**Archivo de salida**: `09_TESTS/unit/test_architecture_robustness.py`

---

### Sesión N+6 — Test Suite F: Integración con Runtime Pipeline
**Objetivo**: Validar que el plugin funciona dentro del ecosistema UAAF real.

- [ ] Carga de `plugin.yaml` → metadata correcta
- [ ] Importación del entrypoint (`ArchitectureAuditorPlugin`)
- [ ] Ejecución vía `ArchitectureAuditorPlugin.execute(context)`
- [ ] Ejecución vía Runtime Pipeline (`UAAFRuntime`)
- [ ] Propagación del `AuditResult` al caller
- [ ] Manejo de fallo del plugin (excepción en `execute`)
- [ ] Convivencia con otros auditores (si existen)
- [ ] Smoke test sobre el propio UAAF (auditar el repo UAAF con el UAAF)

**Archivo de salida**: `09_TESTS/integration/test_architecture_pipeline.py`

---

## 📋 Checklist de sesiones (FASE 2: Extensión)

### Sesión N+7 — Report Engine
- [ ] Generador de reporte Markdown a partir de `AuditResult`
- [ ] Generador de reporte JSON a partir de `AuditResult`
- [ ] Template básico con resumen, métricas y findings
- [ ] Escritura en `07_OUTPUTS/`

**Archivo de salida**: `08_SCRIPTS/uaaf_core/reporting/report_engine.py`

### Sesión N+8 — Nuevo plugin: Documentation Auditor
- [ ] Especificación del plugin
- [ ] Descubrimiento de archivos Markdown / RST / txt
- [ ] Reglas: README presente, CHANGELOG presente, docstrings mínimas
- [ ] Integración con el registro

**Archivo de salida**: `plugins/documentation/documentation_auditor.py`

### Sesión N+9 — Nuevo plugin: Testing Auditor
- [ ] Descubrimiento de archivos de test
- [ ] Reglas: cobertura mínima, tests unitarios presentes, fixtures

**Archivo de salida**: `plugins/testing/testing_auditor.py`

### Sesión N+10 — Nuevos plugins: Configuration + AI Systems
- [ ] Configuration Auditor: validación de config files, secrets, entornos
- [ ] AI Systems Auditor: validación de prompts, model cards, bias checks

**Archivos de salida**: `plugins/configuration/`, `plugins/ai_systems/`

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

- ❌ Mezclar objetivos (no hacer "tests + report engine" juntos)
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
