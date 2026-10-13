"""Guardas de organização do projeto.

Contexto (limpeza de 2026-10-13): a árvore acumulava definições nunca chamadas
(`calcular_meta_acumulada_monitor`, `fmt_hora`, `render_sidebar_kpi`, `_safe_float`,
`filtrar_geometria_por_municipios`, `LinhaResultado`, `_resolver_cor_tema`,
`_markdown_inline_para_html`, `_estado_str`, `StreamlitContainer`), uma página órfã
(`pages/login.py`, com cadastro aberto e um segundo sistema de senhas), 13 pacotes
declarados sem nenhum uso e o motor de datas morando dentro de `pages/`.

Estes testes impedem que os três problemas estruturais voltem:

1. **`pages/` contém páginas, não bibliotecas** — todo arquivo em `pages/` precisa
   estar registrado em `st.navigation` no entrypoint (e vice-versa). Código de
   domínio vai para `components/`, `services/` ou `robo/`.
2. **Toda importação de terceiro está declarada** em `requirements*.txt` — evita o
   caso inverso do que foi limpo: importar algo que só existe por dependência
   transitiva.
3. **Domínio não depende da UI no import** — `services/` e `robo/robo_engine.py`
   podem importar Streamlit apenas dentro de funções (caminho opcional/lazy), nunca
   no topo do módulo.

Execução:

    python tests/test_estrutura_projeto.py    # execução direta (stdlib)
    pytest tests/test_estrutura_projeto.py    # via pytest
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

IGNORADOS = {
    ".git",
    "__pycache__",
    ".venv",
    ".venv-check",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "dist",
    "node_modules",
}

# Pacotes internos (importáveis sem estarem em requirements)
PACOTES_LOCAIS = {"components", "config", "pages", "robo", "services", "tests"}

# Páginas podem importar a página irmã pelo nome puro no caminho de execução
# direta (`streamlit run pages/quebra_unificada.py`). A lista é derivada da
# própria árvore: um `import` para arquivo inexistente continua sendo falha.
MODULOS_IRMAOS = {caminho.stem for caminho in (RAIZ / "pages").glob("*.py")}

# importável -> nome de distribuição, quando os dois não coincidem
ALIAS_DE_DISTRIBUICAO = {
    "pil": "pillow",
    "google": "google-auth",
    "streamlit_gsheets": "st-gsheets-connection",
    "streamlit_folium": "streamlit-folium",
    "streamlit_autorefresh": "streamlit-autorefresh",
}

# Módulos de domínio que não podem depender da UI no topo do arquivo.
MODULOS_SEM_UI = (*sorted((RAIZ / "services").glob("*.py")), RAIZ / "robo" / "robo_engine.py")


def _arquivos(raiz: Path, padrao: str) -> list[Path]:
    return sorted(
        caminho
        for caminho in raiz.rglob(padrao)
        if not any(parte in IGNORADOS for parte in caminho.relative_to(RAIZ).parts)
    )


def _normalizar(nome: str) -> str:
    return re.sub(r"[^a-z0-9]", "", nome.lower())


def _paginas_registradas() -> set[str]:
    """Caminhos de página declarados em `st.Page("pages/...")` no entrypoint."""
    arvore = ast.parse((RAIZ / "streamlit_app.py").read_text(encoding="utf-8"))
    registradas: set[str] = set()
    for no in ast.walk(arvore):
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr == "Page"
            and no.args
            and isinstance(no.args[0], ast.Constant)
            and isinstance(no.args[0].value, str)
        ):
            registradas.add(no.args[0].value)
    return registradas


def test_pages_contem_somente_paginas_navegaveis() -> None:
    """Todo .py em pages/ está na navegação, e toda página navegável existe."""
    registradas = _paginas_registradas()
    assert registradas, "Nenhuma página encontrada em streamlit_app.py (st.Page)."

    existentes_em_pages = {
        f"pages/{caminho.name}" for caminho in _arquivos(RAIZ / "pages", "*.py")
    }

    orfas = sorted(existentes_em_pages - registradas)
    assert not orfas, (
        "Arquivo em pages/ que não é página navegável — mova para components/, "
        f"services/ ou robo/ (ou registre em st.navigation): {orfas}"
    )

    quebradas = sorted(registradas - existentes_em_pages)
    assert not quebradas, f"Página registrada em st.navigation sem arquivo: {quebradas}"


def _declarados_em_requirements() -> set[str]:
    declarados: set[str] = set()
    for arquivo in ("requirements.txt", "requirements-test.txt", "requirements-dev.txt"):
        caminho = RAIZ / arquivo
        if not caminho.is_file():
            continue
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or linha.startswith("-r"):
                continue
            declarados.add(_normalizar(re.split(r"[<>=\[\s;]", linha)[0]))
    assert declarados, "Nenhuma dependência declarada encontrada."
    return declarados


def _modulos_importados() -> set[str]:
    importados: set[str] = set()
    for caminho in _arquivos(RAIZ, "*.py"):
        if "tests" in caminho.parts:
            continue
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados.update(alias.name.split(".")[0] for alias in no.names)
            elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
                importados.add(no.module.split(".")[0])
    return importados


def test_dependencias_importadas_estao_declaradas() -> None:
    """Todo import de terceiro precisa de declaração explícita em requirements."""
    declarados = _declarados_em_requirements()
    stdlib = set(sys.stdlib_module_names)

    faltando: list[str] = []
    for modulo in sorted(_modulos_importados()):
        if (
            modulo in stdlib
            or modulo in PACOTES_LOCAIS
            or modulo in MODULOS_IRMAOS
            or modulo.startswith("_")
        ):
            continue
        distribuicao = ALIAS_DE_DISTRIBUICAO.get(modulo.lower(), modulo)
        if _normalizar(distribuicao) not in declarados:
            faltando.append(f"{modulo} (distribuição: {distribuicao})")

    assert not faltando, (
        "Import de terceiro sem declaração em requirements*.txt — dependências "
        "transitivas não contam:\n  " + "\n  ".join(faltando)
    )


def test_dominio_nao_importa_streamlit_no_topo() -> None:
    """services/ e robo_engine podem usar Streamlit só dentro de funções (lazy)."""
    ofensas: list[str] = []
    for caminho in MODULOS_SEM_UI:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        for no in arvore.body:  # apenas imports de topo do módulo
            if isinstance(no, ast.Import) and any(
                alias.name.split(".")[0] == "streamlit" for alias in no.names
            ):
                ofensas.append(f"{caminho.relative_to(RAIZ)}:{no.lineno}")
            elif (
                isinstance(no, ast.ImportFrom)
                and no.module
                and no.module.split(".")[0] == "streamlit"
            ):
                ofensas.append(f"{caminho.relative_to(RAIZ)}:{no.lineno}")
    assert not ofensas, (
        "Módulo de domínio importando Streamlit no topo do arquivo (use import "
        f"dentro da função): {ofensas}"
    )


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
        except Exception as exc:  # noqa: BLE001 — runner de linha de comando
            falhas += 1
            print(f"FALHOU  {teste.__name__}: {exc}")
        else:
            print(f"OK      {teste.__name__}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_main())
