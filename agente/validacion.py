"""Contratos de lo que producen el modelo y las herramientas.

Una herramienta que devolvió algo no es una herramienta que devolvió algo
usable. Aquí se comprueba, y cuando falla el mensaje dice **qué** falló, porque
ese texto es lo que se le realimenta al modelo en el reintento: "falló" no es
un motivo (03_spec.md §10).

Dónde se valida importa tanto como qué. El borrador se valida **antes** del
gate: una dirección inválida que llega hasta Ronald le hace aprobar algo que no
puede ejecutarse, y descubrirlo después de su aprobación convierte su decisión
en ruido.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field, ValidationError, field_validator

from .calendario import HORA_APERTURA, HORA_CIERRE, TZ
from .correo import ErrorDeEnvio, validar_destinatario

__all__ = [
    "BorradorCorreo",
    "BorradorEvento",
    "ErrorDeValidacion",
    "validar_borrador",
]


class ErrorDeValidacion(ValueError):
    """El motivo, redactado para que el modelo pueda corregir con él."""


class BorradorCorreo(BaseModel):
    """Lo que `redactar_correo` tiene que producir para poder enviarse."""

    destinatario: str
    asunto: str = Field(min_length=1)
    cuerpo: str = Field(min_length=1)
    chunk_ids: tuple[str, ...] = ()

    @field_validator("destinatario")
    @classmethod
    def _direccion(cls, v: str) -> str:
        try:
            validar_destinatario(v)
        except ErrorDeEnvio as exc:
            raise ValueError(str(exc)) from exc
        return v.strip()

    @field_validator("cuerpo")
    @classmethod
    def _sin_marcadores(cls, v: str) -> str:
        # Un borrador con un hueco sin rellenar delata que el modelo no tenía
        # el dato. Enviarlo con el corchete dentro es peor que no enviarlo.
        for marcador in ("[", "TODO", "XXX", "{{"):
            if marcador in v:
                raise ValueError(
                    f"the body still contains a placeholder ({marcador!r}). If a "
                    "detail is missing, ask for it or escalate — do not send a "
                    "template with a gap in it"
                )
        return v


class BorradorEvento(BaseModel):
    """Lo que `redactar_evento` tiene que producir para poder crearse."""

    inicio: datetime
    fin: datetime
    titulo: str = Field(min_length=1)
    descripcion: str = ""

    @field_validator("inicio", "fin")
    @classmethod
    def _con_zona(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(
                "the datetime has no timezone. Providence is UTC-4 in summer "
                "and UTC-5 in winter, so a naive time is ambiguous by an hour"
            )
        return v

    def model_post_init(self, _ctx) -> None:
        if self.inicio >= self.fin:
            raise ValueError("the event ends before it starts")
        if self.fin - self.inicio > timedelta(hours=8):
            raise ValueError("an assessment visit longer than 8 hours is not plausible")
        local = self.inicio.astimezone(TZ)
        if local.weekday() >= 5:
            raise ValueError(f"{local:%A} is not a working day")
        if not (HORA_APERTURA <= local.hour < HORA_CIERRE):
            raise ValueError(
                f"{local:%H:%M} is outside working hours "
                f"({HORA_APERTURA}:00-{HORA_CIERRE}:00)"
            )


def _mensaje(exc: ValidationError) -> str:
    """Aplana los errores de pydantic a algo que el modelo pueda accionar."""
    partes = []
    for e in exc.errors():
        campo = ".".join(str(x) for x in e["loc"]) or "value"
        msg = e["msg"].removeprefix("Value error, ")
        partes.append(f"{campo}: {msg}")
    return "; ".join(partes)


def validar_borrador(tipo: str, datos: dict) -> BorradorCorreo | BorradorEvento:
    """Valida el borrador antes de que llegue al gate.

    Levanta `ErrorDeValidacion` con un texto que sirve de instrucción de
    corrección, no de diagnóstico.
    """
    modelo = BorradorCorreo if tipo == "correo" else BorradorEvento
    try:
        return modelo(**datos)
    except ValidationError as exc:
        raise ErrorDeValidacion(_mensaje(exc)) from exc
