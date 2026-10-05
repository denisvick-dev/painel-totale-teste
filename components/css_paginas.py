"""CSS compartilhado das páginas TOTALE (Design System).

Este módulo concentra os blocos de CSS que estavam **duplicados** entre páginas —
hoje, a família de tabelas corporativas (`.corp-table`), repetida em
`consultivo.py`, `pontos.py` e `qtde_os.py` com pequenas variações de densidade.

Cada página informa os parâmetros que já usava, então o CSS gerado é equivalente
ao que estava escrito à mão; o que muda é existir **um único lugar** para ajustar
a aparência corporativa das tabelas.

Uso (chamar antes do CSS local da página, preservando a ordem do cascade)::

    from components.css_paginas import aplicar_css_tabela_corporativa

    aplicar_css_tabela_corporativa(fonte_px=10.5, padding="4px 6px", altura_linha="1.25")

Páginas que não usam `.corp-table` seguem apenas com o próprio CSS local.
"""

from __future__ import annotations

from components.componentes import injetar_css

# Aparência padrão da marca (cabeçalho e barras de rolagem).
GRADIENTE_CABECALHO_PADRAO = "linear-gradient(180deg, #012869 0%, #1E40AF 100%)"
COR_TRILHO_SCROLLBAR = "#F1F5F9"
COR_BARRA_SCROLLBAR = "#CBD5E1"
COR_BARRA_SCROLLBAR_HOVER = "#94A3B8"


def _bloco(seletor: str, declaracoes: str) -> str:
    """Formata um bloco CSS simples, com indentação legível."""
    linhas = [f"    {seletor} {{"]
    linhas += [f"        {linha.strip()}" for linha in declaracoes.strip().splitlines() if linha.strip()]
    linhas.append("    }")
    return "\n".join(linhas)


def css_tabela_corporativa(
    *,
    fonte_px: float = 11.0,
    padding: str = "5px 8px",
    altura_linha: str = "1.2",
    fonte_celula_px: float | None = None,
    gradiente_cabecalho: str = GRADIENTE_CABECALHO_PADRAO,
    raio_scrollbar: str = "4px",
    colapsar_bordas: bool = True,
    cabecalho_extra: str = "",
    celulas_extra: str = "",
) -> str:
    """Devolve o CSS da tabela corporativa (`.corp-table`).

    Args:
        fonte_px: tamanho da fonte base da tabela.
        padding: espaçamento interno das células.
        altura_linha: `line-height` das células.
        fonte_celula_px: fonte própria das células (opcional).
        gradiente_cabecalho: fundo do `thead`.
        raio_scrollbar: raio das barras de rolagem.
        colapsar_bordas: emite `border-collapse: collapse` (a página `qtde_os`
            mantém o padrão `separate` do navegador — preservado por parâmetro).
        cabecalho_extra: declarações extras do `thead` (ex.: sticky).
        celulas_extra: declarações extras das células.
    """
    celulas = f"font-size: {fonte_celula_px}px !important;" if fonte_celula_px else ""
    if celulas_extra:
        celulas = f"{celulas} {celulas_extra}".strip()

    blocos = [
        _bloco(
            ".corp-table",
            f"""
            width: 100% !important;
            {('border-collapse: collapse !important;' if colapsar_bordas else '')}
            font-size: {fonte_px}px !important;
            """,
        ),
        _bloco(
            ".corp-table th,\n    .corp-table td",
            f"""
            padding: {padding} !important;
            {celulas}
            line-height: {altura_linha} !important;
            """,
        ),
        _bloco(
            ".corp-table thead th",
            f"""
            background: {gradiente_cabecalho} !important;
            color: #FFFFFF !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
            font-size: 10px !important;
            {cabecalho_extra}
            """,
        ),
        # A classe "num" era gerada no HTML das páginas mas não existia no CSS;
        # vivia duplicada em consultivo/pontos — agora é responsabilidade do DS.
        _bloco(
            ".corp-table td.num",
            """
            text-align: right !important;
            font-variant-numeric: tabular-nums !important;
            """,
        ),
        _bloco(
            ".corp-table-wrap::-webkit-scrollbar",
            """
            width: 6px !important;
            height: 6px !important;
            """,
        ),
        _bloco(
            ".corp-table-wrap::-webkit-scrollbar-track",
            f"""
            background: {COR_TRILHO_SCROLLBAR} !important;
            border-radius: {raio_scrollbar} !important;
            """,
        ),
        _bloco(
            ".corp-table-wrap::-webkit-scrollbar-thumb",
            f"""
            background: {COR_BARRA_SCROLLBAR} !important;
            border-radius: {raio_scrollbar} !important;
            """,
        ),
        _bloco(
            ".corp-table-wrap::-webkit-scrollbar-thumb:hover",
            f"""
            background: {COR_BARRA_SCROLLBAR_HOVER} !important;
            """,
        ),
    ]
    return "\n".join(blocos)


def aplicar_css_tabela_corporativa(**kwargs: object) -> None:
    """Injeta na página o CSS de :func:`css_tabela_corporativa`."""
    injetar_css(css_tabela_corporativa(**kwargs))  # type: ignore[arg-type]
