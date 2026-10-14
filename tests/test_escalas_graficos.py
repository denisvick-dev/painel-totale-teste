"""Guardas da régua numérica compartilhada (`components/escalas_graficos.py`).

Contexto (2026-10-14): os gráficos de `consultivo.py`, `qtde_os.py` e
`rota_inicial.py` usavam a escala automática do Plotly — eixos que não começavam
em zero, tetos arbitrários (12, 37, 1180…) e passos de grade diferentes para o
mesmo tipo de dado. Dois painéis lado a lado medindo a mesma métrica pareciam
incomparáveis. O módulo `components/escalas_graficos.py` passou a concentrar a
régua e estes testes garantem que ela continue:

1. zero na base de barras/áreas e teto múltiplo de um passo "bonito" (1/2/2.5/5/10);
2. passo constante e grade com uma quantidade previsível de divisões;
3. séries que medem a mesma coisa podem dividir a mesma régua;
4. uma régua existente pode crescer (simulação) sem trocar o passo;
5. as três páginas consomem o helper e não voltam a definir escala no eixo.

Execução:

    python tests/test_escalas_graficos.py     # execução direta (stdlib)
    pytest tests/test_escalas_graficos.py     # via pytest
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from components.escalas_graficos import (  # noqa: E402
    PASSOS_BONITOS,
    aplicar_escala,
    estender_limites,
    limites_escala,
    passo_bonito,
    teto_bonito,
)

PAGINAS_COM_ESCALA = ("consultivo.py", "qtde_os.py", "rota_inicial.py")


def _eixo(fig: go.Figure, eixo: str = "y") -> dict:
    """Configuração do eixo aplicada à figura (``plotly`` guarda como dict)."""
    chave = "xaxis" if eixo == "x" else "yaxis"
    return dict(fig.layout.to_plotly_json().get(chave) or {})


# ── 1. Base em zero e teto "bonito" ───────────────────────────────────────────


def test_barras_e_areas_comecam_em_zero() -> None:
    """A altura da barra precisa ser proporcional ao valor, sem base deslocada."""
    for serie in ([3], [12, 7], [1180], [0.4, 0.9]):
        minimo, teto, passo = limites_escala(serie)
        assert minimo == 0.0, (serie, minimo)
        assert teto > max(serie) > 0


def test_teto_cobre_o_maior_valor_com_folga_e_fecha_no_passo() -> None:
    """Teto cobre o maior valor, é múltiplo do passo e tem folga para o rótulo."""
    for maior in (9, 12, 37, 48, 120, 460, 1180, 2400, 11800, 36200):
        _, teto, passo = limites_escala([maior])
        assert teto >= maior > 0, (maior, teto)
        assert teto % passo == 0, (maior, teto, passo)
        assert teto <= maior * 1.6, (maior, teto, "folga excessiva")


def test_grade_fica_entre_duas_e_dez_divisoes() -> None:
    """Grade previsível: nem um único passo perdido, nem 20 riscos no eixo."""
    for maior in (3, 9, 12, 37, 48, 120, 460, 1180, 2400, 11800, 36200, 950000):
        minimo, teto, passo = limites_escala([maior])
        divisoes = (teto - minimo) / passo
        assert abs(divisoes - round(divisoes)) < 1e-9, (maior, divisoes)
        assert 2 <= round(divisoes) <= 10, (maior, round(divisoes))


def test_sem_dados_devolve_eixo_neutro() -> None:
    """Página sem dados não pode quebrar nem gerar eixo invertido."""
    for entrada in ([], [None], [float("nan")], [], [""], ["—"]):
        assert limites_escala(entrada) == (0.0, 1.0, 1.0)


# ── 2. Passos "bonitos" ───────────────────────────────────────────────────────


def test_passo_bonito_usa_apenas_1_2_5_e_10_por_magnitude() -> None:
    """O passo é 1, 2, 2.5, 5 ou 10 vezes 10^n — nada de 3, 7 ou 13."""
    for valor in (1, 3, 7, 9, 13, 19, 37, 48, 120, 460, 1180, 36200):
        passo = passo_bonito(valor)
        magnitude = 10.0 ** int(__import__("math").floor(__import__("math").log10(passo)))
        assert round(passo / magnitude, 6) in PASSOS_BONITOS, (valor, passo)
        assert passo >= 1  # contagens: passo fracionário não faz sentido


def test_passo_fracionario_quando_a_metrica_nao_e_contagem() -> None:
    """Percentuais e médias aceitam passo decimal (0.2, 0.5, 2.5…)."""
    minimo, teto, passo = limites_escala([0.4, 0.9], inteiro=False)
    assert (minimo, teto) == (0.0, 1.0)
    assert abs(passo - 0.2) < 1e-9
    assert abs(teto_bonito(1.06, inteiro=False, passo=passo) - 1.2) < 1e-9


def test_teto_minimo_permite_amarrar_escalas() -> None:
    """Uma série pequena pode herdar o teto de outro gráfico já exibido."""
    assert limites_escala([5], teto_minimo=40) == (0.0, 40.0, 10.0)
    assert limites_escala([37], teto_minimo=40) == (0.0, 40.0, 10.0)


def test_valores_aceita_series_escalares_e_texto_numerico() -> None:
    """Aceita listas, Series, escalares e números em texto; ignora o resto."""
    assert limites_escala([10, "20", None, "n/d", True, float("inf")]) == limites_escala(
        [10, 20]
    )
    serie = pd.Series([100, 250, 90], dtype="int64")
    assert limites_escala(serie) == limites_escala([100, 250, 90])
    # "1.234" é ambíguo em pt-BR (milhar) — de propósito não é interpretado
    assert limites_escala(["1.234"]) == (0.0, 1.0, 1.0)


# ── 3. Régua compartilhada e régua estendida ──────────────────────────────────


def test_series_da_mesma_metrica_dividem_a_mesma_regua() -> None:
    """Top 10 e matriz (consultivos) e Atual × Ideal (O.S.) usam um teto só."""
    compartilhada = limites_escala([120, 140, 90], [130, 125, 100])
    assert compartilhada == limites_escala([140])  # teto vem do maior valor
    fig_a, fig_b = go.Figure(go.Bar(y=[120, 140])), go.Figure(go.Scatter(x=[130, 125]))
    aplicar_escala(fig_a, [120, 140], limites=compartilhada)
    aplicar_escala(fig_b, [130, 125], eixo="x", limites=compartilhada)
    assert _eixo(fig_a, "y")["range"] == _eixo(fig_b, "x")["range"]
    assert _eixo(fig_a, "y")["dtick"] == _eixo(fig_b, "x")["dtick"]


def test_estender_limites_sobe_o_teto_sem_trocar_o_passo() -> None:
    """Simulação acima do previsto amplia a régua em degraus do mesmo passo."""
    base = limites_escala([120, 140, 90])
    assert base == (0.0, 150.0, 50.0)
    assert estender_limites(base, [120, 140]) == base  # nada a fazer
    _, teto, passo = estender_limites(base, [120, 400])
    assert passo == base[2], "o passo não pode mudar — os gráficos deixariam de ser comparáveis"
    assert teto == 400.0
    assert teto % passo == 0


# ── 4. Aplicação na figura ────────────────────────────────────────────────────


def test_aplicar_escala_configura_o_eixo_e_devolve_a_figura() -> None:
    """A figura recebe faixa, passo, formato pt-BR e volta encadeável."""
    fig = go.Figure(go.Bar(x=["a", "b"], y=[120, 140]))
    devolvida = aplicar_escala(fig, [120, 140])
    eixo = _eixo(fig, "y")
    assert devolvida is fig
    assert eixo["range"] == [0.0, 150.0]
    assert eixo["dtick"] == 50.0
    assert eixo["tick0"] == 0.0
    assert eixo["tickformat"] == ",.0f"
    assert fig.layout.separators == ",."


def test_aplicar_escala_em_barras_horizontais_usa_o_eixo_x() -> None:
    """Ranking horizontal mede no X — o Y é categórico."""
    fig = go.Figure(go.Bar(x=[3, 9], y=["a", "b"], orientation="h"))
    aplicar_escala(fig, [3, 9], eixo="x")
    assert _eixo(fig, "x")["range"] == [0.0, 10.0]
    assert not _eixo(fig, "y").get("dtick")


def test_aplicar_escala_ignora_series_vazias_sem_quebrar() -> None:
    """Sem dados a figura permanece válida (eixo neutro), sem exceção."""
    fig = go.Figure(go.Bar(x=[], y=[]))
    aplicar_escala(fig, [])
    assert _eixo(fig, "y")["range"] == [0.0, 1.0]


# ── 5. Guardas das páginas ────────────────────────────────────────────────────


def test_paginas_usam_a_regua_compartilhada() -> None:
    """As três páginas consomem o helper em vez de confiar no automático."""
    for pagina in PAGINAS_COM_ESCALA:
        codigo = (RAIZ / "pages" / pagina).read_text(encoding="utf-8")
        assert "components.escalas_graficos" in codigo, f"{pagina} não importa a régua"
        assert "aplicar_escala(" in codigo, f"{pagina} não aplica a régua"


def test_paginas_nao_definem_escala_de_eixo_inline() -> None:
    """Escala no eixo só pelo helper: nada de ``range=``/``dtick=`` avulso."""
    ofensas: list[str] = []
    padrao = re.compile(r"(?:update_[xy]axes\([^)]*\b(?:range|dtick|tickformat)=)|(?:\b(?:xaxis|yaxis)_range=)")
    for pagina in PAGINAS_COM_ESCALA:
        texto = (RAIZ / "pages" / pagina).read_text(encoding="utf-8")
        for numero, linha in enumerate(texto.splitlines(), start=1):
            if "range_color" in linha:  # escala de cor, não eixo
                continue
            if padrao.search(linha):
                ofensas.append(f"{pagina}:{numero}: {linha.strip()[:70]}")
    assert not ofensas, (
        "Escala de eixo definida direto na página — use "
        "components.escalas_graficos.aplicar_escala:\n  " + "\n  ".join(ofensas)
    )


def test_modulo_nao_quebra_com_plotly_antigo() -> None:
    """O helper não depende de API nova do Plotly (>=5.24 é o piso do projeto)."""
    arvore = ast.parse(
        (RAIZ / "components" / "escalas_graficos.py").read_text(encoding="utf-8")
    )
    importados = {
        alias.name
        for no in ast.walk(arvore)
        if isinstance(no, ast.Import)
        for alias in no.names
    } | {
        no.module
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module
    }
    assert "plotly.graph_objects" in importados
    assert "streamlit" not in importados, "o helper precisa ser testável sem subir o app"


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
