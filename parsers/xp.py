"""Parser XP Investimentos: Relatorio XPerformance (Evolucao Patrimonial)."""
from __future__ import annotations
import re
from . import br_to_float, norm, campo_padrao

_MESES = {
    "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04", "MAI": "05", "JUN": "06",
    "JUL": "07", "AGO": "08", "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12",
}

# Linha da tabela "Evolucao Patrimonial por Periodo":
# mai./26 R$ 437.269,94 R$ 0,00 R$ 0,00 R$ 0,00 R$ 438.090,57 R$ 820,64 0,19% 87,79%
_RE_LINHA = re.compile(
    r"([a-z]{3})\.?/(\d{2})\s+"
    r"-?R\$\s*([\d.]+,\d{2})\s+"      # patrimonio inicial
    r"(-?R\$\s*[\d.]+,\d{2})\s+"      # movimentacoes
    r"(-?R\$\s*[\d.]+,\d{2})\s+"      # IR
    r"(-?R\$\s*[\d.]+,\d{2})\s+"      # IOF
    r"-?R\$\s*([\d.]+,\d{2})\s+"      # patrimonio final
    r"(-?R\$\s*[\d.]+,\d{2})\s+"      # ganho financeiro
    r"(-?[\d.]+,\d+)%",               # rentabilidade
    re.IGNORECASE,
)


def parse(texto: str, paginas=None, caminho: str = "", nome_arquivo: str = "", rule_key: str = "",
          **kwargs) -> dict:
    # data de referencia
    m = re.search(r"Data de refer\w+ncia:\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    data_ref = m.group(1) if m else ""
    d = campo_padrao("XP", "XP Investimentos", "xp_investimentos", data_ref)

    linhas = []
    for mt in _RE_LINHA.finditer(texto):
        mes_abbr = norm(mt.group(1))[:3]
        ano = mt.group(2)
        mes_num = _MESES.get(mes_abbr, "00")
        linhas.append({
            "competencia": f"{mes_num}/20{ano}",
            "mes_abbr": mes_abbr,
            "patrimonio_inicial": br_to_float(mt.group(3)),
            "movimentacoes": br_to_float(mt.group(4)),
            "ir": br_to_float(mt.group(5)),
            "iof": br_to_float(mt.group(6)),
            "patrimonio_final": br_to_float(mt.group(7)),
            "ganho_financeiro": br_to_float(mt.group(8)),
        })

    d["movimentacoes"] = linhas
    d["campos_extra"]["evolucao_patrimonial"] = linhas

    # Mes de referencia: prioriza competencia_alvo (do usuario), senao usa data_ref,
    # senao a primeira linha (a tabela vem em ordem decrescente).
    alvo = None
    competencia_alvo = kwargs.get("competencia_alvo")
    if competencia_alvo and linhas:
        for ln in linhas:
            if ln["competencia"] == competencia_alvo:
                alvo = ln
                break
    if alvo is None and data_ref and linhas:
        comp_ref = data_ref[3:5] + "/" + data_ref[6:10]  # mm/yyyy
        for ln in linhas:
            if ln["competencia"] == comp_ref:
                alvo = ln
                break
    if alvo is None and linhas:
        alvo = linhas[0]

    if alvo:
        d["data_referencia"] = d["data_referencia"] or alvo["competencia"]
        d["rendimentos_pagos_mes"] = alvo["ganho_financeiro"]
        d["campos_extra"]["ganho_financeiro"] = alvo["ganho_financeiro"]
        d["saldo_atual"] = alvo["patrimonio_final"]
        d["saldo_bruto"] = alvo["patrimonio_final"]
        d["saldo_anterior"] = alvo["patrimonio_inicial"]
        d["irrf_retido_mes"] = abs(alvo["ir"])
        d["iof_retido_mes"] = abs(alvo["iof"])
        d["resgates"] = abs(alvo["movimentacoes"]) if alvo["movimentacoes"] < 0 else 0.0
        d["aplicacoes"] = alvo["movimentacoes"] if alvo["movimentacoes"] > 0 else 0.0

    # Patrimonio total bruto (cabecalho)
    m_pt = re.search(r"PATRIM\w+NIO TOTAL BRUTO:\s*R\$\s*([\d.]+,\d{2})", texto, re.IGNORECASE)
    if m_pt:
        d["campos_extra"]["patrimonio_total_bruto"] = br_to_float(m_pt.group(1))

    # Aviso quando nao foi possivel localizar a tabela de Evolucao Patrimonial
    # (ex.: "Extrato da Conta Investimento" da XP, que nao traz essa tabela).
    if not linhas:
        d["aviso"] = (
            "Nao foi encontrada a tabela 'Evolucao Patrimonial por Periodo' neste "
            "documento XP. Verifique se o arquivo e o relatorio XPerformance. "
            "Os valores de rendimento/IRRF/IOF podem precisar ser informados manualmente."
        )
    return d
