"""Validacion, reintento con motivo, y escalacion al agotar el presupuesto."""

import pytest
from langchain_core.messages import AIMessage

from agente import correo, escalacion, grafo, validacion
from agente.config import ajustes
from agente.estado import Accion, EstadoLead, Fallo, RegistroLead
from agente.traza import Traza


# --- Contratos (T5.1) -----------------------------------------------------


def test_borrador_con_direccion_invalida_se_rechaza():
    """El caso L12: invalida por un caracter."""
    with pytest.raises(validacion.ErrorDeValidacion, match="not a valid address"):
        validacion.validar_borrador("correo", {
            "destinatario": "j.torres@gmailcom", "asunto": "x", "cuerpo": "y"})


def test_borrador_con_hueco_sin_rellenar_se_rechaza():
    """Un marcador delata que faltaba un dato. Enviarlo es peor que no enviar."""
    with pytest.raises(validacion.ErrorDeValidacion, match="placeholder"):
        validacion.validar_borrador("correo", {
            "destinatario": "a@example.com", "asunto": "x",
            "cuerpo": "Hola [NOMBRE], la visita cuesta..."})


def test_borrador_valido_pasa():
    b = validacion.validar_borrador("correo", {
        "destinatario": "a@example.com", "asunto": "Your enquiry",
        "cuerpo": "Thanks for getting in touch.", "chunk_ids": ["c1"]})
    assert b.destinatario == "a@example.com"


@pytest.mark.parametrize("inicio,fin,error", [
    ("2026-09-05T09:00:00-04:00", "2026-09-05T10:00:00-04:00", "working day"),   # sabado
    ("2026-09-01T22:00:00-04:00", "2026-09-01T23:00:00-04:00", "working hours"),
    ("2026-09-01T11:00:00-04:00", "2026-09-01T10:00:00-04:00", "ends before"),
    ("2026-09-01T08:00:00", "2026-09-01T09:00:00", "no timezone"),
])
def test_eventos_imposibles_se_rechazan(inicio, fin, error):
    with pytest.raises(validacion.ErrorDeValidacion, match=error):
        validacion.validar_borrador("evento", {
            "inicio": inicio, "fin": fin, "titulo": "Visita"})


def test_el_motivo_sirve_para_corregir_no_solo_para_diagnosticar():
    """El texto que se realimenta tiene que decir que hacer."""
    try:
        validacion.validar_borrador("evento", {
            "inicio": "2026-09-01T08:00:00", "fin": "2026-09-01T09:00:00",
            "titulo": "x"})
    except validacion.ErrorDeValidacion as exc:
        assert "Providence" in str(exc) and "ambiguous" in str(exc)


# --- Reintento con el motivo (T5.2, T5.3) ---------------------------------


class LLMFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.vistas = []

    def bind_tools(self, _t):
        return self

    def invoke(self, mensajes):
        self.vistas.append(mensajes)
        return self.respuestas.pop(0)


def _decision(accion="preparar_correo_visita"):
    return AIMessage(content="", tool_calls=[{
        "name": "proponer_siguiente_accion",
        "args": {"accion": accion, "motivo": "m"}, "id": "d1"}])


def _borrador(destinatario, cuerpo="Hello there."):
    return AIMessage(content="", tool_calls=[{
        "name": "redactar_correo",
        "args": {"destinatario": destinatario, "asunto": "Your enquiry",
                 "cuerpo": cuerpo}, "id": "r1"}])


def _estado():
    return EstadoLead(lead=RegistroLead(lead_id="F01", nombre="T",
                                        email="t@example.com"))


def test_el_reintento_lleva_el_motivo_exacto():
    """No 'fallo, reintenta': el texto del validador, literal."""
    llm = LLMFalso([
        _decision(), _borrador("roto@gmailcom"),   # invalido
        _decision(), _borrador("bien@example.com"),  # corregido
    ])
    app = grafo.construir(llm=llm, traza=Traza())
    r = app.invoke(_estado(), {"configurable": {"thread_id": "reintento"},
                               "recursion_limit": 40})
    # El modelo tuvo que ver el motivo concreto en su siguiente turno.
    texto = " ".join(str(getattr(m, "content", "")) for v in llm.vistas for m in v)
    assert "not a valid address" in texto
    assert "fabricating" in texto
    assert r["__interrupt__"], "el borrador corregido debio llegar al gate"


def test_nada_llego_al_cliente_se_dice_en_el_reintento():
    """El modelo tiene que saber que el fallo no tuvo efecto externo."""
    llm = LLMFalso([_decision(), _borrador("roto@gmailcom"),
                    _decision(), _borrador("bien@example.com")])
    app = grafo.construir(llm=llm, traza=Traza())
    app.invoke(_estado(), {"configurable": {"thread_id": "sin-efecto"},
                           "recursion_limit": 40})
    texto = " ".join(str(getattr(m, "content", "")) for v in llm.vistas for m in v)
    assert "Nothing reached the customer" in texto or "not sent to anyone" in texto


def test_agotar_el_presupuesto_escala_en_vez_de_girar(monkeypatch):
    monkeypatch.setattr(ajustes, "reintentos_por_tool", 2)
    # Siempre invalido: el presupuesto se agota.
    llm = LLMFalso([_decision(), _borrador("roto@gmailcom")] * 6)
    app = grafo.construir(llm=llm, traza=Traza())
    r = app.invoke(_estado(), {"configurable": {"thread_id": "agotado"},
                               "recursion_limit": 60})
    assert r["accion"] is Accion.ESCALAR_A_RONALD
    assert "retry budget is spent" in r["motivo"]
    assert not r.get("__interrupt__"), "no debio llegar al gate con un borrador roto"


# --- El paquete de escalacion (T5.4) --------------------------------------


def test_la_escalacion_lleva_todos_los_motivos_no_el_ultimo():
    estado = _estado()
    estado.motivo = "no se pudo entregar"
    estado.fallos = [
        Fallo("correo", "SMTP 550 5.1.1 unknown user", 1),
        Fallo("correo", "SMTP 421 service unavailable", 2),
    ]
    paquete = escalacion.construir(estado)
    assert "550" in paquete.texto and "421" in paquete.texto
    assert len(paquete.intentos) == 2


def test_la_escalacion_dice_que_no_se_envio_nada():
    paquete = escalacion.construir(_estado())
    assert "Nothing was sent" in paquete.texto


def test_la_escalacion_sin_canal_lo_dice():
    estado = EstadoLead(lead=RegistroLead(lead_id="L11", nombre="Steph"))
    assert "NONE" in escalacion.construir(estado).texto


def test_la_escalacion_solo_cita_fuentes_que_respaldan(corpus_real):
    """Nivel C explica, no respalda: llenaria el paquete de ruido."""
    estado = _estado()
    estado.hallazgos = corpus_real.buscar("is the assessment visit charged")
    paquete = escalacion.construir(estado)
    assert paquete.fuentes
    assert all(f.startswith("[A]") or f.startswith("[B]") for f in paquete.fuentes)


# --- Inyeccion deliberada (T7.1) ------------------------------------------


def test_la_inyeccion_esta_apagada_por_defecto():
    """Un interruptor de romper cosas que quedara encendido seria peor que no
    tenerlo. Se comprueba aqui y se comprueba al arrancar la app."""
    assert ajustes.inyeccion == ("", 0)


def test_la_inyeccion_falla_solo_las_veces_pedidas(monkeypatch):
    monkeypatch.setattr(ajustes, "inyectar_fallo", "correo:2")
    monkeypatch.setattr(correo, "_inyectados", 0)
    for intento in (1, 2):
        with pytest.raises(correo.ErrorDeEnvio, match="421"):
            correo._quizas_inyectar()
    correo._quizas_inyectar()  # la tercera ya no falla


def test_el_motivo_inyectado_se_declara_como_tal(monkeypatch):
    """Un fallo simulado que se hace pasar por real contamina la evidencia."""
    monkeypatch.setattr(ajustes, "inyectar_fallo", "correo:1")
    monkeypatch.setattr(correo, "_inyectados", 0)
    with pytest.raises(correo.ErrorDeEnvio, match="injected failure"):
        correo._quizas_inyectar()


def test_el_reintento_dice_donde_fallo_no_solo_que_fallo():
    """Medido: con un mensaje ambiguo, el modelo le contaba a Ronald que el
    correo no se habia podido preparar, cuando se habia preparado y el propio
    Ronald lo habia aprobado. Ver docs/evidence/03."""
    from agente.estado import Aprobacion, EstadoAprobacion

    llm = LLMFalso([_decision(), _borrador("bien@example.com")])
    app = grafo.construir(llm=llm, traza=Traza())
    estado = _estado()
    estado.fallos = [Fallo("correo", "SMTP 421 4.7.0 Temporary System Problem", 1)]
    estado.intentos = {"correo": 1}
    estado.aprobacion = Aprobacion(estado=EstadoAprobacion.APROBADA, quien="ronald")

    nodo = app.nodes["recuperar"]
    salida = nodo.invoke(estado)
    texto = salida["mensajes"][0].content
    assert "you already approved" in texto
    assert "the delivery is what failed" in texto
    assert "TEMPORARY" in texto
    assert "do not tell Ronald something happened that did not" in texto


# --- Citas inventadas (docs/evidence/09) ----------------------------------


def test_una_cita_a_un_fragmento_inexistente_se_rechaza():
    """Medido: el modelo cito UUIDs que no existen en el corpus.

    Una cita inventada es peor que ninguna: crea la apariencia de
    trazabilidad, que es justo lo que S1 existe para que sea real.
    """
    with pytest.raises(validacion.ErrorDeValidacion, match="do not exist"):
        validacion.validar_citas(["613045f2-9844-482a-a28d-1c39050d276f"],
                                 {"S0-ronald-0000"})


def test_citar_nada_es_valido():
    validacion.validar_citas([], {"S0-ronald-0000"})
    validacion.validar_citas(None, set())


def test_el_modelo_ve_el_chunk_id_que_se_le_pide_citar(corpus_real):
    """La causa raiz: se le pedia citar un identificador que nunca veia."""
    from agente import tools
    pasajes = corpus_real.buscar("is the assessment visit charged")
    salida = tools.formatear_pasajes(pasajes)
    for p in pasajes:
        assert f"chunk_id: {p.fragmento.chunk_id}" in salida
