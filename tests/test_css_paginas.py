"""Guardas do CSS compartilhado de páginas (`components/css_paginas.py`).

A família `.corp-table` era copiada em `consultivo.py`, `pontos.py` e
`qtde_os.py` (8 regras por página, com pequenas variações de densidade). Em
2026-10-05 essas regras foram centralizadas em `css_tabela_corporativa()`, com os
parâmetros que cada página já usava — o CSS gerado é equivalente ao anterior.

Estes testes evitam que a duplicação volte:

1. o helper gera as regras essenciais e respeita os parâmetros;
2. nenhuma página volta a declarar localmente os seletores centralizados;
3. páginas que usam `.corp-table` chamam o helper do Design System.

Execução:

    python tests/test_css_paginas.py        # execução direta (stdlib)
    pytest tests/test_css_paginas.py        # via pytest
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from components.css_paginas import css_tabela_corporativa  # noqa: E402

# seletores que passaram a ser responsabilidade do Design System
SELETORES_CENTRALIZADOS = (
    ".corp-table",
    ".corp-table th",
    ".corp-table td.num",
    ".corp-table thead th",
    ".corp-table-wrap::-webkit-scrollbar",
)

PAGINAS_ESPERADAS = ("consultivo.py", "pontos.py", "qtde_os.py")


def _normalizar(css: str) -> str:
    return " ".join(css.split())


def test_helper_gera_regras_essenciais() -> None:
    """O helper precisa emitir a base da tabela e as barras de rolagem."""
    css = _normalizar(css_tabela_corporativa())
    for trecho in (
        ".corp-table {",
        "width: 100% !important",
        "border-collapse: collapse !important",
        ".corp-table thead th {",
        "text-transform: uppercase !important",
        ".corp-table td.num {",
        "font-variant-numeric: tabular-nums !important",
        ".corp-table-wrap::-webkit-scrollbar",
        ".corp-table-wrap::-webkit-scrollbar-thumb:hover",
    ):
        assert trecho in css, f"CSS do helper não contém {trecho!r}"


def test_parametros_sao_respeitados() -> None:
    """Parâmetros de densidade, gradiente e raio precisam aparecer no CSS."""
    css = _normalizar(
        css_tabela_corporativa(
            fonte_px=10.5,
            padding="4px 6px",
            altura_linha="1.25",
            gradiente_cabecalho="linear-gradient(180deg, #012869 0%, #1E3A8A 100%)",
            raio_scrollbar="10px",
            colapsar_bordas=False,
        )
    )
    assert "font-size: 10.5px !important" in css
    assert "padding: 4px 6px !important" in css
    assert "line-height: 1.25 !important" in css
    assert "1E3A8A" in css
    assert css.count("border-radius: 10px !important") == 2  # trilho + barra
    assert "border-collapse" not in css, "colapsar_bordas=False deve omitir a regra"


def _css_local_por_pagina() -> dict[str, str]:
    """CSS declarado em literais <style> de cada página."""
    resultado: dict[str, str] = {}
    for caminho in sorted((RAIZ / "pages").glob("*.py")):
        blocos = []
        for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
            if (
                isinstance(no, ast.Constant)
                and isinstance(no.value, str)
                and "<style>" in no.value
            ):
                blocos += [m.group(1) for m in re.finditer(r"<style>(.*?)</style>", no.value, re.S)]
        resultado[caminho.name] = "\n".join(blocos)
    return resultado


def test_paginas_nao_reduplicam_css_da_tabela() -> None:
    """Nenhuma página deve redeclarar os seletores centralizados."""
    ofensas: list[str] = []
    for pagina, css in _css_local_por_pagina().items():
        for seletor in SELETORES_CENTRALIZADOS:
            # ignora os derivados (.corp-table td.col-x, .corp-table-wrap {...})
            padrao = re.compile(re.escape(seletor) + r"\s*(,|\{|$)", re.M)
            for m in padrao.finditer(css):
                # `.corp-table {` no início de uma linha = declaração local
                linha = css.rfind("\n", 0, m.start()) + 1
                if css[linha : m.start()].strip() == "":
                    ofensas.append(f"{pagina}: {seletor}")
                    break
    assert not ofensas, (
        "CSS da tabela corporativa voltou a ser declarado nas páginas — use "
        "components.css_paginas.aplicar_css_tabela_corporativa:\n  "
        + "\n  ".join(sorted(set(ofensas)))
    )


def test_paginas_da_tabela_chamam_o_helper() -> None:
    """Páginas que exibem .corp-table precisam chamar o CSS compartilhado."""
    texto_completo = "\n".join(
        caminho.read_text(encoding="utf-8")
        for caminho in (RAIZ / "pages").glob("*.py")
    )
    for pagina in PAGINAS_ESPERADAS:
        conteudo = (RAIZ / "pages" / pagina).read_text(encoding="utf-8")
        assert "corp-table" in conteudo, f"{pagina} deveria usar a tabela corporativa"
        assert "aplicar_css_tabela_corporativa(" in conteudo, (
            f"{pagina} usa .corp-table mas não chama aplicar_css_tabela_corporativa()"
        )
    assert texto_completo  # sanity: arquivos lidos


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
