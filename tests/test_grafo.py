"""Pruebas del bucle, con el modelo mockeado.

No llaman al gateway: el grafo se prueba contra respuestas fabricadas, que es
lo que permite fijar el comportamiento sin gastar presupuesto ni depender de
que el modelo tenga un buen dia.
"""

import pytest
from langchain_core.messages import AIMessage

from agente import grafo
from agente.estado import Accion, EstadoLead, RegistroLead
from agente.traza import Traza


class LLMFalso:
    """Devuelve respuestas preparadas, una por invocacion."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.vistas = []

    def bind_tools(self, _tools):
        return self

    def invoke(self, mensajes):
        self.vistas.append(mensajes)
        return self.respuestas.pop(0)


def _decision(accion, motivo="porque si"):
    return AIMessage(content="", tool_calls=[{
        "name": "proponer_siguiente_accion",
        "args": {"accion": accion, "motivo": motivo},
        "id": "c1",
    }])


def _busqueda(consulta="is the assessment visit charged"):
    return AIMessage(content="", tool_calls=[{
        "name": "buscar_corpus", "args": {"consulta": consulta}, "id": "b1",
    }])


def _estado(**kwargs):
    campos = {"lead_id": "T01", "nombre": "Test", "email": "t@example.com"}
    campos.update(kwargs)
    return EstadoLead(lead=RegistroLead(**campos))


def test_decide_sin_buscar_cuando_no_hace_falta():
    llm = LLMFalso([_decision("preparar_correo_visita")])
    app = grafo.construir(llm=llm, traza=Traza())
    final = app.invoke(_estado())
    assert final["accion"] is Accion.PREPARAR_CORREO_VISITA
    assert len(llm.vistas) == 1


def test_busca_y_luego_decide(corpus_real):
    """El bucle cierra: la salida de la tool vuelve al modelo."""
    llm = LLMFalso([_busqueda(), _decision("escalar_a_ronald")])
    app = grafo.construir(llm=llm, traza=Traza())
    final = app.invoke(_estado())
    assert final["accion"] is Accion.ESCALAR_A_RONALD
    assert final["hallazgos"], "los pasajes recuperados no llegaron al estado"
    # La segunda invocacion tiene que haber visto el resultado de la tool.
    assert any(getattr(m, "type", "") == "tool" for m in llm.vistas[1])


def test_la_prosa_suelta_no_cuenta_como_decision():
    """Sin tool_call no hay decision: se le dice y se reintenta."""
    llm = LLMFalso([
        AIMessage(content="Creo que deberiamos escribirle."),
        _decision("escalar_a_ronald"),
    ])
    app = grafo.construir(llm=llm, traza=Traza())
    final = app.invoke(_estado())
    assert final["accion"] is Accion.ESCALAR_A_RONALD
    assert len(llm.vistas) == 2


def test_el_tope_de_llamadas_escala_en_vez_de_gastar():
    """Agotar el presupuesto no es un fallo silencioso: es una escalacion."""
    from agente.config import ajustes
    previo = ajustes.max_llamadas_por_lead
    ajustes.max_llamadas_por_lead = 2
    try:
        llm = LLMFalso([_busqueda(), _busqueda(), _decision("preparar_correo_visita")])
        app = grafo.construir(llm=llm, traza=Traza())
        final = app.invoke(_estado(), {"recursion_limit": 30})
        assert final["accion"] is Accion.ESCALAR_A_RONALD
        assert "limit" in final["motivo"].lower()
    finally:
        ajustes.max_llamadas_por_lead = previo


def test_la_traza_registra_la_decision_y_su_motivo():
    tz = Traza()
    llm = LLMFalso([_decision("escalar_a_ronald", "sin canal de contacto")])
    grafo.construir(llm=llm, traza=tz).invoke(_estado(email=""))
    decisiones = [p for p in tz.pasos if p["nodo"] == "decidir" and "accion" in p]
    assert decisiones and decisiones[0]["motivo"] == "sin canal de contacto"


def test_las_etiquetas_no_entran_en_el_estado():
    """accion_esperada nunca puede llegar al agente."""
    from agente import leads
    estado = leads.por_id("L04")
    volcado = str(estado.__dict__)
    assert "accion_esperada" not in volcado and "por_que" not in volcado
