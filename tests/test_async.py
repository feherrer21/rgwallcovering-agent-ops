"""Suite asincrona sobre el bucle del agente, con las herramientas mockeadas.

El grafo se ejecuta con `ainvoke`, que es el camino que usaria un frontend que
no quiere bloquear un hilo mientras el gate espera a una persona. Que el bucle
funcione sincronamente no implica que funcione asi: los nodos son funciones
sincronas y LangGraph las despacha a un executor, y esa diferencia es
exactamente donde aparecen los fallos de este tipo.

Nada aqui llama al modelo ni a un servicio externo.
"""

import asyncio

import pytest
from langchain_core.messages import AIMessage
from langgraph.types import Command

from agente import correo, grafo, persistencia
from agente.config import ajustes
from agente.estado import Accion, EstadoLead, RegistroLead
from agente.traza import Traza

pytestmark = pytest.mark.asyncio


class LLMFalso:
    """Sincrono a proposito: es lo que LangGraph tiene que despachar bien."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.vistas = []

    def bind_tools(self, _t):
        return self

    def invoke(self, mensajes):
        self.vistas.append(mensajes)
        return self.respuestas.pop(0)


def _decision(accion, motivo="m"):
    return AIMessage(content="", tool_calls=[{
        "name": "proponer_siguiente_accion",
        "args": {"accion": accion, "motivo": motivo}, "id": "d1"}])


def _busqueda(consulta="is the assessment visit charged"):
    return AIMessage(content="", tool_calls=[{
        "name": "buscar_corpus", "args": {"consulta": consulta}, "id": "b1"}])


def _borrador(destinatario="t@example.com", cuerpo="Hello there."):
    return AIMessage(content="", tool_calls=[{
        "name": "redactar_correo",
        "args": {"destinatario": destinatario, "asunto": "Your enquiry",
                 "cuerpo": cuerpo, "chunk_ids": []},
        "id": "r1"}])


def _estado(**kw):
    campos = {"lead_id": "A01", "nombre": "Async", "email": "t@example.com"}
    campos.update(kw)
    return EstadoLead(lead=RegistroLead(**campos))


def _cfg(nombre):
    return {"configurable": {"thread_id": f"async-{nombre}"}, "recursion_limit": 40}


@pytest.fixture
async def saver(tmp_path):
    """Checkpointer asincrono por prueba, en su propio fichero."""
    return await persistencia.checkpointer_async(tmp_path / "cp.sqlite")


# --- El bucle -------------------------------------------------------------


async def test_el_bucle_decide_de_forma_asincrona(saver):
    llm = LLMFalso([_decision("escalar_a_ronald")])
    app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
    final = await app.ainvoke(_estado(), _cfg("decide"))
    assert final["accion"] is Accion.ESCALAR_A_RONALD
    assert final["escalacion"], "la escalacion debio construirse"


async def test_la_herramienta_se_ejecuta_y_su_salida_vuelve_al_modelo(corpus_real, saver):
    llm = LLMFalso([_busqueda(), _decision("escalar_a_ronald")])
    app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
    final = await app.ainvoke(_estado(), _cfg("tool"))
    assert final["hallazgos"]
    assert any(getattr(m, "type", "") == "tool" for m in llm.vistas[1])


async def test_se_detiene_en_el_gate_sin_ejecutar_nada(monkeypatch, saver):
    monkeypatch.setattr(correo, "enviar", lambda *a: pytest.fail("no debio enviar"))
    llm = LLMFalso([_decision("preparar_correo_visita"), _borrador()])
    app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
    final = await app.ainvoke(_estado(), _cfg("gate"))
    assert final["__interrupt__"]
    assert not final.get("resultado")


async def test_aprobar_de_forma_asincrona_ejecuta_lo_aprobado(monkeypatch, saver):
    enviados = []
    monkeypatch.setattr(correo, "enviar", lambda d, a, c: enviados.append((d, c))
                        or correo.ResultadoEnvio(d, a, "id"))
    llm = LLMFalso([_decision("preparar_correo_visita"), _borrador(cuerpo="Exacto.")])
    app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
    cfg = _cfg("aprobar")
    await app.ainvoke(_estado(), cfg)
    final = await app.ainvoke(
        Command(resume={"decision": "aprobada", "quien": "ronald"}), cfg)
    assert enviados == [("t@example.com", "Exacto.")]
    assert final["aprobacion"].quien == "ronald"


# --- La ruta de recuperacion ---------------------------------------------


async def test_recuperacion_asincrona_con_el_motivo_exacto(monkeypatch, saver):
    """Fallo inyectado, motivo literal de vuelta, segundo intento correcto."""
    monkeypatch.setattr(ajustes, "inyectar_fallo", "correo:1")
    monkeypatch.setattr(correo, "_inyectados", 0)
    enviados = []
    real = correo.enviar
    monkeypatch.setattr(correo, "enviar", lambda d, a, c: (
        correo._quizas_inyectar(), enviados.append(d),
        correo.ResultadoEnvio(d, a, "id"))[-1])

    llm = LLMFalso([
        _decision("preparar_correo_visita"), _borrador(),
        _decision("preparar_correo_visita"), _borrador(),
    ])
    app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
    cfg = _cfg("recuperar")
    await app.ainvoke(_estado(), cfg)
    tras_primero = await app.ainvoke(
        Command(resume={"decision": "aprobada", "quien": "ronald"}), cfg)

    # El primer envio fallo y el bucle volvio a preparar; el motivo literal
    # tuvo que llegar al modelo.
    texto = " ".join(str(getattr(m, "content", "")) for v in llm.vistas for m in v)
    assert "421 4.7.0" in texto
    assert "you already approved" in texto
    assert tras_primero["__interrupt__"], "debio volver al gate con el nuevo borrador"

    final = await app.ainvoke(
        Command(resume={"decision": "aprobada", "quien": "ronald"}), cfg)
    assert enviados == ["t@example.com"]
    assert "email sent" in final["resultado"]


async def test_agotar_el_presupuesto_escala_de_forma_asincrona(monkeypatch, saver):
    monkeypatch.setattr(ajustes, "reintentos_por_tool", 1)
    llm = LLMFalso([_decision("preparar_correo_visita"),
                    _borrador(destinatario="roto@gmailcom")] * 4)
    app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
    final = await app.ainvoke(_estado(), _cfg("agotar"))
    assert final["accion"] is Accion.ESCALAR_A_RONALD
    assert final["escalacion"]
    assert not final.get("__interrupt__")


# --- Concurrencia ---------------------------------------------------------


async def test_varios_leads_a_la_vez_no_se_mezclan(corpus_real, saver):
    """Cada lead tiene su hilo: el estado de uno no puede filtrarse a otro.

    Ronald trabaja una cola; si dos corridas comparten estado, un borrador
    acaba dirigido a la persona equivocada.
    """
    async def corre(n):
        llm = LLMFalso([_decision("escalar_a_ronald", motivo=f"motivo-{n}")])
        app = grafo.construir(llm=llm, traza=Traza(), checkpointer=saver)
        return await app.ainvoke(
            _estado(lead_id=f"C{n:02}", email=f"c{n}@example.com"),
            _cfg(f"conc-{n}"))

    resultados = await asyncio.gather(*(corre(n) for n in range(4)))
    for n, r in enumerate(resultados):
        assert r["motivo"] == f"motivo-{n}"
        assert f"c{n}@example.com" in r["escalacion"]
