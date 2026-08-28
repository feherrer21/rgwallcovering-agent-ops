"""Carga de leads del set de evaluacion al estado del grafo."""

import json
from pathlib import Path

from .config import PROYECTO_DIR
from .estado import EstadoLead, RegistroLead, Turno

DISENO = PROYECTO_DIR / "eval" / "leads_design.jsonl"
HOLDOUT = PROYECTO_DIR / "eval" / "leads_holdout.jsonl"


def leer(ruta: Path) -> list[dict]:
    """Lee un fichero de leads. Las etiquetas viajan aparte del estado."""
    with ruta.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def a_estado(registro: dict) -> EstadoLead:
    """Convierte un registro del set en estado inicial del grafo.

    `accion_esperada` y `por_que` NO entran: son la etiqueta, y meterlas en el
    estado seria pasarle al agente la respuesta que se le esta midiendo.
    """
    return EstadoLead(
        lead=RegistroLead.desde_dict(registro),
        turnos=[Turno(rol=t["role"], texto=t["text"]) for t in registro.get("turnos", [])],
    )


def por_id(lead_id: str, ruta: Path = DISENO) -> EstadoLead:
    for r in leer(ruta):
        if r["lead_id"] == lead_id:
            return a_estado(r)
    raise KeyError(f"No existe el lead {lead_id} en {ruta.name}")
