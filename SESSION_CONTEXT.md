# UAAF — SESSION CONTEXT

## 1. Estado actual del proyecto

> Última actualización: 2026-08-07
> Última fase completada y validada remotamente: Fase 3.5 — Exportación SARIF
> Validación remota de la Fase 3.5: completada con éxito
> Próxima fase: Fase 3.6 — Documentación pública

---

### ✅ FASE 1 COMPLETADA — Architecture Auditor MVP

La primera fase estableció el contrato principal de auditoría arquitectónica y su integración con el runtime de UAAF.

* **Suite A — Contrato y configuración**: completada.
* **Suite B — Descubrimiento e índice**: completada.
* **Suite C — Imports y grafo**: completada.
* **Suite D — Reglas arquitectónicas**: completada.
* **Suite E — Robustez**: completada.
* **Suite F — Integración con Runtime Pipeline**: completada.
* **Suite L — Features semánticas avanzadas**: completada.
* **Architecture Auditor**: versión 1.6.0 estable y canónica.
* **Resultado conjunto del Architecture Auditor**: 232 tests pasando.

### ✅ FASE 2 COMPLETADA — Extensión de auditores y reporting

#### 2.1 Report Engine

* Generación de reportes Markdown.
* Generación de reportes JSON.
* Serialización determinista.
* Validación de resultados canónicos.
* 33 tests deterministas.

#### 2.2 Nuevos plugins

* ✅ Documentation Auditor.
* ✅ Testing Auditor.
* ✅ Configuration Auditor.
* ✅ AI Systems Auditor.
* ✅ Integración con el contrato canónico `AuditResult`.

#### 2.3 Features semánticas avanzadas

* Complejidad ciclomática.
* Detección conservadora de dead code.
* Métricas avanzadas de mantenibilidad.
* Análisis de funciones síncronas y asíncronas.
* Métricas por módulo.
* Resultados ordenados y deterministas.
* Findings `ARCH-COMPLEX-001` y `ARCH-DEAD-001`.
* Compatibilidad preservada con las Suites A–F.

### 🚧 FASE 3 EN CURSO — Consolidación y CLI

* ✅ **3.1 Orchestrator / CLI unificado — COMPLETADA**.
* **3.2 Plugin Registry dinámico — ✅ COMPLETADA**.
* **3.3 Configuración global — ✅ COMPLETADA**.
* ✅ **3.4 Integración CI/CD — COMPLETADA Y VALIDADA REMOTAMENTE**.
* ✅ **3.5 Exportación SARIF — COMPLETADA Y VALIDADA REMOTAMENTE**.
* ▶️ **3.6 Documentación pública — SIGUIENTE FASE**.

### Validación acumulada

* **820 tests deterministas, todos pasando localmente**.
* **750 pruebas anteriores preservadas y 70 pruebas nuevas agregadas en la Fase 3.5**.
* **Fase 3.4 validada remotamente mediante `workflow_dispatch`: ejecución #4, commit `fb3f72b`, conclusión `success`**.
* **Fase 3.5 validada remotamente: ejecución #6, commit `62424728d1609233d933207e1a58747153f304bc`, conclusión `success`; los pasos `Upload SARIF to GitHub Code Scanning` y `Post Upload SARIF to GitHub Code Scanning` finalizaron en `success`**.
* Plataforma validada:

  * Windows.
  * Python 3.14.6.
  * pytest 9.1.1.
* Cinco plugins ejecutados correctamente.
* Sin errores internos de plugins.
* Sin regresiones detectadas en las fases anteriores.

---

## 2. Archivos clave del proyecto

| Archivo                                              |   Versión | Descripción                                                     |
| ---------------------------------------------------- | --------: | --------------------------------------------------------------- |
| `run.py`                                             |         — | Entry point principal; delega en `uaaf_core.cli.main()`         |
| `08_SCRIPTS/uaaf_core/audit/audit_result.py`         |  Canónico | Contrato principal de resultados y findings                     |
| `08_SCRIPTS/uaaf_core/runtime/runtime.py`            |  Canónico | Runtime y construcción del contexto de ejecución                |
| `08_SCRIPTS/uaaf_core/kernel.py`                     |  Canónico | Coordinación de componentes centrales                           |
| `08_SCRIPTS/uaaf_core/registry.py`                   | Existente | Registry que será consolidado en la Fase 3.2                    |
| `08_SCRIPTS/uaaf_core/orchestrator.py`               |     1.0.0 | Descubrimiento, selección, ejecución y consolidación de plugins |
| `08_SCRIPTS/uaaf_core/cli.py`                        |     1.0.0 | CLI unificada, configuración y códigos de salida                |
| `08_SCRIPTS/uaaf_core/config.py`                     |     1.0.0 | Configuración global canónica, carga, precedencia y validación      |
| `08_SCRIPTS/uaaf_core/reporting/report_engine.py`    |     1.1.0 | Motor de reportes Markdown, JSON y SARIF                        |
| `08_SCRIPTS/uaaf_core/reporting/sarif_exporter.py`   |     1.0.0 | Exportador SARIF 2.1.0 determinista y seguro                    |
| `08_SCRIPTS/uaaf_core/reporting/__init__.py`         |         — | Exports del paquete de reporting                                |
| `plugins/architecture/architecture_auditor.py`       |     1.6.0 | Auditor arquitectónico y análisis semántico                     |
| `plugins/architecture/__init__.py`                   |         — | Bootstrap del Architecture Auditor                              |
| `plugins/documentation/documentation_auditor.py`     |     1.0.0 | Auditor de documentación compatible con Python 3.14             |
| `plugins/documentation/__init__.py`                  |         — | Bootstrap del Documentation Auditor                             |
| `plugins/testing/testing_auditor.py`                 |     1.0.0 | Auditor de testing                                              |
| `plugins/testing/__init__.py`                        |         — | Bootstrap del Testing Auditor                                   |
| `plugins/configuration/configuration_auditor.py`     |     1.0.0 | Auditor de configuración                                        |
| `plugins/configuration/__init__.py`                  |         — | Bootstrap del Configuration Auditor                             |
| `plugins/ai_systems/ai_systems_auditor.py`           |     1.0.0 | Auditor estático de sistemas de IA y LLMs                       |
| `plugins/ai_systems/__init__.py`                     |         — | Bootstrap del AI Systems Auditor                                |
| `09_TESTS/unit/test_architecture_contract.py`        |         — | Suite A: contrato y configuración                               |
| `09_TESTS/unit/test_architecture_discovery.py`       |         — | Suite B: descubrimiento e índice                                |
| `09_TESTS/unit/test_architecture_imports.py`         |         — | Suite C: imports y grafo                                        |
| `09_TESTS/unit/test_architecture_rules.py`           |         — | Suite D: reglas arquitectónicas                                 |
| `09_TESTS/unit/test_architecture_robustness.py`      |         — | Suite E: robustez                                               |
| `09_TESTS/integration/test_architecture_pipeline.py` |         — | Suite F: integración                                            |
| `09_TESTS/unit/test_report_engine.py`                |         — | Suite G: Report Engine                                          |
| `09_TESTS/unit/test_sarif_exporter.py`               |         — | 53 pruebas específicas del exportador SARIF                     |
| `09_TESTS/unit/test_documentation_auditor.py`        |         — | Suite H: Documentation Auditor, 57 tests                        |
| `09_TESTS/unit/test_testing_auditor.py`              |         — | Suite I: Testing Auditor                                        |
| `09_TESTS/unit/test_configuration_auditor.py`        |         — | Suite J: Configuration Auditor                                  |
| `09_TESTS/unit/test_ai_systems_auditor.py`           |         — | Suite K: AI Systems Auditor                                     |
| `09_TESTS/unit/test_architecture_semantics.py`       |         — | Suite L: features semánticas avanzadas                          |
| `09_TESTS/unit/test_orchestrator.py`                 |         — | Pruebas deterministas del Orchestrator                          |
| `09_TESTS/unit/test_cli.py`                          |         — | Pruebas deterministas de la CLI                                 |
| `.github/workflows/uaaf-ci.yml`                      |     1.1.0 | CI seguro y carga SARIF hacia GitHub Code Scanning              |
| `09_TESTS/unit/test_ci_workflow.py`                  |         — | Pruebas contractuales de CI/CD y carga SARIF                    |

---

## 3. Configuración técnica

* Sistema operativo validado: Windows.
* Python validado: 3.14.6.
* pytest validado: 9.1.1.
* Rutas de findings normalizadas a formato POSIX.
* `uaaf_core` se importa desde `08_SCRIPTS/uaaf_core/`.
* Bootstrap mediante inserción controlada de `08_SCRIPTS` en `sys.path`.
* Análisis estático basado principalmente en AST.
* Uso de nodos AST canónicos compatibles con Python 3.14.
* Tests aislados mediante `TemporaryDirectory` y `tmp_path`.
* Resultados ordenados y deterministas.
* Entry point principal: `python run.py`.
* Reportes generados en `07_OUTPUTS/`.
* Contrato público principal: `run(context) -> dict[str, Any]`.
* Wrapper público de plugins: `execute()`.
* No se deben añadir dependencias externas sin una justificación explícita.

---

## 4. Contratos y arquitectura que deben preservarse

### 4.1 AuditResult

Todos los plugins deben devolver un resultado compatible con el contrato canónico definido en:

```text
08_SCRIPTS/uaaf_core/audit/audit_result.py
```

El resultado debe conservar, según corresponda:

* `plugin_id`.
* `status`.
* `summary`.
* `findings`.
* `metrics`.
* `errors`.
* Metadatos de ejecución.
* Rutas relativas normalizadas.
* Orden determinista.

### 4.2 Findings

Cada finding debe conservar una estructura compatible con el contrato canónico y contener los datos necesarios para:

* Identificar el plugin emisor.
* Identificar la regla o código.
* Representar la severidad.
* Describir el problema.
* Localizar el archivo o elemento afectado.
* Incluir detalles deterministas.
* Ser serializado correctamente a Markdown y JSON.

### 4.3 RuntimeContext

El Orchestrator debe construir y distribuir un contexto canónico de ejecución que preserve:

* Ruta del proyecto.
* Configuración global.
* Directorios ignorados.
* Metadatos del framework.
* Parámetros necesarios por los plugins.
* Compatibilidad con el contrato `run(context)` existente.

### 4.4 Determinismo

Debe preservarse:

* Orden estable de descubrimiento.
* Orden estable de ejecución.
* Orden estable de plugins seleccionados.
* Orden estable de findings.
* Rutas relativas POSIX en resultados.
* Reportes reproducibles salvo por datos deliberadamente variables, como timestamps.

---

## 5. Plugins disponibles

### Architecture Auditor

Ubicación:

```text
plugins/architecture/architecture_auditor.py
```

Capacidades principales:

* Descubrimiento de módulos Python.
* Índice de imports.
* Grafo de dependencias.
* Detección de ciclos.
* Validación de capas.
* Imports prohibidos.
* Validación de `__init__.py`.
* Complejidad ciclomática.
* Dead code conservador.
* Métricas de mantenibilidad.

Códigos principales:

| Código               | Regla                              | Severidad |
| -------------------- | ---------------------------------- | --------- |
| `ARCH-CYCLE-001`     | Dependencia circular               | `ERROR`   |
| `ARCH-LAYER-001`     | Violación de capas                 | `ERROR`   |
| `ARCH-FORBIDDEN-001` | Import prohibido                   | `ERROR`   |
| `ARCH-INIT-001`      | `__init__.py` faltante             | `WARNING` |
| `ARCH-COMPLEX-001`   | Complejidad superior al umbral     | `WARNING` |
| `ARCH-DEAD-001`      | Código potencialmente no utilizado | `WARNING` |

### Documentation Auditor

Ubicación:

```text
plugins/documentation/documentation_auditor.py
```

Capacidades principales:

* Detección de README faltante.
* Validación de documentación de paquetes.
* Docstrings de módulos.
* Docstrings de clases.
* Docstrings de funciones.
* Detección de placeholders.
* Métricas de cobertura documental.

Compatibilidad:

* Corregido para Python 3.14.
* Usa `ast.Constant` como representación canónica de strings.
* No debe usar `ast.Str`.

### Testing Auditor

Ubicación:

```text
plugins/testing/testing_auditor.py
```

Capacidades principales:

* Descubrimiento de archivos de pruebas.
* Identificación de módulos sin cobertura estructural.
* Detección de patrones problemáticos.
* Análisis conservador de estructura de testing.
* Métricas de archivos y funciones de prueba.

### Configuration Auditor

Ubicación:

```text
plugins/configuration/configuration_auditor.py
```

Capacidades principales:

* Descubrimiento de archivos de configuración.
* Validación sintáctica de JSON.
* Validación sintáctica de YAML cuando esté disponible.
* Validación de TOML.
* Detección de configuraciones problemáticas.
* Detección de archivos vacíos o inválidos.

Código relevante:

| Código               | Regla                                          | Severidad |
| -------------------- | ---------------------------------------------- | --------- |
| `CONFIG-INVALID-001` | Archivo de configuración con sintaxis inválida | `ERROR`   |

### AI Systems Auditor

Ubicación:

```text
plugins/ai_systems/ai_systems_auditor.py
```

Capacidades principales:

* Imports de librerías de IA.
* Secretos o API keys hardcodeados.
* Prompts hardcodeados.
* Llamadas a APIs sin manejo de excepciones.
* Evaluación insegura de outputs.
* Configuración de generación insegura.
* Modelos deprecated.
* Agentes o RAG sin safeguards.

Códigos principales:

| Código          | Regla                                | Severidad  |
| --------------- | ------------------------------------ | ---------- |
| `AI-IMPORT-001` | Librería de IA detectada             | `INFO`     |
| `AI-SECRET-001` | API key o secreto hardcodeado        | `CRITICAL` |
| `AI-PROMPT-001` | Prompt hardcodeado                   | `WARNING`  |
| `AI-ERROR-001`  | API de IA sin manejo de excepciones  | `ERROR`    |
| `AI-EVAL-001`   | Evaluación insegura de output        | `CRITICAL` |
| `AI-TEMP-001`   | Configuración de generación insegura | `WARNING`  |
| `AI-MODEL-001`  | Modelo deprecated                    | `WARNING`  |
| `AI-SAFETY-001` | Agente o RAG sin safeguards          | `WARNING`  |

---

## 6. Resultado de la Fase 3.1

### 6.1 Orchestrator unificado

Archivo:

```text
08_SCRIPTS/uaaf_core/orchestrator.py
```

Funcionalidad implementada:

* Descubrimiento automático de plugins bajo `plugins/*/`.
* Reconocimiento del patrón:

  * Directorio de plugin.
  * Archivo `__init__.py`.
  * Archivo `<nombre>_auditor.py`.
* Orden determinista de descubrimiento.
* Selección de todos los plugins.
* Selección de subsets.
* Validación de auditores desconocidos.
* Ejecución secuencial.
* Propagación de un contexto canónico.
* Agregación ordenada de resultados.
* Conservación de errores por plugin.
* Consolidación de findings.
* Integración con `ReportEngine`.

### 6.2 CLI unificada

Archivo:

```text
08_SCRIPTS/uaaf_core/cli.py
```

Entry point:

```text
run.py
```

Argumentos públicos implementados:

```text
--project-path
--auditors
--output-formats
--config
--fail-on
--exclude
--output-dir
--plugins-dir
--framework-root
```

Ejemplo principal:

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --output-formats markdown,json
```

Subset de auditores:

```powershell
python run.py `
  --project-path . `
  --auditors architecture,testing,configuration `
  --output-formats markdown,json
```

Ejecución con exclusiones y severidades bloqueantes:

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --output-formats markdown,json `
  --fail-on critical,error `
  --exclude .git,.venv,node_modules,dist,build,07_OUTPUTS,09_TESTS,.pytest_cache,__pycache__,02_SCHEMAS
```

### 6.3 Códigos de salida

* `0`: ejecución correcta sin findings de severidades configuradas en `--fail-on`.
* `1`: existen findings cuya severidad coincide con `--fail-on`.
* `2`: error operativo, de configuración, descubrimiento o ejecución.

### 6.4 Reporting consolidado

El Orchestrator genera:

* Reporte Markdown.
* Reporte JSON.
* Nombre con timestamp.
* Escritura automática en `07_OUTPUTS/`.
* Lista ordenada de resultados por plugin.
* Findings consolidados.
* Métricas y errores por plugin.

Patrón de nombre:

```text
YYYYMMDD_HHMMSS_uaaf-orchestrator_consolidated.md
YYYYMMDD_HHMMSS_uaaf-orchestrator_consolidated.json
```

### 6.5 Correcciones realizadas durante la validación

#### Inferencia de la raíz del framework

Se corrigió la inferencia de la raíz del repositorio en Windows.

La raíz debe resolverse desde:

```python
Path(__file__).resolve().parents[2]
```

Esto evita que la CLI intente descubrir plugins en:

```text
C:\plugins
```

#### Compatibilidad del Documentation Auditor con Python 3.14

Se eliminó el acceso a:

```python
ast.Str
```

Se conserva únicamente la representación canónica:

```python
ast.Constant
```

Se agregó una prueba de regresión para expresiones AST que no contienen strings.

### 6.6 Validación final

* Suite de Documentation Auditor: 57 tests pasando.
* Suite completa del repositorio: 634 tests pasando.
* Cinco plugins descubiertos.
* Cinco plugins ejecutados.
* Cero errores internos de plugins.
* Markdown generado correctamente.
* JSON generado correctamente.
* `--exclude` validado.
* `--fail-on` validado.
* Códigos de salida `0`, `1` y `2` comprobados.

Validación operativa final:

* 5 auditores.
* 941 findings de severidad `warning`.
* 0 findings `critical`.
* 0 findings `error`.
* Exit code `0`.

---

## 7. Deuda técnica conocida

### 7.1 JSON Schemas pendientes

Los siguientes archivos de `02_SCHEMAS/` son placeholders de cero bytes:

* `audit_evidence.schema.json`
* `audit_finding.schema.json`
* `audit_profile.schema.json`
* `audit_report.schema.json`
* `audit_rule.schema.json`
* `audit_run.schema.json`
* `audit_score.schema.json`
* `project_manifest.schema.json`

El Configuration Auditor los reporta correctamente como:

```text
CONFIG-INVALID-001
```

con severidad:

```text
ERROR
```

No deben rellenarse con `{}` únicamente para silenciar el auditor.

Su implementación debe realizarse en una sesión independiente dedicada a:

* Contratos JSON Schema canónicos.
* Relaciones entre schemas.
* Fixtures válidos.
* Fixtures inválidos.
* Validación cruzada.
* Tests deterministas.

### 7.2 Fixtures de secretos en pruebas

`09_TESTS` contiene secretos simulados utilizados deliberadamente para probar el AI Systems Auditor.

No representan credenciales reales.

Cuando `09_TESTS` forma parte de la auditoría, el AI Systems Auditor puede producir findings `AI-SECRET-001` de severidad `CRITICAL`.

Para una auditoría operativa del código productivo se recomienda excluir `09_TESTS`.

### 7.3 Exclusiones operativas temporales

Para la validación operativa de la Fase 3.1 se utilizaron:

* `.git`
* `.venv`
* `node_modules`
* `dist`
* `build`
* `07_OUTPUTS`
* `09_TESTS`
* `.pytest_cache`
* `__pycache__`
* `02_SCHEMAS`

Estas exclusiones no eliminan la deuda técnica. Únicamente permiten diferenciar:

* Fallos del Orchestrator.
* Findings deliberados de fixtures.
* Archivos placeholder todavía no implementados.
* Hallazgos reales del código productivo.

---

## 8. Fase 3 — Roadmap

| #   | Objetivo                     | Archivo(s) previstos               | Estado               |
| --- | ---------------------------- | ---------------------------------- | -------------------- |
| 3.1 | Orchestrator / CLI unificado | `orchestrator.py`, `cli.py`, tests | ✅ COMPLETADA         |
| 3.2 | Plugin Registry dinámico     | `registry.py`, integración y tests | ✅ COMPLETADA |
| 3.3 | Configuración global         | `config.py`, CLI, Orchestrator, tests | ✅ COMPLETADA         |
| 3.4 | Integración CI/CD            | `.github/workflows/uaaf-ci.yml`, tests | ✅ COMPLETADA / REMOTO OK |
| 3.5 | Exportación SARIF            | `sarif_exporter.py`, integración y tests | ✅ COMPLETADA / REMOTO OK |
| 3.6 | Documentación pública        | `README.md`, `docs/`               | ▶️ SIGUIENTE FASE |

---

## 9. Próxima fase — Fase 3.6

### Estado actual

La Fase 3.5 — Exportación SARIF está completada y validada tanto local como remotamente.

La primera ejecución remota de la Fase 3.5 detectó una incompatibilidad real con GitHub Code Scanning: algunos findings sin una ubicación exportable producían resultados SARIF sin `locations`. GitHub rechazó esa carga en la ejecución #5.

La corrección conserva los findings en el resultado canónico de UAAF y en Markdown/JSON, pero omite de `results[]` SARIF aquellos findings para los que no existe una ubicación exportable segura. No se inventan rutas, columnas, rangos ni fingerprints.

```text
Fase 3.5 local: 820 passed
primer intento remoto: run #5, commit 77865f5, failure
causa: Code Scanning rechazó resultados SARIF sin locations
commit correctivo: 6242472
commit correctivo completo: 62424728d1609233d933207e1a58747153f304bc
validación remota final: run #6, success
Upload SARIF to GitHub Code Scanning: success
Post Upload SARIF to GitHub Code Scanning: success
```

### Objetivo siguiente

Iniciar la Fase 3.6 — Documentación pública, actualizando `README.md` y `docs/` para reflejar la arquitectura, instalación, CLI, configuración, plugins, severidades, códigos de salida, ejemplos, SARIF, CI/CD y troubleshooting del estado real del proyecto.

### Restricción

Preservar los 820 tests actuales, los contratos públicos existentes, los formatos Markdown/JSON/SARIF, la configuración global, Registry, UnifiedOrchestrator, RuntimeContext, AuditResult y los códigos de salida `0`, `1` y `2`.

---

## 10. Comandos de validación

### Pruebas específicas SARIF

```powershell
python -m pytest 09_TESTS/unit/test_sarif_exporter.py -v
```

Resultado final:

```text
53 passed in 0.50s
```

### Pruebas relacionadas

```text
286 passed in 3.13s
```

### Suite completa

```powershell
python -m pytest -q
```

Resultado local validado en la Fase 3.5:

```text
820 passed in 10.77s
```

### Ayuda de la CLI

```powershell
python run.py --help
```

### Auditoría operativa

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --output-formats markdown,json `
  --fail-on critical,error `
  --exclude .git,.venv,node_modules,dist,build,07_OUTPUTS,09_TESTS,.pytest_cache,__pycache__,02_SCHEMAS
```

Resultado validado:

```text
5 auditor(s)
941 warning findings
0 critical findings
0 error findings
exit code 0
```

---

## 11. Historial resumido

### Fase 1 — Architecture Auditor MVP

* Contrato y configuración.
* Descubrimiento.
* Imports y grafo.
* Reglas arquitectónicas.
* Robustez.
* Integración con runtime.
* Architecture Auditor estable.

### Fase 2.1 — Report Engine

* Markdown.
* JSON.
* Serialización determinista.
* 33 tests.

### Fase 2.2 — Nuevos plugins

* Documentation Auditor.
* Testing Auditor.
* Configuration Auditor.
* AI Systems Auditor.
* Contratos compatibles con `AuditResult`.

### Fase 2.3 — Features semánticas avanzadas

* Complejidad ciclomática.
* Dead code conservador.
* Métricas por módulo.
* Findings semánticos.
* Architecture Auditor 1.6.0.
* 232 tests conjuntos del Architecture Auditor.

### Fase 3.1 — Orchestrator / CLI unificado

* Implementado `08_SCRIPTS/uaaf_core/orchestrator.py`.
* Implementado `08_SCRIPTS/uaaf_core/cli.py`.
* Preservado `run.py`.
* Descubrimiento automático de cinco plugins.
* Selección de todos los auditores o subsets.
* Ejecución secuencial.
* `RuntimeContext` canónico.
* Agregación ordenada de `AuditResult`.
* Reportes Markdown y JSON consolidados.
* Nombres con timestamp.
* Escritura en `07_OUTPUTS/`.
* Soporte para `--config`.
* Soporte para `--fail-on`.
* Soporte para `--exclude`.
* Códigos de salida `0`, `1` y `2`.
* Inferencia de raíz corregida en Windows.
* Compatibilidad con Python 3.14 corregida.
* Prueba de regresión AST agregada.
* Suite completa: 634 tests pasando.
* Validación operativa: 941 warnings, 0 critical, 0 error y exit code 0.
* Fase 3.1 completada.
* Próximo objetivo: Fase 3.3 — Configuración global.

---

<!-- UAAF_PHASE_3_2_SESSION_CONTEXT_START -->
## Cierre validado de la Fase 3.2 — Plugin Registry dinámico

### Estado consolidado

* ✅ **Fase 3.2 — Plugin Registry dinámico: COMPLETADA**.
* ⏳ **Fase 3.3 — Configuración global: SIGUIENTE OBJETIVO**.
* Fecha de cierre validado: **2026-08-04**.

### Resultado arquitectónico

La arquitectura canónica de plugins queda establecida como:

```text
CLI
  -> UnifiedOrchestrator
      -> UAAFRegistry
          -> Plugins
```

`UAAFRegistry` es ahora la fuente única de verdad para:

* Descubrimiento dinámico bajo `plugins/*/`.
* Validación estructural de candidatos.
* Importación dinámica controlada y aislada.
* Registro, consulta, listado e iteración determinista.
* Resolución de nombres de CLI, tipos de auditor y `plugin_id`.
* Selección `all` y selección de subsets.
* Detección de plugins inválidos, IDs duplicados, aliases ambiguos y nombres desconocidos.
* Redescubrimiento idempotente y transaccional.

`UnifiedOrchestrator` delega al Registry el descubrimiento y la selección de plugins, conserva la ejecución secuencial y admite inyección de un Registry aislado durante pruebas.

### Archivos implementados

```text
08_SCRIPTS/uaaf_core/registry.py
08_SCRIPTS/uaaf_core/orchestrator.py
09_TESTS/unit/test_registry.py
```

No fue necesario modificar:

```text
08_SCRIPTS/uaaf_core/cli.py
08_SCRIPTS/uaaf_core/audit/audit_result.py
run.py
09_TESTS/unit/test_orchestrator.py
09_TESTS/unit/test_cli.py
```

### Validación automatizada

Pruebas relacionadas:

```text
124 passed in 2.80s
```

Suite completa:

```text
634 passed in 11.56s
```

Composición:

* 577 pruebas anteriores preservadas.
* 57 pruebas nuevas del Plugin Registry y su integración.
* Cero regresiones.

### Validación operativa de la CLI

```text
python run.py --help
Argumentos públicos preservados.
```

```text
--auditors all
5 auditores
1053 findings totales
Reportes Markdown y JSON generados
```

```text
--auditors architecture,testing,configuration
3 auditores
680 findings totales
Reportes Markdown y JSON generados
```

### Nota operativa de pytest

No deben permanecer dentro de la raíz del repositorio carpetas de entrega que contengan copias de pruebas con el mismo nombre, por ejemplo:

```text
UAAF_Fase_3_2/09_TESTS/unit/test_registry.py
```

Pytest puede intentar importar ambas copias como `test_registry` y producir `import file mismatch`. Después de integrar una entrega, la carpeta temporal y su ZIP deben eliminarse o mantenerse fuera del repositorio.

### Continuidad

La siguiente sesión corresponde a:

```text
Fase 3.3 — Configuración global
```

Debe definir una configuración canónica y determinista, preservando la precedencia:

```text
CLI > archivo de configuración > valores predeterminados
```
<!-- UAAF_PHASE_3_2_SESSION_CONTEXT_END -->

<!-- UAAF_PHASE_3_3_SESSION_CONTEXT_START -->
## Cierre validado de la Fase 3.3 — Configuración global

### Estado consolidado

* ✅ **Fase 3.3 — Configuración global: COMPLETADA**.
* ⏳ **Fase 3.4 — Integración CI/CD: SIGUIENTE OBJETIVO**.
* Fecha de cierre validado: **2026-08-05**.

### Arquitectura resultante

```text
run.py
  -> CLI
      -> ResolvedConfig
          -> UnifiedOrchestrator.run_resolved()
              -> UAAFRegistry
                  -> Plugins
              -> RuntimeContext
              -> ReportEngine
```

`08_SCRIPTS/uaaf_core/config.py` es la fuente canónica de configuración de ejecución. La configuración final se resuelve antes de iniciar plugins y aplica la precedencia exacta:

```text
valores predeterminados < archivo de configuración < argumentos explícitos de CLI
```

La CLI conserva sus valores visibles históricos, pero registra por separado qué argumentos fueron proporcionados explícitamente. El Orchestrator conserva `run()` como adaptador compatible y expone `run_resolved()` como vía canónica para ejecutar una configuración ya resuelta.

### Contratos implementados

* Representación final inmutable mediante `ResolvedConfig`.
* Representación parcial mediante `ConfigOverrides` y el sentinel `UNSET`.
* Carga UTF-8 de `.json`, `.toml`, `.yaml` y `.yml`.
* Soporte de `[tool.uaaf]` en TOML.
* Parser YAML limitado, determinista y sin dependencias externas.
* Normalización estable de auditores, formatos, severidades y exclusiones.
* Rutas relativas de CLI resueltas respecto del directorio de trabajo.
* Rutas del archivo resueltas respecto del directorio del archivo.
* Aliases históricos compatibles: `global`, `ignored_directories` y `auditors` como mapping.
* Validación de campos globales y configuraciones específicas por plugin.
* Rechazo de campos reservados `project_path` y `audit_type` en secciones de plugins.
* Snapshot de diagnóstico determinista con redacción de claves sensibles.
* Errores de configuración claros convertidos en código de salida `2`.
* `UAAFRegistry` preservado como fuente canónica de plugins.
* `RuntimeContext`, `AuditResult`, `ReportEngine`, `run.py` y los cinco plugins preservados.

### Archivos implementados

```text
08_SCRIPTS/uaaf_core/config.py
08_SCRIPTS/uaaf_core/cli.py
08_SCRIPTS/uaaf_core/orchestrator.py
09_TESTS/unit/test_global_config.py
09_TESTS/unit/test_cli.py
09_TESTS/unit/test_orchestrator.py
```

No fue necesario modificar:

```text
08_SCRIPTS/uaaf_core/registry.py
08_SCRIPTS/uaaf_core/runtime/runtime.py
08_SCRIPTS/uaaf_core/runtime/runtime_context.py
08_SCRIPTS/uaaf_core/audit/audit_result.py
08_SCRIPTS/uaaf_core/reporting/report_engine.py
run.py
plugins/*
```

### Validación automatizada

Pruebas de configuración global:

```text
68 passed in 1.60s
```

Pruebas relacionadas con configuración, CLI, Orchestrator y Registry:

```text
203 passed in 3.69s
```

Suite completa:

```text
713 passed in 12.48s
```

Composición:

* 634 pruebas anteriores preservadas.
* 79 pruebas nuevas agregadas en la Fase 3.3.
* Cero regresiones.

### Smoke tests validados

* `python run.py --help`: exit code `0`.
* Sin archivo de configuración: 5 auditores, 1027 findings, Markdown y JSON, exit code `0`.
* Subset: 3 auditores, 645 findings, Markdown y JSON, exit code `0`.
* JSON: 3 auditores, 645 findings, Markdown y JSON, exit code `0`.
* TOML: 2 auditores, 418 findings, Markdown y JSON, exit code `0`.
* YAML limitado: 2 auditores, 641 findings, Markdown y JSON, exit code `0`.
* Precedencia: la CLI sobrescribió auditores, formato y directorio del archivo; `PRECEDENCE OK`.
* Campo desconocido: exit code `2`.
* Tipo inválido: exit code `2`.
* Extensión no soportada: exit code `2`.
* Archivo inexistente: exit code `2`.

Los conteos de findings son resultados operativos del estado actual del repositorio y no deben convertirse en aserciones rígidas salvo con fixtures controlados.

### Deuda técnica y límites preservados

* El YAML soportado es deliberadamente limitado; no se implementó un parser YAML general.
* No se agregaron dependencias externas.
* No se creó todavía un archivo `uaaf.yaml` predeterminado ni se modificó `pyproject.toml`; la infraestructura admite archivos explícitos mediante `--config`.
* JSON Schemas, GitHub Actions, SARIF, paralelización, caché, auditoría incremental y auto-remediation permanecen fuera de esta fase.

### Continuidad

La siguiente sesión corresponde a:

```text
Fase 3.4 — Integración CI/CD
```

Debe implementar una integración de GitHub Actions mínima y determinista, ejecutar la suite completa y UAAF, conservar los códigos de salida, y publicar reportes Markdown/JSON como artifacts sin modificar la semántica de configuración global.
<!-- UAAF_PHASE_3_3_SESSION_CONTEXT_END -->

<!-- UAAF_PHASE_3_4_SESSION_CONTEXT_START -->
## Implementación y validación de la Fase 3.4 — Integración CI/CD

### Estado consolidado

* ✅ **Implementación completada y validada localmente el 2026-08-06**.
* ✅ **Validación remota completada con éxito**.
* Evento: `workflow_dispatch`.
* Ejecución: `#4`.
* Commit: `fb3f72b`.
* Conclusión: `success`.

### Workflow implementado

Archivo:

```text
.github/workflows/uaaf-ci.yml
```

Contrato validado:

* Nombre visible `UAAF CI`.
* Eventos `push`, `pull_request` y `workflow_dispatch` para `main`.
* Permisos mínimos.
* Runner `windows-latest`.
* Python `3.14.6`.
* `pytest==9.1.1`.
* Suite completa.
* Ayuda de CLI.
* Smoke test controlado fuera del repositorio.
* Reportes Markdown y JSON.
* Timeout de 30 minutos.
* Concurrencia acotada.
* Sin secretos, commits ni push automáticos.

### Resultados locales de cierre

```text
37 passed in 0.78s
240 passed in 5.75s
750 passed in 14.72s
```

### Evidencia remota

```text
evento: workflow_dispatch
ejecución: #4
commit: fb3f72b
conclusión: success
```

La condición previa para iniciar la Fase 3.5 quedó satisfecha.
<!-- UAAF_PHASE_3_4_SESSION_CONTEXT_END -->

<!-- UAAF_PHASE_3_5_SESSION_CONTEXT_START -->
## Implementación y validación final de la Fase 3.5 — Exportación SARIF

### Estado consolidado

* ✅ **Implementación completada y validada localmente el 2026-08-06**.
* ⚠️ **Primer intento remoto:** ejecución #5 sobre el commit `77865f5`, conclusión `failure`.
* ✅ **Corrección de interoperabilidad SARIF:** commit `6242472`.
* ✅ **Validación remota final:** ejecución #6 sobre `62424728d1609233d933207e1a58747153f304bc`, conclusión `success`.
* ✅ **GitHub Code Scanning:** pasos de carga y post-carga SARIF finalizados en `success`.
* ✅ **Fase 3.5 cerrada y validada remotamente el 2026-08-07**.

### Arquitectura implementada

Archivo principal:

```text
08_SCRIPTS/uaaf_core/reporting/sarif_exporter.py
```

Contrato:

* Exportación opt-in mediante `sarif` en `--output-formats`.
* Formatos predeterminados preservados: `markdown,json`.
* Documento SARIF `2.1.0`.
* Schema oficial SARIF 2.1.0 Errata 01.
* Una ejecución SARIF por reporte consolidado.
* Reglas deduplicadas por código de finding y ordenadas determinísticamente.
* Mapeo de severidad:
  * `critical` y `error` → `error`.
  * `warning` → `warning`.
  * `info` → `note`.
* Ubicaciones relativas al proyecto y normalizadas a POSIX.
* Líneas emitidas únicamente cuando existe un entero positivo válido.
* Sin columnas, rangos ni fingerprints inventados.
* Redacción de rutas absolutas mediante `<PROJECT_ROOT>`.
* Compatibilidad con representaciones Windows escapadas.
* Propiedades conservadoras sin copiar detalles arbitrarios potencialmente sensibles.
* Findings sin ubicación exportable segura permanecen en el resultado canónico UAAF y en Markdown/JSON, pero se omiten de `results[]` SARIF para cumplir el contrato operativo de GitHub Code Scanning.

### Integración

Se actualizaron:

```text
.github/workflows/uaaf-ci.yml
08_SCRIPTS/uaaf_core/cli.py
08_SCRIPTS/uaaf_core/config.py
08_SCRIPTS/uaaf_core/reporting/__init__.py
08_SCRIPTS/uaaf_core/reporting/report_engine.py
```

El workflow incorpora `github/codeql-action/upload-sarif@v4`, permiso acotado `security-events: write` y una condición segura para evitar cargas desde pull requests de forks.

### Pruebas

Archivo nuevo:

```text
09_TESTS/unit/test_sarif_exporter.py
```

Suites ampliadas:

```text
09_TESTS/unit/test_report_engine.py
09_TESTS/unit/test_global_config.py
09_TESTS/unit/test_cli.py
09_TESTS/unit/test_ci_workflow.py
```

Resultados finales:

```text
53 passed in 0.50s
286 passed in 3.13s
820 passed in 10.77s
```

Composición:

* 750 pruebas anteriores preservadas.
* 70 pruebas nuevas agregadas.
* Cero regresiones.
* Validación posterior al hotfix: `53 passed in 0.96s`.
* Suite completa posterior al hotfix: `820 passed in 26.97s`.

### Validaciones funcionales

* SARIF individual: 1 auditor, 3 findings y 1 reporte.
* Markdown, JSON y SARIF funcionan conjuntamente.
* Rutas absolutas detectadas en mensajes: `0`.
* Rutas absolutas detectadas en locations: `0`.
* Placeholder de redacción: `<PROJECT_ROOT>`.
* Determinismo confirmado:

```text
HashA: 26B549B9F432F71B22B89E2267338D361622A2410000E1B88A73D1B02849291B
HashB: 26B549B9F432F71B22B89E2267338D361622A2410000E1B88A73D1B02849291B
Identical: True
```

### Validación remota y corrección de interoperabilidad

Primer intento remoto:

```text
run: #5
commit: 77865f5
status: completed
conclusion: failure
```

GitHub Code Scanning rechazó la carga porque existían resultados SARIF sin al menos una ubicación exportable.

Corrección aplicada:

```text
commit: 6242472
regla: si un finding no tiene URI exportable segura, no se emite en results[] SARIF
resultado canónico UAAF: preservado
Markdown/JSON: preservados
ubicaciones inventadas: ninguna
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

### Compatibilidad preservada

* Markdown y JSON.
* CLI y configuración global.
* Registry y Unified Orchestrator.
* RuntimeContext y AuditResult.
* Cinco plugins.
* Códigos de salida `0`, `1` y `2`.
* Sin dependencias productivas nuevas.

### Continuidad

```text
implementación SARIF validada localmente: 820 passed
run remoto inicial #5: failure
commit correctivo: 6242472
run remoto final #6: success
Upload SARIF to GitHub Code Scanning: success
Post Upload SARIF to GitHub Code Scanning: success
Fase 3.5: COMPLETADA Y VALIDADA REMOTAMENTE
```

La siguiente fase es:

```text
Fase 3.6 — Documentación pública
```
<!-- UAAF_PHASE_3_5_SESSION_CONTEXT_END -->
