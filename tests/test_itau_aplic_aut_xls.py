"""Regressao do formato HTML exportado com extensao .xls pelo Itaú."""
from __future__ import annotations

from modules.processor import processar_arquivo


def test_aplic_aut_mais_xls_html(tmp_path):
    arquivo = tmp_path / "APLICACAO AUTOMATICA 09.2026.xls"
    rows = [
        ["", "Extrato consolidado mensal Aplic Aut Mais"] + [""] * 13,
        ["", "Movimentação em Setembro/2026"] + [""] * 13,
        ["", "DATA"] + [""] * 13,
        ["", "31/08/2026"] + [""] * 8 + ["635.25", "705.42", "0.00", "12.28", "693.14"],
        ["", "30/09/2026"] + [""] * 8 + ["555.64", "620.87", "0.00", "11.41", "609.46"],
        ["", "Acum. Mês", "0.00", "79.61", "88.56", "0.00", "1.56", "87.00", "8.95", "7.39"] + [""] * 6,
    ]
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    arquivo.write_text(f"<html><body><table>{body}</table></body></html>", encoding="utf-8")

    resultado = processar_arquivo(str(arquivo), arquivo.name)[0]

    assert resultado["sucesso"] is True
    assert resultado["produto"] == "Aplic Aut Mais"
    assert resultado["metodo"] == "planilha/csv"
    assert resultado["dados"]["data_referencia"] == "30/09/2026"
    assert resultado["dados"]["saldo_atual"] == 555.64
    assert resultado["dados"]["provisao_irrf_atual"] == 11.41
    assert resultado["dados"]["rendimentos_pagos_mes"] == 8.95
