

import pytest


@pytest.fixture
def sin_frama_c(monkeypatch):
    """Simula un entorno sin Frama-C, con o sin él instalado en el host."""
    real = __import__("shutil").which
    monkeypatch.setattr("shutil.which", lambda t, *a, **k: None if t == "frama-c" else real(t, *a, **k))
