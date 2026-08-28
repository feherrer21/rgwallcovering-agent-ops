"""Acceso al modelo, siempre a través del gateway de la empresa.

Un solo cliente. El proveedor no es una rama de código: viaja dentro del
identificador del modelo (`@dsvertex/...`, `@aws-bedrock-use2/...`) y se
resuelve en el gateway. Cambiar de proveedor es cambiar una cadena en `.env`,
no tocar Python — que es la razón por la que este proyecto no escribe su propia
capa de abstracción sobre proveedores (CLAUDE.md, "Scale").

Política de Perficient: el coursework se rutea por Portkey, nunca por una key
personal de proveedor. Ver docs/03_spec.md §8.
"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI

from .config import ajustes

log = logging.getLogger(__name__)


class ErrorDeConfiguracion(RuntimeError):
    """Falta la key del gateway o el identificador del modelo."""


def cliente(modelo: str | None = None, **kwargs: Any) -> ChatOpenAI:
    """Devuelve un cliente apuntado al gateway.

    `modelo` por defecto es el barato: la iteración es donde se acumula el
    gasto y es la que menos evidencia compra. El frontier se reserva para la
    corrida de comparación.
    """
    if not ajustes.portkey_api_key:
        raise ErrorDeConfiguracion(
            "Falta PORTKEY_API_KEY. Ver .env.example y "
            "scripts/verificar_gateway.py."
        )

    modelo = modelo or ajustes.modelo_barato
    if not modelo:
        raise ErrorDeConfiguracion(
            "Falta el identificador del modelo. Los slugs son del catálogo del "
            "workspace: resolverlos con scripts/verificar_gateway.py, no con la "
            "guía de entorno, cuya tabla etiqueta mal la fila de Gemini."
        )

    return ChatOpenAI(
        model=modelo,
        base_url=ajustes.portkey_base_url,
        api_key=ajustes.portkey_api_key,
        # El gateway acepta la key por Authorization y por su cabecera propia.
        # Se mandan las dos: la segunda es la que Portkey usa para atribuir la
        # llamada al workspace, y sin atribución no hay traza de coste, que es
        # justo la evidencia de observabilidad que pide el checklist.
        default_headers={"x-portkey-api-key": ajustes.portkey_api_key},
        # Gemini 2.5 gasta tokens en razonar ANTES de emitir contenido: medido,
        # ~110 de razonamiento en una llamada trivial. Un presupuesto ajustado
        # devuelve finish_reason=length y un mensaje vacío, que no parece un
        # error y lo es.
        max_tokens=kwargs.pop("max_tokens", ajustes.max_tokens),
        timeout=kwargs.pop("timeout", 120),
        # Sin reintentos del SDK: los reintentos de este sistema los decide el
        # grafo, con el motivo del fallo dentro del prompt (03_spec.md §10). Un
        # reintento silencioso aquí destruiría esa evidencia.
        max_retries=kwargs.pop("max_retries", 0),
        **kwargs,
    )


def frontier(**kwargs: Any) -> ChatOpenAI:
    """Cliente sobre el modelo caro, para la corrida de comparación."""
    return cliente(ajustes.modelo_frontier, **kwargs)
