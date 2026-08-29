"""Pruebas del gate humano y de las acciones irreversibles.

Ninguna envia un correo ni crea un evento: el nodo que toca el mundo se
sustituye o se comprueba por su guardia. Una suite que manda correos de verdad
al probarse es una suite que nadie ejecuta.
"""

import pytest
from langchain_core.messages import AIMessage
from langgraph.types import Command

from agente import correo, grafo
from agente.estado import (
    Accion,
    AccionPropuesta,
    Aprobacion,
    EstadoAprobacion,
    EstadoLead,
    RegistroLead,
)
from agente.traza import Traza


class LLMFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.enlazado = None

    def bind_tools(self, tools):
        self.enlazado = [t["function"]["name"] for t in tools]
        return self

    def invoke(self, mensajes):
        return self.respuestas.pop(0)


def _decision(accion, motivo="porque si"):
    return AIMessage(content="", tool_calls=[{
        "name": "proponer_siguiente_accion",
        "args": {"accion": accion, "motivo": motivo}, "id": "d1"}])


def _borrador(destinatario="t@example.com", cuerpo="Hello."):
    return AIMessage(content="", tool_calls=[{
        "name": "redactar_correo",
        "args": {"destinatario": destinatario, "asunto": "Your enquiry",
                 "cuerpo": cuerpo, "chunk_ids": []},
        "id": "r1"}])


def _estado():
    return EstadoLead(lead=RegistroLead(lead_id="T01", nombre="Test",
                                        email="t@example.com"))


CFG = {"configurable": {"thread_id": "t-1"}}


# --- Invariante estructural (T3.3, T3.7) ----------------------------------


def test_ejecutar_irreversible_tiene_exactamente_una_arista_de_entrada():
    """El gate es estructural, no procedimental.

    Si alguien anade una arista que salte el gate, esta prueba lo dice. Es la
    afirmacion de 03_spec.md §5 convertida en algo comprobable.
    """
    g = grafo.construir(llm=LLMFalso([])).get_graph()
    entrantes = [e for e in g.edges if e.target == "ejecutar_irreversible"]
    assert len(entrantes) == 1
    assert entrantes[0].source == "gate_humano"


def test_ningun_nodo_salvo_el_gate_alcanza_el_envio():
    """Ni un camino de error puede llegar al envio."""
    g = grafo.construir(llm=LLMFalso([])).get_graph()
    fuentes = {e.source for e in g.edges if e.target == "ejecutar_irreversible"}
    assert fuentes == {"gate_humano"}


def test_el_nodo_irreversible_se_niega_sin_aprobacion():
    """Ultima linea: la defensa no vive solo en la topologia.

    Una arista puede anadirse por error manana; esta guardia no depende de que
    el grafo siga teniendo la forma que tiene hoy.
    """
    from agente import grafo as g

    estado = _estado()
    estado.accion_propuesta = AccionPropuesta(tipo="correo", destinatario="t@example.com",
                                              asunto="x", cuerpo="y")
    estado.aprobacion = Aprobacion(estado=EstadoAprobacion.RECHAZADA)

    app = g.construir(llm=LLMFalso([]))
    nodo = app.nodes["ejecutar_irreversible"]
    with pytest.raises(RuntimeError, match="sin aprobación"):
        nodo.invoke(estado)


# --- El ciclo del gate ----------------------------------------------------


def test_el_grafo_se_detiene_en_el_gate_y_muestra_la_propuesta():
    llm = LLMFalso([_decision("preparar_correo_visita"), _borrador()])
    app = grafo.construir(llm=llm, traza=Traza())
    resultado = app.invoke(_estado(), CFG)

    interrupciones = resultado.get("__interrupt__")
    assert interrupciones, "el grafo no se detuvo antes de actuar"
    carga = interrupciones[0].value
    assert carga["propuesta"]["destinatario"] == "t@example.com"
    # Aprobar a ciegas no deberia ser posible: los pasajes en que se apoya la
    # propuesta viajan con ella.
    assert "fuentes" in carga and "pasajes" in carga


def test_aprobar_ejecuta_y_deja_registro(monkeypatch):
    enviados = []
    monkeypatch.setattr(correo, "enviar", lambda d, a, c: enviados.append(d) or
                        correo.ResultadoEnvio(d, a, "id"))
    llm = LLMFalso([_decision("preparar_correo_visita"), _borrador()])
    app = grafo.construir(llm=llm, traza=Traza())
    app.invoke(_estado(), CFG)

    final = app.invoke(
        Command(resume={"decision": "aprobada", "quien": "ronald"}), CFG
    )
    assert enviados == ["t@example.com"]
    assert "email sent" in final["resultado"]
    # ESTO evidencia S2, no que alguien hubiera entrado en la aplicacion.
    assert final["aprobacion"].quien == "ronald"
    assert final["aprobacion"].cuando


def test_rechazar_no_envia_y_realimenta_el_motivo(monkeypatch):
    monkeypatch.setattr(correo, "enviar", lambda *a: pytest.fail("no debio enviar"))
    llm = LLMFalso([
        _decision("preparar_correo_visita"), _borrador(),
        _decision("escalar_a_ronald"),  # tras el rechazo, vuelve a decidir
    ])
    app = grafo.construir(llm=llm, traza=Traza())
    app.invoke(_estado(), CFG)
    final = app.invoke(
        Command(resume={"decision": "rechazada", "quien": "ronald",
                        "motivo": "el tono no es el nuestro"}),
        CFG,
    )
    assert final["accion"] is Accion.ESCALAR_A_RONALD
    assert not final["resultado"]


def test_lo_editado_es_lo_que_se_ejecuta(monkeypatch):
    """Si Ronald corrige el borrador, se envia el suyo, no el del modelo."""
    capturado = {}
    monkeypatch.setattr(correo, "enviar", lambda d, a, c: capturado.update(
        destinatario=d, asunto=a, cuerpo=c) or correo.ResultadoEnvio(d, a, "id"))
    llm = LLMFalso([_decision("preparar_correo_visita"), _borrador(cuerpo="Borrador del modelo.")])
    app = grafo.construir(llm=llm, traza=Traza())
    app.invoke(_estado(), CFG)
    final = app.invoke(
        Command(resume={"decision": "editada", "quien": "ronald", "editada": True,
                        "propuesta": {"destinatario": "t@example.com",
                                      "asunto": "Corregido", "cuerpo": "Texto de Ronald."}}),
        CFG,
    )
    assert capturado["cuerpo"] == "Texto de Ronald."
    assert final["aprobacion"].editada is True


# --- Validacion de la accion irreversible (prepara L12 y L20) -------------


@pytest.mark.parametrize("direccion", ["", "   ", "j.torres@gmailcom", "sin-arroba", "a@b"])
def test_direcciones_invalidas_se_rechazan_antes_de_conectar(direccion):
    """L12 tiene un correo invalido por un caracter.

    Detectarlo tras el rebote es tarde; 'corregirlo' seria inventar un dato de
    contacto, que es un fallo y no una ayuda.
    """
    with pytest.raises(correo.ErrorDeEnvio):
        correo.validar_destinatario(direccion)


def test_el_motivo_del_rechazo_dice_por_que_no_se_corrige():
    with pytest.raises(correo.ErrorDeEnvio, match="fabricating"):
        correo.validar_destinatario("j.torres@gmailcom")


def test_cuerpo_vacio_no_se_envia():
    with pytest.raises(correo.ErrorDeEnvio, match="body is empty"):
        correo.enviar("t@example.com", "asunto", "   ")


# --- Regresion: historial bien formado (docs/evidence/02) -----------------


def test_la_decision_deja_el_historial_bien_formado():
    """Cada tool_call tiene que tener su respuesta.

    Sin el acuse, `decidir` dejaba un mensaje con tool_calls sin responder, la
    conversacion quedaba malformada y `preparar` fallaba de forma
    intermitente. El sintoma aparecia dos nodos despues de la causa.
    """
    llm = LLMFalso([_decision("preparar_correo_visita"), _borrador()])
    app = grafo.construir(llm=llm, traza=Traza())
    resultado = app.invoke(_estado(), {"configurable": {"thread_id": "bien-formado"}})

    pendientes = set()
    for m in resultado["mensajes"]:
        for llamada in getattr(m, "tool_calls", []) or []:
            pendientes.add(llamada["id"])
        if getattr(m, "type", "") == "tool":
            pendientes.discard(m.tool_call_id)
    assert not pendientes, f"tool_calls sin respuesta: {pendientes}"
