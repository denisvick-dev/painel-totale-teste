"""Smoke test do shell multipágina do Streamlit."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]


def test_entrypoint_inicializa_sem_excecao() -> None:
    """O entrypoint deve montar navegação, tema e sidebar sem falhas."""
    app = AppTest.from_file(str(RAIZ / "streamlit_app.py"), default_timeout=60).run()
    assert not list(app.exception), f"Falha ao iniciar o portal: {list(app.exception)}"
