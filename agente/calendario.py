"""Lectura y escritura del calendario.

Leer es de solo lectura y la decide el modelo. Crear un evento es irreversible
y solo lo alcanza `ejecutar_irreversible` desde el gate (03_spec.md §4.2).

El calendario es uno **dedicado**, nunca `primary`: el calendario personal de
la cuenta contiene citas reales con invitados reales, y esos datos no pueden
entrar en un prompt (03_spec.md §12.3).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import ajustes

log = logging.getLogger(__name__)

TZ = ZoneInfo("America/New_York")  # el negocio está en Providence, RI

#: Jornada laboral. Proponer las 22:00 de un domingo sería técnicamente válido
#: y comercialmente absurdo, así que el contrato lo excluye.
HORA_APERTURA = 7
HORA_CIERRE = 18


class ErrorDeCalendario(RuntimeError):
    """La operación no salió. Lleva el motivo específico."""


@dataclass(frozen=True)
class Ocupado:
    """Un intervalo ocupado. Solo horas: los títulos no salen del calendario.

    Deliberado: el agente necesita saber CUÁNDO Ronald está ocupado, no con
    quién. Un título de evento es dato de un tercero y no tiene por qué viajar
    a un prompt.
    """

    inicio: datetime
    fin: datetime


def _servicio():
    if not ajustes.calendario_configurado:
        raise ErrorDeCalendario("Google Calendar credentials are not configured")
    if ajustes.calendar_id == "primary":
        # Salvaguarda dura, no una convención: 'primary' tiene citas reales.
        raise ErrorDeCalendario(
            "refusing to use 'primary' — it holds real appointments with real "
            "third-party attendees. Set CALENDAR_ID to the dedicated calendar."
        )
    cred = Credentials(
        None,
        refresh_token=ajustes.google_refresh_token,
        client_id=ajustes.google_client_id,
        client_secret=ajustes.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=cred, cache_discovery=False)


def leer_ocupados(desde: datetime, hasta: datetime) -> list[Ocupado]:
    """Devuelve los intervalos ocupados. Lista vacía significa agenda libre."""
    if desde >= hasta:
        raise ErrorDeCalendario(f"invalid window: {desde.isoformat()} >= {hasta.isoformat()}")

    try:
        respuesta = (
            _servicio()
            .events()
            .list(
                calendarId=ajustes.calendar_id,
                timeMin=desde.isoformat(),
                timeMax=hasta.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
            )
            .execute()
        )
    except HttpError as exc:
        raise ErrorDeCalendario(f"Calendar API returned {exc.status_code}: {exc.reason}") from exc
    except Exception as exc:
        raise ErrorDeCalendario(f"could not read the calendar: {type(exc).__name__}: {exc}") from exc

    ocupados = []
    for e in respuesta.get("items", []):
        ini, fin = e.get("start", {}), e.get("end", {})
        if "dateTime" not in ini or "dateTime" not in fin:
            continue  # evento de día completo; no acota una hora concreta
        try:
            ocupados.append(
                Ocupado(
                    inicio=datetime.fromisoformat(ini["dateTime"]),
                    fin=datetime.fromisoformat(fin["dateTime"]),
                )
            )
        except ValueError as exc:
            # No se confía en la salida de la herramienta: una fecha ilegible
            # se rechaza en vez de degradarse a algo plausible.
            raise ErrorDeCalendario(
                f"calendar returned an unparseable datetime: {ini.get('dateTime')!r} ({exc})"
            ) from exc
    return ocupados


def huecos_libres(
    desde: datetime, hasta: datetime, duracion_horas: float = 1.5
) -> list[datetime]:
    """Horas de inicio candidatas, dentro de la jornada y sin solaparse."""
    ocupados = leer_ocupados(desde, hasta)
    duracion = timedelta(hours=duracion_horas)
    candidatos: list[datetime] = []

    dia = desde.astimezone(TZ).replace(minute=0, second=0, microsecond=0)
    while dia < hasta.astimezone(TZ):
        if dia.weekday() < 5:  # lunes a viernes
            for hora in range(HORA_APERTURA, HORA_CIERRE):
                inicio = dia.replace(hour=hora)
                fin = inicio + duracion
                if inicio < desde.astimezone(TZ) or fin.hour > HORA_CIERRE:
                    continue
                if not any(o.inicio < fin and inicio < o.fin for o in ocupados):
                    candidatos.append(inicio)
        dia += timedelta(days=1)
    return candidatos


def crear_evento(
    inicio: datetime, fin: datetime, titulo: str, descripcion: str = ""
) -> str:
    """Crea el evento. Irreversible: solo desde el gate. Devuelve su id."""
    if inicio >= fin:
        raise ErrorDeCalendario("the event ends before it starts")
    if (fin - inicio) > timedelta(hours=8):
        raise ErrorDeCalendario("an assessment visit longer than 8 hours is not plausible")
    local = inicio.astimezone(TZ)
    if local.weekday() >= 5 or not (HORA_APERTURA <= local.hour < HORA_CIERRE):
        raise ErrorDeCalendario(
            f"{local:%a %H:%M} is outside working hours "
            f"({HORA_APERTURA}:00–{HORA_CIERRE}:00, Monday to Friday)"
        )

    try:
        evento = (
            _servicio()
            .events()
            .insert(
                calendarId=ajustes.calendar_id,
                body={
                    "summary": titulo,
                    "description": descripcion,
                    "start": {"dateTime": inicio.isoformat(), "timeZone": str(TZ)},
                    "end": {"dateTime": fin.isoformat(), "timeZone": str(TZ)},
                },
            )
            .execute()
        )
    except HttpError as exc:
        raise ErrorDeCalendario(f"Calendar API returned {exc.status_code}: {exc.reason}") from exc
    except Exception as exc:
        raise ErrorDeCalendario(f"could not create the event: {type(exc).__name__}: {exc}") from exc

    log.info("Evento creado %s", evento.get("id"))
    return evento["id"]
