"""La cola de seguimiento de Ronald.

    .venv/Scripts/python.exe -m streamlit run app/main.py

Importa `agente/` y no al revés. Aquí no hay lógica de decisión: la interfaz
muestra lo que el grafo produjo y recoge la aprobación, que es la única cosa
que la aplicación aporta al sistema y que el sistema no puede hacer solo.
"""

import hmac
import sys
import uuid
from pathlib import Path

import streamlit as st
from langgraph.types import Command

# Streamlit Cloud ejecuta este fichero directamente, así que `sys.path[0]` es
# `app/` y no la raíz del repositorio: `agente` no sería importable. En local no
# se nota, porque `python -m streamlit` mete el directorio de trabajo en la
# ruta. Insertar la raíz aquí arriba es lo único que hace falta y sirve en los
# dos sitios. Va antes de los imports del proyecto a propósito.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from agente import grafo, leads, persistencia  # noqa: E402
from agente.config import ajustes  # noqa: E402
from agente.traza import Traza  # noqa: E402

st.set_page_config(page_title="RG Wallcovering — follow-up queue", page_icon="📋")


# --- Puerta ---------------------------------------------------------------


def autorizado() -> bool:
    """Control de acceso: una puerta, no una autorización.

    Lo que evidencia el criterio S2 es el registro de aprobación del gate, no
    haber entrado aquí (03_spec.md §12.1). `compare_digest` evita filtrar la
    longitud correcta por tiempo de respuesta.
    """
    if st.session_state.get("entrado"):
        return True
    if not ajustes.app_password:
        st.error(
            "APP_PASSWORD no está configurada. La aplicación no se sirve sin "
            "control de acceso: es la cola de leads de un negocio real."
        )
        return False

    with st.form("acceso"):
        clave = st.text_input("Access code", type="password")
        if st.form_submit_button("Enter"):
            if hmac.compare_digest(clave, ajustes.app_password):
                st.session_state["entrado"] = True
                st.rerun()
            else:
                st.error("Not recognised.")
    return False


if not autorizado():
    st.stop()

# La inyección de fallos es una herramienta de desarrollo. Que quede encendida
# en producción convertiría cada envío en una ruleta, así que se ve.
if ajustes.inyeccion[0]:
    st.warning(f"Fault injection is ON: {ajustes.inyectar_fallo}")


# --- Estado de la sesión --------------------------------------------------

st.session_state.setdefault("hilo", f"ui-{uuid.uuid4().hex[:8]}")
st.session_state.setdefault("traza", None)
st.session_state.setdefault("estado", None)


def _app_grafo():
    if "grafo" not in st.session_state:
        st.session_state["traza"] = Traza()
        st.session_state["grafo"] = grafo.construir(traza=st.session_state["traza"])
    return st.session_state["grafo"]


def _cfg():
    return {
        "configurable": {"thread_id": st.session_state["hilo"]},
        "recursion_limit": 60,
    }


# --- Cabecera -------------------------------------------------------------

st.title("Follow-up queue")
st.caption(
    "The agent decides what should happen next with an enquiry. "
    "Nothing leaves this building without you approving it."
)

registros = {r["lead_id"]: r for r in leads.leer(leads.DISENO)}

col_a, col_b = st.columns([3, 1])
with col_a:
    elegido = st.selectbox(
        "Enquiry",
        options=list(registros),
        format_func=lambda k: f"{k} — {registros[k].get('nombre') or 'no name'}"
        f" · {registros[k].get('espacio', '')[:45]}",
    )
with col_b:
    st.write("")
    arrancar = st.button("Work this one", type="primary", use_container_width=True)

lead = registros[elegido]

with st.expander("The enquiry as it was captured"):
    st.write(f"**Contact:** {lead.get('email') or lead.get('telefono') or '— none —'}")
    st.write(f"**Location:** {lead.get('ubicacion') or '— not given —'}")
    st.write(f"**Timing:** {lead.get('plazo') or '— not given —'}")
    st.text(lead.get("resumen", ""))

historial = persistencia.historial(elegido)
if historial:
    with st.expander(f"Already attempted on this lead ({len(historial)})"):
        for h in historial:
            st.text(f"{h['cuando']}  {h['accion']} -> {h['resultado']}")

if arrancar:
    st.session_state["hilo"] = f"ui-{uuid.uuid4().hex[:8]}"
    st.session_state.pop("grafo", None)
    with st.spinner("Working…"):
        st.session_state["estado"] = _app_grafo().invoke(
            leads.a_estado(lead), _cfg()
        )

estado = st.session_state.get("estado")
if not estado:
    st.info("Pick an enquiry and press **Work this one**.")
    st.stop()


# --- Lo que hizo ----------------------------------------------------------

st.divider()
traza = st.session_state["traza"]

with st.expander("What it did, step by step", expanded=False):
    st.code(traza.resumen() if traza else "—", language=None)

accion = estado.get("accion")
if accion:
    st.subheader(f"Decision: `{accion.value}`")
    st.write(estado.get("motivo", ""))

if estado.get("hallazgos"):
    with st.expander(f"What it read ({len(estado['hallazgos'])} passages)"):
        for p in estado["hallazgos"]:
            st.markdown(f"**[{p.fragmento.tier}]** {p.fragmento.titulo}  ·  {p.score:.3f}")


# --- El gate --------------------------------------------------------------

interrupciones = estado.get("__interrupt__")
if interrupciones:
    carga = interrupciones[0].value
    st.divider()
    st.subheader("Approve before this goes out")

    p = carga["propuesta"]
    if p["tipo"] == "correo":
        destinatario = st.text_input("To", p["destinatario"])
        asunto = st.text_input("Subject", p["asunto"])
        cuerpo = st.text_area("Message", p["cuerpo"], height=260)
        editado = {"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo}
        cambiado = editado != {
            "destinatario": p["destinatario"], "asunto": p["asunto"], "cuerpo": p["cuerpo"]
        }
    else:
        st.write(f"**{p['titulo']}**")
        inicio = st.text_input("Starts", p["inicio"])
        fin = st.text_input("Ends", p["fin"])
        editado = {"inicio": inicio, "fin": fin, "titulo": p["titulo"],
                   "descripcion": p.get("descripcion", "")}
        cambiado = inicio != p["inicio"] or fin != p["fin"]

    if carga.get("fuentes"):
        st.caption("Claims rest on: " + ", ".join(carga["fuentes"]))
    else:
        # No es un detalle estético: un borrador que afirma algo sobre el
        # negocio sin fuente es el criterio S1 fallando en silencio.
        st.warning(
            "This draft cites no sources. Check that it makes no claim about "
            "price, coverage or timing before approving."
        )

    quien = st.text_input("Approving as", value="ronald")
    c1, c2, c3 = st.columns(3)
    decision = None
    if c1.button("Approve and send" if p["tipo"] == "correo" else "Approve and book",
                 type="primary", use_container_width=True):
        decision = {"decision": "editada" if cambiado else "aprobada",
                    "quien": quien, "editada": cambiado, "propuesta": editado}
    if c2.button("Reject", use_container_width=True):
        decision = {"decision": "rechazada", "quien": quien,
                    "motivo": st.session_state.get("motivo_rechazo", "")}
    c3.text_input("Why (if rejecting)", key="motivo_rechazo",
                  label_visibility="collapsed", placeholder="reason")

    if decision:
        with st.spinner("…"):
            st.session_state["estado"] = _app_grafo().invoke(Command(resume=decision), _cfg())
        st.rerun()

elif estado.get("resultado"):
    st.success(estado["resultado"])
elif estado.get("escalacion"):
    st.warning("Escalated to you — nothing was sent.")
    st.code(estado["escalacion"], language=None)
