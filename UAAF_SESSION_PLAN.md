# UAAF — SESSION PLAN

## 1. Propósito del documento

Este documento define el orden de implementación del Universal Architecture Audit Framework y establece un objetivo único para cada sesión.

Regla principal:

> Una sesión debe concentrarse en un objetivo técnico claramente delimitado, producir entregables verificables y finalizar con tests deterministas pasando.

Cada sesión debe:

1. Leer `SESSION_CONTEXT.md`.
2. Leer este archivo.
3. Revisar los archivos canónicos relacionados con el objetivo.
4. Preservar los contratos públicos existentes.
5. Implementar cambios mínimos y cohesionados.
6. Crear o actualizar pruebas deterministas.
7. Ejecutar las pruebas específicas.
8. Ejecutar la suite completa.
9. Actualizar `SESSION_CONTEXT.md`.
10. Actualizar `UAAF_SESSION_PLAN.md`.
11. Realizar un commit enfocado.

---

## 2. Reglas permanentes del proyecto

### Compatibilidad

No se deben romper:

* `run(context) -> dict[str, Any]`.
* El wrapper público `execute()`.
* El contrato canónico `AuditResult`.
* Las severidades existentes.
* Los códigos de findings existentes.
* Las rutas relativas POSIX.
* El orden determinista.
* El entry point `run.py`.
* Los argumentos públicos de la CLI.
* Los códigos de salida `0`, `1` y `2`.

### Calidad

Cada implementación debe:

* Ser determinista.
* Ser compatible con Windows.
* Ser compatible con la versión de Python validada.
* Evitar dependencias externas innecesarias.
* Aislar errores por plugin.
* Producir mensajes de error claros.
* Mantener responsabilidades separadas.
* Incluir tests positivos, negativos y de borde.
* Mantener la suite completa pasando.

### Restricciones

* No modificar contratos canónicos sin coordinación explícita.
* No ocultar findings reales para hacer pasar una auditoría.
* No rellenar archivos placeholder con contratos ficticios.
* No debilitar detectores para evitar fixtures deliberados.
* No introducir lógica duplicada si existe un componente canónico que debe asumirla.

---

## 3. Flujo de trabajo por sesión

### Paso 1 — Lectura

Leer:

* `SESSION_CONTEXT.md`.
* `UAAF_SESSION_PLAN.md`.
* Archivos canónicos del componente.
* Tests existentes.
* Integraciones que consumen el componente.

### Paso 2 — Definición del contrato

Antes de programar:

* Identificar entradas.
* Identificar salidas.
* Identificar errores.
* Identificar consumidores.
* Identificar compatibilidad que debe preservarse.
* Definir el comportamiento determinista esperado.

### Paso 3 — Implementación

* Aplicar cambios mínimos.
* Evitar refactors no relacionados.
* Mantener separación de responsabilidades.
* Documentar decisiones no evidentes.
* Preservar compatibilidad hacia atrás.

### Paso 4 — Pruebas

Ejecutar:

1. Tests del componente.
2. Tests de integración relacionados.
3. Suite completa.
4. Smoke test funcional cuando corresponda.

### Paso 5 — Documentación

Actualizar:

* Estado de la fase.
* Total de tests.
* Archivos clave.
* Deuda técnica.
* Próximo objetivo.
* Historial resumido.

### Paso 6 — Git

* Revisar `git diff --check`.
* Revisar `git status --short`.
* Revisar el diff completo.
* Crear un commit enfocado.
* Subir al repositorio.

---

## 4. FASE 1 — Architecture Auditor MVP

### Estado

✅ COMPLETADA

### Objetivo

Crear un auditor arquitectónico determinista que pueda descubrir módulos, construir un grafo de dependencias, aplicar reglas arquitectónicas y producir findings canónicos.

### Entregables

* Architecture Auditor.
* Contrato de configuración.
* Descubrimiento de archivos.
* Índice de imports.
* Grafo de dependencias.
* Detección de ciclos.
* Validación de capas.
* Imports prohibidos.
* Validación de paquetes.
* Integración con Runtime Pipeline.
* Tests deterministas.

### Suites

* [x] Suite A — Contrato y configuración.
* [x] Suite B — Descubrimiento e índice.
* [x] Suite C — Imports y grafo.
* [x] Suite D — Reglas arquitectónicas.
* [x] Suite E — Robustez.
* [x] Suite F — Integración.

---

## 5. FASE 2 — Extensión

### Estado

✅ COMPLETADA

---

### Sesión 2.1 — Report Engine

#### Objetivo

Implementar un motor de reportes compatible con `AuditResult`.

#### Checklist

* [x] Reporte Markdown.
* [x] Reporte JSON.
* [x] Serialización determinista.
* [x] Manejo de findings.
* [x] Manejo de métricas.
* [x] Manejo de errores.
* [x] Nombres de archivo controlados.
* [x] 33 tests deterministas.

#### Archivos

* `08_SCRIPTS/uaaf_core/reporting/report_engine.py`
* `08_SCRIPTS/uaaf_core/reporting/__init__.py`
* `09_TESTS/unit/test_report_engine.py`

---

### Sesión 2.2 — Documentation Auditor

#### Objetivo

Auditar documentación estructural de proyectos Python.

#### Checklist

* [x] README raíz.
* [x] README por paquete.
* [x] Docstrings de módulo.
* [x] Docstrings de clase.
* [x] Docstrings de funciones.
* [x] Funciones privadas ignoradas cuando corresponde.
* [x] Dunder methods protegidos.
* [x] Placeholders documentales.
* [x] Métricas.
* [x] Resultado canónico.
* [x] Compatibilidad Python 3.14.
* [x] Prueba de regresión para expresiones AST no string.
* [x] 57 tests pasando.

#### Archivos

* `plugins/documentation/documentation_auditor.py`
* `plugins/documentation/__init__.py`
* `09_TESTS/unit/test_documentation_auditor.py`

---

### Sesión 2.2 — Testing Auditor

#### Objetivo

Auditar estructura, presencia y patrones de pruebas.

#### Checklist

* [x] Descubrimiento de tests.
* [x] Identificación de archivos productivos.
* [x] Relación estructural entre código y tests.
* [x] Detección conservadora de patrones.
* [x] Métricas.
* [x] Resultado canónico.
* [x] Tests deterministas.

#### Archivos

* `plugins/testing/testing_auditor.py`
* `plugins/testing/__init__.py`
* `09_TESTS/unit/test_testing_auditor.py`

---

### Sesión 2.2 — Configuration Auditor

#### Objetivo

Auditar archivos de configuración y detectar sintaxis inválida o configuraciones problemáticas.

#### Checklist

* [x] Descubrimiento de JSON.
* [x] Descubrimiento de YAML.
* [x] Descubrimiento de TOML.
* [x] Validación sintáctica.
* [x] Detección de archivos vacíos.
* [x] Findings `CONFIG-INVALID-001`.
* [x] Métricas.
* [x] Resultado canónico.
* [x] Tests deterministas.

#### Archivos

* `plugins/configuration/configuration_auditor.py`
* `plugins/configuration/__init__.py`
* `09_TESTS/unit/test_configuration_auditor.py`

---

### Sesión 2.2 — AI Systems Auditor

#### Objetivo

Auditar patrones estáticos asociados con sistemas de IA y LLMs.

#### Checklist

* [x] Imports de IA.
* [x] Secretos hardcodeados.
* [x] Prompts hardcodeados.
* [x] APIs sin manejo de errores.
* [x] Evaluación insegura.
* [x] Configuración de generación.
* [x] Modelos deprecated.
* [x] Agentes y RAG sin safeguards.
* [x] Resultado canónico.
* [x] Tests deterministas.

#### Archivos

* `plugins/ai_systems/ai_systems_auditor.py`
* `plugins/ai_systems/__init__.py`
* `09_TESTS/unit/test_ai_systems_auditor.py`

---

### Sesión 2.3 — Features semánticas avanzadas

#### Estado

✅ COMPLETADA

#### Objetivo

Extender el Architecture Auditor con análisis estático semántico avanzado, preservando completamente la compatibilidad con las Suites A–F.

#### Complejidad ciclomática

* [x] Analizar funciones síncronas.
* [x] Analizar funciones asíncronas.
* [x] Calcular complejidad por función.
* [x] Calcular complejidad por método.
* [x] Definir `max_cyclomatic_complexity`.
* [x] Validar el umbral.
* [x] Emitir `ARCH-COMPLEX-001`.
* [x] Mantener orden determinista.

#### Dead code conservador

* [x] Construir índices de definiciones.
* [x] Construir índices de referencias.
* [x] Detectar imports potencialmente no utilizados.
* [x] Detectar funciones sin referencias demostrables.
* [x] Proteger símbolos incluidos en `__all__`.
* [x] Proteger decoradores.
* [x] Proteger fixtures.
* [x] Proteger entry points.
* [x] Proteger funciones dunder.
* [x] Evitar marcar métodos públicos automáticamente.
* [x] Emitir `ARCH-DEAD-001`.

#### Métricas de mantenibilidad

* [x] Líneas físicas por módulo.
* [x] Líneas de código por módulo.
* [x] Número de funciones.
* [x] Número de funciones asíncronas.
* [x] Número de clases.
* [x] Complejidad promedio.
* [x] Complejidad máxima.
* [x] Dependencias locales.
* [x] Imports potencialmente no utilizados.
* [x] Funciones potencialmente no utilizadas.
* [x] Totales agregados.
* [x] Información por módulo.

#### Compatibilidad

* [x] Preservar `run(context)`.
* [x] Preservar `execute()`.
* [x] Preservar códigos anteriores.
* [x] No modificar `audit_result.py`.
* [x] Mantener rutas POSIX.
* [x] Mantener orden determinista.
* [x] Incrementar Architecture Auditor a 1.6.0.

#### Pruebas

* [x] Crear `test_architecture_semantics.py`.
* [x] Probar casos positivos.
* [x] Probar casos negativos.
* [x] Probar límites.
* [x] Probar falsos positivos.
* [x] Ejecutar Suites A–F.
* [x] Ejecutar Suite L.
* [x] Validar 232 tests del Architecture Auditor.
* [x] Cerrar la Fase 2 con todos los tests pasando.

#### Archivos

* `plugins/architecture/architecture_auditor.py`
* `09_TESTS/unit/test_architecture_semantics.py`

---

## 6. FASE 3 — Consolidación y CLI

### Estado

🚧 EN CURSO

| #   | Objetivo                     | Archivos principales               | Estado               |
| --- | ---------------------------- | ---------------------------------- | -------------------- |
| 3.1 | Orchestrator / CLI unificado | `orchestrator.py`, `cli.py`, tests | ✅ COMPLETADA         |
| 3.2 | Plugin Registry dinámico     | `registry.py`, integración y tests | ⏳ SIGUIENTE OBJETIVO |
| 3.3 | Configuración global         | `uaaf.yaml` / `[tool.uaaf]`        | ⏳ PENDIENTE          |
| 3.4 | Integración CI/CD            | GitHub Actions                     | ⏳ PENDIENTE          |
| 3.5 | Exportación SARIF            | `sarif_exporter.py`                | ⏳ PENDIENTE          |
| 3.6 | Documentación pública        | `README.md`, `docs/`               | ⏳ PENDIENTE          |

---

### Sesión 3.1 — Orchestrator / CLI unificado

#### Estado

✅ COMPLETADA

#### Objetivo

Crear un entry point único capaz de descubrir, seleccionar, ejecutar y consolidar todos los plugins de auditoría.

#### Descubrimiento

* [x] Descubrir plugins bajo `plugins/*/`.
* [x] Validar `__init__.py`.
* [x] Validar `<nombre>_auditor.py`.
* [x] Mantener orden determinista.
* [x] Soportar todos los plugins.
* [x] Soportar subsets.
* [x] Rechazar auditores desconocidos.

#### Ejecución

* [x] Construir `RuntimeContext`.
* [x] Ejecutar plugins secuencialmente.
* [x] Preservar `run(context)`.
* [x] Agregar `AuditResult` en orden.
* [x] Conservar errores por plugin.
* [x] Consolidar findings.
* [x] Consolidar métricas.

#### Reporting

* [x] Generar Markdown.
* [x] Generar JSON.
* [x] Utilizar `ReportEngine`.
* [x] Agregar timestamp.
* [x] Escribir en `07_OUTPUTS/`.
* [x] Permitir directorio alternativo.

#### CLI

* [x] `--project-path`.
* [x] `--auditors`.
* [x] `--output-formats`.
* [x] `--config`.
* [x] `--fail-on`.
* [x] `--exclude`.
* [x] `--output-dir`.
* [x] `--plugins-dir`.
* [x] `--framework-root`.
* [x] Compatibilidad con `python run.py`.

#### Códigos de salida

* [x] `0`: ejecución correcta sin severidades bloqueantes.
* [x] `1`: findings incluidos en `--fail-on`.
* [x] `2`: error operativo o plugin fallido.

#### Compatibilidad Python 3.14

* [x] Corregir inferencia de raíz en Windows.
* [x] Eliminar acceso a `ast.Str`.
* [x] Usar `ast.Constant`.
* [x] Agregar prueba de regresión AST.

#### Pruebas

* [x] Crear `test_orchestrator.py`.
* [x] Crear `test_cli.py`.
* [x] Ampliar `test_documentation_auditor.py`.
* [x] Ejecutar tests específicos.
* [x] Ejecutar suite completa.
* [x] Validar 577 tests pasando.
* [x] Ejecutar cinco plugins sin errores.
* [x] Generar Markdown y JSON.
* [x] Validar `--fail-on`.
* [x] Validar `--exclude`.
* [x] Obtener exit code `0` en el perfil operativo.

#### Resultado operativo

* 5 auditores.
* 941 warnings.
* 0 critical.
* 0 error.
* Exit code 0.

#### Archivos

* `08_SCRIPTS/uaaf_core/orchestrator.py`
* `08_SCRIPTS/uaaf_core/cli.py`
* `run.py`
* `09_TESTS/unit/test_orchestrator.py`
* `09_TESTS/unit/test_cli.py`
* `plugins/documentation/documentation_auditor.py`
* `09_TESTS/unit/test_documentation_auditor.py`

---

### Sesión 3.2 — Plugin Registry dinámico

#### Estado

⏳ SIGUIENTE OBJETIVO

#### Objetivo único

Convertir `UAAFRegistry` en la fuente canónica de descubrimiento, registro, validación, consulta y selección de plugins.

El Orchestrator deberá consumir el Registry y dejar de mantener lógica duplicada de descubrimiento.

#### Archivos que deben revisarse primero

1. `SESSION_CONTEXT.md`.
2. `UAAF_SESSION_PLAN.md`.
3. `08_SCRIPTS/uaaf_core/registry.py`.
4. `08_SCRIPTS/uaaf_core/kernel.py`.
5. `08_SCRIPTS/uaaf_core/runtime/runtime.py`.
6. `08_SCRIPTS/uaaf_core/orchestrator.py`.
7. `08_SCRIPTS/uaaf_core/cli.py`.
8. `08_SCRIPTS/uaaf_core/audit/audit_result.py`.
9. `09_TESTS/unit/test_orchestrator.py`.
10. `09_TESTS/unit/test_cli.py`.
11. Plugins representativos bajo `plugins/*/`.

#### Análisis inicial

* [ ] Leer el contrato actual de `UAAFRegistry`.
* [ ] Identificar consumidores actuales.
* [ ] Identificar métodos públicos existentes.
* [ ] Identificar responsabilidades duplicadas.
* [ ] Revisar la relación Registry–Kernel.
* [ ] Revisar la relación Registry–Orchestrator.
* [ ] Revisar cómo se importan actualmente los plugins.

#### Contrato canónico de plugin

* [ ] Definir una representación estable de plugin registrado.
* [ ] Registrar `plugin_id`.
* [ ] Registrar nombre.
* [ ] Registrar versión.
* [ ] Registrar tipo.
* [ ] Registrar ruta.
* [ ] Registrar módulo.
* [ ] Registrar callable `run`.
* [ ] Mantener metadatos inmutables cuando sea posible.
* [ ] Mantener representación determinista.

#### Descubrimiento dinámico

* [ ] Descubrir directorios bajo `plugins/*/`.
* [ ] Ignorar archivos y directorios no válidos.
* [ ] Validar `__init__.py`.
* [ ] Validar `<nombre>_auditor.py`.
* [ ] Importar módulos determinísticamente.
* [ ] Resolver `run(context)`.
* [ ] Aislar errores de importación.
* [ ] Producir errores claros.
* [ ] No detener todo el descubrimiento por un plugin inválido cuando el contrato permita aislarlo.

#### Registro

* [ ] Registrar plugins en orden estable.
* [ ] Rechazar `plugin_id` duplicados.
* [ ] Evitar registros duplicados.
* [ ] Permitir repetir el descubrimiento de forma idempotente.
* [ ] Mantener una fuente única de verdad.
* [ ] Diferenciar plugin descubierto, válido, registrado e inválido.

#### Consulta y selección

* [ ] Obtener plugin por `plugin_id`.
* [ ] Listar plugins registrados.
* [ ] Listar identificadores.
* [ ] Seleccionar todos.
* [ ] Seleccionar subsets.
* [ ] Resolver alias si el contrato lo requiere.
* [ ] Detectar auditores desconocidos.
* [ ] Mantener el orden solicitado cuando sea válido.
* [ ] Mantener orden canónico para `all`.

#### Integración con Orchestrator

* [ ] Inyectar o construir `UAAFRegistry`.
* [ ] Hacer que el Orchestrator consuma el Registry.
* [ ] Eliminar descubrimiento duplicado.
* [ ] Preservar selección de auditores.
* [ ] Preservar ejecución secuencial.
* [ ] Preservar agregación de resultados.
* [ ] Preservar reporting.
* [ ] Preservar errores operativos.
* [ ] Preservar códigos de salida.

#### Integración con CLI

* [ ] Preservar `--auditors`.
* [ ] Preservar `--plugins-dir`.
* [ ] Preservar `--framework-root`.
* [ ] Preservar mensajes de error.
* [ ] Preservar ayuda de argumentos.
* [ ] Preservar `run.py`.

#### Compatibilidad

* [ ] No modificar `AuditResult`.
* [ ] No modificar el contrato `run(context)`.
* [ ] No romper `execute()`.
* [ ] No romper los cinco plugins.
* [ ] No romper `ReportEngine`.
* [ ] No romper `RuntimeContext`.
* [ ] No cambiar códigos de salida.
* [ ] No cambiar formatos de reporte.
* [ ] Mantener Windows.
* [ ] Mantener Python 3.14.
* [ ] Mantener determinismo.

#### Pruebas del Registry

Crear o ampliar:

```text
09_TESTS/unit/test_registry.py
```

Casos mínimos:

* [ ] Registry vacío.
* [ ] Registro válido.
* [ ] Listado determinista.
* [ ] Consulta por ID.
* [ ] Plugin desconocido.
* [ ] ID duplicado.
* [ ] Módulo inválido.
* [ ] Directorio sin `__init__.py`.
* [ ] Directorio sin auditor.
* [ ] Auditor sin `run`.
* [ ] Error de importación.
* [ ] Descubrimiento repetido.
* [ ] Idempotencia.
* [ ] Selección de todos.
* [ ] Selección de subset.
* [ ] Orden solicitado.
* [ ] Integración Registry–Orchestrator.
* [ ] Integración con plugins reales.
* [ ] Rutas con espacios.
* [ ] Rutas Windows.
* [ ] Resultados deterministas.

#### Validación de la sesión 3.2

Ejecutar:

```powershell
python -m pytest 09_TESTS/unit/test_registry.py -v
```

Después:

```powershell
python -m pytest `
  09_TESTS/unit/test_registry.py `
  09_TESTS/unit/test_orchestrator.py `
  09_TESTS/unit/test_cli.py `
  -v
```

Finalmente:

```powershell
python -m pytest -q
```

Requisito:

```text
Los 577 tests existentes deben continuar pasando.
```

También deben pasar todas las pruebas nuevas del Registry.

#### Entregables previstos

* `08_SCRIPTS/uaaf_core/registry.py`
* `08_SCRIPTS/uaaf_core/orchestrator.py`
* `09_TESTS/unit/test_registry.py`
* Ajustes mínimos en `test_orchestrator.py`
* Ajustes mínimos en `test_cli.py` solo si son necesarios
* Actualización de `SESSION_CONTEXT.md`
* Actualización de `UAAF_SESSION_PLAN.md`

#### Criterio de finalización

La Fase 3.2 se considerará terminada cuando:

* `UAAFRegistry` sea la fuente canónica de plugins.
* El Orchestrator no duplique el descubrimiento.
* Los cinco plugins sean descubiertos y registrados.
* La selección `all` funcione.
* Los subsets funcionen.
* Los plugins inválidos generen errores controlados.
* El orden sea determinista.
* La CLI permanezca compatible.
* Los reportes permanezcan compatibles.
* Los códigos de salida permanezcan compatibles.
* La suite completa pase.

---

### Sesión 3.3 — Configuración global

#### Estado

⏳ PENDIENTE

#### Objetivo

Definir una configuración global canónica y su precedencia respecto de la CLI.

#### Checklist preliminar

* [ ] Definir contrato de `uaaf.yaml`.
* [ ] Evaluar `[tool.uaaf]` en `pyproject.toml`.
* [ ] Definir precedencia:

  1. CLI.
  2. Archivo de configuración.
  3. Valores predeterminados.
* [ ] Configurar auditores.
* [ ] Configurar exclusiones.
* [ ] Configurar formatos.
* [ ] Configurar severidades bloqueantes.
* [ ] Configurar output.
* [ ] Validar claves desconocidas.
* [ ] Agregar tests deterministas.

---

### Sesión 3.4 — Integración CI/CD

#### Estado

⏳ PENDIENTE

#### Checklist preliminar

* [ ] Crear workflow de GitHub Actions.
* [ ] Configurar Python.
* [ ] Instalar dependencias.
* [ ] Ejecutar tests.
* [ ] Ejecutar UAAF.
* [ ] Aplicar `--fail-on`.
* [ ] Publicar reportes como artifacts.
* [ ] Conservar Markdown y JSON.
* [ ] Documentar uso en pull requests.

---

### Sesión 3.5 — Exportación SARIF

#### Estado

⏳ PENDIENTE

#### Checklist preliminar

* [ ] Definir mapeo UAAF–SARIF.
* [ ] Implementar `sarif_exporter.py`.
* [ ] Mapear severidades.
* [ ] Mapear reglas.
* [ ] Mapear locations.
* [ ] Agregar `sarif` a `--output-formats`.
* [ ] Crear tests.
* [ ] Validar integración con GitHub Code Scanning.

---

### Sesión 3.6 — Documentación pública

#### Estado

⏳ PENDIENTE

#### Checklist preliminar

* [ ] Actualizar `README.md`.
* [ ] Documentar instalación.
* [ ] Documentar CLI.
* [ ] Documentar plugins.
* [ ] Documentar configuración.
* [ ] Documentar severidades.
* [ ] Documentar códigos de salida.
* [ ] Agregar ejemplos.
* [ ] Agregar arquitectura.
* [ ] Agregar contribución.
* [ ] Agregar troubleshooting.

---

## 7. Deuda técnica programada

### JSON Schemas canónicos

Estado:

⏳ PENDIENTE DE SESIÓN INDEPENDIENTE

Archivos:

* `02_SCHEMAS/audit_evidence.schema.json`
* `02_SCHEMAS/audit_finding.schema.json`
* `02_SCHEMAS/audit_profile.schema.json`
* `02_SCHEMAS/audit_report.schema.json`
* `02_SCHEMAS/audit_rule.schema.json`
* `02_SCHEMAS/audit_run.schema.json`
* `02_SCHEMAS/audit_score.schema.json`
* `02_SCHEMAS/project_manifest.schema.json`

Objetivo futuro:

* [ ] Diseñar contratos JSON Schema reales.
* [ ] Definir `$schema`.
* [ ] Definir `$id`.
* [ ] Definir versiones.
* [ ] Definir propiedades.
* [ ] Definir required.
* [ ] Definir enums.
* [ ] Definir referencias cruzadas.
* [ ] Crear fixtures válidos.
* [ ] Crear fixtures inválidos.
* [ ] Crear tests de validación.
* [ ] Integrar con Configuration Auditor.

Restricción:

> No rellenar estos archivos con `{}` únicamente para evitar findings.

---

## 8. Fases futuras

Estas fases no forman parte de la primera versión terminada y deberán planificarse después de completar la consolidación principal.

| Fase                      | Objetivo                                          | Complejidad |
| ------------------------- | ------------------------------------------------- | ----------: |
| Fase 4 — Performance      | Paralelización, caché AST y auditoría incremental |       Media |
| Fase 5 — Multi-lenguaje   | TypeScript y JavaScript                           |        Alta |
| Fase 6 — Cloud/SaaS       | Auditoría remota, historial y tendencias          |    Muy alta |
| Fase 7 — Auto-remediation | Generación de patches y pull requests             |        Alta |

---

## 9. Próxima sesión activa

**Fase**: 3.2
**Componente**: `UAAFRegistry`
**Objetivo único**: centralizar el descubrimiento, registro, validación, consulta y selección de plugins, integrándolo con el Orchestrator sin romper la CLI.

### Archivos iniciales

1. `SESSION_CONTEXT.md`.
2. `UAAF_SESSION_PLAN.md`.
3. `08_SCRIPTS/uaaf_core/registry.py`.
4. `08_SCRIPTS/uaaf_core/kernel.py`.
5. `08_SCRIPTS/uaaf_core/runtime/runtime.py`.
6. `08_SCRIPTS/uaaf_core/orchestrator.py`.
7. `08_SCRIPTS/uaaf_core/cli.py`.
8. `08_SCRIPTS/uaaf_core/audit/audit_result.py`.
9. `09_TESTS/unit/test_orchestrator.py`.
10. `09_TESTS/unit/test_cli.py`.

### Regla principal

El Registry debe convertirse en la fuente canónica de plugins sin romper:

* La CLI.
* El Orchestrator.
* El Kernel.
* `RuntimeContext`.
* `AuditResult`.
* Los cinco plugins existentes.
* Los códigos de salida.
* Los reportes.
* Los 577 tests existentes.

---

## 10. Prompt para iniciar la siguiente sesión

```text
ROL: Actúa como Arquitecto Senior de IA, Ingeniero Full Stack especialista
en LLMs, Prompt Engineer, Context Engineer y Agent Engineer. Posees
experiencia equivalente a la de un líder técnico en empresas de IA.

Contexto: Estoy continuando mi proyecto UAAF
(Universal Architecture Audit Framework).

La Fase 1 — Architecture Auditor MVP está terminada.

La Fase 2 — Extensión está terminada:
- Report Engine.
- Documentation Auditor.
- Testing Auditor.
- Configuration Auditor.
- AI Systems Auditor.
- Features semánticas avanzadas.

La Fase 3.1 — Orchestrator / CLI unificado está terminada:
- Descubrimiento automático de cinco plugins.
- Selección de todos los auditores o subsets.
- Ejecución secuencial con RuntimeContext.
- Agregación ordenada de AuditResult.
- Reportes Markdown y JSON.
- Soporte para --config.
- Soporte para --fail-on.
- Soporte para --exclude.
- Códigos de salida 0, 1 y 2.
- Compatibilidad con Windows y Python 3.14.
- 577 tests deterministas pasando.

Lee PRIMERO:
1. SESSION_CONTEXT.md
2. UAAF_SESSION_PLAN.md
3. 08_SCRIPTS/uaaf_core/registry.py
4. 08_SCRIPTS/uaaf_core/kernel.py
5. 08_SCRIPTS/uaaf_core/runtime/runtime.py
6. 08_SCRIPTS/uaaf_core/orchestrator.py
7. 08_SCRIPTS/uaaf_core/cli.py
8. 08_SCRIPTS/uaaf_core/audit/audit_result.py
9. 09_TESTS/unit/test_orchestrator.py
10. 09_TESTS/unit/test_cli.py

Objetivo de ESTA sesión:

Implementar la Fase 3.2 — Plugin Registry dinámico.

UAAFRegistry debe convertirse en la fuente canónica de descubrimiento,
registro, validación, consulta y selección de plugins.

El Orchestrator debe consumir el Registry y eliminar la lógica duplicada
de descubrimiento.

Debes preservar:
- AuditResult.
- run(context).
- execute().
- RuntimeContext.
- run.py.
- Todos los argumentos públicos de la CLI.
- Códigos de salida 0, 1 y 2.
- Reportes Markdown y JSON.
- Los cinco plugins existentes.
- Orden determinista.
- Los 577 tests existentes.

Crea o amplía 09_TESTS/unit/test_registry.py con tests deterministas.

Limitaciones:
- Uso VS Code en Windows.
- Python 3.14.
- Dame solo código listo para copiar y pegar.
- Indica el path de cada archivo.
- No modifiques componentes no relacionados.
```
