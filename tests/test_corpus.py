"""Pruebas de la tool de corpus.

Ninguna llama al modelo: el índice y la recuperación se verifican solos, que es
la razón de que la fase 1 no dependa de la key del gateway.
"""

import json

import numpy as np
import pytest

from agente import corpus as c


# --- Fixtures de índice sintético -----------------------------------------


def _escribir_indice(directorio, registros, matriz=None):
    """Escribe un índice mínimo en disco y devuelve su ruta."""
    directorio.mkdir(parents=True, exist_ok=True)
    with (directorio / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if matriz is None:
        matriz = np.zeros((len(registros), 384), dtype=np.float32)
        matriz[:, 0] = 1.0
    np.save(directorio / "embeddings.npy", matriz)
    return directorio


def _registro(**kwargs):
    base = {
        "chunk_id": "x-001",
        "text": "TITULO — cuerpo del fragmento.",
        "title": "TITULO",
        "source_id": "S1",
        "tier": "A",
        "url": "https://ejemplo.invalid/a",
        "date": "2024-01-01",
    }
    base.update(kwargs)
    return base


# --- Validación al cargar (T1.2, T1.5) ------------------------------------


def test_falta_el_indice(tmp_path):
    with pytest.raises(c.ErrorDeCorpus, match="Falta"):
        c.cargar(tmp_path / "no_existe")


def test_tier_ausente_rechaza_el_indice(tmp_path):
    """Un fragmento sin tier no se degrada: invalida el índice.

    Sin tier no se sabe qué se puede afirmar sobre el negocio con ese pasaje,
    y el criterio S1 deja de ser exigible.
    """
    r = _registro()
    del r["tier"]
    _escribir_indice(tmp_path, [r])
    with pytest.raises(c.ErrorDeCorpus, match="sin campos"):
        c.cargar(tmp_path)


def test_tier_desconocido_rechaza_el_indice(tmp_path):
    _escribir_indice(tmp_path, [_registro(tier="D")])
    with pytest.raises(c.ErrorDeCorpus, match="tier"):
        c.cargar(tmp_path)


def test_indice_desalineado(tmp_path):
    """Dos fragmentos, tres vectores: el índice miente sobre sí mismo."""
    _escribir_indice(
        tmp_path,
        [_registro(chunk_id="a"), _registro(chunk_id="b")],
        matriz=np.zeros((3, 384), dtype=np.float32),
    )
    with pytest.raises(c.ErrorDeCorpus, match="desalineado"):
        c.cargar(tmp_path)


def test_dimension_incorrecta(tmp_path):
    _escribir_indice(
        tmp_path, [_registro()], matriz=np.zeros((1, 128), dtype=np.float32)
    )
    with pytest.raises(c.ErrorDeCorpus, match="matriz"):
        c.cargar(tmp_path)


def test_json_invalido(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "chunks.jsonl").write_text("{no es json\n", encoding="utf-8")
    np.save(tmp_path / "embeddings.npy", np.zeros((1, 384), dtype=np.float32))
    with pytest.raises(c.ErrorDeCorpus, match="JSON"):
        c.cargar(tmp_path)


# --- Recuperación sobre el corpus real (T1.3, T1.4) -----------------------


def test_el_indice_heredado_carga(corpus_real):
    """370 fragmentos, 384 dimensiones, alineados. Ver 02 §1.1."""
    assert len(corpus_real.fragmentos) == 370
    assert corpus_real.matriz.shape == (370, 384)
    assert {f.tier for f in corpus_real.fragmentos} <= c.TIERS_VALIDOS


def test_consulta_tematica_recupera_su_documento(corpus_real):
    """Comprobación del prefijo de consulta de BGE.

    Los pasajes se embebieron SIN prefijo y la consulta lo lleva. Si se cruzan
    las convenciones, las similitudes se degradan en silencio y una consulta
    que apunta directamente a un ensayo del corpus deja de recuperarlo.
    """
    resultados = corpus_real.buscar("block printing on walls")
    assert resultados, "una consulta cubierta por el corpus no recuperó nada"
    assert any(
        "block printing" in p.fragmento.titulo.lower()
        or "block printing" in p.fragmento.texto.lower()
        for p in resultados
    )
    assert all(p.score >= c.ajustes.piso_relevancia for p in resultados)


def test_consulta_fuera_del_corpus_devuelve_vacio(corpus_real):
    """La lista vacía es un resultado correcto, no un fallo.

    Nada del corpus habla de mecánica de motores, así que el piso debe cortar
    el mejor candidato en lugar de entregarlo.
    """
    assert corpus_real.buscar("how do I rebuild a diesel engine turbocharger") == []


def test_consulta_vacia(corpus_real):
    assert corpus_real.buscar("") == []
    assert corpus_real.buscar("   ") == []


def test_tope_por_documento(corpus_real):
    """Un documento largo no puede acaparar el contexto entero."""
    resultados = corpus_real.buscar("wallpaper", top_k=10, max_por_fuente=1)
    claves = [p.fragmento.url or p.fragmento.fuente_id for p in resultados]
    assert len(claves) == len(set(claves))


def test_el_tier_sobrevive_a_la_recuperacion(corpus_real):
    for p in corpus_real.buscar("wallpaper installation"):
        assert p.fragmento.tier in c.TIERS_VALIDOS


def test_top_k_invalido(corpus_real):
    with pytest.raises(ValueError):
        corpus_real.buscar("wallpaper", top_k=0)
