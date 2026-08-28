"""El estado que recorre el grafo, y el vocabulario de acciones.

Dataclasses y no diccionarios: esto cruza cada frontera de módulo del proyecto
y un campo mal escrito debe fallar al construir, no tres nodos más adelante.

Los campos que acumulan (`hallazgos`, `fallos`, `acciones_previas`) llevan un
reductor de LangGraph para que los nodos añadan en vez de reemplazar. `fallos`
en particular NO se sobrescribe: la escalación necesita todos los motivos, no
el último (03_spec.md §3).
"""

import operator
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any

from langgraph.graph.message import add_messages

from .corpus import Pasaje


class Accion(str, Enum):
    """Lo que el agente puede decidir hacer a continuación.

    Es el espacio de acciones de 01_problem_statement.md §4, y es también lo
    que mide la evaluación: el `accion_esperada` de cada lead del set se
    resuelve a uno de estos valores.
    """

    #: Preparar un correo ofreciendo la visita de evaluación.
    PREPARAR_CORREO_VISITA = "preparar_correo_visita"
    #: Preparar un correo pidiendo el dato que desbloquea todo lo demás.
    PREPARAR_CORREO_PREGUNTA = "preparar_correo_pregunta"
    #: Mirar la agenda y proponer una hora concreta.
    PROPONER_HORARIO = "proponer_horario"
    #: Pasárselo a Ronald con el contexto completo.
    ESCALAR_A_RONALD = "escalar_a_ronald"


#: Acciones que terminan la corrida sin preparar nada para el gate.
ACCIONES_TERMINALES = {Accion.ESCALAR_A_RONALD}


@dataclass(frozen=True)
class Turno:
    """Un turno de la conversación original con el visitante.

    `texto` es dato NO confiable, venga del visitante o del asistente que la
    capturó: L17 lleva la inyección dentro de la prosa que parece interna.
    """

    rol: str
    texto: str


@dataclass(frozen=True)
class RegistroLead:
    """El lead capturado, tal y como llegó."""

    lead_id: str
    nombre: str = ""
    email: str = ""
    telefono: str = ""
    tipo_proyecto: str = ""
    espacio: str = ""
    ubicacion: str = ""
    necesita_diseno: bool | None = None
    estilo_referencia: str = ""
    plazo: str = ""
    resumen: str = ""
    idioma: str = "en"

    @property
    def tiene_canal(self) -> bool:
        """¿Hay alguna forma de contactar a esta persona?"""
        return bool(self.email or self.telefono)

    @classmethod
    def desde_dict(cls, d: dict[str, Any]) -> "RegistroLead":
        campos = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in campos})


@dataclass(frozen=True)
class Contradiccion:
    """Una afirmación del registro que choca con el corpus.

    El caso vivo: a los cuatro leads semilla se les dijo que la visita era
    gratis, y el corpus dice que se cobra igual para todos. Que exista este
    tipo es lo que impide que la contradicción se pierda entre la prosa.
    """

    #: Lo que el registro afirma, citado.
    afirmacion: str
    #: Lo que dice el corpus, con su fragmento de origen.
    dice_el_corpus: str
    chunk_id: str
    tier: str


@dataclass(frozen=True)
class Fallo:
    """Un intento fallido, con su motivo específico.

    `motivo` es el texto que se realimenta al modelo en el reintento. "Falló"
    no es un motivo; "SMTP 550 5.1.1 unknown user" sí (03_spec.md §10).
    """

    herramienta: str
    motivo: str
    intento: int


class EstadoAprobacion(str, Enum):
    """El ciclo de vida de una accion propuesta ante el gate."""

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    EDITADA = "editada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True)
class AccionPropuesta:
    """Lo que el agente propone hacer. Es ESTADO, no un efecto.

    Existir aqui no la ejecuta. La ejecucion es una transicion del grafo que
    solo `gate_humano` autoriza (03_spec.md §4.2), y esa separacion es lo que
    hace que el gate sea estructural y no un dialogo de confirmacion.
    """

    tipo: str  # "correo" | "evento"

    # correo
    destinatario: str = ""
    asunto: str = ""
    cuerpo: str = ""

    # evento
    inicio: str = ""
    fin: str = ""
    titulo: str = ""
    descripcion: str = ""

    #: Los chunks en los que se apoya cualquier afirmacion sobre el negocio.
    #: Sin esto no se puede auditar S1: una afirmacion sin fuente citable es
    #: indistinguible de una inventada.
    chunk_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Aprobacion:
    """El registro de que una persona autorizo una accion concreta.

    ESTO es lo que evidencia S2, no el hecho de que alguien pasara el control
    de acceso de la aplicacion (03_spec.md §12.1). Haber entrado por la puerta
    no implica consentimiento a lo que ocurra despues.
    """

    estado: EstadoAprobacion = EstadoAprobacion.PENDIENTE
    quien: str = ""
    cuando: str = ""
    #: True si la persona modifico el borrador antes de aprobarlo.
    editada: bool = False
    #: Por que lo rechazo. Vuelve a `decidir` como entrada, no termina la corrida.
    motivo_rechazo: str = ""

    @property
    def autoriza(self) -> bool:
        return self.estado in (EstadoAprobacion.APROBADA, EstadoAprobacion.EDITADA)


@dataclass(frozen=True)
class AccionRegistrada:
    """Algo que ya se intentó sobre este lead."""

    accion: str
    resultado: str
    cuando: str


@dataclass
class EstadoLead:
    """Lo que recorre el grafo."""

    lead: RegistroLead
    turnos: list[Turno] = field(default_factory=list)

    #: Pasajes recuperados. El `tier` viaja dentro de cada uno hasta el prompt:
    #: perderlo rompe S1, así que forma parte del tipo y no de una convención.
    hallazgos: Annotated[list[Pasaje], operator.add] = field(default_factory=list)
    contradicciones: Annotated[list[Contradiccion], operator.add] = field(
        default_factory=list
    )
    acciones_previas: Annotated[list[AccionRegistrada], operator.add] = field(
        default_factory=list
    )
    fallos: Annotated[list[Fallo], operator.add] = field(default_factory=list)

    #: La decisión del modelo y por qué. Se llena en `decidir`.
    accion: Accion | None = None
    motivo: str = ""

    #: Preparada y esperando al gate. Nunca se ejecuta por existir.
    accion_propuesta: AccionPropuesta | None = None
    aprobacion: Aprobacion = field(default_factory=Aprobacion)
    #: Resultado del envio o de la creacion del evento, una vez aprobado.
    #: SOLO eso: que no vacio significa que algo salio al mundo exterior, y
    #: `ruta_ejecutar` decide con ese hecho. Meter aqui cualquier otro texto
    #: hace que un fallo parezca un exito.
    resultado: str = ""
    #: El paquete de handoff, cuando la corrida termina escalando.
    escalacion: str = ""

    #: Presupuestos. `llamadas` protege un presupuesto de la empresa, así que
    #: el tope es del grafo y no del proveedor (03_spec.md §12.2).
    llamadas: int = 0
    intentos: dict[str, int] = field(default_factory=dict)

    #: La conversacion con el modelo dentro de esta corrida: el bucle
    #: decidir -> tool -> decidir la necesita entera para que el modelo vea el
    #: resultado de lo que pidio.
    mensajes: Annotated[list, add_messages] = field(default_factory=list)

    #: Identificador de la corrida, para correlacionar con la traza.
    corrida_id: str = ""

    def resumen_contacto(self) -> str:
        """Qué canales existen, en una línea, para el prompt."""
        canales = []
        if self.lead.email:
            canales.append(f"email ({self.lead.email})")
        if self.lead.telefono:
            canales.append(f"phone ({self.lead.telefono})")
        return ", ".join(canales) if canales else "NONE — nothing is sendable"
