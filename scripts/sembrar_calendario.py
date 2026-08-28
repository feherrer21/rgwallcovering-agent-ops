"""Siembra una agenda sintética que representa la semana de Ronald.

Un calendario vacío hace que la ruta de agendamiento *parezca* funcionar sin
haberse ejercitado nunca: cualquier hueco está libre, así que el agente nunca
tiene que leer nada para proponer uno. La agenda de abajo existe para que
proponer una hora sea una decisión con restricciones reales.

    .venv/Scripts/python.exe -m scripts.sembrar_calendario [--limpiar]

Todo es inventado. Los nombres no corresponden a ninguna persona real, y el
calendario es uno dedicado: el agente NUNCA apunta a `primary`, que contiene
citas reales con invitados reales (docs/03_spec.md §12.3).
"""

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from agente.config import ajustes

TZ = ZoneInfo("America/New_York")  # el negocio está en Providence, RI

#: Marca en la descripción para poder borrar solo lo que sembró este script.
MARCA = "[sintetico:agent-ops]"

#: (offset en días laborables desde el lunes base, hora inicio, duración h, título)
#:
#: Diseñada con dos intenciones. Primera: que haya semanas con instalaciones de
#: varios días, porque una instalación típica ocupa jornadas completas y es lo
#: que de verdad bloquea la agenda. Segunda, y es el punto: el MARTES de la
#: semana 1 está ocupado por la mañana y el de la semana 2 está libre. El lead
#: L19 pide expresamente "un martes por la mañana", así que el agente tiene que
#: leer el calendario para responderle — no puede acertar por defecto.
AGENDA = [
    # --- Semana 1 ---
    (0, 8, 2.0, "Site visit — Whitmore residence, Cranston"),
    (0, 13, 1.5, "Assessment visit — Halloran offices, Providence"),
    (1, 7, 9.0, "Install day 1/3 — Bexley Hotel corridor, Newport"),
    (2, 7, 9.0, "Install day 2/3 — Bexley Hotel corridor, Newport"),
    (3, 7, 9.0, "Install day 3/3 — Bexley Hotel corridor, Newport"),
    (4, 9, 1.0, "Assessment visit — Okonkwo residence, Warwick"),
    (4, 14, 2.0, "Materials pickup and supplier meeting"),
    # --- Semana 2 --- (martes libre por la mañana: es el hueco de L19)
    (5, 8, 1.5, "Assessment visit — Larkin dental practice, Providence"),
    (6, 13, 3.0, "Install — Fennimore accent wall, Barrington"),
    (7, 7, 8.0, "Install day 1/2 — Castellano restaurant, Providence"),
    (8, 7, 8.0, "Install day 2/2 — Castellano restaurant, Providence"),
    (9, 10, 1.0, "Assessment visit — Underhill townhouse, East Providence"),
    # --- Semana 3 ---
    (10, 9, 1.5, "Assessment visit — Praeger loft, Pawtucket"),
    (11, 7, 9.0, "Install day 1/3 — Sable & Finch retail, Providence"),
    (12, 7, 9.0, "Install day 2/3 — Sable & Finch retail, Providence"),
    (13, 7, 9.0, "Install day 3/3 — Sable & Finch retail, Providence"),
    (14, 12, 4.0, "Design consultation — Marchetti residence, Cranston"),
    # --- Semana 4 --- (más despejada: el agente debe poder encontrar hueco)
    (15, 8, 1.0, "Assessment visit — Nakamura condo, Providence"),
    (17, 13, 2.0, "Supplier showroom — sample selection"),
    (19, 9, 1.5, "Assessment visit — Ferraro duplex, Johnston"),
]


def _servicio():
    cred = Credentials(
        None,
        refresh_token=ajustes.google_refresh_token,
        client_id=ajustes.google_client_id,
        client_secret=ajustes.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=cred)


def _lunes_base() -> datetime:
    """El próximo lunes a medianoche, hora de Providence."""
    hoy = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)


def _fecha(base: datetime, indice_laborable: int, hora: int) -> datetime:
    """Convierte un índice de día laborable en una fecha real, saltando fines de semana."""
    semana, dia = divmod(indice_laborable, 5)
    return base + timedelta(weeks=semana, days=dia, hours=hora)


def limpiar(svc, cal: str) -> int:
    """Borra solo los eventos que sembró este script."""
    borrados = 0
    pagina = None
    while True:
        r = svc.events().list(
            calendarId=cal, q=MARCA, maxResults=250, pageToken=pagina
        ).execute()
        for e in r.get("items", []):
            if MARCA in (e.get("description") or ""):
                svc.events().delete(calendarId=cal, eventId=e["id"]).execute()
                borrados += 1
        pagina = r.get("nextPageToken")
        if not pagina:
            break
    return borrados


def main() -> int:
    if ajustes.calendar_id == "primary":
        print("CALENDAR_ID apunta a 'primary'. Este script no escribe ahí:")
        print("contiene citas reales con invitados reales. Ver 03_spec.md §12.3.")
        return 2
    if not ajustes.calendario_configurado:
        print("Faltan credenciales de Google. Ver scripts/autorizar_calendario.py.")
        return 2

    svc = _servicio()
    cal = ajustes.calendar_id

    borrados = limpiar(svc, cal)
    if borrados:
        print(f"Limpiados {borrados} eventos sintéticos previos.")
    if "--limpiar" in sys.argv:
        return 0

    base = _lunes_base()
    print(f"Sembrando desde el lunes {base:%Y-%m-%d} (hora de Providence)\n")

    for indice, hora, duracion, titulo in AGENDA:
        inicio = _fecha(base, indice, hora)
        fin = inicio + timedelta(hours=duracion)
        svc.events().insert(
            calendarId=cal,
            body={
                "summary": titulo,
                "description": (
                    f"{MARCA} Persona y proyecto inventados. Agenda sintética "
                    "para probar la ruta de agendamiento del agente."
                ),
                "start": {"dateTime": inicio.isoformat(), "timeZone": str(TZ)},
                "end": {"dateTime": fin.isoformat(), "timeZone": str(TZ)},
            },
        ).execute()
        print(f"  {inicio:%a %d %b %H:%M}–{fin:%H:%M}  {titulo}")

    print(f"\n{len(AGENDA)} eventos sembrados.")
    print("Martes semana 1: ocupado por la mañana. Martes semana 2: libre.")
    print("El lead L19 pide 'un martes por la mañana', así que el agente tiene")
    print("que leer el calendario para contestarle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
