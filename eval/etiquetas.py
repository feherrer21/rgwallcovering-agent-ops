"""Normaliza las etiquetas del set en algo puntuable.

Al escribir el set usé etiquetas compuestas — `buscar_luego_escalar`,
`consultar_calendario_luego_preparar` — que mezclan dos cosas distintas: qué
decidió el agente, y qué pasos tuvo que dar antes.

**Los datos no se reescriben.** Fueron commiteados antes de que existiera el
código y esa fecha es su valor; cambiarlos ahora, con resultados a la vista,
sería exactamente lo que `02_data_provenance.md` §2.4 se compromete a no hacer.
Se traducen aquí, la traducción se declara, y queda auditable frente al fichero
original.

La distinción importa al puntuar: un agente que llega a la acción correcta sin
haber consultado lo que debía consultar acertó por casualidad, y eso no es lo
mismo que acertar.
"""

from dataclasses import dataclass

#: etiqueta original -> (accion final esperada, herramientas que debieron usarse)
TRADUCCION: dict[str, tuple[str, tuple[str, ...]]] = {
    "escalar_a_ronald": ("escalar_a_ronald", ()),
    "preparar_correo_visita": ("preparar_correo_visita", ()),
    "preparar_correo_pregunta": ("preparar_correo_pregunta", ()),
    # Compuestas: la parte "luego_X" es la accion; la primera, un requisito.
    "buscar_luego_escalar": ("escalar_a_ronald", ("buscar_corpus",)),
    "buscar_luego_preparar_correo": (
        "preparar_correo_visita",
        ("buscar_corpus",),
    ),
    "consultar_calendario_luego_preparar": (
        "proponer_horario",
        ("leer_calendario",),
    ),
    # El "_luego_recuperar" describe lo que pasa DESPUES del gate, no la
    # decision. Como decision, este lead es un correo de visita.
    "preparar_correo_visita_luego_recuperar": ("preparar_correo_visita", ()),
}

#: Leads donde dos acciones son defendibles. Se puntuan contra ambas y se
#: reportan aparte: fingir que hay una sola respuesta correcta cuando no la
#: hay infla la puntuacion y esconde el desacuerdo real.
ALTERNATIVAS_DEFENDIBLES: dict[str, set[str]] = {
    # Plazo duro: ofrecer la visita y mirar la agenda son ambas razonables.
    "L04": {"preparar_correo_visita", "proponer_horario"},
    # Direccion irresoluble: intentar y fallar, o no intentar. El agente
    # eligio lo segundo por inspeccion (docs/evidence/03).
    "L20": {"preparar_correo_visita", "escalar_a_ronald"},
    # Sin estilo ni medidas: ofrecer la visita o preguntar. La etiqueta
    # defiende la visita; preguntar no es absurdo.
    "L08": {"preparar_correo_visita", "preparar_correo_pregunta"},
}


@dataclass(frozen=True)
class Esperado:
    lead_id: str
    accion: str
    herramientas: tuple[str, ...]
    alternativas: frozenset[str]

    def acierta(self, accion: str, estricto: bool = True) -> bool:
        if accion == self.accion:
            return True
        return not estricto and accion in self.alternativas


def esperado(registro: dict) -> Esperado:
    etiqueta = registro["accion_esperada"]
    if etiqueta not in TRADUCCION:
        raise KeyError(
            f"{registro['lead_id']}: etiqueta {etiqueta!r} sin traduccion. "
            "Anadirla aqui, nunca cambiar el dato."
        )
    accion, herramientas = TRADUCCION[etiqueta]
    return Esperado(
        lead_id=registro["lead_id"],
        accion=accion,
        herramientas=herramientas,
        alternativas=frozenset(
            ALTERNATIVAS_DEFENDIBLES.get(registro["lead_id"], set())
        ),
    )
