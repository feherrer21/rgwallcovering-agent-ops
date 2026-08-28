"""Genera el refresh token de Google Calendar. Se ejecuta UNA vez.

Abre el navegador para que una persona autorice el acceso. Eso es
deliberadamente manual: la autorización la da Fabián sobre su propia cuenta de
prueba, no el agente y no un visitante.

    .venv/Scripts/python.exe -m scripts.autorizar_calendario

El token resultante se escribe directamente en `.env` y NO se imprime: un
secreto en el scrollback de la terminal acaba en una captura de pantalla.

Requiere GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET ya presentes en `.env`.
"""

import pathlib
import re
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from agente.config import ajustes

#: Mínimo que cubre las dos operaciones del agente: leer los huecos ocupados
#: (events.list) y crear la visita (events.insert). No pide `calendar`, que
#: además daría acceso a la configuración y a crear o borrar calendarios.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

RUTA_ENV = pathlib.Path(__file__).resolve().parent.parent / ".env"


def _guardar_en_env(token: str) -> None:
    """Escribe el refresh token en .env sin imprimirlo."""
    texto = RUTA_ENV.read_text(encoding="utf-8")
    if re.search(r"^GOOGLE_REFRESH_TOKEN=", texto, flags=re.M):
        texto = re.sub(
            r"^GOOGLE_REFRESH_TOKEN=.*$",
            f"GOOGLE_REFRESH_TOKEN={token}",
            texto,
            flags=re.M,
        )
    else:
        texto += f"\nGOOGLE_REFRESH_TOKEN={token}\n"
    RUTA_ENV.write_text(texto, encoding="utf-8")


def main() -> int:
    if not (ajustes.google_client_id and ajustes.google_client_secret):
        print("Faltan GOOGLE_CLIENT_ID y/o GOOGLE_CLIENT_SECRET en .env.")
        print("Se obtienen en console.cloud.google.com -> APIs y servicios ->")
        print("Credenciales -> ID de cliente de OAuth -> Aplicación de escritorio.")
        return 2

    config = {
        "installed": {
            "client_id": ajustes.google_client_id,
            "client_secret": ajustes.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("Se abrirá el navegador. Autoriza con la cuenta de PRUEBA, no con")
    print("una cuenta personal ni con la de Ronald.\n")

    flujo = InstalledAppFlow.from_client_config(config, SCOPES)
    # access_type=offline es lo que hace que Google emita un refresh token;
    # prompt=consent fuerza que lo reemita aunque ya hubiera una autorización
    # previa, que si no devuelve solo un access token y este script no sirve.
    credenciales = flujo.run_local_server(
        port=0, access_type="offline", prompt="consent"
    )

    if not credenciales.refresh_token:
        print("Google no devolvió refresh token. Revoca el acceso en")
        print("myaccount.google.com/permissions y vuelve a ejecutar esto.")
        return 1

    _guardar_en_env(credenciales.refresh_token)
    print(f"\nRefresh token guardado en .env ({len(credenciales.refresh_token)} car.)")

    servicio = build("calendar", "v3", credentials=credenciales)
    try:
        eventos = (
            servicio.events()
            .list(calendarId=ajustes.calendar_id, maxResults=10, singleEvents=True)
            .execute()
            .get("items", [])
        )
    except Exception as exc:
        print(f"El token se guardó pero la lectura del calendario falló: {exc}")
        return 1

    print(f"Calendario '{ajustes.calendar_id}' accesible: {len(eventos)} eventos.")
    if not eventos:
        print("\nEstá vacío. Hay que sembrar eventos sintéticos que representen")
        print("la agenda ocupada de Ronald: con un calendario vacío, la ruta de")
        print("agendamiento parece funcionar sin haberse ejercitado nunca.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
