"""Fixtures compartidas."""

import pytest

from agente import corpus as c


@pytest.fixture(scope="session")
def corpus_real():
    """El indice heredado. Se salta si no esta copiado todavia."""
    try:
        return c.cargar()
    except c.ErrorDeCorpus as exc:
        pytest.skip(f"indice no disponible: {exc}")
