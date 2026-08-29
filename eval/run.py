"""Corre el agente sobre un set de leads y escribe los resultados.

    python -m eval.run --set diseno --repeticiones 2
    python -m eval.run --set diseno --modelo frontier
    python -m eval.run --set holdout --repeticiones 1     # UNA vez. Ver 04 fase 9.

Se detiene en el gate a propósito. Lo que se mide es la decisión, no el envío:
aprobar automáticamente para "completar" la corrida convertiría la evaluación
en el único sitio del sistema donde algo sale sin que una persona lo autorice.

Cada corrida se repite N veces con la misma configuración, y el desacuerdo
entre repeticiones se reporta como número. Una métrica que se mueve cuando
nada cambia no se puede mejorar, y saberlo antes vale más que un número limpio
después (docs/evidence/02).
"""

import argparse
import json
import statistics
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from agente import grafo, leads, modelo as modelo_mod
from agente.config import PROYECTO_DIR, ajustes
from agente.traza import Traza

from . import baseline, etiquetas

RESULTADOS = PROYECTO_DIR / "eval" / "results"


def una_corrida(registro: dict, llm=None) -> dict:
    """Un lead, una vez. Devuelve lo observable, no el estado entero."""
    tz = Traza(modelo=ajustes.modelo_frontier if llm else ajustes.modelo_barato)
    app = grafo.construir(llm=llm, traza=tz)
    cfg = {
        "configurable": {"thread_id": f"eval-{uuid.uuid4().hex[:10]}"},
        "recursion_limit": 60,
    }
    t0 = time.time()
    try:
        estado = app.invoke(leads.a_estado(registro), cfg)
        error = ""
    except Exception as exc:  # una corrida rota no puede tumbar el barrido
        return {
            "lead_id": registro["lead_id"],
            "accion": None,
            "error": f"{type(exc).__name__}: {exc}",
            "segundos": round(time.time() - t0, 1),
        }

    herramientas = [
        p["herramienta"] for p in tz.pasos if p["nodo"] == "tool"
    ]
    tokens = sum(
        (p.get("uso") or {}).get("total_tokens", 0)
        for p in tz.pasos
        if p["nodo"] == "decidir"
    )
    propuesta = estado.get("accion_propuesta")
    accion = estado.get("accion")

    tz.escribir()
    return {
        "lead_id": registro["lead_id"],
        "corrida_id": tz.corrida_id,
        "accion": accion.value if accion else None,
        "motivo": estado.get("motivo", ""),
        "herramientas": herramientas,
        "tiers": "".join(
            h.fragmento.tier for h in estado.get("hallazgos", [])
        ),
        "llego_al_gate": bool(estado.get("__interrupt__")),
        "cita_fuentes": bool(propuesta and propuesta.chunk_ids),
        # El cuerpo entero. La rubrica compromete una revision MANUAL de S1
        # -leer cada afirmacion contra los pasajes citados- y esa revision es
        # imposible sin el texto. La primera corrida no lo guardo, que es un
        # fallo de instrumentacion y no del agente.
        "borrador": {
            "destinatario": propuesta.destinatario,
            "asunto": propuesta.asunto or propuesta.titulo,
            "cuerpo": propuesta.cuerpo or propuesta.descripcion,
            "chunk_ids": list(propuesta.chunk_ids),
        } if propuesta else None,
        "fallos": [f.motivo for f in estado.get("fallos", [])],
        "llamadas": estado.get("llamadas", 0),
        "tokens": tokens,
        "segundos": round(time.time() - t0, 1),
        "error": error,
    }


def barrido(registros: list[dict], repeticiones: int, llm=None) -> list[dict]:
    filas = []
    for r in registros:
        for n in range(repeticiones):
            fila = una_corrida(r, llm=llm)
            fila["repeticion"] = n + 1
            filas.append(fila)
            print(
                f"  {fila['lead_id']:5} #{n+1}  {str(fila['accion']):24} "
                f"tools={','.join(fila.get('herramientas', [])) or '-':30} "
                f"{fila['segundos']}s"
            )
    return filas


def puntuar(registros: list[dict], filas: list[dict]) -> dict:
    """Compara contra las etiquetas y contra el baseline."""
    por_id = {r["lead_id"]: r for r in registros}
    agrupado = defaultdict(list)
    for f in filas:
        agrupado[f["lead_id"]].append(f)

    resumen = {
        "aciertos_estrictos": 0,
        "aciertos_con_alternativas": 0,
        "herramienta_requerida_ok": 0,
        "herramienta_requerida_total": 0,
        "inestables": [],
        "coincide_con_baseline": 0,
        "detalle": [],
    }

    for lead_id, corridas in agrupado.items():
        registro = por_id[lead_id]
        esp = etiquetas.esperado(registro)
        acciones = [c["accion"] for c in corridas]
        moda = Counter(acciones).most_common(1)[0][0]
        inestable = len(set(acciones)) > 1
        if inestable:
            resumen["inestables"].append((lead_id, sorted(set(a or "-" for a in acciones))))

        estricto = esp.acierta(moda or "", estricto=True)
        laxo = esp.acierta(moda or "", estricto=False)
        resumen["aciertos_estrictos"] += int(estricto)
        resumen["aciertos_con_alternativas"] += int(laxo)

        if esp.herramientas:
            resumen["herramienta_requerida_total"] += 1
            usadas = set(corridas[0].get("herramientas", []))
            if set(esp.herramientas) <= usadas:
                resumen["herramienta_requerida_ok"] += 1

        del_baseline = baseline.decidir(registro)
        if del_baseline == moda:
            resumen["coincide_con_baseline"] += 1

        resumen["detalle"].append({
            "lead_id": lead_id,
            "esperado": esp.accion,
            "agente": moda,
            "baseline": del_baseline,
            "estricto": estricto,
            "con_alternativas": laxo,
            "inestable": inestable,
            "acciones": acciones,
            "cita_fuentes": corridas[0].get("cita_fuentes"),
            "herramientas": corridas[0].get("herramientas", []),
        })

    n = len(agrupado)
    resumen["n"] = n
    resumen["acuerdo_con_baseline"] = round(resumen["coincide_con_baseline"] / n, 3)
    resumen["baseline_aciertos"] = sum(
        1 for d in resumen["detalle"]
        if etiquetas.esperado(por_id[d["lead_id"]]).acierta(d["baseline"], estricto=False)
    )
    return resumen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="conjunto", default="diseno",
                    choices=["diseno", "holdout"])
    ap.add_argument("--repeticiones", type=int, default=2)
    ap.add_argument("--modelo", default="barato", choices=["barato", "frontier"])
    ap.add_argument("--etiqueta", default="")
    args = ap.parse_args()

    ruta = leads.DISENO if args.conjunto == "diseno" else leads.HOLDOUT
    registros = leads.leer(ruta)
    llm = modelo_mod.frontier() if args.modelo == "frontier" else None

    marca = args.etiqueta or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    nombre = f"{args.conjunto}_{args.modelo}_{marca}"
    print(f"\n{len(registros)} leads x {args.repeticiones} repeticiones "
          f"| modelo {args.modelo}\n")

    filas = barrido(registros, args.repeticiones, llm=llm)
    resumen = puntuar(registros, filas)

    RESULTADOS.mkdir(parents=True, exist_ok=True)
    (RESULTADOS / f"{nombre}.jsonl").write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in filas) + "\n",
        encoding="utf-8")
    (RESULTADOS / f"{nombre}_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    n = resumen["n"]
    print(f"\n{'='*66}")
    print(f"acierto estricto        : {resumen['aciertos_estrictos']}/{n}")
    print(f"acierto con alternativas: {resumen['aciertos_con_alternativas']}/{n}")
    print(f"baseline (alternativas) : {resumen['baseline_aciertos']}/{n}")
    if resumen["herramienta_requerida_total"]:
        print(f"uso la herramienta que debia: "
              f"{resumen['herramienta_requerida_ok']}/{resumen['herramienta_requerida_total']}")
    print(f"tokens medios/lead      : "
          f"{round(statistics.mean([f.get('tokens',0) for f in filas]))}")
    print(f"segundos medios/lead    : "
          f"{round(statistics.mean([f['segundos'] for f in filas]), 1)}")
    print(f"\nleads inestables entre repeticiones: {len(resumen['inestables'])}")
    for lead_id, vistas in resumen["inestables"]:
        print(f"   {lead_id}: {vistas}")
    print(f"\nACUERDO CON EL BASELINE : {resumen['acuerdo_con_baseline']:.0%}"
          f"   (falsador de 01 §5.5: >= 90% => el agente no se gano su lugar)")
    print(f"\nresultados en eval/results/{nombre}*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
