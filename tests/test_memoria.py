"""Pruebas de las dos memorias.

La central es T4.3: una aprobacion que llega despues de que el proceso muera
tiene que completar la accion que se preparo antes. Esa prueba es la que gana
el argumento de 03_spec.md §7.1 — sin ella, la eleccion de checkpointer
duradero es una opinion.
"""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from agente import persistencia
from agente.config import PROYECTO_DIR, ajustes

PYTHON = str(PROYECTO_DIR / ".venv" / "Scripts" / "python.exe")


def _correr(fase: str, thread: str, entorno: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "-m", "scripts._proceso_gate", fase, thread],
        cwd=str(PROYECTO_DIR),
        capture_output=True,
        text=True,
        env=entorno,
        timeout=180,
    )


@pytest.mark.slow
def test_la_aprobacion_sobrevive_a_la_muerte_del_proceso(tmp_path, monkeypatch):
    """Preparar en un proceso, matarlo, aprobar en otro.

    Es el escenario real: el agente redacta, Ronald cierra el portatil, y
    aprueba media hora despues desde otro sitio. Con un checkpointer en
    memoria, lo que aprueba no existe.
    """
    import os

    entorno = dict(os.environ)
    entorno["CHECKPOINT_DB"] = str(tmp_path / "cp.sqlite")
    entorno["LEDGER_FILE"] = str(tmp_path / "ledger.jsonl")
    hilo = f"persist-{uuid.uuid4().hex[:8]}"

    primero = _correr("preparar", hilo, entorno)
    assert primero.returncode == 0, primero.stderr[-800:]
    assert "DETENIDO_EN_GATE:" in primero.stdout
    borrador = primero.stdout.split("DETENIDO_EN_GATE:")[1].splitlines()[0]

    # El primer proceso ya no existe. Nada en memoria sobrevive a esta linea.
    segundo = _correr("aprobar", hilo, entorno)
    assert segundo.returncode == 0, segundo.stderr[-800:]

    assert "RESULTADO:email sent to persistencia@example.com" in segundo.stdout
    assert "APROBO:ronald" in segundo.stdout
    # Y lo que se envio es EXACTAMENTE lo que se aprobo, no un borrador nuevo:
    # el proceso que reanuda tiene prohibido llamar al modelo.
    assert f"CUERPO_ENVIADO:{borrador}" in segundo.stdout


def test_un_hilo_desconocido_no_ejecuta_nada(tmp_path):
    """Reanudar un hilo que no existe no puede inventar una aprobacion."""
    import os

    entorno = dict(os.environ)
    entorno["CHECKPOINT_DB"] = str(tmp_path / "cp.sqlite")
    entorno["LEDGER_FILE"] = str(tmp_path / "ledger.jsonl")
    r = _correr("aprobar", "hilo-que-no-existe", entorno)
    assert "RESULTADO:email sent" not in r.stdout


# --- Ledger ---------------------------------------------------------------


def test_el_ledger_acumula_y_no_reescribe(tmp_path, monkeypatch):
    monkeypatch.setattr(ajustes, "ledger_file", tmp_path / "l.jsonl")
    persistencia.registrar("L01", "correo", "fallo", motivo="SMTP 550")
    persistencia.registrar("L01", "correo", "fallo", motivo="SMTP 550")
    persistencia.registrar("L01", "correo", "ok", detalle="enviado")
    persistencia.registrar("L02", "escalacion", "ok")

    h = persistencia.historial("L01")
    assert len(h) == 3
    assert [e["resultado"] for e in h] == ["fallo", "fallo", "ok"]
    assert persistencia.historial("L02") == h[:0] + persistencia.historial("L02")
    assert len(persistencia.historial("L02")) == 1


def test_los_intentos_fallidos_se_cuentan_entre_sesiones(tmp_path, monkeypatch):
    """Un presupuesto de reintentos que solo cuenta dentro de un proceso no es
    un presupuesto: el seguimiento es multi-sesion por naturaleza."""
    monkeypatch.setattr(ajustes, "ledger_file", tmp_path / "l.jsonl")
    persistencia.registrar("L20", "correo", "fallo", motivo="dominio inexistente")
    persistencia.registrar("L20", "correo", "fallo", motivo="dominio inexistente")
    assert persistencia.intentos_fallidos("L20", "correo") == 2
    assert persistencia.intentos_fallidos("L20", "evento") == 0


def test_una_linea_corrupta_no_impide_leer_las_demas(tmp_path, monkeypatch):
    ruta = tmp_path / "l.jsonl"
    monkeypatch.setattr(ajustes, "ledger_file", ruta)
    persistencia.registrar("L01", "correo", "ok")
    with ruta.open("a", encoding="utf-8") as f:
        f.write("{esto no es json\n")
    persistencia.registrar("L01", "correo", "ok")
    assert len(persistencia.historial("L01")) == 2


def test_el_ledger_no_guarda_el_cuerpo_del_correo(tmp_path, monkeypatch):
    """Lleva datos personales del lead y este fichero no es el sitio."""
    ruta = tmp_path / "l.jsonl"
    monkeypatch.setattr(ajustes, "ledger_file", ruta)
    persistencia.registrar("L01", "correo", "ok", detalle="email sent to a@example.com")
    contenido = ruta.read_text(encoding="utf-8")
    assert "Dear" not in contenido and "cuerpo" not in contenido


def test_los_tipos_del_estado_estan_declarados_para_serializar():
    """Un tipo del estado sin declarar se deserializa con aviso hoy y fallara
    manana. La lista tiene que cubrir lo que de verdad viaja en el estado."""
    from agente import estado as e

    declarados = {n for _, n in persistencia.TIPOS_PERMITIDOS}
    necesarios = {
        "RegistroLead", "Turno", "Accion", "AccionPropuesta",
        "Aprobacion", "EstadoAprobacion", "Fallo",
    }
    assert necesarios <= declarados
    for nombre in necesarios:
        assert hasattr(e, nombre), f"{nombre} ya no existe en agente.estado"
