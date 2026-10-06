"""Testes unitários para os resumos e indicadores da página inicial."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pages.home as home  # noqa: E402

FUSO = ZoneInfo("America/Sao_Paulo")


def test_resumir_dados_conta_linhas_em_abas_dataframe() -> None:
    """O número de registros deve ser a soma das linhas, não das abas."""
    dados = {
        "Prod": pd.DataFrame({"os": [1, 2, 3]}),
        "Gpon": pd.DataFrame({"id": [10, 11]}),
        "Sem dados": pd.DataFrame(columns=["id"]),
    }

    resumo = home.resumir_dados_producao(dados)

    assert resumo.registros == 5
    assert resumo.tabelas == 3
    assert resumo.tabelas_com_dados == 2
    assert resumo.carregado


def test_resumir_dados_aceita_estrutura_legada_e_vazia() -> None:
    """Mantém compatibilidade com listas antigas sem tratar dict vazio como carga."""
    resumo_legado = home.resumir_dados_producao([{"os": 1}, {"os": 2}])
    resumo_vazio = home.resumir_dados_producao({})

    assert (resumo_legado.registros, resumo_legado.tabelas) == (2, 1)
    assert resumo_legado.carregado
    assert resumo_vazio.registros == 0
    assert resumo_vazio.tabelas == 0
    assert not resumo_vazio.carregado


def test_formatar_data_pt_br_nao_depende_do_locale() -> None:
    """Nomes de meses aparecem em português em qualquer locale do servidor."""
    assert home.formatar_data_pt_br(datetime(2025, 3, 8, tzinfo=FUSO)) == (
        "8 de março de 2025"
    )


def test_metricas_refletem_registros_e_estado_de_cada_fonte(monkeypatch) -> None:
    """A Home diferencia carga parcial e mostra metadados de fontes com falha."""
    instante = datetime(2025, 3, 8, 12, 30, tzinfo=FUSO)
    session_state = {
        "dados_prod": {
            "Prod": pd.DataFrame({"os": [1, 2, 3]}),
            "Gpon": pd.DataFrame({"id": [10, 11]}),
        },
        "status_fontes": {
            "Produção": SimpleNamespace(
                ok=True,
                linhas=5,
                ultimo_sucesso=instante,
                ultima_tentativa=instante,
                erro=None,
            ),
            "Consultivo": {
                "ok": False,
                "linhas": "8",
                "ultimo_sucesso": instante,
                "ultima_tentativa": instante,
                "erro": "Timeout\nna leitura",
            },
        },
        "ultima_atualizacao": instante,
        "ultima_tentativa_sync": instante,
    }
    monkeypatch.setattr(home.st, "session_state", session_state)

    info = home._obter_metricas_base()

    assert info["total_linhas"] == 5
    assert info["tabelas"] == 2
    assert info["status_carga"] == "Parcial"
    assert info["fontes_ok"] == 1
    assert info["fontes_total"] == 2
    assert info["fontes_com_falha"] == ["Consultivo"]
    consultivo = info["fontes"][1]
    assert consultivo["tem_sucesso_anterior"]
    assert consultivo["linhas"] == 8
    assert consultivo["erro"] == "Timeout na leitura"
    assert info["ultima_tentativa_curta"] == "08/03/2025 12:30"


def test_fontes_sem_sucesso_anterior_sao_reportadas_com_falha(monkeypatch) -> None:
    """Uma falha sem snapshot anterior não deve parecer uma carga válida."""
    monkeypatch.setattr(
        home.st,
        "session_state",
        {
            "dados_prod": None,
            "status_fontes": {
                "Produção": SimpleNamespace(
                    ok=False,
                    linhas=0,
                    ultimo_sucesso=None,
                    ultima_tentativa=None,
                    erro="ConnectionError",
                )
            },
        },
    )

    info = home._obter_metricas_base()

    assert info["status_carga"] == "Com falhas"
    assert not info["carregado"]
    assert info["fontes"][0]["ultimo_sucesso"] == "Não disponível"
    assert not info["fontes"][0]["tem_sucesso_anterior"]


def test_home_renderiza_estado_das_fontes_sem_excecao() -> None:
    """A Home apresenta sucesso, fallback e falha sem interromper a renderização."""
    instante = datetime(2025, 3, 8, 12, 30, tzinfo=FUSO)
    app = AppTest.from_file(str(RAIZ / "pages" / "home.py"), default_timeout=60)
    app.session_state["dados_prod"] = {
        "Prod": pd.DataFrame({"os": [1, 2]}),
        "Gpon": pd.DataFrame({"id": [3]}),
    }
    app.session_state["status_fontes"] = {
        "Produção": SimpleNamespace(
            ok=True,
            linhas=3,
            ultimo_sucesso=instante,
            ultima_tentativa=instante,
            erro=None,
        ),
        "Consultivo": SimpleNamespace(
            ok=False,
            linhas=8,
            ultimo_sucesso=instante,
            ultima_tentativa=instante,
            erro="Timeout na leitura",
        ),
        "Ativos": SimpleNamespace(
            ok=False,
            linhas=0,
            ultimo_sucesso=None,
            ultima_tentativa=instante,
            erro="ConnectionError",
        ),
    }
    app.session_state["ultima_atualizacao"] = instante
    app.session_state["ultima_tentativa_sync"] = instante

    app.run()

    assert not list(app.exception)
    assert len(app.success) == 1
    assert len(app.warning) == 1
    assert len(app.error) == 1
