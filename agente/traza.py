"""Traza paso a paso de una corrida del grafo.

Portkey ve las llamadas al modelo: cuánto costaron y cuánto tardaron. No ve
que `validar` rechazó una salida, ni que el modelo eligió buscar antes de
decidir, ni qué pasajes sostenían esa decisión. Las dos capas hacen falta y
ninguna sustituye a la otra (03_spec.md §11).

El fichero es JSONL, una línea por paso, para poder seguir una corrida a mano
sin herramientas. Vive en `traces/`, que está gitignoreado: una traza contiene
el contenido de la conversación. Lo que se entrega como evidencia se cura a
mano en `docs/evidence/` con personas sintéticas.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ajustes

log = logging.getLogger(__name__)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Traza:
    """Acumula los pasos de una corrida y los escribe a disco."""

    corrida_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    lead_id: str = ""
    modelo: str = ""
    pasos: list[dict[str, Any]] = field(default_factory=list)

    def paso(self, nodo: str, **datos: Any) -> None:
        """Registra un paso. `datos` es lo que ese nodo tenga que contar."""
        self.pasos.append({"t": _ahora(), "nodo": nodo, **datos})

    def decision(self, accion: str, motivo: str, uso: dict | None = None) -> None:
        """El modelo eligió una acción. Es el paso que hay que poder auditar."""
        self.paso("decidir", accion=accion, motivo=motivo, uso=uso or {})

    def tool(self, nombre: str, entrada: dict, resumen: str, n: int = 0) -> None:
        """Una herramienta se ejecutó.

        `resumen` y no la salida entera: la salida cruda puede ser el corpus
        completo formateado, y una traza que nadie lee por su tamaño no es
        observabilidad.
        """
        self.paso("tool", herramienta=nombre, entrada=entrada, resultado=resumen, n=n)

    def fallo(self, donde: str, motivo: str) -> None:
        self.paso("fallo", donde=donde, motivo=motivo)

    def escribir(self) -> Path | None:
        """Vuelca la traza. Un fallo aquí no puede tumbar la corrida."""
        try:
            ajustes.trazas_dir.mkdir(parents=True, exist_ok=True)
            ruta = ajustes.trazas_dir / f"{self.corrida_id}.jsonl"
            with ruta.open("w", encoding="utf-8") as f:
                cabecera = {
                    "t": _ahora(),
                    "nodo": "corrida",
                    "corrida_id": self.corrida_id,
                    "lead_id": self.lead_id,
                    "modelo": self.modelo,
                    "pasos": len(self.pasos),
                }
                f.write(json.dumps(cabecera, ensure_ascii=False) + "\n")
                for p in self.pasos:
                    f.write(json.dumps(p, ensure_ascii=False, default=str) + "\n")
            return ruta
        except OSError:
            # Perder la traza degrada la evidencia; perder la corrida por no
            # poder escribirla sería peor.
            log.exception("No se pudo escribir la traza %s", self.corrida_id)
            return None

    def resumen(self) -> str:
        """Una línea por paso, para leer una corrida en la terminal."""
        lineas = [f"corrida {self.corrida_id}  lead {self.lead_id}  {self.modelo}"]
        for p in self.pasos:
            nodo = p["nodo"]
            if nodo == "tool":
                lineas.append(
                    f"  tool   {p['herramienta']}({p['entrada']}) -> {p['resultado']}"
                )
            elif nodo == "decidir" and "accion" in p:
                lineas.append(f"  decide {p['accion']}  — {p['motivo'][:70]}")
            elif nodo == "decidir":
                # El otro paso que emite este nodo: pidió herramientas y sigue.
                lineas.append(f"  pide   {', '.join(p.get('pide', []))}")
            elif nodo == "fallo":
                lineas.append(f"  FALLO  {p['donde']}: {p['motivo'][:70]}")
            else:
                extra = {k: v for k, v in p.items() if k not in ("t", "nodo")}
                lineas.append(f"  {nodo:6} {extra if extra else ''}")
        return "\n".join(lineas)
