"""Envío de correo. Es una de las dos acciones irreversibles del sistema.

Este módulo NO decide nada y no se invoca desde el modelo: lo llama
`ejecutar_irreversible`, que solo es alcanzable desde el gate humano
(03_spec.md §4.2).

**El fallo se propaga.** El proyecto certificado hacía deliberadamente lo
contrario — registraba el fallo y le confirmaba al visitante que todo había
ido bien — porque allí el usuario era el visitante, que no podía hacer nada
con la verdad. Aquí el usuario es Ronald, que sí puede: un seguimiento que él
cree enviado y no salió es peor que no tener agente (CLAUDE.md).
"""

import logging
import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from .config import ajustes

log = logging.getLogger(__name__)

#: Suficiente para rechazar lo que SMTP rechazaría de todas formas, y para
#: atrapar el fallo de L12 -una direccion invalida por un caracter- antes de
#: gastar una conexion. No pretende validar RFC 5322.
_DIRECCION = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")


class ErrorDeEnvio(RuntimeError):
    """El correo no salió. Lleva el motivo específico, no 'falló'."""


@dataclass(frozen=True)
class ResultadoEnvio:
    destinatario: str
    asunto: str
    mensaje_id: str


def validar_destinatario(direccion: str) -> None:
    """Rechaza una dirección malformada antes de intentar enviarla.

    Detectarlo después del rebote es tarde, y "corregirla" por nuestra cuenta
    sería inventar un dato de contacto. Se rechaza y se explica.
    """
    if not direccion or not direccion.strip():
        raise ErrorDeEnvio("recipient is empty")
    if not _DIRECCION.match(direccion.strip()):
        raise ErrorDeEnvio(
            f"recipient {direccion!r} is not a valid address — it will not be "
            "corrected automatically, because guessing a contact detail is "
            "fabricating one"
        )


#: Cuántas veces ya se inyectó un fallo en esta sesión.
_inyectados = 0


def _quizas_inyectar() -> None:
    """Rompe el envío a propósito, si la configuración lo pide.

    El mensaje imita un rechazo real de servidor porque el objetivo es
    ejercitar la ruta de recuperación con un motivo del que se pueda aprender,
    no con un texto que delate que es de mentira.
    """
    global _inyectados
    herramienta, veces = ajustes.inyeccion
    if herramienta == "correo" and _inyectados < veces:
        _inyectados += 1
        raise ErrorDeEnvio(
            "SMTP error: SMTPSenderRefused: 421 4.7.0 Temporary System Problem. "
            f"Try again later. (injected failure {_inyectados}/{veces})"
        )


def enviar(destinatario: str, asunto: str, cuerpo: str) -> ResultadoEnvio:
    """Envía. Levanta ErrorDeEnvio con el motivo exacto si no sale."""
    validar_destinatario(destinatario)
    _quizas_inyectar()
    if not cuerpo or not cuerpo.strip():
        raise ErrorDeEnvio("body is empty")
    if not ajustes.envio_configurado:
        raise ErrorDeEnvio("SMTP credentials are not configured")

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = ajustes.remitente
    mensaje["To"] = destinatario
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP(ajustes.smtp_host, ajustes.smtp_port, timeout=25) as s:
            s.starttls()
            s.login(ajustes.smtp_user, ajustes.smtp_password)
            rechazos = s.send_message(mensaje)
    except smtplib.SMTPRecipientsRefused as exc:
        detalle = "; ".join(
            f"{d.decode() if isinstance(d, bytes) else d}"
            for _, (c, d) in exc.recipients.items()
        )
        raise ErrorDeEnvio(f"SMTP refused the recipient: {detalle}") from exc
    except smtplib.SMTPAuthenticationError as exc:
        raise ErrorDeEnvio(
            f"SMTP authentication failed: {exc.smtp_code} "
            f"{exc.smtp_error.decode(errors='replace') if isinstance(exc.smtp_error, bytes) else exc.smtp_error}"
        ) from exc
    except smtplib.SMTPException as exc:
        raise ErrorDeEnvio(f"SMTP error: {type(exc).__name__}: {exc}") from exc
    except OSError as exc:
        raise ErrorDeEnvio(f"could not reach the mail server: {exc}") from exc

    if rechazos:
        raise ErrorDeEnvio(f"the server accepted the message but refused: {rechazos}")

    # Nunca se registra el cuerpo: lleva datos personales del lead.
    log.info("Correo enviado a %s", destinatario)
    return ResultadoEnvio(
        destinatario=destinatario,
        asunto=asunto,
        mensaje_id=mensaje.get("Message-ID", ""),
    )
