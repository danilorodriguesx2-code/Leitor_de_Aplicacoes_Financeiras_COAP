from parsers.sicoob import parse


def test_rdc_flexivel_ocr_com_valores_em_coluna_separada():
    texto = """05/10/2026 EXTRATO DE APROPRIAÇÃO DIÁRIA
Conta: 200.313-9
Número da aplicação: 16 Modalidade: RDC Flexível
Data Histórico
24/09/2026 APLICAÇÃO FINANCEIRA
25/09/2026 APROPRIAÇÃO DE CM
28/09/2026 APROPRIAÇÃO DE CM
29/09/2026 APROPRIAÇÃO DE CM
30/09/2026 APROPRIAÇÃO DE CM
Resumo
Saldo bruto em 30/09/2026:
Saldo disponível em 30/09/2026:
Valor
2.027.331,07C
1.039,94C
1.040,47C
1.041,00C
1.041,54C
2.031.494,02C
2.027.976,33C
"""

    d = parse(texto)

    assert d["produto"] == "RDC Flexivel"
    assert d["data_referencia"] == "30/09/2026"
    assert d["aplicacoes"] == 2027331.07
    assert d["rendimentos_pagos_mes"] == 4162.95
    assert d["saldo_bruto"] == 2031494.02
    assert d["saldo_atual"] == 2027331.07
    assert d["campos_extra"]["saldo_disponivel"] == 2027976.33
    assert len(d["movimentacoes"]) == 5


def test_rdc_flexivel_ocr_normaliza_leitura_de_c_euro():
    texto = """Data Histórico
31/08/2026 SALDO ANTERIOR 1.596,76€
01/09/2026 APROPRIAÇÃO DE CM 0,82€
23/09/2026 RESGATE DE APLICAÇÃO FINANCEIRA 1.581,19D
23/09/2026 RETENÇÃO DE IRRF 28,76D
Resumo
Saldo bruto em 23/09/2026: 0,00D
Saldo disponível em 23/09/2026: 0,00C
"""

    d = parse(texto)

    assert d["saldo_anterior"] == 1596.76
    assert d["rendimentos_pagos_mes"] == 0.82
    assert d["resgates"] == 1581.19
    assert d["irrf_retido_mes"] == 28.76
