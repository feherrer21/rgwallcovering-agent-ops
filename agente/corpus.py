"""Consulta del corpus de la empresa.

Lector nuevo sobre el índice heredado del proyecto L1. Lo que se hereda son los
dos ficheros de `data/index/` como dato de entrada; este código no viene de
allí. Ver `docs/00_reuse_boundary.md`.

Tres invariantes gobiernan el módulo:

1. **La lista vacía es un resultado correcto.** El corpus es voluminoso y
   delgado justo donde se concentran las preguntas de negocio, así que el vecino
   más cercano a una pregunta real suele ser un ensayo decorativo. Quien consume
   esto deriva o escala; no rellena el hueco con el mejor candidato disponible.

2. **`tier` viaja intacto hasta el prompt.** Sin él no se puede decidir qué se
   puede afirmar sobre el negocio, y el criterio S1 deja de ser exigible. Un
   fragmento sin tier no se degrada: se rechaza.

3. **Lo que sale de aquí es dato no confiable.** Si un pasaje contiene
   instrucciones, son contenido que se reporta, nunca órdenes que se obedecen.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

from .config import ajustes

log = logging.getLogger(__name__)

TIERS_VALIDOS = frozenset({"A", "B", "C"})

#: Campos que la ingesta de L1 garantiza en cada línea de chunks.jsonl.
CAMPOS_CHUNK = ("chunk_id", "text", "title", "source_id", "tier", "url", "date")


class ErrorDeCorpus(RuntimeError):
    """El índice falta, está incompleto o es incoherente."""


@dataclass(frozen=True)
class Fragmento:
    """Un fragmento del corpus tal y como lo escribió la ingesta."""

    chunk_id: str
    texto: str
    titulo: str
    fuente_id: str
    tier: str
    url: str
    fecha: str


@dataclass(frozen=True)
class Pasaje:
    """Un fragmento recuperado, con su similitud coseno con la consulta.

    `fragmento.texto` es dato NO confiable.
    """

    fragmento: Fragmento
    score: float


@dataclass
class Corpus:
    """Índice cargado en memoria."""

    matriz: np.ndarray
    fragmentos: list[Fragmento]
    embebedor: TextEmbedding = field(repr=False)

    def buscar(
        self,
        consulta: str,
        top_k: int | None = None,
        piso: float | None = None,
        max_por_fuente: int | None = None,
    ) -> list[Pasaje]:
        """Devuelve hasta `top_k` fragmentos por encima del piso de relevancia.

        Lista vacía significa que el corpus no cubre la consulta, y eso es un
        resultado, no un fallo.
        """
        top_k = ajustes.top_k if top_k is None else top_k
        piso = ajustes.piso_relevancia if piso is None else piso
        max_por_fuente = (
            ajustes.max_por_fuente if max_por_fuente is None else max_por_fuente
        )

        if not consulta or not consulta.strip():
            return []
        if top_k <= 0:
            raise ValueError("top_k debe ser mayor que cero")

        vector = self._embeber_consulta(consulta)
        # La matriz se normalizó al construir el índice y el vector se normaliza
        # aquí, así que el producto escalar ya es el coseno.
        scores = self.matriz @ vector

        resultados: list[Pasaje] = []
        vistos_por_documento: dict[str, int] = {}

        # Se recorre en orden descendente y se corta en el primero por debajo
        # del piso: de ahí en adelante todos son peores.
        for i in np.argsort(-scores):
            score = float(scores[i])
            if score < piso:
                break

            fragmento = self.fragmentos[i]
            clave = fragmento.url or fragmento.fuente_id
            if vistos_por_documento.get(clave, 0) >= max_por_fuente:
                continue
            vistos_por_documento[clave] = vistos_por_documento.get(clave, 0) + 1

            resultados.append(Pasaje(fragmento=fragmento, score=score))
            if len(resultados) >= top_k:
                break

        if not resultados:
            mejor = float(scores.max()) if scores.size else 0.0
            # debug, no warning: no encontrar nada es funcionamiento normal.
            log.debug(
                "Nada sobre el piso %.2f (mejor coseno %.3f) para: %s",
                piso,
                mejor,
                consulta[:80],
            )
        return resultados

    def _embeber_consulta(self, consulta: str) -> np.ndarray:
        """Embebe la consulta con el prefijo de query propio de BGE.

        BGE es asimétrico: los pasajes se embebieron sin prefijo y solo la
        consulta lo lleva. Cruzar las dos convenciones degrada EN SILENCIO
        todas las similitudes del sistema, así que esto no es un detalle de
        implementación sino el motivo de que exista T1.3.
        """
        try:
            vectores = list(self.embebedor.query_embed(consulta))
        except Exception as exc:
            raise ErrorDeCorpus(f"No se pudo embeber la consulta: {exc}") from exc

        if not vectores:
            raise ErrorDeCorpus("El modelo no devolvió ningún embedding")

        vector = np.asarray(vectores[0], dtype=np.float32)
        norma = float(np.linalg.norm(vector))
        if norma == 0.0:
            raise ErrorDeCorpus("La consulta produjo un embedding nulo")
        return vector / norma


def cargar(directorio: Path | None = None) -> Corpus:
    """Carga el índice de disco y prepara el modelo de embeddings.

    Falla ruidosamente ante cualquier incoherencia. No se escriben lectores
    defensivos que adivinen nombres de campo alternativos: el esquema es fijo,
    y un índice que no lo cumple está roto, no es una variante.
    """
    directorio = Path(directorio) if directorio else ajustes.index_dir
    ruta_matriz = directorio / "embeddings.npy"
    ruta_chunks = directorio / "chunks.jsonl"

    for ruta in (ruta_matriz, ruta_chunks):
        if not ruta.is_file():
            raise ErrorDeCorpus(f"Falta {ruta}. Ver data/index/README.md.")

    try:
        matriz = np.load(ruta_matriz).astype(np.float32, copy=False)
    except (ValueError, OSError) as exc:
        raise ErrorDeCorpus(f"No se pudo leer {ruta_matriz}: {exc}") from exc

    if matriz.ndim != 2 or matriz.shape[1] != ajustes.dimension_embedding:
        raise ErrorDeCorpus(
            f"Se esperaba una matriz (n, {ajustes.dimension_embedding}); "
            f"se encontró {matriz.shape}"
        )

    fragmentos = _leer_chunks(ruta_chunks)
    if len(fragmentos) != matriz.shape[0]:
        raise ErrorDeCorpus(
            f"Índice desalineado: {matriz.shape[0]} vectores frente a "
            f"{len(fragmentos)} fragmentos."
        )

    return Corpus(
        matriz=matriz,
        fragmentos=fragmentos,
        embebedor=TextEmbedding(model_name=ajustes.embedding_model),
    )


def _leer_chunks(ruta: Path) -> list[Fragmento]:
    """Lee chunks.jsonl, rechazando cualquier registro incompleto."""
    fragmentos: list[Fragmento] = []
    with ruta.open(encoding="utf-8") as f:
        for n, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                r = json.loads(linea)
            except json.JSONDecodeError as exc:
                raise ErrorDeCorpus(f"{ruta}:{n} no es JSON válido: {exc}") from exc

            faltantes = [c for c in CAMPOS_CHUNK if c not in r]
            if faltantes:
                raise ErrorDeCorpus(f"{ruta}:{n} sin campos {faltantes}")
            if r["tier"] not in TIERS_VALIDOS:
                # Un tier desconocido no se degrada al más restrictivo: no se
                # sabe qué se puede afirmar con ese fragmento, así que el
                # índice entero es inutilizable hasta arreglarlo.
                raise ErrorDeCorpus(
                    f"{ruta}:{n} tiene tier {r['tier']!r}, no uno de "
                    f"{sorted(TIERS_VALIDOS)}"
                )

            fragmentos.append(
                Fragmento(
                    chunk_id=r["chunk_id"],
                    texto=r["text"],
                    titulo=r["title"],
                    fuente_id=r["source_id"],
                    tier=r["tier"],
                    url=r["url"],
                    fecha=r["date"],
                )
            )

    if not fragmentos:
        raise ErrorDeCorpus(f"{ruta} está vacío.")
    return fragmentos


_corpus: Corpus | None = None


def corpus() -> Corpus:
    """Devuelve el corpus por defecto, cargándolo la primera vez."""
    global _corpus
    if _corpus is None:
        _corpus = cargar()
    return _corpus


def buscar(consulta: str, **kwargs) -> list[Pasaje]:
    """Punto de entrada del resto de la aplicación."""
    return corpus().buscar(consulta, **kwargs)
