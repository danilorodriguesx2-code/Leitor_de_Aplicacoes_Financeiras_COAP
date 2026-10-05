"""Testes da competencia usada no arquivo CSV ERP."""
from __future__ import annotations

from modules.export import consolidar_csv_erp, competencia_erp, exportar_csv_erp


def _lanc(data_ref: str):
    return {
        "data": data_ref,
        "data_ref": data_ref,
        "valor": 0.78,
        "debito": "3.1.06.01.002",
        "credito": "1.1.01.03.097",
        "historico": 591,
        "complemento": "Sicoob RDC Automatico - Pessoa 25",
    }


def test_competencia_erp_usa_data_padrao_fora_do_ultimo_dia():
    assert competencia_erp([_lanc("06/07/2026")], "31/07/2026") == "31/07/2026"


def test_competencia_erp_preserva_ultimo_dia():
    assert competencia_erp([_lanc("31/07/2026")], "15/08/2026") == "31/07/2026"


def test_csv_erp_grava_competencia_calculada():
    competencia = competencia_erp([_lanc("06/07/2026")], "31/07/2026")
    csv = exportar_csv_erp([_lanc("06/07/2026")], competencia, "37433314000198").decode("utf-8-sig")
    lote = next(linha for linha in csv.splitlines() if linha.startswith("LOT;"))

    assert ";31/07/2026;" in lote


def test_consolidar_csv_erp_mantem_um_cabecalho_para_varios_lotes():
    parte_a = exportar_csv_erp([_lanc("23/09/2026")], "05/10/2026", "03632872001728")
    parte_b = exportar_csv_erp([_lanc("30/09/2026")], "30/09/2026", "03632872001728")
    csv = consolidar_csv_erp([parte_a, parte_b])
    texto = csv.decode("utf-8-sig")
    linhas = texto.splitlines()
    cabecalho = "TIPO;COD LOTE;VLR CONTABIL LOTE;COMPETENCIA;"

    assert sum(linha.startswith(cabecalho) for linha in linhas) == 1
    assert sum(linha.startswith("LOT;") for linha in linhas) == 2
    assert "\ufeff" not in texto
    assert csv.startswith(b"\xef\xbb\xbf")
