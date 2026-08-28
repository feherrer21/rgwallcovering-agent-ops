"""El grafo. Fase 2: el bucle más pequeño que ya decide.

`cargar -> decidir -> (buscar_corpus | terminar) -> ...`

Todavía no hay gate, ni correo, ni calendario, ni memoria durable: llegan en
las fases 3 y 4. Lo que sí está es la propiedad que el caso evalúa — las
aristas que salen de `decidir` dependen de lo que el modelo eligió, no de un
contador de pasos ni de un campo del lead.
"""

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from . import modelo as modelo_mod
from . import prompts, tools
from .config import ajustes
from .estado import Accion, EstadoLead
from .traza import Traza

log = logging.getLogger(__name__)

NOMBRE_DECISION = "proponer_siguiente_accion"


def construir(llm=None, traza: Traza | None = None):
    """Compila el grafo. `llm` y `traza` se inyectan para poder mockearlos."""
    llm = llm if llm is not None else modelo_mod.cliente()
    con_tools = llm.bind_tools(tools.TOOLS_DECISION)
    tz = traza if traza is not None else Traza()

    # --- Nodos ------------------------------------------------------------

    def cargar(estado: EstadoLead) -> dict:
        """Determinista. Prepara el primer mensaje y no llama al modelo."""
        tz.lead_id = estado.lead.lead_id
        tz.paso(
            "cargar",
            lead=estado.lead.lead_id,
            canales=estado.resumen_contacto(),
            turnos=len(estado.turnos),
        )
        return {
            "corrida_id": tz.corrida_id,
            "mensajes": [
                SystemMessage(content=prompts.SISTEMA),
                HumanMessage(content=prompts.contexto(estado)),
            ],
        }

    def decidir(estado: EstadoLead) -> dict:
        """El nodo agéntico: el modelo elige qué hacer a continuación."""
        if estado.llamadas >= ajustes.max_llamadas_por_lead:
            # El tope protege un presupuesto de la empresa. Agotarlo no es un
            # fallo silencioso: es una escalación con su motivo (03 §12.2).
            tz.fallo("decidir", f"tope de {ajustes.max_llamadas_por_lead} llamadas")
            return {
                "accion": Accion.ESCALAR_A_RONALD,
                "motivo": (
                    "Reached the per-lead call limit without deciding. "
                    "Escalated rather than continuing to spend."
                ),
            }

        respuesta: AIMessage = con_tools.invoke(estado.mensajes)
        uso = getattr(respuesta, "usage_metadata", None) or {}

        for llamada in respuesta.tool_calls:
            if llamada["name"] == NOMBRE_DECISION:
                args = llamada["args"]
                accion = Accion(args["accion"])
                tz.decision(accion.value, args.get("motivo", ""), uso)
                return {
                    "mensajes": [respuesta],
                    "llamadas": estado.llamadas + 1,
                    "accion": accion,
                    "motivo": args.get("motivo", ""),
                }

        if not respuesta.tool_calls:
            # Ni herramienta ni decisión: el modelo se salió del contrato. Se
            # devuelve al bucle diciéndoselo, en vez de aceptar prosa suelta
            # como si fuera una decisión.
            tz.fallo("decidir", "respuesta sin tool_call")
            aviso = HumanMessage(
                content=(
                    "You replied with prose. Decide by calling "
                    f"`{NOMBRE_DECISION}`, or search first with `buscar_corpus`."
                )
            )
            return {
                "mensajes": [respuesta, aviso],
                "llamadas": estado.llamadas + 1,
            }

        tz.paso(
            "decidir",
            pide=[c["name"] for c in respuesta.tool_calls],
            uso=uso,
        )
        return {"mensajes": [respuesta], "llamadas": estado.llamadas + 1}

    def ejecutar_tool(estado: EstadoLead) -> dict:
        """Mecánica. Ejecuta lo que el modelo pidió y devuelve el resultado."""
        ultimo = estado.mensajes[-1]
        resultados, hallazgos = [], []

        for llamada in ultimo.tool_calls:
            nombre = llamada["name"]
            if nombre not in tools.NOMBRES_LECTURA:
                resultados.append(
                    ToolMessage(
                        content=f"Unknown tool: {nombre}", tool_call_id=llamada["id"]
                    )
                )
                tz.fallo("ejecutar_tool", f"herramienta desconocida: {nombre}")
                continue

            texto, pasajes = tools.ejecutar_lectura(nombre, llamada["args"])
            hallazgos.extend(pasajes)
            tiers = "".join(p.fragmento.tier for p in pasajes) or "-"
            tz.tool(
                nombre,
                llamada["args"],
                f"{len(pasajes)} pasajes [{tiers}]",
                n=len(pasajes),
            )
            resultados.append(
                ToolMessage(content=texto, tool_call_id=llamada["id"])
            )

        return {"mensajes": resultados, "hallazgos": hallazgos}

    def escalar(estado: EstadoLead) -> dict:
        """Handoff a Ronald. En la fase 5 lleva además todos los fallos."""
        tz.paso(
            "escalar",
            lead=estado.lead.lead_id,
            motivo=estado.motivo[:200],
            pasajes=len(estado.hallazgos),
        )
        return {}

    # --- Aristas ----------------------------------------------------------

    def ruta(estado: EstadoLead) -> str:
        """Depende de lo que el modelo eligió, no de un contador de pasos."""
        if estado.accion is not None:
            return "escalar" if estado.accion is Accion.ESCALAR_A_RONALD else END
        ultimo = estado.mensajes[-1]
        if isinstance(ultimo, AIMessage) and ultimo.tool_calls:
            return "ejecutar_tool"
        return "decidir"

    g = StateGraph(EstadoLead)
    g.add_node("cargar", cargar)
    g.add_node("decidir", decidir)
    g.add_node("ejecutar_tool", ejecutar_tool)
    g.add_node("escalar", escalar)

    g.set_entry_point("cargar")
    g.add_edge("cargar", "decidir")
    g.add_conditional_edges(
        "decidir", ruta, {"ejecutar_tool": "ejecutar_tool", "escalar": "escalar",
                          "decidir": "decidir", END: END}
    )
    g.add_edge("ejecutar_tool", "decidir")
    g.add_edge("escalar", END)

    return g.compile()
