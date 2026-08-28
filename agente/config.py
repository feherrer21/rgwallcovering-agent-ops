"""Configuración del proyecto, resuelta desde el entorno.

Ningún secreto vive en el código ni se escribe en los logs. En local se leen
de `.env` (gitignoreado desde el primer commit); en despliegue, del almacén de
secretos de la plataforma.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROYECTO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROYECTO_DIR / "data"


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROYECTO_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Pasarela de modelos ---------------------------------------------
    # Política de Perficient: las llamadas de coursework van por el gateway de
    # la empresa, nunca por una key personal de proveedor. Ver 03_spec.md §8.
    portkey_api_key: str = ""
    portkey_base_url: str = "https://portkeygateway.perficient.com/v1"

    # PROVISIONAL: los identificadores son del catálogo del workspace y la guía
    # de entorno se contradice a sí misma en la fila de Gemini. Se resuelven
    # contra el catálogo vivo (T0.5) antes de fijarlos aquí.
    modelo_barato: str = ""
    modelo_frontier: str = ""

    max_tokens: int = 4000

    # --- Índice del corpus -----------------------------------------------
    # Heredado del proyecto L1 como dato de entrada. El lector es nuevo:
    # ver docs/00_reuse_boundary.md.
    index_dir: Path = DATA_DIR / "index"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    dimension_embedding: int = 384

    # Piso de recuperación. 0.62 es el valor que L1 calibró contra su set de
    # evaluación; aquí es un punto de partida heredado, no un resultado propio.
    piso_relevancia: float = 0.62
    top_k: int = 5
    max_por_fuente: int = 2

    # --- Presupuestos del bucle -------------------------------------------
    # Un fallo repetido escala; no reintenta indefinidamente (03_spec.md §10).
    reintentos_por_tool: int = 2
    # Tope duro de llamadas al modelo por lead. El gateway mide un presupuesto
    # de $50 de la empresa: un bucle patológico no puede vaciarlo antes de que
    # alguien lo note (03_spec.md §12.2).
    max_llamadas_por_lead: int = 12

    # --- Persistencia ------------------------------------------------------
    # Checkpointer durable, no en memoria: la aprobación del gate llega en
    # tiempo humano y debe sobrevivir a un reinicio (03_spec.md §7.1).
    checkpoint_db: Path = DATA_DIR / "runtime" / "checkpoints.sqlite"
    # Ledger append-only por lead: qué se intentó, cuándo, con qué resultado.
    ledger_file: Path = DATA_DIR / "runtime" / "acciones.jsonl"
    trazas_dir: Path = PROYECTO_DIR / "traces"

    # --- Correo ------------------------------------------------------------
    # OJO: en desarrollo esto apunta a la cuenta de prueba, NUNCA a la de
    # Ronald. Un lead de prueba en su bandeja es una llamada perdida a una
    # persona que no existe.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    correo_remitente: str = ""
    correo_escalacion: str = ""

    # --- Calendario --------------------------------------------------------
    # OAuth con refresh token generado una sola vez por autorización manual.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    calendar_id: str = "primary"

    # --- Inyección deliberada de fallos -----------------------------------
    # Formato "herramienta:n" — falla las n primeras llamadas a esa acción.
    # Ej. INYECTAR_FALLO=correo:2
    #
    # Existe porque el fallo planificado NO se disparó: el agente reconoció el
    # dominio irresoluble de L20 por inspección y escaló sin intentar enviar.
    # Un fallo que el modelo puede esquivar mirando no ejercita la ruta de
    # recuperación, y esa ruta es la que hay que demostrar rota a propósito.
    # Vacío en producción; se comprueba al arrancar.
    inyectar_fallo: str = ""

    @property
    def inyeccion(self) -> tuple[str, int]:
        """(herramienta, veces). ("", 0) si no hay inyección activa."""
        if not self.inyectar_fallo or ":" not in self.inyectar_fallo:
            return "", 0
        herramienta, _, veces = self.inyectar_fallo.partition(":")
        try:
            return herramienta.strip(), int(veces)
        except ValueError:
            return "", 0

    # --- Acceso a la aplicación -------------------------------------------
    # Puerta, no autorización. El registro que evidencia S2 es la aprobación
    # del gate, no el hecho de haber entrado (03_spec.md §12.1).
    app_password: str = ""

    @property
    def gateway_configurado(self) -> bool:
        return bool(self.portkey_api_key and self.modelo_barato)

    @property
    def envio_configurado(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def calendario_configurado(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_refresh_token
        )

    @property
    def remitente(self) -> str:
        return self.correo_remitente or self.smtp_user

    @property
    def embeddings_path(self) -> Path:
        return self.index_dir / "embeddings.npy"

    @property
    def chunks_path(self) -> Path:
        return self.index_dir / "chunks.jsonl"


ajustes = Ajustes()
