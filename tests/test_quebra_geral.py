from __future__ import annotations

import pandas as pd

from pages.quebra_geral import DataLoader, Utils


def test_normalizar_login_remove_decimal_de_identificador_numerico() -> None:
    assert Utils.normalizar_login("123.0") == "123"
    assert Utils.normalizar_login("00123.00") == "123"
    assert Utils.normalizar_login("123") == "123"


def test_preparar_base_correlaciona_login_decimal_com_lista_de_ativos() -> None:
    ativos = DataLoader._processar_lista_ativos(
        pd.DataFrame(
            {
                "Login": [123],
                "Técnico": ["Técnico Exemplo"],
                "Monitor": ["Monitor Exemplo"],
                "Base": ["São Paulo"],
            }
        )
    )
    ordens = pd.DataFrame(
        {
            "Contrato": ["OS-1"],
            "Login do Técnico": ["123.0"],
            "Status da O.S 1": ["EXECUTADA"],
        }
    )

    base = DataLoader.preparar_base(ordens, ativos)

    assert base.loc[0, "TÉCNICO"] == "TÉCNICO EXEMPLO"
    assert base.loc[0, "MONITOR"] == "MONITOR EXEMPLO"
    assert base.attrs["logins_encontrados"] == 1


def test_match_nao_depende_do_preenchimento_do_nome_do_tecnico() -> None:
    ativos = DataLoader._processar_lista_ativos(
        pd.DataFrame(
            {
                "Login": ["123"],
                "Técnico": [""],
                "Monitor": ["Monitor Exemplo"],
            }
        )
    )
    colunas_originais = list(ativos.columns)
    ordens = pd.DataFrame(
        {
            "Contrato": ["OS-1"],
            "Login do Técnico": ["123"],
            "Status da O.S 1": ["EXECUTADA"],
        }
    )

    base = DataLoader.preparar_base(ordens, ativos)

    assert base.loc[0, "TÉCNICO"] == "NÃO MAPEADO"
    assert base.loc[0, "MONITOR"] == "MONITOR EXEMPLO"
    assert base.attrs["logins_encontrados"] == 1
    assert list(ativos.columns) == colunas_originais
