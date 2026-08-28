# Frontera de reutilización — L1 → L2

> Restricción vinculante, definida por Fabián Herrera el 2026-08-28, antes de
> escribir una sola línea de código del proyecto nuevo. Gobierna cualquier
> decisión de "esto ya existe en L1, lo aprovecho". Si una propuesta choca con
> este documento, se descarta la propuesta.

## La regla

**La reutilización solo vale para datos y disciplina de proceso. Nunca para el
código ni para el sistema en sí.**

El objeto que L2 evalúa es si el sistema nuevo **decide en tiempo de
ejecución**. Eso no se hereda: se construye. Un `agent_core/` de L1 envuelto en
LangGraph seguiría siendo el pipeline `recuperar → responder` con una capa
cosmética de agente encima — exactamente el error que la nota del Chief
Learning Officer del brief penaliza de forma explícita.

## Prohibido

- **No reutilizar el código de `rgwallcovering-ai-assistant` como base.** Ni
  copiar módulos, ni importarlos, ni "adaptarlos", ni envolverlos.
- **No hacer commits nuevos en ese repo.** Quedó certificado (Distinction,
  109/120) y debe permanecer intacto tal como fue evaluado.
- El proyecto nuevo (`rgwallcovering-agent-ops`) empieza con **git history
  propio, desde cero**, en un repo de GitHub separado.

## Permitido — y solo esto

Todo lo de abajo se cita con procedencia explícita en `02_data_provenance.md`.

1. **`data/index/embeddings.npy` + `chunks.jsonl`** (el corpus indexado), como
   **dato de entrada**. Se envuelve en una tool **nueva** que el agente decide
   si invocar en cada turno — no una llamada automática como en el pipeline
   original.
2. **`data/leads.jsonl`**, como **semilla** de datos reales. Obligatoriamente
   ampliada con casos incómodos nuevos: información contradictoria entre
   turnos, sin forma de contacto, fallo de herramienta a mitad de conversación.
   Los 4 leads originales solos no alcanzan y **cuentan en contra** si se usan
   tal cual.
3. **Las convenciones del `CLAUDE.md` de L1** — tiers de confianza, regla de no
   fabricar datos sobre el negocio, manejo de datos personales — como **estilo
   a replicar** en un `CLAUDE.md` nuevo. No como import de código.
4. **La disciplina spec-first** — docs numerados, commits de spec antes que los
   de código, `PROGRESS.md` vivo — como **método**, no como documento a copiar.

### Esquema del índice: contrato de datos, no código heredado

Leer el corpus exige conocer su forma. Conocerla es un contrato de datos; el
lector se escribe nuevo dentro de la tool nueva.

```
embeddings.npy   float32, (n_chunks, 384), normalizado L2 en construcción
chunks.jsonl     un registro por línea, mismo orden que la matriz
                 {chunk_id, text, title, source_id, tier, url, date}
```

Embeddings: `fastembed`, `BAAI/bge-small-en-v1.5`. BGE es asimétrico — los
pasajes se embebieron sin prefijo, la consulta lo lleva. Contenido medido:
370 fragmentos (331 tier A, 4 tier B, 35 tier C).

## Genuinamente nuevo

Sin excepción, y sin "adaptar" desde L1, porque **no existe en L1**:

- El grafo de LangGraph (nodos, estado, aristas condicionales).
- Las tools y sus esquemas.
- La memoria y la justificación de su tier.
- El gate humano previo a cualquier acción irreversible.
- El manejo de fallos: validación de salida, reintento con el motivo
  específico, escalación con contexto completo.
- La suite `pytest-asyncio`.
- La observabilidad (trazas).
- `REFLECTION.md`, la slide, la declaración de esfuerzo.

## La idea de fondo

Reusar **contexto del negocio** — qué sabe la empresa, qué leads reales
existen — está bien y se premia si se cita bien. Reusar la **arquitectura o el
código** del sistema anterior no, porque lo que se evalúa en L2 es si el
sistema nuevo decide de verdad.

## Pendiente de confirmar antes de tocar los datos

`data/leads.jsonl` tiene 4 registros: 3 son la misma persona (Ana Ruiz) y 1 es
"Yuliet Mazo Holguín", que **no** figura entre las personas sintéticas del set
de evaluación de L1 ni usa correo `example.com` como aquellas. Si es una
persona real, no entra: ni al repo, ni a la app pública, ni al deck.
`02_data_provenance.md` de L1 §3.2 se comprometió a personas inventadas en todo
material demostrativo.
