"""Escalas numéricas unificadas para os gráficos Plotly das páginas operacionais.

Contexto (2026-10-14)
---------------------
`consultivo.py`, `qtde_os.py` e `rota_inicial.py` montavam os gráficos com
`plotly.express`/`graph_objects` puros: cada eixo ficava com a escala automática
do Plotly. O resultado eram réguas diferentes para o mesmo tipo de dado — barras
que pareciam "cheias" em um painel e "vazias" no painel ao lado, eixos que não
começavam em zero (distorcendo a proporção entre as barras) e passos de grade
arbitrários (1, 7, 13, 19…), o que impedia comparar dois gráficos de relance.

Este módulo concentra a régua única usada por essas páginas:

1. **zero obrigatório** em barras/áreas — a altura da barra é proporcional ao
   valor, sem começar no mínimo dos dados;
2. **teto "bonito"** — o topo do eixo é arredondado para múltiplo de um passo
   de 1, 2, 2.5, 5 ou 10 × 10^n, com folga (padrão 6%) para o rótulo da maior
   barra não encostar no limite;
3. **passo de grade único por métrica** — duas séries que medem a mesma coisa
   podem ser passadas juntas em :func:`limites_escala` e passam a dividir
   exatamente o mesmo teto e o mesmo passo (ex.: Top 10 × Matriz em
   `consultivo.py`; O.S. Atual × Ideal e O.S. Atual × Simulada em
   `rota_inicial.py`);
4. **números em pt-BR** — a grade usa o separador de milhar do portal
   (`1.000` em vez de `1000`).

Uso
---
::

    from components.escalas_graficos import aplicar_escala, limites_escala

    # escala própria do gráfico
    fig = px.bar(df, x="Monitor", y="Total Consultivos")
    aplicar_escala(fig, df["Total Consultivos"])

    # escala compartilhada entre dois gráficos da mesma métrica
    escala = limites_escala(df["Total Consultivos"])
    aplicar_escala(fig_top10, df["Total Consultivos"], limites=escala)
    aplicar_escala(fig_matriz, df["Total Consultivos"], eixo="x", limites=escala)

Nada aqui depende de Streamlit: os helpers recebem a figura Plotly já montada e
devolvem a mesma figura (encadeável), o que mantém as páginas testáveis sem
subir o app.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable, Sequence

import numpy as np
import plotly.graph_objects as go

__all__ = [
    "PASSOS_BONITOS",
    "aplicar_escala",
    "estender_limites",
    "limites_escala",
    "passo_bonito",
    "teto_bonito",
]

#: Multiplicadores aceitos para o passo da grade (× potência de 10).
PASSOS_BONITOS: tuple[float, ...] = (1.0, 2.0, 2.5, 5.0, 10.0)

#: Quantidade de divisões desejada no eixo; define o tamanho do passo.
ALVO_DIVISOES = 5

#: Folga sobre o maior valor para o rótulo da barra não tocar o teto.
FOLGA_PADRAO = 0.06


#: Texto numérico aceito: apenas decimal em notação ASCII ("20", "0.4", "-3").
#: Rótulos já formatados com separador de milhar ("1.234") **não** entram, porque
#: em pt-BR seriam lidos como mil e duzentos e trinta e quatro.
_PADRAO_NUMERO_TEXTO = re.compile(r"^-?\d+(?:\.\d+)?$")


def _para_float(item: Any) -> float | None:
    """Converte item em float finito; ignora vazios, textos e não numéricos.

    Texto só passa quando é decimal ASCII inequívoco ("20", "0.4", "-3"):
    rótulos com separador de milhar pt-BR ("1.234") são descartados em vez de
    virarem 1,234 na régua.
    """
    if item is None or isinstance(item, bool):
        return None
    if isinstance(item, str):
        texto = item.strip()
        if not _PADRAO_NUMERO_TEXTO.match(texto):
            return None
        if "." in texto and len(texto.split(".")[1]) == 3 and "," not in texto:
            # "1.234" / "12.345": ambíguo (milhar pt-BR) → fora da régua
            return None
        item = texto
    try:
        valor = float(item)
    except (TypeError, ValueError):
        return None
    return valor if math.isfinite(valor) else None


def _valores(series: Sequence[Any]) -> list[float]:
    """Achata séries/escalares em uma lista de floats finitos (ignora vazios)."""
    numeros: list[float] = []
    for serie in series:
        if serie is None or isinstance(serie, bytes):
            continue
        if isinstance(serie, (str, int, float, np.integer, np.floating)):
            candidatos: Iterable[Any] = [serie]
        else:
            try:
                candidatos = list(serie)
            except TypeError:  # escalar exótico (ex.: Decimal)
                candidatos = [serie]
        for item in candidatos:
            valor = _para_float(item)
            if valor is not None:
                numeros.append(valor)
    return numeros


def passo_bonito(
    valor: float, *, alvo_divisoes: int = ALVO_DIVISOES, inteiro: bool = True
) -> float:
    """Menor passo "bonito" (1, 2, 2.5, 5, 10 × 10^n) que cobre ``valor``.

    ``alvo_divisoes`` é quantas divisões o eixo deveria ter; com ``inteiro=True``
    (padrão, para contagens) o passo nunca fica abaixo de 1.
    """
    if not math.isfinite(valor) or valor <= 0:
        return 1.0
    bruto = valor / max(1, int(alvo_divisoes))
    magnitude = 10.0 ** math.floor(math.log10(bruto))
    passo = 10.0 * magnitude
    for fator in PASSOS_BONITOS:
        candidato = fator * magnitude
        if candidato >= bruto:
            passo = candidato
            break
    if inteiro:
        # arredonda o passo para cima: 2.5 vira 3 (5 divisões) em vez de 2 (7 divisões)
        passo = max(1.0, float(math.ceil(passo)))
    return float(passo)


def teto_bonito(
    valor: float,
    *,
    alvo_divisoes: int = ALVO_DIVISOES,
    inteiro: bool = True,
    passo: float | None = None,
) -> float:
    """Teto do eixo: múltiplo do passo bonito imediatamente acima de ``valor``.

    Informe ``passo`` para arredondar um valor já com folga usando o passo
    calculado sobre o dado original (mantém a grade fina sem estourar o alvo de
    divisões).
    """
    if not math.isfinite(valor) or valor <= 0:
        return 1.0
    passo = passo or passo_bonito(valor, alvo_divisoes=alvo_divisoes, inteiro=inteiro)
    return float(math.ceil(valor / passo) * passo)


def limites_escala(
    *series: Any,
    zero: bool = True,
    alvo_divisoes: int = ALVO_DIVISOES,
    folga: float = FOLGA_PADRAO,
    inteiro: bool = True,
    teto_minimo: float | None = None,
) -> tuple[float, float, float]:
    """Régua ``(mínimo, teto, passo)`` unificada para uma ou mais séries.

    Passe todas as séries que precisam dividir a mesma escala: o teto considera o
    maior valor do conjunto, então os gráficos ficam comparáveis barra a barra.
    ``teto_minimo`` permite amarrar o teto de um gráfico ao de outro já exibido
    (ex.: simulação que nunca deve ficar com escala menor que a distribuição atual).
    Sem dados, devolve ``(0.0, 1.0, 1.0)`` — eixo neutro em vez de erro.
    """
    numeros = _valores(series)
    maior = max(numeros) if numeros else 0.0
    menor = min(numeros) if numeros else 0.0

    alvo = max(1.0, maior * (1.0 + max(0.0, folga))) if maior > 0 else 1.0
    # O passo vem do dado original (não da folga) para a grade não ficar grossa
    # quando o maior valor fica logo acima de um limiar "bonito" (ex.: 1180).
    passo = passo_bonito(maior, alvo_divisoes=alvo_divisoes, inteiro=inteiro)
    teto = teto_bonito(alvo, alvo_divisoes=alvo_divisoes, inteiro=inteiro, passo=passo)
    if teto_minimo is not None and math.isfinite(teto_minimo) and teto_minimo > teto:
        # Régua amarrada a outro gráfico: o teto vem de fora e a grade se ajusta a ele.
        teto = float(teto_minimo)
        passo = passo_bonito(teto, alvo_divisoes=alvo_divisoes, inteiro=inteiro)
        teto = float(math.ceil(teto / passo) * passo)

    if zero:
        minimo = 0.0
    else:
        referencia = min(menor, 0.0) if menor < 0 else menor * (1.0 - max(0.0, folga))
        minimo = float(math.floor(referencia / passo) * passo)
    if minimo >= teto:
        minimo = teto - passo
    return minimo, teto, passo


def estender_limites(
    limites: tuple[float, float, float], *series: Any
) -> tuple[float, float, float]:
    """Amplia o teto de uma régua existente **sem mudar o passo**.

    Usado quando um gráfico irmão (ex.: a simulação de redistribuição de O.S.)
    pode passar do teto do gráfico original: o teto sobe em múltiplos inteiros do
    passo, então as duas figuras continuam na mesma unidade de grade e comparáveis
    — em vez de cada uma ganhar uma escala independente.
    """
    minimo, teto, passo = limites
    numeros = _valores(series)
    if not numeros or passo <= 0:
        return limites
    maior = max(numeros)
    if maior <= teto:
        return limites
    return minimo, float(math.ceil(maior / passo) * passo), passo


def aplicar_escala(
    fig: go.Figure,
    *series: Any,
    eixo: str = "y",
    limites: tuple[float, float, float] | None = None,
    zero: bool = True,
    alvo_divisoes: int = ALVO_DIVISOES,
    folga: float = FOLGA_PADRAO,
    inteiro: bool = True,
    teto_minimo: float | None = None,
    formato: str = ",.0f",
    separadores_br: bool = True,
) -> go.Figure:
    """Aplica a régua unificada ao eixo ``x`` ou ``y`` da figura.

    Quando ``limites`` é informado (vindo de :func:`limites_escala`), a escala é
    literalmente a mesma do outro gráfico; caso contrário é calculada a partir das
    séries recebidas. A figura é devolvida para permitir encadeamento.
    """
    if limites is None:
        limites = limites_escala(
            *series,
            zero=zero,
            alvo_divisoes=alvo_divisoes,
            folga=folga,
            inteiro=inteiro,
            teto_minimo=teto_minimo,
        )
    minimo, teto, passo = limites
    if not all(math.isfinite(v) for v in (minimo, teto, passo)) or teto <= minimo:
        return fig
    opcoes: dict[str, Any] = {
        "range": [minimo, teto],
        "tick0": minimo,
        "dtick": passo,
        "tickformat": formato,
    }
    if str(eixo).lower() == "x":
        fig.update_xaxes(**opcoes)
    else:
        fig.update_yaxes(**opcoes)
    if separadores_br:
        # decimal "," e milhar "." — a mesma convenção dos demais números do portal
        fig.update_layout(separators=",.")
    return fig
