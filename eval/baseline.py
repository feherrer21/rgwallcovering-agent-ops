"""El baseline determinista del que depende el falsador de `01` §5.5.

Es el script de cuatro ramas que el problem statement escribió como la
alternativa a construir un agente. Está implementado **en su versión más
fuerte**, no como un hombre de paja: si va a decidir si el agente se ganó su
lugar, tiene que ser el mejor script razonable que alguien escribiría en una
tarde, no el peor.

Concesiones que se le hacen deliberadamente, todas a su favor:

- Ve los mismos campos estructurados que el agente.
- Se le permite una heurística léxica sobre la promesa falsa, que es la clase
  de cosa que alguien añadiría en cuanto viera fallar el primer lead.
- Se le permite conocer el área de servicio y la política de la visita, o sea
  el corpus congelado en el día en que se escribió — que es precisamente lo que
  un script puede hacer y lo que `01` §5.3 argumenta que caduca.

No llama a ningún modelo y no cuesta nada por corrida.
"""

import re

#: Frases que delatan la promesa falsa. Es lo que un desarrollador escribiría
#: tras ver L01: cubre la redaccion directa y no la indirecta.
_GRATIS = re.compile(
    r"(isn't charged|is not charged|no charge|free|"
    r"sin costo|no tiene costo|gratis|gratuita)",
    re.IGNORECASE,
)
_VISITA = re.compile(
    r"(visit|assessment|estimate|visita|evaluaci[oó]n|presupuesto)", re.IGNORECASE
)

_DIRECCION_VALIDA = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")


def decidir(registro: dict) -> str:
    """Devuelve la accion que el script elegiría para este lead."""
    resumen = registro.get("resumen", "") or ""
    turnos = " ".join(t.get("text", "") for t in registro.get("turnos", []))
    texto = f"{resumen} {turnos}"

    email = (registro.get("email") or "").strip()
    telefono = (registro.get("telefono") or "").strip()

    # 1. Sin canal utilizable, no hay nada que enviar.
    if not email and not telefono:
        return "escalar_a_ronald"
    if email and not _DIRECCION_VALIDA.match(email):
        return "escalar_a_ronald"

    # 2. La heuristica de la promesa falsa. Concesion generosa al script.
    if _GRATIS.search(texto) and _VISITA.search(texto):
        return "escalar_a_ronald"

    # 3. Pidio una hora concreta.
    if re.search(r"\b(monday|tuesday|wednesday|thursday|friday|morning|afternoon)\b",
                 texto, re.IGNORECASE):
        return "proponer_horario"

    # 4. Falta el dato que bloquea todo lo demas.
    if not (registro.get("estilo_referencia") or "").strip():
        return "preparar_correo_pregunta"
    if not (registro.get("plazo") or "").strip():
        return "preparar_correo_pregunta"

    return "preparar_correo_visita"


def sin_email(registro: dict) -> bool:
    """Util para reportar por que el script escalo, cuando escalo."""
    return not (registro.get("email") or "").strip()
