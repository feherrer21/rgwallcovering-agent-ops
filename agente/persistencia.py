"""Las dos memorias del sistema, que resuelven necesidades distintas.

**Checkpointer duradero** (`SqliteSaver`). Elegido sobre uno en memoria por el
gate, no por gusto: el grafo se detiene esperando a una persona, y la
aprobación llega en tiempo humano — minutos después, tras refrescar la página.
Si el estado de la corrida muere con el proceso, esa aprobación no resucita
nada: la acción preparada se pierde en silencio, que es exactamente el fallo
que el gate existe para impedir (03_spec.md §7.1).

**Ledger por lead**, append-only. Qué se intentó, cuándo y con qué resultado.
Vive aparte del checkpointer porque tiene otra vida y otro lector: el
seguimiento es multi-sesión por naturaleza —un correo el lunes, una respuesta
el miércoles— y "escalar tras fallos repetidos" no significa nada si la
repetición solo se cuenta dentro de un proceso. Además Ronald lo lee, y un
blob de checkpointer no está hecho para ojos humanos.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .config import ajustes

log = logging.getLogger(__name__)

#: Tipos propios que viajan dentro del estado y por tanto se serializan. Se
#: declaran explícitamente en vez de dejar que el serializador los acepte por
#: omisión: deserializar cualquier cosa que aparezca en un fichero es una vía
#: de ejecución que nadie pidió.
TIPOS_PERMITIDOS = [
    ("agente.estado", "RegistroLead"),
    ("agente.estado", "Turno"),
    ("agente.estado", "Accion"),
    ("agente.estado", "AccionPropuesta"),
    ("agente.estado", "Aprobacion"),
    ("agente.estado", "EstadoAprobacion"),
    ("agente.estado", "Contradiccion"),
    ("agente.estado", "Fallo"),
    ("agente.estado", "AccionRegistrada"),
    ("agente.corpus", "Pasaje"),
    ("agente.corpus", "Fragmento"),
]


def serializador() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=TIPOS_PERMITIDOS)


def checkpointer(ruta=None) -> SqliteSaver:
    """Abre el checkpointer duradero. El llamante es dueño de la conexión."""
    ruta = ruta or ajustes.checkpoint_db
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False porque Streamlit reentra desde otro hilo; el
    # acceso sigue siendo secuencial, no hay concurrencia real que proteger.
    conn = sqlite3.connect(str(ruta), check_same_thread=False)
    return SqliteSaver(conn, serde=serializador())


async def checkpointer_async(ruta=None) -> AsyncSqliteSaver:
    """Version asincrona del mismo almacen.

    Hace falta de verdad, no por simetria: `SqliteSaver` levanta
    NotImplementedError ante cualquier metodo async, asi que un frontend que
    use `ainvoke` -lo natural cuando el gate deja el grafo esperando a una
    persona- se queda sin checkpointer duradero y por tanto sin gate que
    sobreviva a un reinicio. Se descubrio al escribir la suite asincrona.
    """
    import aiosqlite

    ruta = ruta or ajustes.checkpoint_db
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(ruta))
    return AsyncSqliteSaver(conn, serde=serializador())


# --- Ledger ---------------------------------------------------------------


def registrar(lead_id: str, accion: str, resultado: str, **extra: Any) -> None:
    """Añade una línea al ledger. Nunca reescribe ni borra.

    No se registra el contenido de la acción: el cuerpo de un correo lleva
    datos personales del lead y este fichero no es el sitio (CLAUDE.md).
    """
    entrada = {
        "cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lead_id": lead_id,
        "accion": accion,
        "resultado": resultado,
        **extra,
    }
    try:
        ajustes.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with ajustes.ledger_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False, default=str) + "\n")
    except OSError:
        # Perder una línea del ledger degrada la memoria entre sesiones; que
        # tumbe una corrida en curso sería peor.
        log.exception("No se pudo escribir el ledger para %s", lead_id)


def historial(lead_id: str) -> list[dict[str, Any]]:
    """Lo que ya se intentó sobre este lead, en orden."""
    if not ajustes.ledger_file.exists():
        return []
    entradas = []
    with ajustes.ledger_file.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                # Una línea corrupta no puede impedir leer las demás.
                log.warning("Línea ilegible en el ledger")
                continue
            if registro.get("lead_id") == lead_id:
                entradas.append(registro)
    return entradas


def intentos_fallidos(lead_id: str, herramienta: str) -> int:
    """Cuántas veces ya falló esta herramienta con este lead.

    Cuenta a través de sesiones, que es el punto: un reintento que solo cuenta
    dentro de un proceso no es un presupuesto de reintentos.
    """
    return sum(
        1
        for e in historial(lead_id)
        if e.get("accion") == herramienta and e.get("resultado") == "fallo"
    )
