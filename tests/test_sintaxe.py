"""Guarda de sintaxe — todo script do app precisa compilar no Python do projeto.

Contexto (corrigido em 2026-10-05): `pages/quebra_geral.py` usava aspas duplas
aninhadas dentro de f-string, sintaxe válida apenas a partir do **Python 3.12**
(PEP 701) e inválida no 3.11 — a versão fixada pelo projeto no
`.devcontainer/devcontainer.json` (`python:1-3.11-bullseye`). Resultado: a página
(o entrypoint e o `pages/quebra_unificada.py`, que a importam) não abria.

Este teste compila todos os módulos com o interpretador atual e falha apontando
arquivo + linha de qualquer `SyntaxError`, evitando que uma sintaxe nova demais
volte a entrar sem ser percebida.

Execução:

    python tests/test_sintaxe.py        # execução direta (stdlib)
    pytest tests/test_sintaxe.py        # via pytest
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Diretórios ignorados: `old/` guarda scripts legados que não fazem parte do app.
IGNORADOS = {"old", "__pycache__", ".venv", ".git", "build", "dist"}


def _arquivos_python() -> list[Path]:
    return sorted(
        caminho
        for caminho in RAIZ.rglob("*.py")
        if not any(parte in IGNORADOS for parte in caminho.relative_to(RAIZ).parts)
    )


def _erro_de_sintaxe(caminho: Path) -> str | None:
    """Compila o arquivo e devolve a descrição do erro, se houver."""
    try:
        compile(caminho.read_text(encoding="utf-8"), str(caminho), "exec")
    except SyntaxError as exc:
        return f"{caminho.relative_to(RAIZ)}:{exc.lineno} -> {exc.msg}"
    return None


def test_todos_modulos_compilam() -> None:
    """Nenhum módulo do app pode ter erro de sintaxe no interpretador atual."""
    arquivos = _arquivos_python()
    assert arquivos, "Nenhum arquivo .py encontrado — verifique o caminho da raiz."

    problemas = [erro for caminho in arquivos if (erro := _erro_de_sintaxe(caminho))]

    detalhe = (
        "\nSintaxe incompatível com o Python do projeto "
        f"({sys.version.split()[0]}) — ex.: PEP 701 (f-strings) exige 3.12+:\n  "
    )
    assert not problemas, detalhe + "\n  ".join(problemas)


def test_quebra_geral_compila() -> None:
    """Regressão específica do bug de f-string com aspas aninhadas."""
    erro = _erro_de_sintaxe(RAIZ / "pages" / "quebra_geral.py")
    assert erro is None, f"pages/quebra_geral.py não compila: {erro}"


def _main() -> int:
    testes = [
        valor
        for nome, valor in sorted(globals().items())
        if nome.startswith("test_") and callable(valor)
    ]
    falhas = 0
    for teste in testes:
        try:
            teste()
        except Exception as exc:  # noqa: BLE001 — runner de testes
            falhas += 1
            print(f"FALHOU  {teste.__name__}: {exc}")
        else:
            print(f"OK      {teste.__name__}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_main())
