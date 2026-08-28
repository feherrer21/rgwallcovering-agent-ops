"""El grafo.

`cargar -> decidir -> (tools | preparar | escalar)`, y `preparar -> gate_humano
-> ejecutar_irreversible`.

Dos invariantes que este fichero existe para sostener, y que los tests
comprueban en vez de que la prosa los prometa:

1. `decidir` no ejecuta nada. Elige, y las aristas que salen dependen de lo
   elegido, no de un contador de pasos.
2. `ejecutar_irreversible` tiene **exactamente una arista de entrada**, desde
   `gate_humano`. No hay camino a un envío sin aprobación: ni en el camino
   feliz, ni en un reintento, ni en un manejador de error.
"""

import logging
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from . import calendario, correo, persistencia
from . import modelo as modelo_mod
from . import prompts, tools
from .config import ajustes
from .estado import (
    Accion,
    AccionPropuesta,
    Aprobacion,
    EstadoAprobacion,
    EstadoLead,
    Fallo,
)
from .traza import Traza

log = logging.getLogger(__name__)

NOMBRE_DECISION = "proponer_siguiente_accion"

#: Qué se redacta para cada decisión. Que sea una tabla y no una cadena de
#: `if` es deliberado: añadir una acción no debe poder olvidarse de pasar por
#: el gate.
REDACCION = {
    Accion.PREPARAR_CORREO_VISITA: ("correo", tools.REDACTAR_CORREO),
    Accion.PREPARAR_CORREO_PREGUNTA: ("correo", tools.REDACTAR_CORREO),
    Accion.PROPONER_HORARIO: ("evento", tools.REDACTAR_EVENTO),
}


def construir(llm=None, traza: Traza | None = None, checkpointer=None):
    """Compila el grafo. Todo lo externo se inyecta para poder mockearlo."""
    llm = llm if llm is not None else modelo_mod.cliente()
    con_decision = llm.bind_tools(tools.TOOLS_DECISION)
    tz = traza if traza is not None else Traza()
    # Duradero, no en memoria. La aprobación llega en tiempo humano y el
    # estado tiene que sobrevivir al proceso que lo preparó: el argumento
    # completo está en persistencia.py y lo prueba test_memoria.py.
    saver = checkpointer if checkpointer is not None else persistencia.checkpointer()

    # --- Nodos ------------------------------------------------------------

    def cargar(estado: EstadoLead) -> dict:
        tz.lead_id = estado.lead.lead_id
        tz.paso("cargar", lead=estado.lead.lead_id, canales=estado.resumen_contacto())
        return {
            "corrida_id": tz.corrida_id,
            "mensajes": [
                SystemMessage(content=prompts.SISTEMA),
                HumanMessage(content=prompts.contexto(estado)),
            ],
        }

    def decidir(estado: EstadoLead) -> dict:
        if estado.llamadas >= ajustes.max_llamadas_por_lead:
            tz.fallo("decidir", f"tope de {ajustes.max_llamadas_por_lead} llamadas")
            return {
                "accion": Accion.ESCALAR_A_RONALD,
                "motivo": (
                    "Reached the per-lead call limit without deciding. "
                    "Escalated rather than continuing to spend."
                ),
            }

        respuesta: AIMessage = con_decision.invoke(estado.mensajes)
        uso = getattr(respuesta, "usage_metadata", None) or {}

        for llamada in respuesta.tool_calls:
            if llamada["name"] == NOMBRE_DECISION:
                args = llamada["args"]
                accion = Accion(args["accion"])
                tz.decision(accion.value, args.get("motivo", ""), uso)
                return {
                    # El acuse NO es decorativo. Sin él queda un mensaje con
                    # `tool_calls` sin respuesta, la conversación está
                    # malformada, y el proveedor se comporta de forma errática:
                    # medido, `preparar` fallaba en una corrida y no en la
                    # siguiente. Ver docs/evidence/02_historial_malformado.md.
                    "mensajes": [
                        respuesta,
                        ToolMessage(
                            content=f"Recorded: {accion.value}. Now draft it.",
                            tool_call_id=llamada["id"],
                        ),
                    ],
                    "llamadas": estado.llamadas + 1,
                    "accion": accion,
                    "motivo": args.get("motivo", ""),
                }

        if not respuesta.tool_calls:
            tz.fallo("decidir", "respuesta sin tool_call")
            return {
                "mensajes": [
                    respuesta,
                    HumanMessage(
                        content=(
                            "You replied with prose. Decide by calling "
                            f"`{NOMBRE_DECISION}`, or search first."
                        )
                    ),
                ],
                "llamadas": estado.llamadas + 1,
            }

        tz.paso("decidir", pide=[c["name"] for c in respuesta.tool_calls], uso=uso)
        return {"mensajes": [respuesta], "llamadas": estado.llamadas + 1}

    def ejecutar_tool(estado: EstadoLead) -> dict:
        """Mecánica de solo lectura. No cambia nada fuera del proceso."""
        resultados, hallazgos = [], []
        for llamada in estado.mensajes[-1].tool_calls:
            nombre = llamada["name"]
            if nombre not in tools.NOMBRES_LECTURA:
                tz.fallo("ejecutar_tool", f"herramienta desconocida: {nombre}")
                resultados.append(
                    ToolMessage(content=f"Unknown tool: {nombre}", tool_call_id=llamada["id"])
                )
                continue
            try:
                texto, pasajes = tools.ejecutar_lectura(nombre, llamada["args"])
            except (calendario.ErrorDeCalendario, ValueError) as exc:
                # La salida de una herramienta no se confía; su fallo tampoco
                # se traga. El motivo vuelve al modelo (03_spec.md §10).
                tz.fallo(nombre, str(exc))
                resultados.append(
                    ToolMessage(content=f"TOOL FAILED: {exc}", tool_call_id=llamada["id"])
                )
                continue
            hallazgos.extend(pasajes)
            tiers = "".join(p.fragmento.tier for p in pasajes) or "-"
            tz.tool(nombre, llamada["args"], f"{len(pasajes)} pasajes [{tiers}]", len(pasajes))
            resultados.append(ToolMessage(content=texto, tool_call_id=llamada["id"]))
        return {"mensajes": resultados, "hallazgos": hallazgos}

    def preparar(estado: EstadoLead) -> dict:
        """Redacta la acción. La escribe en el estado; NO la ejecuta."""
        tipo, esquema = REDACCION[estado.accion]
        redactor = llm.bind_tools([esquema])
        instruccion = HumanMessage(
            content=(
                f"Draft the {tipo} for action `{estado.accion.value}`. "
                "It will not be sent until Ronald approves it. Use only what "
                "you retrieved; if a claim is not in a passage you have, leave "
                "it out."
            )
        )
        respuesta: AIMessage = redactor.invoke(estado.mensajes + [instruccion])

        if not respuesta.tool_calls:
            tz.fallo("preparar", "el modelo no llamó a la herramienta de redacción")
            return {
                "mensajes": [instruccion, respuesta],
                "llamadas": estado.llamadas + 1,
            }

        args = respuesta.tool_calls[0]["args"]
        propuesta = AccionPropuesta(
            tipo=tipo,
            destinatario=args.get("destinatario", ""),
            asunto=args.get("asunto", ""),
            cuerpo=args.get("cuerpo", ""),
            inicio=args.get("inicio", ""),
            fin=args.get("fin", ""),
            titulo=args.get("titulo", ""),
            descripcion=args.get("descripcion", ""),
            chunk_ids=tuple(args.get("chunk_ids", []) or []),
        )
        tz.paso(
            "preparar",
            tipo=tipo,
            destinatario=propuesta.destinatario,
            asunto=propuesta.asunto or propuesta.titulo,
            fuentes=list(propuesta.chunk_ids),
        )
        return {
            # Mismo acuse que en `decidir`, y por el mismo motivo. Importa
            # sobre todo aquí: si Ronald rechaza el borrador se vuelve a
            # `decidir`, y volver con un tool_call sin responder reintroduce
            # exactamente el fallo intermitente que este acuse elimina.
            "mensajes": [
                instruccion,
                respuesta,
                ToolMessage(
                    content="Draft recorded. It is waiting for approval.",
                    tool_call_id=respuesta.tool_calls[0]["id"],
                ),
            ],
            "llamadas": estado.llamadas + 1,
            "accion_propuesta": propuesta,
        }

    def gate_humano(estado: EstadoLead) -> dict:
        """Detiene el grafo. Una persona ve exactamente qué pasaría.

        Lo que se devuelve al reanudar es el REGISTRO de la autorización —
        quién, cuándo, si editó — y es eso lo que evidencia S2, no que alguien
        hubiera entrado en la aplicación (03_spec.md §12.1).
        """
        p = estado.accion_propuesta
        respuesta = interrupt(
            {
                "lead_id": estado.lead.lead_id,
                "accion": estado.accion.value,
                "motivo": estado.motivo,
                "propuesta": {
                    "tipo": p.tipo,
                    "destinatario": p.destinatario,
                    "asunto": p.asunto,
                    "cuerpo": p.cuerpo,
                    "inicio": p.inicio,
                    "fin": p.fin,
                    "titulo": p.titulo,
                },
                # Sobre qué se apoya lo que afirma. Aprobar sin poder ver esto
                # sería aprobar a ciegas.
                "fuentes": list(p.chunk_ids),
                "pasajes": [
                    {"tier": h.fragmento.tier, "titulo": h.fragmento.titulo}
                    for h in estado.hallazgos
                ],
            }
        )

        decision = (respuesta or {}).get("decision", "rechazada")
        editada = bool((respuesta or {}).get("editada"))
        aprobacion = Aprobacion(
            estado=EstadoAprobacion(decision),
            quien=(respuesta or {}).get("quien", ""),
            cuando=datetime.now().astimezone().isoformat(timespec="seconds"),
            editada=editada,
            motivo_rechazo=(respuesta or {}).get("motivo", ""),
        )
        tz.paso(
            "gate_humano",
            decision=aprobacion.estado.value,
            quien=aprobacion.quien,
            editada=aprobacion.editada,
        )

        actualizacion: dict = {"aprobacion": aprobacion}
        # Si editó el borrador, lo que se ejecuta es lo que él dejó, no lo que
        # el modelo escribió.
        if editada and (respuesta or {}).get("propuesta"):
            campos = respuesta["propuesta"]
            actualizacion["accion_propuesta"] = AccionPropuesta(
                tipo=estado.accion_propuesta.tipo,
                chunk_ids=estado.accion_propuesta.chunk_ids,
                **{k: v for k, v in campos.items() if k != "tipo"},
            )
        if aprobacion.estado is EstadoAprobacion.RECHAZADA:
            actualizacion["mensajes"] = [
                HumanMessage(
                    content=(
                        "Ronald rejected that draft. Reason: "
                        f"{aprobacion.motivo_rechazo or 'not given'}. Decide again."
                    )
                )
            ]
            actualizacion["accion"] = None
            actualizacion["accion_propuesta"] = None
        return actualizacion

    def ejecutar_irreversible(estado: EstadoLead) -> dict:
        """El único nodo que toca el mundo. Solo alcanzable desde el gate.

        La comprobación de aprobación se repite aquí aunque la arista ya la
        garantice: es la última línea, y una defensa que solo vive en la
        topología se pierde el día que alguien añade una arista.
        """
        if not estado.aprobacion.autoriza:
            raise RuntimeError(
                "ejecutar_irreversible alcanzado sin aprobación — esto es un bug "
                "estructural, no una condición a manejar"
            )

        p = estado.accion_propuesta
        try:
            if p.tipo == "correo":
                r = correo.enviar(p.destinatario, p.asunto, p.cuerpo)
                resultado = f"email sent to {r.destinatario}"
            else:
                ident = calendario.crear_evento(
                    datetime.fromisoformat(p.inicio),
                    datetime.fromisoformat(p.fin),
                    p.titulo,
                    p.descripcion,
                )
                resultado = f"calendar event created ({ident})"
        except (correo.ErrorDeEnvio, calendario.ErrorDeCalendario, ValueError) as exc:
            # Se propaga como estado, no se traga: la fase 5 lo convierte en
            # reintento con el motivo y escalación tras agotarlo.
            tz.fallo("ejecutar_irreversible", str(exc))
            persistencia.registrar(
                estado.lead.lead_id, p.tipo, "fallo",
                motivo=str(exc), corrida=estado.corrida_id,
            )
            return {
                "resultado": "",
                "fallos": [Fallo(herramienta=p.tipo, motivo=str(exc), intento=1)],
            }

        tz.paso("ejecutar_irreversible", tipo=p.tipo, resultado=resultado)
        persistencia.registrar(
            estado.lead.lead_id, p.tipo, "ok",
            detalle=resultado, aprobo=estado.aprobacion.quien,
            corrida=estado.corrida_id,
        )
        return {"resultado": resultado}

    def escalar(estado: EstadoLead) -> dict:
        tz.paso(
            "escalar",
            lead=estado.lead.lead_id,
            motivo=estado.motivo[:200],
            pasajes=len(estado.hallazgos),
            fallos=[f.motivo for f in estado.fallos],
        )
        persistencia.registrar(
            estado.lead.lead_id, "escalacion", "ok",
            motivo=estado.motivo[:300], corrida=estado.corrida_id,
        )
        return {}

    # --- Aristas ----------------------------------------------------------

    def ruta_decidir(estado: EstadoLead) -> str:
        if estado.accion is Accion.ESCALAR_A_RONALD:
            return "escalar"
        if estado.accion is not None:
            return "preparar"
        ultimo = estado.mensajes[-1]
        if isinstance(ultimo, AIMessage) and ultimo.tool_calls:
            return "ejecutar_tool"
        return "decidir"

    def ruta_preparar(estado: EstadoLead) -> str:
        # Sin borrador no hay nada que aprobar: se vuelve a decidir en lugar de
        # presentarle al humano una propuesta vacía.
        return "gate_humano" if estado.accion_propuesta else "decidir"

    def ruta_gate(estado: EstadoLead) -> str:
        return "ejecutar_irreversible" if estado.aprobacion.autoriza else "decidir"

    g = StateGraph(EstadoLead)
    for nombre, fn in (
        ("cargar", cargar),
        ("decidir", decidir),
        ("ejecutar_tool", ejecutar_tool),
        ("preparar", preparar),
        ("gate_humano", gate_humano),
        ("ejecutar_irreversible", ejecutar_irreversible),
        ("escalar", escalar),
    ):
        g.add_node(nombre, fn)

    g.set_entry_point("cargar")
    g.add_edge("cargar", "decidir")
    g.add_conditional_edges(
        "decidir",
        ruta_decidir,
        {
            "ejecutar_tool": "ejecutar_tool",
            "preparar": "preparar",
            "escalar": "escalar",
            "decidir": "decidir",
        },
    )
    g.add_edge("ejecutar_tool", "decidir")
    g.add_conditional_edges(
        "preparar", ruta_preparar, {"gate_humano": "gate_humano", "decidir": "decidir"}
    )
    # La ÚNICA arista que entra a ejecutar_irreversible.
    g.add_conditional_edges(
        "gate_humano",
        ruta_gate,
        {"ejecutar_irreversible": "ejecutar_irreversible", "decidir": "decidir"},
    )
    g.add_edge("ejecutar_irreversible", END)
    g.add_edge("escalar", END)

    return g.compile(checkpointer=saver)
