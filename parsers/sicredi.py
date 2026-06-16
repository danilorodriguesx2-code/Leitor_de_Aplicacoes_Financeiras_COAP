"""Parser Sicredi: Sicredinvest, Evolutivo, Automatico e Poupanca Tradicional."""
from __future__ import annotations
import re
from . import br_to_float, norm, achar_valor, campo_padrao

_RE_LINHA_MOV = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.]+,\d{2})", re.MULTILINE)


def _valor_posicao(texto: str, rotulo: str) -> float:
    """Le valores do quadro 'Posicao para Saque' (rotulo seguido de numero)."""
    alvo = norm(rotulo)
    for linha in texto.splitlines():
        ln = norm(linha)
        # evita capturar 'SALDO ATUAL' da movimentacao com data
        if ln.strip().startswith(alvo):
            nums = re.findall(r"[\d.]+,\d{2}", linha)
            if nums:
                return br_to_float(nums[-1])
    return 0.0


def parse(texto: str, paginas=None, caminho: str = "", nome_arquivo: str = "", rule_key: str = "",
          **kwargs) -> dict:
    n = norm(texto)
    # Produto
    if "EVOLUTIVO" in n:
        produto, rk = "Sicredinvest Evolutivo", "sicredi_evolutivo"
    elif "AUTOMATICO" in n:
        produto, rk = "Sicredinvest Automatico", "sicredi_automatico"
    elif "POUPANCA" in n:
        produto, rk = "Poupanca Tradicional", "sicredi_poupanca"
    else:
        produto, rk = "Sicredinvest", "sicredi_sicredinvest"
    rk = rule_key or rk

    # data de referencia = data da 'Posicao em'
    m_pos = re.search(r"Posic\w+ em\s+(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    if not m_pos:
        m_pos = re.search(r"(\d{2}/\d{2}/\d{4})\s+Saldo Atual", texto, re.IGNORECASE)
    data_ref = m_pos.group(1) if m_pos else ""

    d = campo_padrao("Sicredi", produto, rk, data_ref)

    # Percorre movimentacao
    soma_rend = soma_irrf = soma_iof = soma_resg = soma_aplic = 0.0
    for mt in _RE_LINHA_MOV.finditer(texto):
        data, hist, val = mt.group(1), norm(mt.group(2)), br_to_float(mt.group(3))
        d["movimentacoes"].append({"data": data, "historico": mt.group(2).strip(), "valor": val})
        if "SALDO ANTERIOR" in hist:
            d["saldo_anterior"] = val
        elif "SALDO ATUAL" in hist:
            d["saldo_atual"] = val
        elif "APLICAC" in hist:
            soma_aplic += val
        elif "RESGATE" in hist:
            soma_resg += val
        elif "ENCARGOS DE IRRF" in hist:
            soma_irrf += val
        elif "ENCARGOS DE IOF" in hist:
            soma_iof += val
        elif "RENDIMENTO" in hist:
            soma_rend += val

    d["rendimentos_pagos_mes"] = round(soma_rend, 2)
    d["irrf_retido_mes"] = round(soma_irrf, 2)
    d["iof_retido_mes"] = round(soma_iof, 2)
    d["resgates"] = round(soma_resg, 2)
    d["aplicacoes"] = round(soma_aplic, 2)

    # Quadro Posicao para Saque
    saldo_atual_pos = _valor_posicao(texto, "Saldo Atual")
    if saldo_atual_pos:
        d["saldo_atual"] = saldo_atual_pos
    d["rendimentos_provisionados_atual"] = _valor_posicao(texto, "Rendimentos Provisionados")
    d["saldo_bruto"] = _valor_posicao(texto, "Saldo Bruto")
    d["provisao_irrf_atual"] = _valor_posicao(texto, "Provisao IRRF")
    d["provisao_iof_atual"] = _valor_posicao(texto, "Provisao IOF")

    d["campos_extra"] = {
        "liquido_para_saque": _valor_posicao(texto, "Liquido para Saque"),
        "cooperativa": _extra(texto, r"Cooperativa:\s*(\d+)"),
        "conta_corrente": _extra(texto, r"Conta Corrente:\s*(\d+)"),
        "periodo": _extra(texto, r"Per\w+odo de Consulta:\s*([\d/ a]+)"),
    }
    return d


def _extra(texto, pat):
    m = re.search(pat, texto, re.IGNORECASE)
    return m.group(1).strip() if m else ""
