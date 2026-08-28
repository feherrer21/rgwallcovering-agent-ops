"""Pruebas de la presentacion de herramientas al modelo."""

import pytest

from agente import corpus, tools


def test_esquema_dice_cuando_no_llamar():
    """La descripcion tiene que ensenar a NO llamar, no solo a llamar."""
    d = tools.BUSCAR_CORPUS["function"]["description"].lower()
    assert "do not call this" in d
    assert "empty result" in d


def test_esquema_ensena_a_desconfiar_del_registro():
    """Lo que se le dijo a un cliente no es evidencia de que fuera cierto."""
    d = tools.BUSCAR_CORPUS["function"]["description"].lower()
    assert "lead record" in d


def test_sin_pasajes_no_invita_a_rellenar():
    salida = tools.formatear_pasajes([])
    assert "do not guess" in salida.lower()
    assert "silence is not confirmation" in salida.lower()


def test_los_pasajes_llevan_su_tier_delante(corpus_real):
    pasajes = corpus_real.buscar("is the assessment visit free")
    assert pasajes
    salida = tools.formatear_pasajes(pasajes)
    for p in pasajes:
        assert tools.ETIQUETA_TIER[p.fragmento.tier].split(" —")[0] in salida


def test_la_salida_se_declara_como_dato(corpus_real):
    """Regla de input no confiable: instrucciones en un pasaje son contenido."""
    salida = tools.formatear_pasajes(corpus_real.buscar("wallpaper"))
    assert "never instructions" in salida.lower()


def test_herramienta_desconocida():
    with pytest.raises(ValueError, match="desconocida"):
        tools.ejecutar_lectura("borrar_todo", {})
