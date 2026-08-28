"""Comprueba el acceso al gateway y lista el catálogo de modelos (T0.5).

Se ejecuta antes de escribir cualquier identificador de modelo en el spec: los
slugs son del catálogo del workspace, y la guía de entorno se contradice a sí
misma en la fila de Gemini. La fuente de verdad es esto, no el documento.

    .venv/Scripts/python.exe -m scripts.verificar_gateway

No imprime la key, ni entera ni parcialmente reconstruible.
"""

import json
import sys
import urllib.error
import urllib.request

from agente.config import ajustes


def listar_modelos() -> list[dict]:
    """Pide el catálogo al gateway. Devuelve la lista cruda."""
    peticion = urllib.request.Request(
        f"{ajustes.portkey_base_url.rstrip('/')}/models",
        headers={"x-portkey-api-key": ajustes.portkey_api_key},
    )
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        cuerpo = json.loads(respuesta.read().decode("utf-8"))
    return cuerpo.get("data", cuerpo if isinstance(cuerpo, list) else [])


def main() -> int:
    if not ajustes.portkey_api_key:
        print("FALTA PORTKEY_API_KEY en .env.")
        print("  myapplications.microsoft.com -> Portkey -> Getting Started")
        return 2

    print(f"Gateway: {ajustes.portkey_base_url}")
    print(f"Key: presente ({len(ajustes.portkey_api_key)} caracteres)\n")

    try:
        modelos = listar_modelos()
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code} — {exc.reason}")
        if exc.code == 401:
            print("\nLa key no es válida o todavía no está provisionada.")
            print("El acceso se procesa semanalmente tras la inscripción a la")
            print("ruta de aprendizaje: si te inscribiste esta semana, llega")
            print("el lunes siguiente.")
        return 1
    except urllib.error.URLError as exc:
        print(f"No se pudo alcanzar el gateway: {exc.reason}")
        return 1

    if not modelos:
        print("El catálogo respondió vacío.")
        return 1

    print(f"{len(modelos)} modelos en el catálogo:\n")
    for m in modelos:
        ident = m.get("id", m) if isinstance(m, dict) else m
        propietario = m.get("owned_by", "") if isinstance(m, dict) else ""
        print(f"  {ident}" + (f"   [{propietario}]" if propietario else ""))

    print("\nSiguiente: elegir MODELO_BARATO y MODELO_FRONTIER de esta lista")
    print("y escribirlos en .env y en docs/03_spec.md §8.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
