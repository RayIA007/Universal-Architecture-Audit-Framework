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
| 3.2 | Plugin Registry dinámico     | `registry.py`, integración y tests | ✅ COMPLETADA |
| 3.3 | Configuración global         | `config.py`, CLI, Orchestrator, tests | ✅ COMPLETADA         |
| 3.4 | Integración CI/CD            | GitHub Actions                         | ✅ COMPLETADA         |
| 3.5 | Exportación SARIF            | `sarif_exporter.py`, integración y tests | ✅ COMPLETADA / REMOTO OK |
| 3.6 | Documentación pública        | `README.md`, `docs/`               | ▶️ SIGUIENTE FASE |

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
* [x] Validar 634 tests pasando.
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

✅ COMPLETADA

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

* [x] Leer el contrato actual de `UAAFRegistry`.
* [x] Identificar consumidores actuales.
* [x] Identificar métodos públicos existentes.
* [x] Identificar responsabilidades duplicadas.
* [x] Revisar la relación Registry–Kernel.
* [x] Revisar la relación Registry–Orchestrator.
* [x] Revisar cómo se importan actualmente los plugins.

#### Contrato canónico de plugin

* [x] Definir una representación estable de plugin registrado.
* [x] Registrar `plugin_id`.
* [x] Registrar nombre.
* [x] Registrar versión.
* [x] Registrar tipo.
* [x] Registrar ruta.
* [x] Registrar módulo.
* [x] Registrar callable `run`.
* [x] Mantener metadatos inmutables cuando sea posible.
* [x] Mantener representación determinista.

#### Descubrimiento dinámico

* [x] Descubrir directorios bajo `plugins/*/`.
* [x] Ignorar archivos y directorios no válidos.
* [x] Validar `__init__.py`.
* [x] Validar `<nombre>_auditor.py`.
* [x] Importar módulos determinísticamente.
* [x] Resolver `run(context)`.
* [x] Aislar errores de importación.
* [x] Producir errores claros.
* [x] No detener todo el descubrimiento por un plugin inválido cuando el contrato permita aislarlo.

#### Registro

* [x] Registrar plugins en orden estable.
* [x] Rechazar `plugin_id` duplicados.
* [x] Evitar registros duplicados.
* [x] Permitir repetir el descubrimiento de forma idempotente.
* [x] Mantener una fuente única de verdad.
* [x] Diferenciar plugin descubierto, válido, registrado e inválido.

#### Consulta y selección

* [x] Obtener plugin por `plugin_id`.
* [x] Listar plugins registrados.
* [x] Listar identificadores.
* [x] Seleccionar todos.
* [x] Seleccionar subsets.
* [x] Resolver alias si el contrato lo requiere.
* [x] Detectar auditores desconocidos.
* [x] Mantener el orden solicitado cuando sea válido.
* [x] Mantener orden canónico para `all`.

#### Integración con Orchestrator

* [x] Inyectar o construir `UAAFRegistry`.
* [x] Hacer que el Orchestrator consuma el Registry.
* [x] Eliminar descubrimiento duplicado.
* [x] Preservar selección de auditores.
* [x] Preservar ejecución secuencial.
* [x] Preservar agregación de resultados.
* [x] Preservar reporting.
* [x] Preservar errores operativos.
* [x] Preservar códigos de salida.

#### Integración con CLI

* [x] Preservar `--auditors`.
* [x] Preservar `--plugins-dir`.
* [x] Preservar `--framework-root`.
* [x] Preservar mensajes de error.
* [x] Preservar ayuda de argumentos.
* [x] Preservar `run.py`.

#### Compatibilidad

* [x] No modificar `AuditResult`.
* [x] No modificar el contrato `run(context)`.
* [x] No romper `execute()`.
* [x] No romper los cinco plugins.
* [x] No romper `ReportEngine`.
* [x] No romper `RuntimeContext`.
* [x] No cambiar códigos de salida.
* [x] No cambiar formatos de reporte.
* [x] Mantener Windows.
* [x] Mantener Python 3.14.
* [x] Mantener determinismo.

#### Pruebas del Registry

Crear o ampliar:

```text
09_TESTS/unit/test_registry.py
```

Casos mínimos:

* [x] Registry vacío.
* [x] Registro válido.
* [x] Listado determinista.
* [x] Consulta por ID.
* [x] Plugin desconocido.
* [x] ID duplicado.
* [x] Módulo inválido.
* [x] Directorio sin `__init__.py`.
* [x] Directorio sin auditor.
* [x] Auditor sin `run`.
* [x] Error de importación.
* [x] Descubrimiento repetido.
* [x] Idempotencia.
* [x] Selección de todos.
* [x] Selección de subset.
* [x] Orden solicitado.
* [x] Integración Registry–Orchestrator.
* [x] Integración con plugins reales.
* [x] Rutas con espacios.
* [x] Rutas Windows.
* [x] Resultados deterministas.

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
Los 634 tests existentes deben continuar pasando.
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

✅ COMPLETADA

#### Objetivo cumplido

Definir una fuente canónica, tipada, inmutable y determinista para representar la configuración completa de una ejecución de UAAF.

#### Implementación

* [x] Crear `08_SCRIPTS/uaaf_core/config.py`.
* [x] Definir `ResolvedConfig` inmutable.
* [x] Definir `ConfigOverrides` y `UNSET` para fuentes parciales.
* [x] Centralizar valores predeterminados.
* [x] Implementar precedencia `defaults < archivo < CLI explícita`.
* [x] Diferenciar argumentos ausentes y argumentos explícitos.
* [x] Conservar los defaults visibles históricos de `argparse`.
* [x] Cargar JSON mediante biblioteca estándar.
* [x] Cargar TOML mediante `tomllib`.
* [x] Admitir `[tool.uaaf]`.
* [x] Cargar YAML/YML mediante parser limitado y determinista.
* [x] Eliminar dependencia opcional de PyYAML en la interpretación global.
* [x] Validar archivo existente, archivo regular, extensión, UTF-8 y raíz mapping.
* [x] Normalizar auditores, formatos, `fail_on` y exclusiones.
* [x] Preservar orden y eliminar duplicados de manera estable.
* [x] Resolver rutas relativas de CLI respecto del directorio de trabajo.
* [x] Resolver rutas del archivo respecto de su directorio.
* [x] Preservar aliases históricos de configuración.
* [x] Validar campos desconocidos y tipos inválidos.
* [x] Validar configuración específica por plugin mediante Registry.
* [x] Redactar claves sensibles en snapshots de diagnóstico.
* [x] Integrar `cli.py` con la configuración canónica.
* [x] Implementar `UnifiedOrchestrator.run_resolved()`.
* [x] Conservar `UnifiedOrchestrator.run()` como adaptador histórico.
* [x] Preservar `UAAFRegistry`, `RuntimeContext`, `AuditResult`, Report Engine y `run.py`.
* [x] Preservar los cinco plugins existentes.
* [x] Preservar los códigos de salida `0`, `1` y `2`.
* [x] No agregar dependencias externas.

#### Archivos

* [x] `08_SCRIPTS/uaaf_core/config.py` — nuevo.
* [x] `08_SCRIPTS/uaaf_core/cli.py` — modificado.
* [x] `08_SCRIPTS/uaaf_core/orchestrator.py` — modificado.
* [x] `09_TESTS/unit/test_global_config.py` — nuevo.
* [x] `09_TESTS/unit/test_cli.py` — ampliado.
* [x] `09_TESTS/unit/test_orchestrator.py` — ampliado.

#### Validación

* [x] 68 pruebas de configuración global pasando.
* [x] 203 pruebas relacionadas pasando.
* [x] 713 pruebas totales pasando en 12.48s.
* [x] 634 pruebas históricas preservadas.
* [x] 79 pruebas nuevas agregadas.
* [x] Cero regresiones.

#### Smoke tests

* [x] Ayuda de CLI con exit code `0`.
* [x] Ejecución de los cinco auditores sin archivo.
* [x] Ejecución de subset.
* [x] Archivo JSON.
* [x] Archivo TOML y `[tool.uaaf]` cubierto por pruebas.
* [x] Archivo YAML dentro del subconjunto soportado.
* [x] Precedencia de argumentos explícitos de CLI.
* [x] Campo desconocido con exit code `2`.
* [x] Tipo inválido con exit code `2`.
* [x] Formato no soportado con exit code `2`.
* [x] Archivo inexistente con exit code `2`.

#### Criterio de finalización

Todos los criterios de aceptación de la Fase 3.3 fueron validados. La configuración se resuelve una sola vez antes de ejecutar plugins, el Orchestrator no mantiene un loader paralelo y la suite completa permanece estable.

---

### Sesión 3.4 — Integración CI/CD

#### Estado

✅ COMPLETADA Y VALIDADA REMOTAMENTE

#### Checklist

* [x] Crear `.github/workflows/uaaf-ci.yml`.
* [x] Configurar `windows-latest` y Python `3.14.6`.
* [x] Instalar únicamente `pytest==9.1.1`.
* [x] Ejecutar `python -m pytest -q`.
* [x] Ejecutar `python run.py --help`.
* [x] Ejecutar un smoke test controlado de UAAF.
* [x] Generar y validar Markdown y JSON fuera del repositorio.
* [x] Declarar permisos mínimos.
* [x] Evitar `pull_request_target`, secretos, commits y push automáticos.
* [x] Crear 37 pruebas contractuales del workflow.
* [x] Preservar las 713 pruebas anteriores.
* [x] Validar 750 pruebas totales localmente.
* [x] Confirmar una ejecución remota exitosa.

#### Evidencia remota

```text
evento: workflow_dispatch
ejecución: #4
commit: fb3f72b
conclusión: success
```

#### Decisiones de alcance

* No se agregó caché.
* No se agregó matriz multiplataforma.
* Windows permanece como plataforma canónica validada.
* No se modificó `pyproject.toml`.
* La implementación SARIF se realizó posteriormente en la Sesión 3.5.

---

### Sesión 3.5 — Exportación SARIF

#### Estado

✅ COMPLETADA Y VALIDADA REMOTAMENTE

#### Checklist

* [x] Definir mapeo UAAF–SARIF.
* [x] Implementar `sarif_exporter.py`.
* [x] Mapear severidades.
* [x] Mapear reglas.
* [x] Mapear locations.
* [x] Agregar `sarif` a `--output-formats`.
* [x] Preservar `markdown,json` como formatos predeterminados.
* [x] Integrar SARIF con el Report Engine.
* [x] Redactar rutas absolutas del proyecto.
* [x] Cubrir rutas Windows escapadas.
* [x] Crear pruebas específicas y contractuales.
* [x] Validar determinismo.
* [x] Preparar carga mediante `upload-sarif@v4`.
* [x] Proteger pull requests provenientes de forks.
* [x] Validar ejecución remota.
* [x] Validar GitHub Code Scanning.

---

### Sesión 3.6 — Documentación pública

#### Estado

▶️ SIGUIENTE FASE

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

**Fase**: 3.6 — Documentación pública
**Componente inmediato**: `README.md` y `docs/`
**Estado**: lista para iniciar; Fase 3.5 cerrada y validada remotamente

### Evidencia que habilita la Fase 3.6

```text
Fase 3.5 local: 820 passed
primer intento remoto: run #5, commit 77865f5, failure
commit correctivo: 6242472
validación remota final: run #6, success
Upload SARIF to GitHub Code Scanning: success
Post Upload SARIF to GitHub Code Scanning: success
```

### Próxima implementación

La siguiente sesión técnica será:

```text
Fase 3.6 — Documentación pública
```

Debe preservar las 820 pruebas actuales, Markdown, JSON, SARIF, configuración global, Registry, RuntimeContext, AuditResult y los códigos de salida `0`, `1` y `2`.

---

## 10. Prompt para iniciar la siguiente sesión

```text
ROL: Actúa como Arquitecto Senior de Software e IA, Ingeniero Full Stack especialista en Python, documentación técnica, GitHub Actions, SARIF 2.1.0, análisis estático, sistemas de plugins, Prompt Engineer, Context Engineer y Agent Engineer.

Contexto: Estoy continuando el proyecto UAAF — Universal Architecture Audit Framework.

Estado validado:
- Fases 1 y 2 completadas.
- Fase 3.1 — Orchestrator / CLI unificado completada.
- Fase 3.2 — Plugin Registry dinámico completada.
- Fase 3.3 — Configuración global completada.
- Fase 3.4 — Integración CI/CD completada y validada remotamente.
- Evidencia 3.4: workflow_dispatch, ejecución #4, commit fb3f72b, conclusión success.
- Fase 3.5 — Exportación SARIF COMPLETADA Y VALIDADA REMOTAMENTE.
- 53 pruebas específicas SARIF.
- 286 pruebas relacionadas de la validación inicial.
- 820 pruebas totales pasando después del hotfix.
- Markdown, JSON y SARIF funcionan conjuntamente.
- Redacción de rutas validada: 0 leaks en mensajes y locations.
- Determinismo SARIF confirmado.
- Primer intento remoto de 3.5: ejecución #5 sobre 77865f5, conclusion failure porque GitHub Code Scanning rechazó resultados SARIF sin locations.
- Corrección: commit 6242472; los findings sin ubicación exportable se conservan en el resultado canónico y Markdown/JSON, pero se omiten de results[] SARIF.
- Validación remota final de 3.5: ejecución #6 sobre 62424728d1609233d933207e1a58747153f304bc, conclusion success.
- Upload SARIF to GitHub Code Scanning: success.
- Post Upload SARIF to GitHub Code Scanning: success.
- UAAFRegistry, ResolvedConfig, UnifiedOrchestrator, RuntimeContext, AuditResult, Report Engine, run.py y los cinco plugins permanecen compatibles.

Lee primero:
1. SESSION_CONTEXT.md
2. UAAF_SESSION_PLAN.md
3. README.md
4. .github/workflows/uaaf-ci.yml
5. 08_SCRIPTS/uaaf_core/cli.py
6. 08_SCRIPTS/uaaf_core/config.py
7. 08_SCRIPTS/uaaf_core/orchestrator.py
8. 08_SCRIPTS/uaaf_core/registry.py
9. 08_SCRIPTS/uaaf_core/reporting/report_engine.py
10. 08_SCRIPTS/uaaf_core/reporting/sarif_exporter.py

Objetivo único de ESTA sesión:
Implementar la Fase 3.6 — Documentación pública.

La documentación debe reflejar únicamente el comportamiento real y validado del repositorio. Actualiza README.md y la documentación necesaria en docs/ para cubrir, como mínimo: propósito y arquitectura de UAAF, requisitos e instalación, uso de la CLI, configuración global y precedencia, plugins disponibles, reporting Markdown/JSON/SARIF, severidades, códigos de salida, CI/CD y Code Scanning, ejemplos reproducibles, troubleshooting y contribución.

Preserva las 820 pruebas actuales y todos los contratos públicos. No avances a paralelización, caché AST, auditoría incremental, dashboard, API, Docker, despliegues ni auto-remediation.
```

---

<!-- UAAF_PHASE_3_2_SESSION_PLAN_START -->
## Registro de cierre — Fase 3.2

### Estado

✅ **COMPLETADA el 2026-08-04**.

### Entregables completados

* [x] `08_SCRIPTS/uaaf_core/registry.py` convertido en Registry canónico de plugins.
* [x] `08_SCRIPTS/uaaf_core/orchestrator.py` integrado mediante delegación e inyección de dependencias.
* [x] `09_TESTS/unit/test_registry.py` creado con 57 pruebas nuevas.
* [x] Descubrimiento de los cinco plugins reales.
* [x] Selección `all` y subsets.
* [x] Detección de plugins inválidos, IDs duplicados, aliases ambiguos y nombres desconocidos.
* [x] Contratos de CLI, `RuntimeContext`, `AuditResult`, Report Engine y `run.py` preservados.
* [x] Reportes Markdown y JSON preservados.
* [x] Códigos de salida `0`, `1` y `2` preservados.
* [x] Cero regresiones.

### Resultado final validado

```text
124 pruebas relacionadas pasando
634 pruebas totales pasando en 11.56s
```

Composición:

* 577 pruebas anteriores preservadas.
* 57 pruebas nuevas agregadas.

Smoke tests:

```text
--auditors all
5 auditores
1053 findings
Markdown y JSON generados

--auditors architecture,testing,configuration
3 auditores
680 findings
Markdown y JSON generados
```

### Siguiente objetivo

## Fase 3.3 — Configuración global

Objetivo único: implementar una configuración global canónica y definir su precedencia respecto de los argumentos de la CLI.

La precedencia requerida será:

```text
CLI > archivo de configuración > valores predeterminados
```

Debe analizarse e implementar, sin adelantar fases posteriores:

* Contrato de `uaaf.yaml`.
* Posible soporte de `[tool.uaaf]` en `pyproject.toml`.
* Auditores seleccionados.
* Exclusiones.
* Formatos de salida.
* Severidades de `--fail-on`.
* Directorio de salida.
* Validación de claves desconocidas y valores inválidos.
* Errores claros y deterministas con código de salida `2`.
* Integración con CLI, Orchestrator, `RuntimeContext` y `UAAFRegistry`.
* Compatibilidad hacia atrás cuando no exista archivo de configuración.
* Preservación de los 634 tests existentes.

### Archivos que deben revisarse primero en la Fase 3.3

1. `SESSION_CONTEXT.md`.
2. `UAAF_SESSION_PLAN.md`.
3. `08_SCRIPTS/uaaf_core/cli.py`.
4. `08_SCRIPTS/uaaf_core/orchestrator.py`.
5. `08_SCRIPTS/uaaf_core/registry.py`.
6. `08_SCRIPTS/uaaf_core/runtime/runtime.py`.
7. `08_SCRIPTS/uaaf_core/runtime/runtime_context.py`.
8. `08_SCRIPTS/uaaf_core/models/profile.py`.
9. `09_TESTS/unit/test_cli.py`.
10. `09_TESTS/unit/test_orchestrator.py`.
11. `09_TESTS/unit/test_registry.py`.

### Prompt de continuidad

```text
ROL: Actúa como Arquitecto Senior de Software e IA, Ingeniero Full Stack especialista en Python, LLMs, sistemas de plugins y configuración, Prompt Engineer, Context Engineer y Agent Engineer.

Contexto: Estoy continuando el proyecto UAAF — Universal Architecture Audit Framework.

Estado validado:
- Fase 1 completada.
- Fase 2 completada.
- Fase 3.1 — Orchestrator / CLI unificado completada.
- Fase 3.2 — Plugin Registry dinámico completada.
- UAAFRegistry es la fuente canónica de plugins.
- El Orchestrator delega descubrimiento y selección al Registry.
- Los cinco plugins reales funcionan.
- 634 tests deterministas pasando.

Objetivo único de ESTA sesión:
Implementar la Fase 3.3 — Configuración global.

Define una configuración canónica para UAAF y la precedencia exacta:
CLI > archivo de configuración > valores predeterminados.

Lee primero SESSION_CONTEXT.md, UAAF_SESSION_PLAN.md, cli.py, orchestrator.py, registry.py, los componentes de runtime y las pruebas relacionadas. Conserva todos los contratos públicos, los cinco plugins, los reportes, los códigos de salida y los 634 tests existentes. No avances a GitHub Actions, SARIF, paralelización, caché, auditoría incremental ni auto-remediation.
```
<!-- UAAF_PHASE_3_2_SESSION_PLAN_END -->

<!-- UAAF_PHASE_3_3_SESSION_PLAN_START -->
## Registro de cierre — Fase 3.3

### Estado

✅ **COMPLETADA el 2026-08-05**.

### Entregables completados

* [x] Modelo canónico e inmutable de configuración global.
* [x] Cargadores JSON, TOML y YAML/YML limitado sin dependencias externas.
* [x] Soporte de `[tool.uaaf]`.
* [x] Precedencia determinista `defaults < archivo < CLI explícita`.
* [x] Integración con CLI, Orchestrator, Registry, RuntimeContext y Report Engine.
* [x] Construcción histórica del Orchestrator preservada.
* [x] Validaciones y errores deterministas con código de salida `2`.
* [x] Configuración específica por plugin aislada y validada.
* [x] Contratos públicos y cinco plugins preservados.
* [x] Cero dependencias externas nuevas.
* [x] Cero regresiones.

### Resultado final validado

```text
68 pruebas de configuración global pasando
203 pruebas relacionadas pasando
713 pruebas totales pasando en 12.48s
```

Composición:

* 634 pruebas anteriores preservadas.
* 79 pruebas nuevas agregadas.

### Smoke tests

```text
--help: exit code 0
sin config: 5 auditores, Markdown y JSON, exit code 0
subset: 3 auditores, Markdown y JSON, exit code 0
JSON: exit code 0
TOML: exit code 0
YAML: exit code 0
precedencia: PRECEDENCE OK
campo desconocido: exit code 2
tipo inválido: exit code 2
extensión no soportada: exit code 2
archivo inexistente: exit code 2
```

### Siguiente objetivo

## Fase 3.4 — Integración CI/CD

Objetivo único: crear una integración de GitHub Actions que ejecute pytest y UAAF, aplique una política explícita de `--fail-on`, y publique reportes Markdown/JSON como artifacts, sin alterar la configuración global ni avanzar a SARIF.
<!-- UAAF_PHASE_3_3_SESSION_PLAN_END -->

<!-- UAAF_PHASE_3_4_SESSION_PLAN_START -->
## Registro de implementación y validación — Fase 3.4

### Estado

✅ **IMPLEMENTADA Y VALIDADA LOCALMENTE el 2026-08-06**.
✅ **VALIDACIÓN REMOTA COMPLETADA CON ÉXITO**.

```text
evento: workflow_dispatch
ejecución: #4
commit: fb3f72b
conclusión: success
```

### Entregables

* [x] `.github/workflows/uaaf-ci.yml`.
* [x] `09_TESTS/unit/test_ci_workflow.py`.
* [x] Eventos `push`, `pull_request` y `workflow_dispatch`.
* [x] Permisos mínimos.
* [x] Runner `windows-latest`.
* [x] Python `3.14.6`.
* [x] `pytest==9.1.1`.
* [x] Suite completa.
* [x] Ayuda de CLI.
* [x] Smoke test controlado.
* [x] Markdown y JSON.
* [x] Concurrencia y timeout de 30 minutos.
* [x] Sin secretos ni escrituras al repositorio.
* [x] Ejecución remota exitosa confirmada.

### Resultados locales

```text
37 passed in 0.78s
240 passed in 5.75s
750 passed in 14.72s
```

### Compatibilidad

* [x] 713 pruebas anteriores preservadas.
* [x] 37 pruebas nuevas.
* [x] Cero regresiones.
* [x] CLI y configuración global preservadas.
* [x] Registry y Orchestrator preservados.
* [x] RuntimeContext, AuditResult y Report Engine preservados.
* [x] Cinco plugins preservados.
* [x] Códigos de salida `0`, `1` y `2` preservados.
* [x] Sin dependencias productivas nuevas.

### Cierre remoto

La ejecución remota `#4` del workflow `UAAF CI` concluyó con `success` sobre el commit `fb3f72b`.
<!-- UAAF_PHASE_3_4_SESSION_PLAN_END -->

<!-- UAAF_PHASE_3_5_SESSION_PLAN_START -->
## Registro de implementación y validación final — Fase 3.5

### Estado

✅ **IMPLEMENTADA Y VALIDADA LOCALMENTE el 2026-08-06**.
✅ **VALIDADA REMOTAMENTE Y CERRADA el 2026-08-07**.

### Entregables

* [x] `08_SCRIPTS/uaaf_core/reporting/sarif_exporter.py`.
* [x] `09_TESTS/unit/test_sarif_exporter.py`.
* [x] Integración opt-in con CLI, configuración global y Report Engine.
* [x] SARIF `2.1.0` con schema oficial Errata 01.
* [x] Reglas deduplicadas y ordenadas.
* [x] Severidades UAAF mapeadas a niveles SARIF.
* [x] Locations relativas y POSIX.
* [x] Redacción de rutas absolutas.
* [x] Compatibilidad con rutas Windows escapadas.
* [x] Markdown y JSON preservados.
* [x] Códigos de salida `0`, `1` y `2` preservados.
* [x] Workflow preparado con `github/codeql-action/upload-sarif@v4`.
* [x] Permiso acotado `security-events: write`.
* [x] Protección para pull requests de forks.
* [x] Pruebas específicas, contractuales y de integración.
* [x] Determinismo validado.
* [x] Confirmar ejecución remota exitosa.
* [x] Confirmar carga SARIF aceptada por GitHub Code Scanning.

### Resultados reales

```text
53 passed in 0.50s
286 passed in 3.13s
820 passed in 10.77s
```

### Validación SARIF

```text
1 auditor
3 findings
1 archivo SARIF
MessagePathLeaks: 0
LocationPathLeaks: 0
Identical: True
```

SHA-256 determinista:

```text
26B549B9F432F71B22B89E2267338D361622A2410000E1B88A73D1B02849291B
```

### Corrección y evidencia remota

Primer intento:

```text
run: #5
commit: 77865f5
status: completed
conclusion: failure
causa: GitHub Code Scanning rechazó resultados SARIF sin locations
```

Corrección:

```text
commit: 6242472
comportamiento: findings sin ubicación exportable segura se omiten de results[] SARIF
resultado canónico UAAF: preservado
Markdown/JSON: preservados
ubicaciones inventadas: ninguna
```

Validación local posterior al hotfix:

```text
53 passed in 0.96s
820 passed in 26.97s
```

Validación remota final:

```text
run: #6
commit: 62424728d1609233d933207e1a58747153f304bc
status: completed
conclusion: success
Upload SARIF to GitHub Code Scanning: success
Post Upload SARIF to GitHub Code Scanning: success
```

### Compatibilidad

* [x] 750 pruebas anteriores preservadas.
* [x] 70 pruebas nuevas.
* [x] Cero regresiones.
* [x] CLI pública preservada.
* [x] Configuración global preservada.
* [x] Registry y Orchestrator preservados.
* [x] RuntimeContext y AuditResult preservados.
* [x] Cinco plugins preservados.
* [x] Sin dependencias productivas nuevas.

### Cierre

```text
implementación local: completada
validación remota SARIF: completada
GitHub Code Scanning: success
Fase 3.5: COMPLETADA Y VALIDADA REMOTAMENTE
siguiente fase: 3.6 — Documentación pública
```
<!-- UAAF_PHASE_3_5_SESSION_PLAN_END -->
