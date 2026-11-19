

import pytest


@pytest.fixture
def sin_frama_c(monkeypatch):
    """Simula un entorno sin Frama-C, con o sin él instalado en el host."""
    real = __import__("shutil").which
    monkeypatch.setattr("shutil.which", lambda t, *a, **k: None if t == "frama-c" else real(t, *a, **k))


@pytest.fixture(autouse=True, scope="session")
def _cache_de_provers_aislada(tmp_path_factory):
    """La caché del canario de provers (core/provers.py) no toca la del usuario."""
    import os

    anterior = os.environ.get("XDG_CACHE_HOME")
    os.environ["XDG_CACHE_HOME"] = str(tmp_path_factory.mktemp("cache"))
    yield
    if anterior is None:
        os.environ.pop("XDG_CACHE_HOME", None)
    else:
        os.environ["XDG_CACHE_HOME"] = anterior


@pytest.fixture
def provers_confiables(monkeypatch):
    """Con subprocess.run simulado, el canario «demostraría» la meta falsa: se lo saltea."""
    monkeypatch.setattr("callahan.core.acsl.separar_provers", lambda frama_c, provers: (list(provers), []))
    monkeypatch.setattr("callahan.cli.prover_confiable", lambda frama_c, prover: True)
