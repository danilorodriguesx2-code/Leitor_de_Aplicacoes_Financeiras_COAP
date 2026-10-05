"""Regressao do extrato PDF do Itaú Aplic Aut Mais."""
from __future__ import annotations

from modules.processor import _detectar_extensao
from parsers.itau import parse as parse_itau


TEXTO_APLIC_AUT_PDF = """APLIC AUT MAIS - EXTRATO CONSOLIDADO DE MOVIMENTAÇÃO
Movimentação em Agosto/2026
31/07/2026 715,30 789,27 0,00 12,94 776,33
04/08/2026 80,05 88,47 0,00 1,47 87,00 8,42 6,95 635,25 701,29 0,00 11,55 689,74
31/08/2026 635,25 705,42 0,00 12,28 693,14
Acum. Mês 0,00 80,05 88,47 1,47 87,00 8,42 6,95
"""


def test_aplic_aut_mais_pdf_nativo():
    dados = parse_itau(TEXTO_APLIC_AUT_PDF, caminho="extrato.pdf", nome_arquivo="extrato.aspx")

    assert dados["rule_key"] == "itau_aplic_aut_mais"
    assert dados["data_referencia"] == "31/08/2026"
    assert dados["saldo_anterior"] == 715.30
    assert dados["saldo_atual"] == 635.25
    assert dados["saldo_bruto"] == 705.42
    assert dados["provisao_irrf_atual"] == 12.28
    assert dados["provisao_irrf_anterior"] == 12.94
    assert dados["rendimentos_pagos_mes"] == 8.42
    assert dados["resgates"] == 88.47


def test_pdf_com_extensao_aspx_eh_detectado(tmp_path):
    arquivo = tmp_path / "extrato.aspx"
    arquivo.write_bytes(b"%PDF-1.7\nconteudo")

    assert _detectar_extensao(str(arquivo), arquivo.name) == "pdf"
