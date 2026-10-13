"""Camada de serviços de infraestrutura, integração externa e domínio do Portal TOTALE.

Módulos:

* ``google_drive_client``: download/parse de Google Drive e Sheets (HTTP resiliente).
* ``datas_dashboard``: motor de datas (ISO/BR, fuso, janelas) sem dependência de Streamlit.
"""

from .datas_dashboard import (
    converter_serie_datas,
    converter_serie_datas_mdy,
    data_ancora_projecao,
    detectar_coluna_data,
    garantir_datetime,
    garantir_datetime_auto,
    limites_datas_disponiveis,
    mascara_periodo,
    normalizar_janela_datas,
    validar_estado_janela,
)
from .google_drive_client import (
    adicionar_confirm_url,
    baixar_arquivo_drive,
    baixar_bytes_drive,
    carregar_excel_drive,
    carregar_planilha_gsheets_csv,
    criar_sessao_http,
    e_resposta_html,
    extrair_token_confirm,
    ler_csv_remoto,
    ler_csv_uma_tentativa,
    separadores_csv,
    urls_download_drive,
)

__all__ = [
    "adicionar_confirm_url",
    "baixar_arquivo_drive",
    "baixar_bytes_drive",
    "carregar_excel_drive",
    "carregar_planilha_gsheets_csv",
    "converter_serie_datas",
    "converter_serie_datas_mdy",
    "criar_sessao_http",
    "data_ancora_projecao",
    "detectar_coluna_data",
    "e_resposta_html",
    "extrair_token_confirm",
    "garantir_datetime",
    "garantir_datetime_auto",
    "ler_csv_remoto",
    "ler_csv_uma_tentativa",
    "limites_datas_disponiveis",
    "mascara_periodo",
    "normalizar_janela_datas",
    "separadores_csv",
    "urls_download_drive",
    "validar_estado_janela",
]
