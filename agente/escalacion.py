"""El handoff a Ronald.

Escalar no es rendirse: es la respuesta correcta cuando algo no le toca al
agente decidir, o cuando lo intentado no funcionó. Pero solo vale si llega con
lo suficiente para que él actúe sin abrir un log.

Lo que va dentro está fijado por lo que el checklist exige de una escalación —
"con contexto completo tras fallos repetidos"— y por lo que a Ronald le hace
falta antes de marcar un teléfono.
"""

from dataclasses import dataclass

from .estado import EstadoLead


@dataclass(frozen=True)
class Escalacion:
    """El paquete que recibe Ronald."""

    lead_id: str
    nombre: str
    contacto: str
    motivo: str
    intentos: tuple[str, ...]
    fuentes: tuple[str, ...]
    texto: str


def construir(estado: EstadoLead) -> Escalacion:
    """Arma la escalación desde el estado."""
    lead = estado.lead

    intentos = tuple(
        f"{f.herramienta} attempt {f.intento}: {f.motivo}" for f in estado.fallos
    )
    # Solo nivel A y B: lo que sostiene una afirmación sobre el negocio. Los
    # de nivel C explican, no respaldan, y llenarían esto de ruido.
    fuentes = tuple(
        f"[{p.fragmento.tier}] {p.fragmento.titulo}"
        for p in estado.hallazgos
        if p.fragmento.tier in ("A", "B")
    )

    lineas = [
        f"Lead {lead.lead_id} — {lead.nombre or 'no name given'}",
        f"Contact: {estado.resumen_contacto()}",
        f"Project: {lead.tipo_proyecto or 'not stated'}, "
        f"{lead.espacio or 'space not described'}, "
        f"{lead.ubicacion or 'location not given'}",
        "",
        "WHY THIS NEEDS YOU:",
        estado.motivo or "(no reason recorded — this is itself a defect)",
    ]

    if intentos:
        lineas += [
            "",
            f"WHAT WAS TRIED ({len(intentos)} attempt"
            f"{'s' if len(intentos) != 1 else ''}, all failed):",
            *[f"  - {i}" for i in intentos],
        ]

    if fuentes:
        lineas += ["", "WHAT THIS RESTS ON:", *[f"  - {f}" for f in fuentes]]

    if estado.accion_propuesta is not None:
        p = estado.accion_propuesta
        lineas += [
            "",
            "WHAT WAS GOING TO GO OUT (not sent):",
            f"  to: {p.destinatario or p.titulo}",
            f"  {p.asunto}",
            # El cuerpo entero, no un resumen: si Ronald va a decidir sobre un
            # texto, tiene que ver el texto.
            *[f"  | {l}" for l in (p.cuerpo or p.descripcion or "").splitlines()],
        ]

    lineas += [
        "",
        f"Nothing was sent to this person. Run {estado.corrida_id}.",
    ]

    return Escalacion(
        lead_id=lead.lead_id,
        nombre=lead.nombre,
        contacto=estado.resumen_contacto(),
        motivo=estado.motivo,
        intentos=intentos,
        fuentes=fuentes,
        texto="\n".join(lineas),
    )
