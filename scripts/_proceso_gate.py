"""Media corrida del gate, para ejecutarse en un proceso aparte.

Uso interno de la prueba T4.3, que es la que justifica el tier de memoria
elegido en 03_spec.md §7.1. Mockear el proceso no sirve aquí: lo que se está
comprobando es precisamente que el estado sobrevive a que el proceso muera, y
eso solo se demuestra matándolo.

    python -m scripts._proceso_gate preparar <thread_id>
    python -m scripts._proceso_gate aprobar  <thread_id>

El modelo es falso a propósito. Lo que se prueba es la frontera de proceso, no
el comportamiento del modelo, y una prueba que gasta presupuesto cada vez que
se ejecuta es una prueba que se acaba desactivando.
"""

import sys

from langchain_core.messages import AIMessage
from langgraph.types import Command

from agente import correo, grafo
from agente.estado import EstadoLead, RegistroLead


class LLMCanned:
    """Devuelve la decisión y el borrador. Falla si se le pide algo más."""

    def bind_tools(self, _tools):
        return self

    def invoke(self, mensajes):
        for m in reversed(mensajes):
            if getattr(m, "type", "") == "human" and "Draft the" in (m.content or ""):
                return AIMessage(content="", tool_calls=[{
                    "name": "redactar_correo",
                    "args": {
                        "destinatario": "persistencia@example.com",
                        "asunto": "Your enquiry",
                        "cuerpo": "Drafted before the process died.",
                        "chunk_ids": [],
                    },
                    "id": "r1"}])
        return AIMessage(content="", tool_calls=[{
            "name": "proponer_siguiente_accion",
            "args": {"accion": "preparar_correo_visita",
                     "motivo": "listo para avanzar"},
            "id": "d1"}])


class LLMProhibido:
    """Cualquier llamada al modelo al reanudar es un fallo de la prueba.

    Reanudar tras una aprobación no debe requerir volver a pensar: si lo
    requiere, el borrador no se guardó y lo que se ejecutaría sería otro texto
    distinto del que la persona aprobó.
    """

    def bind_tools(self, _tools):
        return self

    def invoke(self, mensajes):
        raise AssertionError("reanudar no debe volver a llamar al modelo")


def _estado():
    return EstadoLead(
        lead=RegistroLead(
            lead_id="PERSIST-01",
            nombre="Persistence Test",
            email="persistencia@example.com",
        )
    )


def main() -> int:
    fase, thread = sys.argv[1], sys.argv[2]
    cfg = {"configurable": {"thread_id": thread}}

    if fase == "preparar":
        app = grafo.construir(llm=LLMCanned())
        r = app.invoke(_estado(), cfg)
        if not r.get("__interrupt__"):
            print("ERROR: no se detuvo en el gate")
            return 1
        print("DETENIDO_EN_GATE:" + r["__interrupt__"][0].value["propuesta"]["cuerpo"])
        return 0

    if fase == "aprobar":
        enviados = []
        # No se envía de verdad: lo que se comprueba es que se ejecuta lo que
        # se aprobó, no el transporte SMTP, que ya tiene sus propias pruebas.
        correo.enviar = lambda d, a, c: (
            enviados.append((d, c)) or correo.ResultadoEnvio(d, a, "id")
        )
        app = grafo.construir(llm=LLMProhibido())
        final = app.invoke(Command(resume={"decision": "aprobada", "quien": "ronald"}), cfg)
        print("RESULTADO:" + (final.get("resultado") or ""))
        print("APROBO:" + final["aprobacion"].quien)
        print("CUERPO_ENVIADO:" + (enviados[0][1] if enviados else ""))
        return 0

    print(f"fase desconocida: {fase}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
